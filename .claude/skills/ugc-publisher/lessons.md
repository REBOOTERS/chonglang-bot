# 犯错经验日志（持续更新）

规则：每次发布任务结束追加记录；同一问题出现 2 次以上，把结论提炼进 SKILL.md / 对应 reference 正文。
页面结构与本日志记录冲突时，以页面实况为准并立即修订 `references/page-map.md`。

格式：
```
## YYYY-MM-DD 简短标题
- 现象：
- 根因：
- 解决：
- 涉及选择器/接口：
```

---

## 2026-09-19 初始建库：从源码评审得到的先验经验

- **发布后验证码是随机的（约 70%），不能因为第一次没弹就假设永远不弹。**
  - 现象：点 `#publishBtn` 后有时直接成功，有时弹窗。
  - 根因：`tryPublish()` 内 `Math.random() < 0.7` → `startRandomCaptcha()`。
  - 解决：发布后一律进入弹窗轮询循环，见 captcha-playbook。

- **验证码通过即自动发帖，重复点发布会发两条。**
  - 根因：`captchaPass()` 内部直接调用 `onSuccess`（= `finalizePublish`）。
  - 解决：看到"验证通过/验证成功"后只等待 toast"发布成功"，绝不再点 `#publishBtn`。

- **点"取消发帖"会丢掉待发内容且不保留草稿。**
  - 根因：`overlay._close()` 执行 `state.pendingPost = null`；此时文本框通常也已被读取，媒体还在预览，状态不一致。
  - 解决：永远不点 `#captchaCancel`；验证码解不开就换一张（字符码）或重跑（滑动/顺序），超过重试上限再找用户。

- **登录态不能只看界面，以 localStorage 为准。**
  - 根因：导航栏由 JS 渲染，快照时机不同可能拿到旧状态；`wb_sim_session` 是唯一事实源。
  - 解决：每次会话先 evaluate 读 `wb_sim_session`；新浏览器上下文无会话时，优先用凭据库 default 登录而非重新注册。

- **注册用户名有严格正则，昵称字段仅注册模式出现。**
  - 根因：`register()` 校验 `^[a-zA-Z0-9_]{3,20}$`、密码 ≥6、昵称非空；`#nickField` 在登录模式 hidden。
  - 解决：自动生成 `ugc_` + 6 位小写字母数字；先确认弹窗标题是"注册微博"再填昵称；撞名（"用户名已被占用"）换随机后缀，最多 3 次。

- **滑块靠合成事件可能判定不到位，必须拖到距最右 ≤4px。**
  - 根因：`onUp` 判定 `knob.offsetLeft >= max() - 4`，且位置来自真实 mousemove 的 clientX。
  - 解决：首选 `browser_run_code_unsafe` + `page.mouse` 匀速分步拖拽（见 captcha-playbook §1）；一次不到位会回弹，可原地再拖。

- **图片点选验证码的目标动物要从说明文字解析，不能凭宫格猜。**
  - 根因：目标是随机的，宫格里可能有多个同类（判重要求"恰好全选"），目标藏在 `#captchaDesc` 的「」中。
  - 解决：正则 `「(.+?)」` 取目标，按 `.pick-cell[data-t=...]` 全选后再确认。

- **字符验证码答案读不到，只能看图。**
  - 根因：`code` 是 `captchaTextCode` 闭包内局部变量。
  - 解决：截图 canvas 自行 OCR；字符集 `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`（无 I/O/0/1）；看不清主动换一张，最多 4 次。

- **视频/图片以 DataURL 写入 localStorage，大视频会导致存储溢出。**
  - 根因：`readFiles()` 用 `FileReader.readAsDataURL`，最终随 `wb_sim_posts` 序列化进 localStorage（通常上限 5MB 左右）。
  - 解决：视频明显偏大（>~10MB）时先告知用户风险；上传后若页面报错（toast/控制台 QuotaExceededError），删除该待发媒体并反馈。

- **页面是纯静态页，没有任何后端 API。**
  - 含义：不要尝试抓接口；链接解读走 WebFetch；页面刷新后登录态/帖子仍在（localStorage），换浏览器上下文则没有。

## 2026-09-19 真机联调记录（建库当天首次冒烟，全部通过）

- **Playwright MCP 不允许 `file://`，直接导航本地文件被拦截。**
  - 现象：`browser_navigate file:///.../ugc-index.html` 报 "Access to \"file:\" protocol is blocked"。
  - 解决：项目根目录后台跑 `python3 -m http.server 8765 --directory <项目根>`，打开
    `http://localhost:8765/ugc-index.html`；任务结束停掉服务。端口必须固定——localStorage 按 origin 隔离，换端口账号就"没了"。
  - 已同步修订 SKILL.md 步骤 2 与 page-map.md。

- **元素截图的 filename 是相对当前工作目录的裸路径。**
  - 现象：`browser_take_screenshot(filename:"captcha-test.png")` 把图写到了项目根目录。
  - 解决：截图一律存 `.ugc-publisher/captcha.png`（已加 gitignore），任务结束清理。

- **四种验证码解法全部真机验证通过（经页面测试钩子 `window.__wbForceCaptcha(type)` 逐个触发）：**
  - ① 滑块：`browser_run_code_unsafe` + `page.mouse` 25 步匀速拖到最右 → 一次通过，自动"发布成功"。
  - ② 图片点选：从 `#captchaDesc` 的「」解析目标，按 `data-t` 全选后点 `#captchaOk` → 一次通过。
  - ③ 字符码：截 `#captchaCanvas` 自己读图（实测 VRFV 一次识别正确）→ 填入确认通过。`#captchaInput` 用 `.fill()` 即可，确认按钮直接读 value，不依赖 input 事件。
  - ④ 顺序点：按 `data-n` 1→8 每步间隔 60ms 连点 → 8 格 done 后自动通过。
  - 注册链路（`#openReg` → 填昵称/用户名/密码 → `#authSubmit`）与图片上传链路（`#imgBtn` → file chooser → `browser_file_upload` → `#mediaPreview` 出现 1 个 `.media-item`）均实测通过；`fill()` 会触发字数统计更新。
  - 测试后已清空浏览器 localStorage 并删除测试账号残留（测试仅发生在 Playwright 独立浏览器配置中，不影响真实数据）。
  - 唯一控制台报错是 favicon 404，无关。

## 2026-09-19 准备测试素材时的环境经验（test-cases 配套）

- **WebFetch 对 mp.weixin.qq.com 全部报 "Unable to verify if domain ... is safe to fetch"。**
  - 解决：按 content-pipeline 兜底直接用 curl（带桌面 UA、--max-time 30），四篇文章均 200。
  - 已把该域名写进 test-cases.md 注意事项，链接类 case 不必先试 WebFetch。

- **微信公众号文章可能没有静态正文（临时链接/JS 渲染）。**
  - 现象：urls.md 第 2 条（fXv50j4O1xhkIchVeGnYRw）HTML 中无 `id="js_content"`，正文为空。
  - 解决：读 `<meta property="og:title">` 与 `<meta property="og:description">`——后者含全文要点摘要，足够生成微博摘要；不要编造 meta 之外的细节。提取脚本：正则去标签后取 js_content，缺失时回退 og 字段。

- **本机 sips 不能编码 webp。**
  - 现象：`sips -s format webp x.png` 报 `Can't write format: org.webmproject.webp`（exit 13）。
  - 解决：用 homebrew 的 `/opt/homebrew/bin/cwebp`：`cwebp -q 80 in.png -o out.webp`（15 张全部转换成功，尺寸保持，体积远小于 png）。ffmpeg 亦可作备选。

## 2026-09-19 Case 01 录屏执行（res/4 铅笔素描单图，成功）

- **analyze_image MCP 不支持 webp。**
  - 现象：传 res/4 的 .webp 报 `Unsupported image format: .webp. Supported formats: .jpg, .jpeg, .png`。
  - 解决：`dwebp x.webp -o .ugc-publisher/tmp-analyze.png` 转临时 png 再分析，分析完删除。**页面上传不受影响**：`#imgInput accept=image/*` + FileReader 正常吃 webp，预览与帖子 DataURL 均为 `data:image/webp;base64,`，feed 展示正常。已写入 content-pipeline.md。

- **字符验证码首次识别失败（2 次机会内通过）。**
  - 现象：第一张读成 `EFAT` 提交 → `#captchaErr`"验证码错误"，页面自动换码清空；第二张 `2GMR` 一次通过。
  - 根因：首字符蓝色衬线 E/F 在旋转+干扰线下，中横是否存在不易判定（E 三横、F 两横）。
  - 对策：E/F、C/G、I/L 这类仅差一笔的字符拿不准时，**直接点 canvas 换一张**比硬猜划算（失败也会自动换，但多一次错误交互）；数字 2/7、字母 Z 同理。

- **录屏要用仓库自带的 `recordings/rec-start.sh <case-id>` / `rec-stop.sh`。**
  - 手搓 ffmpeg 时踩坑：ffmpeg 8.1.2 没有 `-capture_cursors`（复数），报 `Unrecognized option` exit 8；脚本里正确的参数是 `-capture_cursor 1`（单数）。脚本带 pidfile 防重复、SIGINT 优雅收尾（保证 mp4 moov 完整）、1 小时上限。
  - 双屏时第二参数指定屏幕索引；avfoundation 列表里屏幕是 "Capture screen 0/1"。

- **执行结果留痕**：自动注册账号 `ugc_7k2m9x`（昵称"冲浪选手7K2M"），已存 `.ugc-publisher/accounts.json`（chmod 600，default）。帖子正文 284 字符/248 汉字，1 张 webp，`wb_sim_posts` 长度 3。

## 2026-09-19 Case 03 双图发布 + 流程性能优化

- **跨浏览器配置的 localStorage 是空的：凭据在库里 ≠ 页面里有这个账号。**
  - 现象：Case 03 新起 Playwright 浏览器后 `wb_sim_users` 为 `{}`，仍按旧决策先登录 → "用户名或密码错误"，再切注册重填昵称，账号环节白跑约 4 次工具往返。
  - 解决：登录失败先区分"页面无此用户（重注册同一身份）"与"密码真不符（报告）"；该判定已内置进 autopost.js，accounts.md 决策表同步修订。

- **慢的根因是工具往返次数，不是页面速度：一次发帖 20+ 次 MCP 调用，每次 click/type 还回传整页快照。**
  - 优化（已落地）：新增 `scripts/autopost.js` 快速通道——
    1. 一次 `browser_run_code_unsafe`（filename 加载脚本，入参走 `.ugc-publisher/next-post.json`）完成
       导航→会话检测→登录/静默重注册→`fill()` 文案→单个 filechooser `setFiles` 批量传图→发布→
       ①②④验证码全自动处置→以 feed 首帖正文前缀+媒体数判定成功，返回值自带验证信息；
    2. 仅 ③ 字符码中断返回 `need:'textCaptcha'`，识图后写 `step:'solveText'` 再跑一次；
    3. dwebp/analyze 多图并行，且与服务器探活/页面打开并行；
    4. 服务器先 `curl` 探活复用，浏览器+http.server 默认跨任务保活，不再每次收尾重启；
    5. 去掉固定 700–800ms 等待，一律 `waitForSelector/waitForFunction` 事件驱动；发布后轮询 250ms。
  - 实测往返：有 ①②④验证码的帖子从 ~15 次降到 2 次（publish + 可能的一次 solveText）。
  - 验证手段：`step:'dryRun'` 只跑到预览数量校验然后 reload 丢弃，不产生帖子。
  - **坑：browser_run_code_unsafe 的 filename 文件必须整体是一个 `async (page) => { ... }` 表达式**
    （与内联 code 同格式，末尾不要加分号），顶层直接写 `const` 会报
    `SyntaxError: Unexpected token 'const'`，末尾分号报 `Unexpected token ';'`。
  - **沙箱里没有任何 Node 全局**（`require/process/module/global` 均 undefined，`await import('node:fs')`
    报 "A dynamic import callback was not specified"）。配置改走 `page.request.get` 经本机
    `http://localhost:8765/.ugc-publisher/next-post.json`（python http.server 会服务点目录，curl 实测 200）。
    文件路径通过 `page.setInputFiles(selector, paths)` 直接灌进隐藏 input（不经文件读取）。

- **filechooser 路线在 MCP 下走不通，且 API 名不是 setFiles。**
  - 点 `#imgBtn` → MCP 层拦截 filechooser、挂起脚本弹原生文件框；`chooser.setFiles` 等不到。
  - 该定制版 Playwright 的方法名是 **`page.setInputFiles('#imgInput', paths)` / Locator `setInputFiles`**
    （没有 Locator.setFiles，报 "is not a function"）。直接灌隐藏 input 不触发 chooser，干净可靠。
  - **预览残留坑**：中断的运行/手动上传会在 `#mediaPreview` 留下旧媒体，新上传是追加不是替换，
    数量校验会超时。脚本已在上传前逐个点 `.rm` 清空——注意 `.rm` 点击会 `renderMediaPreview()`
    整体重写 innerHTML，批量 forEach 点击只有第一个生效，必须点一个等数量减一再点下一个。
  - **solveText 配置没有 text 字段**：成功判定不能读 cfg.text；发布时把 `{head,n}` 存到
    `window.__lastPost`，判定与 solveText 重跑都从 window 取。2026-09-20 实测：回填 SDWQ 后
    正是这行报错，但验证码实际正确、帖子已成功发布——排查此类"脚本报错"先查 wb_sim_posts/feed。

## 2026-09-22 res/2 六猫图发布：沙箱 setTimeout 消失 + 多图 PNG 撑爆配额

- **MCP 外层沙箱不再提供 setTimeout/setInterval（环境变更，脚本历史上依赖过它）。**
  - 现象：autopost.js 一跑就报 ReferenceError: setTimeout is not defined；探测确认 setTimeout/setInterval/queueMicrotask 均 undefined，Promise 正常。
  - 解决：sleep 改用 Playwright 自带的 page.waitForTimeout(ms)（实测可用）；page.evaluate 浏览器上下文内的 setTimeout 不受影响（solveSequence 无需改）。已改 autopost.js 第 17 行。
  - 改动后按 SKILL 规则先 dryRun：via=session、preview=6 通过，再正式发布。

- **多张高分辨率 PNG 原图直接上传导致 QuotaExceededError，验证码白过、帖子差点丢失。**
  - 现象：首次发布触发方式③字符码，识别 YNJQ 正确，captchaPass→finalizePublish 执行（输入框/预览被清空），但 savePosts 抛 QuotaExceededError（wb_sim_posts exceeded the quota）；localStorage 仍只有 4 条旧帖。脚本返回 timeout（弹窗已关、轮询 45s 无果）。
  - 根因：6 张 PNG 共 7.8MB，base64 膨胀后远超 localStorage 约 5MB 配额；finalize 先 unshift 内存态再 save，异常导致未持久化。
  - 解决：reload 丢弃内存半成品 → sips 批量压成 1280px/质量 75 JPEG（共 1.2MB，存 .ugc-publisher/compressed/）→ 重跑成功：首帖 nick 冲浪选手7K2M、6 张媒体，本次未再弹验证码（30% 直放路径）。
  - 预防：上传前按 原文件总大小 × 1.4 估算配额，超限先压缩；压缩只为上传，analyze 仍用原图。已写入 content-pipeline.md 第五节。
  - 排查经验复用：solveText/超时后先查控制台错误与 localStorage 帖子数，再看弹窗（延续 2026-09-20 教训）。

## 2026-09-23 微信链接摘要发布（纯链接无媒体，一次成功）

- 流程完全按既有经验走通：mp.weixin.qq.com 直接跳过 WebFetch 走 curl（200），文章含静态 js_content，用 python 正则提正文成功（og:title「一张截图开局，AI 自己做规划写代码：实测 Seed Evolving 的 0 到 1 产品力」）。
- 文案要点：摘要覆盖起因（不想为汽水音乐 SVIP 音效氪金）→ AI 自动规划 plan → 踩坑（缺 gradle、UI 丑）→ 多轮截图/参考图引导后成品开源 → 结论（详细参考资料胜过模糊需求）；正文保留原文 URL 与文中 GitHub 地址；标签蹭了页面热门话题 #代码能治百病吗#，配 #AI编程# #SeedEvolving#。
- 无媒体发布不强制 120 字，但摘要型帖子自然写到约 400 字；autopost 一次通过、未弹验证码。无新坑。

## 2026-09-23 图片 URL 下载发布（gstatic WebP 画廊，一次识别通过）

- 规则 7 流程走通：https://www.gstatic.com/webp/gallery/1.jpg curl 直下 200，Content-Type image/jpeg、44KB（虽在 WebP 画廊路径下，.jpg 链接给的是原始 JPEG，无需转码/压缩）；按 Content-Type 补 .jpg 扩展名存 .ugc-publisher/downloads/gallery1.jpg，再 analyze。
- 图片内容：高崖俯瞰的北欧峡湾 S 形蓝绿湖泊、苔原山坡、远山残雪与大气透视。文案以用户句子为骨架扩写至约 350 字，配 🏞️⛰️，标签 #风景摄影# #峡湾# #周末去哪儿#（蹭热门）。
- 发布触发方式③字符码 J8R4（J/8/R/4 均清晰），截图识别一次通过，自动完成发帖，首帖 1 张媒体。无新坑。
- 小提醒：URL 路径含 webp 不代表文件是 webp，以 Content-Type/扩展名实际探测为准。

## 2026-09-23 指定新账号 ugc_catfan 发帖：补齐快速通道的切账号/全新注册路径

- **用户指定了与当前会话不同的用户名，旧版 autopost 不支持，会无视 cfg.username 直接用旧 session 发帖。**
  - 解决：增强 authenticate()——session 存在且 cfg.username 不同 → 点 `#logoutBtn` + waitForFunction 等 session 清空；随后：
    1. 凭据库命中该用户名 → 原登录/同身份重注册路径；
    2. 凭据库未命中且页面 wb_sim_users 也无 → 用 cfg.password/cfg.nick 全新注册（返回 creds 供落库）；
    3. 页面已有该用户名但库中无密码 → 返回 ACCOUNT_EXISTS_NO_PASSWORD，不硬闯。
  - 凭据（密码/昵称）由执行者预生成放进 next-post.json，注册成功后立刻写入 accounts.json（chmod 600），避免密码只存在于内存。
  - 验证：改动后 dryRun（via=register、preview=1），再正式发布一次通过，首帖 nick=猫咪播报员、1 张媒体。
- **用户给的媒体文件名与实际扩展名不符：说 res/2/z-image-turbo_05684_.webp，实际目录只有同名 .png。**
  - 处置：按同基名匹配到 .png（臭脸英短蓝猫），不追问；analyze 用 PNG 原图，上传复用 .ugc-publisher/compressed/05684.jpg（299KB，规避配额）。
  - 经验：扩展名以磁盘实际文件为准，同基名唯一匹配时直接用，汇报时说明偏差。

## 2026-09-23 九图（res/1×5+res/3×3+res/4×1）：配额是累计的，1280/75 标准档不够用

- **现象**：9 张原图 10.5MB，按标准档（1280px/q75，共 1.95MB→base64 2.6MB）压缩后发布，验证码已自动通过，savePosts 仍抛 QuotaExceededError；脚本 timeout。
- **根因**：此前各任务积累的 7 条帖子已占 4114KB（两个大图帖分别 2056KB/1608KB），剩余空间仅约 1MB。只估算"新文件×1.4"而不看存量，判断错误。
- **解决**：reload 丢弃半成品 → evaluate 测 `JSON.stringify(localStorage).length` 得真实占用 → 改激进档 800px/q50 重压 9 张（532KB→base64 约 726KB）→ 重发成功，方式②点选码自动解除，9 张媒体齐全。
- **沉淀（已改 content-pipeline 第五节）**：压缩档位必须按"剩余配额"选，不是固定档：
  - 先测存量占用，配额按 5MB 算；
  - 剩余 >3MB → 1280/q75（约 150–300KB/张）；
  - 剩余 1–3MB → 1000/q60；
  - 剩余 <1MB → 800/q50（约 50–80KB/张）；
  - 新帖目标 ≤ 剩余空间的 80%，留余量。
- **建议未采纳先不做**：存量大头是用户旧帖里的全尺寸 DataURL，重压旧帖或删帖需用户确认，不自行处理；如用户同意可整体"瘦身"wb_sim_posts。
