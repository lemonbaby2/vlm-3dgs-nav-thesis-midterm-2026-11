# -*- coding: utf-8 -*-
"""
阶段 1：从 1845 篇候选池里精选 100 篇（严格 2025-11-01 ~ 2026-11-16）。

选取原则（可解释、可复查，不靠手感）：
  1) 四支柱配额：G=高斯建图底座 28 / V=视觉语言 24 / D=动态环境 22 / N=目标导航 26
  2) 组内打分 = 多检索式命中数 × 2 + 标题核心词命中 × 3 + 摘要核心词命中 × 1
     + 近期加权（2026 年 +3，2026-06 之后 +2）
  3) 排除上一轮已入库的 50 篇（按 arXiv id 比对），避免重复下载
  4) 每个支柱内部做一次标题去重（防同一工作多版本）
"""
import json
import os
import re
import time

ROOT = r"E:\研究生学习\03_科研与论文\毕业论文参考文献_2026-11-16"
REP = os.path.join(ROOT, "report")
OLD = r"E:\研究生学习\03_科研与论文\毕业论文参考文献_2026-11-13\report\refs50_final.json"

QUOTA = {"G": 28, "V": 24, "D": 22, "N": 26}

# 时间分层：保证 12 个月窗口都有覆盖（否则全挤在最近三个月，综述看不出演进脉络）
# (起月, 止月, 名额比例)
QSPLIT = [
    ("2025-11", "2026-01", 0.18),
    ("2026-02", "2026-04", 0.18),
    ("2026-05", "2026-07", 0.26),
    ("2026-08", "2026-11", 0.38),
]

# 支柱归属：检索式名前缀
PREFIX = {"G": "G", "V": "V", "D": "D", "N": "N"}

# 标题核心词（出现在标题里，说明是该文的主线而非顺带提及）
TITLE_CORE = {
    "G": ["gaussian splatting", "3d gaussian", "gaussian", "splat", "radiance field",
          "semantic map", "open-vocabulary", "language-embedded", "language embedded",
          "scene graph", "slam", "mapping"],
    "V": ["vision-language", "vision language", "vlm", "language model", "llm",
          "open-vocabulary", "language-grounded", "language embedded", "clip",
          "foundation model", "vla", "vision-and-language"],
    "D": ["dynamic", "moving object", "deformable", "4d", "change detection",
          "long-term", "lifelong", "map update", "transient"],
    "N": ["navigation", "object goal", "objectnav", "object-goal", "exploration",
          "active search", "embodied", "next best view", "goal-oriented", "planner"],
}
# 摘要核心词（弱权重，用于同类内排序）
ABS_CORE = {
    "G": ["3d gaussian splatting", "gaussian", "semantic", "open-vocabulary", "slam"],
    "V": ["vision-language model", "language", "open-vocabulary", "clip", "llm"],
    "D": ["dynamic", "moving", "change", "long-term"],
    "N": ["navigation", "object goal", "exploration", "embodied", "policy"],
}


def load_old_ids():
    if not os.path.exists(OLD):
        return set()
    d = json.load(open(OLD, encoding="utf-8"))
    return {r["arxiv_id"] for r in d.get("refs", [])}


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def pillar_of(hit_by):
    """按命中的检索式前缀投票，取多数。"""
    votes = {}
    for h in hit_by:
        p = h[0]
        if p in PREFIX:
            votes[p] = votes.get(p, 0) + 1
    if not votes:
        return None
    return max(votes.items(), key=lambda kv: kv[1])[0]


def score(e, pillar):
    s = len(e["hit_by"]) * 2.0
    t = (e["title"] or "").lower()
    a = (e["abstract"] or "").lower()
    s += sum(3.0 for k in TITLE_CORE[pillar] if k in t)
    s += sum(1.0 for k in ABS_CORE[pillar] if k in a)
    pub = e.get("published", "")
    if pub.startswith("2026"):
        s += 3.0
        if pub >= "2026-06":
            s += 2.0
    # 纯综述在开题里价值高，额外加权
    if re.search(r"\bsurvey\b|\breview\b|\bbenchmark\b", t):
        s += 2.5
    return s


def main():
    d = json.load(open(os.path.join(REP, "00_search_pool.json"), encoding="utf-8"))
    pool = d["candidates"]
    old = load_old_ids()
    print(f"[in] 候选 {len(pool)} 篇；上一轮已有 {len(old)} 篇将跳过")

    # 归属 + 过滤
    buckets = {k: [] for k in QUOTA}
    skipped_old, no_pillar = 0, 0
    for e in pool:
        if e["arxiv_id"] in old:
            skipped_old += 1
            continue
        p = pillar_of(e["hit_by"])
        if p is None:
            no_pillar += 1
            continue
        e["pillar"] = p
        e["score"] = round(score(e, p), 2)
        buckets[p].append(e)

    print(f"[filter] 跳过已有 {skipped_old}；无支柱归属 {no_pillar}")
    for k, v in buckets.items():
        print(f"   {k}: {len(v)} 篇可竞争 {QUOTA[k]} 个名额")

    # 组内排序 + 标题去重 + 配额截断（按时间分层分配，避免全挤在最近三个月）
    chosen = []
    for p, quota in QUOTA.items():
        arr = sorted(buckets[p], key=lambda x: -x["score"])
        # 先按标题去重
        seen, uniq = set(), []
        for e in arr:
            nt = norm_title(e["title"])
            if nt in seen:
                continue
            seen.add(nt)
            uniq.append(e)

        # 分季度
        cohorts = {}
        for a, b, _ in QSPLIT:
            cohorts[(a, b)] = [e for e in uniq if a <= e["published"][:7] <= b]
        # 分配名额
        take, used = [], set()
        need = quota
        for idx, (a, b, frac) in enumerate(QSPLIT):
            want = round(quota * frac)
            pool_q = [e for e in cohorts[(a, b)] if e["arxiv_id"] not in used]
            got = pool_q[:want]
            for e in got:
                used.add(e["arxiv_id"])
            take.extend(got)
            need -= len(got)
        # 某季度不足时，用剩余最高分补齐
        if need > 0:
            rest = [e for e in uniq if e["arxiv_id"] not in used]
            take.extend(rest[:need])
        chosen.extend(take[:quota])
        cnt = {}
        for e in take[:quota]:
            k = next(f"{a}~{b}" for a, b, _ in QSPLIT if a <= e["published"][:7] <= b)
            cnt[k] = cnt.get(k, 0) + 1
        print(f"[pick] {p}: 取 {len(take[:quota])} 篇  分布 {cnt}")

    # 全局按支柱编号 R101 起
    chosen.sort(key=lambda x: (x["pillar"], -x["score"]))
    for i, e in enumerate(chosen, start=101):
        e["rank"] = i

    out = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "window": "2025-11-01 ~ 2026-11-16",
        "total": len(chosen),
        "quota": QUOTA,
        "refs": chosen,
    }
    p = os.path.join(REP, "01_selected100.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"\n{'='*62}\n总计选出 {len(chosen)} 篇 -> {p}")
    for pil in QUOTA:
        sub = [e for e in chosen if e["pillar"] == pil]
        print(f"\n--- {pil} ({len(sub)} 篇) ---")
        for e in sub[:6]:
            print(f"  R{e['rank']} [{e['score']:5.1f}] {e['published'][:7]} {e['title'][:66]}")
        if len(sub) > 6:
            print(f"  ... 另 {len(sub)-6} 篇")
    print("=" * 62)


if __name__ == "__main__":
    main()
