# 验证码处置手册（四种）

发布后若出现 `#captchaOverlay.show`，先读 `#captchaBadge` 文本确定类型。
**通过后页面会自动完成发帖**，不要再点发布；**不要点 `#captchaCancel`**（会丢弃待发帖子）。

通用状态检查（evaluate）：
```js
() => ({
  captcha: document.getElementById('captchaOverlay').classList.contains('show'),
  badge: document.getElementById('captchaBadge').textContent,
  auth: document.getElementById('authOverlay').classList.contains('show'),
  toast: document.getElementById('toast').textContent,
  err: document.getElementById('captchaErr').textContent
})
```

## 1. 方式① 滑动验证

判定：badge 含"滑动验证"；轨道 `#sliderTrack`、滑块 `#sliderKnob`。
要求：松手时滑块距最右端 ≤4px，拖不到位会回弹并提示"请拖到最右侧"。

**首选：`browser_run_code_unsafe` 走真实鼠标事件**（合成 mousedown 容易被坐标判定卡住）：

```js
async (page) => {
  const b = await page.evaluate(() => {
    const track = document.getElementById('sliderTrack');
    const knob = document.getElementById('sliderKnob');
    const t = track.getBoundingClientRect(), k = knob.getBoundingClientRect();
    return { kx: k.left + k.width / 2, ky: k.top + k.height / 2, max: t.width - k.width };
  });
  await page.mouse.move(b.kx, b.ky);
  await page.mouse.down();
  const steps = 25;
  for (let i = 1; i <= steps; i++) {
    await page.mouse.move(b.kx + b.max * i / steps, b.ky, { steps: 2 });
    await page.waitForTimeout(25); // 匀速带轻微停顿，更像真人
  }
  await page.mouse.up();
  return await page.evaluate(() => document.getElementById('sliderTrack').classList.contains('ok'));
}
```

返回 `true` → 轨道变绿（"验证成功"），约 350ms 后自动关闭并发帖。
返回 `false`（看到 `#captchaErr`"请拖到最右侧"）→ 滑块已回弹，原样再拖一次。

也可用 `browser_drag`：起点 `#sliderKnob`，终点为 `#sliderTrack` 右缘（用 ref 定位），
但不同分辨率下终点可能差几像素，优先上面的脚本。

## 2. 方式② 图片点选

判定：badge 含"图片点选"；3×3 宫格 `.pick-cell`（emoji），每个有 `data-t`（猫/狗/熊猫/狐狸/老虎/兔子/熊/考拉/狮子）。
目标动物在说明文本里：`点击所有「猫」……`。规则：必须**恰好选中全部目标**（可能 1 个或多个），多选/漏选都报错"选择不正确，请重试"并清空选择。

一步完成（evaluate，从 desc 解析目标并点选，不点确认）：
```js
() => {
  const target = document.querySelector('#captchaDesc').textContent.match(/「(.+?)」/)[1];
  document.querySelectorAll('.pick-cell').forEach(c => {
    if (c.dataset.t === target && !c.classList.contains('selected')) c.click();
  });
  return { target, picked: document.querySelectorAll('.pick-cell.selected').length };
}
```
确认返回的 picked ≥1 后，点 `#captchaOk`（evaluate `document.getElementById('captchaOk').click()`）。
若 `#captchaErr` 出现"选择不正确"：说明目标解析错了，重新读 `#captchaDesc` 文本再来一轮（选项不会刷新，只是取消选中）。

## 3. 方式③ 字符识别（图形验证码）

判定：badge 含"字符识别"；`#captchaCanvas`（160×48）上 4 个扭曲大写字符，
字符集 `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`（**没有 I、O、0、1**），不区分大小写。
输入框 `#captchaInput`，点 canvas 或"换一张"(`#refreshCode`) 会换码。

流程：
1. `browser_take_screenshot` 直接用 CSS 选择器定位（`target: "#captchaCanvas"`, type png）。
   **filename 必须落在 `.ugc-publisher/` 下**（如 `.ugc-publisher/captcha.png`）——该工具的 filename
   相对当前工作目录，写裸文件名会把截图丢到项目根目录污染仓库（实测）；再用 Read 读图；
2. 直接读图识别 4 个字符（注意旋转、粘连、干扰线；候选只在上面的字符集里，拿不准时按字符集排除）。
   必要时可用 `extract_text_from_screenshot` MCP 辅助，但以自己读图为准；
3. `browser_type` 填入 `#captchaInput`，回车（输入框已绑 Enter=确认）或点 `#captchaOk`；
4. 错误时页面自动换码并清空输入、`#captchaErr` 显示"验证码错误"：重新截图识别；
5. **最多重试 4 次**；仍失败就点 canvas 主动换一张清晰的（选噪点少、字符端正的）。

> 识别技巧：字符逐个等宽分布（约每 34px 一个，起始 x≈22），心里给图片画 4 个竖格再辨认。
> 易混对：E/F（看下横：E 三横、F 两横）、C/G（G 右侧有闭合小横）、I/L、2/Z、7/T。
> 2026-09-19 实战：某张首字符 E/F 拿不准硬猜导致错误一次；**易混字符辨不清时直接点 canvas 换一张，比猜错重来更省**。
> 提交后若 `#captchaErr`="验证码错误"，页面会自动换码并清空输入框，重新截图即可。
> 不要试图从 JS 里读答案：code 是闭包内变量，读不到。

## 4. 方式④ 顺序点击

判定：badge 含"顺序点击"；4×2 宫格 8 个 `.seq-cell`，文字 1–8，`data-n` 为数字。
按 1→8 顺序点；点错会清空进度、提示"顺序错误，已重置"。

```js
async () => {
  for (let n = 1; n <= 8; n++) {
    document.querySelector(`.seq-cell[data-n="${n}"]`).click();
    await new Promise(r => setTimeout(r, 60));
  }
  return document.querySelectorAll('.seq-cell.done').length; // 成功时为 8，随后自动关闭
}
```
若返回 <8 且有"顺序错误"提示（有格子没带 done），等错误提示消失后重跑一遍。

## 处置循环建议（evaluate 轮询）

点发布后轮询约 40 秒（每 ~800ms 一次）：
- toast 含"发布成功" → 完成；
- captcha 弹窗在 → 按 badge 分发到上面四种解法；
- auth 弹窗在 → 走 accounts 手册登录/注册，关闭后**重新点 `#publishBtn`**（待发草稿：文本仍在框里、媒体仍在预览里，无需重填；若发现已被清空则从头再发）；
- 都不在且没成功 toast → 看 `#toast` 文本（如"写点什么或添加媒体再发布"），按提示修正。

出现本手册未覆盖的新型阻断弹窗：先快照记录其结构，解决后把类型与解法补进本文件并记 lessons。
