/* 库管理「完整数据包」往返一致守护（2026-09-21）
 * -----------------------------------------------------------------------------
 * 用户诉求：导出的数据包重新导入后，能被系统正确识别与完整还原，确保数据一致性。
 * 本脚本不做 mock：直接 require 与运行时同源的 docs/_fullpack_engine.js，
 * 从真实源文件（qa.html 六库 / beauty.html 话术库与产品库）抽取数据，
 * 跑「导出 → 校验 → 还原 → 逐条深比对」，并覆盖篡改检测、编辑/删除后的往返。
 * 用法：node _verify_kb_fullpack.js
 */
'use strict';
const fs = require('fs');
const path = require('path');

const B = __dirname + '/';
const F = require(B + 'docs/_fullpack_engine.js');

let pass = 0, fail = 0;
const fails = [];
function ok(cond, name, extra) {
  if (cond) { pass++; console.log('  ✓ ' + name); }
  else { fail++; fails.push(name + (extra ? ' → ' + extra : '')); console.log('  ✗ ' + name + (extra ? ' → ' + extra : '')); }
}

/* ---------- 从真实源文件抽取数据（与 _build_kbadmin.py 同口径） ---------- */
function grab(text, start, open_ch, close_ch) {
  let depth = 0, i = start, inStr = null;
  for (; i < text.length; i++) {
    const c = text[i];
    if (inStr) { if (c === '\\') { i++; continue; } if (c === inStr) inStr = null; continue; }
    if (c === '"' || c === "'" || c === '`') { inStr = c; continue; }
    if (c === open_ch) depth++;
    else if (c === close_ch) { depth--; if (depth === 0) return text.slice(start, i + 1); }
  }
  throw new Error('bracket not closed');
}
function evalLit(src) { return new Function('return (' + src + ')')(); }
function arrFrom(file, re) {
  const t = fs.readFileSync(B + file, 'utf8');
  const m = re.exec(t);
  if (!m) throw new Error('not found: ' + re + ' in ' + file);
  return evalLit(grab(t, m.index + m[0].length - 1, '[', ']'));
}
function objFrom(file, re) {
  const t = fs.readFileSync(B + file, 'utf8');
  const m = re.exec(t);
  if (!m) throw new Error('not found: ' + re + ' in ' + file);
  return evalLit(grab(t, m.index + m[0].length - 1, '{', '}'));
}

console.log('== 1. 引擎与数据源 ==');
ok(F && typeof F.buildFullPack === 'function' && typeof F.verifyPack === 'function'
  && typeof F.applyFullPack === 'function' && typeof F.roundTripCheck === 'function'
  && typeof F.diffToEdits === 'function' && typeof F.applyEdits === 'function'
  && typeof F.stripMeta === 'function', '引擎导出全部关键 API');

const KB_LIBS = {
  daily: arrFrom('qa.html', /^const KB = \[/m),
  ccm: arrFrom('qa.html', /^window\.KB_CCM_RAW = \[/m),
  mgm: arrFrom('qa.html', /^window\.KB_MGM_RAW = \[/m),
  svc: arrFrom('qa.html', /^window\.KB_SVC_RAW = \[/m),
  dc: arrFrom('qa.html', /^window\.DC_KB = \[/m),
  cbt: arrFrom('qa.html', /^window\.KB_CBT_RAW = \[/m)
};
const SCRIPT_LIB = objFrom('beauty.html', /^\s*const scriptLibraryData = \{/m);
const PRODUCTS = arrFrom('beauty.html', /^\s*const products = \[/m);

function flattenScript(lib) {
  const out = [];
  Object.keys(lib).forEach(k => {
    const c = lib[k] || {};
    (c.scripts || []).forEach(s => out.push({ __cat: k, __label: c.label || k, id: s.id, content: s.content, tags: s.tags || [] }));
  });
  return out;
}
const SRC_DEF = [
  { id: 'daily', kind: 'kb', name: '日常库', origin: 'qa.html · KB' },
  { id: 'ccm', kind: 'kb', name: '乘务员手册', origin: 'qa.html · KB_CCM_RAW' },
  { id: 'mgm', kind: 'kb', name: '管理手册', origin: 'qa.html · KB_MGM_RAW' },
  { id: 'svc', kind: 'kb', name: '服务规范', origin: 'qa.html · KB_SVC_RAW' },
  { id: 'dc', kind: 'kb', name: '大撤专项', origin: 'qa.html · DC_KB' },
  { id: 'cbt', kind: 'kb', name: 'CBT 题库', origin: 'qa.html · KB_CBT_RAW' },
  { id: 'script', kind: 'script', name: '销售话术库', origin: 'beauty.html · scriptLibraryData' },
  { id: 'product', kind: 'product', name: '产品库', origin: 'beauty.html · products' }
];
const BASE = {
  daily: KB_LIBS.daily, ccm: KB_LIBS.ccm, mgm: KB_LIBS.mgm, svc: KB_LIBS.svc,
  dc: KB_LIBS.dc, cbt: KB_LIBS.cbt, script: flattenScript(SCRIPT_LIB), product: PRODUCTS
};
/* 基线固化 uid（与运行时 csInit 同序：先固化再谈编辑，否则 uid 会随增删错位） */
SRC_DEF.forEach(s => F.stampUids(BASE[s.id], s));
function sources() { return SRC_DEF.map(s => ({ id: s.id, name: s.name, kind: s.kind, origin: s.origin, items: BASE[s.id] })); }

ok(SRC_DEF.every(s => Array.isArray(BASE[s.id]) && BASE[s.id].length > 0), '8 个数据源全部取到非空条目',
  SRC_DEF.map(s => s.id + ':' + (BASE[s.id] || []).length).join(' '));
const TOTAL = SRC_DEF.reduce((a, s) => a + BASE[s.id].length, 0);
ok(TOTAL > 4000, '数据总量覆盖全部话术与手册数据（' + TOTAL + ' 条）');

console.log('\n== 2. 导出：全量包自洽 ==');
const pack = F.buildFullPack(sources(), { packId: 'full-test', exportedAt: '2026-09-21T00:00:00.000Z' });
ok(pack.magic === 'cabin-fullpack-v1' && pack.kind === 'full', '包 magic/kind 正确');
ok(pack.sources.length === 8, '包内含 8 个数据源');
ok(pack.summary.items === TOTAL, '包级条数与源一致（' + pack.summary.items + '）');
const v1 = F.verifyPack(pack);
ok(v1.ok, '导出后自检通过', (v1.errors || []).join('；'));
ok(pack.sources.every(s => s.count === s.items.length), '每个源声明条数与实际一致');
ok(pack.sources.every(s => s.items.every(it => it.uid && it.fp && it.data)), '每条都带 uid / 指纹 / 数据');
const uidSet = {};
let dupUid = 0;
pack.sources.forEach(s => s.items.forEach(it => { const k = s.id + '|' + it.uid; if (uidSet[k]) dupUid++; uidSet[k] = 1; }));
ok(dupUid === 0, '同一数据源内 uid 无重复');

console.log('\n== 3. 往返：导出 → 校验 → 还原 → 逐条深比对 ==');
const rt = F.roundTripCheck(sources());
ok(rt.ok, '往返自检整体通过（逐条内容一致）', rt.perSource.filter(p => !p.same).map(p => p.id + ':' + p.diffCount).join(' '));
ok(rt.perSource.length === 8, '往返覆盖 8 个数据源');
ok(rt.perSource.every(p => p.srcCount === p.outCount), '每个源还原条数与导出一致',
  rt.perSource.map(p => p.id + ' ' + p.srcCount + '/' + p.outCount).join(' '));
ok(rt.perSource.every(p => p.fpMismatch === 0), '还原后指纹全部复算一致');
ok(rt.stats && rt.stats.items === TOTAL, '往返统计条数正确（' + (rt.stats && rt.stats.items) + '）');

console.log('\n== 4. 识别：损坏/篡改必须被挡下 ==');
const p2 = JSON.parse(JSON.stringify(pack));
p2.sources[1].items[10].data.q = '被篡改的问题';
ok(!F.verifyPack(p2).ok, '内容被篡改 → 校验失败（指纹不符）');
const p3 = JSON.parse(JSON.stringify(pack));
p3.sources[2].items.splice(5, 1);
ok(!F.verifyPack(p3).ok, '少一条 → 校验失败（源校验和/声明条数不符）');
const p4 = JSON.parse(JSON.stringify(pack));
p4.magic = 'cabin-data-pack-v1';
const v4 = F.verifyPack(p4);
ok(!v4.ok && /旧版增量数据包/.test(v4.errors[0]), '旧增量包 protocol 被识别并给出明确指引');
const p5 = JSON.parse(JSON.stringify(pack));
p5.magic = 'x';
ok(!F.verifyPack(p5).ok, 'magic 不对 → 拒绝');
ok(!F.verifyPack(null).ok, '空输入 → 拒绝');
ok(!F.verifyPack({ magic: 'cabin-fullpack-v1' }).ok, '缺 sources → 拒绝');

console.log('\n== 5. 还原：工作区 == 包内容（导入闭环） ==');
const cur = {};
SRC_DEF.forEach(s => { cur[s.id] = BASE[s.id]; });
const ap = F.applyFullPack(pack, { mode: 'replace', current: cur });
ok(ap.ok, '整包还原执行成功');
ok(ap.report.every(r => r.packCount === r.outCount), '每个源还原输出条数 == 包内条数');
let metaDiff = 0;
SRC_DEF.forEach(s => {
  const want = (pack.sources.find(x => x.id === s.id).items || []).map(x => x.data);
  const got = ap.state[s.id] || [];
  const n = Math.max(want.length, got.length);
  for (let i = 0; i < n; i++) {
    if (!want[i] || !got[i]) { metaDiff++; continue; }
    if (F.stableStringify(F.stripMeta(want[i])) !== F.stableStringify(F.stripMeta(got[i]))) metaDiff++;
  }
});
ok(metaDiff === 0, '还原结果与包内容逐条一致（' + TOTAL + ' 条）', String(metaDiff));

/* 关键路径：导入后落编辑层，再读工作区，必须与包内容一致（忽略 _uid 元字段） */
const edits = {};
SRC_DEF.forEach(s => {
  const e = F.diffToEdits(BASE[s.id], ap.state[s.id], s);
  edits[s.id] = e;
});
let restoreDiff = 0;
SRC_DEF.forEach(s => {
  const work = F.applyEdits(BASE[s.id], edits[s.id], s);
  const want = (pack.sources.find(x => x.id === s.id).items || []).map(x => x.data);
  if (work.length !== want.length) { restoreDiff += Math.abs(work.length - want.length); return; }
  for (let i = 0; i < want.length; i++) {
    if (F.stableStringify(F.stripMeta(work[i])) !== F.stableStringify(F.stripMeta(want[i]))) restoreDiff++;
  }
});
ok(restoreDiff === 0, '导入后工作区 == 包内容（逐条一致）', String(restoreDiff));
ok(SRC_DEF.every(s => F.editStats(edits[s.id]).total === 0), '导入「未改动」的包不产生虚假改动（_uid 不算差异）',
  SRC_DEF.map(s => s.id + ':' + F.editStats(edits[s.id]).total).join(' '));

console.log('\n== 6. 编辑 / 删除 后导出再导入，仍完整还原 ==');
const eCcm = F.emptyEdits();
const ccmItem = JSON.parse(JSON.stringify(BASE.ccm[3]));
ccmItem.q = '（人工改过的问题）';
ccmItem[F.META_KEY] = 'ccm#3';
eCcm.mod['ccm#3'] = ccmItem;
eCcm.del.push('ccm#7');
eCcm.add.push({ uid: 'ccm#new-1', data: { cat: '新增', icon: '📘', src: 'CCM 9.9', t: ['人工'], q: '新增的问题', a: '新增的答案', _uid: 'ccm#new-1' } });
const workCcm = F.applyEdits(BASE.ccm, eCcm, SRC_DEF[1]);
ok(workCcm.length === BASE.ccm.length, '改1删1增1 → 条数不变');
ok(workCcm[3].q === '（人工改过的问题）', '修改生效');
ok(!workCcm.some(x => (x[F.META_KEY] || '') === 'ccm#7'), '删除生效');
ok(workCcm[workCcm.length - 1].q === '新增的问题', '新增追加在末尾');

const editedSources = sources().map(s => ({ id: s.id, name: s.name, kind: s.kind, origin: s.origin, items: s.id === 'ccm' ? workCcm : BASE[s.id] }));
const pack2 = F.buildFullPack(editedSources, { packId: 'full-edited', exportedAt: '2026-09-21T01:00:00.000Z' });
ok(F.verifyPack(pack2).ok, '含人工改动的包自检通过');
const ap2 = F.applyFullPack(pack2, { mode: 'replace' });
const e2 = F.diffToEdits(BASE.ccm, ap2.state.ccm, SRC_DEF[1]);
const work2 = F.applyEdits(BASE.ccm, e2, SRC_DEF[1]);
let d2 = 0;
if (work2.length !== workCcm.length) d2 += Math.abs(work2.length - workCcm.length);
else for (let i = 0; i < workCcm.length; i++) {
  if (F.stableStringify(F.stripMeta(work2[i])) !== F.stableStringify(F.stripMeta(workCcm[i]))) d2++;
}
ok(d2 === 0, '「编辑后导出 → 重新导入」工作区逐条一致', String(d2));
ok(work2[3] && work2[3].q === '（人工改过的问题）', '人工修改在往返后保留');
ok(!work2.some(x => (x[F.META_KEY] || '') === 'ccm#7'), '人工删除在往返后保留');
ok(F.editStats(e2).add === 1 && F.editStats(e2).del === 1, '往返后编辑层仍精确记录 增1/删1',
  JSON.stringify(F.editStats(e2)));

console.log('\n== 7. 合并模式 ==');
const mergeBase = JSON.parse(JSON.stringify(BASE.daily));
const packDaily = F.buildFullPack([{ id: 'daily', kind: 'kb', name: '日常库', items: [mergeBase[0]] }], { packId: 'd1' });
const apM = F.applyFullPack(packDaily, { mode: 'merge', current: { daily: mergeBase } });
ok(apM.state.daily.length === mergeBase.length, '合并模式不删现有条目');
const packNew = F.buildFullPack([{ id: 'daily', kind: 'kb', name: '日常库', items: [{ cat: '新', icon: '📘', src: 'NEW 1', t: [], q: '新问', a: '新答', _uid: 'daily#new-1' }] }], { packId: 'd2' });
const apM2 = F.applyFullPack(packNew, { mode: 'merge', current: { daily: mergeBase } });
ok(apM2.state.daily.length === mergeBase.length + 1, '合并模式追加包内新条目',
  apM2.state.daily.length + ' vs ' + (mergeBase.length + 1));
ok(apM2.report[0].added === 1 && apM2.report[0].updated === 0, '合并模式统计：新增 1 / 覆盖 0',
  JSON.stringify(apM2.report[0]));

console.log('\n== 8. 产物针（kb-admin.html 已带上库管理总台） ==');
const prod = fs.readFileSync(B + 'kb-admin.html', 'utf8');
[
  ['全量包引擎', 'cabin-fullpack-v1'],
  ['库管理视图', 'id="view-console"'],
  ['导出入口', 'csExportAll'],
  ['导入入口', 'csApplyImport'],
  ['往返自检', 'csRoundTrip'],
  ['编辑落盘', 'kb_console_edit_v1'],
  ['数据源注册表', 'CS_SOURCES'],
  ['大撤专项数据', '大撤专项·动态舱应急撤离流程'],
  ['CBT 题库数据', 'KB_CBT_RAW'],
  ['销售话术库', 'const BASE_SCRIPT_LIB'],
  ['产品库', 'const BASE_PRODUCTS'],
].forEach(function (p) { ok(prod.indexOf(p[1]) >= 0, '产物含 ' + p[0]); });
/* 占位符必须已被替换（注入块内的标记字面量除外，故统计出现次数） */
['__BASE_DC_ARR__', '__BASE_CBT_ARR__'].forEach(function (ph) {
  const n = prod.split(ph).length - 1;
  ok(n === 0, '占位符已替换：' + ph);
});

console.log('\n===== 汇总 =====');
console.log('通过 ' + pass + ' / ' + (pass + fail));
if (fail) {
  console.log('失败项：');
  fails.forEach(f => console.log('  - ' + f));
  process.exit(1);
}
console.log('库管理完整数据包：导出/导入/往返一致性 全绿。');
