# -*- coding: utf-8 -*-
"""
worker.py — 单卡训练 worker，供 daily_verify.py 以进程方式并行拉起。

用法（由 daily_verify.py 调用，也可手工跑）：
    CUDA_VISIBLE_DEVICES=0 python worker.py --seeds 0 --outdir runs/2026-11-18 --tag gpu0

输出：<outdir>/seed{s}_{mode}.json  （每个组合一个文件，支持断点续跑）
"""
import os
import sys
import json
import time
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = r"E:\研究生学习\dy3dgs-thesis-repro\synthetic\code"
sys.path.insert(0, CODE)

import torch  # noqa: E402
import train_3dgs as T  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--modes", default="naive,dyn-mask,no-dyn-data")
    ap.add_argument("--iters", type=int, default=2500)
    ap.add_argument("--points", type=int, default=5000)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--tag", default="")
    ap.add_argument("--tasks", default="", help="精确任务列表，如 0:naive,1:dyn-mask（优先于 seeds/modes）")
    args = ap.parse_args()

    if args.tasks.strip():
        tasks = []
        for t in args.tasks.split(","):
            t = t.strip()
            if not t:
                continue
            sd, md = t.split(":")
            tasks.append((int(sd), md))
    else:
        tasks = [(s, m) for s in [int(x) for x in args.seeds.split(",") if x.strip()]
                 for m in [y.strip() for y in args.modes.split(",") if y.strip()]]
    seeds = sorted({s for s, _ in tasks})
    modes = sorted({m for _, m in tasks})
    os.makedirs(args.outdir, exist_ok=True)

    dev_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
    print(f"[{args.tag}] device={dev_name} seeds={seeds} modes={modes} "
          f"iters={args.iters} points={args.points}", flush=True)

    meta, K, frames = T.load_scene()
    print(f"[{args.tag}] scene {meta['frames']}f {meta['W']}x{meta['H']}", flush=True)

    for seed, mode in tasks:
        if True:
            out = os.path.join(args.outdir, f"seed{seed}_{mode}.json")
            if os.path.exists(out):
                print(f"[{args.tag}] skip {seed}/{mode} (已存在)", flush=True)
                continue
            t0 = time.time()
            try:
                model, hist, use_frames, tt = T.train(
                    mode, frames, K, meta, iters=args.iters,
                    max_points=args.points, seed=seed)
                rows, agg = T.evaluate(model, frames, K, meta)
                agg["train_time_s"] = round(tt, 2)
                agg["n_gauss"] = int(model.means.shape[0])
                agg["mode"] = mode
                agg["seed"] = seed
                agg["device"] = dev_name
                agg["iters"] = args.iters
                agg["init_points"] = args.points
                with open(out, "w", encoding="utf-8") as f:
                    json.dump({"agg": agg, "per_frame": rows}, f,
                              ensure_ascii=False, indent=2)
                print(f"[{args.tag}] OK {seed}/{mode} wall={time.time()-t0:.0f}s "
                      f"static={agg['psnr_static_mean']:.3f} "
                      f"ghost={agg['ghost_residual_mean']:.5f}", flush=True)
            except Exception as e:  # 单组失败不拖垮整批
                print(f"[{args.tag}] FAIL {seed}/{mode}: {type(e).__name__}: {e}", flush=True)
            finally:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
