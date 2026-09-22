/* 日期匹配引擎验证（docs/_season_engine.js + docs/_date_match.js）
 * 用法：node _verify_date_match.js [--today YYYY-MM-DD]
 * 覆盖：公历节日 / 农历节日 / 通用节点 / 修饰语 / 相对时间 / 节气 / 跨年 / 负例 / 输出结构
 */
'use strict';
const fs = require('fs');
const vm = require('vm');

const sb = { console, Math, Date, JSON, Set, Map, Array, Object, String, Number, RegExp, parseInt, parseFloat, isNaN };
sb.window = sb;
vm.createContext(sb);
vm.runInContext(fs.readFileSync('docs/_season_engine.js', 'utf8'), sb, { filename: 'season.js' });
vm.runInContext(fs.readFileSync('docs/_date_match.js', 'utf8'), sb, { filename: 'date_match.js' });
const SE = sb.SeasonEngine;
const DM = sb.DateMatch;

const T = '2026-09-12';            // 基准「今天」：教师节刚过 2 天、中秋前 13 天
const D = (s) => new Date(s + 'T09:00:00');

let pass = 0, fail = 0;
const failures = [];
function ok(name, cond, extra) {
  if (cond) { pass++; return; }
  fail++; failures.push(name + (extra ? '  <' + extra + '>' : ''));
}
function best(text, today) {
  return DM.parseBest(text, { today: D(today || T) });
}

/* ---------- ① 节日词 → 日期（用户要求的核心：先识别节日词） ---------- */
const FEST_CASES = [
  // [话术片段, 期望 key, 期望 type, 期望 offset, 期望 start, 期望 end]
  ['教师节快到了，想给老师挑份礼物', 'teachers', 'solar', 'soon', '2027-09-03', '2027-09-10'],
  ['中秋想送点礼给爸妈', 'midautumn', 'lunar', 'none', '2026-09-25', '2026-09-27'],
  ['国庆出去玩，路上带点什么好', 'national', 'solar', 'none', '2026-10-01', '2026-10-07'],
  ['春节前一天飞', 'spring', 'lunar', 'before', '2027-02-05', '2027-02-05'],
  ['国庆节前的班次', 'national', 'solar', 'before', '2026-09-28', '2026-09-30'],
  ['中秋前一周开始备货', 'midautumn', 'lunar', 'before', '2026-09-18', '2026-09-24'],
  ['明年中秋想提前一个月准备', 'midautumn', 'lunar', 'before', '2027-08-15', '2027-09-14'],
  ['临近中秋的航班', 'midautumn', 'lunar', 'soon', '2026-09-18', '2026-09-25'],
  ['中秋当天想订一盒', 'midautumn', 'lunar', 'same', '2026-09-25', '2026-09-25'],
  ['双十一准备囤货', 'shuang11', 'shopping', 'none', '2026-11-11', '2026-11-11'],
  ['618有什么值得买的', 'shopping618', 'shopping', 'none', '2027-06-18', '2027-06-18'],
  ['立冬那天开始用', '立冬', 'term', 'same', null, null],
  ['冬至快到了', '冬至', 'term', 'soon', null, null]
];
FEST_CASES.forEach(function (c) {
  const m = best(c[0]);
  const tag = '① ' + c[0];
  if (!m) { ok(tag, false, '未命中'); return; }
  ok(tag + ' → key=' + c[1], m.key === c[1], 'got ' + m.key);
  ok(tag + ' → type=' + c[2], m.type === c[2], 'got ' + m.type);
  ok(tag + ' → offset=' + c[3], m.offset === c[3], 'got ' + m.offset);
  if (c[4]) ok(tag + ' → ' + c[4] + '~' + c[5], m.start === c[4] && m.end === c[5], 'got ' + m.start + '~' + m.end);
});

/* ---------- ② 相对时间 → 绝对日期 ---------- */
const REL_CASES = [
  ['前三天刚买了这个', '2026-09-09', '2026-09-11'],
  ['这周有促销吗', '2026-09-07', '2026-09-13'],
  ['下周末回来', '2026-09-19', '2026-09-20'],
  ['下个月要出差', '2026-10-01', '2026-10-31'],
  ['三天后出发', '2026-09-15', '2026-09-15'],
  ['明年中秋想提前一个月准备', null, null]
];
REL_CASES.forEach(function (c) {
  const m = best(c[0]);
  const tag = '② ' + c[0];
  if (!m) { ok(tag, false, '未命中'); return; }
  if (c[1]) ok(tag + ' → ' + c[1] + '~' + c[2], m.start === c[1] && m.end === c[2], 'got ' + m.start + '~' + m.end);
  else ok(tag + ' 命中', !!m);
});

/* ---------- ③ 输出结构完整性 ---------- */
['教师节快到了', '中秋想送点礼', '下个月出差', '立冬那天'].forEach(function (t) {
  const m = best(t);
  const need = ['raw', 'type', 'key', 'name', 'start', 'end', 'label', 'confidence', 'offset', 'note'];
  const missing = need.filter(function (k) { return m[k] === undefined || m[k] === null || m[k] === ''; });
  ok('③ 结构完整：' + t + (missing.length ? ' 缺 ' + missing.join(',') : ''), missing.length === 0);
});

/* ---------- ④ 跨年策略 ---------- */
const CROSS = [
  ['2026-12-28', '元旦', '2027-01-01'],
  ['2026-01-05', '圣诞', '2026-12-25'],
  ['2026-09-13', '教师节', '2026-09-10'],   // 刚过 3 天，宽限内仍按今年
  ['2026-09-20', '教师节', '2027-09-10'],   // 已过 10 天，顺延明年
  ['2026-09-12', '教师节快到了', '2027-09-03'] // 临近语义 → 必须指向未来（区间从节前 7 天起）
];
CROSS.forEach(function (c) {
  const m = best(c[1], c[0]);
  ok('④ 跨年 ' + c[0] + '说「' + c[1] + '」→ ' + c[2], m && m.start === c[2], m ? 'got ' + m.start : '未命中');
});

/* ---------- ⑤ 农历不固定：同节日不同年不同日，表内精确、表外降级 ---------- */
const MA = DM.FESTS.filter(function (f) { return f.key === 'midautumn'; })[0];
const ma26 = DM.datesOf(MA, 2026), ma27 = DM.datesOf(MA, 2027), ma28 = DM.datesOf(MA, 2028);
ok('⑤ 中秋逐年不同', DM.ymd(ma26.s) !== DM.ymd(ma27.s) && DM.ymd(ma27.s) !== DM.ymd(ma28.s),
  [ma26, ma27, ma28].map(function (r) { return DM.ymd(r.s); }).join(' / '));
ok('⑤ 表内精确', ma26.estimated === false && ma27.estimated === false);
const ma25 = DM.datesOf(MA, 2025);
ok('⑤ 表外降级为估算', ma25.estimated === true);
const m25 = best('去年中秋', '2026-09-12');
ok('⑤ 表外置信度降低且标注', m25 && m25.confidence <= 0.6 && /估算/.test(m25.note || ''),
  m25 ? 'conf=' + m25.confidence + ' note=' + m25.note : '未命中');

/* ---------- ⑥ 当日匹配 todayMatch（统一「今天是什么节」） ---------- */
const TODAY = [
  ['2026-10-03', 'national', '国庆假期第 3 天'],
  ['2026-11-11', 'shuang11', '购物节点当日'],
  ['2026-09-26', 'midautumn', '中秋假期内'],
  ['2026-11-08', '立冬', '节气当日'],
  ['2026-03-05', null, '普通日（惊蛰前后，无节）']
];
TODAY.forEach(function (c) {
  const m = DM.todayMatch(D(c[0]));
  if (c[1] === null) ok('⑥ ' + c[0] + ' 无节日', !m, m ? 'got ' + m.name : '');
  else ok('⑥ ' + c[0] + ' → ' + c[1] + '（' + c[2] + '）', m && m.key === c[1], m ? 'got ' + m.key : '未命中');
});

/* ---------- ⑦ 话术挂载点 resolveScript（识别 → 可用性，含降级） ---------- */
const RS = [
  ['教师节快到了', 'fest', 'teachers'],
  ['立冬那天开始用', 'term', '立冬'],
  ['下个月要出差', null, ''],
  ['感恩节想送点什么', null, '']      // 识别得到但没有专属开场白 → script=null + inlineHint
];
RS.forEach(function (c) {
  const r = DM.resolveScript(c[0], { today: D(T) });
  if (c[1] === null) ok('⑦ ' + c[0] + ' → 不挂载但可降级', (!r.script) && !!r.match, 'script=' + JSON.stringify(r.script));
  else ok('⑦ ' + c[0] + ' → ' + c[1] + ':' + c[2], r.script && r.script.kind === c[1] && r.script.key === c[2],
    r.script ? r.script.kind + ':' + r.script.key : 'null');
});
const rsNone = DM.resolveScript('下个月要出差', { today: D(T) });
ok('⑦ 相对时间不误挂节日开场', rsNone.script === null && rsNone.name === '下个月');

/* ---------- ⑧ 负例：不应误命中 ---------- */
['11月去日本', '十一月出差', '三十一号结算', '五一路那人多'].forEach(function (t) {
  const m = best(t);
  ok('⑧ 负例「' + t + '」不误命中', !m, m ? 'got ' + m.name : '');
});

/* ---------- ⑩ 多基准日稳定性：全年多月各跑一遍，校验结构与区间合法性 ---------- */
(function () {
  const days = ['2026-01-05', '2026-02-15', '2026-03-15', '2026-04-15', '2026-05-15', '2026-06-15',
    '2026-07-15', '2026-08-15', '2026-09-15', '2026-10-15', '2026-11-15', '2026-12-15',
    '2027-01-15', '2027-06-15', '2028-02-15'];
  let bad = 0, total = 0;
  const badDetail = [];
  days.forEach(function (day) {
    DM.SAMPLES.forEach(function (t) {
      total++;
      try {
        const m = DM.parseBest(t, { today: D(day) });
        if (!m) return;                       // 负例允许无命中
        ['raw', 'type', 'key', 'name', 'start', 'end', 'label', 'confidence'].forEach(function (k) {
          if (m[k] === undefined || m[k] === '') { bad++; badDetail.push(day + '/' + t + ' 缺 ' + k); }
        });
        if (!/^\d{4}-\d{2}-\d{2}$/.test(m.start) || !/^\d{4}-\d{2}-\d{2}$/.test(m.end)) { bad++; badDetail.push(day + '/' + t + ' 日期格式'); }
        if (m.start > m.end) { bad++; badDetail.push(day + '/' + t + ' 区间倒置'); }
        if (m.confidence < 0.3 || m.confidence > 1) { bad++; badDetail.push(day + '/' + t + ' 置信度越界'); }
      } catch (e) { bad++; badDetail.push(day + '/' + t + ' 异常 ' + e.message); }
    });
  });
  ok('⑩ 多基准日稳定性（' + days.length + ' 基准 × ' + DM.SAMPLES.length + ' 样例 = ' + total + ' 次）', bad === 0,
    badDetail.slice(0, 5).join('；'));
})();

/* ---------- ⑨ SeasonEngine.match 已统一到 DateMatch ---------- */
const seMatch = SE.match(D('2026-10-03'));
ok('⑨ SeasonEngine.match 认假期区间', seMatch && seMatch.key === 'national' && seMatch.via === 'DateMatch',
  seMatch ? seMatch.key + '/' + seMatch.via : 'null');

console.log('===== 日期匹配引擎验证（today=' + T + '）=====');
console.log('通过 ' + pass + ' 项 / 失败 ' + fail + ' 项');
if (failures.length) { console.log('\n--- 失败明细 ---'); failures.forEach(function (f) { console.log('• ' + f); }); }

console.log('\n--- 典型话术识别样例 ---');
DM.SAMPLES.forEach(function (t) {
  const m = best(t);
  if (!m) { console.log('  ' + t + '  →  （无命中）'); return; }
  console.log('  ' + t + '  →  ' + m.name + '【' + DM.typeName(m.type) + '/' + m.offset + '】' + (m.label || m.start)
    + '  conf=' + m.confidence + (m.estimated ? ' (估算)' : ''));
});
process.exit(fail ? 1 : 0);
