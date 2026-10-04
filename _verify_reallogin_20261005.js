/* 真实登录路径 E2E（2026-10-05）
 * 用真实凭据在 index.html 登录页输入并登录（非伪造 session）：
 *   - 普通账号 002191/GJY → performance/risk 入口不可见
 *   - 管理员 028981/LWH  → 入口可见
 * 附：登录态下检查导航 DOM 与 shellCanMod。
 */
const { chromium } = require('playwright-core');
const path = require('path');
const HERE = __dirname;
const PAGE = 'file:///' + path.join(HERE, 'index.html').replace(/\\/g, '/');

let pass = 0, fail = 0;
const t = (name, cond, extra) => {
  if (cond) { pass++; console.log('  PASS  ' + name); }
  else { fail++; console.log('  FAIL  ' + name + (extra !== undefined ? '  → ' + JSON.stringify(extra) : '')); }
};

(async () => {
  const browser = await chromium.launch({ channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', e => errs.push(String(e).slice(0, 150)));

  // 预置"已看过教程"，避免教程遮罩拦截后续点击（与登录流程无关）
  await p.addInitScript(() => { try { localStorage.setItem('cabin_tutorial_seen', '1'); localStorage.setItem('spring_onb_done', '1'); } catch (e) {} });

  // ---- 普通账号真实登录 ----
  await p.goto(PAGE, { waitUntil: 'load' });
  await p.waitForTimeout(2000);
  await p.locator('#afId').fill('002191');
  await p.locator('#afPwd').fill('GJY');
  await p.locator('.auth-btn').first().click();
  await p.waitForTimeout(3000);

  let st = await p.evaluate(() => ({
    authGone: (() => { const o = document.querySelector('.auth-overlay'); return !o || getComputedStyle(o).display === 'none'; })(),
    isUser: document.body.classList.contains('is-user'),
    can: { performance: window.shellCanMod && window.shellCanMod('performance'), risk: window.shellCanMod && window.shellCanMod('risk'), qa: window.shellCanMod && window.shellCanMod('qa') },
    who: (() => { try { return JSON.parse(localStorage.getItem('cabin_session_v1') || 'null'); } catch (e) { return null; } })()
  }));
  t('普通账号登录成功（登录层消失）', st.authGone, st.who);
  t('普通账号 session.role=user', st.who && st.who.role === 'user', st.who);
  t('普通账号 body.is-user', st.isUser);
  t('普通账号 shellCanMod(performance)=false', st.can.performance === false, st.can);
  t('普通账号 shellCanMod(risk)=false', st.can.risk === false, st.can);
  t('普通账号 shellCanMod(qa)=true', st.can.qa === true, st.can);

  // 入口可见性（真实渲染）
  const vis = await p.evaluate(() => {
    const out = { performance: [], risk: [] };
    document.querySelectorAll('[data-mod],[onclick]').forEach(e => {
      const key = (e.getAttribute('data-mod') || '') + ' ' + (e.getAttribute('onclick') || '');
      const m = key.match(/performance|risk/);
      if (!m) return;
      const rc = e.getBoundingClientRect();
      const disp = getComputedStyle(e).display;
      out[m[0]].push(rc.width > 0 && rc.height > 0 && disp !== 'none');
    });
    return { perfVisible: out.performance.filter(Boolean).length, riskVisible: out.risk.filter(Boolean).length };
  });
  t('普通账号绩效入口 0 个可见', vis.perfVisible === 0, vis);
  t('普通账号风险入口 0 个可见', vis.riskVisible === 0, vis);

  // 截图存证
  await p.screenshot({ path: path.join(HERE, '_walk_out3', 'e2e-login-user.png') });

  // ---- 登出 → 管理员真实登录 ----
  await p.evaluate(() => { try { window.shellLogout(); } catch (e) {} });
  await p.waitForTimeout(1500);
  const outOk = await p.evaluate(() => document.body.classList.contains('is-user'));
  t('登出后复位 .is-user', outOk);

  // 登录层可能需要重新显示
  await p.evaluate(() => { try { window.showAuth && window.showAuth(); } catch (e) {} });
  await p.waitForTimeout(800);
  await p.locator('#afId').fill('028981');
  await p.locator('#afPwd').fill('LWH');
  await p.locator('.auth-btn').first().click();
  await p.waitForTimeout(3000);

  st = await p.evaluate(() => ({
    authGone: (() => { const o = document.querySelector('.auth-overlay'); return !o || getComputedStyle(o).display === 'none'; })(),
    isUser: document.body.classList.contains('is-user'),
    can: { performance: window.shellCanMod && window.shellCanMod('performance'), risk: window.shellCanMod && window.shellCanMod('risk') },
    who: (() => { try { return JSON.parse(localStorage.getItem('cabin_session_v1') || 'null'); } catch (e) { return null; } })()
  }));
  t('管理员登录成功', st.authGone, st.who);
  t('管理员 session.role=admin', st.who && st.who.role === 'admin', st.who);
  t('管理员 body 无 .is-user', !st.isUser);
  t('管理员 shellCanMod(performance)=true', st.can.performance === true, st.can);
  t('管理员 shellCanMod(risk)=true', st.can.risk === true, st.can);

  const vis2 = await p.evaluate(() => {
    // 判据用 computed display（risk 入口在"更多"抽屉内，抽屉收起时 rect 不可见属正常 UI 状态，
    // 权限判据应为「CSS 门禁是否隐藏」，即 display 是否为 none）
    const out = { performance: 0, risk: 0, riskTotal: 0 };
    document.querySelectorAll('[data-mod],[onclick]').forEach(e => {
      const key = (e.getAttribute('data-mod') || '') + ' ' + (e.getAttribute('onclick') || '');
      const m = key.match(/performance|risk/);
      if (!m) return;
      const disp = getComputedStyle(e).display;
      if (m[0] === 'risk') { out.riskTotal++; if (disp !== 'none') out.risk++; }
      else {
        const rc = e.getBoundingClientRect();
        if (rc.width > 0 && rc.height > 0 && disp !== 'none') out.performance++;
      }
    });
    return out;
  });
  t('管理员绩效入口可见（≥1）', vis2.performance >= 1, vis2);
  t('管理员风险入口未被 CSS 隐藏（≥1/' + vis2.riskTotal + '）', vis2.risk >= 1, vis2);

  await p.screenshot({ path: path.join(HERE, '_walk_out3', 'e2e-login-admin.png') });
  t('全程无页面级 JS 错误', errs.length === 0, errs.slice(0, 3));

  await ctx.close();
  await browser.close();
  console.log('\n=== 真实登录 E2E：PASS ' + pass + ' / FAIL ' + fail + ' ===');
  process.exitCode = fail ? 1 : 0;
})();
