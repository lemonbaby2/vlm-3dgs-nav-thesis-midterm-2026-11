# -*- coding: utf-8 -*-
"""生成 PPT 专用的跨规模对比图（宽幅、大字号、无底部注释）。
输出：assets/fig_cross_scale.png  约 2320x660 px（PPT 中按 1160x330 放置）
"""
import os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 14

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = r"E:\研究生学习\开题中期_2026-11\中期汇报PPT\中期汇报PPT\assets"
S5060 = json.load(open(os.path.join(HERE, "code_tmp", "out_seeds", "summary.json"), encoding="utf8"))
SDGX = json.load(open(os.path.join(HERE, "dgx_large", "summary.json"), encoding="utf8"))

MODES = ["naive", "dyn-mask", "no-dyn-data"]
SHORT = {"naive": "A 朴素", "dyn-mask": "B 掩码加权", "no-dyn-data": "C 初始化滤波"}
BLUE, GREEN = "#1E4FA8", "#2E8B57"

fig, axes = plt.subplots(1, 2, figsize=(11.6, 3.6))
x = np.arange(3); w = 0.36
for ax, (key, title, logy) in zip(axes, [
        ("psnr_static_mean", "静态区 PSNR（dB）↑", False),
        ("ghost_residual_mean", "动态残影 ↓（对数轴）", True)]):
    a = [S5060["stats"][m][key]["mean"] for m in MODES]
    b = [SDGX["stats"][m][key]["mean"] for m in MODES]
    ea = [S5060["stats"][m][key]["std"] for m in MODES]
    eb = [SDGX["stats"][m][key]["std"] for m in MODES]
    ax.bar(x - w/2, a, w, yerr=ea, capsize=4, label="小场景 2500 iter（RTX 5060 Ti）",
           color=BLUE, alpha=0.92)
    ax.bar(x + w/2, b, w, yerr=eb, capsize=4, label="放大场景 250 iter（DGX GB10）",
           color=GREEN, alpha=0.92)
    ax.set_xticks(x); ax.set_xticklabels([SHORT[m] for m in MODES], fontsize=13.5)
    ax.set_title(title, fontsize=15.5, fontweight="bold", pad=8)
    ax.tick_params(axis="y", labelsize=12)
    if logy:
        ax.set_yscale("log")
        ax.set_ylim(0.0035, 0.32)
    else:
        ax.set_ylim(0, 44)
    ax.grid(axis="y", alpha=0.22)
    if logy:
        # 对数轴上数值标签易与刻度冲突：高柱放柱内（白字），矮柱放柱上方
        ymin = 0.0035
        for xi, v, c in ([(xi, v, BLUE) for xi, v in zip(x - w/2, a)]
                         + [(xi, v, GREEN) for xi, v in zip(x + w/2, b)]):
            if v < ymin * 3:
                ax.annotate(f"{v:.4f}", (xi, v), xytext=(0, 6), textcoords="offset points",
                            ha="center", va="bottom", fontsize=12, color=c, fontweight="bold")
            else:
                ax.annotate(f"{v:.4f}", (xi, v), xytext=(0, -7), textcoords="offset points",
                            ha="center", va="top", fontsize=12, color="white", fontweight="bold")
    else:
        for xi, v in zip(x - w/2, a):
            ax.annotate(f"{v:.2f}", (xi, v), xytext=(-2, 5), textcoords="offset points",
                        ha="right", va="bottom", fontsize=12.5, color=BLUE, fontweight="bold")
        for xi, v in zip(x + w/2, b):
            ax.annotate(f"{v:.2f}", (xi, v), xytext=(2, 5), textcoords="offset points",
                        ha="left", va="bottom", fontsize=12.5, color=GREEN, fontweight="bold")

h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="upper center", ncol=2, fontsize=12.5, frameon=False,
           bbox_to_anchor=(0.5, 1.045))
fig.tight_layout(pad=0.6, rect=(0, 0, 1, 0.92))
out = os.path.join(ASSETS, "fig_cross_scale.png")
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
plt.close(fig)
from PIL import Image
im = Image.open(out)
print("saved", out, im.size, "ratio %.3f" % (im.size[0] / im.size[1]))
