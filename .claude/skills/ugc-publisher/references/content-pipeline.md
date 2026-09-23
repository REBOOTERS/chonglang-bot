# 内容管线：链接解读、媒体下载、文案创作

## 一、输入形态

用户给的媒体/链接可能是：
- 本地路径：`/Users/.../xxx.png`、`./photos/a.jpg`、`~/Movies/b.mp4`
- URL：`https://.../a.png`、`https://example.com/article`（文章页和媒体 URL 要区分）
- 直接写在文案里的链接：需要从 `text` 里正则提取 `https?://[^\s，。）)]+`

URL 类型判断：先看扩展名（jpg/jpeg/png/gif/webp/heic → 图片；mp4/mov/m4v/webm → 视频），
不确定的用 `curl -sIL <url>` 看 `Content-Type`：`image/*` 图片、`video/*` 视频、`text/html` 网页。

## 二、媒体 URL 下载（task 规则 7）

```bash
mkdir -p .ugc-publisher/downloads
curl -fsSL --max-time 60 -o .ugc-publisher/downloads/<名字> "<url>"
```

- 文件名用 URL 末段或 hash 命名，**扩展名按 Content-Type 修正**（image/jpeg→.jpg，video/mp4→.mp4）。
- 下载后 `file <path>` 或 Read 图片确认文件有效；失败（403/超时/不是媒体）→ 告诉用户并跳过该媒体，不要假装发了。
- 视频仅支持上传可被 `<input accept=video/*>` 接受的文件；分析工具限制 ≤8MB、MP4/MOV/M4V。
- 用完的下载文件可保留在 `.ugc-publisher/downloads/`（已 gitignore），不必每次清理，但同名要覆盖前确认。
- 本地路径要先展开 `~` 并检查存在性。

## 三、网页链接解读（task 规则 6）

- 一律使用 **WebFetch（MCP）** 抓取，prompt 要求：概括主题、关键信息/数据、适合微博的 1–3 句中文摘要。
- **绝不用 Playwright 标签页导航过去**——规则 1 要求所有页面操作留在 ugc-index.html 内。
- WebFetch 失败（鉴权墙、反爬）：再试 `curl -fsSL --max-time 30 -A "Mozilla/5.0..."` 取正文；
  仍失败则文案中保留原链接并说明"链接内容暂无法读取"，不要编造摘要。
- 微信公众号（mp.weixin.qq.com）已知特性：WebFetch 会被安全策略拦截（2026-09-19 实测），直接走 curl；
  部分文章静态 HTML 无 `#js_content`（临时链接/JS 渲染），此时回退读 `<meta property="og:title">`
  和 `og:description`（description 常含完整要点），只写 meta 里有的信息。
- 多个链接分别解读；同一域名的重复链接只解读一次。

## 四、媒体内容理解（task 规则 4）

### 图片
逐张调用 `mcp__zai-mcp-server__analyze_image`，prompt 至少要求：
主体是什么、场景/环境、显眼文字（OCR）、色彩与氛围、可写进文案的细节。
多张图要做**合并归纳**：它们是同一件事的不同角度，还是并列的多个事物。

**webp 注意**：analyze_image 仅接受 `.jpg/.jpeg/.png`，传 `.webp` 会报
"Unsupported image format"。素材是 webp 时先用 dwebp 转临时 png：
`dwebp in.webp -o .ugc-publisher/tmp-analyze.png`，分析后删除临时文件。
（页面的 `<input accept=image/*>` 与 FileReader 本身完全支持 webp，上传发布不需要转。）

### 视频
调用 `mcp__zai-mcp-server__analyze_video`，要求：开头/中段/结尾发生了什么、
关键画面、人物动作、可辨识文字与声音信息（若能感知）。
文件 >8MB 或格式不受支持时：截取文件名、上下文、（若是 URL）海报帧/网页信息做保守描述，
并在向用户汇报时说明视频未完整解析——文案里不得杜撰镜头细节。

### 读图失败的兜底
单张图片分析失败：自己 Read 该图片（Read 工具可直接看图）再描述。
全部分析手段都失败：如实在回复中说明，文案改为围绕用户给定文字与文件名，不虚构画面。

## 五、上传前压缩（localStorage 配额硬约束，强制）

页面把所有媒体以 DataURL 存进 localStorage（通常配额 ~5MB，**base64 还会再膨胀 ~33%**），
存量帖子也占同一份配额。超限时 `savePosts` 抛 `QuotaExceededError`——
注意此时验证码已通过、输入框已清空，只有内存里有帖子，**reload 即永久丢失**。
2026-09-22 实测：6 张 PNG 原图 7.8MB → 超限；压成 1280px JPEG 后 1.2MB → 成功。

**规则（配额是累计的，压缩档位按"剩余空间"选，不是固定档）：**
1. 先在页面 evaluate 测真实占用：`JSON.stringify(localStorage).length`；
   配额按 5MB（5,242,880 字节）算，`剩余 = 5MB − 已用`。
   新帖（文件总大小 ×1.4 + 文案）目标 **≤ 剩余空间的 80%**，留安全余量。
2. 按剩余空间选压缩档（sips 能编 JPEG，不能编 webp）：
   - 剩余 >3MB → 标准档：`-Z 1280 -s formatOptions 75`（约 150–300KB/张）
   - 剩余 1–3MB → 中配档：`-Z 1000 -s formatOptions 60`（约 90–160KB/张）
   - 剩余 <1MB → 激进档：`-Z 800 -s formatOptions 50`（约 50–80KB/张）
   压完先 `stat` 求和验证再上传；超限就降一档重压。
3. 压缩仅为**上传用**：媒体理解（analyze_image）仍对原图进行，细节不丢；压缩产物放
   `.ugc-publisher/compressed/`，next-post.json 指向压缩文件。
4. 视频不能转码时（本机有 ffmpeg 可压则压：`ffmpeg -i in.mp4 -vcodec libx264 -crf 28 out.mp4`），
   超预算先告知用户；发布后控制台出现 QuotaExceededError 要主动检查，
   不能仅凭"验证码通过/弹窗关闭"汇报成功。
5. 存量帖子的大尺寸 DataURL 是用户数据，**重压或删除旧帖必须先征得用户同意**，不自行处理。

## 六、文案创作规范

### 硬要求
1. **只要本次发布含图片或视频，最终文案 ≥120 个汉字**（不含 URL 与话题符号也要够数；写完自己数）。
2. 内容必须与媒体/链接的实际内容强相关，具体到画面里的事物，禁止"今天分享一组美照，大家快来看看"这类万能模板。
3. 含网页链接：摘要融入正文（讲清楚链接是什么、值得看的点），**末尾保留原始 URL**。
4. 上限 2000 字；超长优先压缩链接摘要，不砍媒体观察细节。
5. 用户给了明确文案：保留其核心信息与语气，在其骨架上补足到 120 字；不要加入与用户立场冲突的观点。
6. 不得编造媒体中不存在的事实、数据、人物身份；不确定的用模糊表述（"看起来像是…"）。

### 风格
- 模拟社区（微博风格）：第一人称、口语化、有现场感；可自然使用 1–3 个 emoji 和 `#话题#`，
  但不要堆砌；话题优先蹭页面右侧"热门话题"中与内容真正相关的。
- 结构参考（不必照搬）：开场钩子 → 看到/经历了什么（具体细节）→ 感受或观点 → 链接/互动收尾。
- 多图：点出图片之间的关系（"前两张是…最后一张…"）；视频：用文字还原动态过程。

### 自检清单（发布前默读）
- [ ] 有媒体时汉字 ≥120
- [ ] 描述与 analyze 结果一一对应，无幻觉
- [ ] 链接摘要准确且 URL 原样保留
- [ ] ≤2000 字、无多余的 Markdown 语法（页面按纯文本展示，`white-space: pre-wrap`）
- [ ] 与用户指定意图一致
