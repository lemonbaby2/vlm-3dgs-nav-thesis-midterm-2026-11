# 表3 官方 NeRF Synthetic Lego 独立复现（本轮实测，非引用旧数字）

> 数据：`nerf_synthetic/lego_white_rgb`，100 训练视角 / 100 评测视角。
> 环境：官方 `graphdeco-inria/gaussian-splatting` + `gaussian_3dgs`（torch 2.1.2），RTX 4060 8G，7000 iter，训练 2 分 53 秒 + 渲染 19 秒。
> 迭代数仅为原论文 30k 的 1/4，故 PSNR 低于 30k 主结果（37.4118 dB）符合预期；本表用途是证明**本机可独立跑通官方大数据管线**，不作为论文主结果。

| 划分 | PSNR (dB) | SSIM | LPIPS |
|---|---:|---:|---:|
| 全部 100 视角 | 34.8542 | 0.97961 | 0.02240 |

> ⚠️ 避坑：`outputs/3dgs/lego_30000/results.json` 是失败残留（PSNR 2.38 / SSIM 0.27），不可引用；正确的 30k 指标源为 `metrics/experiment_summary.json`（41/41 项验收 PASS）。
