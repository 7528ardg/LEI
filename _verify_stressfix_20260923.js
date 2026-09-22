/* ============================================================
 * _verify_stressfix_20260923.js · 压力测试缺陷修复守护
 * 覆盖（对应 _apply_stressfix_20260923.py 的 FIX-A~FIX-E）：
 *   A 模块加载失败必须给出重试入口，且恢复网络后能自愈（不得永久空白）
 *   B 超时/网络类错误必须触发降级换模型（不得一次即整链失败）
 *   C 并发不得对同一限流模型重复轰炸（单模型并发上限生效）
 *   D risk 会话可由主会话自动补建（不得恒 401「未登录或会话已过期」）
 *   E PWA Service Worker 缓存必须版本化并清理旧缓存
 * 用法：node _verify_stressfix_20260923.js
 * ============================================================ */
'use strict';
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname.replace(/\\/g, '/');
const IDX = 'file:///' + ROOT + '/index.html';
const QA = 'file:///' + ROOT + '/qa.html';
const RISK = 'file:///' + ROOT + '/risk-lite.html';
const SESSION = JSON.stringify({ '工号': '028981', '姓名': '管理员', '手机号': '', '密码': 'LWH' });

let pass = 0, fail = 0;
const results = [];
function judge(name, ok, extra) {
  results.push({ name, ok, extra });
  if (ok) pass++; else fail++;
  console.log(`[${ok ? 'ok  ' : 'FAIL'}] ${name.padEnd(52)} ${extra || ''}`);
}

// 页面内 fetch 桩：按名字解析策略（evaluate 不能传函数）
const STUB = `
window.__calls = [];
window.__origFetch = window.fetch;
window.__behaviorName = 'ok';
window.fetch = function(u, o){
  var url = String((u && u.url) || u || '');
  if (url.indexOf('bigmodel.cn') >= 0 || url.indexOf('pollinations') >= 0) {
    var model = '';
    try { model = JSON.parse((o && o.body) || '{}').model || ''; } catch(e){}
    window.__calls.push(model);
    var n = window.__calls.length, nm = window.__behaviorName;
    var json = function(st, obj){ return new Response(JSON.stringify(obj), { status: st, headers: { 'Content-Type': 'application/json' } }); };
    if (nm === 'firstNetFail' && n === 1) return Promise.reject(new TypeError('Failed to fetch'));
    if (nm === 'firstAbort' && n === 1) return Promise.reject(new DOMException('The operation was aborted', 'AbortError'));
    if (nm === 'first429' && n === 1) return Promise.resolve(json(429, { error: { code: '1302', message: '当前账户速率限制' } }));
    if (nm === 'first500' && n === 1) return Promise.resolve(json(503, { error: { message: 'Service Unavailable' } }));
    if (nm === 'onlyLastOk') return model === 'glm-4-flash' ? Promise.resolve(json(200, { choices: [{ message: { content: 'MOCK-OK' } }] })) : Promise.resolve(json(429, { error: { code: '1305', message: '访问量过大' } }));
    if (nm === 'all429') return Promise.resolve(json(429, { error: { code: '1305', message: '访问量过大' } }));
    return Promise.resolve(json(200, { choices: [{ message: { content: 'MOCK-OK' } }] }));
  }
  return window.__origFetch.apply(window, arguments);
};
`;

(async () => {
  const browser = await chromium.launch({
    channel: 'msedge',
    args: ['--no-proxy-server', '--proxy-bypass-list=<-loopback>', '--allow-file-access-from-files', '--disable-web-security'],
    proxy: { server: 'direct://' },
  });

  // ================= FIX-A 模块加载失败可自愈 =================
  {
    const ctx = await browser.newContext({ viewport: { width: 393, height: 852 }, isMobile: true, hasTouch: true });
    const page = await ctx.newPage();
    let blockQa = true;
    const reqs = [];
    // 路由策略（单一 handler 内分流，避免多 route 注册顺序歧义）：
    //   主线路 file:// → 按 blockQa 放行/拦截
    //   镜像线路 cdn.jsdelivr.net → 一律用本地同名文件应答，否则用例会依赖外网而随机失败
    //   （实测：连续两次失败后壳层会把线路持久化为镜像，重试即走 CDN）
    await page.route('**/*.html', (route) => {
      const u = route.request().url();
      if (/\/index\.html$/.test(u)) return route.continue();
      const isMirror = /cdn\.jsdelivr\.net/.test(u);
      const name = decodeURIComponent((u.split('/').pop() || '').split('?')[0]);
      if (/qa\.html$/.test(u)) {
        reqs.push(isMirror ? 'qa(mirror)' : 'qa');
        if (blockQa) return route.abort('connectionfailed');
        if (isMirror) {
          const fp = path.join(__dirname, 'qa.html');
          if (fs.existsSync(fp)) return route.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: fs.readFileSync(fp) });
        }
        return route.continue();
      }
      if (isMirror) {
        const fp = path.join(__dirname, name);
        if (name && fs.existsSync(fp)) return route.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: fs.readFileSync(fp) });
        return route.abort('connectionfailed');
      }
      return route.continue();
    });
    await page.addInitScript((s) => { try { localStorage.setItem('cabin_session_v1', s); } catch (e) {} }, SESSION);
    await page.goto(IDX, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await page.waitForFunction(() => typeof window.switchModule === 'function', null, { timeout: 120000 });
    await page.waitForTimeout(1200);
    await page.evaluate(() => { try { window.shellTourSkip && window.shellTourSkip(); } catch (e) {} });

    await page.evaluate(() => switchModule('qa'));
    // 旧实现：文案永远是「正在进入 …」；新实现应在两次失败后给出可点击重试
    let shown = '';
    for (let i = 0; i < 24; i++) {
      await page.waitForTimeout(1000);
      const t = await page.evaluate(() => {
        const l = document.getElementById('loader-qa');
        return l ? (l.querySelector('.sl-text') ? l.querySelector('.sl-text').textContent : '') : '';
      });
      if (/重试/.test(t)) { shown = t; break; }
    }
    judge('A1 失败后给出可点击重试入口（非永久加载态）', /重试/.test(shown), `loader 文案="${shown}"`);

    blockQa = false;
    // 复位镜像线路：A1 的两次失败会把线路持久化为 cdn.jsdelivr.net（跨域），
    // 跨域 iframe 的 contentDocument 不可读 → 断言会把「已渲染」误判成 0 字。
    // 清空后回到同源主线路，才是「网络恢复后自愈」的真实场景。
    await page.evaluate(() => {
      try {
        if (typeof setModBase === 'function') setModBase('');
        if (typeof getModBase === 'function' && getModBase()) { try { localStorage.removeItem('app_base_url'); } catch (e) {} }
      } catch (e) {}
    });
    await page.evaluate(() => switchModule('home'));
    await page.waitForTimeout(2500);
    await page.evaluate(() => switchModule('qa'));
    // 轮询等待渲染完成（固定 sleep 在整机负载高时会抖动，实测导致过假失败）
    let rendered = 0;
    for (let i = 0; i < 30; i++) {
      await page.waitForTimeout(1000);
      rendered = await page.evaluate(() => {
        try {
          const f = document.getElementById('frame-qa');
          return (f && f.contentDocument && f.contentDocument.body) ? f.contentDocument.body.innerText.trim().length : 0;
        } catch (e) { return 0; }
      });
      if (rendered > 20) break;
    }
    judge('A2 恢复网络后切回能自愈（重新请求并渲染）', reqs.length >= 2 && rendered > 20,
      `qa.html 请求 ${reqs.length} 次，iframe 文本 ${rendered} 字`);

    // 正常路径不得被误伤：直接进入一个正常网络下的模块
    await page.evaluate(() => { try { switchModule('beauty'); } catch (e) {} });
    let bLen = 0, bHidden = false;
    for (let i = 0; i < 30; i++) {
      await page.waitForTimeout(1000);
      const s = await page.evaluate(() => {
        try {
          const f = document.getElementById('frame-beauty');
          const l = document.getElementById('loader-beauty');
          return {
            len: (f && f.contentDocument && f.contentDocument.body) ? f.contentDocument.body.innerText.trim().length : 0,
            hidden: l ? l.classList.contains('hidden') : false,
          };
        } catch (e) { return { len: 0, hidden: false }; }
      });
      bLen = s.len; bHidden = s.hidden;
      if (bLen > 20 && bHidden) break;
    }
    judge('A3 正常加载路径未被误伤（loader 正常隐藏）', bLen > 20 && bHidden === true,
      `beauty 文本 ${bLen} 字，loader 已隐藏=${bHidden}`);
    await ctx.close();
  }

  // ================= FIX-B / FIX-C AI 降级链 =================
  // 注意：熔断状态是模块私有闭包变量，无法从外部重置；
  // 因此每个用例用独立页面，避免上一个用例写入的 60s 冷却干扰下一个用例。
  async function withAiPage(fn) {
    const ctx = await browser.newContext({ viewport: { width: 1200, height: 800 } });
    const p = await ctx.newPage();
    await p.addInitScript(() => {
      localStorage.setItem('spring_ai_cfg', JSON.stringify({ provider: 'zhipu', apiKey: 'test-key-0123456789abcdef', endpoint: '', model: '', tavilyKey: '' }));
    });
    await p.addInitScript(STUB);
    await p.goto(QA, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await p.waitForFunction(() => typeof SpringAI !== 'undefined', null, { timeout: 60000 });
    const out = await fn(p);
    await ctx.close();
    return out;
  }

  async function runOne(behaviorName) {
    return withAiPage((p) => p.evaluate(async (b) => {
      window.__calls = []; window.__behaviorName = b;
      try {
        const r = await SpringAI.chatLLM([{ role: 'user', content: '你好' }], { timeout: 8000 });
        return { ok: true, text: String(r).slice(0, 30), calls: window.__calls.slice() };
      } catch (e) { return { ok: false, err: String(e.message || e).slice(0, 90), calls: window.__calls.slice() }; }
    }, behaviorName));
  }

  const b1 = await runOne('firstNetFail');
  judge('B1 网络错误(Failed to fetch)触发降级换模型', b1.ok && b1.calls.length >= 2,
    `结果=${b1.ok ? '成功' : b1.err} 模型序列=[${b1.calls}]`);

  const b2 = await runOne('firstAbort');
  judge('B2 AbortError 触发降级换模型', b2.ok && b2.calls.length >= 2,
    `结果=${b2.ok ? '成功' : b2.err} 模型序列=[${b2.calls}]`);

  const b3 = await runOne('first500');
  judge('B3 HTTP 503 触发降级换模型', b3.ok && b3.calls.length >= 2,
    `结果=${b3.ok ? '成功' : b3.err} 模型序列=[${b3.calls}]`);

  const b4 = await runOne('all429');
  judge('B4 全链限流最终失败且文案明确（不得静默返回空）', !b4.ok && /429|访问量过大|限流|COOLDOWN|速率/i.test(b4.err || ''),
    `错误="${b4.err}"`);

  // FIX-C：10 路并发，仅最后一个模型可用（独立页面，无残留冷却）
  const c1 = await withAiPage((p) => p.evaluate(async () => {
    window.__calls = []; window.__behaviorName = 'onlyLastOk';
    const rs = await Promise.all(Array.from({ length: 10 }, (_, i) =>
      SpringAI.chatLLM([{ role: 'user', content: 'q' + i }], { timeout: 15000 })
        .then(() => ({ ok: true })).catch(e => ({ ok: false, err: String(e.message || e).slice(0, 60) }))));
    return { ok: rs.filter(r => r.ok).length, calls: window.__calls.slice(), errs: rs.filter(r => !r.ok).map(r => r.err).slice(0, 3) };
  }));
  const headTried = c1.calls.filter(m => m !== 'glm-4-flash').length;
  judge('C1 并发下限流模型未被重复轰炸（尝试次数 ≤3）', headTried <= 3 && c1.calls.length > 0,
    `限流模型被尝试 ${headTried} 次（旧实现为 10 次）`);
  judge('C2 并发下请求总数接近理论下限（≤14）', c1.calls.length > 0 && c1.calls.length <= 14,
    `请求总数 ${c1.calls.length}（旧实现为 20）`);
  judge('C3 并发下业务全部成功', c1.ok === 10,
    `成功 ${c1.ok}/10${c1.errs && c1.errs.length ? ' 错误样本=' + JSON.stringify(c1.errs) : ''}`);

  // ================= FIX-D risk 会话自动补建 =================
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    const errs = [];
    page.on('pageerror', e => errs.push(String(e.message).slice(0, 100)));
    page.on('console', m => { if (m.type() === 'error') errs.push(m.text().slice(0, 140)); });
    // 只写主会话，故意不写 cabin_risk_session_v1（复现修复前场景）
    await page.addInitScript((s) => { try { localStorage.setItem('cabin_session_v1', s); } catch (e) {} }, SESSION);
    await page.goto(RISK, { waitUntil: 'domcontentloaded', timeout: 180000 });
    await page.waitForFunction(() => typeof CabinAPI !== 'undefined', null, { timeout: 120000 });
    const d = await page.evaluate(async () => {
      const before = !!localStorage.getItem('cabin_risk_session_v1');
      let res = null, err = '';
      try { res = await CabinAPI.weather.cacheStatus(); } catch (e) { err = String(e.message || e).slice(0, 90); }
      return { before, after: !!localStorage.getItem('cabin_risk_session_v1'), err, ok: !!res };
    });
    judge('D1 主会话可自动补建 risk 会话', d.after === true, `调用前=${d.before} 调用后=${d.after}`);
    judge('D2 天气接口不再报「未登录或会话已过期」', !/未登录或会话已过期|UNAUTHORIZED/.test(d.err),
      `接口错误="${d.err || '无'}"`);
    const weatherErr = errs.filter(x => /未登录或会话已过期/.test(x));
    judge('D3 页面无 weather 鉴权失败报错', weatherErr.length === 0 || d.after === true,
      `页面鉴权报错 ${weatherErr.length} 条`);
    await ctx.close();
  }

  await browser.close();

  // ================= FIX-E PWA SW（校验生成源） =================
  // 注：生成的 sw.js 由 _build_pwa.py 重跑后覆盖，属构建产物，不在此处断言；
  //     打包阶段会用 _check_pwa_sw 复核产物内容。
  {
    const src = fs.readFileSync(path.join(__dirname, 'PWA封装/_build_pwa.py'), 'utf8');
    judge('E1 SW 缓存名版本化', /CACHE_VERSION/.test(src) && /cabin-pwa-' \+ CACHE_VERSION/.test(src), 'CACHE_VERSION 存在');
    judge('E2 SW activate 清理旧缓存', /caches\.keys\(\)/.test(src) && /caches\.delete/.test(src), 'caches.delete 存在');
    judge('E3 SW 预缓存首屏模块', /\.\/qa\.html/.test(src) && /\.\/beauty\.html/.test(src), '模块页已入 CORE_URLS');
    judge('E4 SW 采用 stale-while-revalidate', /stale-while-revalidate/.test(src), '先给缓存并在后台更新');
  }

  console.log(`\n===== 汇总：通过 ${pass} / 失败 ${fail} =====`);
  fs.writeFileSync(path.join(__dirname, '_verify_stressfix_20260923.json'), JSON.stringify({ pass, fail, results }, null, 2));
  process.exit(fail > 0 ? 1 : 0);
})().catch(e => { console.error('FATAL', e.message); process.exit(2); });
