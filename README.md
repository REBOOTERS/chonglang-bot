# 🌊 chonglang-bot · Claude Code 技能合集

> 看得懂页面、读得了教程、破得开验证码，还会从每一次犯错中自我进化的 Skill 集 —— 从 UGC 自动发布到裸眼 3D 视频特效。

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-orange.svg)](#-技能总览)
[![Model](https://img.shields.io/badge/Model-Seed%202.1%20pro%200915-blue.svg)

chonglang-bot 收集以 [Claude Code](https://claude.com/claude-code) **Skill** 形式实现的智能体技能：每个 Skill 都是自包含的（技能定义 + 脚本 + 踩坑经验库），放在 `.claude/skills/` 下，在本项目中打开 Claude Code，用一句自然语言即可驱动。

## 🧩 技能总览

| Skill | 领域 | 一句话介绍 | 状态 |
|---|---|---|---|
| [ugc-publisher](#-skill-1ugc-publisher--ugc-自动发布) | UGC 自动发布 | 在模拟社区页面完成注册登录 → 多模态文案创作 → 上传发布 → 四类验证码自动破解的全流程无人值守 | 稳定 |
| [burst-out-frame](#-skill-2burst-out-frame--人物冲出画面裸眼-3d) | 视频特效 | 看教程视频自学剪法，用本地 ffmpeg + rembg 复刻「人物冲出画面」裸眼 3D 效果 | 🆕 新增 |

## 🤖 Seed-2.1-pro-0915 加持

本项目由豆包 **Seed-2.1-pro-0915**（Seed Evolving 系列）模型提供核心智能：

| 能力 | 在本项目中的体现 |
|---|---|
| **多模态理解** | 调用视觉模型逐张解析图片内容（支持视频解析），文案与媒体内容一一对应；逐帧看懂教程视频并沉淀为可执行剪法 |
| **规划与推理** | 自动制定发布/剪辑计划；面对验证码弹窗、存储配额超限、登录态失效、抠像主体翻转等意外，基于环境反馈动态调整策略 |
| **工具调用（Agent）** | 编排 Playwright 浏览器自动化、视觉分析 MCP、WebFetch 网页解读、本地 ffmpeg / Python 管道等多种工具协同完成任务 |
| **进化能力** | 周级迭代的模型 + 每个 Skill 持续积累的 `lessons.md` 经验库，双层进化：模型本身在进化，智能体的"经验"也在每次任务后增长 |

---

## 📢 Skill 1：ugc-publisher · UGC 自动发布

一个**能看、能想、能进化**的 UGC 自动发布智能体。在仓库自带的模拟社区页面 `ugc-index.html`（纯前端、数据存于浏览器 localStorage，无后端、可安全演练）中，用一句自然语言指令即可完成从账号注册登录、多模态内容创作到验证码自动破解的全流程无人值守发布。

传统脚本式机器人依赖写死的选择器和预制文案，页面一改版、内容一换主题就罢工。ugc-publisher 不一样在：

- 👁️ **多模态理解**：图片 / 视频不是"附件"，而是创作输入 —— 逐张分析主体、场景、氛围甚至画面中的文字，再据此动态生成强相关文案；
- 🧠 **长程任务规划**：自动把"发布"拆解为 鉴权 → 内容准备 → 填写 → 上传 → 发布 → 弹窗处置 → 结果校验 的完整计划并自主执行；
- 🧬 **自我进化**：每次任务的踩坑都会沉淀为经验日志，重复出现的教训被提炼进技能正文；页面 DOM 一变，当场更新页面地图并记录原因，越用越稳。

### 核心能力

- 🔐 **账号全自动管理** —— 未登录且未指定账号时自动注册新用户；用户名、密码、昵称加密存储于本地凭据库（`.ugc-publisher/accounts.json`），后续任务自动复用登录；支持指定任意账号切换发布
- 🖼️ **多模态文案创作** —— 含图片 / 视频的帖子，基于媒体实际内容动态生成 **不少于 120 字**的高质量文案，并自动配置贴合主题的 emoji 与话题标签
- 🔗 **网页链接智能解读** —— 文案中的网址通过 MCP 工具后台解读（浏览器标签页绝不跳转），生成 1–3 句摘要自然融入正文，文末保留原始 URL
- ⬇️ **媒体链接下载** —— 图片 / 视频 URL 自动下载，按 Content-Type 修正格式后按本地媒体同等规则处理
- 🛡️ **四种验证码自动破解**
  - ① **滑动验证**：模拟真实鼠标匀速拖至最右
  - ② **图片点选**：解析说明文字中的目标，按数据特征精确全选
  - ③ **字符识别**：截图 + 视觉识图填入，看不清自动换码
  - ④ **顺序点击**：按序号 1→8 依次完成
- ⚡ **快速通道** —— 除视觉理解与字符识图外，所有浏览器动作合并进 `autopost.js`，**一次工具往返**完成鉴权、填写、批量上传、发布与验证码处置，返回值自带发布校验
- 📊 **配额自适应** —— 自动探测 localStorage 剩余空间，按剩余容量分档压缩图片（1280 / 1000 / 800px），多图也不撑爆存储
- 🧬 **经验沉淀与页面适配** —— 每次任务复盘写入经验日志；发现真实 DOM 与手册不符立即更新页面地图，持续适配页面改版

### 快速开始

**环境要求**

- [Claude Code](https://claude.com/claude-code) CLI
- **Playwright MCP**：浏览器自动化（Skill 会自动复用本地 `python3 -m http.server 8765` 静态服务，因为 Playwright MCP 禁止 `file://` 协议）
- **视觉分析 MCP**：用于图片 / 视频内容理解与字符验证码识别
- `python3`（macOS 自带）

**使用方式**

Skill 已随仓库放在 `.claude/skills/` 下，在本项目中打开 Claude Code，直接用自然语言下达指令即可，例如：

```text
用 ugc-publisher 发布内容「翻了翻相册，我家镜头里的猫生百态」，选择 res/2 目录下的图片
```

```text
用 ugc-publisher 发布内容，链接为 https://example.com/article ，根据文章内容生成摘要，配置标签和 emoji
```

```text
用 ugc-publisher 以用户名 ugc_catfan 发布内容「今日份猫咪播报员上线」，选择 res/2 下指定图片
```

首次执行时 Skill 会自动完成：启动 / 复用本地静态服务 → 注册账号并存储凭据 → 内容理解与文案创作 → 上传发布 → 自动处置验证码 → 校验发布结果。浏览器与服务默认跨任务保活，无需重复初始化。

**发布规格**

| 项目 | 限制 |
|---|---|
| 文案长度 | 0–2000 字（含媒体时 ≥120 个汉字） |
| 媒体数量 | 单次 ≤ 9 个 |
| 视频 | 单文件；过大有 localStorage 配额提示 |
| 账号 | 用户名 3–20 位字母 / 数字 / 下划线，密码 ≥6 位 |

### 测试用例

系统化的测试用例集 `test-cases.md`，覆盖：

- **图片发布**：1 图 / 2 图 / 3 图 / 5 图 / 6 图 / 9 图上限 / 超 9 图
- **链接发布**：4 篇不同主题文章的摘要生成
- **账号链路**：自动注册、凭据复用、指定账号切换
- **验证码专项**：四类验证码逐一演练（页面内置测试钩子可强制触发）

配套录屏脚本位于 `recordings/`，素材位于 `res/`。

---

## 🎬 Skill 2：burst-out-frame · 人物冲出画面（裸眼 3D）

复刻剪映教程类视频「人物如何冲出画面」的效果：竖屏画布中央是一条 16:9 画面带，主体在带内时与背景完全重合，随后沿关键帧放大，**冲破画面带边缘**，形成主体穿出屏幕的裸眼 3D 观感。

这个 Skill 的特别之处在于它的**来源**：智能体观看 `videox-factory/lesson.mp4` 剪映教程视频，逐帧拆解效果构成 → 用本地工具链复现 → 把踩过的坑沉淀成 `lessons.md` → 最终固化为可对**任意视频**复用的 Skill。一条「看视频学技能」的完整链路。

### 核心能力

- 🏠 **全本地、零云端依赖** —— AI 抠像用 rembg（isnet-general-use 模型）+ onnxruntime 本地推理，裁剪、合成、关键帧动画、编码全部在本地 ffmpeg filter graph 内完成，保留原音频
- 🎯 **HeroTracker 跨帧主体跟踪** —— 按与上一帧主体的重叠量锁定主角而非每帧独立取最大块：主体贴近镜头时不会误判为背景，远处的第二只狗、背后的路人也不会被一起抠出来
- 📐 **方向守恒** —— 横屏源输出保持横屏（1920×1080）、竖屏源输出竖屏，先 ffprobe 探测源方向，绝不把横屏素材塞进竖屏画布
- 🌫️ **模糊填充，不用黑边** —— 四周背景是同源画面放大模糊 + 压暗，主体冲出画面带后进入的是"画面延伸区"而非突兀黑框
- 🎥 **竖屏素材智能裁切** —— `--track-crop` 让 16:9 裁切窗口沿主体纵向跟随，高潮近景的头不会被静态中心裁切掉
- ⚡ **一条命令出片** —— 先 ffmpeg 截 3 秒短片段快速调放大时机与强度，contact sheet 目检满意后再跑全片（抠像约 1.4s/帧，不浪费在反复全片试错上）

### 快速开始

**环境要求**

- ffmpeg / ffprobe 6.x+（只用内置 filter）
- [uv](https://docs.astral.sh/uv/) + Python 3.13 venv：`uv venv` 后 `uv pip install rembg pillow numpy scipy onnxruntime`
- 抠像模型：`scripts/fetch_model.py isnet-general-use` 自动走镜像下载到 `~/.u2net/`（国内直连 GitHub 仅 21KB/s，脚本实测镜像 2.9MB/s）

**使用方式**

在本项目中打开 Claude Code，自然语言触发即可：

```text
把 videox-factory/example/1.mp4 做成人物冲出画面的裸眼 3D 效果，输出到 videox-factory/output/
```

```text
用 burst-out-frame 处理这段横屏视频，保持横屏输出，背景用模糊填充
```

对应底层命令（Skill 会自动编排）：

```bash
.venv/Scripts/python.exe .claude/skills/burst-out-frame/scripts/burst_effect.py \
  INPUT.mp4 -o OUTPUT.mp4 --bg blur
```

完整的参数调优表（放大时机、倍数、锚点、mask 边缘质量等 20+ 项）、
症状 → 参数故障对照、ffmpeg filter graph 逐段图解，见 Skill 内的
`SKILL.md`、`lessons.md` 与 `references/`。跨设备环境复刻步骤见
`videox-factory/CLAUDE.md`。

---

## 🏗️ 项目结构

```
chonglang-bot/
├── ugc-index.html                        # 模拟社区页面（纯前端，localStorage 存储）
├── .claude/skills/
│   ├── ugc-publisher/                    # ★ Skill 1：UGC 自动发布
│   │   ├── SKILL.md                      #   技能定义与执行流程
│   │   ├── lessons.md                    #   犯错经验日志（持续进化）
│   │   ├── scripts/
│   │   │   └── autopost.js               #   快速通道一键发布脚本
│   │   └── references/
│   │       ├── page-map.md               #   页面 DOM 地图与状态判定
│   │       ├── accounts.md               #   注册/登录/凭据库规范
│   │       ├── captcha-playbook.md       #   四类验证码破解手册
│   │       └── content-pipeline.md       #   媒体下载、链接解读、文案规范
│   └── burst-out-frame/                  # ★ Skill 2：人物冲出画面（裸眼 3D）
│       ├── SKILL.md                      #   技能定义、参数调优表、质量判定
│       ├── lessons.md                    #   踩坑记录（模型下载/抠像翻转/黑边否决…）
│       ├── scripts/
│       │   ├── burst_effect.py           #   主编排器：一条命令出片
│       │   ├── segment.py                #   rembg 抠像 + HeroTracker 主体跟踪
│       │   ├── track_crop.py             #   竖屏素材的裁切窗口跟随
│       │   └── fetch_model.py            #   抠像模型镜像下载
│       └── references/
│           ├── ffmpeg-graph.md           #   filter graph 逐段图解
│           └── troubleshooting.md        #   症状 → 参数对照
├── videox-factory/                       # burst-out-frame 的实验场与产出目录
│   ├── CLAUDE.md                         #   环境配置与跨设备复刻指南
│   ├── task.md                           #   任务定义（看 lesson 学技能）
│   ├── lesson.mp4                        #   教程源视频（不入库）
│   ├── example/                          #   待复刻素材（不入库）
│   ├── output/                           #   最终成片（不入库）
│   └── analysis/                         #   调试中间产物（不入库）
├── res/                                  # ugc 测试素材（15 张图片，4 组主题）
├── recordings/                           # ugc 录屏脚本
├── test-cases.md                         # ugc 完整测试用例集
└── task.md                               # 原始需求
```

## 🧬 进化机制

chonglang-bot 的"进化"不是一句口号，而是每个 Skill 内置的强制流程（两个 Skill 各自维护 `lessons.md`）：

1. **每次任务结束必复盘**：日期、现象、根因、解决办法，逐条追加到对应 Skill 的 `lessons.md`；
2. **重复 2 次以上的教训**自动（由执行者）提炼进 `SKILL.md` 或对应 reference 正文，而不是堆积日志；
3. **现实漂移即时响应**：ugc-publisher 运行时发现页面结构与 `page-map.md` 不符当场修订；burst-out-frame 每次执行前先读踩坑记录，新的失败模式（抠像翻转、跟踪丢失、filter 断链）即时补录；
4. **模型周级迭代**：配合 Seed Evolving 系列统一 Model ID 的快速升级，智能体能力随模型持续增长，零迁移成本。

## 📄 License

[Apache License 2.0](LICENSE)
