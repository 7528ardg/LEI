/* 你问我答 · 跨板块唤醒回归（常驻）
 * 用途：验证「日常库提问 → 跨库强证据切库 / 决定性更优切库 / AI 上下文兜底」整条决策链，
 *       确保引擎改动不会破坏各板块（手册奖惩 / 医疗急救 / 大撤 / 绩效 / 销售日常）的可唤醒性。
 * 用法：node _verify_qa_wakeup.js      失败即非零退出（供 _build_all.py 守护）
 * 说明：脚本从 qa.html 实时抽取 KB 五库 + kbSearch 引擎，逐行镜像 process() 的决策顺序。
 */
"use strict";
const fs = require('fs');

const src = fs.readFileSync('qa.html', 'utf8');

function sliceBetween(text, startMark, endMark) {
  const i = text.indexOf(startMark);
  if (i < 0) throw new Error('缺少起始标记: ' + startMark);
  const j = text.indexOf(endMark, i);
  if (j < 0) throw new Error('缺少结束标记: ' + endMark);
  return text.slice(i, j);
}

// 1) 数据块：const KB = [ ... ];（DC_KB 同步块结束前的最后一个 ];
const iData = src.indexOf('const KB = [');
const iEndMark = src.indexOf('DC_KB_END');
const jData = src.lastIndexOf('];', iEndMark);
const dataJs = src.slice(iData, jData + 2);

// 2) 引擎块：GENERIC_TAGS ... kbSearch 结束（按大括号配对定位）
const iEng = src.indexOf('const GENERIC_TAGS');
const iKb = src.indexOf('function kbSearch', iEng);
let depth = 0, started = false, kbEnd = -1;
for (let k = iKb; k < src.length; k++) {
  const ch = src[k];
  if (ch === '{') { depth++; started = true; }
  else if (ch === '}') { depth--; if (started && depth === 0) { kbEnd = k; break; } }
}
const engJs = src.slice(iEng, kbEnd + 1);

const factory = new Function('window', 'localStorage', 'SeasonEngine', `
  ${dataJs}
  ${engJs}
  return { KB: KB, ccm: window.KB_CCM_RAW, mgm: window.KB_MGM_RAW, svc: window.KB_SVC_RAW, dc: window.DC_KB, kbSearch: kbSearch };
`);
const win = { addEventListener() {}, dispatchEvent() {} };
const sto = { getItem: () => null, setItem() {}, removeItem() {} };
const SE = { FEST_OPTS: [], match: () => null, parse: () => null };
const M = factory(win, sto, SE);

const POOLS = { daily: M.KB, ccm: M.ccm, mgm: M.mgm, svc: M.svc, dc: M.dc };
const IDX = {};
for (const p in POOLS) { IDX[p] = new Map(); POOLS[p].forEach((k, i) => IDX[p].set(k, i)); }
const strip = h => String(h || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();

function searchTop(text, pool, n) {
  return M.kbSearch(text, n || 3, POOLS[pool]).map(h => ({
    pool, idx: IDX[pool].get(h.k), q: h.k.q || '', a: strip(h.k.a),
    s: h.s, sem: !!h.sem, ev: h.ev || 0, sim: h.sim || 0
  }));
}
function kbStrong(hits) {
  if (!hits || !hits.length) return false;
  const h0 = hits[0];
  return !!h0.sem && h0.s >= 4 && (h0.s >= 8 || (h0.sim || 0) >= 0.25 || (h0.ev || 0) >= 2);
}
// 镜像 qa process()：当前库强证据直答 → 跨库决定性更优(≥15分)切库 → 跨库强证据切库 → AI 上下文
function ask(text) {
  const own = searchTop(text, 'daily', 3);
  let decisive = null;
  if (kbStrong(own)) {
    for (const p of ['ccm', 'mgm', 'svc', 'dc']) {
      const h = searchTop(text, p, 3);
      if (kbStrong(h) && h[0].s >= own[0].s + 15 && (!decisive || h[0].s > decisive.s)) decisive = { pool: p, s: h[0].s };
    }
    if (!decisive) return { pool: 'daily', entries: own.slice(0, 3), mode: '当前库直答' };
  }
  let best = null;
  for (const p of ['ccm', 'mgm', 'svc', 'dc']) {
    const h = searchTop(text, p, 3);
    if (kbStrong(h) && (!best || h[0].s > best.s)) best = { pool: p, s: h[0].s, entries: h };
  }
  if (best) return { pool: best.pool, entries: best.entries.slice(0, 3), mode: '跨库强证据切库' };
  const ctx = searchTop(text, 'daily', 3);
  const seen = new Set(ctx.map(h => h.pool + ':' + h.idx));
  for (const p of ['ccm', 'mgm', 'svc', 'dc']) {
    searchTop(text, p, 3).forEach(h => {
      if (h.s >= 3 && !seen.has(h.pool + ':' + h.idx) && ctx.length < 12) { ctx.push(h); seen.add(h.pool + ':' + h.idx); }
    });
  }
  return { pool: null, entries: ctx, mode: 'AI 上下文兜底' };
}

// 用例：[提问, 期望关键词（须出现在作答条目标题/答案或 AI 上下文中）, 归类]
const CASES = [
  ['销转保哪些情况可以用', '销转保', '日常·销售'],
  ['旅客网订的餐机上没有怎么保障', '网订餐', '日常·网订餐'],
  ['跨境购物年度额度是多少怎么查', '跨境', '日常·商品知识'],
  ['销售做错钱要补给公司怎么转', '补款', '日常·销售收款'],
  ['配送系统没反应点不动怎么处理', '系统', '日常·配送'],
  ['电子发票怎么开', '发票', '日常·发票'],
  ['因公加机组和因私加机组有什么要求', '加机组', '日常·乘务管理'],
  ['酒测的标准是多少', '酒测', '手册·管理'],
  ['竞聘乘务长需要什么条件', '乘务长', '手册·管理'],
  ['降级后怎么恢复原等级', '恢复', '手册·管理'],
  ['撤离口令有哪些', '口令', '手册·乘务员'],
  ['氧气瓶使用有什么注意事项', '氧气', '手册·乘务员'],
  ['着装标准是什么要求', '着装', '手册·服务规范'],
  ['UM无陪儿童怎么服务', '陪', '手册·服务规范'],
  ['旅客遗留物品怎么处理', '遗留', '手册·服务规范'],
  ['三人灭火小组怎么分工', '灭火', '大撤'],
  ['客舱释压了怎么处置', '释压', '大撤'],
  ['滑梯救生筏能坐多少人', '滑梯', '大撤'],
  ['往期挂点有哪些经验', '挂点', '大撤·往期经验'],
  ['机门卡阻怎么处理', '卡阻', '大撤·往期经验'],
  ['简令纸遗漏组员会怎样', '简令纸', '大撤·往期经验'],
  ['机上旅客癫痫发作怎么处理', '癫痫', '医疗急救'],
  ['心肺复苏按压深度多少', '按压', '医疗急救'],
  ['气道异物梗阻怎么急救', '异物', '医疗急救'],
  ['旅客烫伤了怎么处理', '烫伤', '医疗急救'],
  ['旅客过敏性休克怎么办', '过敏', '医疗急救·扩充'],
  ['旅客低血糖发作了怎么办', '低血糖', '医疗急救·扩充'],
  ['旅客疑似深静脉血栓腿肿怎么办', '深静脉', '医疗急救·扩充'],
  ['旅客耳朵疼航空性中耳炎', '中耳炎', '医疗急救·扩充'],
  ['旅客机上要分娩了怎么办', '分娩', '医疗急救'],
  ['月度绩效考核多少分不合格', '绩效', '绩效管理'],
  ['机上事件报告单什么时候交', '事件报告单', '事件报告'],
  ['请病假需要哪些材料', '病假', '病假管理'],
];

let pass = 0;
const fails = [];
CASES.forEach(([q, kw, tag]) => {
  const r = ask(q);
  const hay = r.entries.map(e => e.q + ' ' + e.a).join(' ');
  const ok = hay.indexOf(kw) >= 0;
  if (ok) pass++;
  else fails.push({ q, kw, tag, mode: r.mode, pool: r.pool || '(无)', top: r.entries.length ? r.entries[0].q : '(空)' });
});

console.log('=== 你问我答 跨板块唤醒回归 ===');
console.log('通过 ' + pass + ' / ' + CASES.length);
if (fails.length) {
  console.log('--- 失败明细 ---');
  fails.forEach(f => console.log('  ✗ [' + f.tag + '] ' + f.q + ' → 期望含「' + f.kw + '」｜' + f.mode + ' / ' + f.pool + ' / top1: ' + f.top));
  process.exit(1);
}
console.log('全部用例可唤醒 ✓');
