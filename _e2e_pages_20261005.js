/* 补测：离线完整版 + spring-assistant 单文件自包含性+ 二次登录问题 */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const BASE = 'http://127.0.0.1:8899/';
const OUT = path.join(__dirname, '__e2e_out');
const log = (...a) => console.log(...a);

const PAGES = [
  { f: '客舱小助手（离线完整版）.html', name: '离线完整版', shot: 'p-offline.png' },
  { f: 'spring-assistant.html', name: '南昌分队小助手', shot: 'p-spring.png' },
  { f: 'nc/index.html', name: 'nc/index', shot: 'p-nc.png' },
];

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const out = [];
  for (const p of PAGES) {
    const ctx = await browser.newContext({ viewport: { width: 414, height: 896 } });
    const page = await ctx.newPage();
    const errs = [];
    const netfail = [];
    page.on('pageerror', e => errs.push(String(e).slice(0, 150)));
    page.on('console', m => { if (m.type() === 'error') errs.push('C:' + m.text().slice(0, 150)); });
    page.on('requestfailed', r => netfail.push(r.url().slice(-60) + ' :: ' + (r.failure() || {}).errorText));
    let ok = true, info = {};
    try {
      await page.goto(BASE + encodeURIComponent(p.f), { waitUntil: 'domcontentloaded', timeout: 90000 });
      await page.waitForTimeout(4000);
      info = await page.evaluate(() => {
        const b = document.body;
        return {
          title: document.title,
          textLen: (b.innerText || '').replace(/\s+/g, ' ').trim().length,
          sample: (b.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 220),
          domNodes: b.querySelectorAll('*').length,
          hasLogin: !!document.querySelector('.auth-overlay:not([style*="display:none"]), .auth-btn, #afId, .login-box'),
          loginOverlay: !!document.querySelector('.auth-overlay'),
          session: localStorage.getItem('cabin_session_v1'),
        };
      });
      await page.screenshot({ path: path.join(OUT, p.shot) });
    } catch (e) { ok = false; info = { err: String(e).slice(0, 200) }; }
    const r = { name: p.name, file: p.f, ok, ...info, errs: errs.slice(0, 5), netfail: netfail.slice(0, 5) };
    out.push(r);
    log(`\n=== ${p.name} (${p.f})`);
    log('  loaded=', ok, 'title=', info.title, 'textLen=', info.textLen, 'nodes=', info.domNodes);
    log('  hasLoginUI=', info.hasLogin, 'loginOverlay=', info.loginOverlay, 'session=', info.session ? 'YES' : 'no');
    log('  sample=', (info.sample || info.err || '').slice(0, 180));
    if (r.errs.length) log('  ERRS:', JSON.stringify(r.errs));
    if (r.netfail.length) log('  NETFAIL:', JSON.stringify(r.netfail));
    await ctx.close();
  }
  fs.writeFileSync(path.join(OUT, 'result_pages.json'), JSON.stringify(out, null, 2), 'utf8');
  await browser.close();
  log('\nDONE');
  process.exitCode = 0;
})().catch(e => { console.error('FATAL', e); process.exitCode = 1; });
