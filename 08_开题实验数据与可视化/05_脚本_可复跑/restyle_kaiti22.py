# -*- coding: utf-8 -*-
"""开题报告 22 页精排：全字体改为 中文楷体 / 西文 Times New Roman，标题上移，版式微调。
源文件不动，输出 _楷体精排22页。
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "开题报告_李梓鹏_2026-11.pptx")
DST = os.path.join(HERE, "..", "开题报告_李梓鹏_2026-11_楷体精排22页.pptx")

LATIN = "Times New Roman"
EA = "楷体"

prs = Presentation(SRC)
stat = {"run": 0, "impact_bold": 0, "组标题上移": 0, "二级标题上移": 0,
        "正文框上移": 0, "圆点上移": 0}


def fix_run(r):
    """统一 run 字体：latin=TNR / ea=楷体 / cs=TNR"""
    rPr = r._r.find(qn("a:rPr"))
    old_latin = None
    if rPr is not None:
        la = rPr.find(qn("a:latin"))
        if la is not None:
            old_latin = la.get("typeface")

    r.font.name = LATIN                      # 建/改 a:latin
    rPr = r._r.get_or_add_rPr()
    latin = rPr.find(qn("a:latin"))
    for tag in ("a:ea", "a:cs"):
        e = rPr.find(qn(tag))
        if e is not None:
            rPr.remove(e)
    ea = rPr.makeelement(qn("a:ea"), {"typeface": EA})
    cs = rPr.makeelement(qn("a:cs"), {"typeface": LATIN})
    latin.addnext(ea)
    ea.addnext(cs)

    # Impact 装饰数字（章节号 01-05）改 TNR 会变细，加粗补偿
    if old_latin == "Impact":
        r.font.bold = True
        stat["impact_bold"] += 1
    stat["run"] += 1


def walk(shapes):
    for sh in shapes:
        if sh.shape_type == 6:            # GROUP
            walk(sh.shapes)
            continue
        if sh.has_table:
            for row in sh.table.rows:
                for cell in row.cells:
                    walk(cell.shapes)
                    for p in cell.text_frame.paragraphs:
                        for r in p.runs:
                            fix_run(r)
            continue
        if not sh.has_text_frame:
            continue
        for p in sh.text_frame.paragraphs:
            for r in p.runs:
                fix_run(r)


# ---------- 1. 字体 ----------
for s in prs.slides:
    walk(s.shapes)

# ---------- 2. 版式 ----------
SHIFT = 0.09
for s in prs.slides:
    for sh in s.shapes:
        try:
            top = Emu(sh.top).inches
            L = Emu(sh.left).inches
            h = Emu(sh.height).inches
            w = Emu(sh.width).inches
        except Exception:
            continue

        # 2a. 左上「编号 + 一级标题」组：top 0.39 -> 0.30
        if sh.shape_type == 6 and top < 1.0 and L < 1.0 and w > 2.0:
            sh.top = Inches(top - SHIFT)
            stat["组标题上移"] += 1
            continue

        # 2b. 右上四点进度指示：top 0.49 -> 0.40
        if sh.shape_type == 6 and top < 1.0 and L > 10.0:
            sh.top = Inches(top - SHIFT)
            stat["圆点上移"] += 1
            continue

        # 2c. 二级标题（19pt，top≈1.26）-> 1.17
        if 1.18 < top < 1.35 and 0.4 < L < 0.8 and sh.has_text_frame and sh.text_frame.text.strip():
            sh.top = Inches(top - SHIFT)
            stat["二级标题上移"] += 1
            continue

        # 2d. 正文框（top≈1.92）：上移并等量增高，底部保持不变
        if 1.85 < top < 2.05 and w > 8.0 and sh.has_text_frame:
            sh.top = Inches(top - SHIFT)
            sh.height = Inches(h + SHIFT)
            stat["正文框上移"] += 1

# ---------- 3. 正文行距自适应：内容少的页放宽行距，把下半页空白收拢 ----------
import math
import re

CPL = 55          # 15pt 楷体在 11.6in 宽框内每行约 55 个中文字
stat["行距调整"] = 0
for i, s in enumerate(prs.slides, 1):
    for sh in s.shapes:
        if not sh.has_text_frame:
            continue
        try:
            top = Emu(sh.top).inches
            w = Emu(sh.width).inches
            h = Emu(sh.height).inches
        except Exception:
            continue
        # 只处理整幅正文框，跳过扉页大标题与英文参考文献页
        if not (w > 11 and h > 4.4 and top < 2.2):
            continue
        tf = sh.text_frame
        full = "\n".join(p.text for p in tf.paragraphs)
        cjk = len(re.findall(r"[\u4e00-\u9fa5]", full))
        if cjk < 100:                      # 英文为主，行宽不可估，跳过
            continue
        lines = 0
        for p in tf.paragraphs:
            t = p.text
            lines += max(1, math.ceil(len(t) / CPL)) if t.strip() else 1
        old_ls = tf.paragraphs[0].line_spacing or 1.45
        target = h * 0.86
        new_ls = max(1.45, min(1.72, target * 72.0 / (lines * 15.0)))
        if new_ls <= old_ls + 0.02:
            continue
        for p in tf.paragraphs:
            p.line_spacing = round(new_ls, 2)
        stat["行距调整"] += 1
        print(f"  P{i:02d} 行数={lines:2d} 占高={lines*15*old_ls/72:.2f}→{lines*15*new_ls/72:.2f}in "
              f"ls {old_ls}→{new_ls:.2f} (框高 {h:.2f})")

prs.save(DST)
print("保存:", os.path.basename(DST))
print(stat)

# ---------- 3. 核验 ----------
chk = Presentation(DST)
W = Emu(chk.slide_width).inches
fonts = {}
ok = tot = 0
for s in chk.slides:
    if s.has_notes_slide and s.notes_slide.notes_text_frame and s.notes_slide.notes_text_frame.text.strip():
        ok += 1
        tot += len(s.notes_slide.notes_text_frame.text)


def scan(shapes):
    for sh in shapes:
        if sh.shape_type == 6:
            scan(sh.shapes)
            continue
        if not sh.has_text_frame:
            continue
        for p in sh.text_frame.paragraphs:
            for r in p.runs:
                rPr = r._r.find(qn("a:rPr"))
                if rPr is None:
                    continue
                for tag in ("a:latin", "a:ea", "a:cs"):
                    e = rPr.find(qn(tag))
                    if e is not None:
                        k = (tag, e.get("typeface"))
                        fonts[k] = fonts.get(k, 0) + 1


for s in chk.slides:
    scan(s.shapes)

print(f"页数 {len(chk.slides)} | 备注 {ok} 页 | 备注字符 {tot}")
print("字体统计:")
for k, v in sorted(fonts.items(), key=lambda x: -x[1]):
    print("  ", k, v)

bad = []
for i, s in enumerate(chk.slides, 1):
    for j, sh in enumerate(s.shapes):
        try:
            L = Emu(sh.left).inches
            w = Emu(sh.width).inches
            b = Emu(sh.top + sh.height).inches
        except Exception:
            continue
        if L + w > W + 0.05 and w < 13.0:
            bad.append(f"P{i:02d} s{j:02d} 右越界 {L+w:.2f}")
        if b > 7.30:
            bad.append(f"P{i:02d} s{j:02d} 底越界 {b:.2f}")
print("越界项:", len(bad))
for x in bad[:10]:
    print("  ", x)
