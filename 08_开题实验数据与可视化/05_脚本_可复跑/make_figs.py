# -*- coding: utf-8 -*-
"""开题 PPT 配图重绘：图2 三配置对照、图3 跨种子重复、图4 三端证据链。
数据源：auto_verify_2026-11/runs/2026-11-17（本机 9 组，2026-11-18 跑完）
       答辩验证_2026-11-17/dgx_large/summary.json（DGX GB10 放大版 9 组）
"""
import os
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.ticker import FuncFormatter
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figs")
os.makedirs(OUT, exist_ok=True)

RUNS = r"E:\研究生学习\auto_verify_2026-11\runs\2026-11-17"
DGX = r"E:\研究生学习\dy3dgs-thesis-repro\答辩验证_2026-11-17\dgx_large\summary.json"

# ---- 字体：优先楷体，与 PPT 正文一致 ----
for cand in ("SimHei", "Microsoft YaHei", "SimSun"):
    if any(f.name == cand for f in fm.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [cand]
        plt.rcParams["font.serif"] = [cand]
        FONT = cand
        break
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.family"] = "sans-serif"

C_A = "#1F3864"   # 朴素 深蓝
C_B = "#2E9B5B"   # 掩码 绿（最优）
C_C = "#C55A11"   # 初始化滤波 橙
GREY = "#595959"


def decimal_ticks(v, _=None):
    """对数轴刻度改成普通小数，避开楷体缺 U+2212 导致的 10⁻¹ 显示异常"""
    if v >= 0.1:
        return f"{v:.1f}" if v < 1 else f"{v:.0f}"
    if v >= 0.01:
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return f"{v:.3f}".rstrip("0").rstrip(".")

# ---- 读本机 9 组 ----
MODES = ["naive", "no-dyn-data", "dyn-mask"]
LBL = {"naive": "A 朴素全图", "dyn-mask": "B 动态掩码加权", "no-dyn-data": "C 仅初始化滤波"}
COL = {"naive": C_A, "dyn-mask": C_B, "no-dyn-data": C_C}
SHORT = {"naive": "A\n朴素全图", "dyn-mask": "B\n掩码加权", "no-dyn-data": "C\n初始化滤波"}

data = {m: {"static": [], "ghost": [], "all": []} for m in MODES}
for seed in (0, 1, 2):
    for m in MODES:
        p = os.path.join(RUNS, f"seed{seed}_{m}.json")
        agg = json.load(open(p, encoding="utf-8"))["agg"]
        data[m]["static"].append(agg["psnr_static_mean"])
        data[m]["ghost"].append(agg["ghost_residual_mean"])
        data[m]["all"].append(agg["psnr_all_mean"])

order = ["naive", "dyn-mask", "no-dyn-data"]   # A / B / C


def bar_labels(ax, xs, vals, fmt, colors, logy=False, dy_frac=0.03):
    lo, hi = ax.get_ylim()
    for x, v, c in zip(xs, vals, colors):
        if logy:
            ax.annotate(fmt.format(v), (x, v), xytext=(0, 5), textcoords="offset points",
                        ha="center", va="bottom", fontsize=11.5, color=c, fontweight="bold")
        else:
            ax.annotate(fmt.format(v), (x, v), xytext=(0, 4), textcoords="offset points",
                        ha="center", va="bottom", fontsize=11.5, color=c, fontweight="bold")


# ================= 图 2：三配置 均值±标准差（P13） =================
fig, axes = plt.subplots(1, 2, figsize=(5.95, 2.89), dpi=210)
fig.subplots_adjust(left=0.105, right=0.975, top=0.83, bottom=0.20, wspace=0.34)

ax = axes[0]
xs = np.arange(3)
means = [np.mean(data[m]["static"]) for m in order]
stds = [np.std(data[m]["static"], ddof=1) for m in order]
cols = [COL[m] for m in order]
ax.bar(xs, means, width=0.58, color=cols, yerr=stds, capsize=5,
       error_kw=dict(lw=1.3, ecolor="#404040"))
ax.set_xticks(xs); ax.set_xticklabels([SHORT[m] for m in order], fontsize=11)
ax.set_ylim(28, 38.2)
ax.set_ylabel("静态区 PSNR (dB)　越高越好", fontsize=11)
ax.set_title("静态区渲染质量", fontsize=12.5, fontweight="bold", color="#1F3864", pad=8)
ax.grid(axis="y", ls=":", color="#BFBFBF", lw=0.8)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for i, (m, sd) in enumerate(zip(means, stds)):
    if i == 0:
        # A 柱：误差棒上端会顶到标注，改写在柱体内（白字）
        ax.text(i, 29.0, f"{m:.2f}\n±{sd:.2f}", ha="center", va="bottom",
                fontsize=11, color="white", fontweight="bold", linespacing=1.35)
    else:
        ax.annotate(f"{m:.2f}\n±{sd:.2f}", (i, m + sd), xytext=(0, 6), textcoords="offset points",
                    ha="center", va="bottom", fontsize=11.5, color=cols[i], fontweight="bold")
ax.annotate("", xy=(0.66, 33.9), xytext=(0.32, 33.9),
            arrowprops=dict(arrowstyle="->", color=C_B, lw=1.6))
ax.text(0.49, 34.02, "+3.4 dB", ha="center", va="bottom", fontsize=11.5,
        color=C_B, fontweight="bold")

ax = axes[1]
gm = [np.mean(data[m]["ghost"]) for m in order]
gs = [np.std(data[m]["ghost"], ddof=1) for m in order]
ax.bar(xs, gm, width=0.58, color=cols, yerr=gs, capsize=5,
       error_kw=dict(lw=1.3, ecolor="#404040"))
ax.set_yscale("log")
ax.set_ylim(0.0035, 0.30)
ax.set_yticks([0.005, 0.01, 0.02, 0.05, 0.1, 0.2])
ax.yaxis.set_major_formatter(FuncFormatter(decimal_ticks))
ax.yaxis.set_minor_formatter(FuncFormatter(lambda v, _: ""))
ax.set_xticks(xs); ax.set_xticklabels([SHORT[m] for m in order], fontsize=11)
ax.set_ylabel("动态残影 (对数轴)　越低越好", fontsize=11)
ax.set_title("动态残影残留", fontsize=12.5, fontweight="bold", color="#1F3864", pad=8)
ax.grid(axis="y", ls=":", color="#BFBFBF", lw=0.8, which="both")
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
for i, m in enumerate(gm):
    ax.annotate(f"{m:.4f}", (i, m), xytext=(0, 7), textcoords="offset points",
                ha="center", va="bottom", fontsize=11.5, color=cols[i], fontweight="bold")
ax.annotate("", xy=(0.62, 0.0235), xytext=(0.40, 0.0235),
            arrowprops=dict(arrowstyle="->", color=C_B, lw=1.6))
ax.text(0.51, 0.0275, "16.9×", ha="center", va="bottom", fontsize=12,
        color=C_B, fontweight="bold")
fig.text(0.5, 0.955, "3 个随机种子 · 各 2500 迭代 · RTX 4060 8G / 5060 Ti 16G 双卡",
         ha="center", fontsize=10.5, color=GREY)
fig.savefig(os.path.join(OUT, "fig2_three_config.png"), dpi=210, facecolor="white")
plt.close(fig)
print("图2 完成")

# ================= 图 3：逐种子重复验证（P16） =================
fig, axes = plt.subplots(1, 2, figsize=(5.95, 3.67), dpi=210)
fig.subplots_adjust(left=0.105, right=0.975, top=0.86, bottom=0.16, wspace=0.34)

ax = axes[0]
xp = [0, 1, 2]
for m in order:
    ax.plot(xp, data[m]["static"], "o-", color=COL[m], lw=2.0, ms=7,
            mec="white", mew=1.2, label=LBL[m], zorder=3)
ax.set_xticks(xp); ax.set_xticklabels(["种子 0", "种子 1", "种子 2"], fontsize=11)
ax.set_xlim(-0.35, 2.35)
ax.set_ylim(28.5, 35.8)
ax.set_ylabel("静态区 PSNR (dB)", fontsize=11)
ax.set_title("逐种子静态区 PSNR", fontsize=12.5, fontweight="bold", color="#1F3864", pad=8)
ax.grid(ls=":", color="#BFBFBF", lw=0.8)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.legend(fontsize=8.8, loc="lower left", frameon=False, handlelength=1.4, labelspacing=0.35, borderaxespad=0.2)

ax = axes[1]
for m in order:
    ax.plot(xp, data[m]["ghost"], "o-", color=COL[m], lw=2.0, ms=7,
            mec="white", mew=1.2, zorder=3)
ax.set_yscale("log")
ax.set_xticks(xp); ax.set_xticklabels(["种子 0", "种子 1", "种子 2"], fontsize=11)
ax.set_xlim(-0.35, 2.35)
ax.set_ylim(0.003, 0.16)
ax.set_yticks([0.005, 0.01, 0.02, 0.05, 0.1])
ax.yaxis.set_major_formatter(FuncFormatter(decimal_ticks))
ax.yaxis.set_minor_formatter(FuncFormatter(lambda v, _: ""))
ax.set_ylabel("动态残影 (对数轴)", fontsize=11)
ax.set_title("逐种子动态残影", fontsize=12.5, fontweight="bold", color="#1F3864", pad=8)
ax.grid(ls=":", color="#BFBFBF", lw=0.8, which="both")
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.annotate("B 三点几乎重合\n0.0048 / 0.0050 / 0.0048", xy=(0.5, 0.0052), xytext=(0.5, 0.0125),
            ha="center", fontsize=9.5, color=C_B, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=C_B, lw=1.3))
fig.text(0.5, 0.955, "9 次独立训练（3 配置 × 3 种子）· 总耗时 3980.2 s",
         ha="center", fontsize=10.5, color=GREY)
fig.savefig(os.path.join(OUT, "fig3_seed_verify.png"), dpi=210, facecolor="white")
plt.close(fig)
print("图3 完成")

# ================= 图 4：三端证据链（P17，竖版） =================
d = json.load(open(DGX, encoding="utf-8"))["stats"]
dgx_static = {m: d[m]["psnr_static_mean"]["mean"] for m in MODES}
dgx_ghost = {m: d[m]["ghost_residual_mean"]["mean"] for m in MODES}

fig, axes = plt.subplots(2, 1, figsize=(4.30, 4.35), dpi=210)
fig.subplots_adjust(left=0.20, right=0.975, top=0.90, bottom=0.13, hspace=0.52)

ax = axes[0]
groups = ["小场景\n12f·160×120·5000pt", "放大场景\n24f·320×240·8000pt"]
w = 0.26
for k, m in enumerate(order):
    vals = [np.mean(data[m]["static"]), dgx_static[m]]
    errs = [np.std(data[m]["static"], ddof=1), d[m]["psnr_static_mean"]["std"]]
    ax.bar(np.arange(2) + (k - 1) * w, vals, width=w * 0.92, color=COL[m],
           yerr=errs, capsize=3, error_kw=dict(lw=1.0, ecolor="#404040"),
           label=LBL[m])
    # 柱内底部标 A/B/C，省掉图例，避免遮挡
    for gx in (0, 1):
        ax.text(gx + (k - 1) * w, 19.6, "ABC"[k], ha="center", va="bottom",
                fontsize=10.5, color="white", fontweight="bold")
ax.set_xticks([0, 1]); ax.set_xticklabels(groups, fontsize=9.5)
ax.set_ylim(18, 41)
ax.set_ylabel("静态区 PSNR (dB)", fontsize=10.5)
ax.set_title("A→B 收益随场景放大而变大", fontsize=11.5, fontweight="bold", color="#1F3864", pad=6)
ax.grid(axis="y", ls=":", color="#BFBFBF", lw=0.7)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.annotate("+3.4 dB", xy=(0.0, 36.2), ha="center", fontsize=10.5, color=C_B, fontweight="bold")
ax.annotate("+8.3 dB", xy=(1.0, 33.4), ha="center", fontsize=10.5, color=C_B, fontweight="bold")
ax.text(0.5, 39.4, "A 朴素　B 掩码加权　C 初始化滤波", ha="center", fontsize=9.2, color=GREY)

ax = axes[1]
ratio = [np.mean(data["naive"]["ghost"]) / np.mean(data["dyn-mask"]["ghost"]),
         dgx_ghost["naive"] / dgx_ghost["dyn-mask"]]
ax.bar([0, 1], ratio, width=0.42, color=["#4472C4", "#7B3FA0"])
for x, v in zip([0, 1], ratio):
    ax.annotate(f"{v:.1f}×", (x, v), xytext=(0, 4), textcoords="offset points",
                ha="center", va="bottom", fontsize=12, fontweight="bold",
                color="#4472C4" if x == 0 else "#7B3FA0")
ax.set_xticks([0, 1]); ax.set_xticklabels(["小场景\nRTX 双卡", "放大场景\nDGX GB10"], fontsize=9.5)
ax.set_ylim(0, 22)
ax.set_ylabel("残影下降倍数", fontsize=10.5)
ax.set_title("残影降幅稳定在 16× 量级", fontsize=11.5, fontweight="bold", color="#1F3864", pad=6)
ax.grid(axis="y", ls=":", color="#BFBFBF", lw=0.7)
ax.set_axisbelow(True)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
fig.text(0.5, 0.965, "19 次训练：RTX 4060 8G + RTX 5060 Ti 16G + DGX GB10",
         ha="center", fontsize=9.8, color=GREY)
fig.savefig(os.path.join(OUT, "fig4_three_platforms.png"), dpi=210, facecolor="white")
plt.close(fig)
print("图4 完成")

for f in ("fig2_three_config.png", "fig3_seed_verify.png", "fig4_three_platforms.png"):
    p = os.path.join(OUT, f)
    print(f, os.path.getsize(p), "bytes")
