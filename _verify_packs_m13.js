/* 客舱小助手 · kb-admin 数据包中心 M1.3 验证（Node）
 * 1) 模板与构建产物特征串断言（防 _build_kbadmin.py 重建时丢失新功能）
 * 2) 在 vm 沙箱中真实执行模板"数据包中心"JS 块：magic/type 校验、sales 合规拦截、安装落库
 * 运行：node _verify_packs_m13.js
 */
'use strict';
const fs = require('fs');
const vm = require('vm');
const PACKS = require('./docs/_packs_engine.js');

const TPL = 'kb-admin.template.html';
const OUT = 'kb-admin.html';
const FEATURES = ['data-v="packs"', 'view-packs', '数据包中心', 'PACK_COMPLIANCE', 'renderPacks', 'importPackText', 'makeSamplePack', 'migrateLegacyOverlay'];

const results = [];
function check(name, cond, extra) { results.push({ name, pass: !!cond, extra: extra || '' }); }

for (const f of [TPL, OUT]) {
  const s = fs.readFileSync(f, 'utf8');
  for (const feat of FEATURES) {
    check(f + ' 含特征 [' + feat + ']', s.indexOf(feat) >= 0);
  }
}

/* ============ 真实执行模板内数据包中心逻辑 ============ */
const tpl = fs.readFileSync(TPL, 'utf8');
const mBlock = tpl.match(/\/\* ===================== 数据包中心（M1.3） ===================== \*\/([\s\S]*?)\n\/\* ===================== 体检/);
check('模板中存在数据包中心 JS 块', !!(mBlock && mBlock[1]));
if (!(mBlock && mBlock[1])) {
  let p = 0, f = 0;
  for (const r of results) { if (r.pass) p++; else { f++; console.log('FAIL  ' + r.name); } }
  console.log('\n结果: ' + p + ' 通过 / ' + f + ' 失败');
  process.exit(f ? 1 : 0);
}

function memStore() {
  const d = {};
  return { getItem: k => (Object.prototype.hasOwnProperty.call(d, k) ? d[k] : null), setItem: (k, v) => { d[k] = String(v); }, removeItem: k => { delete d[k]; } };
}
const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const elStub = { value: '', addEventListener() {}, className: '', innerHTML: '' };
const sandbox = {
  PACKS, esc, console,
  toast() {}, openModal() {},
  localStorage: memStore(),
  $() { return elStub; }
};
vm.createContext(sandbox);
vm.runInContext(mBlock[1], sandbox, { filename: 'packs-center.js' });
const P = sandbox; // vm 顶层声明的 function/const 挂到上下文全局

/* --- magic 校验 --- */
{
  const r = P.importPackText('{not-json');
  check('非 JSON 文本被拒', r.ok === false);
  const r2 = P.importPackText(JSON.stringify({ magic: 'wrong', packId: 'x', type: 'sales', items: [] }));
  check('错误 magic 被拒', r2.ok === false && String(r2.msg).indexOf('magic') >= 0);
  const r3 = P.importPackText(JSON.stringify({ magic: PACKS.MAGIC, packId: 'x', type: 'sales' }));
  check('缺 items 被拒', r3.ok === false);
  const r4 = P.importPackText(JSON.stringify({ magic: PACKS.MAGIC, packId: 'x', type: 'bogus', items: [{}] }));
  check('未知 type 被拒', r4.ok === false && String(r4.msg).indexOf('type') >= 0);
}
/* --- 合规拦截 --- */
{
  const bad = { magic: PACKS.MAGIC, packId: 'bad-sales', type: 'sales', title: '违规测试', version: 1, issuedAt: '2026-08-29',
    items: [{ op: 'upsert', key: 'k', data: { id: 'k', name: '爆款面膜', description: '全网最低价，手慢无', coreBenefits: [], tags: [] } }] };
  const r = P.importPackText(JSON.stringify(bad));
  check('sales 包含违禁词被拒（爆款/最低价/手慢无）', r.ok === false && String(r.msg).indexOf('爆款') >= 0 && String(r.msg).indexOf('最低价') >= 0 && String(r.msg).indexOf('手慢无') >= 0);
  check('违规包未写入存储', PACKS.readIndex(sandbox.localStorage) === null);
  const hits = P.checkPackCompliance('这款人气精华是明星产品，错过就没有了');
  check('合规检查文本命中', hits.length === 2, 'hits=' + hits.length);
}
/* --- 合规包正常安装 --- */
{
  const good = { magic: PACKS.MAGIC, packId: 'ok-sales', type: 'sales', title: '合规销售包', version: 1, issuedAt: '2026-08-29',
    items: [{ op: 'upsert', key: 'estee-001', data: { id: 'estee-001', name: '人气精华', description: '价格实惠，含税一价全包', coreBenefits: [], tags: [] } }] };
  const r = P.importPackText(JSON.stringify(good));
  check('合规 sales 包安装成功', r.ok === true && r.count === 1);
  check('安装后索引存在', sandbox.localStorage.getItem('packs_index') !== null);
  check('安装后包数据存在', sandbox.localStorage.getItem('pack:ok-sales') !== null);
  const m = PACKS.buildPackMap(sandbox.localStorage, 'sales');
  check('安装后引擎可读到覆盖', m.map['estee-001'] && m.map['estee-001'].name === '人气精华');
}
/* --- quiz 包 --- */
{
  const q = { magic: PACKS.MAGIC, packId: 'ok-quiz', type: 'quiz', title: '新题包', version: 1, issuedAt: '2026-08-29',
    items: [{ op: 'upsert', key: 'NEW-Q1', data: { q: '新题', origNum: 'NEW-Q1' } }] };
  const r = P.importPackText(JSON.stringify(q));
  check('quiz 包安装成功', r.ok === true);
  const m = PACKS.buildPackMap(sandbox.localStorage, 'quiz');
  check('quiz 覆盖生效', m.map['NEW-Q1'].q === '新题');
}

let pass = 0, fail = 0;
for (const r of results) {
  if (r.pass) { pass++; console.log('PASS  ' + r.name); }
  else { fail++; console.log('FAIL  ' + r.name + (r.extra ? '   [' + r.extra + ']' : '')); }
}
console.log('\n结果: ' + pass + ' 通过 / ' + fail + ' 失败 / 共 ' + results.length);
process.exit(fail ? 1 : 0);