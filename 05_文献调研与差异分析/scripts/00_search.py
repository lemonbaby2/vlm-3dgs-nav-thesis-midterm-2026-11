# -*- coding: utf-8 -*-
"""
阶段 0：检索统计（不下载）。目标：用事实回答"2025-11-01 ~ 2026-11-16 窗口内到底能捞到多少篇"。

沿用 2026-11-13 那轮的 30 组检索式基础，删掉旧条目、补足近期方向，
全部套上 submittedDate 窗口，按 arXiv id 去重后统计。
"""
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

import requests

ROOT = r"E:\研究生学习\03_科研与论文\毕业论文参考文献_2026-11-16"
REP = os.path.join(ROOT, "report")
API = "https://export.arxiv.org/api/query"

# 时间窗（用户要求：2025.11 — 2026.11.16）
WIN = "submittedDate:[202511010000 TO 202611162359]"

# 主题分组：G=建图底座  V=视觉语言  D=动态  N=导航
QUERIES = [
    # —— 3DGS 语义 / 语言底座 ——
    ("G01_高斯语义", 'abs:"Gaussian Splatting" AND (abs:semantic OR abs:language)', 100),
    ("G02_开放词汇高斯", 'abs:"Gaussian Splatting" AND abs:"open-vocabulary"', 80),
    ("G03_高斯SLAM", 'abs:"Gaussian Splatting" AND abs:SLAM', 100),
    ("G04_高斯建图", 'abs:"3D Gaussian" AND (abs:mapping OR abs:"scene reconstruction")', 100),
    ("G05_语言嵌入场", '(abs:"language embedded" OR abs:"language-embedded" OR abs:"language field") AND abs:"3D"', 80),
    ("G06_高斯场景图", 'abs:"scene graph" AND (abs:Gaussian OR abs:"3D")', 80),
    ("G07_语义高斯SLAM", 'abs:Gaussian AND abs:SLAM AND abs:semantic', 60),
    # —— 视觉语言模型 ——
    ("V01_VLM三维", 'abs:"vision-language model" AND (abs:"3D" OR abs:mapping)', 100),
    ("V02_开放词汇三维", 'abs:"open-vocabulary" AND (abs:"3D scene" OR abs:mapping)', 100),
    ("V03_LLM具身", 'abs:"large language model" AND abs:embodied', 100),
    ("V04_VLA", 'abs:"vision-language-action" OR abs:"vision language action model"', 100),
    ("V05_基础模型机器人", '(abs:"foundation model" OR abs:"vision foundation model") AND abs:robot', 80),
    ("V06_视觉语言导航", 'abs:"vision-and-language navigation" OR abs:"vision language navigation" OR abs:VLN', 100),
    ("V07_语义地图语言", 'abs:language AND abs:"semantic map"', 80),
    # —— 动态环境 ——
    ("D01_动态高斯", 'abs:"Gaussian Splatting" AND abs:dynamic', 100),
    ("D02_动态场景重建", 'abs:dynamic AND (abs:"neural rendering" OR abs:"radiance field")', 80),
    ("D03_动态SLAM", 'abs:SLAM AND abs:dynamic AND (abs:semantic OR abs:object)', 100),
    ("D04_动态地图更新", 'abs:"map update" OR abs:"map updating" AND abs:robot', 60),
    ("D05_长期建图", 'abs:"long-term" AND (abs:"semantic mapping" OR abs:"map maintenance")', 60),
    ("D06_变化检测三维", 'abs:"change detection" AND abs:"3D"', 60),
    ("D07_动态物体剔除", '(abs:"dynamic object removal" OR abs:"dynamic removal") AND (abs:SLAM OR abs:mapping)', 60),
    # —— 机器人目标导航 ——
    ("N01_ObjectNav", 'abs:"object-goal navigation" OR abs:"object goal navigation" OR abs:ObjectNav', 100),
    ("N02_导航VLM", '(abs:"vision-language model" OR abs:VLM) AND abs:navigation', 100),
    ("N03_语义导航", 'abs:semantic AND abs:navigation AND abs:robot', 100),
    ("N04_主动搜索", '(abs:"object search" OR abs:"active perception") AND abs:robot', 100),
    ("N05_最佳视点", 'abs:"next best view" AND (abs:robot OR abs:exploration)', 60),
    ("N06_具身导航", 'abs:embodied AND abs:navigation', 100),
    ("N07_零样本导航", '(abs:"zero-shot" OR abs:"open-vocabulary") AND abs:navigation', 80),
    ("N08_高斯导航", 'abs:Gaussian AND abs:navigation', 60),
    ("N09_场景图导航", 'abs:"scene graph" AND abs:navigation', 60),
    ("N10_蒙特卡洛目标搜索", '(abs:"probabilistic" OR abs:"belief") AND abs:"object search"', 50),
    # —— 支撑技术 ——
    ("S01_实例分割三维", '(abs:"instance segmentation" OR abs:"panoptic") AND abs:"3D"', 60),
    ("S02_点云语义", 'abs:"point cloud" AND abs:semantic AND (abs:segmentation OR abs:mapping)', 80),
    ("S03_不确定性建图", 'abs:uncertainty AND (abs:mapping OR abs:"semantic map")', 60),
    ("S04_多传感器融合定位", '(abs:"LiDAR-inertial" OR abs:"multi-sensor fusion") AND abs:SLAM', 60),
    ("S05_语义SLAM综述", 'abs:survey AND abs:SLAM AND abs:semantic', 40),
]


def parse_feed(txt):
    """极简 Atom 解析，不依赖 feedparser。"""
    out = []
    for m in re.finditer(r"<entry>(.*?)</entry>", txt, re.S):
        e = m.group(1)

        def grab(tag, src=e):
            mm = re.search(rf"<{tag}>(.*?)</{tag}>", src, re.S)
            return re.sub(r"\s+", " ", mm.group(1)).strip() if mm else ""

        aid_url = grab("id")
        aid = aid_url.rsplit("/", 1)[-1] if aid_url else ""
        base = re.sub(r"v\d+$", "", aid)
        title = grab("title")
        summ = grab("summary")
        pub = grab("published")
        upd = grab("updated")
        authors = re.findall(r"<name>(.*?)</name>", e)
        cats = re.findall(r'<category[^>]*term="([^"]+)"', e)
        comment = grab("arxiv:comment")
        jref = grab("arxiv:journal_ref")
        doi = grab("arxiv:doi")
        out.append({
            "arxiv_id": base,
            "title": title,
            "abstract": summ,
            "published": pub,
            "updated": upd,
            "authors": authors,
            "cats": cats,
            "primary_cat": cats[0] if cats else "",
            "comment": comment,
            "journal_ref": jref,
            "doi": doi,
            "abs_url": f"https://arxiv.org/abs/{base}",
            "pdf_url": f"https://arxiv.org/pdf/{base}",
        })
    return out


def main():
    pool = {}
    per_query = {}
    sess = requests.Session()
    sess.headers.update({"User-Agent": "thesis-ref-survey/1.0 (academic use)"})

    for name, q, n in QUERIES:
        full = f"({q}) AND {WIN}"
        params = {
            "search_query": full,
            "start": 0,
            "max_results": n,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        got, total = 0, None
        for attempt in range(4):
            try:
                r = sess.get(API, params=params, timeout=60)
                if r.status_code == 200:
                    ents = parse_feed(r.text)
                    mm = re.search(r"<opensearch:totalResults[^>]*>(\d+)<", r.text)
                    total = int(mm.group(1)) if mm else len(ents)
                    got = len(ents)
                    for e in ents:
                        e["hit_by"] = [name]
                        if e["arxiv_id"] in pool:
                            pool[e["arxiv_id"]]["hit_by"].append(name)
                        else:
                            pool[e["arxiv_id"]] = e
                    break
                else:
                    print(f"  [{name}] HTTP {r.status_code}, retry {attempt+1}", flush=True)
            except Exception as ex:
                print(f"  [{name}] {type(ex).__name__}: {ex}, retry {attempt+1}", flush=True)
            time.sleep(4 + 3 * attempt)
        per_query[name] = {"query": q, "total": total, "fetched": got}
        print(f"[{name}] total={total} fetched={got} pool={len(pool)}", flush=True)
        time.sleep(3.2)  # arXiv 限速：3 秒一次

    # 统计
    def month(pub):
        return pub[:7] if pub else "?"

    months = Counter(month(e["published"]) for e in pool.values())
    cat = Counter(e["primary_cat"] for e in pool.values())
    multi = sum(1 for e in pool.values() if len(e["hit_by"]) > 1)

    res = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "window": "2025-11-01 ~ 2026-11-16",
        "queries": per_query,
        "pool_size": len(pool),
        "multi_hit": multi,
        "by_month": dict(sorted(months.items())),
        "by_primary_cat": dict(cat.most_common(15)),
        "candidates": list(pool.values()),
    }
    os.makedirs(REP, exist_ok=True)
    p = os.path.join(REP, "00_search_pool.json")
    json.dump(res, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("\n" + "=" * 62)
    print(f"去重后候选池：{len(pool)} 篇（其中被 ≥2 个检索式命中的 {multi} 篇）")
    print("按月分布：")
    for k, v in sorted(months.items()):
        print(f"   {k}  {v:4d}  {'#' * min(v, 50)}")
    print("\n主分类 Top10：")
    for k, v in cat.most_common(10):
        print(f"   {k:14s} {v}")
    print(f"\n池子 -> {p}")
    print("=" * 62)


if __name__ == "__main__":
    main()
