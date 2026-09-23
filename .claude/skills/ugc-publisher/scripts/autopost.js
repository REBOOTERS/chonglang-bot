// ugc-publisher 一键发布脚本（快速通道）
// 通过 browser_run_code_unsafe 的 filename 加载；本文件必须整体是一个 async (page) => { ... } 表达式，
// 末尾不要加分号。沙箱内无 require/process，配置经本机静态服务器用 page.request 读取。
// 先写 .ugc-publisher/next-post.json：
//   { "step": "publish",   "text": "文案", "images": ["/abs/a.webp"], "videos": [], "username": "可选" }
//   { "step": "solveText", "code": "EFAT" }   // 字符验证码识图后回填
//   { "step": "dryRun" }                       // 鉴权+填写+上传+预览校验，不发布（reload 丢弃草稿）
// 全新注册用户（凭据库与页面均无 username）时另需 "password"（必填）/"nick"（缺省取 username）。
async (page) => {
  const BASE = 'http://localhost:8765';
  const loadJson = async p => {
    const r = await page.request.get(BASE + p);
    if (!r.ok()) return { __http: r.status() };
    return r.json();
  };
  const cfg = await loadJson('/.ugc-publisher/next-post.json');
  if (cfg.__http) return { ok: false, stage: 'config', err: 'next-post.json HTTP ' + cfg.__http };
  // 注意：MCP 外层沙箱已无 setTimeout/setInterval（2026-09-22 起实测），用 Playwright 自带等待。
  const sleep = ms => page.waitForTimeout(ms);

  const st = () => page.evaluate(() => ({
    session: localStorage.getItem('wb_sim_session'),
    users: Object.keys(JSON.parse(localStorage.getItem('wb_sim_users') || '{}')),
    auth: document.getElementById('authOverlay').classList.contains('show'),
    authErr: document.getElementById('authErr').textContent,
    captcha: document.getElementById('captchaOverlay').classList.contains('show'),
    badge: document.getElementById('captchaBadge').textContent,
  }));

  // —— 鉴权：会话直用；指定不同账号先退出；库中有→登录（页面缺用户则同身份重注册）；库中无→全新注册 ——
  async function authenticate() {
    let s = await st();
    // 指定的账号与当前会话不同：先退出，再按未登录处理
    if (s.session && cfg.username && s.session !== cfg.username) {
      await page.locator('#logoutBtn').click();
      await page.waitForFunction(() => !localStorage.getItem('wb_sim_session'), null, { timeout: 5000 });
      s = await st();
    }
    if (s.session) return { via: 'session' };
    const store = await loadJson('/.ugc-publisher/accounts.json');
    if (store.__http === 404) return { fail: 'NO_ACCOUNTS_FILE' };
    if (store.__http) return { fail: 'ACCOUNTS_HTTP', status: store.__http };
    const wantUser = cfg.username || store.default;
    const a = store.accounts.find(x => x.username === wantUser);

    // 凭据库无此账号：页面里也没有 → 用该用户名全新注册（密码/昵称由 cfg.password/cfg.nick 提供）；
    // 页面里已存在该用户名 → 我们没有密码，不能登录也不能重注册，返回让用户处理。
    if (!a) {
      if (s.users.includes(wantUser)) return { fail: 'ACCOUNT_EXISTS_NO_PASSWORD', username: wantUser };
      if (!cfg.password) return { fail: 'NO_PASSWORD_FOR_NEW_ACCOUNT' };
      const nick = cfg.nick || wantUser;
      await page.locator('#openReg').click();
      await page.waitForSelector('#authOverlay.show', { timeout: 3000 });
      await page.locator('#regNick').fill(nick);
      await page.locator('#authUser').fill(wantUser);
      await page.locator('#authPass').fill(cfg.password);
      await page.locator('#authSubmit').click();
      await sleep(400);
      s = await st();
      if (s.session) return { via: 'register', creds: { username: wantUser, password: cfg.password, nick } };
      return { fail: 'REGISTER_FAILED', err: s.authErr };
    }

    await page.locator('#openLogin').click();
    await page.waitForSelector('#authOverlay.show', { timeout: 3000 });
    await page.locator('#authUser').fill(a.username);
    await page.locator('#authPass').fill(a.password);
    await page.locator('#authSubmit').click();
    await sleep(400);
    s = await st();
    if (s.session) return { via: 'login' };

    if (s.authErr.includes('用户名或密码错误')) {
      await page.locator('#authSwitchLink').click();
      await page.locator('#regNick').fill(a.nick || a.username);
      await page.locator('#authSubmit').click();
      await sleep(400);
      s = await st();
      if (s.session) return { via: 're-register' };
      return { fail: 'REGISTER_FAILED', err: s.authErr };
    }
    return { fail: 'LOGIN_FAILED', err: s.authErr };
  }

  // —— 三种可全自动解决的验证码 ——
  async function solveSlider() {
    const b = await page.evaluate(() => {
      const track = document.getElementById('sliderTrack');
      const knob = document.getElementById('sliderKnob');
      const t = track.getBoundingClientRect(), k = knob.getBoundingClientRect();
      return { kx: k.left + k.width / 2, ky: k.top + k.height / 2, max: t.width - k.width };
    });
    await page.mouse.move(b.kx, b.ky);
    await page.mouse.down();
    for (let i = 1; i <= 25; i++) {
      await page.mouse.move(b.kx + b.max * i / 25, b.ky, { steps: 2 });
      await sleep(25);
    }
    await page.mouse.up();
    await sleep(700);
  }

  async function solvePick() {
    const r = await page.evaluate(() => {
      const target = document.querySelector('#captchaDesc').textContent.match(/「(.+?)」/)[1];
      document.querySelectorAll('.pick-cell').forEach(c => {
        if (c.dataset.t === target && !c.classList.contains('selected')) c.click();
      });
      return { target, n: document.querySelectorAll('.pick-cell.selected').length };
    });
    await page.locator('#captchaOk').click();
    await sleep(500);
    return r;
  }

  async function solveSequence() {
    await page.evaluate(async () => {
      for (let n = 1; n <= 8; n++) {
        document.querySelector(`.seq-cell[data-n="${n}"]`).click();
        await new Promise(r => setTimeout(r, 60));
      }
    });
    await sleep(600);
  }

  const nMedia = (cfg.images || []).length + (cfg.videos || []).length;
  const isPublished = () => page.evaluate(() => {
    const e = window.__lastPost;
    if (!e) return false;
    const p = document.querySelector('#feed .post');
    if (!p) return false;
    const body = p.querySelector('.post-body').textContent;
    const media = p.querySelectorAll('.post-media img, .post-media video').length;
    return body.startsWith(e.head) && media === e.n;
  });

  const postInfo = () => page.evaluate(() => {
    const p = document.querySelector('#feed .post');
    return p ? {
      nick: p.querySelector('.post-name').textContent,
      bodyStart: p.querySelector('.post-body').textContent.slice(0, 24),
      media: p.querySelectorAll('.post-media img, .post-media video').length,
    } : null;
  });

  // 发布后的统一处置循环；③ 字符码需要模型识图，抛出 need:textCaptcha
  async function afterPublish(seen, attempts) {
    const deadline = Date.now() + 45000;
    while (Date.now() < deadline) {
      if (await isPublished()) return { ok: true, captchas: seen, post: await postInfo() };
      const s = await st();
      if (s.auth) return { ok: false, need: 'authOverlay', state: s };
      if (s.captcha) {
        if (s.badge.includes('方式①')) {
          if ((attempts.slider = (attempts.slider || 0) + 1) > 3) return { ok: false, need: 'manual', type: 'slider' };
          seen.push('slider'); await solveSlider();
        } else if (s.badge.includes('方式②')) {
          if ((attempts.pick = (attempts.pick || 0) + 1) > 2) return { ok: false, need: 'manual', type: 'imagePick' };
          seen.push('imagePick'); await solvePick();
        } else if (s.badge.includes('方式④')) {
          if ((attempts.seq = (attempts.seq || 0) + 1) > 2) return { ok: false, need: 'manual', type: 'sequence' };
          seen.push('sequence'); await solveSequence();
        } else if (s.badge.includes('方式③')) {
          seen.push('textCode');
          return { ok: false, need: 'textCaptcha' };
        }
      }
      await sleep(250);
    }
    return { ok: false, need: 'timeout' };
  }

  // —— 主流程 ——
  if (!page.url().includes('ugc-index.html')) {
    await page.goto(BASE + '/ugc-index.html', { waitUntil: 'domcontentloaded' });
  }

  const auth = await authenticate();
  if (auth.fail) return { ok: false, stage: 'auth', ...auth };

  if (cfg.step === 'solveText') {
    await page.locator('#captchaInput').fill(cfg.code || '');
    await page.locator('#captchaOk').click();
    return await afterPublish(['textCode(retry)'], {});
  }

  // 清空可能残留的预览（中断的上次运行/手动上传），否则新旧累加导致数量校验失败。
  // .rm 点击会整体重渲染预览，必须逐个点（每次重新查询），批量点只有第一个生效。
  let leftovers = await page.evaluate(() => document.querySelectorAll('#mediaPreview .media-item').length);
  while (leftovers > 0) {
    await page.locator('#mediaPreview .rm').first().click();
    const before = leftovers;
    await page.waitForFunction(n => document.querySelectorAll('#mediaPreview .media-item').length === n, before - 1, { timeout: 3000 });
    leftovers--;
  }

  // 填写文案
  await page.locator('#postInput').fill(cfg.text || '');

  // 上传图片：直接给隐藏的 #imgInput setFiles（Playwright 对 input[type=file] 不要求可见）。
  // 不要点 #imgBtn 走 filechooser——MCP 层会拦截 chooser 弹原生框、打断脚本。
  if ((cfg.images || []).length) {
    await page.setInputFiles('#imgInput', cfg.images);
    await page.waitForFunction(
      n => document.querySelectorAll('#mediaPreview .media-item').length === n,
      cfg.images.length, { timeout: 15000 }
    );
  }
  // 上传视频：同理直接 setInputFiles #vidInput
  if ((cfg.videos || []).length) {
    await page.setInputFiles('#vidInput', cfg.videos);
    await page.waitForFunction(
      n => document.querySelectorAll('#mediaPreview .media-item').length === n,
      nMedia, { timeout: 30000 }
    );
  }

  if (cfg.step === 'dryRun') {
    const preview = await page.evaluate(() => document.querySelectorAll('#mediaPreview .media-item').length);
    await page.reload(); // 丢弃草稿，不发布
    return { ok: true, dryRun: true, via: auth.via, preview };
  }

  // 缓存成功判定依据；solveText 重跑时配置里没有 text/media，从 window 取
  await page.evaluate(({ head, n }) => { window.__lastPost = { head, n }; },
    { head: cfg.text.slice(0, 16), n: nMedia });

  await page.locator('#publishBtn').click();
  return await afterPublish([], {});
}
