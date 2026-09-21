---
name: ugc-publisher
description: 在本地 ugc-index.html 模拟微博社区页面中自动发布内容（文字 / 图片 / 视频 / 网页链接）。当用户要求"发帖、发布微博、自动发布、帮我发一条、向 ugc 页面发布图文或视频、附带链接摘要发布"时使用。自动处理注册与登录（用户名密码本地存储以便复用）、发帖时随机出现的四种真人验证弹窗、图片/视频内容理解并动态搭配不少于 120 字文案、网页链接 MCP 解读与摘要、图片/视频链接下载上传，以及发布后的经验复盘与页面变更适配。
---

# UGC 自动发布 Skill

面向同目录下的 `ugc-index.html`（纯前端模拟社区，数据存于浏览器 localStorage，**无后端**）。
所有浏览器操作只能发生在这一个页面内，严禁跳转到其他网址。

## 0. 每次执行前必读

1. 读 `references/page-map.md` —— 当前页面 DOM 地图与状态判定方法。
2. 读 `lessons.md` —— 历史踩坑记录，**先避开已知坑**，再开始操作。
3. 操作中一旦发现真实 DOM 与 `page-map.md` 不一致，立即更新该文件（规则 8）。

## 1. 解析发布需求

从用户指令中提取以下字段（缺失项按默认策略处理，不要反复追问）：

| 字段 | 说明 | 缺失时 |
|---|---|---|
| `text` | 用户明确指定的文案 | 有媒体时自动创作；无媒体无文字则拒绝发布 |
| `images` | 本地图片路径 **和/或** 图片 URL 列表 | 无 |
| `videos` | 本地视频路径 **和/或** 视频 URL 列表 | 无 |
| `links` | 文案中的网页链接（也需从 text 中正则提取 `https?://...`） | 无 |
| `username` | 指定以哪个账号发布 | 未登录则自动注册新账号（见步骤 3） |

媒体与链接的处理规则见 `references/content-pipeline.md`。

## 2. 打开页面并判定登录态（不跳出页面）

1. Playwright MCP **禁止 `file://` 协议**（实测报错 "Access to file: protocol is blocked"），
   必须用本地静态服务器：`python3 -m http.server 8765 --directory <项目根>`（后台运行）。
   **先复用再启动**：`curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/ugc-index.html`
   返回 200 说明服务已在跑（上一个任务留下的），直接用，不要重复起服务。
   端口固定 8765——localStorage 按 origin 隔离，换端口账号/登录态就"没了"。
   localhost 等同于该页面本身，**仍严禁导航到任何外站**。
2. 始终复用同一标签页；**浏览器与服务器默认跨任务保持运行**（登录态在 localStorage 里，
   关浏览器可能丢上下文导致下次重新登录/注册），只在用户明确要求时才收尾关闭。
3. 登录态判定由快速通道脚本内部完成（读 `wb_sim_session`），无需单独一次 evaluate 探查；
   手动流程时用 `localStorage.getItem('wb_sim_session')`，不要只凭视觉判断。

## 3. 账号决策（task 规则 2）

详细流程见 `references/accounts.md`，决策表：

| 当前登录态 | 用户是否指定 username | 动作 |
|---|---|---|
| 已登录 | 未指定 / 与当前一致 | 直接用当前账号 |
| 已登录 | 指定且不同 | 点 `#logoutBtn` 退出后，按"未登录"行处理 |
| 未登录 | 指定 | 凭据库命中→登录；未命中→用该用户名注册（生成密码并存储） |
| 未登录 | 未指定 | **自动注册新用户**，用户名/密码/昵称写入凭据库 |

凭据库路径：`.ugc-publisher/accounts.json`（已 gitignore，注册后设 `chmod 600`）。
注册/登录失败（如"用户名已被占用""用户名或密码错误"）的处置见 accounts 参考手册。

## 4. 准备发布内容（task 规则 4 / 6 / 7）

按 `references/content-pipeline.md` 执行，顺序：

1. **链接下载型媒体（规则 7）**：`images/videos` 中的 http(s) URL 用 curl 下载到
   `.ugc-publisher/downloads/`，按 Content-Type 修正扩展名；下载失败则告知用户并跳过该媒体。
2. **网页链接（规则 6）**：文案中的网页链接一律用 **WebFetch（MCP）** 在后台解读，
   **绝不允许浏览器标签页跳转到该链接**（规则 1）。生成 1–3 句中文摘要备用。
3. **媒体理解（规则 4）**：
   - 图片 → `mcp__zai-mcp-server__analyze_image`（逐张，描述主体/场景/氛围/醒目文字）；
   - 视频 → `mcp__zai-mcp-server__analyze_video`（≤8MB，MP4/MOV/M4V；超限或失败则按文件名与链接上下文处理并在文案中保守描述）。
4. **文案合成**：
   - **含图片/视频时，最终文案不少于 120 个汉字**，必须基于媒体实际内容动态创作，
     与媒体强相关、自然真实，不得套模板空泛抒情；
   - 用户给了 `text` 时，以其意图为骨架扩写，不歪曲原意；
   - 含链接时，把网页摘要自然融入文案，并在末尾保留原始 URL；
   - 上限 2000 字（textarea `maxlength=2000`），超出则压缩摘要部分。

## 5–7. 快速通道（首选，一次工具往返完成发布）

**性能原则：慢的根因是每个 UI 动作都是一次独立 MCP 往返（每次 click/type 还附带整页快照）。
因此除"内容理解"和"字符验证码识图"外，所有浏览器动作一律合并进
`scripts/autopost.js` 一次 `browser_run_code_unsafe` 调用完成，不要逐步 click/type/fill。**

标准执行顺序：

1. 内容准备（这部分无法合并）：媒体转换/下载、`analyze_image`/`analyze_video`、
   WebFetch/curl 读链接——多张图的 dwebp 与 analyze 在**同一并行 block** 发出；
   这些调用可以与"确认服务器存活/打开页面"并行。
2. 用 Write 写 `.ugc-publisher/next-post.json`：
   ```json
   { "step": "publish", "text": "最终文案", "images": ["/绝对路径/a.webp"], "videos": [], "username": "可选" }
   ```
   路径必须是绝对路径；媒体总数 ≤9。
3. 调一次 `browser_run_code_unsafe`（filename = `.claude/skills/ugc-publisher/scripts/autopost.js`）。
   脚本内部依次完成：必要时导航 → 会话检测 → 登录/同身份静默重注册（见 accounts.md）→
   填文案 → 一个 filechooser 批量上传全部图片/视频 → 点发布 → 轮询处置弹窗
   （①滑块 ②点选 ④顺序点击全部自动解，带重试上限）→ 以 feed 首帖正文+媒体数判定成功。
4. 返回 `{ ok: true, via, captchas, post }` → 已含发布验证（首帖 nick/正文开头/媒体数），
   **无需再发任何验证工具调用**，直接向用户汇报。
5. 返回 `{ ok:false, need:'textCaptcha' }`（方式③，唯一需要模型看图的）：
   - 对 `#captchaCanvas` 截图到 `.ugc-publisher/captcha.png` → Read 识图（字符集与
     E/F、C/G 易混经验见 captcha-playbook §3，拿不准先点 canvas 换一张）；
   - 把 next-post.json 改为 `{ "step":"solveText", "code":"识别结果" }`，
     再调一次 autopost.js（它会填码、确认、继续同一个处置循环直到出结果）；
   - 验证码错误会自动换码，重复截图-回填，最多 4 次。
6. 返回 `need:'manual'|'timeout'|'authOverlay'` 或 `stage:'auth'`：脚本无法自愈，
   按对应 reference 手动处置（此时才退回逐工具操作），解决后重跑脚本；
   连续 2 次同一失败，停下来向用户报告。
7. 改动脚本本身后先跑 `{ "step":"dryRun" }`：只做 鉴权+填写+上传+预览数量校验然后 reload
   丢弃草稿、不发布，用于验证回归。

手动逐工具流程（快速通道失效时的兜底）见 `references/captcha-playbook.md` 与步骤 3；
其弹窗识别表仍有效：

| 弹窗 | 识别 | 处置 |
|---|---|---|
| 登录/注册框 | `#authOverlay.show` | 按步骤 3 完成登录或注册，弹窗关闭后**重新点 `#publishBtn`** |
| 滑动验证 | `#captchaBadge` 含"方式①" | captcha-playbook §1（Playwright 鼠标拖拽到最右） |
| 图片点选 | 含"方式②" | 从 `#captchaDesc` 解析「目标」，点选所有匹配 `.pick-cell`，再点确认 |
| 字符验证码 | 含"方式③" | 截图 `#captchaCanvas` 自行识图填入；看不清就换一张，最多 4 次 |
| 顺序点击 | 含"方式④" | 按 `data-n` 1→8 依次点击 `.seq-cell` |
| 图片灯箱 | `.lightbox.show` | 点击遮罩关闭（非阻断） |
| 原生 confirm 对话框 | 浏览器 dialog | 仅删除微博时出现；发布流程内出现则接受 |

验证码通过后页面会**自动完成发帖**，任何路径下都不要再重复点发布、不要点 `#captchaCancel`。

## 8. 收尾与经验沉淀（task 规则 8，强制）

收尾策略（**默认保活**，为下一个发帖任务省掉启动/登录往返）：
- 保留浏览器标签与 http.server 8765 继续运行，供后续任务复用；
- 仅清理本次临时文件：dwebp 转出的分析用 png、`captcha.png` 等（一律在 `.ugc-publisher/` 下，
  不污染项目根目录）；`next-post.json` 可留可删（不含密码）；
- 只在用户明确要求（如"关闭/清理/结束"）或确认长时间不再发帖时，才关浏览器、停服务。

每次发布任务结束后（尤其失败或走了弯路）：

1. 向 `lessons.md` 追加一条记录：日期、现象、根因、解决办法、涉及的选择器；
2. 若页面 DOM 与手册不符（选择器失效、结构改版、出现新验证码类型），
   **当场更新** `references/page-map.md` 与 `captcha-playbook.md`；
3. 重复出现 2 次以上的教训，提炼进 SKILL.md 或对应 reference 的正文，不只是堆日志。

## 参考文件

- `scripts/autopost.js` —— **快速通道一键发布脚本**（鉴权+填写+上传+发布+验证码①②④+校验）
- `references/page-map.md` —— 页面 DOM 地图、localStorage 键位、限制参数
- `references/accounts.md` —— 注册/登录流程、凭据库格式、错误处置
- `references/captcha-playbook.md` —— 四种验证码的具体解法与可复用脚本（手动兜底）
- `references/content-pipeline.md` —— 媒体下载、链接解读、文案创作规范
- `lessons.md` —— 犯错经验日志（持续更新）
