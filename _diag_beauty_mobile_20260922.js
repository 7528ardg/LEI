/* ============================================================
 * _diag_beauty_mobile_20260922.js
 * 手机视口下复现「产品浏览」板块下方大块空白遮挡，量化壳层与模块盒模型。
 * 用法：node _diag_beauty_mobile_20260922.js [port] [tab]
 * ============================================================ */
'use strict';
const { chromium } = require('playwright-core');
const fs = require('fs');

const PORT = process.argv[2] || '8901';
const TAB = process.argv[3] || 'browse';
const BASE = process.env.BASE || ('file:///' + __dirname.replace(/\\/g, '/') + '/index.html');
const SESSION = JSON.stringify({ '工号': '028981', '姓名': '管理员', '手机号': '', '密码': 'LWH' });

(async () => {
  const browser = await chromium.launch({
    channel: 'msedge',
    args: ['--no-proxy-server', '--proxy-bypass-list=<-loopback>', '--allow-file-access-from-files', '--disable-web-security'],
    proxy: { server: 'direct://' },
  });
  const ctx = await browser.newContext({
    viewport: { width: 393, height: 852 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
  });
  const page = await ctx.newPage();
  await page.addInitScript((s) => { try { localStorage.setItem('cabin_session_v1', s); } catch (e) {} }, SESSION);
  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForFunction(() => typeof window.switchModule === 'function', null, { timeout: 120000 });
  await page.waitForTimeout(2500);
  // 关掉壳层新手引导
  await page.evaluate(() => { try { if (typeof window.shellTourSkip === 'function') window.shellTourSkip(); } catch (e) {} });
  await page.waitForTimeout(500);
  await page.evaluate(() => switchModule('beauty'));
  await page.waitForFunction(() => {
    const f = document.getElementById('frame-beauty');
    const d = f && f.contentDocument;
    return !!(d && d.querySelector('main.main-scroll-container'));
  }, null, { timeout: 90000 });
  await page.waitForTimeout(2500);

  // 关掉 beauty 的新手引导层（fixed inset-0 遮罩），否则截图与量测都被它污染
  await page.evaluate(() => {
    const f = document.getElementById('frame-beauty');
    const d = f && f.contentDocument, w = f && f.contentWindow;
    if (!d) return;
    try { if (typeof w.closeTutorial === 'function') w.closeTutorial(); } catch (e) {}
    [...d.querySelectorAll('div.fixed.inset-0')].forEach(e => { if (e.querySelector('.max-w-lg')) e.remove(); });
  });
  await page.waitForTimeout(1000);

  // 切到目标 tab
  if (TAB !== 'browse') {
    try {
      await page.evaluate((t) => {
        const d = document.getElementById('frame-beauty').contentDocument;
        const btns = [...d.querySelectorAll('nav button')];
        const hit = btns.find(b => (b.textContent || '').indexOf(t) >= 0);
        if (hit) hit.click();
      }, TAB);
      await page.waitForTimeout(1800);
    } catch (e) { console.log('tab switch failed', e.message); }
  }

  const out = await page.evaluate(() => {
    const r = (e) => { if (!e) return null; const b = e.getBoundingClientRect(); return { top: Math.round(b.top), bottom: Math.round(b.bottom), h: Math.round(b.height), w: Math.round(b.width) }; };
    const shellRoot = document.documentElement;
    const shell = {
      innerH: innerHeight, innerW: innerWidth,
      topbarH: getComputedStyle(shellRoot).getPropertyValue('--topbar-h').trim(),
      sysArea: r(document.getElementById('sysArea')),
      tabbar: r(document.getElementById('mTabbar')),
      frame: r(document.getElementById('frame-beauty')),
    };
    const f = document.getElementById('frame-beauty');
    const d = f.contentDocument, w = f.contentWindow;
    if (!d) return { shell, inner: { err: 'no doc' } };

    const nav = d.querySelector('nav');
    const main = d.querySelector('main.main-scroll-container');
    const card = main ? main.querySelector(':scope > div') : null;
    const cs = main ? w.getComputedStyle(main) : null;

    // 内层 max-h 容器（Tailwind 任意值）
    let innerScroll = null;
    if (card) {
      const all = [...card.querySelectorAll('div')];
      const hit = all.find(e => (e.className || '').toString().indexOf('max-h-[calc') >= 0);
      if (hit) {
        const b = hit.getBoundingClientRect();
        innerScroll = { cls: hit.className.toString().slice(0, 120), top: Math.round(b.top), bottom: Math.round(b.bottom), h: Math.round(b.height), maxH: w.getComputedStyle(hit).maxHeight, scrollH: hit.scrollHeight, clientH: hit.clientHeight };
      }
    }

    // 空白带采样：main 底边到 iframe 底边之间
    const mb = main ? Math.round(main.getBoundingClientRect().bottom) : 0;
    const probe = [];
    for (let y = mb + 10; y < w.innerHeight - 4; y += 40) {
      const el = d.elementFromPoint(20, y) || d.elementFromPoint(Math.round(w.innerWidth / 2), y);
      const chain = [];
      let cur = el;
      for (let i = 0; i < 5 && cur; i++) {
        const b = cur.getBoundingClientRect();
        chain.push(cur.tagName + '#' + (cur.id || '') + '.' + (cur.className || '').toString().slice(0, 40) + ' [' + Math.round(b.top) + '→' + Math.round(b.bottom) + ']');
        cur = cur.parentElement;
      }
      probe.push({ y, chain });
    }

    // 所有 fixed / sticky 可见层
    const fixedEls = [];
    d.querySelectorAll('*').forEach(e => {
      const s = w.getComputedStyle(e);
      if (s.position !== 'fixed' && s.position !== 'sticky') return;
      const b = e.getBoundingClientRect();
      if (b.width <= 0 || b.height <= 0) return;
      fixedEls.push({
        tag: e.tagName + '#' + (e.id || '') + '.' + (e.className || '').toString().slice(0, 60),
        pos: s.position, top: Math.round(b.top), bottom: Math.round(b.bottom), h: Math.round(b.height),
        z: s.zIndex, bg: s.backgroundColor, op: s.opacity, vis: s.visibility,
        txt: (e.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 40),
      });
    });

    // main 的兄弟节点（#app 直接子元素）
    const appKids = main && main.parentElement
      ? [...main.parentElement.children].map((e, i) => {
        const b = e.getBoundingClientRect();
        return { i, tag: e.tagName + '#' + (e.id || '') + '.' + (e.className || '').toString().slice(0, 50), top: Math.round(b.top), bottom: Math.round(b.bottom), h: Math.round(b.height) };
      })
      : [];

    const bodyChildren = [...d.body.children].map(e => {
      const b = e.getBoundingClientRect();
      return { tag: e.tagName + '#' + (e.id || '') + '.' + (e.className || '').toString().split(' ')[0], top: Math.round(b.top), h: Math.round(b.height) };
    });

    return {
      shell,
      inner: {
        innerH: w.innerHeight, innerW: w.innerWidth,
        docClientH: d.documentElement.clientHeight,
        bodyScrollH: d.body.scrollHeight,
        embedBottom: w.getComputedStyle(d.documentElement).getPropertyValue('--embed-bottom').trim(),
        padSrc: {
          htmlPadTop: w.getComputedStyle(d.documentElement).paddingTop,
          bodyPadTop: w.getComputedStyle(d.body).paddingTop,
          bodyPadTopInline: d.body.style.paddingTop,
          bodyMarginTop: w.getComputedStyle(d.body).marginTop,
          appMarginTop: d.getElementById('app') ? w.getComputedStyle(d.getElementById('app')).marginTop : null,
          appPadTop: d.getElementById('app') ? w.getComputedStyle(d.getElementById('app')).paddingTop : null,
          appOffsetTop: d.getElementById('app') ? d.getElementById('app').offsetTop : null,
          bodyOffsetTop: d.body.offsetTop,
          navPadTop: nav ? w.getComputedStyle(nav).paddingTop : null,
          navPadTopInline: nav ? nav.style.paddingTop : null,
          navMarginTop: nav ? w.getComputedStyle(nav).marginTop : null,
          appRectTop: d.getElementById('app') ? Math.round(d.getElementById('app').getBoundingClientRect().top) : null,
          appBefore: (() => { const e = d.getElementById('app'); if (!e) return null; const s = w.getComputedStyle(e, '::before'); return { content: s.content, h: s.height, display: s.display, mt: s.marginTop }; })(),
          topHit: [4, 12, 20, 30].map(y => { const e = d.elementFromPoint(5, y); return y + ':' + (e ? e.tagName + '#' + e.id + '.' + (e.className || '').toString().slice(0, 18) : 'null'); }),
          bodyBorderTop: w.getComputedStyle(d.body).borderTopWidth,
          htmlRectTop: Math.round(d.documentElement.getBoundingClientRect().top),
          appTransform: d.getElementById('app') ? w.getComputedStyle(d.getElementById('app')).transform : null,
          bodyBefore: (() => { const s = w.getComputedStyle(d.body, '::before'); return { content: s.content, h: s.height, display: s.display, mt: s.marginTop }; })(),
          navBefore: nav ? (() => { const s = w.getComputedStyle(nav, '::before'); return { content: s.content, h: s.height, display: s.display }; })() : null,
          bodyPadBottomInline: d.body.style.paddingBottom,
          topOcc: [...d.querySelectorAll('*')].map(e => ({ e, b: e.getBoundingClientRect() }))
            .filter(x => x.b.height > 0 && x.b.width > 0 && x.b.bottom > 0 && x.b.bottom <= 26)
            .slice(0, 10)
            .map(x => x.e.tagName + '#' + x.e.id + '.' + (x.e.className || '').toString().slice(0, 30) + '[' + Math.round(x.b.top) + '→' + Math.round(x.b.bottom) + ']w' + Math.round(x.b.width)),
        },
        nav: nav ? { ...r(nav), top_css: w.getComputedStyle(nav).top, pos: w.getComputedStyle(nav).position } : null,
        main: main ? { ...r(main), maxH: cs.maxHeight, minH: cs.minHeight, overflowY: cs.overflowY, padBottom: cs.paddingBottom, scrollH: main.scrollHeight, clientH: main.clientHeight } : null,
        card: r(card),
        innerScroll,
        bodyChildren: bodyChildren.filter(x => x.h > 0),
        appKids,
        fixedEls,
        probe,
      }
    };
  });

  console.log(JSON.stringify(out, null, 2));
  await page.screenshot({ path: '_diag_beauty_mobile_20260922.png' });
  fs.writeFileSync('_diag_beauty_mobile_20260922.json', JSON.stringify(out, null, 2));

  // ===== 修复方案预演：--embed-bottom 归零 + main 高度按实际占位精确计算 =====
  if (process.env.FIX === '1') {
    const after = await page.evaluate(() => {
      const f = document.getElementById('frame-beauty');
      const d = f.contentDocument, w = f.contentWindow;
      d.documentElement.style.setProperty('--embed-bottom', '0px');
      const main = d.querySelector('main.main-scroll-container');
      const st = d.createElement('style');
      st.id = 'diag-fix-probe';
      st.textContent = '#app>main.main-scroll-container{padding-bottom:16px!important;}';
      d.head.appendChild(st);
      const fit = () => { const t = main.getBoundingClientRect().top; main.style.setProperty('max-height', Math.max(200, w.innerHeight - t) + 'px', 'important'); };
      fit();
      w.addEventListener('resize', fit);
      return new Promise(res => setTimeout(() => {
        const b = (e) => { if (!e) return null; const r = e.getBoundingClientRect(); return { top: Math.round(r.top), bottom: Math.round(r.bottom), h: Math.round(r.height) }; };
        const nav = d.querySelector('nav');
        res({ iframeH: w.innerHeight, nav: b(nav), main: b(main), mainMaxH: w.getComputedStyle(main).maxHeight, gap: w.innerHeight - Math.round(main.getBoundingClientRect().bottom) });
      }, 600));
    });
    console.log('=== AFTER FIX ===');
    console.log(JSON.stringify(after, null, 2));
    await page.screenshot({ path: '_diag_beauty_mobile_fixed_20260922.png' });
  }

  await browser.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
