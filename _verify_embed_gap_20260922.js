/* ============================================================
 * _verify_embed_gap_20260922.js · 嵌入态「死带空白」回归
 * 覆盖：多视口 × 嵌入态（切 tab 前后）× 独立打开 beauty.html
 * 判定：嵌入态 main 底边应贴合 iframe 底边（|gap| <= 2px）
 * 用法：node _verify_embed_gap_20260922.js
 * ============================================================ */
'use strict';
const { chromium } = require('playwright-core');
const path = require('path');

const ROOT = __dirname.replace(/\\/g, '/');
const IDX = 'file:///' + ROOT + '/index.html';
const BEAUTY = 'file:///' + ROOT + '/beauty.html';
const SESSION = JSON.stringify({ '工号': '028981', '姓名': '管理员', '手机号': '', '密码': 'LWH' });

const VPS = [
  { w: 393, h: 852, label: 'iPhone 15 竖' },
  { w: 360, h: 780, label: 'Android 窄屏' },
  { w: 414, h: 896, label: 'iPhone Max' },
  { w: 768, h: 1024, label: '平板竖' },
  { w: 320, h: 680, label: '超窄屏 320' },
];

const results = [];
let fails = 0;

function judge(name, gap, extra) {
  const ok = Math.abs(gap) <= 2;
  if (!ok) fails++;
  results.push({ name, gap, ok, extra });
  console.log((ok ? '[ok]  ' : '[FAIL]') + ' ' + name.padEnd(38) + ' gap=' + gap + 'px' + (extra ? '  ' + extra : ''));
}

(async () => {
  const browser = await chromium.launch({
    channel: 'msedge',
    args: ['--no-proxy-server', '--proxy-bypass-list=<-loopback>', '--allow-file-access-from-files', '--disable-web-security'],
    proxy: { server: 'direct://' },
  });

  for (const vp of VPS) {
    const ctx = await browser.newContext({
      viewport: { width: vp.w, height: vp.h },
      deviceScaleFactor: 1,
      isMobile: vp.w <= 480,
      hasTouch: vp.w <= 480,
    });
    const page = await ctx.newPage();
    await page.addInitScript((s) => { try { localStorage.setItem('cabin_session_v1', s); } catch (e) {} }, SESSION);
    await page.goto(IDX, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await page.waitForFunction(() => typeof window.switchModule === 'function', null, { timeout: 120000 });
    await page.waitForTimeout(2000);
    await page.evaluate(() => { try { if (typeof window.shellTourSkip === 'function') window.shellTourSkip(); } catch (e) {} });
    await page.waitForTimeout(400);
    await page.evaluate(() => switchModule('beauty'));
    await page.waitForFunction(() => {
      const f = document.getElementById('frame-beauty');
      const d = f && f.contentDocument;
      return !!(d && d.querySelector('main.main-scroll-container'));
    }, null, { timeout: 90000 });
    await page.waitForTimeout(1500);
    await page.evaluate(() => {
      const f = document.getElementById('frame-beauty');
      const d = f.contentDocument, w = f.contentWindow;
      try { if (typeof w.closeTutorial === 'function') w.closeTutorial(); } catch (e) {}
      [...d.querySelectorAll('div.fixed.inset-0')].forEach(e => { if (e.querySelector('.max-w-lg')) e.remove(); });
    });
    await page.waitForTimeout(700);

    const measure = () => page.evaluate(() => {
      const f = document.getElementById('frame-beauty');
      const d = f.contentDocument, w = f.contentWindow;
      const main = d.querySelector('main.main-scroll-container');
      const eb = w.getComputedStyle(d.documentElement).getPropertyValue('--embed-bottom').trim();
      const et = w.getComputedStyle(d.documentElement).getPropertyValue('--embed-top').trim();
      const de = d.documentElement.getAttribute('data-embed');
      const b = main.getBoundingClientRect();
      const bar = document.getElementById('mTabbar');
      const sa = document.getElementById('sysArea');
      return {
        gap: Math.round(w.innerHeight - b.bottom),
        mainTop: Math.round(b.top), mainH: Math.round(b.height),
        iframeH: w.innerHeight, eb, et, de,
        overlap: bar ? Math.round(sa.getBoundingClientRect().bottom - bar.getBoundingClientRect().top) : null,
        innerScrollTop: Math.round(main.scrollTop),
        bodyScrollH: d.body.scrollHeight,
      };
    });

    let m = await measure();
    judge(vp.label + ' · 产品浏览', m.gap, `iframeH=${m.iframeH} main=${m.mainTop}->${m.mainTop + m.mainH} eb=${m.eb} et=${m.et} data-embed=${m.de} iframe∩TabBar=${m.overlap}px`);
    await page.screenshot({ path: `_verify_gap_${vp.w}x${vp.h}_browse.png` });

    // 切到「肤质筛选」（render 会重建容器）后重新量测
    await page.evaluate(() => {
      const d = document.getElementById('frame-beauty').contentDocument;
      const b = [...d.querySelectorAll('nav button')].find(x => (x.textContent || '').indexOf('肤质筛选') >= 0);
      if (b) b.click();
    });
    await page.waitForTimeout(1600);
    m = await measure();
    judge(vp.label + ' · 肤质筛选(切tab后)', m.gap, `main=${m.mainTop}->${m.mainTop + m.mainH} et=${m.et}`);

    await page.screenshot({ path: `_verify_gap_${vp.w}x${vp.h}.png` });
    await ctx.close();
  }

  // ---- 独立打开 beauty.html（不经壳）应保持可用：main 不溢出视口 ----
  const ctx2 = await browser.newContext({ viewport: { width: 393, height: 852 }, isMobile: true, hasTouch: true });
  const p2 = await ctx2.newPage();
  await p2.goto(BEAUTY, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await p2.waitForFunction(() => !!document.querySelector('main.main-scroll-container'), null, { timeout: 90000 });
  await p2.waitForTimeout(1500);
  await p2.evaluate(() => { try { if (typeof closeTutorial === 'function') closeTutorial(); } catch (e) {} });
  await p2.waitForTimeout(600);
  const solo = await p2.evaluate(() => {
    const main = document.querySelector('main.main-scroll-container');
    const b = main.getBoundingClientRect();
    return { bottom: Math.round(b.bottom), innerH: innerHeight, h: Math.round(b.height), top: Math.round(b.top), headVisible: !!document.querySelector('header[class*="bg-gradient-to-r"]') && document.querySelector('header[class*="bg-gradient-to-r"]').offsetHeight > 0 };
  });
  judge('独立打开 beauty.html · 不溢出', solo.bottom - solo.innerH <= 2 ? 0 : solo.bottom - solo.innerH, `main=${solo.top}->${solo.bottom} innerH=${solo.innerH} 顶栏可见=${solo.headVisible}`);
  await ctx2.close();

  await browser.close();
  console.log('\n===== 汇总：' + results.length + ' 项，失败 ' + fails + ' =====');
  require('fs').writeFileSync('_verify_embed_gap_20260922.json', JSON.stringify({ results, fails }, null, 2));
  process.exit(fails > 0 ? 1 : 0);
})().catch(e => { console.error('ERR', e.message); process.exit(2); });
