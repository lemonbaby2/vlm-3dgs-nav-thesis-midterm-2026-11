# -*- coding: utf-8 -*-
"""
阶段 3：把 100 篇真实写入 Zotero（Connector API v3），复用 2026-11-13 那轮已验证的通道。
  - /connector/saveItems     写元数据（自带 connector key 供附件挂载）
  - /connector/saveAttachment 用本地已下载 PDF 二进制挂子附件（不联网重下）
  - 幂等：按归一化标题去重，已存在的跳过
"""
import json
import os
import re
import sys
import time
import unicodedata
import uuid

import requests

ROOT = r"E:\研究生学习\03_科研与论文\毕业论文参考文献_2026-11-16"
REP = os.path.join(ROOT, "report")
PDFDIR = os.path.join(ROOT, "pdf")
API = "http://127.0.0.1:23119"
TAG = "毕业论文参考文献100_2025-11至2026-11"
BATCH = 8

PILLAR_NAME = {
    "G": "高斯建图底座",
    "V": "视觉语言模型",
    "D": "动态环境",
    "N": "机器人目标导航",
}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def existing_titles():
    titles, start = set(), 0
    while True:
        r = requests.get(API + "/api/users/0/items",
                         params={"limit": 100, "start": start}, timeout=25,
                         headers={"Zotero-API-Version": "3"})
        if r.status_code != 200:
            print("[warn] local API", r.status_code, flush=True)
            break
        arr = r.json()
        for it in arr:
            t = (it.get("data") or {}).get("title")
            if t:
                titles.add(norm(t))
        if len(arr) < 100:
            break
        start += 100
    return titles


def counts():
    out = {}
    for label, params in [("items", {"limit": 1}),
                          ("attachments", {"limit": 1, "itemType": "attachment"}),
                          ("tagged", {"limit": 1, "tag": TAG})]:
        try:
            r = requests.get(API + "/api/users/0/items", params=params, timeout=20,
                             headers={"Zotero-API-Version": "3"})
            out[label] = int(r.headers.get("Total-Results", 0))
        except Exception:
            out[label] = -1
    return out


def split_author(n):
    p = n.split()
    if not p:
        return {"firstName": "", "lastName": n, "creatorType": "author"}
    return {"firstName": " ".join(p[:-1]), "lastName": p[-1], "creatorType": "author"}


def make_item(r):
    venue = (r.get("journal_ref") or "").strip()
    is_conf = bool(re.search(r"CVPR|ICCV|ECCV|ICRA|IROS|AAAI|CoRL|NeurIPS|RSS|WACV|ICML|ICLR|"
                             r"Conference|Symposium|Proceedings|Workshop|3DV|SIGGRAPH", venue, re.I))
    is_journal = bool(re.search(r"Transactions|Journal|Letters|Review|IJRR|TPAMI|TOG|RA-L", venue, re.I))
    if venue and not venue.lower().startswith("arxiv"):
        itype = "conferencePaper" if is_conf else ("journalArticle" if is_journal else "conferencePaper")
    else:
        itype = "preprint"
    item = {
        "id": f"thesisref100-R{r['rank']}",
        "itemType": itype,
        "title": r["title"],
        "creators": [split_author(a) for a in r["authors"][:20]],
        "date": r["published"][:10],
        "url": r["abs_url"],
        "abstractNote": (r.get("abstract") or "")[:2000],
        "repository": "arXiv",
        "archiveID": "arXiv:" + r["arxiv_id"],
        "extra": (f"arXiv:{r['arxiv_id']} | 支柱：{PILLAR_NAME.get(r.get('pillar',''),'')} | "
                  f"命中的检索式：{','.join(r.get('hit_by', [])[:6])}"),
        "tags": [TAG, PILLAR_NAME.get(r.get("pillar", ""), "未分类"),
                 "R" + str(r["rank"]), r["published"][:7]],
    }
    if r.get("doi"):
        item["DOI"] = r["doi"]
    if venue and not venue.lower().startswith("arxiv"):
        item["proceedingsTitle" if itype == "conferencePaper" else "publicationTitle"] = venue
    return item


def save_batch(sid, items):
    try:
        r = requests.post(API + "/connector/saveItems",
                          json={"sessionID": sid, "items": items}, timeout=120)
        return r.status_code, r.text[:160]
    except Exception as e:
        return -1, str(e)[:160]


def attach(sid, key, r):
    fn = r.get("pdf_file")
    if not fn:
        return -1, "no local pdf"
    path = os.path.join(PDFDIR, fn)
    if not os.path.exists(path):
        return -1, "pdf missing"
    with open(path, "rb") as f:
        data = f.read()
    meta = {"sessionID": sid, "parentItemID": key,
            "title": "Full Text (PDF)",
            "url": f"https://arxiv.org/pdf/{r['arxiv_id']}"}
    headers = {"Content-Type": "application/pdf",
               "X-Metadata": json.dumps(meta, ensure_ascii=True)}
    try:
        resp = requests.post(API + f"/connector/saveAttachment?sessionID={sid}",
                             data=data, headers=headers, timeout=300)
        return resp.status_code, resp.text[:120]
    except Exception as e:
        return -1, str(e)[:120]


def main():
    d = json.load(open(os.path.join(REP, "02_selected100_with_pdf.json"), encoding="utf-8"))
    refs = d["refs"]
    before = counts()
    existing = existing_titles()
    todo = [r for r in refs if norm(r["title"]) not in existing]
    skipped = [r for r in refs if norm(r["title"]) in existing]
    print(f"[init] 库中 条目{before['items']} 附件{before['attachments']} 已打标{before['tagged']}", flush=True)
    print(f"[init] 待导入 {len(todo)}，跳过已存在 {len(skipped)}", flush=True)

    results = []
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        sid = "thesisref100-" + uuid.uuid4().hex[:12]
        items = [make_item(r) for r in batch]
        st, msg = save_batch(sid, items)
        print(f"[batch {i//BATCH+1}/{(len(todo)+BATCH-1)//BATCH}] saveItems {len(batch)} -> {st} {msg}", flush=True)
        if st not in (200, 201):
            for r in batch:
                results.append({"rank": r["rank"], "arxiv_id": r["arxiv_id"],
                                "title": r["title"], "item": "FAILED", "pdf": "SKIP",
                                "detail": f"saveItems {st} {msg}"})
            continue
        for r in batch:
            key = f"thesisref100-R{r['rank']}"
            a, am = attach(sid, key, r)
            results.append({"rank": r["rank"], "arxiv_id": r["arxiv_id"], "title": r["title"],
                            "item": "OK", "pdf": "OK" if a in (200, 201) else "FAILED",
                            "detail": f"saveAttachment {a} {am}"})
            print(f"   R{r['rank']} item=OK pdf->{a} {r['arxiv_id']}", flush=True)
        time.sleep(0.5)

    after = counts()
    okn = sum(1 for x in results if x["item"] == "OK")
    pdfok = sum(1 for x in results if x["pdf"] == "OK")

    res = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "tag": TAG,
           "before": before, "after": after, "todo": len(todo),
           "skipped_existing": [{"rank": r["rank"], "title": r["title"]} for r in skipped],
           "items_ok": okn, "pdf_ok": pdfok, "results": results}
    json.dump(res, open(os.path.join(REP, "03_zotero_import_result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    L = ["# Zotero 导入结果（100 篇，真实写入）", "",
         f"- 时间：{res['generated']}",
         f"- 标签：`{TAG}`",
         f"- 库中条目：{before['items']} → {after['items']}；PDF 附件：{before['attachments']} → {after['attachments']}",
         f"- 本次新增条目 **{okn}**，成功挂载 PDF **{pdfok}**",
         f"- 跳过已存在 {len(skipped)} 篇（幂等）", ""]
    if skipped:
        L += ["## 已在库、本次跳过", ""] + [f"- R{r['rank']} {r['title']}" for r in skipped] + [""]
    L += ["## 逐条结果", "", "| 编号 | arXiv | 条目 | PDF | 说明 |", "|---|---|---|---|---|"]
    for x in results:
        L.append(f"| R{x['rank']} | {x['arxiv_id']} | {x['item']} | {x['pdf']} | {x['detail'][:64]} |")
    open(os.path.join(REP, "03_Zotero导入结果.md"), "w", encoding="utf-8").write("\n".join(L))

    print("\n" + "=" * 62)
    print(f"完成：新增条目 {okn}，PDF {pdfok}；库 {before['items']}->{after['items']}，附件 {before['attachments']}->{after['attachments']}")
    print("=" * 62)


if __name__ == "__main__":
    main()
