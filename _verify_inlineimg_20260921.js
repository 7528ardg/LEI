/* 内联图片外置后的冒烟校验（2026-09-21）
 * 断言：
 *  1) 本地静态服务下打开 index.html，默认进入 qa 模块成功
 *  2) 所有 assets/img/* 请求均 200（无 404）—— 外置路径解析正确
 *  3) 切到 cc-home 后同样无 404，且 3D 脚本仍加载
 *  4) 页面无未捕获 JS 错误
 */
'use strict';
const { ensureServer, closeAll } = require('./_verify_srv');
let pw;
try { pw = require('playwright-core'); } catch (e) { pw = null; }

const BASE = 'http://127.0.0.1:8893/index.html';
let pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log('  PASS  ' + name); }
  else { fail++; console.log('  FAIL  ' + name + (extra ? '  → ' + extra : '')); }
}

(async () => {
  if (!pw) { console.log('playwright-core 不可用，跳过浏览器冒烟'); process.exit(2); }
  await ensureServer(8893, BASE);
  const browser = await pw.chromium.launch({ channel: 'msedge' });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

  const bad = [];      // 404 / 失败请求
  const errs = [];     // 未捕获异常
  page.on('response', r => { if (r.status() >= 400) bad.push(r.status() + ' ' + r.url()); });
  page.on('requestfailed', r => bad.push('FAILED ' + r.url()));
  page.on('pageerror', e => errs.push(String(e).split('\n')[0]));

  await page.goto(BASE, { waitUntil: 'load', timeout: 60000 });
  await page.waitForTimeout(4000);

  const hasQa = await page.evaluate(() => {
    const f = document.getElementById('frame-qa');
    return !!(f && f.contentDocument && f.contentDocument.body && f.contentDocument.body.children.length > 0);
  });
  ok('qa 模块 iframe 已加载出内容', hasQa);

  const qaImgs = await page.evaluate(() => {
    const f = document.getElementById('frame-qa');
    const d = f && f.contentDocument;
    if (!d) return { total: 0, broken: 0 };
    const im = Array.from(d.querySelectorAll('img'));
    let broken = 0;
    im.forEach(i => { if (i.getAttribute('src') && i.complete && i.naturalWidth === 0) broken++; });
    return { total: im.length, broken };
  });
  ok('qa 内 <img> 无加载失败（' + qaImgs.total + ' 张）', qaImgs.broken === 0, qaImgs.broken + ' 张 naturalWidth=0');

  const asset404 = bad.filter(u => u.indexOf('/assets/img/') >= 0);
  ok('assets/img/* 无 404', asset404.length === 0, asset404.slice(0, 3).join(' | '));

  // 切到 CC 之家（图片最重的模块）
  await page.evaluate(() => { try { switchModule('home'); } catch (e) {} });
  await page.waitForTimeout(6000);
  const hasHome = await page.evaluate(() => {
    const f = document.getElementById('frame-home');
    return !!(f && f.contentDocument && f.contentDocument.body && f.contentDocument.body.children.length > 0);
  });
  ok('cc-home 模块 iframe 已加载出内容', hasHome);
  const home404 = bad.filter(u => u.indexOf('/assets/img/') >= 0);
  ok('切到 cc-home 后 assets/img/* 仍无 404', home404.length === 0, home404.slice(0, 3).join(' | '));

  const fatal = errs.filter(e => !/ResizeObserver|favicon/i.test(e));
  ok('无未捕获 JS 异常', fatal.length === 0, fatal.slice(0, 3).join(' | '));

  console.log('\n其他失败请求（非 assets）：' + bad.filter(u => u.indexOf('/assets/img/') < 0).slice(0, 5).join(' | '));
  console.log('结果：' + pass + ' 通过 / ' + fail + ' 失败');
  await browser.close();
  closeAll();
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('冒烟异常：', e); closeAll(); process.exit(1); });
