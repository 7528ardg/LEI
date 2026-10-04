/* 考试/练习模式行为守护（2026-10-03）
   背景：quiz.html 考试模式答题后无论对错都弹解析。根因：qz.isExam/qz.isMock
   两属性从未被赋值（模式唯一可信来源是 qz.mode），所有考试守卫恒失效。
   修复 11 处（quiz.html 主源 + nc/index.html 南昌副本同构修复）：
     F1  updateOptState/confirmMultiAnswer 的 isExamOrMock 改用 qz.mode 判定（解析不再弹）
     F2  考试/模拟考试 feedback 中性化（"已作答"，不显示"正确答案：X"）
     F3  渲染重绘 feedback 同步中性化
     F4  getOptClass 考试守卫（交卷前不高亮正确选项、无✓/✗徽章）
     F5  pickOpt 考试模式跳过对错脉冲/连击/里程碑弹窗
     F6  顶部 qt-meta 考试模式不显示实时"正确 N"
     F7  激励横条考试模式中性化（原文案基于实时正确率）
     F8  .fb-neutral CSS
     F9  pickOpt noBack 快捷键防绕过（已答题禁止键盘改答案）

   本守护覆盖：
     A. 静态断言：quiz.html 无失效判断、含全部新守卫；nc 副本解压后一致
     B. 行为断言（Playwright+msedge，file:// 直开 quiz.html）：
        考试/模拟考试/多选答题后无解析卡、feedback 中性、选项不泄露对错、
        无连击/里程碑弹窗；练习模式解析仍在；背题模式答案区仍在。

   用法：node _verify_exam_mode_20261003.js            # 静态+行为全量
         node _verify_exam_mode_20261003.js --static   # 仅静态
   退出码：0 全绿 / 1 有失败 / 2 环境异常
*/
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const vm = require('vm');

const HERE = __dirname;
const QUIZ = path.join(HERE, 'quiz.html');
const NC = path.join(HERE, 'nc', 'index.html');
const SPRING = path.join(HERE, 'spring-assistant.html');

let pass = 0, fail = 0;
const check = (name, ok, detail) => {
  console.log((ok ? 'PASS' : 'FAIL') + ' | ' + name + (detail && !ok ? '→ ' + detail : ''));
  ok ? pass++ : fail++;
};

/* ---------- A. 静态断言 ---------- */
function staticChecks() {
  const quiz = fs.readFileSync(QUIZ, 'utf8');
  check('A01 quiz.html 无失效判断 qz.isExam||qz.isMock', !quiz.includes('qz.isExam || qz.isMock'));
  const cntQuiz = (quiz.match(/[qz_]+\.mode==='exam' \|\| [qz_]+\.mode==='mock_exam'/g) || []).length;
  check('A02 quiz.html mode 守卫 ≥4 处', cntQuiz >= 4);
  check('A03 quiz.html 含 fb-neutral CSS 与用法', quiz.includes('.bp-feedback.fb-neutral') && quiz.includes('bp-feedback show fb-neutral'));
  check('A04 quiz.html getOptClass 交卷前守卫', quiz.includes("!_qz.submitted && (_qz.mode==='exam'"));
  check('A05 quiz.html pickOpt 游戏化守卫', quiz.includes('if(!_isExamOrMock){') && quiz.includes('无对错脉冲、无连击、无里程碑'));
  // 2026-10-03 审查修复：锁定条件由 `qz.mode==='exam' && qz.noBack` 扩展为
  // `((qz.mode==='exam' && qz.noBack) || qz.mode==='mock_exam')`，补上 mock_exam
  // （此前 UI 层 pointer-events 锁定对所有模式生效，键盘却能改模考答案 —— 实测 1→3）。
  check('A06 quiz.html noBack/mode 快捷键防绕过',
    quiz.includes('_qzLockedSingle = (qz.mode===\'exam\' && qz.noBack) || qz.mode===\'mock_exam\'')
    && quiz.includes('if(_qzLockedSingle && curAns!==undefined && curAns!==null) return;')
    && quiz.includes('qz._qzLocked[qi] = true;'),
    '须同时覆盖 exam(noBack) 与 mock_exam，且多选经 confirmMultiAnswer 打 _qzLocked 标记');
  check('A07 quiz.html 内联 script 语法全过', (() => {
    const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
    let m, i = 0;
    while ((m = re.exec(quiz)) !== null) {
      if (/\bsrc\s*=/.test(m[1])) continue;
      if (!m[2].trim()) continue;
      i++;
      try { new vm.Script(m[2], { filename: 'quiz#' + i }); } catch (e) { console.error('      语法错误 script#' + i + ': ' + e.message); return false; }
    }
    return i > 0;
  })());

  // ---- 2026-10-03 三视角审查补充断言（原先全绿的守护漏掉了这3 个 P0）----
  check('A14 quiz.html togglePauseExam 已改用 qz.mode（3 个 P0 之一）',
    quiz.includes("if(APP.quiz.mode !== 'exam' && APP.quiz.mode !== 'mock_exam')")
    && !quiz.includes('if(!APP.quiz.isMock && !APP.quiz.isExam)'),
    '旧守卫读从未赋值的 isMock/isExam → 考试按 P 恒被误拦');
  check('A15 quiz.html 答题卡网格有交卷前守卫（第 2 个 P0）',
    quiz.includes('const _hideVerdict = !qz.submitted')
    && quiz.includes("else if(answered) cls += ' answered';")
    && !quiz.includes('const isW = answered && !checkAnswer(qItem, a);'),
    '答题卡无条件判对错 → 交卷前开卡即泄露');
  check('A16 quiz.html 模考实时得分已中性化（第 3 个 P0 同源）',
    quiz.includes('📊 实时进度')
    && quiz.includes('const _submitted = !!qz.submitted;')
    && !quiz.includes("title:'📊 模拟考试 · 实时得分'")
    && !quiz.includes('/* 模拟考试实时得分 */'),
    '旧实现无条件输出 earned/pct → 答一题即可反推对错');

  // nc 壳副本（南昌定制版，gzip+b64 内嵌）
  const nc = fs.readFileSync(NC, 'utf8');
  const mNc = nc.match(/quiz: "([A-Za-z0-9+/=]+)"/);
  check('A08 nc/index.html 内嵌 quiz 副本可提取', !!mNc);
  if (mNc) {
    const ncQuiz = zlib.gunzipSync(Buffer.from(mNc[1], 'base64')).toString('utf8');
    const cntNc = (ncQuiz.match(/[qz_]+\.mode==='exam' \|\| [qz_]+\.mode==='mock_exam'/g) || []).length;
    check('A09 nc 副本无失效判断、含 mode 守卫', !ncQuiz.includes('qz.isExam || qz.isMock') && cntNc >= 4);
    check('A10 nc 副本内联 script 语法全过', (() => {
      const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
      let m, i = 0;
      while ((m = re.exec(ncQuiz)) !== null) {
        if (/\bsrc\s*=/.test(m[1])) continue;
        if (!m[2].trim()) continue;
        i++;
        try { new vm.Script(m[2], { filename: 'ncQuiz#' + i }); } catch (e) { console.error('      语法错误 script#' + i + ': ' + e.message); return false; }
      }
      return i > 0;
    })());
    // 标题守卫：确认为南昌定制版（防未来误用广州版覆盖）
    check('A11 nc 副本保持南昌定制标题', ncQuiz.includes('南昌刷题系统'));
    // 2026-10-03 审查补充：南昌副本须含第二批修复（togglePauseExam / 答题卡守卫 / mock_exam 锁）
    check('A11b nc 副本含第二批修复（暂停守卫+答题卡+mock锁）',
      ncQuiz.includes("if(APP.quiz.mode !== 'exam' && APP.quiz.mode !== 'mock_exam')")
      && ncQuiz.includes('const _hideVerdict = !qz.submitted')
      && ncQuiz.includes('_qzLockedSingle')
      && !ncQuiz.includes('if(!APP.quiz.isMock && !APP.quiz.isExam)'),
      '南昌副本若未同步第二批修复，壳内培训考核仍是旧行为');
  }

  // spring 壳副本（广州版，_gzip_build 产物）
  if (fs.existsSync(SPRING)) {
    const sp = fs.readFileSync(SPRING, 'utf8');
    const mSp = sp.match(/quiz: "([A-Za-z0-9+/=]+)"/);
    check('A12 spring 副本可提取', !!mSp);
    if (mSp) {
      const spQuiz = zlib.gunzipSync(Buffer.from(mSp[1], 'base64')).toString('utf8');
      check('A13 spring 副本与 quiz.html 源一致', spQuiz === quiz);
    }
  } else {
    console.log('SKIP | A12/A13（spring-assistant.html 不存在）');
  }
}

/* ---------- B. 行为断言 ---------- */
async function behaviorChecks() {
  let chromium;
  try { chromium = require('playwright-core').chromium; }
  catch (e) { console.log('SKIP | 行为断言（playwright-core 不可用）'); return; }
  const { chromium: ch } = { chromium };
  const browser = await ch.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errs = [];
  page.on('pageerror', e => errs.push(String(e)));
  await page.goto('file:///' + encodeURI(QUIZ.replace(/\\/g, '/')).replace(/#/g, '%23'));
  await page.waitForFunction('typeof APP!=="undefined" && APP.questions && APP.questions.length > 0', null, { timeout: 30000 });

  // B1 考试模式：单选
  await page.evaluate('startExam(Array.from({length:5},(_,i)=>i), 300)');
  await page.waitForSelector('#optList .bp-opt', { timeout: 15000 });
  await page.evaluate('pickOpt(0)');
  await page.waitForTimeout(300);
  check('B1 考试-单选答后无解析卡', await page.evaluate('!document.getElementById("questionExplain")'));
  const fb1 = await page.evaluate('(document.getElementById("feedback")||{}).textContent||""');
  check('B2 考试-单选feedback中性', fb1.includes('已作答') && !fb1.includes('正确答案'));
  const cls1 = await page.evaluate('Array.from(document.querySelectorAll("#optList .bp-opt")).map(o=>o.className).join("|")');
  check('B3 考试-选项不高亮对错', !cls1.includes('correct') && !cls1.includes('wrong'));
  check('B4 考试-无连击/里程碑弹窗', await page.evaluate('!document.querySelector(".combo-counter") && !document.querySelector(".quiz-milestone")'));

  // B5 考试模式：多选（内置题库全为单选/判断 → 注入合成多选题确保覆盖 confirmMultiAnswer 多选分支）
  await page.evaluate(`(function(){
    APP.questions.push({q:'__verify_multi_test__', type:'多选', opts:['A. 甲','B. 乙','C. 丙','D. 丁'], ans:'A|B', chapter:'', section:'', explain:'', diff:'易'});
    const mi = APP.questions.length - 1;
    startExam([0, mi], 300);
  })()`);
  await page.waitForSelector('#optList .bp-opt', { timeout: 15000 });
  await page.evaluate('pickOpt(0); pickOpt(1); confirmMultiAnswer()');
  await page.waitForTimeout(300);
  check('B5 考试-多选确认后无解析卡', await page.evaluate('!document.getElementById("questionExplain")'));
  const fb2 = await page.evaluate('(document.getElementById("feedback")||{}).textContent||""');
  check('B6 考试-多选feedback中性', fb2.includes('已作答') && !fb2.includes('正确答案'));

  // B7 模拟考试
  await page.evaluate(`(function(){
    APP.quiz = { indices: Array.from({length:5},(_,i)=>i), current:0, answers:{}, flagged:new Set(),
      startTime:Date.now(), submitted:false, mode:'mock_exam', timeLimit:300, scores:{}, totalScore:5 };
    go('quiz');
  })()`);
  await page.waitForSelector('#optList .bp-opt', { timeout: 15000 });
  await page.evaluate('pickOpt(0)');
  await page.waitForTimeout(300);
  // 修正：原写法 `(() => {})() || true && await page.evaluate(...)` 因运算符优先级恒为 true，断言形同虚设
  check('B7 模拟考试-答后无解析卡且feedback中性',
    await page.evaluate('!document.getElementById("questionExplain")'));
  const fb3 = await page.evaluate('(document.getElementById("feedback")||{}).textContent||""');
  check('B8 模拟考试-feedback中性', fb3.includes('已作答') && !fb3.includes('正确答案'));

  // B9 练习模式回归：解析仍在
  await page.evaluate('startQuiz(Array.from({length:5},(_,i)=>i))');
  await page.waitForSelector('#optList .bp-opt', { timeout: 15000 });
  await page.evaluate('pickOpt(0)');
  await page.waitForTimeout(500);
  check('B9 练习模式-答后仍有解析卡(回归)', await page.evaluate('!!document.getElementById("questionExplain")'));

  // B10 背题模式回归：答案区仍在
  await page.evaluate('startStudyMode(Array.from({length:3},(_,i)=>i))');
  await page.waitForTimeout(400);
  check('B10 背题模式-答案条仍在(回归)', await page.evaluate('!!document.querySelector(".sc-answer-bar")'));

  check('B11 页面无未捕获 JS 错误', errs.length === 0);
  if (errs.length) console.error('      页面JS错误: ' + errs.slice(0, 3).join(' ; '));

  // ========== 2026-10-03 审查补充：3 个 P0 的行为断言 ==========
  // B12 考试模式：答题卡交卷前不得染色（须先 nextQ 让作答题离开 cur 位，
  //     否则被 `if(i===cur)` 分支抢先 → 假阴性，实测踩过此坑）
  await page.evaluate(`(function(){
    APP.questions.push({q:'__ac_leak_test__', type:'单选题', opts:['A. 甲','B. 乙','C. 丙','D. 丁'], ans:'A', chapter:'', section:'', explain:'', diff:'易'});
    startExam([0], 300);
  })()`);
  await page.waitForSelector('#optList .bp-opt', { timeout: 15000 });
  await page.evaluate('(function(){ const q=APP.questions[0]; const right=String(q.ans).split("|")[0].trim().charCodeAt(0)-65; for(let i=0;i<q.opts.length;i++){ if(i!==right){ pickOpt(i); return; } } })()');
  await page.waitForTimeout(300);
  await page.evaluate('APP.quiz.indices.push(1); APP.quiz.current = 1; renderQuiz && renderQuiz()');
  await page.waitForTimeout(400);
  await page.evaluate(`(function(){
    const b=Array.from(document.querySelectorAll('button')).find(x=>(x.textContent||'').includes('📋'));
    if(b) b.click();
  })()`);
  await page.waitForTimeout(600);
  const acCls = await page.evaluate(`Array.from(document.querySelectorAll('.ac-cell')).map(c=>c.className).join('|')`);
  check('B12 考试-答题卡不泄露对错（P0，回归）',
    !acCls.includes('answered-wrong') && !acCls.includes('answered-right'),
    '答题卡出现 answered-wrong/right 说明仍在泄露对错；实测类名: ' + acCls.slice(0, 120));
  const acLegend = await page.evaluate(`((document.querySelector('.seat-map-legend')||{}).textContent||'').replace(/\\s+/g,' ')`);
  check('B13 考试-答题卡图例隐藏「答错」（P0）', !acLegend.includes('答错'), '图例文本: ' + acLegend);

  // B14 考试模式暂停可用（旧守卫读从未赋值的 isMock/isExam → 恒被误拦）
  await page.evaluate('startExam(Array.from({length:5},(_,i)=>i), 600)');
  await page.waitForSelector('#optList .bp-opt', { timeout: 15000 });
  await page.evaluate('togglePauseExam()');
  await page.waitForTimeout(500);
  check('B14 考试-可成功暂停（P0，回归）',
    await page.evaluate('!!document.getElementById("examPauseOverlay") && !!APP.quiz._paused'),
    '未出现 #examPauseOverlay 说明仍被旧守卫误拦');
  await page.evaluate('(function(){ const o=document.getElementById("examPauseOverlay"); if(o) o.remove(); if(APP.quiz) APP.quiz._paused=false; })()');

  // B15 mock_exam 下键盘不可改已锁定答案（UI pointer-events 锁死而键盘能改，实测 1→3）
  await page.evaluate(`(function(){
    APP.quiz = { indices: Array.from({length:5},(_,i)=>i), current:0, answers:{}, flagged:new Set(),
      startTime:Date.now(), submitted:false, mode:'mock_exam', timeLimit:600, scores:{}, totalScore:5 };
    renderQuiz && renderQuiz();
  })()`);
  await page.waitForSelector('#optList .bp-opt', { timeout: 15000 });
  const lockRes = await page.evaluate(`(function(){
    const qz=APP.quiz, qi=qz.indices[0], q=APP.questions[qi];
    if(q.type==='多选') return { skipped:'多选' };
    pickOpt(0);
    const a1 = qz.answers[qi];
    pickOpt(q.opts.length-1);
    const a2 = qz.answers[qi];
    return { a1, a2, changed: a1 !== a2 };
  })()`);
  check('B15 模拟考试-键盘不可改已锁定答案（P1）',
    lockRes.skipped ? true : lockRes.changed === false,
    lockRes.skipped ? '当前为多选，跳过' : ('第一次=' + lockRes.a1 + ' 键盘再改=' + lockRes.a2));

  // B16 模考实时进度面板不得出现得分/正确率
  const mockPanel = await page.evaluate(`(function(){
    if(!document.querySelector('.quiz-sidebar-score-btn')) return { noBtn:true };
    openMockExamSummary && openMockExamSummary();
    return { noBtn:false };
  })()`);
  if (!mockPanel.noBtn) {
    await page.waitForTimeout(600);
    const panelTxt = await page.evaluate(`(function(){
      const m=document.querySelector('.exam-modal,.modal,[class*="modal"]');
      return ((m?m.textContent:document.body.textContent)||'').replace(/\\s+/g,' ');
    })()`);
    // 未交卷的模考面板：只允许「已答 N/M·答题进度」，不得出现「正确率 N%」或旧标题「实时得分」
    // 注意：提示语「不显示实时得分与正确率」本身含「实时得分」字样，故不能按字面判
    const hasScoreWords = /正确率\s*\d/.test(panelTxt) || panelTxt.includes('模拟考试 · 实时得分');
    const hasHint = /考试模式下不显示实时得分/.test(panelTxt);
    check('B16 模拟考试-进度面板不显示得分/正确率（P1）',
      hasHint && !hasScoreWords,
      '面板文本: ' + panelTxt.slice(0, 120) + ' | hasHint=' + hasHint + ' hasScoreWords=' + hasScoreWords);
    await page.evaluate(`(function(){ document.querySelectorAll('.modal-mask,.modal,.exam-modal,[class*="modal"]').forEach(e=>{ if(e && e.closest) {} }); const btns=Array.from(document.querySelectorAll('button')).filter(b=>(b.textContent||'').includes('继续答题')); if(btns[0]) btns[0].click(); })()`);
  } else {
    check('B16 模拟考试-进度面板不显示得分/正确率（P1）', true, '（无实时得分按钮，跳过）');
  }

  await browser.close();
}

(async () => {
  staticChecks();
  if (!process.argv.includes('--static')) {
    await behaviorChecks();
  }
  console.log(`结果: ${pass} 通过 / ${fail} 失败`);
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error('FATAL', e && e.message || e); process.exit(2); });
