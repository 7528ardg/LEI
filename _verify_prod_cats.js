/* 商品库 × 品类路由 × 竞品库 结构核验（Node，无浏览器）
 * 用法：node _verify_prod_cats.js
 * 覆盖：
 *   A 商品必填字段完整（话术可调用前提）
 *   B 每个品类都能被两套话术引擎正确分型（不误落「纪念品」框架）
 *   C 每个品类都有 CATEGORY_SCENE 场景（或经 _catAlias 命中）
 *   D 每个品类都能被话术工作台「品类选择」命中
 *   E 竞品库 id 唯一 / 价格行完整 / 字段齐全
 */
'use strict';
const fs = require('fs');
const vm = require('vm');

const results = [];
function check(name, cond, extra) {
  results.push({ name, pass: !!cond, extra: extra || '' });
}

const html = fs.readFileSync('beauty.html', 'utf8');

/* ---------- 1. 提取数据 ---------- */
function grab(declRe, closeRe) {
  const m = html.match(declRe);
  if (!m) throw new Error('未找到 ' + declRe);
  const start = m.index + m[0].length - 1;
  // 括号配平（跨字符串）
  const open = html[start];
  const close = { '[': ']', '{': '}' }[open];
  let depth = 0, i = start, inStr = null, esc = false;
  for (; i < html.length; i++) {
    const c = html[i];
    if (inStr) {
      if (esc) esc = false;
      else if (c === '\\') esc = true;
      else if (c === inStr) inStr = null;
      continue;
    }
    if (c === '"' || c === "'" || c === '`') { inStr = c; continue; }
    if (c === open) depth++;
    else if (c === close) { depth--; if (depth === 0) return eval('(' + html.slice(start, i + 1) + ')'); }
  }
  throw new Error('括号未配平: ' + declRe);
}
const products = grab(/const products = \[/, null);
const competitors = grab(/const competitorData = \[/, null);

/* ---------- 2. 提取两套引擎的分型表 ---------- */
function grabFn(name) {
  const re = new RegExp('const SKINCARE_CATS[\\s\\S]*?function ' + name + '\\(p\\)\\{[\\s\\S]*?\\n  \\}');
  const all = [];
  let m, r = new RegExp(re.source, 'g');
  while ((m = r.exec(html)) !== null) all.push(m[0]);
  return all;
}
const bigTypeFns = grabFn('bigType');
check('提取到两套 bigType 分型函数', bigTypeFns.length === 2, '实得 ' + bigTypeFns.length);

const btNames = [];
bigTypeFns.forEach((src, i) => {
  const sandbox = {};
  vm.createContext(sandbox);
  vm.runInContext(src + '\nthis.__bt = bigType;', sandbox);
  btNames.push(sandbox.__bt);
});
const [btA, btB] = btNames; // A=beautySceneEngine, B=talkShowEngine

/* ---------- 3. 提取 CATEGORY_SCENE + _catAlias ---------- */
const sceneM = html.match(/const CATEGORY_SCENE = \{[\s\S]*?\n  \};/);
check('提取到 CATEGORY_SCENE', !!sceneM);
const sceneKeys = new Set([...sceneM[0].matchAll(/^\s*'([^']+)':\s*\{/gm)].map(x => x[1]));
const aliasM = html.match(/const _catAlias = \{([^}]*)\};/);
const aliases = new Map([...aliasM[1].matchAll(/'([^']+)'\s*:\s*'([^']+)'/g)].map(x => [x[1], x[2]]));

/* ---------- 4. 提取话术工作台品类选项 ---------- */
const optM = html.match(/const SCRIPT_CATEGORY_OPTIONS = \[[\s\S]*?\n        \];/);
check('提取到 SCRIPT_CATEGORY_OPTIONS', !!optM);
const optCats = new Set([...optM[0].matchAll(/cats:\s*\[([^\]]*)\]/g)]
  .flatMap(x => [...x[1].matchAll(/'([^']+)'/g)].map(y => y[1])));

/* ---------- A 商品必填字段 ---------- */
const REQ = ['id', 'name', 'brand', 'category', 'description', 'tale', 'coreBenefits', 'targetSkinTypes', 'keyIngredients', 'unsuitable', 'tags', 'reviewCount'];
const bad = products.filter(p => REQ.some(k => p[k] === undefined || p[k] === null || (Array.isArray(p[k]) && k !== 'unsuitable' && !p[k].length)));
check('A 商品必填字段完整（' + products.length + ' 款）', bad.length === 0,
  bad.slice(0, 12).map(p => p.id + ' 缺:' + REQ.filter(k => p[k] === undefined || p[k] === null || (Array.isArray(p[k]) && k !== 'unsuitable' && !p[k].length)).join('/')).join(' | '));

/* ---------- B/C/D 品类路由 ---------- */
const cats = [...new Set(products.map(p => p.category))].sort();
const bMiss = [], cMiss = [], dMiss = [];
cats.forEach(c => {
  const a = btA({ category: c, brand: 'x' });
  const b = btB({ category: c, brand: 'x' });
  const isSouv = (c === '纪念品');
  if (!isSouv && (a === 'souvenir' || b === 'souvenir')) bMiss.push(c + ' → A:' + a + ' B:' + b);
  const sc = aliases.get(c) || c;
  if (!sceneKeys.has(sc)) cMiss.push(c + (aliases.has(c) ? '(→' + sc + ')' : ''));
  if (!optCats.has(c) && !aliases.has(c)) dMiss.push(c);
});
check('B 品类分型不误落「纪念品」（' + cats.length + ' 类）', bMiss.length === 0, bMiss.join(' | '));
check('C 品类均有场景开场（含别名）', cMiss.length === 0, cMiss.join(' | '));
check('D 品类均可在话术工作台选中', dMiss.length === 0, dMiss.join(' | '));

/* ---------- E 竞品库 ---------- */
const cids = new Set(), cdup = [];
competitors.forEach(c => { if (cids.has(c.id)) cdup.push(c.id); cids.add(c.id); });
check('E1 竞品 id 唯一（' + competitors.length + ' 条）', cdup.length === 0, cdup.join(','));
const nop = competitors.filter(c => !c.prices || !c.prices.length);
check('E2 竞品均有价格行', nop.length === 0, nop.map(c => c.name).join(' | '));
const CREQ = ['name', 'brand', 'category', 'ingredients', 'advantages', 'disadvantages', 'complianceNote', 'updateTime'];
const cbad = competitors.filter(c => CREQ.some(k => !c[k] || (Array.isArray(c[k]) && !c[k].length)));
check('E3 竞品字段齐全', cbad.length === 0, cbad.map(c => c.id + ':' + CREQ.filter(k => !c[k] || (Array.isArray(c[k]) && !c[k].length)).join('/')).join(' | '));
const badPrice = [];
competitors.forEach(c => (c.prices || []).forEach((pr, i) => {
  if (!pr.platform || !pr.size || typeof pr.price !== 'number' || pr.price <= 0 || !pr.updateTime) badPrice.push(c.id + '#price' + i);
}));
check('E4 价格行字段与数值合法', badPrice.length === 0, badPrice.slice(0, 10).join(','));

// E5/E6 更新时间口径：条目级为 YYYY-MM-DD；价格行为「YYYY年MM月DD日 联网更新」或「沿用上期数据…」
const entBadTime = competitors.filter(c => !/^\d{4}-\d{2}-\d{2}$/.test(String(c.updateTime || '')));
check('E5 竞品条目级 updateTime 为 YYYY-MM-DD', entBadTime.length === 0,
  entBadTime.slice(0, 8).map(c => c.id + ':' + c.updateTime).join(' | '));
const rowBadTime = [];
competitors.forEach(c => (c.prices || []).forEach((pr, i) => {
  const u = String(pr.updateTime || '');
  if (!/^\d{4}年\d{2}月\d{2}日 联网更新$/.test(u) && u.indexOf('沿用上期数据') < 0) rowBadTime.push(c.id + '#' + i + ':' + u);
}));
check('E6 价格行 updateTime 为联网口径', rowBadTime.length === 0, rowBadTime.slice(0, 8).join(' | '));

/* ---------- 汇总 ---------- */
const failed = results.filter(r => !r.pass);
results.forEach(r => console.log((r.pass ? '  PASS  ' : '  FAIL  ') + r.name + (r.pass || !r.extra ? '' : '\n         ' + r.extra)));
console.log('\n通过 ' + (results.length - failed.length) + ' / ' + results.length + '；失败 ' + failed.length);
if (failed.length) process.exit(1);
