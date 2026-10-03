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
const check = (name, ok) => {
  console.log((ok ? 'PASS' : 'FAIL') + ' | ' + name);
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
  check('A06 quiz.html noBack 快捷键防绕过', quiz.includes('qz.mode===' + "'exam'" + ' && qz.noBack && curAns!==undefined'));
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
  check('B7 模拟考试-答后无解析卡且feedback中性', (() => {})() || true && await page.evaluate('!document.getElementById("questionExplain")'));
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
