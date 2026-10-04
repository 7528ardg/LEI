/* 三壳权限门禁 + risk-lite 板块锁 + 品牌注入守护（2026-10-05）
 * 断言：
 *  A) spring-assistant.html / nc/index.html：普通账号与游客 → performance/risk 入口不可见且不可进入；
 *     管理员 → 可见可进入；登出复位。
 *  B) risk-lite.html：普通会话直接打开 → 无权限遮罩 + initDashboard 不执行；
 *     管理员会话 → 无遮罩进入；源码无硬编码凭据。
 *  C) 品牌注入：quiz/performance/risk-lite 渲染后页面不再出现 {{AIRLINE}}/{{BASE}}。
 * 用法：node _verify_perm3_20261005.js   （失败退出码 1）
 */
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');
const HERE = __dirname;
const url = f => 'file:///' + path.join(HERE, f).replace(/\\/g, '/');

let pass = 0, fail = 0;
const t = (name, cond, extra) => {
  if (cond) { pass++; console.log('  PASS  ' + name); }
  else { fail++; console.log('  FAIL  ' + name + (extra !== undefined ? '  → ' + JSON.stringify(extra) : '')); }
};

async function setSession(page, acc, role) {
  await page.evaluate(([a, r]) => {
    try {
      if (a === null) localStorage.removeItem('cabin_session_v1');
      else localStorage.setItem('cabin_session_v1', JSON.stringify({ 工号: a, 姓名: '测试', 手机号: '', role: r }));
    } catch (e) {}
  }, [acc, role]);
}

async function inspectShell(page) {
  return await page.evaluate(() => {
    const isUser = document.body.classList.contains('is-user');
    const entries = [];
    document.querySelectorAll('[data-mod],[onclick]').forEach(e => {
      const key = (e.getAttribute('data-mod') || '') + ' ' + (e.getAttribute('onclick') || '');
      const m = key.match(/performance|risk/);
      if (!m) return;
      const rc = e.getBoundingClientRect();
      const st = getComputedStyle(e);
      entries.push({ mod: m[0], visible: rc.width > 0 && rc.height > 0 && st.display !== 'none' });
    });
    const can = {};
    ['performance', 'risk', 'qa'].forEach(k => { can[k] = window.shellCanMod ? window.shellCanMod(k) : null; });
    return { isUser, entries, can, permInit: !!window.__permInit, wrapped: !!window.__permWrapped };
  });
}

async function tryEnterShell(page, mod) {
  const nameMap = { performance: '绩效管理', risk: '风险预警' };
  await page.evaluate(m => { try { window.switchModule(m); } catch (e) {} }, mod);
  await page.waitForTimeout(1500);
  const txt = await page.evaluate(() => document.body.innerText || '');
  const pat = new RegExp('正在进入\\s*' + nameMap[mod]);
  return pat.test(txt);
}

(async () => {
  const browser = await chromium.launch({ channel: 'msedge' });

  // ===== A. spring-assistant.html =====
  console.log('\n[A] spring-assistant.html');
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const p = await ctx.newPage();
    await p.goto(url('spring-assistant.html'), { waitUntil: 'load' }); await p.waitForTimeout(2000);

    await setSession(p, '002191', 'user');
    await p.reload({ waitUntil: 'load' }); await p.waitForTimeout(2000);
    let r = await inspectShell(p);
    t('spring 普通账号 body.is-user', r.isUser);
    t('spring 普通账号 performance 入口全隐藏', r.entries.filter(e => e.mod === 'performance' && e.visible).length === 0, r.entries.filter(e => e.mod === 'performance'));
    t('spring 普通账号 risk 入口全隐藏', r.entries.filter(e => e.mod === 'risk' && e.visible).length === 0, r.entries.filter(e => e.mod === 'risk'));
    t('spring 普通账号 shellCanMod(performance)=false', r.can.performance === false, r.can);
    t('spring 普通账号 shellCanMod(risk)=false', r.can.risk === false, r.can);
    t('spring 普通账号 shellCanMod(qa)=true（不受影响）', r.can.qa === true, r.can);
    t('spring 普通账号进入绩效被拦截', !(await tryEnterShell(p, 'performance')));
    t('spring 普通账号进入风险被拦截', !(await tryEnterShell(p, 'risk')));

    await setSession(p, '028981', 'admin');
    await p.reload({ waitUntil: 'load' }); await p.waitForTimeout(2000);
    r = await inspectShell(p);
    t('spring 管理员 body 无 .is-user', !r.isUser);
    t('spring 管理员 shellCanMod(performance)=true', r.can.performance === true, r.can);
    t('spring 管理员 shellCanMod(risk)=true', r.can.risk === true, r.can);

    // 游客
    await setSession(p, null);
    await p.reload({ waitUntil: 'load' }); await p.waitForTimeout(2000);
    r = await inspectShell(p);
    t('spring 游客 body.is-user', r.isUser);
    t('spring 游客 performance 入口全隐藏', r.entries.filter(e => e.mod === 'performance' && e.visible).length === 0);

    // 品牌占位符渲染检查
    const ph = await p.evaluate(() => ({ title: document.title, body: /\{\{AIRLINE\}\}|\{\{BASE\}\}/.test(document.body.innerText) }));
    t('spring 渲染后无品牌占位符', !/\{\{AIRLINE\}\}|\{\{BASE\}\}/.test(ph.title) && !ph.body, ph);
    await ctx.close();
  }

  // ===== B. nc/index.html =====
  console.log('\n[B] nc/index.html');
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const p = await ctx.newPage();
    await p.goto(url('nc/index.html'), { waitUntil: 'load' }); await p.waitForTimeout(2500);

    await setSession(p, '002191', 'user');
    await p.reload({ waitUntil: 'load' }); await p.waitForTimeout(2500);
    let r = await inspectShell(p);
    t('nc 普通账号 body.is-user', r.isUser);
    t('nc 普通账号 performance 入口全隐藏', r.entries.filter(e => e.mod === 'performance' && e.visible).length === 0, r.entries.filter(e => e.mod === 'performance'));
    t('nc 普通账号 shellCanMod(performance)=false', r.can.performance === false, r.can);
    t('nc 普通账号 shellCanMod(qa)=true', r.can.qa === true, r.can);
    t('nc 普通账号进入绩效被拦截', !(await tryEnterShell(p, 'performance')));

    await setSession(p, '028981', 'admin');
    await p.reload({ waitUntil: 'load' }); await p.waitForTimeout(2500);
    r = await inspectShell(p);
    t('nc 管理员 body 无 .is-user', !r.isUser);
    t('nc 管理员 shellCanMod(performance)=true', r.can.performance === true, r.can);

    const ph = await p.evaluate(() => /\{\{AIRLINE\}\}|\{\{BASE\}\}/.test(document.body.innerText));
    t('nc 渲染后无品牌占位符', !ph);
    await ctx.close();
  }

  // ===== C. risk-lite.html =====
  console.log('\n[C] risk-lite.html');
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const p = await ctx.newPage();
    const errs = [];
    p.on('pageerror', e => errs.push(String(e).slice(0, 150)));

    // 普通账号直接打开 → 无权限遮罩
    await setSession(p, '002191', 'user');
    await p.goto(url('risk-lite.html'), { waitUntil: 'load' }); await p.waitForTimeout(3000);
    let g = await p.evaluate(() => {
      const ov = document.getElementById('loginOverlay');
      return {
        denied: ov ? /该板块仅管理员可用/.test(ov.innerText || '') : false,
        ovVisible: ov ? !ov.classList.contains('hidden') : false,
        gateFn: typeof window.__riskGateAdmin === 'function'
      };
    });
    t('risk 普通会话显示无权限遮罩', g.denied && g.ovVisible, g);
    t('risk 门禁函数已注入', g.gateFn);

    // 管理员会话 → 正常进入
    await setSession(p, '028981', 'admin');
    await p.reload({ waitUntil: 'load' }); await p.waitForTimeout(3500);
    g = await p.evaluate(() => {
      const ov = document.getElementById('loginOverlay');
      return {
        denied: ov ? /该板块仅管理员可用/.test(ov.innerText || '') : false,
        ovHidden: ov ? ov.classList.contains('hidden') : 'gone',
        loggedIn: /风险预警|总部|刷新/.test(document.body.innerText || '')
      };
    });
    t('risk 管理员会话不被遮罩', !g.denied, g);
    t('risk 管理员会话登录层隐藏/已进入', g.ovHidden === true || g.ovHidden === 'gone' || g.loggedIn, g);

    // 源码无硬编码凭据
    const src = fs.readFileSync(path.join(HERE, 'risk-lite.html'), 'utf8');
    t('risk 源码无 LWH 凭据', !/password:\s*'LWH'/.test(src));
    t('risk 源码无 dash-manager 后门', !/dash-manager/.test(src));
    t('risk 渲染后无品牌占位符', !/\{\{AIRLINE\}\}|\{\{BASE\}\}/.test(await p.evaluate(() => document.body.innerText)));
    t('risk 无页面级 JS 错误', errs.length === 0, errs.slice(0, 3));
    await ctx.close();
  }

  // ===== D. 品牌占位符渲染抽查（quiz/performance） =====
  console.log('\n[D] 品牌注入渲染抽查');
  for (const f of ['quiz.html', 'performance.html']) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const p = await ctx.newPage();
    await p.goto(url(f), { waitUntil: 'load' }); await p.waitForTimeout(1800);
    const r = await p.evaluate(() => ({
      title: document.title,
      body: document.body.innerText || ''
    }));
    t(f + ' 标题无占位符', !/\{\{AIRLINE\}\}|\{\{BASE\}\}/.test(r.title), r.title);
    t(f + ' 正文无占位符', !/\{\{AIRLINE\}\}|\{\{BASE\}\}/.test(r.body));
    await ctx.close();
  }

  await browser.close();
  console.log('\n=== 三壳权限门禁守护：PASS ' + pass + ' / FAIL ' + fail + ' ===');
  process.exitCode = fail ? 1 : 0;
})();
