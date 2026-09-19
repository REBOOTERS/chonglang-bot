# ugc-publisher 测试用例集（test-cases.md）

- 适用页面：`ugc-index.html`（模拟微博社区，单标签页内完成所有操作）
- 图片资源：`res/` 已由 PNG 全部转为 WebP（q=80，尺寸不变），并按主题分为 4 组（共 15 张）
- 链接资源：`res/urls.md`（4 个微信公众号文章链接）
- 账号：首次执行任意一条 case 时 skill 自动注册账号并把用户名/密码存到 `.ugc-publisher/accounts.json`，后续复用
- **每条 case 的「指令」**：`>` 引用块内为可直接粘贴执行的话术语；含图片的微博文案必须由 skill 基于图片实际内容动态生成（**≥120 汉字**），不要提前写死；标签与 emoji 由 skill 根据文章或图片内容自行配置。

## 资源清单

### 图片分组（res/）

| 目录 | 主题 | 数量 | 单图内容速查 |
|---|---|---|---|
| `res/1` | 写生女孩系列 | 5 | ①00738 黄昏欧洲石板老街卷发女孩站着画人像速写｜②00739 雨天江南小巷黑长发女孩廊下画速写（红灯笼湿石板）｜③00741 佛堂香火气里黑衣女孩坐长椅低头画本（金佛蜡烛背景）｜④00743 老图书馆窗边逆光金发女孩在厚书上画素描｜⑤00744 涂鸦街角霓虹招牌下黑背心女孩翻看建筑速写本 |
| res/2 | 猫咪系列 | 6 | ①01386 橘猫戴墨镜双爪合十坐沙发（小风扇+奶茶+毛绒玩具排排坐）｜②01855 竹林夕阳下趴卧的橘猫（武侠片氛围感拉满）｜③03207 书架格子里与书并排的狸花白猫（绿眼直视镜头）｜④05638 银渐层戴金色派对帽捧草莓蛋糕（一点燃蜡烛）｜⑤05684 布艺沙发上英短蓝猫胖脸特写（琥珀眼蓝胡须光）｜⑥05704 花园逆光草地金渐层幼猫抬爪扑帝王蝶 |
| `res/3` | 城市通勤/秋日人像 | 3 | ①01365 地铁站台白T黑长发女孩｜②05957 秋日公园长椅燕麦色针织套装女孩（落叶长椅高跟鞋）｜③05986 街头人潮中白毛衣短裙女孩回头微笑 |
| `res/4` | 绘画作品 | 1 | ①05652 黑白铅笔素描长发女孩四分之三侧脸，发丝层次细腻 |

### 链接清单（res/urls.md）

| # | URL | 主题（curl 抓取确认） |
|---|---|---|
| L1 | https://mp.weixin.qq.com/s/n3yKcO3KxZfnDbTly1fAyA | 《一张截图开局，AI 自己做规划写代码：实测 Seed Evolving 的 0 到 1 产品力》——仅靠一张音效列表截图+简单需求，让 doubao-seed-evolving 用 Compose Multiplatform 从 0 搭出三端（Android/iOS/桌面）音乐播放器 SodaMusic，自动规划 plan、coding-build-verify 循环、refer 官方图修 UI |
| L2 | https://mp.weixin.qq.com/s/fXv50j4O1xhkIchVeGnYRw | 《Seed-Evolving再升级：检索准、幻觉少！》——三大能力升级：Coding 工程能力（复杂仓库修复、跨文件修改）、Agent 检索（缺失召回、多工具并行）、幻觉控制（不基于错误结果硬答）；统一 Model ID 周级迭代，零迁移成本 |
| L3 | https://mp.weixin.qq.com/s/mJflWTs5MAZOUAtHFTuY2Q | 《从能跑到好用：Doubao-Seed-Evolving 如何把 Android 组件高质量迁到 iOS》——把知乎 Matisse 图片选择器复刻为 SwiftUI 版 MatisseSwift：15 分钟代码迁移、7 分钟自动修复编译错误、3900 行 Java → 1345 行 Swift，API 链式语法几乎 1:1 |
| L4 | https://mp.weixin.qq.com/s/7BJvU8DvxjYATsgdmdojbA | 《不是谁更强，而是谁更适合你：Seedance 2.0 Fast 与 MiniMax H3 的实测结论》——AI 视频生成双雄从指令遵循、一致性、多模态（含「10 张猫咪武侠图」提示词案例）、性价比四维实测，结论各有千秋 |
| | https://ark.volcengine.com/region:cn-beijing/promotion/model?modelName=doubao-seed-evolving | 模型体验入口（L2 摘要里的附带链接，不单独开 case） |

## 测试用例

### A. 图片发布类（覆盖 1 图 / 2 图 / 3 图 / 5 图 / 6 图 / 9 图上限 / 超 9 图）

---

#### Case 01｜单图 · 绘画作品（res/4）
- **测试点**：最基础的"文字+1 图"链路；验证 webp 上传、预览计数=1、120 字硬指标。
- **指令**：
  > 用 ugc-publisher 发布内容「这张铅笔素描的发丝质感我能看一整天，分享给你们」，选择 res/4 目录下的图片

#### Case 02｜单图 · 生日猫（res/2 之 05638）
- **测试点**：单图+强话题性内容；预期文案贴合"生日仪式感"，自然带出 `#猫咪生日#` 之类标签与 🎂🐱 等 emoji。
- **指令**：
  > 用 ugc-publisher 发布内容「家里主子今天过生日，蛋糕和小皇冠都给它安排上了」，选择 res/2 目录下 z-image-turbo_05638_.webp 这张图片

#### Case 03｜双图 · 东方意境写生（res/1 之 00739+00741）
- **测试点**：按文件名指定同一目录下 2 张；预期合并归纳两张共性（都是中国元素场景中画速写的女孩：雨巷+佛堂）并点出差异。
- **指令**：
  > 用 ugc-publisher 发布内容「跟着速写本逛古寺和雨巷，笔尖比脚步先到」，选择 res/1 目录下 z-image-turbo_00739_.webp 和 z-image-turbo_00741_.webp 两张图片

#### Case 04｜三图 · 猫咪三连（res/2 之 01386+05684+05704）
- **测试点**：按文件名指定 3 张；三张猫姿态/场景差异大（耍酷/慵懒/灵动），考验多图合并与细节对应（小风扇奶茶、蓝胡须光、帝王蝶）。
- **指令**：
  > 用 ugc-publisher 发布内容「同一只猫的三种人设：大佬、厌世和快乐小狗」，选择 res/2 目录下 z-image-turbo_01386_.webp、z-image-turbo_05684_.webp、z-image-turbo_05704_.webp 三张图片

#### Case 05｜整组 5 图 · 写生女孩全系列（res/1 全部）
- **测试点**：目录下所有文件全选（5 张）；多图文案需点出五场景跨度（老街/雨巷/佛堂/图书馆/涂鸦街）。
- **指令**：
  > 用 ugc-publisher 发布内容「把世界当成画室：一个速写本女孩的五个现场」，选择 res/1 目录下的图片

#### Case 06｜整组 6 图 · 猫咪全系列（res/2 全部）
- **测试点**：全选 6 张；预期统一主题收束（"猫的一万种生活方式"之类），逐猫给画面细节，≥120 字。
- **指令**：
  > 用 ugc-publisher 发布内容「翻了翻相册，我家镜头里的猫生百态」，选择 res/2 目录下的图片

#### Case 07｜整组 3 图 · 城市与人像（res/3 全部）
- **测试点**：全选 3 张；地铁站→秋日长椅→闹市回头，考验串联叙事能力。
- **指令**：
  > 用 ugc-publisher 发布内容「从地铁到黄昏街头，这座城市的通勤与浪漫」，选择 res/3 目录下的图片

#### Case 08｜边界 · 恰好 9 图（跨 res/1+res/3+res/4）
- **测试点**：页面媒体上限为 9；跨目录取图（5+3+1=9），应全部上传成功，预览=9，发布后 feed 中呈 3×3 宫格。
- **指令**：
  > 用 ugc-publisher 发布内容「九条 post 里的瞬间：写生、通勤与一张素描」，选择 res/1 目录下全部 5 张、res/3 目录下全部 3 张以及 res/4 目录下的 1 张图片

#### Case 09｜异常 · 超过 9 图（res/1 全部 + res/2 全部 = 11 张）
- **测试点**：**负面用例**。页面 toast「最多 9 个媒体文件」；预期 skill 在上传前拦截，明确告知"最多 9 张"并询问/建议保留哪 9 张，**不得**静默丢弃后直接发布。
- **指令**：
  > 用 ugc-publisher 发布内容「全部素材都放上去吧」，选择 res/1 和 res/2 两个目录下所有图片（共 11 张）

### B. 链接解读类（覆盖 4 篇文章；浏览器绝不跳转外站，摘要由 skill 用 MCP/curl 解读）

---

#### Case 10｜纯文字+链接 L1（AI 0→1 做产品）
- **测试点**：无图纯链接；WebFetch 若被拦应自动降级 curl（已实测 WebFetch 对该域名报 unsafe domain），生成摘要+标签+emoji，URL 原样保留。
- **指令**：
  > 用 ugc-publisher 发布内容，链接为 https://mp.weixin.qq.com/s/n3yKcO3KxZfnDbTly1fAyA ，根据文章内容生成合适摘要，并配置标签和 emoji

#### Case 11｜纯文字+链接 L2（模型升级，正文 JS 渲染）
- **测试点**：**特殊兜底用例**。该页静态 HTML 无 `js_content` 正文（临时链接/需微信环境），摘要只能从 `og:description` 提取（三大升级点）；预期 skill 用 og:description 写摘要，不编造正文没有的细节。
- **指令**：
  > 用 ugc-publisher 发布内容，链接为 https://mp.weixin.qq.com/s/fXv50j4O1xhkIchVeGnYRw ，根据文章内容生成合适摘要，并配置标签和 emoji

#### Case 12｜纯文字+链接 L3（Android→iOS 迁移）
- **测试点**：摘要应包含关键数字（15 分钟、7 分钟、3900→1345 行）和 Matisse/SwiftUI 关键词；标签如 `#iOS开发` `#AI编程`。
- **指令**：
  > 用 ugc-publisher 发布内容，链接为 https://mp.weixin.qq.com/s/mJflWTs5MAZOUAtHFTuY2Q ，根据文章内容生成合适摘要，并配置标签和 emoji

#### Case 13｜纯文字+链接 L4（视频模型测评）
- **测试点**：摘要需呈现对比框架（四个维度+各有胜负的结论），不能只夸一个模型；为 Case 15 的组合做铺垫。
- **指令**：
  > 用 ugc-publisher 发布内容，链接为 https://mp.weixin.qq.com/s/7BJvU8DvxjYATsgdmdojbA ，根据文章内容生成合适摘要，并配置标签和 emoji

### C. 组合与账号类

---

#### Case 14｜网络图片 URL（测试规则 7：下载→理解→发布）
- **测试点**：媒体是 http URL 而非本地路径；预期 curl 下载到 `.ugc-publisher/downloads/`，按 Content-Type 定扩展名，analyze_image 理解后配 ≥120 字文案再上传。依赖外网，可回归时跳过。
- **指令**：
  > 用 ugc-publisher 发布内容「看到一张很舒服的 webp 官方测试图，下载下来发一条」，图片链接为 https://www.gstatic.com/webp/gallery/1.jpg

#### Case 15｜图片+外链组合（武侠猫 × AI 视频测评 L4）
- **测试点**：同一帖内 1 张 webp（01855 竹林橘猫，文章里恰好提到"武侠猫"提示词）+ 1 个网页链接；预期文案把画面、文章核心结论自然串起，末尾保留 URL；同时满足图片帖 ≥120 字。
- **指令**：
  > 用 ugc-publisher 发布内容「这只竹林橘猫，就是我心目中 AI 视频里该走出来的武侠猫主角——配合这篇双模型实测一起看」，选择 res/2 目录下 z-image-turbo_01855_.webp 这张图片，链接为 https://mp.weixin.qq.com/s/7BJvU8DvxjYATsgdmdojbA ，根据文章内容生成合适摘要，并配置标签和 emoji

#### Case 16｜指定用户名发布（测试规则 2 的账号切换）
- **测试点**：当前若有会话则先退出，用指定用户名登录（库中无则自动注册并存储密码），发布成功后验证帖子归属该账号（feed「我的」tab / `wb_sim_posts` 中 userId 一致）。
- **指令**：
  > 用 ugc-publisher 以用户名 ugc_catfan 发布内容「今日份猫咪播报员上线」，选择 res/2 目录下 z-image-turbo_05684_.webp 这张图片

#### Case 17｜异常 · 音频不支持（res 下 .mp3）
- **测试点**：**负面用例**。页面只有图片/视频两个 input（`accept=image/*` / `accept=video/*`），mp3 无法上传；预期 skill 明确说明不支持音频、不发布空内容，并建议配封面图或跳过；验证后把这次拦截记入 `lessons.md`。
- **指令**：
  > 用 ugc-publisher 发布内容「分享一首老歌：难念的经」，附件是 res/周华健-难念的经.mp3

## 执行注意事项（给 skill 的提醒，同样适用每条 case）

1. Playwright 禁 file://，先在项目根起 `python3 -m http.server 8765 --directory <项目根>`，打开 `http://localhost:8765/ugc-index.html`；固定 8765 端口（localStorage 按 origin 隔离）。
2. 每次点发布后约 70% 概率弹验证码（滑块/图片点选/字符识别/顺序点击随机），按 captcha-playbook 自动处理，通过后页面会自动发帖，请勿重复点发布。
3. 字符识别验证码截图统一存到 `.ugc-publisher/`，不要往项目根写文件。
4. WebFetch 对 `mp.weixin.qq.com` 已实测被安全策略拦截，链接类 case 直接用带 UA 的 curl 抓 og:title / og:description / `#js_content`。
5. 每个 case 执行完在 skill 的 `lessons.md` 追加一条结果记录（成功也记关键数据，失败记根因）；DOM 漂移当场更新 page-map。
6. Case 09、17 是"预期被友好拒绝"的用例——判定标准是 skill 说清原因而非硬发。
