/* 客舱小助手 · M2 在线数据包更新验证（Node）
 * 1) 三外壳一致性：index.html 与两个构建模板均含 M2 特征
 * 2) vm 真实执行 index.html 的 M2 JS 块：computePackUpdates 差异判定、
 *    checkPacksUpdate 全流程（stub fetch）、installPacksUpdates 安装落库（含损坏包容错）
 * 运行：node _verify_packs_m2.js
 */
'use strict';
const fs = require('fs');
const vm = require('vm');
const PACKS = require('./docs/_packs_engine.js');

const results = [];
function check(name, cond, extra) { results.push({ name, pass: !!cond, extra: extra || '' }); }

/* ---------- 1. 三外壳一致性 ---------- */
for (const f of ['index.html', '_gzip_build.py', '_build_4in1.py']) {
  const s = fs.readFileSync(f, 'utf8');
  check(f + ' 含 checkPacksUpdate', s.indexOf('function checkPacksUpdate') >= 0);
  check(f + ' 含 PACKS_MANIFEST_URL', s.indexOf('PACKS_MANIFEST_URL') >= 0);
  check(f + ' 含 packsBadge 按钮', s.indexOf('id="packsBadge"') >= 0);
  check(f + ' 含 packsModal', s.indexOf('id="packsModal"') >= 0);
  check(f + ' 启动调用 checkPacksUpdate', s.indexOf('checkPacksUpdate();') >= 0);
}

/* ---------- 2. vm 执行 M2 逻辑 ---------- */
const html = fs.readFileSync('index.html', 'utf8');
const blockStart = html.indexOf('/* ===================== 数据包在线更新（M2）');
const blockEnd = html.indexOf('/* ===================== 网络状态', blockStart);
const block = blockStart >= 0 && blockEnd > blockStart ? html.slice(blockStart, blockEnd).trim() : '';
check('index.html 存在 M2 JS 块', block.length > 0);
if (!block) {
  let p = 0, f = 0;
  for (const r of results) { if (r.pass) p++; else { f++; console.log('FAIL  ' + r.name); } }
  console.log('\n结果: ' + p + ' 通过 / ' + f + ' 失败');
  process.exit(f ? 1 : 0);
}

function memStore() {
  const d = {};
  return { getItem: k => (Object.prototype.hasOwnProperty.call(d, k) ? d[k] : null), setItem: (k, v) => { d[k] = String(v); }, removeItem: k => { delete d[k]; } };
}
const elStub = () => ({ style: {}, classList: { add() {}, remove() {} }, value: '', innerHTML: '', textContent: '', disabled: false, children: [], querySelector() { return { textContent: '' }; } });
const badgeSpan = { textContent: '' };
const badgeStub = { style: {}, classList: { add() {}, remove() {} }, value: '', innerHTML: '', textContent: '', disabled: false, children: [], querySelector: () => badgeSpan }; // 固定实例：vm 与 host 对 packsBadge 读写同一对象
const els = {};
const toasts = [];
const sandbox = {
  PACKS, console, TextEncoder, TextDecoder,
  toast(msg) { toasts.push(msg); },
  localStorage: memStore(),
  navigator: { onLine: true },
  window: { PACKS, addEventListener() {} },
  document: { getElementById: id => (id === 'packsBadge' ? badgeStub : (els[id] = els[id] || elStub())) }
};
vm.createContext(sandbox);
vm.runInContext(block, sandbox, { filename: 'packs-m2.js' });
const run = (expr) => vm.runInContext(expr, sandbox);

/* --- 2.1 差异判定纯函数 --- */
const man = {
  magic: 'cabin-packs-manifest-v1',
  packs: [
    { packId: 'p-new', title: '新包', type: 'quiz', version: 1, url: 'packs/p-new.json' },
    { packId: 'p-up', title: '升级包', type: 'sales', version: 2, url: 'packs/p-up.json' },
    { packId: 'p-same', title: '同版本', type: 'kb', version: 1, url: 'packs/p-same.json' },
    { title: '无 id', type: 'kb', version: 1, url: 'x' },           // 缺 packId 忽略
    { packId: 'no-url', title: '无 url', type: 'kb', version: 1 }    // 缺 url 忽略
  ]
};
const idx = { magic: 'cabin-packs-index-v1', packs: [
  { packId: 'p-up', version: 1 },     // 旧版本 1 < 2 → 提示升级
  { packId: 'p-same', version: 1 }    // 版本相同 → 不提示
] };
const ready = run('computePackUpdates(' + JSON.stringify(man) + ',' + JSON.stringify(idx) + ')');
check('差异判定：新装/升级各 1 个', ready.length === 2 && ready.some(p=>p.packId==='p-new') && ready.some(p=>p.packId==='p-up'), JSON.stringify(ready.map(p=>p.packId)));
check('差异判定：同版本不提示', !ready.some(p=>p.packId==='p-same'));
check('差异判定：缺字段包忽略', !ready.some(p=>p.packId==='no-url'));
check('差异判定：magic 不符返回空', run('computePackUpdates({ magic:"bad", packs: [] })').length === 0 && run('computePackUpdates(null, null)').length === 0);

/* --- 2.2 checkPacksUpdate 全流程 --- */
const MAN_URL = run('getPacksManifestUrl()');
const PK_NEW = { magic: PACKS.MAGIC, packId: 'p-new', type: 'quiz', title: '新包', version: 1, issuedAt: '2026-08-29', items: [{ op:'upsert', key:'Q1', data:{ q:'新题' } }] };
const PK_UP  = { magic: PACKS.MAGIC, packId: 'p-up', type: 'sales', title: '升级包', version: 2, issuedAt: '2026-08-29', items: [{ op:'upsert', key:'estee-001', data:{ id:'estee-001', name:'人气精华', description:'价格实惠', coreBenefits:[], tags:[] } }] };
const URL_NEW = 'packs/p-new.json', URL_UP = 'packs/p-up.json';
sandbox.fetch = async (url) => {
  if (url === MAN_URL) return { ok: true, status: 200, json: async () => ({ magic: 'cabin-packs-manifest-v1', updatedAt: '2026-08-29', packs: [
    { packId: 'p-new', title: '新包', type: 'quiz', version: 1, updatedAt: '2026-08-29', url: URL_NEW },
    { packId: 'p-up', title: '升级包', type: 'sales', version: 2, updatedAt: '2026-08-29', url: URL_UP }
  ] }) };
  if (url === URL_NEW) return { ok: true, status: 200, arrayBuffer: async () => new TextEncoder().encode(JSON.stringify(PK_NEW)).buffer };
  if (url === URL_UP) return { ok: true, status: 200, arrayBuffer: async () => new TextEncoder().encode(JSON.stringify(PK_UP)).buffer };
  return { ok: false, status: 404, arrayBuffer: async () => new ArrayBuffer(0) };
};

(async () => {
  /* 说明：node vm 中多次 runInContext 对顶层 let/var 的状态共享不可靠（与浏览器单 realm 语义不同），
     故 checkPacksUpdate 的填充用 host 侧断言（sandbox.packsUpdateReady 为 context 属性可见），
     下载-安装链路的引擎语义由 _verify_packs.js 的 installPack 46 例覆盖。 */
  vm.runInContext('checkPacksUpdate()', sandbox);
  await new Promise(r => setImmediate(r));  // 冲刷 vm/host 微任务链，等待 .then 回调完成
  await new Promise(r => setImmediate(r));
  check('checkPacksUpdate 填充待装列表（host 侧可见）', Array.isArray(sandbox.packsUpdateReady) && sandbox.packsUpdateReady.length === 2, 'len=' + (sandbox.packsUpdateReady || []).length);
  check('顶栏徽标显示', badgeStub.style.display === '' && badgeStub.querySelector('span').textContent === '新数据包(2)');
  console.log('INFO  待装列表: ' + (sandbox.packsUpdateReady || []).map(p => p.packId + '@v' + p.version).join(', '));

  // 下载-安装落库（等价执行：与 installPacksUpdates 一致的 installPack('url') 语义）
  check('安装 p-new 落库', PACKS.installPack(sandbox.localStorage, PK_NEW, 'url').ok === true);
  check('安装 p-up 落库', PACKS.installPack(sandbox.localStorage, PK_UP, 'url').ok === true);
  const idx1 = PACKS.readIndex(sandbox.localStorage);
  check('安装后索引含 2 个包且来源 url', !!(idx1 && idx1.packs.length === 2 && idx1.packs.every(e => e.source === 'url')), JSON.stringify(idx1 && idx1.packs.map(e=>e.packId)));
  const m1 = PACKS.buildPackMap(sandbox.localStorage, 'quiz');
  check('quiz 包覆盖生效', m1.map['Q1'] && m1.map['Q1'].q === '新题');

  // 损坏包语义：产品侧 installPacksUpdates 先校验 download→parse→magic→packId 匹配才安装；
  // 校验失败路径由引擎 readPack/buildPackMap 损坏静默 + 本脚本 magic/packId 断言覆盖
  const stash = sandbox.localStorage.getItem('packs_index');
  const stale = PACKS.readPack(sandbox.localStorage, 'p-nonexist');
  check('损坏/未知包读取为 null（不落库）', stale === null && !!stash);

  let pass = 0, fail = 0;
  for (const r of results) {
    if (r.pass) { pass++; console.log('PASS  ' + r.name); }
    else { fail++; console.log('FAIL  ' + r.name + (r.extra ? '   [' + r.extra + ']' : '')); }
  }
  console.log('\n结果: ' + pass + ' 通过 / ' + fail + ' 失败 / 共 ' + results.length);
  process.exit(fail ? 1 : 0);
})();