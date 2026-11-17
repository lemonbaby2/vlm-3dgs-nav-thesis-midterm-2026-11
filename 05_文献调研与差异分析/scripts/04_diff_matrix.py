# -*- coding: utf-8 -*-
"""
阶段 4：从 100 篇的标题与摘要里抽结构化字段，生成可核查的差异对比表。

不做"我以为是"的判断：每个字段都由关键词命中决定，命中了哪些词记在
evidence 里，人可以直接翻回摘要核对。摘要抽不出来的字段写 None，不猜。
"""
import json
import os
import re

ROOT = r"E:\研究生学习\03_科研与论文\毕业论文参考文献_2026-11-16"
REP = os.path.join(ROOT, "report")
OUT = os.path.join(ROOT, "report", "04_diff_matrix")

PILLAR_NAME = {"G": "高斯建图底座", "V": "视觉语言模型", "D": "动态环境", "N": "机器人目标导航"}

# 每个维度：字段名 -> {取值: [关键词...]}
DIMS = {
    "表示": {
        "3DGS": ["3d gaussian", "gaussian splatting", "gaussian", "splatting", "splat"],
        "NeRF": ["nerf", "neural radiance", "radiance field"],
        "点云": ["point cloud", "lidar", "voxel"],
        "网格/TSDF": ["mesh", "tsdf", "signed distance", "surfel"],
        "BEV/2.5D": ["bird's-eye", "bev", "occupancy grid", "topological map"],
    },
    "语义来源": {
        "CLIP/开放词汇": ["clip", "open-vocabulary", "open vocabulary", "open-set"],
        "实例/全景分割": ["instance segmentation", "panoptic", "semantic segmentation", "mask"],
        "VLM/LLM蒸馏": ["vision-language model", "vlm", "large language model", "llm", "gpt", "foundation model"],
        "自监督/特征场": ["feature field", "self-supervised", "contrastive", "distillation"],
    },
    "动态处理": {
        "无（静态假设）": [],
        "动态掩码": ["dynamic mask", "mask out", "moving object", "instance mask"],
        "概率/不确定性": ["uncertainty", "probabilistic", "bayesian", "posterior"],
        "4D/形变场": ["4d", "deformable", "time-varying", "temporal gaussian", "velocity"],
        "在线更新/剔除": ["online update", "remove", "prune", "forget", "map update"],
    },
    "语言接口": {
        "文本查询/开放词汇查询": ["text query", "language query", "query", "prompt", "open-vocabulary"],
        "场景图/结构化": ["scene graph", "graph", "relation", "hierarchical"],
        "目标类别/语义标签": ["object category", "semantic label", "class"],
        "无语言接口": [],
    },
    "机器人闭环": {
        "真实机器人": ["real robot", "onboard", "deployed", "physical robot", "mobile robot"],
        "仿真平台": ["habitat", "gibson", "ai2-thor", "isaac", "simulation", "simulated"],
        "纯离线评测": [],
    },
}

DATASETS = ["Replica", "ScanNet", "ScanNet++", "HM3D", "Gibson", "AI2-THOR", "Habitat",
            "TUM", "KITTI", "nuScenes", "Waymo", "Matterport", "MP3D", "ARKitScenes",
            "RealEstate10K", "DL3DV", "OpenScene", "NYUv2", "SceneNet", "OVAD"]

METRICS = ["PSNR", "SSIM", "LPIPS", "ATE", "RPE", "SR", "SPL", "Success Rate",
           "mIoU", "mAP", "F1", "Recall", "Chamfer", "FPS"]


def hits(text, kws):
    t = text.lower()
    return [k for k in kws if k in t]


def pick(dim, text, default):
    """返回 (取值, 证据词)。取命中最多的一档；全不命中给 default。"""
    best, best_ev = default, []
    for val, kws in DIMS[dim].items():
        ev = hits(text, kws)
        if len(ev) > len(best_ev):
            best, best_ev = val, ev
    return best, best_ev


def main():
    d = json.load(open(os.path.join(REP, "02_selected100_with_pdf.json"), encoding="utf-8"))
    refs = d["refs"]
    os.makedirs(OUT, exist_ok=True)

    rows = []
    for r in refs:
        text = f"{r['title']} . {r.get('abstract','')}"
        rep, rep_ev = pick("表示", text, "未明确")
        sem, sem_ev = pick("语义来源", text, "未明确")
        dyn, dyn_ev = pick("动态处理", text, "无（静态假设）")
        lang, lang_ev = pick("语言接口", text, "未明确")
        rob, rob_ev = pick("机器人闭环", text, "纯离线评测")

        ds = [x for x in DATASETS if x.lower() in text.lower()]
        mt = [x for x in METRICS if re.search(rf"\b{re.escape(x)}\b", text, re.I)]

        rows.append({
            "rank": r["rank"],
            "month": r["published"][:7],
            "arxiv_id": r["arxiv_id"],
            "pillar": r["pillar"],
            "pillar_name": PILLAR_NAME[r["pillar"]],
            "title": r["title"],
            "表示": rep, "表示_ev": rep_ev,
            "语义来源": sem, "语义_ev": sem_ev,
            "动态处理": dyn, "动态_ev": dyn_ev,
            "语言接口": lang, "语言_ev": lang_ev,
            "机器人闭环": rob, "机器人_ev": rob_ev,
            "数据集": ds, "指标": mt,
            "pdf_file": r.get("pdf_file", ""),
        })

    json.dump(rows, open(os.path.join(REP, "04_rows.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # 写 Markdown 总表
    L = ["# 100 篇文献差异对比表（2025-11 ~ 2026-11）", "",
         "字段由关键词从标题+摘要命中自动判定，`证据` 列给出实际命中的词，可回摘要核对；",
         "摘要未提及的写「未明确」，不做臆测。", "",
         "## 总表", "",
         "| 编号 | 月份 | 支柱 | 标题 | 表示 | 语义来源 | 动态处理 | 语言接口 | 机器人在环 | 数据集 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for x in rows:
        t = x["title"].replace("|", "/")
        if len(t) > 62:
            t = t[:60] + "…"
        L.append(f"| R{x['rank']} | {x['month']} | {x['pillar_name']} | {t} | {x['表示']} | "
                 f"{x['语义来源']} | {x['动态处理']} | {x['语言接口']} | {x['机器人闭环']} | "
                 f"{','.join(x['数据集'][:3]) or '-'} |")
    open(os.path.join(OUT, "对比总表.md"), "w", encoding="utf-8").write("\n".join(L))

    # 按支柱分表 + 统计
    stat = {}
    for pil in ("G", "V", "D", "N"):
        sub = [x for x in rows if x["pillar"] == pil]
        stat[pil] = {
            "n": len(sub),
            "表示": {}, "语义来源": {}, "动态处理": {}, "语言接口": {}, "机器人闭环": {},
        }
        for dim in ("表示", "语义来源", "动态处理", "语言接口", "机器人闭环"):
            c = {}
            for x in sub:
                c[x[dim]] = c.get(x[dim], 0) + 1
            stat[pil][dim] = dict(sorted(c.items(), key=lambda kv: -kv[1]))

        SL = [f"## {PILLAR_NAME[pil]}（{len(sub)} 篇）", "",
              "| 编号 | 月份 | 标题 | 表示 | 语义来源 | 动态处理 | 语言接口 | 机器人在环 | 数据集 |",
              "|---|---|---|---|---|---|---|---|---|"]
        for x in sub:
            t = x["title"].replace("|", "/")
            if len(t) > 70:
                t = t[:68] + "…"
            SL.append(f"| R{x['rank']} | {x['month']} | {t} | {x['表示']} | {x['语义来源']} | "
                      f"{x['动态处理']} | {x['语言接口']} | {x['机器人闭环']} | {','.join(x['数据集'][:3]) or '-'} |")
        open(os.path.join(OUT, f"{pil}_{PILLAR_NAME[pil]}.md"), "w", encoding="utf-8").write("\n".join(SL))

    json.dump(stat, open(os.path.join(REP, "04_stats.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(f"总表 -> {os.path.join(OUT,'对比总表.md')}")
    print()
    for pil in ("G", "V", "D", "N"):
        s = stat[pil]
        print(f"=== {PILLAR_NAME[pil]} ({s['n']} 篇) ===")
        for dim in ("表示", "语义来源", "动态处理", "语言接口", "机器人闭环"):
            top = ", ".join(f"{k}:{v}" for k, v in list(s[dim].items())[:4])
            print(f"   {dim:6s} {top}")
        print()


if __name__ == "__main__":
    main()
