/* 你问我答 · 候选追问 + 联想记忆回归（常驻）
 * 用途：验证 QA_ASSOC 块（qaClarSearch / qaAssoc* / qaClarPick / qaClarNone / qaAssocUndo）：
 *   ① 未收录表述（"灭火是什么""机上黑色三角形标志在哪里"）能收集到相关候选且满足追问门条件；
 *   ② 用户肯定确认后「原始问法 → 条目+库」写入 localStorage（qa_assoc_v1，上限 200 条 LRU）；
 *   ③ 后续相同/相似问法（含错别字）直接记忆命中作答，条目被删时自然降级；
 *   ④ 「都不是」加入会话跳过集并放行原链路（不写记忆）；撤销可删除记忆。
 * 用法：node _verify_qa_assoc.js      失败即非零退出（供 _build_all.py 守护）
 * 说明：脚本从 qa.html 实时抽取 KB 五库 + kbSearch 引擎 + QA_ASSOC 标记块运行，
 *       kbReply/typing/addMsg/process 用桩替换并记录调用。强命中直答路径由
 *       _verify_qa_wakeup.js（33 例）守护，本脚本不重复。
 */
"use strict";
const fs = require('fs');

const src = fs.readFileSync('qa.html', 'utf8');

// 1) 数据块：const KB = [ ... ];（DC_KB 同步块结束前的最后一个 ];
const iData = src.indexOf('const KB = [');
if (iData < 0) throw new Error('缺少 const KB 数据块');
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

// 3) QA_ASSOC 标记块
const iA = src.indexOf('/* ===== QA_ASSOC_BEGIN');
const iB = src.indexOf('/* ===== QA_ASSOC_END');
if (iA < 0 || iB < 0 || iB < iA) throw new Error('QA_ASSOC 标记块缺失（qa.html）');
const assocJs = src.slice(iA, iB);

const factory = new Function('window', 'localStorage', 'SeasonEngine', 'document', '__esc', 'kbReply', '__typing', '__clearTyping', '__addMsg', 'process', `
  ${dataJs}
  ${engJs}
  /* 测试桩覆盖：dataJs 里夹带的 esc/addMsg/typing/clearTyping 依赖完整 DOM，换成可记录调用的桩 */
  esc = __esc; addMsg = __addMsg; typing = __typing; clearTyping = __clearTyping;
  ${assocJs}
  return { KB: KB, ccm: window.KB_CCM_RAW, mgm: window.KB_MGM_RAW, svc: window.KB_SVC_RAW, dc: window.DC_KB,
    qaClarSearch: qaClarSearch, qaAssocSave: qaAssocSave, qaAssocLookup: qaAssocLookup, qaAssocForget: qaAssocForget,
    qaAssocAnswer: qaAssocAnswer, qaClarPick: qaClarPick, qaClarNone: qaClarNone, qaAssocUndo: qaAssocUndo,
    qaAssocLoad: qaAssocLoad, qaAssocNorm: qaAssocNorm, getQaSource: function(){ return qaSource; }, skipSet: qaClarSkip };
`);

// ---- 桩 ----
const store = new Map();
const ls = { getItem: k => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, String(v)), removeItem: k => store.delete(k) };
const doc = { querySelectorAll: () => [] };
const escT = s => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const kbCalls = [], botMsgs = [], userMsgs = [], procCalls = [];
const kbReply = (hits) => { if (hits && hits.length) kbCalls.push({ q: hits[0].k.q }); };
const typing = async () => {};
const clearTyping = () => {};
const addMsg = (role, html) => { (role === 'user' ? userMsgs : botMsgs).push(html); };
const proc = async (t) => { procCalls.push(t); };
const win = { addEventListener() {}, dispatchEvent() {} };
const SE = { FEST_OPTS: [], match: () => null, parse: () => null };
const M = factory(win, ls, SE, doc, escT, kbReply, typing, clearTyping, addMsg, proc);

const b64 = s => Buffer.from(String(s), 'utf8').toString('base64');
let pass = 0;
function ok(cond, msg) {
  if (cond) { pass++; return; }
  throw new Error('FAIL: ' + msg);
}

async function main() {
  const pools = { daily: M.KB, ccm: M.ccm, mgm: M.mgm, svc: M.svc, dc: M.dc };
  const flat = (c) => ((c.k.q || '') + ' ' + (c.k.t || []).join(' ')).toLowerCase();
  const flatA = (c) => (flat(c) + ' ' + String(c.k.a || '').replace(/<[^>]+>/g, ' ')).toLowerCase();

  // ① 未收录表述："灭火是什么" → 候选收集 + 满足追问门（单条也需首条 ≥55 分）
  const cFire = M.qaClarSearch('灭火是什么');
  ok(cFire.length >= 1, '「灭火是什么」应有候选');
  ok(cFire.every(c => c.score >= 25), '候选分数须≥25');
  ok(cFire.some(c => flat(c).indexOf('灭火') >= 0), '候选应含灭火相关条目');
  ok(cFire[0].score >= 55, '「灭火是什么」首条候选须≥55分（追问门条件）');

  // ② 未收录表述："机上黑色三角形标志在哪里" → ≥2 条候选且含三角形相关
  const cTri = M.qaClarSearch('机上黑色三角形标志在哪里');
  ok(cTri.length >= 2, '「黑色三角形」应有≥2条候选（追问门条件）');
  ok(cTri.every(c => c.score >= 25), '候选分数须≥25');
  ok(cTri.some(c => flatA(c).indexOf('三角') >= 0), '候选中应有三角形相关条目');

  // ③ 记忆写入 + 精确命中 + 相似问法（错别字）模糊命中
  let triEntry = null, triPool = null;
  for (const p of Object.keys(pools)) {
    const e = (pools[p] || []).find(k => (k.t || []).some(t => String(t).indexOf('三堆火三角形') >= 0));
    if (e) { triEntry = e; triPool = p; break; }
  }
  ok(triEntry, '应能找到 三堆火三角形（求救信号）条目');
  ok(M.qaAssocSave('机上黑色三角形标志在哪里', triEntry.q, triPool) === true, '记忆写入应成功');
  const hit1 = M.qaAssocLookup('机上黑色三角形标志在哪里');
  ok(hit1 && hit1.exact && hit1.rec.q === triEntry.q, '归一化后应精确命中');
  const hit2 = M.qaAssocLookup('机上黑色三角型标志在哪里');
  ok(hit2 && !hit2.exact && hit2.rec.q === triEntry.q, '相似问法（错别字 形→型）应模糊命中');

  // ④ 记忆直答：不再追问，直接作答并定位到记住的库
  const before = kbCalls.length;
  ok(await M.qaAssocAnswer('机上黑色三角型标志在哪里') === true, '联想记忆应直答');
  ok(kbCalls.length === before + 1 && kbCalls[kbCalls.length - 1].q === triEntry.q, '记忆直答应作答正确条目');
  ok(M.getQaSource() === triPool, '记忆直答应静默切到记住的库');

  // ⑤ 候选确认（qaClarPick）：作答该条目 + 写入联想记忆 + 定位库
  const dcEntry = (M.dc || []).find(k => String(k.q || '').indexOf('灭火') >= 0) || (M.dc || [])[0];
  ok(dcEntry, '大撤库应有灭火相关条目');
  const uBefore = userMsgs.length;
  await M.qaClarPick(b64(JSON.stringify({ pool: 'dc', q: dcEntry.q })), b64('灭火是什么'));
  ok(kbCalls.length > 0 && kbCalls[kbCalls.length - 1].q === dcEntry.q, '确认候选应作答该条目');
  const recFire = M.qaAssocLoad()[M.qaAssocNorm('灭火是什么')];
  ok(recFire && recFire.q === dcEntry.q && recFire.pool === 'dc', '确认后应写入联想记忆（问法→条目+库）');
  ok(userMsgs.length === uBefore + 1, '确认候选应追加用户选择气泡');
  ok(M.getQaSource() === 'dc', '确认后应定位到条目所在库');
  ok(await M.qaAssocAnswer('灭火是什么') === true, '确认过的问法再次提问应记忆直答');

  // ⑥ 都不是：加入会话跳过集 + 放行原链路（重走 process）+ 不写记忆
  const uBefore2 = userMsgs.length, pBefore = procCalls.length;
  await M.qaClarNone(b64('随手编个XYZ问题'));
  ok(M.skipSet.has(M.qaAssocNorm('随手编个XYZ问题')), '「都不是」后应加入本会话跳过集');
  ok(procCalls.length === pBefore + 1 && procCalls[procCalls.length - 1] === '随手编个XYZ问题', '「都不是」应放行原链路（重走 process）');
  ok(userMsgs.length === uBefore2 + 1, '「都不是」应有用户气泡');
  ok(!M.qaAssocLoad()[M.qaAssocNorm('随手编个XYZ问题')], '「都不是」不应写记忆');

  // ⑦ 撤销记忆
  const undoKey = M.qaAssocNorm('灭火是什么');
  M.qaAssocUndo(b64(undoKey));
  ok(!M.qaAssocLoad()[undoKey], '撤销后记忆应删除');

  // ⑧ 上限 200 条，最旧淘汰
  for (let i = 0; i < 210; i++) M.qaAssocSave('批量问法' + i, triEntry.q, triPool);
  const m2 = M.qaAssocLoad();
  ok(Object.keys(m2).length === 200, '记忆上限 200 条');
  ok(!m2[M.qaAssocNorm('批量问法0')], '最旧记忆应被淘汰');
  ok(!!m2[M.qaAssocNorm('批量问法209')], '最新记忆应保留');

  // ⑨ 条目被删除（库管理移除）→ 记忆自然作废降级
  M.qaAssocSave('指向不存在条目的问法', '根本不存在的条目XYZ', 'svc');
  ok(await M.qaAssocAnswer('指向不存在条目的问法') === false, '条目已删除时记忆直答应降级为 false');

  // ⑩ 空输入 / 边界
  ok(M.qaAssocLookup('') === null, '空输入不命中记忆');
  ok(M.qaClarSearch('').length === 0, '空输入无候选');

  console.log('=== 你问我答 候选追问+联想记忆回归 ===');
  console.log('通过 ' + pass + ' / ' + pass + ' 项断言（灭火/黑色三角形 候选 · 确认记忆 · 精确/模糊命中 · 直答定位 · 都不是跳过 · 撤销 · 200条上限 · 失效降级）');
  console.log('全部通过 ✓');
}

main().then(() => process.exit(0)).catch(e => { console.error(e.message); process.exit(1); });
