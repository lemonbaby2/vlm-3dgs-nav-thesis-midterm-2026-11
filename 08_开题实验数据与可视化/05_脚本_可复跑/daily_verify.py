# -*- coding: utf-8 -*-
"""
daily_verify.py — 每日闲时算力自动验证主控

流程：
 1) GPU 门控：检测本机每块卡的利用率与显存占用，只有"闲"的卡才参与本轮
 2) 任务分片：把 (seed × mode) 组合按可用卡轮转，各卡一个进程并行
 3) 汇总：读回全部 metrics.json，算跨种子均值±标准差，跑 C1–C5 判定
 4) 漂移检测：与 baseline.json 比对，静态区 PSNR 偏离 > 0.5 dB 或残影偏离 > 20% 记告警
 5) 产出：三线表 Word + Markdown + 对比图 + 当日日报

用法：
    python daily_verify.py                 # 正常跑（含 GPU 门控）
    python daily_verify.py --force         # 忽略门控强制跑
    python daily_verify.py --quick         # 冒烟：1 种子 3 配置 300 iter
    python daily_verify.py --report-only   # 只重出报表，不训练
"""
import os
import sys
import json
import time
import glob
import argparse
import subprocess
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
PY = r"D:\Anaconda\python.exe"
WORKER = os.path.join(HERE, "worker.py")
RUNS = os.path.join(HERE, "runs")
REPORTS = os.path.join(HERE, "reports")
STATE = os.path.join(HERE, "state.json")

MODES = ["naive", "dyn-mask", "no-dyn-data"]
MODE_CN = {"naive": "A 朴素全图", "dyn-mask": "B 动态掩码加权", "no-dyn-data": "C 仅初始化滤波"}
KEYS = [("psnr_all_mean", "PSNR 全图", "dB"), ("psnr_static_mean", "PSNR 静态区", "dB"),
        ("psnr_dyn_mean", "PSNR 动态区", "dB"), ("ssim_mean", "SSIM", ""),
        ("ghost_residual_mean", "动态残影", "")]

# 门控阈值
UTIL_MAX = 20          # %
MEM_FREE_MIN_RATIO = 0.55   # 空闲显存占比下限


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def gpu_state():
    """返回 [{index, mem_used, mem_total, util, idle}]"""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=30).stdout
    except Exception as e:
        print(f"[gate] nvidia-smi 调用失败: {e}")
        return []
    gpus = []
    for line in out.strip().splitlines():
        p = [x.strip() for x in line.split(",")]
        if len(p) < 4:
            continue
        idx, used, total, util = int(p[0]), int(p[1]), int(p[2]), int(p[3])
        free_ratio = 1 - used / max(total, 1)
        gpus.append({"index": idx, "mem_used": used, "mem_total": total,
                     "util": util, "free_ratio": free_ratio,
                     "idle": util <= UTIL_MAX and free_ratio >= MEM_FREE_MIN_RATIO})
    return gpus


def split_tasks(tasks, n):
    buckets = [[] for _ in range(n)]
    for i, t in enumerate(tasks):
        buckets[i % n].append(t)
    return buckets


def launch(tasks, gpus, run_dir, iters, points):
    """按 (seed,mode) 精确分片并并行拉起 worker，返回 [(proc, tag, logf)]"""
    procs = []
    for gpu, bucket in zip(gpus, split_tasks(tasks, len(gpus))):
        if not bucket:
            continue
        tag = f"gpu{gpu['index']}"
        spec = ",".join(f"{s}:{m}" for s, m in bucket)
        env = dict(os.environ)
        env["CUDA_VISIBLE_DEVICES"] = str(gpu["index"])
        env["PYTHONIOENCODING"] = "utf-8"
        cmd = [PY, WORKER, "--tasks", spec, "--iters", str(iters),
               "--points", str(points), "--outdir", run_dir, "--tag", tag]
        logf = open(os.path.join(run_dir, f"{tag}.log"), "w", encoding="utf-8")
        print(f"[launch] {tag} {len(bucket)} 组: {spec}", flush=True)
        p = subprocess.Popen(cmd, env=env, stdout=logf, stderr=subprocess.STDOUT, cwd=HERE)
        procs.append((p, tag, logf))
    return procs


def collect(run_dir):
    """读回 run_dir 下所有 seed*_*.json"""
    runs = {}
    for f in glob.glob(os.path.join(run_dir, "seed*_*.json")):
        base = os.path.basename(f)[:-5]
        try:
            seed_s, mode = base.split("_", 1)
            seed = int(seed_s.replace("seed", ""))
        except Exception:
            continue
        with open(f, encoding="utf-8") as fh:
            runs.setdefault(seed, {})[mode] = json.load(fh)["agg"]
    return runs


def summarize(runs):
    import statistics as st
    stats, checks = {}, []
    seeds = sorted(runs.keys())
    for mode in MODES:
        stats[mode] = {}
        for k, _, _ in KEYS:
            vals = [runs[s][mode][k] for s in seeds if mode in runs.get(s, {}) and k in runs[s][mode]]
            if not vals:
                continue
            stats[mode][k] = {
                "mean": st.mean(vals),
                "std": st.stdev(vals) if len(vals) > 1 else 0.0,
                "vals": vals,
            }

    def ok(mode, k):
        return stats.get(mode, {}).get(k)

    if all(ok(m, "psnr_static_mean") for m in MODES):
        c1 = sum(1 for s in seeds if runs[s]["dyn-mask"]["psnr_static_mean"] > runs[s]["naive"]["psnr_static_mean"])
        checks.append(("C1 静态区 PSNR：B(掩码加权) > A(朴素)", c1 == len(seeds), f"{c1}/{len(seeds)}"))
        c2 = sum(1 for s in seeds if runs[s]["dyn-mask"]["ghost_residual_mean"] < runs[s]["naive"]["ghost_residual_mean"]
                 and runs[s]["dyn-mask"]["ghost_residual_mean"] < runs[s]["no-dyn-data"]["ghost_residual_mean"])
        checks.append(("C2 动态残影：B 同时低于 A 与 C", c2 == len(seeds), f"{c2}/{len(seeds)}"))
        ratios = [runs[s]["naive"]["ghost_residual_mean"] / max(runs[s]["dyn-mask"]["ghost_residual_mean"], 1e-9) for s in seeds]
        checks.append((f"C3 残影下降 ≥10×（实测 {min(ratios):.1f}–{max(ratios):.1f}×）",
                       min(ratios) >= 10, f"{sum(1 for r in ratios if r >= 10)}/{len(seeds)}"))
        c4 = sum(1 for s in seeds if runs[s]["no-dyn-data"]["ghost_residual_mean"] > 5 * runs[s]["dyn-mask"]["ghost_residual_mean"])
        checks.append(("C4 仅初始化滤波(C)残影 > B 的 5 倍", c4 == len(seeds), f"{c4}/{len(seeds)}"))
        c5 = sum(1 for s in seeds
                 if sorted(MODES, key=lambda m: -runs[s][m]["psnr_static_mean"]) == ["dyn-mask", "no-dyn-data", "naive"])
        checks.append(("C5 静态区排序稳定为 B > C > A", c5 == len(seeds), f"{c5}/{len(seeds)}"))
    return stats, checks, seeds


def drift(stats, base):
    """与基线比对，返回告警字符串列表"""
    warns = []
    if not base:
        return warns
    for mode in MODES:
        for k, tol in (("psnr_static_mean", 0.5), ("ghost_residual_mean", 0.20)):
            cur = stats.get(mode, {}).get(k)
            old = base.get(mode, {}).get(k)
            if not cur or not old:
                continue
            m0 = old["mean"] if isinstance(old, dict) else old
            m1 = cur["mean"]
            if k == "ghost_residual_mean":
                if abs(m1 - m0) / max(abs(m0), 1e-9) > tol:
                    warns.append(f"{MODE_CN[mode]} 残影漂移 {m0:.5f} → {m1:.5f}")
            elif abs(m1 - m0) > tol:
                warns.append(f"{MODE_CN[mode]} 静态区 PSNR 漂移 {m0:.3f} → {m1:.3f} dB")
    return warns


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(s):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--iters", type=int, default=2500)
    ap.add_argument("--points", type=int, default=5000)
    ap.add_argument("--date", default=None, help="指定 run_dir 名（如 smoke_1117_2320）")
    args = ap.parse_args()

    os.makedirs(RUNS, exist_ok=True)
    os.makedirs(REPORTS, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    if args.quick and not args.report_only:
        today = "smoke_" + datetime.now().strftime("%m%d_%H%M")
    if args.date:
        today = args.date
    run_dir = os.path.join(RUNS, today)
    os.makedirs(run_dir, exist_ok=True)

    if args.quick:
        args.seeds, args.iters = "0", 300

    print(f"===== daily_verify {now()} =====")
    print(f"run_dir={run_dir} seeds={args.seeds} iters={args.iters} points={args.points}")

    if not args.report_only:
        gpus = gpu_state()
        for g in gpus:
            print(f"[gate] GPU{g['index']} util={g['util']}% mem={g['mem_used']}/{g['mem_total']}MiB "
                  f"free={g['free_ratio']*100:.0f}% -> {'闲' if g['idle'] else '忙'}")
        use = [g for g in gpus if g["idle"]]
        if not use and not args.force:
            msg = f"{now()} 两块卡均不空闲（util>{UTIL_MAX}% 或空闲显存<{int(MEM_FREE_MIN_RATIO*100)}%），本轮跳过。"
            print("[gate] " + msg)
            with open(os.path.join(REPORTS, f"{today}_skip.md"), "w", encoding="utf-8") as f:
                f.write(f"# {today} 跳过\n\n{msg}\n")
            return 0
        if not use:
            use = gpus
            print("[gate] --force：忽略门控，全部卡参与")
        print(f"[gate] 参与本轮 {len(use)} 块卡: {[g['index'] for g in use]}")

        seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
        tasks = [(s, m) for s in seeds for m in MODES]
        procs = launch(tasks, use, run_dir, args.iters, args.points)
        for p, tag, logf in procs:
            rc = p.wait()
            logf.close()
            print(f"[done] {tag} exit={rc}")

    runs = collect(run_dir)
    if not runs:
        print("[warn] 本轮没有任何 metrics，退出")
        return 1
    stats, checks, seeds = summarize(runs)

    state = load_state()
    base = state.get("baseline")
    warns = drift(stats, base)

    # ---- 输出报表 ----
    sys.path.insert(0, HERE)
    import make_report  # noqa: E402
    md_path, docx_path = make_report.build(today, run_dir, seeds, stats, checks, warns,
                                           iters=args.iters, points=args.points)
    print(f"[report] {md_path}")
    print(f"[word]   {docx_path}")

    # ---- 更新状态 ----
    state.setdefault("history", []).append({
        "date": today, "seeds": seeds, "iters": args.iters, "points": args.points,
        "checks_pass": sum(1 for _, p, _ in checks if p), "checks_total": len(checks),
        "warn": warns,
        "static_B": stats.get("dyn-mask", {}).get("psnr_static_mean", {}).get("mean"),
    })
    if not base and len(seeds) >= 2:
        state["baseline"] = stats
        print("[state] 已写入基线（首次多种子运行）")
    save_state(state)

    print("\n===== 判定 =====")
    for name, passed, detail in checks:
        print(f"  {'✅' if passed else '❌'} {name}  [{detail}]")
    if warns:
        print("\n===== 漂移告警 =====")
        for w in warns:
            print("  ⚠", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
