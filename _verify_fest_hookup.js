/* 节日识别 → 话术挂载 端到端验证
 * 链路：话术主题文本 → DateMatch.resolveScript → 'fest:x' / 'solar:节气' → 三个话术引擎的开场段
 * 用法：node _verify_fest_hookup.js
 */
'use strict';
const fs = require('fs');
const vm = require('vm');
const html = fs.readFileSync('beauty.html', 'utf8');

function extractBalanced(src, openIdx) {
  const P = { '{': '}', '[': ']', '(': ')' };
  const close = P[src[openIdx]];
  let depth = 0, i = openIdx, inStr = null, esc = false;
  for (; i < src.length; i++) {
    const ch = src[i];
    if (inStr) { if (esc) esc = false; else if (ch === '\\') esc = true; else if (ch === inStr) inStr = null; continue; }
    if (ch === '"' || ch === "'" || ch === '`') { inStr = ch; continue; }
    if (ch === src[openIdx]) depth++;
    else if (ch === close) { depth--; if (depth === 0) return src.slice(openIdx, i + 1); }
  }
  throw new Error('括号未配平 @' + openIdx);
}

const products = eval('([' + html.match(/const products = \[([\s\S]*?)\n        \];/)[1] + '])');
const sb = {
  console, Math, Date, JSON, Set, Map, Array, Object, String, Number, RegExp, parseInt, parseFloat, isNaN,
  localStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} }, products
};
sb.window = sb;
vm.createContext(sb);
vm.runInContext(fs.readFileSync('docs/_season_engine.js', 'utf8'), sb, { filename: 'season.js' });
vm.runInContext(fs.readFileSync('docs/_date_match.js', 'utf8'), sb, { filename: 'date_match.js' });
vm.runInContext('const BRAND_STORY = ' + extractBalanced(html, html.indexOf('{', html.indexOf('const BRAND_STORY = {'))) + ';', sb, { filename: 'brand.js' });
function inject(n) {
  const s = html.indexOf('const ' + n + ' = (function(){');
  vm.runInContext('const ' + n + ' = ' + extractBalanced(html, html.indexOf('(function(){', s)) + '();', sb, { filename: n + '.js' });
  return vm.runInContext(n, sb);
}
const sceneEngine = inject('beautySceneEngine');
const talkEngine = inject('talkShowEngine');
const DM = sb.DateMatch;

let pass = 0, fail = 0;
const failures = [];
function ok(name, cond, extra) { if (cond) pass++; else { fail++; failures.push(name + (extra ? '  <' + extra + '>' : '')); } }

const sel = [
  products.find(p => p.id === 'estee-001'),
  products.find(p => p.brand === '古驰')
].filter(Boolean);

/* 页面层入口等价实现（与 beauty.festivalKeyForScript / qa.qaFestKeyOf 同逻辑） */
function festKeyFor(topic) {
  const r = DM.resolveScript(String(topic || ''));
  return (r && r.script) ? (r.script.kind + ':' + r.script.key) : 'auto';
}

const CASES = [
  { topic: '教师节快到了，想给老师挑份礼物', kind: 'fest', key: 'teachers', word: '教师节' },
  { topic: '中秋想送点礼给爸妈', kind: 'fest', key: 'midautumn', word: '中秋' },
  { topic: '立冬那天开始用', kind: 'term', key: '立冬', word: '立冬' },
  { topic: '冬至快到了', kind: 'term', key: '冬至', word: '冬至' },
  { topic: '双十一准备囤货', kind: 'fest', key: 'shuang11', word: '双十一' }
];

CASES.forEach(function (c) {
  const key = festKeyFor(c.topic);
  ok('挂载点 ' + c.topic + ' → ' + c.kind + ':' + c.key, key === c.kind + ':' + c.key, 'got ' + key);

  // talk 引擎
  const ts = talkEngine.build(sel, { mode: 'strict', duration: 8, time: 'auto', holiday: key });
  const openTalk = ts.modules[0].content;
  ok('talk 开场已应景（' + c.key + '）', openTalk.indexOf(c.word) >= 0, openTalk.slice(0, 60));

  // scene 引擎
  const ss = sceneEngine.build(sel, { mode: 'strict', duration: 8, fest: key });
  const all = ss.fullText;
  ok('scene 已应景（' + c.key + '）', all.indexOf(c.word) >= 0, '');

  // 节日应景段应独立成段（不吞掉产品内容）
  ok('talk 模块数正常（' + c.key + '）', ts.modules.length >= sel.length + 2, 'modules=' + ts.modules.length);
});

/* 识别得到但无专属开场白：不能报错，且要给出降级提示 */
(function () {
  const r = DM.resolveScript('感恩节想送点什么给客户');
  ok('感恩节识别成功', !!r.match && r.match.key === 'thanksgiving', r.match ? r.match.key : 'null');
  ok('感恩节无专属开场白 → 降级提示', r.script === null && !!r.inlineHint, JSON.stringify({ script: r.script, hint: r.inlineHint }));
  const ts = talkEngine.build(sel, { mode: 'strict', duration: 8, time: 'auto', holiday: festKeyFor('感恩节想送点什么给客户') });
  ok('感恩节走通用开场不报错', !!ts && ts.fullText.length > 200, ts ? String(ts.fullText.length) : 'null');
})();

/* 相对时间 / 纯日期表达不应挂节日开场（避免误植入） */
['下个月要出差', '这周有促销吗', '前三天刚买的'].forEach(function (t) {
  ok('不误挂：' + t, festKeyFor(t) === 'auto', festKeyFor(t));
});

/* 手动指定优先（'none' 表示常规航班） */
(function () {
  const manual = 'none';
  const ts = talkEngine.build(sel, { mode: 'strict', duration: 8, time: 'auto', holiday: manual });
  ok('手动 none → 常规开场', !!ts && ts.fullText.indexOf('教师节') < 0);
})();

console.log('===== 节日识别 → 话术挂载 端到端 =====');
console.log('通过 ' + pass + ' 项 / 失败 ' + fail + ' 项');
if (failures.length) { console.log('\n--- 失败明细 ---'); failures.forEach(function (f) { console.log('• ' + f); }); }
process.exit(fail ? 1 : 0);
