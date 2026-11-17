# -*- coding: utf-8 -*-
"""
阶段 2：下载 100 篇 PDF（断点续传 + 并发 + 重试）。

arXiv 对并发有软限速，这里用 5 个 worker、每个请求间隔 0.8 s，
失败退避重试 4 次；已存在且 >60 KB 的文件直接跳过（可反复重跑）。
"""
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

ROOT = r"E:\研究生学习\03_科研与论文\毕业论文参考文献_2026-11-16"
PDFDIR = os.path.join(ROOT, "pdf")
REP = os.path.join(ROOT, "report")
WORKERS = 5
MIN_BYTES = 60 * 1024

_lock = threading.Lock()


def fname(r):
    """R101_2026_Title_Slug_2603.16301.pdf —— 按题名生成，便于人眼扫。"""
    t = re.sub(r"[^A-Za-z0-9 ]+", " ", r["title"])
    slug = "_".join(t.split())[:48].strip("_")
    return f"R{r['rank']}_{r['published'][:4]}_{slug}_{r['arxiv_id']}.pdf"


def fetch(r, sess):
    path = os.path.join(PDFDIR, fname(r))
    if os.path.exists(path) and os.path.getsize(path) > MIN_BYTES:
        return r["rank"], "cached", os.path.getsize(path), path
    url = f"https://arxiv.org/pdf/{r['arxiv_id']}"
    last = ""
    for attempt in range(4):
        try:
            resp = sess.get(url, timeout=90, allow_redirects=True)
            if resp.status_code == 200 and resp.content[:4] == b"%PDF":
                with open(path, "wb") as f:
                    f.write(resp.content)
                return r["rank"], "ok", len(resp.content), path
            last = f"HTTP {resp.status_code} head={resp.content[:8]!r}"
        except Exception as ex:
            last = f"{type(ex).__name__}: {ex}"
        time.sleep(2.5 * (attempt + 1))
    return r["rank"], "FAILED", 0, last


def main():
    d = json.load(open(os.path.join(REP, "01_selected100.json"), encoding="utf-8"))
    refs = d["refs"]
    os.makedirs(PDFDIR, exist_ok=True)

    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (academic literature survey; contact: local)",
        "Accept": "application/pdf,*/*",
    })

    t0 = time.time()
    done, failed = [], []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {}
        for r in refs:
            futs[ex.submit(fetch, r, sess)] = r
            time.sleep(0.8 / WORKERS)
        for i, fut in enumerate(as_completed(futs), 1):
            r = futs[fut]
            rank, st, size, info = fut.result()
            if st == "FAILED":
                failed.append({"rank": rank, "arxiv_id": r["arxiv_id"],
                               "title": r["title"], "err": info})
                print(f"[{i:3d}/{len(refs)}] R{rank} FAILED  {r['arxiv_id']}  {info[:70]}", flush=True)
            else:
                done.append({"rank": rank, "status": st, "bytes": size, "file": os.path.basename(info)})
                if st == "ok":
                    print(f"[{i:3d}/{len(refs)}] R{rank} ok {size/1024/1024:5.2f}MB  {r['arxiv_id']}", flush=True)

    # 回填 pdf_file 到选中列表
    by_rank = {x["rank"]: x for x in done}
    for r in refs:
        x = by_rank.get(r["rank"])
        r["pdf_file"] = x["file"] if x else ""

    json.dump(d, open(os.path.join(REP, "02_selected100_with_pdf.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    total_b = sum(x["bytes"] for x in done)
    ok = sum(1 for x in done if x["status"] == "ok")
    cached = sum(1 for x in done if x["status"] == "cached")
    res = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
           "wanted": len(refs), "ok": ok, "cached": cached,
           "failed": len(failed), "total_mb": round(total_b / 1024 / 1024, 1),
           "seconds": round(time.time() - t0, 1), "failures": failed}
    json.dump(res, open(os.path.join(REP, "02_download_result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("\n" + "=" * 62)
    print(f"下载完成：新下 {ok} 篇，复用缓存 {cached} 篇，失败 {len(failed)} 篇")
    print(f"总大小 {res['total_mb']} MB，耗时 {res['seconds']} s")
    if failed:
        print("失败清单：")
        for x in failed:
            print(f"   R{x['rank']} {x['arxiv_id']} {x['title'][:50]}")
    print(f"目录 -> {PDFDIR}")
    print("=" * 62)


if __name__ == "__main__":
    main()
