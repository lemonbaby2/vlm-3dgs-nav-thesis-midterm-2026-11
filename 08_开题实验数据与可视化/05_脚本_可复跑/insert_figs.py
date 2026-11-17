# -*- coding: utf-8 -*-
"""把重绘的三张实验图贴进开题 PPT：
   P13 图2 换成三配置对照（原图是消融实验，与图注不符）
   P16 图3 换成逐种子重复验证（原图是全图 PSNR，与图注不符）
   P17 新增图4 三端 GPU 证据链，正文框收窄让位
"""
import os
import copy
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "开题报告_李梓鹏_2026-11_楷体精排22页.pptx")
DST = os.path.join(HERE, "..", "开题报告_李梓鹏_2026-11_楷体精排22页_含DGX实验图.pptx")
F2 = os.path.join(HERE, "figs", "fig2_three_config.png")
F3 = os.path.join(HERE, "figs", "fig3_seed_verify.png")
F4 = os.path.join(HERE, "figs", "fig4_three_platforms.png")

prs = Presentation(SRC)


def replace_picture(slide, new_path, keep_h=True):
    """删除该页唯一图片并在原位置插入新图"""
    for sh in list(slide.shapes):
        if str(sh.shape_type).startswith("PICTURE"):
            top, left, w, h = sh.top, sh.left, sh.width, sh.height
            sh._element.getparent().remove(sh._element)
            pic = slide.shapes.add_picture(new_path, left, top, width=w, height=h)
            return (Emu(top).inches, Emu(left).inches, Emu(w).inches, Emu(h).inches)
    return None


def set_text(shape, text, size=None):
    if shape is None or not shape.has_text_frame:
        return False
    tf = shape.text_frame
    p0 = tf.paragraphs[0]
    runs = p0.runs
    if not runs:
        p0.text = text
        return True
    runs[0].text = text
    for r in list(runs)[1:]:
        r._r.getparent().remove(r._r)
    for p in list(tf.paragraphs)[1:]:
        p._p.getparent().remove(p._p)
    if size:
        for p in tf.paragraphs:
            for r in p.runs:
                r.font.size = Pt(size)
    return True


# ---------- P13：换图 2 ----------
s13 = prs.slides[12]
print("P13 替换:", replace_picture(s13, F2))
for sh in s13.shapes:
    if sh.has_text_frame and "图 2" in sh.text_frame.text:
        set_text(sh, "图 2　三配置跨 3 个随机种子对照：B（掩码加权）静态区 +3.4 dB、残影降至 1/16.9，A/B/C 各 3 种子")
        print("  P13 图注已更新")

# ---------- P16：换图 3 ----------
s16 = prs.slides[15]
print("P16 替换:", replace_picture(s16, F3))
for sh in s16.shapes:
    if sh.has_text_frame and "图 3" in sh.text_frame.text:
        set_text(sh, "图 3　三配置 × 3 随机种子的重复验证：B 组三点几乎重合（34.35 / 34.53 / 34.40 dB），C 组波动最大")
        print("  P16 图注已更新")

# ---------- P17：正文收窄 + 插入图 4 ----------
s17 = prs.slides[16]
body = None
for sh in s17.shapes:
    if sh.has_text_frame:
        t = sh.text_frame.text
        if "环境核验" in t or "Anaconda base" in t:
            body = sh
            break
if body is not None:
    body.left = Inches(0.62)
    body.width = Inches(7.42)
    body.top = Inches(1.83)
    body.height = Inches(5.04)
    # 行数变多，行距略收紧
    for p in body.text_frame.paragraphs:
        p.line_spacing = 1.32
    print("P17 正文框收窄至 7.95 in")

PIC_L, PIC_T, PIC_W = 8.50, 1.84, 4.28
pic = s17.shapes.add_picture(F4, Inches(PIC_L), Inches(PIC_T), width=Inches(PIC_W))
print("P17 插图:", round(Emu(pic.height).inches, 2), "in 高")

cap = s17.shapes.add_textbox(Inches(PIC_L - 0.10), Inches(PIC_T) + pic.height + Inches(0.08),
                             Inches(PIC_W + 0.20), Inches(0.56))
tf = cap.text_frame
tf.word_wrap = True
p0 = tf.paragraphs[0]
r0 = p0.add_run()
r0.text = "图 4　三端 GPU 证据链：小场景（RTX 4060 / 5060 Ti 双卡）与放大场景（DGX GB10）共 19 次训练，A→B 静态区 +3.4 / +8.3 dB，残影降幅稳定 16×"
r0.font.size = Pt(10.5)
r0.font.name = "Times New Roman"
rPr = r0._r.get_or_add_rPr()
latin = rPr.find(qn("a:latin"))
for tag in ("a:ea", "a:cs"):
    e = rPr.find(qn(tag))
    if e is not None:
        rPr.remove(e)
ea = rPr.makeelement(qn("a:ea"), {"typeface": "楷体"})
cs = rPr.makeelement(qn("a:cs"), {"typeface": "Times New Roman"})
latin.addnext(ea)
ea.addnext(cs)
p0.alignment = 1  # 居中

prs.save(DST)
print("保存:", os.path.basename(DST))

# ---------- 核验 ----------
chk = Presentation(DST)
W = Emu(chk.slide_width).inches
ok = tot = 0
for s in chk.slides:
    if s.has_notes_slide and s.notes_slide.notes_text_frame and s.notes_slide.notes_text_frame.text.strip():
        ok += 1
        tot += len(s.notes_slide.notes_text_frame.text)
print(f"页数 {len(chk.slides)} | 备注 {ok} 页 | {tot} 字符")
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
        if b > 7.35:
            bad.append(f"P{i:02d} s{j:02d} 底越界 {b:.2f}")
print("越界项:", len(bad))
for x in bad[:8]:
    print("  ", x)
