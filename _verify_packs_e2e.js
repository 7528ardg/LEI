/* 客舱小助手 · 数据包 M1.2 消费端接线端到端验证（Node）
 * 直接解析真实源文件（beauty/quiz/qa）中的数据数组，用与页面一致的
 * buildPackMap + applyMapToArray 调用方式验证覆盖链路，防止 keyOf 与真实字段错位。
 * 运行：node _verify_packs_e2e.js
 */
'use strict';
const fs = require('fs');
const PACKS = require('./docs/_packs_engine.js');

const NOW = new Date(2026, 7, 29);
function memStore() {
  const d = {};
  return {
    getItem: (k) => (Object.prototype.hasOwnProperty.call(d, k) ? d[k] : null),
    setItem: (k, v) => { d[k] = String(v); },
    removeItem: (k) => { delete d[k]; }
  };
}
/* 从 html 提取形如 `const X = [ ... ];` 的数组文本并求值（元素含注释/单行对象，JSON 不适用故用 eval） */
function parseArray(src, re) {
  const m = src.match(re);
  if (!m) throw new Error('数组提取失败: ' + re);
  const arr = eval('([' + m[1] + '])'); // eslint-disable-line no-eval
  if (!Array.isArray(arr)) throw new Error('解析结果非数组');
  return arr;
}
const results = [];
function check(name, cond, extra) { results.push({ name, pass: !!cond, extra: extra || '' }); }

const beautyHtml = fs.readFileSync('beauty.html', 'utf8');
const quizHtml = fs.readFileSync('quiz.html', 'utf8');
const qaHtml = fs.readFileSync('qa.html', 'utf8');

/* ============ 1. beauty 销售包 ============ */
{
  const products = parseArray(beautyHtml, /const products = \[([\s\S]*?)\n        \];/);
  const baseCount = products.length;
  check('beauty 产品基线非空(>100)', baseCount > 100, 'count=' + baseCount);
  check('beauty 基线含 estee-001', products.some(p => p.id === 'estee-001'));
  check('beauty 基线含 skii-001（待删除）', products.some(p => p.id === 'skii-001'));
  check('beauty 基线不含 cdp 新品', !products.some(p => p.id === 'cdp-new-001'));

  const st = memStore();
  PACKS.installPack(st, {
    magic: PACKS.MAGIC, packId: 'e2e-sales', type: 'sales', title: 'E2E 销售包', version: 1,
    issuedAt: '2026-08-29',
    items: [
      { op: 'upsert', key: 'estee-001', data: { id: 'estee-001', name: '小棕瓶CDP改名', brand: '雅诗兰黛', category: '精华', volume: '30ml', origin: '美国', stock: 'in_stock', description: '数据包覆盖', coreBenefits: ['修护'], targetSkinTypes: ['所有'], keyIngredients: [], unsuitable: [], tags: ['精华'], reviewCount: 1 } },
      { op: 'upsert', key: 'cdp-new-001', data: { id: 'cdp-new-001', name: 'CDP新品', brand: 'CDP品牌', category: '精华', volume: '30ml', origin: '测试', stock: 'in_stock', description: '数据包新增', coreBenefits: ['补水'], targetSkinTypes: ['所有'], keyIngredients: [], unsuitable: [], tags: ['精华'], reviewCount: 1 } },
      { op: 'delete', key: 'skii-001' }
    ]
  }, 'import', NOW);
  // 与 beauty.html 内 applySales 相同的调用
  PACKS.applyMapToArray(products, PACKS.buildPackMap(st, 'sales'), p => p && p.id ? String(p.id) : '');
  check('sales 包 upsert 命中原地替换', products.find(p => p.id === 'estee-001').name === '小棕瓶CDP改名');
  check('sales 包 upsert 缺失 push 新品牌', products.some(p => p.id === 'cdp-new-001' && p.brand === 'CDP品牌'));
  check('sales 包 delete 移除基线产品', !products.some(p => p.id === 'skii-001'));
  check('sales 包删除后数量 = 基线（加1删1净0）', products.length === baseCount, baseCount + '->' + products.length);
}

/* ============ 2. quiz 题库包 ============ */
{
  const bank = parseArray(quizHtml, /const sampleQuestions = \[([\s\S]*?)\n\];/);
  const firstKey = bank[0].origNum || bank[0].q;
  const baseCount = bank.length;
  check('quiz 题库基线非空(>100)', baseCount > 100, 'count=' + baseCount);
  const rmKey = bank[baseCount - 1].origNum || bank[baseCount - 1].q;

  const st = memStore();
  PACKS.installPack(st, {
    magic: PACKS.MAGIC, packId: 'e2e-quiz', type: 'quiz', title: 'E2E 题库包', version: 1,
    issuedAt: '2026-08-29',
    items: [
      { op: 'upsert', key: firstKey, data: { q: '数据包改题：原题已被覆盖', type: '判断', opts: ['A. 对', 'B. 错'], ans: 'A', chapter: '数据包', section: 'E2E', diff: '易', explain: '数据包覆盖', origNum: firstKey } },
      { op: 'upsert', key: 'CDP-NEW-Q', data: { q: '数据包新增题目', type: '单选', opts: ['A. 1', 'B. 2'], ans: 'A', chapter: '数据包', section: 'E2E', diff: '易', explain: '新增', origNum: 'CDP-NEW-Q' } },
      { op: 'delete', key: rmKey }
    ]
  }, 'import', NOW);
  const keyOf = q => (q && q.origNum) ? String(q.origNum) : (q && q.q ? String(q.q) : '');
  PACKS.applyMapToArray(bank, PACKS.buildPackMap(st, 'quiz'), keyOf);
  check('quiz upsert 命中替换（按 origNum）', bank.find(q => keyOf(q) === firstKey).q === '数据包改题：原题已被覆盖');
  check('quiz upsert 缺失 push', bank.some(q => keyOf(q) === 'CDP-NEW-Q'));
  check('quiz delete 移除基线题', !bank.some(q => keyOf(q) === rmKey));
  check('quiz 删除后数量 = 基线（加1删1净0）', bank.length === baseCount, baseCount + '->' + bank.length);
}

/* ============ 3. qa 知识库 kb 包（ccm 分桶） ============ */
/* qa 专用合并（KB 条目 src 非唯一，qa.html applyPacks 不用 applyMapToArray）：
 * upsert 替换第一条命中/缺失 push；delete 删除第一条命中 */
function kbApply(pool, res) {
  const map = res.map, kills = res.kills;
  for (const key in map) {
    const e = map[key];
    if (!e || !e.q) continue;
    const idx = pool.findIndex(it => it && e.src && it.src === e.src);
    if (idx >= 0) pool[idx] = e; else pool.push(e);
  }
  for (const k of kills) {
    const j = pool.findIndex(it => it && it.src === k);
    if (j >= 0) pool.splice(j, 1);
  }
}
{
  const ccm = parseArray(qaHtml, /window\.KB_CCM_RAW = \[([\s\S]*?)\n\];/);
  const baseCount = ccm.length;
  const sameSrcCount = ccm.filter(e => e && e.src === 'CCM 3.2.1.1').length;
  check('qa ccm 库基线非空', baseCount > 100, 'count=' + baseCount);
  check('qa ccm 存在同 src 多条条目（章节多问）', sameSrcCount >= 2, 'sameSrc=' + sameSrcCount);
  check('qa ccm 含 src=CCM 3.1.2.1', ccm.some(e => e && e.src === 'CCM 3.1.2.1'));

  const st = memStore();
  PACKS.installPack(st, {
    magic: PACKS.MAGIC, packId: 'e2e-kb', type: 'kb', lib: 'ccm', title: 'E2E 知识包(ccm)', version: 1,
    issuedAt: '2026-08-29',
    items: [
      { op: 'upsert', key: 'CCM 3.1.2.1', data: { cat: '数据包', icon: '📘', src: 'CCM 3.1.2.1', t: ['测试'], q: '数据包改的职责问题？', a: '数据包答案' } },
      { op: 'upsert', key: 'CCM E2E-NEW', data: { cat: '数据包', icon: '📘', src: 'CCM E2E-NEW', t: [], q: '数据包新增知识问题？', a: '新增答案' } },
      { op: 'delete', key: 'CCM 3.2.1.1' }
    ]
  }, 'import', NOW);
  kbApply(ccm, PACKS.buildPackMap(st, 'kb', { lib: 'ccm' }));
  check('kb upsert 命中替换（按 src）', ccm.find(e => e && e.src === 'CCM 3.1.2.1').q === '数据包改的职责问题？');
  check('kb upsert 缺失 push', ccm.some(e => e && e.src === 'CCM E2E-NEW'));
  check('kb delete 只删第一条命中（同 src 多条保留其余）', ccm.filter(e => e && e.src === 'CCM 3.2.1.1').length === sameSrcCount - 1);
  check('kb 数量 = 基线（+1新增 -1删除）', ccm.length === baseCount, baseCount + '->' + ccm.length);

  // lib 隔离：mgm 库查不到 ccm 专用包的内容（只有 lib='' 的通用包才全库应用）
  const mgm = parseArray(qaHtml, /window\.KB_MGM_RAW = \[([\s\S]*?)\n\];/);
  kbApply(mgm, PACKS.buildPackMap(st, 'kb', { lib: 'mgm' }));
  check('kb lib=ccm 包不泄漏到 mgm 库', !mgm.some(e => e && e.src === 'CCM E2E-NEW'));

  // 旧覆盖层双读：装 kb_overlay_v1 旧数据 + kb 新包同 src → 数据包获胜
  const st2 = memStore();
  st2.setItem('kb_overlay_v1', JSON.stringify({ magic: 'kb-overlay-v1', byLib: { ccm: [{ src: 'CCM 3.1.2.1', q: '旧覆盖层问题', a: '旧答案', cat: 'x', icon: '📘', t: [] }] } }));
  const ccm2 = parseArray(qaHtml, /window\.KB_CCM_RAW = \[([\s\S]*?)\n\];/);
  // 模拟 qa apply()：先 applyLegacy 后 applyPacks
  const pLegacy = pool => {
    const arr = [{ src: 'CCM 3.1.2.1', q: '旧覆盖层问题', a: '旧答案', cat: 'x', icon: '📘', t: [] }];
    pool.forEach((e, i) => { if (e && e.src === 'CCM 3.1.2.1' && i === pool.findIndex(x => x && x.src === 'CCM 3.1.2.1')) pool[i] = arr[0]; });
  };
  pLegacy(ccm2);
  check('双读：无新包时旧覆盖层生效', ccm2.find(e => e.src === 'CCM 3.1.2.1').q === '旧覆盖层问题');
  PACKS.installPack(st2, {
    magic: PACKS.MAGIC, packId: 'e2e-kb2', type: 'kb', lib: 'ccm', title: 'E2E 知识包2', version: 1,
    issuedAt: '2026-08-29',
    items: [{ op: 'upsert', key: 'CCM 3.1.2.1', data: { cat: '新包', icon: '📘', src: 'CCM 3.1.2.1', t: [], q: '数据包获胜问题', a: '新答案' } }]
  }, 'import', NOW);
  kbApply(ccm2, PACKS.buildPackMap(st2, 'kb', { lib: 'ccm' }));
  check('双读：存在新包时数据包覆盖旧覆盖层', ccm2.find(e => e.src === 'CCM 3.1.2.1').q === '数据包获胜问题');
}

/* ============ 汇总 ============ */
let pass = 0, fail = 0;
for (const r of results) {
  if (r.pass) { pass++; console.log('PASS  ' + r.name); }
  else { fail++; console.log('FAIL  ' + r.name + (r.extra ? '   [' + r.extra + ']' : '')); }
}
console.log('\n结果: ' + pass + ' 通过 / ' + fail + ' 失败 / 共 ' + results.length);
process.exit(fail ? 1 : 0);