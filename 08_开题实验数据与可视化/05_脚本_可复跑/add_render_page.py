# -*- coding: utf-8 -*-
"""在 P17 之后插入一页「渲染图像可视化」，复用 P17 的标题组与四点进度的样式。
输出：开题报告_..._含DGX实验图.pptx（在原含图版基础上增页）
"""
import os
from copy import deepcopy
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.oxml.ns import qn
from pptx.oxml import parse_xml

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "开题报告_李梓鹏_2026-11_楷体精排22页_含DGX实验图.pptx")
DST = os.path.join(HERE, "..", "开题报告_李梓鹏_2026-11_楷体精排23页_含DGX实验图.pptx")
RENDER = r"E:\研究生学习\dy3dgs-thesis-repro\synthetic\figures\fig_repro_render.png"

prs = Presentation(SRC)
src = prs.slides[16]                      # P17
new = prs.slides.add_slide(prs.slide_layouts[6])

# --- 复制标题组、二级标题、四点进度 ---
title_grp = src.shapes[0]
sub = src.shapes[1]
dots = [sh for sh in src.shapes if str(sh.shape_type) == "GROUP (6)" and Emu(sh.left).inches > 10][0]
for sh in (title_grp, sub, dots):
    new.shapes._spTree.append(deepcopy(sh._element))

# --- 改文字 ---
def rewrite(shape, text, size=None):
    tf = shape.text_frame
    p0 = tf.paragraphs[0]
    if p0.runs:
        p0.runs[0].text = text
        for r in list(p0.runs)[1:]:
            r._r.getparent().remove(r._r)
    for p in list(tf.paragraphs)[1:]:
        p._p.getparent().remove(p._p)
    if size:
        for p in tf.paragraphs:
            for r in p.runs:
                r.font.size = Pt(size)

for sh in new.shapes:
    if sh.has_text_frame and sh.text_frame.text.strip() == "前期基础与启动检查":
        rewrite(sh, "前期基础与启动检查")
    elif sh.has_text_frame and "完整启动检查实测" in sh.text_frame.text:
        rewrite(sh, "三、渲染图像可视化：残影为何消失", 19.0)

# --- 插图：合成场景 4 行 × 3 帧渲染对比 ---
PIC_L, PIC_T, PIC_H = 0.55, 1.72, 4.72
pic = new.shapes.add_picture(RENDER, Inches(PIC_L), Inches(PIC_T), height=Inches(PIC_H))
pic_w = Emu(pic.width).inches
print(f"图: {pic_w:.2f} x {PIC_H} in")

# --- 右侧读图要点 ---
BLK_L = PIC_L + pic_w + 0.34
BLK_W = 13.33 - BLK_L - 0.45
tb = new.shapes.add_textbox(Inches(BLK_L), Inches(1.80), Inches(BLK_W), Inches(4.55))
tf = tb.text_frame
tf.word_wrap = True

PARAS = [
    ("读图要点", True, 15.5, "#C00000", 0.10),
    ("第 0 帧　三配置都与 GT 接近，差异不明显——动态物体还没进入视野。", False, 14.0, "#1F3864", 0.13),
    ("第 6 帧　球进入画面。A 朴素与 C 仅初始化滤波在蓝箱右上留下橙色残影，B 掩码加权几乎无残留。", False, 14.0, "#1F3864", 0.13),
    ("第 11 帧　球覆盖大半视野。A 拖影最重，C 次之，B 依然干净。", False, 14.0, "#1F3864", 0.24),
    ("对应指标（3 种子均值）", True, 14.5, "#C00000", 0.09),
    ("动态残影　A 0.0831　C 0.0768　B 0.0049", False, 14.0, "#1F3864", 0.10),
    ("静态区 PSNR　A 30.99　C 31.29　B 34.42 dB", False, 14.0, "#1F3864", 0.24),
    ("结论　残影不是分辨率不足，而是动态像素被当作静态结构参与了优化。掩码加权在损失层切断这条路径，残影降一个数量级而静态区反而更清晰。", True, 14.0, "#1F3864", 0.0),
]
first = True
for text, bold, size, color, gap in PARAS:
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    first = False
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = __import__("pptx.dml.color", fromlist=["RGBColor"]).RGBColor.from_string(color[1:])
    if gap:
        p.space_after = Pt(gap * 72)
    # 字体：楷体 + Times New Roman
    r.font.name = "Times New Roman"
    rPr = r._r.get_or_add_rPr()
    latin = rPr.find(qn("a:latin"))
    for tag in ("a:ea", "a:cs"):
        e = rPr.find(qn(tag))
        if e is not None:
            rPr.remove(e)
    ea = rPr.makeelement(qn("a:ea"), {"typeface": "楷体"})
    cs = rPr.makeelement(qn("a:cs"), {"typeface": "Times New Roman"})
    latin.addnext(ea)
    ea.addnext(cs)

# --- 图注 ---
cap = new.shapes.add_textbox(Inches(0.55), Inches(6.44), Inches(pic_w), Inches(0.42))
p0 = cap.text_frame.paragraphs[0]
p0.alignment = 1
r0 = p0.add_run()
r0.text = "图 5　合成动态场景渲染对比（GT / C / B / A），第 0、6、11 帧"
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

# --- 备注（四段结构，与全篇一致）---
NOTES = """【本页作用】用一组能"看见"的渲染对比，把前两页的表格数字落到图像上。评委看完表格会问"你说的残影到底长什么样"，这页就是答案。

【口述稿｜约 70 秒】这一页是同一场景的四行渲染。第一行是真值，橙色球从左侧移到右侧。第二行 C 仅初始化滤波，第三行 B 掩码加权，第四行 A 朴素全图。
请看第 6 帧和第 11 帧：球经过的地方，A 留下了一团橙色斑，C 也留了、只是轻一些，B 的位置是干净的。原因不在分辨率——三组用的是同样的点数、同样的迭代数、同样的分辨率。差别只在损失函数：A 和 C 让动态像素参与了渲染损失的优化，网络就把"球"当成需要拟合的固定结构写进了地图；B 在损失层按掩码加权，等于告诉优化器"这些像素不要求你拟合"，路径被切断，残影自然消失。
而且注意一个反直觉现象：B 的全图 PSNR 是最低的，因为它主动放弃了动态像素；但静态区 PSNR 反而是最高的，34.42 dB 对 30.99 dB。这就是为什么我们的判据必须看静态区与残影，而不是全图 PSNR。

【数据出处】图为合成动态场景单次渲染样张（与表 1 同配置：12 帧 / 160×120 / 5000 点 / 2500 迭代）；右侧指标为 3 个随机种子均值，原始数据见 `06_实验数据与复现/raw/`。

【预判提问】
问：这图是不是挑好看的帧放的？
答：三列是第 0、6、11 帧，按时间轴等间隔取，不是挑选；第 0 帧三组几乎一样，正好反证差异来自动态物体而非随机性。
问：为什么 B 在球的位置是空白而不是把球也渲染出来？
答：本课题只重建静态背景，动态物体由掩码主动剔除；球的位置空白是正确的，渲染出球才是错误。
问：残影 0.0049 和 0.0831 是怎么算的？
答：在动态掩码区域逐像素统计渲染值与真值的残差均值，跨 12 帧平均，再跨 3 种子平均。"""

ns = new.notes_slide
NS_SP = (
    '<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
    '<p:nvSpPr><p:cNvPr id="{sid}" name="Notes {sid}"/>'
    '<p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
    '<p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr>'
    "<p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>"
)
tf_n = ns.notes_text_frame
if tf_n is None:
    spTree = ns.shapes._spTree
    used = [int(e.get("id")) for e in spTree.iter()
            if e.tag.endswith("}cNvPr") and (e.get("id") or "").isdigit()]
    sid = (max(used) + 1) if used else 2
    spTree.append(parse_xml(NS_SP.format(sid=sid)))
    tf_n = ns.notes_text_frame
tf_n.text = NOTES
print("备注已写入", len(NOTES), "字符")

# --- 移动到 P17 之后（索引 17）---
sldIdLst = prs.slides._sldIdLst
ids = list(sldIdLst)
sldIdLst.remove(ids[-1])
sldIdLst.insert(17, ids[-1])

prs.save(DST)
print("保存:", os.path.basename(DST))

chk = Presentation(DST)
ok = tot = 0
for s in chk.slides:
    if s.has_notes_slide and s.notes_slide.notes_text_frame and s.notes_slide.notes_text_frame.text.strip():
        ok += 1
        tot += len(s.notes_slide.notes_text_frame.text)
print(f"页数 {len(chk.slides)} | 备注 {ok} 页 | {tot} 字符")
for i, s in enumerate(chk.slides, 1):
    t = [sh.text_frame.text.strip()[:22] for sh in s.shapes
         if sh.has_text_frame and sh.text_frame.text.strip()]
    print(f"P{i:02d} {' / '.join(t[:3])[:60]}")
