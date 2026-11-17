# -*- coding: utf-8 -*-
"""
fetch_sota.py — 每日追踪最新论文与开源指标，评估与本地结果的差距

做三件事：
 1) 用 arXiv API 按四支柱（3DGS / VLM / 动态 / 导航）抓最近 N 天新论文
 2) 从摘要里抽 PSNR / SSIM / ATE / FPS 等数字型指标，记录声称的 SOTA
 3) 与本地 state.json 的实测结果对比，输出差距表（供人判断，不自动宣称超越）

输出：
    papers/YYYY-MM-DD.json      当日抓取的论文清单（含指标抽取）
    reports/YYYY-MM-DD_sota.md  差距说明

用法：
    python fetch_sota.py                # 抓最近 7 天
    python fetch_sota.py --days 30
"""
import os
import re
import json
import time
import argparse
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER_DIR = os.path.join(HERE, "papers")
REPORT_DIR = os.path.join(HERE, "reports")
STATE = os.path.join(HERE, "state.json")
ARXIV = "http://export.arxiv.org/api/query"

ATOM = "{http://www.w3.org/2005/Atom}"

QUERIES = {
    "G 高斯建图": 'all:"3D Gaussian" AND (all:splatting OR all:SLAM OR all:mapping)',
    "D 动态环境": 'all:dynamic AND all:Gaussian AND (all:SLAM OR all:mapping)',
    "V 视觉语言": 'all:"vision-language" AND all:"3D Gaussian"',
    "N 目标导航": 'all:"object goal navigation" OR all:"object-goal navigation"',
}

# 指标抽取：只认带单位的明确数字，避免把 "3D" 当指标
PATTERNS = {
    "PSNR": re.compile(
        r"(?:PSNR|psnr)[^0-9\n]{0,25}(\d{2}(?:\.\d+)?)"
        r"|(\d{2}(?:\.\d+)?)\s*dB[^0-9\n]{0,20}(?:PSNR|psnr)"
        r"|(\d{2}\.\d+)\s*dB", re.I),
    "SSIM": re.compile(r"(?:SSIM|ssim)[^0-9\n]{0,20}(0\.\d{3,4})|(0\.\d{3,4})\s*(?:SSIM|ssim)", re.I),
    "ATE": re.compile(r"(?:ATE|absolute trajectory error)[^0-9\n]{0,25}(\d?\.\d{2,4})", re.I),
    "FPS": re.compile(r"(\d{2,4})\s*(?:FPS|fps)", re.I),
}


def fetch(query, max_results=40, days=7, retries=3):
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y%m%d%H%M")
    q = f'({query}) AND submittedDate:[{since} TO 299912312359]'
    params = {
        "search_query": q, "start": 0, "max_results": max_results,
        "sortBy": "submittedDate", "sortOrder": "descending",
    }
    url = ARXIV + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=45) as r:
                return r.read()
        except Exception as e:
            if attempt == retries - 1:
                print(f"  [warn] 检索失败 {query[:40]}…: {e}")
                return None
            time.sleep(3 * (attempt + 1))
    return None


def extract(abstract):
    hits = {}
    for name, pat in PATTERNS.items():
        m = pat.search(abstract)
        if m:
            v = next((g for g in m.groups() if g), None)
            if v:
                hits[name] = float(v)
    return hits


def parse(xml_bytes, pillar):
    out = []
    if not xml_bytes:
        return out
    root = ET.fromstring(xml_bytes)
    for e in root.findall(f"{ATOM}entry"):
        title = " ".join((e.findtext(f"{ATOM}title") or "").split())
        summ = " ".join((e.findtext(f"{ATOM}summary") or "").split())
        pub = (e.findtext(f"{ATOM}published") or "")[:10]
        link = ""
        aid = e.findtext(f"{ATOM}id") or ""
        for ln in e.findall(f"{ATOM}link"):
            if ln.get("rel") == "alternate":
                link = ln.get("href")
        cats = [c.get("term") for c in e.findall(f"{ATOM}category")]
        metrics = extract(summ)
        out.append({
            "pillar": pillar, "title": title, "published": pub,
            "arxiv_id": aid.rsplit("/", 1)[-1], "url": link or aid,
            "categories": cats, "metrics": metrics,
            "code_hint": bool(re.search(r"github\.com|code (?:is )?(?:available|released)|open[- ]source", summ, re.I)),
            "abstract_head": summ[:400],
        })
    return out


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--max", type=int, default=40)
    ap.add_argument("--milestone", action="store_true",
                    help="额外抓近一年带指标的里程碑论文（慢，建议每周一次）")
    args = ap.parse_args()

    os.makedirs(PAPER_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    all_papers, seen = [], set()
    for pillar, q in QUERIES.items():
        print(f"[fetch] {pillar} (最近 {args.days} 天) …", flush=True)
        raw = fetch(q, args.max, args.days)
        papers = parse(raw, pillar)
        for p in papers:
            if p["arxiv_id"] in seen:
                continue
            seen.add(p["arxiv_id"])
            all_papers.append(p)
        print(f"   {len(papers)} 篇（去重后累计 {len(all_papers)}）", flush=True)
        time.sleep(3)  # arXiv 礼貌间隔

    if args.milestone:
        print("[fetch] 近一年里程碑（365 天，仅保留摘要含显式指标的） …", flush=True)
        mile = []
        for pillar, q in QUERIES.items():
            got = parse(fetch(q, 100, 365), pillar)
            mile += [x for x in got if x["metrics"]]
            print(f"   {pillar}: 带指标 {len([x for x in got if x['metrics']])}/{len(got)}", flush=True)
            time.sleep(3)
        seen2, uniq = set(), []
        for x in sorted(mile, key=lambda y: -y["metrics"].get("PSNR", 0)):
            if x["arxiv_id"] in seen2:
                continue
            seen2.add(x["arxiv_id"]); uniq.append(x)
        with open(os.path.join(PAPER_DIR, f"milestone_{today}.json"), "w", encoding="utf-8") as f:
            json.dump({"date": today, "days": 365, "count": len(uniq), "papers": uniq},
                      f, ensure_ascii=False, indent=2)
        print(f"[milestone] {len(uniq)} 篇带指标 → papers/milestone_{today}.json", flush=True)

    all_papers.sort(key=lambda x: x["published"], reverse=True)
    with open(os.path.join(PAPER_DIR, f"{today}.json"), "w", encoding="utf-8") as f:
        json.dump({"date": today, "days": args.days, "count": len(all_papers),
                   "papers": all_papers}, f, ensure_ascii=False, indent=2)

    # ---- 与本地实测对比 ----
    state = load_state()
    local = state.get("baseline", {}).get("dyn-mask", {})
    local_psnr = local.get("psnr_static_mean", {}).get("mean") if local else None
    local_ghost = local.get("ghost_residual_mean", {}).get("mean") if local else None

    with_metrics = [p for p in all_papers if p["metrics"]]
    with_code = [p for p in all_papers if p["code_hint"]]

    md = [f"# SOTA 追踪 {today}", "",
          f"- 时间窗：最近 {args.days} 天",
          f"- 抓取论文：**{len(all_papers)}** 篇（四支柱去重后）",
          f"- 摘要中出现显式指标的：{len(with_metrics)} 篇",
          f"- 提及开源代码的：{len(with_code)} 篇", ""]

    md += ["## 一、本地实测基线（B 动态掩码加权）", ""]
    if local_psnr is not None:
        md += [f"- 静态区 PSNR：**{local_psnr:.3f} dB**",
               f"- 动态残影：**{local_ghost:.5f}**", ""]
    else:
        md += ["- 尚未建立基线（先跑一次 `daily_verify.py`）", ""]

    md += ["## 二、带指标的论文（按 PSNR 降序）", ""]
    if with_metrics:
        md += ["| PSNR | SSIM | ATE | FPS | 日期 | 标题 |", "|---|---|---|---|---|---|"]
        for p in sorted(with_metrics, key=lambda x: -x["metrics"].get("PSNR", 0))[:25]:
            m = p["metrics"]
            md.append(f"| {m.get('PSNR','—')} | {m.get('SSIM','—')} | {m.get('ATE','—')} | "
                      f"{m.get('FPS','—')} | {p['published']} | [{p['title'][:60]}]({p['url']}) |")
    else:
        md.append("_本窗口内没有论文在摘要中给出可直接引用的指标数字。_")
    md.append("")

    md += ["## 三、判定口径（重要）", "",
           "摘要里的 PSNR 与本仓库的 PSNR **不可直接比较**：",
           "本仓库为 12 帧 / 160×120 / 5000 点 / 2500 迭代的解析合成场景，",
           "论文多为 Replica / TUM / NeRF Synthetic 全分辨率。",
           "因此本表只用于**判断领域水位与动向**，不用于宣称超越。",
           "要真正对标，必须换到同一数据集、同一划分、同一分辨率重跑。", ""]

    md_path = os.path.join(REPORT_DIR, f"{today}_sota.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"[ok] {len(all_papers)} 篇 → {md_path}")

    state["last_sota_fetch"] = {"date": today, "count": len(all_papers),
                                "with_metrics": len(with_metrics), "with_code": len(with_code)}
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
