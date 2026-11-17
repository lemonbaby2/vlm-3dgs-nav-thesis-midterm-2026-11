# DESIGN.md — 硕士学位论文中期检查汇报

## 一、需求对齐

| 维度 | 结论 |
|---|---|
| 主题 | 《动态环境下视觉语言模型辅助三维高斯语义建图与机器人目标导航》中期检查汇报 |
| 目标 | 向中期检查小组说明：选题依据、已完成工作、实测结果、存在不足与下阶段计划，争取"通过"结论 |
| 受众 | 导师陈静教授 + 学院中期检查小组（同行教授，熟悉 SLAM / 三维视觉） |
| 场合 | 广东工业大学硕士研究生中期检查答辩会，口头汇报 15–20 分钟 |
| 调性 | 可信、证据驱动、克制；不修饰、不宣传 |
| 页数 | 26 页（封面 / 目录 / 4 章节扉页 / 18 内容页 / 参考文献 / 结束页） |
| 素材来源 | 中期检查表、开题报告表、文献综述、Dy3DGS-SLAM 论文（arXiv:2506.05965）、本机 3DGS 动态场景复刻实验（2026-11-11 实跑） |

## 二、全局视觉约定

### ① 画布与安全区
- 画布 1280×720
- 顶条：全幅 `0,0 → 1280,72`，深蓝实色，高 72px（替代上 padding，承载页面主标题）
- 内容区：`x 60–1220`，`y 96–660`，可用 1160×564
- 页脚：`y = 670`，左论文题目缩写 / 右页码 `NN / 26`，左右受 60px 安全区约束

### ② 配色方案

| 槽位 | Hex | 用途 |
|---|---|---|
| 主色 | `#1E4FA8` | 顶条、章节编号块、表格表头、关键强调 |
| 辅色 | `#3D7BD9` | 图表第二序列、次级强调、细线 |
| 浅辅底 | `#E8EFF8` | 结论条底色、信息横幅底、表头底 |
| 强调红 | `#D9534F` | 关键缺陷 / 风险 / 与基线的差距，全篇 ≤3 处 |
| 数据黄 | `#FFC107` | 仅图表"本研究"序列，≤3% |
| 正文色 | `#1A2230` / `#4A5568` / `#8B97A8` | 主 / 副 / 辅助 |
| 底色 | `#FFFFFF` | 全篇白底 |
| 分隔线 | `#D6DCE5` | 1px 细线、表格边框 |

**纪律**：蓝族合计 20–40%；白底 ≥60%；红 + 黄 ≤5%；金色 = 0；禁用紫 / 粉 / 彩虹渐变 / 纯黑大底。

### ③ 字体系统

- 中文：`Microsoft YaHei`（系统未安装思源黑体，微软雅黑同为无衬线，层级靠字重区分；不引入第三族）
- 西文 / 数字：`Arial`

| 层级 | 字号 | 字重 |
|---|---|---|
| 封面主标 | 44px | Bold |
| 封面英文副标 | 20px | Normal |
| 章节扉页大数字 | 180px | Bold |
| 页面主标（顶条白字） | 32px | Bold |
| 顶条右侧英文章节标识 | 16px | Normal |
| 卡片小标题 | 24px | Bold |
| 正文 | 18px | Normal |
| KPI 巨数字 | 72px | Bold |
| KPI 说明 | 16px | Normal |
| 表格 | 16px | 表头 Bold / 表体 Normal |
| 脚注 / 页码 | 14px | Normal |

### ④ 视觉母题
顶条左侧 8px 宽竖条（`#3D7BD9`，高 36px）+ 页面主标，全篇复用；内容页下方统一 `#E8EFF8` 结论条收口。

### ⑤ 配图清单

| 文件 | 等级 | 生成方式 | 真实内容 | 使用页 |
|---|---|---|---|---|
| `fig_pipeline.png` | L1 | matplotlib 实绘 | 贝叶斯动态掩码融合流程（光流/几何/聚类三支 → 后验） | P09 |
| `fig_ablation.png` | L1 | matplotlib 实绘 | 七配置消融 ATE / PSNR 双轴柱图（数据来自论文表 8） | P14 |
| `fig_repro_curve.png` | L1 | 本机训练实跑导出 | 三配置 3DGS 训练 PSNR 曲线 | P15 |
| `fig_repro_render.png` | L1 | 本机渲染实跑导出 | naive / dyn-mask / 无动态三配置渲染对比 | P15 |
| `fig_traj.png` | L2 | matplotlib 实绘 | ATE 对比条形图（ORB-SLAM3 / MonoGS / SplaTAM / 本研究） | P12 |

> 所有图均为脚本生成的真实数据可视化，不使用 ImageGen 生成插画式配图——学术报告禁止虚构视觉证据。

## 三、页面清单（26 页）

| # | 标题 | type | role | rhythm | 要点 |
|---|---|---|---|---|---|
| 01 | 封面 | cover | hero | peak | 题目 / 英文题 / 副标 / 姓名学号导师单位时间 |
| 02 | 目录 | catalog | transition | transition | 4 章 + 页码区间（04–07 / 09–13 / 15–21 / 23–24） |
| 03 | 01 研究背景与问题 | section | transition | transition | 大数字 01 |
| 04 | 动态环境让静态世界假设失效 | content | hero | peak | 核心问题 + 三个失败模式 |
| 05 | 已有研究的三条脉络与共同空白 | content | supporting | valley | 三栏脉络卡 + 空白结论条 |
| 06 | **研究空白：近一年 100 篇的能力矩阵** | content | hero | peak | 单能力覆盖条形 + 交叉稀缺性 + 四者兼备为 0（2026-11-16 新增） |
| 07 | 三个可验证的子问题 | content | supporting | valley | Q1/Q2/Q3 ↔ 目标 ↔ 考核指标 |
| 08 | 02 研究内容与技术路线 | section | transition | transition | 大数字 02 |
| 09 | 四阶段技术路线 | content | supporting | valley | 流程链 + 阶段输出条 |
| 10 | 内容一：贝叶斯概率融合动态掩码 | content | hero | peak | 三证据支路 + 后验公式 + 流程图 |
| 11 | 内容二：尺度感知跟踪与动态感知高斯映射 | content | supporting | valley | 两组机制对比 + 掩码加权渲染 |
| 12 | **内容三：VLM 语义接口与开放词汇查询** | content | hero | peak | 三步挂载 + 验收口径 + 与内容一的关系澄清（2026-11-16 新增） |
| 13 | **内容四：语义—几何目标导航闭环** | content | supporting | valley | 五步流程 + 不自建 benchmark 的评测方案（2026-11-16 新增） |
| 14 | 03 阶段性研究结果 | section | transition | transition | 大数字 03 |
| 15 | 动态掩码质量与相机轨迹精度 | content | hero | peak | KPI 0.012 m / 96.2% + 对比表 + 条形图 |
| 16 | 渲染质量与实时性 | content | supporting | valley | Replica 表 + 118 FPS |
| 17 | 消融实验：哪个模块真的在起作用 | content | supporting | valley | 七配置双轴图 + 排序结论 |
| 18 | 本机复刻：三配置对照实验 | content | hero | peak | 训练曲线 + 渲染对比 + 残影指标 |
| 19 | **跨规模复核：数据放大后收益反而更大** | content | hero | peak | 小场景 vs 放大场景对比图 + 两卡说明 + 如实披露 C4 不成立（2026-11-17 新增） |
| 20 | 公开数据集复现 | content | supporting | valley | 官方 3DGS / 4DGS 复现 + 预处理消融 |
| 21 | 阶段性成果 | content | supporting | valley | 论文 / 专利 / 工程方案 / 实验复现 + 四项进度 |
| 22 | 04 存在问题与下阶段计划 | section | transition | transition | 大数字 04 |
| 23 | 三个尚未解决的问题 | content | supporting | valley | 掩码漏检 / 语义膨胀 / 导航未闭环 |
| 24 | 下阶段时间节点 | content | supporting | valley | 2026.12–2028.05 四条时间线 |
| 25 | 参考文献 | content | supporting | valley | IEEE 格式，与正文引用对应 |
| 26 | 结束页 | ending | hero | peak | 致谢 / 请指正 |

## 四、逐页字段表

### P01 封面
- type: cover / role: hero / rhythm: peak
- layout: 左对齐信息块 + 右侧竖向色条
- visual: L3 `#1E4FA8` 竖条装饰（无 L1）
- visual_role: atmosphere
- density: 字数约 90 / 图片 0 / 留白约 45%
- anti_pattern: 禁止放数据指标；禁止放校徽以外的图片；禁止信息层级超过 4 层

### P02 目录
- type: catalog / role: transition / rhythm: transition
- layout: 左侧「目录 CONTENTS」+ 右侧 4 条章节清单（编号 + 章节名 + 页码区间）
- visual: L3 竖排编号块
- visual_role: atmosphere
- density: 字数约 60 / 图片 0 / 留白约 35%
- anti_pattern: 禁止统计装饰块（"共 21 页"）；禁止"阅读顺序"复述条；禁止全篇主线预告

### P03 / P07 / P11 / P17 章节扉页
- type: section / role: transition / rhythm: transition
- layout: 左大数字 01–04 + 右章节名与一句概括；四页版式完全一致
- density: 字数约 30 / 图片 0 / 留白约 55%
- anti_pattern: 禁止看点列表；禁止本章结论条；禁止四卡片预览

### P04 研究背景与问题
- type: content / role: hero / rhythm: peak
- layout: 上方信息横幅（kicker「核心问题」+ 一句论断）+ 下方三栏失败模式
- visual: L2 三栏文字卡（白底 + 1px `#D6DCE5` 描边）
- visual_role: evidence
- density: 字数约 260 / 图片 0 / 留白约 22%
- anti_pattern: 禁止用"随着…的发展"式万能句开头；禁止三卡等宽等高做成均分网格的观感（三栏需有编号层差）

### P05 文献综述
- type: content / role: supporting / rhythm: valley
- layout: 三栏脉络卡（Ⅰ 动态 SLAM · Ⅱ 三维高斯建图 · Ⅲ 开放词汇语义场）+ 底部空白结论条
- visual: L2 三栏卡
- visual_role: evidence
- density: 字数约 300 / 图片 0 / 留白约 20%
- anti_pattern: 禁止堆砌文献数量；禁止"研究热点"式空话；代表文献必须真实

### P06 三个可验证的子问题
- type: content / role: supporting / rhythm: valley
- layout: 三行竖排分区（Q1/Q2/Q3），每行左问题右考核指标，行间 1px 细线
- density: 字数约 240 / 图片 0 / 留白约 25%
- anti_pattern: 禁止写成"提升效果""深入研究"这类不可考核目标

### P08 四阶段技术路线
- type: content / role: supporting / rhythm: valley
- layout: 顶部四阶段卡片横向流程链 + 箭头 → 下方阶段输出条 → 底部反馈闭环虚线说明
- visual: L1 `fig_pipeline.png` 不适用，本页用纯结构图（Box 绘制的流程链）
- visual_role: anchor
- density: 字数约 280 / 图片 0 / 留白约 18%
- anti_pattern: 禁止四个阶段做成完全等宽等高无主次；禁止流程图里出现未实现的模块而不标注

### P09 内容一：贝叶斯概率融合动态掩码
- type: content / role: hero / rhythm: peak
- layout: 左 55% 流程图 + 右 45% 三证据支路说明与后验公式
- visual: L1 `fig_pipeline.png`（占左 55%）
- visual_role: anchor
- density: 字数约 220 / 图片 1 / 留白约 20%
- anti_pattern: 禁止把公式写成装饰；禁止未标注变量含义

### P10 内容二：尺度感知跟踪与动态感知高斯映射
- type: content / role: supporting / rhythm: valley
- layout: 左右两区（5:5）：左尺度感知联合优化，右动态感知高斯映射
- visual: L2 两区结构图（Box 绘制）
- visual_role: evidence
- density: 字数约 260 / 图片 0 / 留白约 22%
- anti_pattern: 禁止两区完全对称等分而无主次差异

### P12 动态掩码与轨迹精度
- type: content / role: hero / rhythm: peak
- layout: 上方 2 个 KPI 巨数字 + 下方左表右图（表 55% / 图 45%）
- visual: L1 `fig_traj.png`（占右 45%）
- visual_role: anchor
- density: 字数约 230 / 图片 1 / 留白约 18%
- anti_pattern: 禁止只摆数字不给判断；禁止 KPI 卡内塞多条正文

### P13 渲染质量与实时性
- type: content / role: supporting / rhythm: valley
- layout: 左 Replica 对比表（60%）+ 右三项关键读数（40%）
- visual: L2 表格
- visual_role: evidence
- density: 字数约 200 / 留白约 20%
- anti_pattern: 禁止整行底色填充表格；重点行用加粗 + 上下边框

### P14 消融实验
- type: content / role: supporting / rhythm: valley
- layout: 上图（70%）+ 下结论条；图内双轴柱状对比七配置
- visual: L1 `fig_ablation.png`
- visual_role: anchor
- density: 字数约 200 / 图片 1 / 留白约 20%
- anti_pattern: 禁止只贴图不给排序结论；禁止用饼图

### P15 本机复刻
- type: content / role: hero / rhythm: peak
- layout: 左训练曲线（50%）+ 右渲染对比（50%）+ 底部指标条
- visual: L1 `fig_repro_curve.png` + `fig_repro_render.png`
- visual_role: anchor
- density: 字数约 200 / 图片 2 / 留白约 15%
- anti_pattern: 禁止把复刻实验写成"复现论文结果"——必须说明是本机独立实现的对照实验

### P16 阶段性成果清单
- type: content / role: supporting / rhythm: valley
- layout: 四行成果条目（类型 / 名称 / 状态），行间 1px 细线
- density: 字数约 240 / 留白约 22%
- anti_pattern: 禁止把"在审"写成"已发表"；禁止模糊状态

### P18 三个尚未解决的问题
- type: content / role: supporting / rhythm: valley
- layout: 三行分区，每行「问题 + 量化证据 + 影响」，问题名用强调红
- density: 字数约 260 / 留白约 22%
- anti_pattern: 禁止把局限写成优点；禁止"进一步优化"式空话

### P19 下阶段时间节点
- type: content / role: supporting / rhythm: valley
- layout: 横向时间轴 4 节点 + 每节点任务清单
- visual: L2 SVG 时间轴
- visual_role: anchor
- density: 字数约 240 / 留白约 22%
- anti_pattern: 禁止画出开题计划里不存在的里程碑

### P20 参考文献
- type: content / role: supporting / rhythm: valley
- layout: 单栏列表，`[n]` 序号 + IEEE 格式
- density: 字数约 420 / 留白约 10%
- anti_pattern: 禁止编造文献；禁止序号与正文不对应

### P21 结束页
- type: ending / role: hero / rhythm: peak
- layout: 居中大字「请各位老师批评指正」+ 姓名 / 导师 / 单位
- density: 字数约 40 / 留白约 60%
- anti_pattern: 禁止在结束页塞正文结论

---

## 五、修订记录

### 2026-11-16 增补 VLM 与机器人导航（21 页 → 25 页）

| 动作 | 页面 | 说明 |
|---|---|---|
| 新增 | 06 | 研究空白：近一年 100 篇的能力矩阵。基于 arXiv 严格时间窗 2025-11-01~2026-11-16 检索的 100 篇文献，给出单能力覆盖与交叉稀缺性统计，明确「3DGS+语义+动态+导航」四者兼备为 0 篇 |
| 新增 | 12 | 内容三：VLM 语义接口与开放词汇查询。含与内容一的边界澄清（几何判「动没动」、VLM 答「是什么」） |
| 新增 | 13 | 内容四：语义—几何目标导航闭环。五步流程 + 复用 NavArena / HM3D-M3 注入动态扰动的评测方案 |
| 新增 | 19 | 公开数据集复现：官方 3DGS / 4DGS 复现 + 预处理消融（2026-11-17 交叉验证补记：21→25 实为净增 4 页，此前修订表漏列此页） |
| 改写 | 02 | 目录页码区间同步为 04–07 / 09–13 / 15–20 / 22–23 |
| 改写 | 20 | 进度行与《中期检查表》「五、工作进度」保持同一编号与同一数值 |
| 改写 | 22 | 问题 03 由「多楼层真实数据不足」改为「语义地图到导航未闭环」，与检查表「六、存在问题」一致 |
| 改写 | 25 | 参考文献补 2 条近一年导航 / 时空建图工作，并注明 100 篇清单随附录提交 |
| 重排 | 全部 | 页码 22 → 25，全篇页脚同步 |

### 2026-11-17 补跨规模复核页 + 全篇演讲者备注（25 页 → 26 页）

| 动作 | 页面 | 说明 |
|---|---|---|
| 新增 | 19 | 跨规模复核：数据放大后收益反而更大。DGX GB10 上 3 种子 × 3 配置 × 250 iter，共 9 组、197 分钟；静态区 21.820 → 30.071（**+8.25 dB**，小场景为 +3.52 dB），残影 0.1335 → 0.0082（16.3×）。如实披露「仅初始化滤波残影 > B 的 5 倍」在放大版不成立（1.70× vs 小数据 14.7×） |
| 改写 | 2 | 目录页码区间同步为 04–07 / 09–13 / 15–21 / 23–24 |
| 改写 | 14 | 03 章节扉页补「本机与 DGX 双平台、19 次训练」说明 |
| 改写 | 18 | 三配置数值统一为**跨种子均值**（A 30.90/0.080、B 34.42/0.005、C 31.52/0.072），与表 1 完全一致；右上角标注「3 种子均值」 |
| 新增 | 全篇 | **26 页全部写入演讲者备注**（共 14,515 字），每页统一四段：本页作用 / 口述稿（含时长）/ 数据出处 / 预判提问。演讲稿即备注，演讲者视图直接可用 |
| 重排 | 全部 | 页码 25 → 26，全篇页脚同步 |

> 数据来源：`06_实验数据与复现/表2_DGX放大版_3种子.md`、`总表_三端证据链.md`、`图5_三端静态区与残影对比.png`。
> 备注导出稿：`答辩演讲稿_中期_26页_从PPT备注导出.md`（由 PPTX 备注逐页导出，与幻灯片严格一一对应）。
