# 页面地图：ugc-index.html

> 最后核对日期：2026-09-19（基于仓库内 ugc-index.html 源码）。
> 页面是**纯前端**应用：账号、会话、帖子全部在浏览器 localStorage，刷新页面不丢登录态。
> 若运行时发现本文件与实际页面不符，**立即更新本文件**，并在 lessons.md 记录变更原因。

## 打开方式

- **Playwright MCP 屏蔽 `file://` 协议**（2026-09-19 实测），不能直接打开本地文件。
  改为在项目根目录起本地静态服务器：
  `python3 -m http.server 8765 --directory <项目根>`（后台运行，端口占用就换号），
  然后浏览器打开 `http://localhost:8765/ugc-index.html`，`curl` 探到 200 再操作。
- 只允许这一个标签页；解读外链用 WebFetch，**禁止 browser_navigate 到外站**。
- 已知无害控制台报错：`/favicon.ico 404`，忽略。
- 经 http 访问后 localStorage 按 origin（`http://localhost:8765`）隔离；换端口等于换一份数据，
  端口要固定，否则账号/登录态"丢失"。

## localStorage 键位

| 键 | 内容 |
|---|---|
| `wb_sim_session` | 当前登录用户名（字符串）；无此键 = 游客 |
| `wb_sim_users` | `{ username: { nick, pass, bio, created } }`，pass 是页面自带 hash，**无法反推明文**（所以密码必须自己存一份） |
| `wb_sim_posts` | 帖子数组，新帖 `unshift` 在最前 |

一键读取登录态：
```js
() => ({ session: localStorage.getItem('wb_sim_session'),
         users: Object.keys(JSON.parse(localStorage.getItem('wb_sim_users') || '{}')) })
```

## 关键选择器

### 顶部导航 / 登录态
- 已登录：`#navUser` 内含 `.nav-nick`（昵称）和 `#logoutBtn`（退出）
- 游客：`#navUser` 内含 `#openLogin`、`#openReg`
- 游客横幅：`#guestBanner`（含 `#guestLoginBtn`）

### 登录/注册弹窗 `#authOverlay`（出现时带 `.show`）
- 标题 `#authTitle`；昵称字段 `#nickField`（仅注册时显示，内含 `#regNick`）
- 用户名 `#authUser`（正则 `^[a-zA-Z0-9_]{3,20}$`，placeholder"字母数字，至少 3 位"）
- 密码 `#authPass`（≥6 位，回车即提交）
- 提交 `#authSubmit`（登录文案"登录"，注册文案"注册并登录"）
- 模式切换链接 `#authSwitchLink`；右上角关闭 `#authClose`
- 错误条 `#authErr.show`，文本即失败原因

### 发帖区
- 文本框 `#postInput`（textarea，`maxlength=2000`，输入后需同步 `#charCount`）
- 图片按钮 `#imgBtn` → 隐藏 `<input type=file id=imgInput accept=image/* multiple>`
- 视频按钮 `#vidBtn` → 隐藏 `<input type=file id=vidInput accept=video/*>`（单选）
- 表情 `#emojiBtn`（发帖用不到，且其弹层会被 document click 关闭）
- 已选媒体预览 `#mediaPreview`（`.media-item` 每项一个，含 `.rm` 删除按钮）；上限 9 个
- 发布按钮 `#publishBtn`；字数 `#charCount`

### 验证弹窗 `#captchaOverlay`（出现时带 `.show`）
- 类型徽章 `#captchaBadge`：
  - `方式① 滑动验证` / `方式② 图片点选` / `方式③ 字符识别` / `方式④ 顺序点击`
- 标题 `#captchaTitle`、说明 `#captchaDesc`、容器 `#captchaBody`、错误 `#captchaErr`、按钮区 `#captchaActions`
- 取消按钮固定 id `#captchaCancel`（点了会丢弃本次待发帖子 `pendingPost=null`，**不要点**）
- 测试钩子：登录后控制台执行 `window.__wbForceCaptcha('slider' | 'imagePick' | 'textCode' | 'sequence')`
  可强制弹出指定类型验证码（会带一条"（测试验证码）"帖子），仅用于演练/回归验证 captcha-playbook。

### 其他
- toast `#toast`（成功/失败提示，出现时带 `.show`，约 2.2s 消失）
- 大图灯箱 `#lightbox.show`（点遮罩关闭）
- Feed：`#feed`，帖子 `.post`，正文 `.post-body`，媒体 `.post-media`（`.cell img` / `.cell.video video`）
- 只有删除自己的帖子会触发原生 `confirm()`，发布流程不涉及

## 发布机制要点（源码行为）

1. `#publishBtn` 点击 → `tryPublish()`：游客先弹登录框；文本和媒体都为空时 toast 报错不继续。
2. 待发帖子存入 `state.pendingPost`；随后 **`Math.random() < 0.7` 概率弹验证码**，否则直接发布。
3. 验证码**通过后自动调用 `finalizePublish()`**：帖子入列、清空输入框与预览、跳"全部"feed、toast"发布成功"。
4. 验证码弹了但被关闭/取消 → `pendingPost` 被清空，需重新填写发布（因此不要点"取消发帖"）。
5. 媒体以 DataURL 存进 localStorage（`readAsDataURL`），视频过大可能撑爆 localStorage：
   上传前若视频明显过大（>~10MB）应提示用户。

## 限制参数速查

- 文案：0–2000 字；媒体：≤9 个；视频：单文件
- 用户名：3–20 位字母/数字/下划线；密码：≥6 位；昵称：非空，≤20 字
