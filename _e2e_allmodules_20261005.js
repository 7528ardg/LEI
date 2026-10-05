/* 全站逐模块 E2E v3（2026-10-05）
   v2 暴露两个问题，本版修正：
   1) 新手引导浮层（1/6 你问我答）在模块切换后弹出 → 遮挡页面，必须先点「跳过」
   2) performance / risk 是 ADMIN_ONLY_MODS，普通账号被门禁 → 需管理员账号复测
   本版：普通账号跑全量12 模块 + 管理员账号专测 performance/risk */
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const BASE = 'http://127.0.0.1:8899/index.html';
const OUT = path.join(__dirname, '__e2e_out');
fs.mkdirSync(OUT, { recursive: true });

const MODULES = [
  { id: 'qa', name: '你问我答', kw: ['你问我答', '提问', '五库', '问'] },
  { id: 'quiz', name: '培训考核', kw: ['题', '考试', '练习', '刷题'] },
  { id: 'performance', name: '绩效管理', kw: ['绩效', '飞行', '月'], admin: true },
  { id: 'beauty', name: '美妆话术', kw: ['话术', '美妆', '品牌'] },
  { id: 'daily', name: '日常问题', kw: ['日常', '问题'] },
  { id: 'manual', name: '手册奖惩', kw: ['手册', '奖惩'] },
  { id: 'home', name: 'CC之家', kw: ['CC', '之家', '角色'] },
  { id: 'medical', name: '医疗急救', kw: ['医疗', '急救'] },
  { id: 'risk', name: '风险预警', kw: ['风险', '预警'], admin: true },
  { id: 'report', name: '事件报告', kw: ['报告', '事件'] },
  { id: 'kbadmin', name: '库管理', kw: ['库', '管理'] },
  { id: 'issues', name: '问题反馈', kw: ['反馈', '问题'] },
];

const log = (...a) => console.log(...a);

async function dismissTour(page) {
  // 新手引导：优先点「跳过」(#tourSkip)，否则走完 6 步
  for (let k = 0; k < 10; k++) {
    const skip = await page.$('#tourSkip');
    if (skip && await skip.isVisible().catch(() => false)) {
      await skip.click({ timeout: 3000 }).catch(() => {});
      await page.waitForTimeout(600); continue;
    }
    const next = await page.$('#tourNext, .tour-nav button.tour-next');
    if (next && await next.isVisible().catch(() => false)) {
      await next.click({ timeout: 3000 }).catch(() => {});
      await page.waitForTimeout(500); continue;
    }
    break;
  }
  await page.waitForTimeout(400);
}

async function login(page, acc, pwd) {
  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(1500);
  await page.evaluate(() => localStorage.clear());
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1800);
  await page.waitForSelector('#afId', { timeout: 10000 });
  await page.fill('#afId', acc);
  await page.fill('#afPwd', pwd);
  await page.click('.auth-btn');
  await page.waitForTimeout(2500);
  return page.evaluate(() => {
    const ov = document.querySelector('.auth-overlay');
    const s = localStorage.getItem('cabin_session_v1');
    let role = null;
    try { role = JSON.parse(s || '{}').role; } catch (e) {}
    return {
      session: !!s, role,
      overlayGone: !ov || getComputedStyle(ov).display === 'none' || !ov.offsetHeight,
      authErr: ((document.querySelector('#authErr') || {}).textContent || '').trim(),
      shownRole: ((document.getElementById('userRole') || {}).textContent || '').trim(),
    };
  });
}

async function probe(page, id) {
  let info = {};
  for (let i = 0; i < 40; i++) {
    await page.waitForTimeout(500);
    info = await page.evaluate((mid) => {
      const wrap = document.getElementById('wrap-' + mid);
      const fr = document.getElementById('frame-' + mid);
      let rs = null, txt = '', bodyH = 0, loader = '', nodes = 0, hasCanvas = false, denied = '';
      try {
        const d = fr.contentDocument;
        if (d) {
          rs = d.readyState;
          bodyH = d.body ? d.body.scrollHeight : 0;
          nodes = d.body ? d.body.querySelectorAll('*').length : 0;
          txt = (d.body ? (d.body.innerText || '') : '').replace(/\s+/g, ' ').trim();
          hasCanvas = !!(d.querySelector('canvas'));
          const le = d.querySelector('.sl-text');
          loader = le ? (le.textContent || '').trim() : '';
          if (/权限|管理员|无权限|禁止|登录/.test(txt.slice(0, 400))) denied = txt.slice(0, 200);
        }
      } catch (e) { rs = 'X:' + String(e).slice(0, 50); }
      return { active: !!(wrap && wrap.classList.contains('active')), readyState: rs, textLen: txt.length, sample: txt.slice(0, 500), bodyH, nodes, hasCanvas, loaderText: loader, denied };
    }, id);
    if (info.readyState === 'complete' && info.textLen > 20) break;
  }
  return info;
}

(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const all = {};

  // =================普通账号 002191 =================
  {
    const ctx = await browser.newContext({ viewport: { width: 414, height: 896 } });
    const page = await ctx.newPage();
    const errs = [];
    page.on('pageerror', e => errs.push('PAGEERROR: ' + String(e).slice(0, 160)));
    page.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text().slice(0, 160)); });

    const lg = await login(page, '002191', 'GJY');
    log('LOGIN(user 002191):', JSON.stringify(lg));
    await page.screenshot({ path: path.join(OUT, 'u-00-login.png') });
    await dismissTour(page);
    await page.screenshot({ path: path.join(OUT, 'u-01-after-tour.png') });

    const res = [];
    for (const m of MODULES) {
      const mark = errs.length;
      let via = 'none';
      for (const sel of [`.mod-tab[data-mod="${m.id}"]`, `[data-mtab="${m.id}"]`]) {
        const el = await page.$(sel);
        if (!el) continue;
        const vis = await el.isVisible().catch(() => false);
        if (!vis) continue;
        await el.click({ timeout: 6000, force: true }).then(() => { via = 'click'; }).catch(() => {});
        if (via === 'click') break;
      }
      if (via !== 'click') {
        const r = await page.evaluate(id => { try { switchModule(id); return 'api'; } catch (e) { return 'x'; } }, m.id);
        via = (r === 'api') ? 'api' : 'fail';
      }
      await dismissTour(page);   // 模块内可能再弹一次
      const info = await probe(page, m.id);
      await page.screenshot({ path: path.join(OUT, `u-${m.id}.png`) }).catch(() => {});
      const kw = m.kw.some(k => (info.sample || '').includes(k));
      const myErrs = errs.slice(mark).filter(e => !e.startsWith('NOTE:'));
      const r = {
        id: m.id, name: m.name, admin: !!m.admin, via, kw,
        active: info.active, rs: String(info.readyState).slice(0, 12),
        textLen: info.textLen, domNodes: info.nodes, bodyH: info.bodyH,
        hasCanvas: !!info.hasCanvas, loaderText: info.loaderText,
        deniedHint: info.denied || '', sample: (info.sample || '').slice(0, 220),
        errs: myErrs.slice(0, 5),
      };
      res.push(r);
      log(`  [${m.id}] via=${via} active=${info.active} rs=${r.rs} len=${r.textLen} nodes=${r.domNodes} h=${r.bodyH} kw=${kw} err=${myErrs.length}`);
      if (info.denied) log('DENIED-TEXT:', info.denied.slice(0, 120));
      myErrs.slice(0, 2).forEach(e => log('     !', e.slice(0, 140)));
    }
    all.user = { login: lg, modules: res };
    fs.writeFileSync(path.join(OUT, 'result_user.json'), JSON.stringify(all.user, null, 2), 'utf8');
    await ctx.close();
  }

  // ================= 管理员 028981 =================
  {
    const ctx = await browser.newContext({ viewport: { width: 414, height: 896 } });
    const page = await ctx.newPage();
    const errs = [];
    page.on('pageerror', e => errs.push('PAGEERROR: ' + String(e).slice(0, 160)));
    page.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text().slice(0, 160)); });
    const lg = await login(page, '028981', 'LWH');
    log('\nLOGIN(admin 028981):', JSON.stringify(lg));
    await dismissTour(page);
    const res = [];
    for (const m of MODULES.filter(x => x.admin)) {
      const mark = errs.length;
      let via = 'none';
      const el = await page.$(`.mod-tab[data-mod="${m.id}"]`);
      if (el && await el.isVisible().catch(() => false)) {
        await el.click({ timeout: 6000, force: true }).then(() => { via = 'click'; }).catch(() => {});
      }
      if (via !== 'click') {
        const r = await page.evaluate(id => { try { switchModule(id); return 'api'; } catch (e) { return 'x'; } }, m.id);
        via = (r === 'api') ? 'api' : 'fail';
      }
      await dismissTour(page);
      const info = await probe(page, m.id);
      await page.screenshot({ path: path.join(OUT, `a-${m.id}.png`) }).catch(() => {});
      const kw = m.kw.some(k => (info.sample || '').includes(k));
      const myErrs = errs.slice(mark);
      const r = {
        id: m.id, name: m.name, via, kw,
        active: info.active, rs: String(info.readyState).slice(0, 12),
        textLen: info.textLen, domNodes: info.nodes, bodyH: info.bodyH,
        hasCanvas: !!info.hasCanvas, loaderText: info.loaderText,
        sample: (info.sample || '').slice(0, 240), errs: myErrs.slice(0, 5),
      };
      res.push(r);
      log(`  [${m.id}] via=${via} active=${info.active} rs=${r.rs} len=${r.textLen} nodes=${r.domNodes} h=${r.bodyH} canvas=${r.hasCanvas} kw=${kw} err=${myErrs.length}`);
      myErrs.slice(0, 3).forEach(e => log('     !', e.slice(0, 150)));
    }
    all.admin = { login: lg, modules: res };
    fs.writeFileSync(path.join(OUT, 'result_admin.json'), JSON.stringify(all.admin, null, 2), 'utf8');
    await ctx.close();
  }

  await browser.close();
  log('\nDONE');
  process.exitCode = 0;
})().catch(e => { console.error('FATAL', e); process.exitCode = 1; });
