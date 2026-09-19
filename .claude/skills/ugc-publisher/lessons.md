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
