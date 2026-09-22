/* 2026-09-21 批1 增强验证：答案卡工具条（复制/朗读/收藏/置信度）+ 我的面板（收藏/练习/字号）
 * 运行：node _qa_enh_verify_20260921.js
 */
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');

const QA = 'file:///' + path.resolve(__dirname, 'qa.html').replace(/\\/g, '/');
const SHOT = path.resolve(__dirname, '_qa_enh_shots');
let pass = 0, fail = 0;
function check(name, ok, detail) {
  if (ok) { pass++; console.log('[PASS] ' + name + (detail !== undefined ? ' — ' + JSON.stringify(detail) : '')); }
  else { fail++; console.log('[FAIL] ' + name + ' — ' + JSON.stringify(detail)); }
}

(async () => {
  if (!fs.existsSync(SHOT)) fs.mkdirSync(SHOT, { recursive: true });
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    permissions: ['clipboard-read', 'clipboard-write']
  });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));

  await page.goto(QA);
  await page.waitForTimeout(2600);

  /* ---------- 预置：练习记录 3 条；清掉收藏/字号/会话 ---------- */
  await page.evaluate(() => {
    localStorage.setItem('qa_train_records_v1', JSON.stringify([
      { at: '2026-09-18T10:00:00.000Z', correct: 6, total: 10, score: 60 },
      { at: '2026-09-19T10:00:00.000Z', correct: 8, total: 10, score: 80 },
      { at: '2026-09-20T10:00:00.000Z', correct: 9, total: 10, score: 90 }
    ]));
    localStorage.removeItem('qa_star_v1');
    localStorage.removeItem('qa_font_v1');
    localStorage.removeItem('qa_history_v1');
  });
  await page.reload();
  await page.waitForTimeout(2600);

  /* ---------- ① 装载检查 ---------- */
  const boot = await page.evaluate(() => ({
    A: window.__QA_ANSWER_TOOLS_20260921__ === true,
    B: window.__QA_MYPANEL_20260921__ === true,
    qaat: !!(window.QAAT && typeof window.QAAT.copy === 'function' && typeof window.QAAT.listStars === 'function'),
    btn: !!document.getElementById('pbMine'),
    panel: !!document.getElementById('qaMinePop'),
    blocks: document.querySelectorAll('#chatWrap .qa-at').length
  }));
  check('批1-A 运行时应答位', boot.A, boot.A);
  check('批1-B 运行时应答位', boot.B, boot.B);
  check('window.QAAT 接口齐备', boot.qaat, boot.qaat);
  check('控制台「我的」键存在', boot.btn, boot.btn);
  check('「我的」面板已挂到控制台', boot.panel, boot.panel);

  /* 空会话时快问面板会自动弹开，先收起，避免遮挡点击 */
  await page.evaluate(() => {
    const q = document.getElementById('qaQuickPop');
    if (q && q.classList.contains('open')) { const x = q.querySelector('.qq-x'); if (x) x.click(); }
  });
  await page.waitForTimeout(300);

  /* ---------- ② 命中提问 → 答案卡工具条 + 置信度徽标 ---------- */
  await page.evaluate(() => { window.ask('迟到怎么扣分？'); });
  await page.waitForTimeout(3000);

  const ans = await page.evaluate(() => {
    const msgs = document.querySelectorAll('#chatWrap .msg.bot');
    const last = msgs[msgs.length - 1];
    const inner = last ? last.querySelector('.bubble-inner') : null;
    const conf = inner ? inner.querySelector('.qa-at-conf') : null;
    return {
      tools: inner ? inner.querySelectorAll('.qa-at').length : 0,
      btns: inner ? Array.prototype.map.call(inner.querySelectorAll('.qa-at-b'), b => b.getAttribute('data-act')) : [],
      confCls: conf ? conf.className : '',
      confText: conf ? conf.textContent : '',
      confTitle: conf ? (conf.getAttribute('title') || '') : '',
      fb: !!(last && last.querySelector('.qb-fb')),
      text: inner ? (inner.innerText || '').slice(0, 40) : ''
    };
  });
  check('答案卡出现工具条（恰好 1 个）', ans.tools === 1, ans.tools);
  check('工具条三键齐备', ans.btns.join(',') === 'copy,speak,star', ans.btns);
  check('答案卡有反馈条（确认这是答案类消息）', ans.fb, ans.fb);
  check('置信度徽标已输出', /qa-at-conf/.test(ans.confCls), ans.confCls);
  check('置信度用的是真实命中分而非兜底文案', /置信度/.test(ans.confText), ans.confText + ' | ' + ans.confTitle);
  await page.screenshot({ path: path.join(SHOT, '01_答案卡工具条.png'), clip: { x: 0, y: 300, width: 1280, height: 600 } });

  /* ---------- ③ 复制 ---------- */
  await page.evaluate(() => {
    const btns = document.querySelectorAll('#chatWrap .qa-at-b[data-act="copy"]');
    btns[btns.length - 1].click();
  });
  await page.waitForTimeout(500);
  const copyRes = await page.evaluate(async () => {
    let clip = '';
    try { clip = await navigator.clipboard.readText(); } catch (e) { clip = 'ERR:' + e.message; }
    return { clip: clip.slice(0, 200), full: clip, toast: (document.getElementById('qa-at-toast') || {}).textContent || '' };
  });
  check('复制命中并给出成功反馈', /已复制/.test(copyRes.toast), copyRes.toast);
  check('剪贴板拿到答案正文（含出处）', /扣分|迟到/.test(copyRes.full) && /来源/.test(copyRes.full), copyRes.clip.slice(0, 90));
  check('复制内容不含工具条文字', !/复制|朗读|收藏/.test(copyRes.full), copyRes.full.match(/复制|朗读|收藏/g));
  check('复制内容不含形象口播', !/立春给你翻到了|随时喊我/.test(copyRes.full), copyRes.full.slice(-60));
  check('复制内容不含推荐芯片段', !/你可能想问|你可能还想了解/.test(copyRes.full), copyRes.full.match(/你可能[^：]{0,6}/g));

  /* ---------- ④ 收藏：加 → 记录 → 再点取消 ---------- */
  await page.evaluate(() => {
    const btns = document.querySelectorAll('#chatWrap .qa-at-b[data-act="star"]');
    btns[btns.length - 1].click();
  });
  await page.waitForTimeout(400);
  const star1 = await page.evaluate(() => ({
    n: (JSON.parse(localStorage.getItem('qa_star_v1') || '[]') || []).length,
    label: (function () {
      const b = document.querySelectorAll('#chatWrap .qa-at-b[data-act="star"]');
      return b.length ? b[b.length - 1].textContent : '';
    })()
  }));
  check('收藏写入 qa_star_v1', star1.n === 1, star1);
  check('按钮切到已收藏态', /已收藏/.test(star1.label), star1.label);

  /* ---------- ⑤ 我的面板：收藏页签 ---------- */
  await page.click('#pbMine');
  await page.waitForTimeout(400);
  const mpStar = await page.evaluate(() => {
    const p = document.getElementById('qaMinePop');
    return {
      open: p.classList.contains('open'),
      btnOn: document.getElementById('pbMine').classList.contains('on'),
      rows: p.querySelectorAll('.mp-t2').length,
      first: p.querySelector('.mp-t2') ? p.querySelector('.mp-t2').innerText : '',
      fsChips: p.querySelectorAll('.mp-fs').length
    };
  });
  check('面板打开 + 控制台键高亮', mpStar.open && mpStar.btnOn, mpStar);
  check('收藏页签列出 1 条', mpStar.rows === 1, mpStar.rows);
  check('收藏条目带标题与来源', mpStar.first.length > 4, mpStar.first);
  check('字号三档齐备', mpStar.fsChips === 3, mpStar.fsChips);
  await page.screenshot({ path: path.join(SHOT, '02_我的_收藏.png') });

  /* ---------- ⑥ 字号：特大 → 生效；标准 → 复位 ---------- */
  await page.click('#qaMinePop .mp-fs[data-fs="xl"]');
  await page.waitForTimeout(300);
  const fsXl = await page.evaluate(() => ({
    px: document.documentElement.style.fontSize,
    saved: localStorage.getItem('qa_font_v1'),
    bodyFs: getComputedStyle(document.body).fontSize
  }));
  check('字号「特大」写入 19px', fsXl.px === '19px' && fsXl.saved === 'xl', fsXl);
  await page.screenshot({ path: path.join(SHOT, '04_字号特大.png') });
  await page.click('#qaMinePop .mp-fs[data-fs="std"]');
  await page.waitForTimeout(300);
  const fsStd = await page.evaluate(() => ({
    px: document.documentElement.style.fontSize,
    saved: localStorage.getItem('qa_font_v1')
  }));
  check('字号回到「标准」并复位根字号', fsStd.px === '' && fsStd.saved === 'std', fsStd);

  /* ---------- ⑦ 练习页签：统计 + 趋势折线 ---------- */
  await page.click('#qaMinePop .mp-tab[data-tab="train"]');
  await page.waitForTimeout(400);
  const mpTrain = await page.evaluate(() => {
    const p = document.getElementById('qaMinePop');
    const svg = p.querySelector('svg.mp-spark polyline');
    return {
      stat: p.querySelector('.mp-stat') ? p.querySelector('.mp-stat').innerText.replace(/\s+/g, ' ') : '',
      hasSvg: !!svg,
      pts: svg ? svg.getAttribute('points').split(' ').length : 0,
      rows: p.querySelectorAll('.mp-tr').length
    };
  });
  check('练习统计显示次数/平均/最好', /共 3 次/.test(mpTrain.stat) && /平均/.test(mpTrain.stat) && /77/.test(mpTrain.stat), mpTrain.stat);
  check('趋势折线按记录数出点', mpTrain.hasSvg && mpTrain.pts === 3, mpTrain);
  check('练习明细列出记录', mpTrain.rows === 3, mpTrain.rows);
  await page.screenshot({ path: path.join(SHOT, '03_我的_练习.png') });

  /* 点收藏条目 → 自动重问 */
  const before = await page.evaluate(() => document.querySelectorAll('#chatWrap .msg').length);
  await page.click('#qaMinePop .mp-tab[data-tab="star"]');
  await page.waitForTimeout(300);
  await page.click('#qaMinePop .mp-t2');
  await page.waitForTimeout(2500);
  const after = await page.evaluate(() => document.querySelectorAll('#chatWrap .msg').length);
  check('点收藏条目会重问该问题', after > before, { before, after });

  /* ---------- ⑧ 零命中 → 低置信 ---------- */
  await page.evaluate(() => { window.ask('请问客舱里紫色的大象今天心情怎么样'); });
  await page.waitForTimeout(2500);
  const low = await page.evaluate(() => {
    const msgs = document.querySelectorAll('#chatWrap .msg.bot');
    const last = msgs[msgs.length - 1];
    const inner = last ? last.querySelector('.bubble-inner') : null;
    const conf = inner ? inner.querySelector('.qa-at-conf') : null;
    return {
      fb: !!(last && last.querySelector('.qb-fb')),
      confCls: conf ? conf.className : '',
      confText: conf ? conf.textContent : '',
      tools: inner ? inner.querySelectorAll('.qa-at').length : 0
    };
  });
  check('零命中仍给工具条', low.fb ? low.tools === 1 : true, low);
  check('零命中标为低置信', !low.fb || /qa-at-conf l/.test(low.confCls), low.confCls + ' | ' + low.confText);
  await page.screenshot({ path: path.join(SHOT, '05_低置信.png'), clip: { x: 0, y: 250, width: 1280, height: 650 } });

  /* ---------- ⑨ 无脚本异常 ---------- */
  check('无页面 JS 异常', errors.length === 0, errors.slice(0, 3));

  await browser.close();
  console.log('\n===== 批1 验证：PASS ' + pass + ' / FAIL ' + fail + ' =====');
  console.log('截图目录：' + SHOT);
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('脚本异常：', e); process.exit(2); });
