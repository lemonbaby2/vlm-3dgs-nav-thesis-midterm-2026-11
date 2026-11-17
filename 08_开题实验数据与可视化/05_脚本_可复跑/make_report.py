# -*- coding: utf-8 -*-
"""
make_report.py — 把每日验证结果出成「三线表 Word + Markdown + 对比图」

三线表实现：整表无边框，仅保留 顶线(1.5pt) / 表头下线(0.75pt) / 底线(1.5pt)。
"""
import os
import json
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# 中文字体：优先 SimHei，退回雅黑/楷体
for _f in ("SimHei", "Microsoft YaHei", "KaiTi", "SimSun"):
    if any(_f == f.name for f in fm.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [_f]
        break
plt.rcParams["axes.unicode_minus"] = False

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(HERE, "reports")

MODES = ["naive", "dyn-mask", "no-dyn-data"]
MODE_CN = {"naive": "A 朴素全图", "dyn-mask": "B 动态掩码加权", "no-dyn-data": "C 仅初始化滤波"}
KEYS = [("psnr_all_mean", "PSNR 全图 (dB)"), ("psnr_static_mean", "PSNR 静态区 (dB)"),
        ("psnr_dyn_mean", "PSNR 动态区 (dB)"), ("ssim_mean", "SSIM"),
        ("ghost_residual_mean", "动态残影")]

BLUE = "#1E4FA8"
RED = "#C0392B"
GRAY = "#5A6472"


# ---------------- Word 工具 ----------------
def set_cell_border(cell, **kwargs):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = tcPr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcPr.append(borders)
    for edge in ("top", "bottom", "left", "right"):
        if edge in kwargs:
            spec = kwargs[edge]
            el = borders.find(qn(f"w:{edge}"))
            if el is None:
                el = OxmlElement(f"w:{edge}")
                borders.append(el)
            el.set(qn("w:val"), spec.get("val", "single"))
            el.set(qn("w:sz"), str(spec.get("sz", 4)))
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), spec.get("color", "000000"))


def _no_borders(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "none")
        el.set(qn("w:sz"), "0")
        borders.append(el)
    tblPr.append(borders)


def style_run(run, size=10.5, bold=False, cn="宋体", en="Times New Roman",
              color=None):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = en
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), en)
    rFonts.set(qn("w:hAnsi"), en)
    rFonts.set(qn("w:eastAsia"), cn)
    if color:
        run.font.color.rgb = RGBColor.from_string(color.replace("#", ""))


def three_line_table(doc, caption, header, rows, col_widths=None, note=None):
    """生成一张学术三线表"""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(3)
    style_run(p.add_run(caption), size=10.5, bold=True, cn="黑体", en="Times New Roman")

    t = doc.add_table(rows=1 + len(rows), cols=len(header))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _no_borders(t)

    # 表头
    for j, h in enumerate(header):
        cell = t.cell(0, j)
        cell.text = ""
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.space_before = Pt(2)
        para.paragraph_format.space_after = Pt(2)
        style_run(para.add_run(h), size=10, bold=True, cn="黑体")
        set_cell_border(cell, top={"sz": 12}, bottom={"sz": 6})

    # 数据行
    for i, row in enumerate(rows, start=1):
        for j, v in enumerate(row):
            cell = t.cell(i, j)
            cell.text = ""
            para = cell.paragraphs[0]
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER if j else WD_ALIGN_PARAGRAPH.LEFT
            para.paragraph_format.space_before = Pt(2)
            para.paragraph_format.space_after = Pt(2)
            style_run(para.add_run(str(v)), size=10)
            if i == len(rows):
                set_cell_border(cell, bottom={"sz": 12})

    if col_widths:
        for j, w in enumerate(col_widths):
            for r in t.rows:
                r.cells[j].width = Cm(w)

    if note:
        pn = doc.add_paragraph()
        pn.paragraph_format.space_before = Pt(3)
        pn.paragraph_format.space_after = Pt(10)
        style_run(pn.add_run(note), size=9, cn="宋体", color=GRAY)
    return t


def fmt(m, s, nd=3):
    if m is None:
        return "—"
    return f"{m:.{nd}f} ± {s:.{nd}f}"


# ---------------- 图 ----------------
def make_fig(today, stats, outdir):
    modes = [m for m in MODES if m in stats and "psnr_static_mean" in stats[m]]
    if not modes:
        return None
    x = np.arange(len(modes))
    stat_m = [stats[m]["psnr_static_mean"]["mean"] for m in modes]
    stat_s = [stats[m]["psnr_static_mean"]["std"] for m in modes]
    ghost_m = [stats[m]["ghost_residual_mean"]["mean"] for m in modes]
    ghost_s = [stats[m]["ghost_residual_mean"]["std"] for m in modes]

    fig, axes = plt.subplots(1, 2, figsize=(11.4, 3.8))
    for ax, vals, errs, title, color, better in (
        (axes[0], stat_m, stat_s, "静态区 PSNR（越高越好）", BLUE, "high"),
        (axes[1], ghost_m, ghost_s, "动态残影（越低越好）", RED, "low"),
    ):
        bars = ax.bar(x, vals, yerr=errs, capsize=5, color=color, alpha=0.86,
                      edgecolor="white", linewidth=1.2,
                      error_kw={"ecolor": "#333", "lw": 1.1})
        ax.set_xticks(x)
        ax.set_xticklabels([MODE_CN[m].replace(" ", "\n", 1) for m in modes], fontsize=9.5)
        ax.set_title(title, fontsize=12, fontweight="bold", color="#222")
        ax.grid(axis="y", alpha=0.25, linestyle="--")
        ax.set_axisbelow(True)
        for b, v in zip(bars, vals):
            nd = 3 if better == "high" else 4
            ax.annotate(f"{v:.{nd}f}", (b.get_x() + b.get_width() / 2, v),
                        xytext=(0, 8), textcoords="offset points",
                        ha="center", fontsize=10.5, fontweight="bold", color=color)
        ax.margins(y=0.18)
    fig.suptitle(f"三配置对照 · 跨种子均值±标准差 · {today}", fontsize=12.5,
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    path = os.path.join(outdir, f"fig_{today}.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------- 主入口 ----------------
def build(today, run_dir, seeds, stats, checks, warns, iters=2500, points=5000):
    os.makedirs(REPORTS, exist_ok=True)
    env = {
        "seeds": seeds, "iters": iters, "points": points,
        "run_dir": run_dir, "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    fig_path = make_fig(today, stats, REPORTS)
    passed = sum(1 for _, p, _ in checks if p)

    # ---------- Markdown ----------
    md = [f"# 自动验证日报 {today}", "",
          f"- 生成时间：{env['generated']}",
          f"- 随机种子：{seeds}　迭代：{iters}　初值点：{points}",
          f"- 判定通过：**{passed}/{len(checks)}**",
          f"- 原始数据：`{run_dir}`", ""]

    md += ["## 表 1 三配置跨种子汇总", "",
           "| 配置 | " + " | ".join(k[1] for k in KEYS) + " |",
           "|---|" + "---:|" * len(KEYS)]
    for m in MODES:
        if m not in stats:
            continue
        cells = []
        for k, _lbl in KEYS:
            v = stats[m].get(k)
            cells.append(fmt(v["mean"], v["std"], 4 if "ghost" in k else 3) if v else "—")
        md.append(f"| {MODE_CN[m]} | " + " | ".join(cells) + " |")
    md.append("")

    md += ["## 表 2 判定", "", "| 判据 | 结果 | 覆盖 |", "|---|---|---|"]
    for name, p, d in checks:
        md.append(f"| {name} | {'✅ 通过' if p else '❌ 未通过'} | {d} |")
    md.append("")

    if warns:
        md += ["## 漂移告警", ""] + [f"- ⚠ {w}" for w in warns] + [""]

    if fig_path:
        md += ["## 图", "", f"![三配置对照]({os.path.basename(fig_path)})", ""]

    md_path = os.path.join(REPORTS, f"{today}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    # ---------- Word ----------
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2.4)
    sec.top_margin = sec.bottom_margin = Cm(2.2)

    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_run(h.add_run("动态高斯建图机制验证 · 每日自动复跑报告"), size=16, bold=True, cn="黑体")

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_run(sub.add_run(f"{today}　│　生成 {env['generated']}"), size=9.5, cn="宋体", color=GRAY)

    info = doc.add_paragraph()
    info.paragraph_format.space_before = Pt(8)
    style_run(info.add_run(
        f"随机种子 {seeds}；迭代 {iters}；初值 {points} 点；场景为解析合成动态场景，"
        f"真值位姿/深度/掩码已知。判据：静态区 PSNR 越高越好，动态残影越低越好。"
        f"本轮判定通过 {passed}/{len(checks)}。"), size=10.5)

    # 表 1
    header = ["配置"] + [k[1] for k in KEYS]
    rows = []
    for m in MODES:
        if m not in stats:
            continue
        cells = [MODE_CN[m]]
        for k, _lbl in KEYS:
            v = stats[m].get(k)
            cells.append(fmt(v["mean"], v["std"], 4 if "ghost" in k else 3) if v else "—")
        rows.append(cells)
    three_line_table(doc, "表 1　三配置跨随机种子汇总（均值 ± 标准差）", header, rows,
                     col_widths=[3.4, 2.6, 2.9, 2.6, 2.5, 2.5],
                     note="注：B 组全图 PSNR 最低属设计使然——掩码加权损失主动放弃拟合动态像素，"
                          "评价应看静态区 PSNR 与动态残影两项分区指标。")

    # 表 2
    rows2 = [[n, "通过" if p else "未通过", d] for n, p, d in checks]
    three_line_table(doc, "表 2　核心结论稳定性判定", ["判据", "结果", "覆盖"], rows2,
                     col_widths=[10.5, 2.6, 2.6])

    # 表 3 逐种子
    import glob
    per_rows = []
    for m in MODES:
        v = stats.get(m, {}).get("psnr_static_mean")
        g = stats.get(m, {}).get("ghost_residual_mean")
        if not v:
            continue
        cells = [MODE_CN[m]]
        for i, s in enumerate(seeds):
            ps = v["vals"][i] if i < len(v["vals"]) else None
            gs = g["vals"][i] if g and i < len(g["vals"]) else None
            cells.append(f"{ps:.3f} / {gs:.4f}" if ps is not None and gs is not None else "—")
        per_rows.append(cells)
    if per_rows:
        three_line_table(doc, "表 3　逐种子明细（静态区 PSNR dB / 动态残影）",
                         ["配置"] + [f"seed{s}" for s in seeds], per_rows)

    if warns:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        style_run(p.add_run("漂移告警"), size=11, bold=True, cn="黑体")
        for w in warns:
            pw = doc.add_paragraph(style="List Bullet")
            style_run(pw.add_run(w), size=10.5)

    if fig_path:
        doc.add_picture(fig_path, width=Cm(15.5))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        style_run(cap.add_run("图 1　三配置在静态区 PSNR 与动态残影上的对比"), size=9.5, cn="宋体", color=GRAY)

    docx_path = os.path.join(REPORTS, f"{today}.docx")
    doc.save(docx_path)
    return md_path, docx_path
