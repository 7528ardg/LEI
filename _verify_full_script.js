/* 客舱小助手 · 全话术链路回归测试（Node）
 * 随机 ≥24 套组合（数量 1~8 随机、品类随机、时长 2~12 随机），逐套审计
 * 从「开场白」到「落地前下单」整条话术链路：
 *   A 模块链路结构（首=opening 末=closing 顺序固定、模块非空）
 *   B 开场问候语义（各位旅客/旅客朋友们/大家好）
 *   C 收尾下单语义（落地前下单/下单/带走）
 *   D 全文违禁词清零
 *   E 品牌名不重复（name 与 brand 片段重叠扫描）
 *   F 句级重复（同一脚本内重复句子）
 *   G 每款产品都进了「开场清单」（非极短时）
 * 运行：node _verify_full_script.js [seed] [--dump]
 */
'use strict';
const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync('beauty.html', 'utf8');
const results = [];
function check(name, cond, extra) { results.push({ name, pass: !!cond, extra: extra || '' }); }

function parseArray(src, re) { const m = src.match(re); if (!m) throw new Error('数组提取失败: ' + re); return eval('([' + m[1] + '])'); }
function extractBalanced(src, openIdx) {
  const pairs = { '{': '}', '[': ']', '(': ')' };
  const close = pairs[src[openIdx]]; let depth = 0, i = openIdx, inStr = null, esc = false;
  for (; i < src.length; i++) { const ch = src[i]; if (inStr) { if (esc) esc = false; else if (ch === '\\') esc = true; else if (ch === inStr) inStr = null; continue; } if (ch === '"' || ch === "'" || ch === '`') { inStr = ch; continue; } if (ch === src[openIdx]) depth++; else if (ch === close) { depth--; if (depth === 0) return src.slice(openIdx, i + 1); } }
  throw new Error('括号未配平 @' + openIdx);
}
const products = parseArray(html, /const products = \[([\s\S]*?)\n        \];/);
const fullName = (p) => { const b = String((p && p.brand) || '').trim(); const n = String((p && p.name) || '').trim(); if (!n) return b || '机上好物'; if (!b || b === '机上好物') return n; if (n.toLowerCase().indexOf(b.toLowerCase()) === 0) return n; return b + n; };
const vocabStart = html.indexOf('const vocab = {');
const vocab = eval('(' + extractBalanced(html, html.indexOf('{', vocabStart)) + ')');
const engineStart = html.indexOf('// ========== 话术生成引擎 ==========');
const fsDef = html.indexOf('window.generateScript = function', engineStart);
const fnOpen = html.indexOf('{', html.indexOf('(', fsDef));
const fnBody = extractBalanced(html, fnOpen);
const lineStart = html.lastIndexOf('\n', engineStart) + 1;
const engineCode = html.slice(lineStart, fnOpen + fnBody.length + 1);
const sandbox = { console, Math, Date, JSON, Set, Map, Array, Object, String, Number, RegExp, products, vocab,
  state: { selectedProductIds: [], duration: 8, showCustomerProfile: false, customerProfile: {}, scriptConfig: { categories: [], effects: [], brand: 'all', count: 3 }, generatedScript: null },
  showAlert: () => {}, render: () => {}, getProductById: (id) => products.find(p => p.id === id), getTemplateForProduct: () => null, fillTemplate: () => null };
sandbox.window = sandbox;
vm.createContext(sandbox);
try { vm.runInContext(engineCode, sandbox, { filename: 'beauty_full_engine.js' }); }
catch (e) { console.error('引擎注入失败:', e.message); process.exit(1); }
const generateScript = sandbox.window.generateScript;

const BIG = { souvenir: ['纪念品'], alcohol: ['清酒', '红酒', '梅子酒', '烧酒', '酒'], makeup: ['粉底液', '口红', '隔离', '彩妆'], fragrance: ['香水'], health: ['保健品'] };
const typeOf = (p) => { if (BIG.alcohol.includes(p.category)) return 'alcohol'; if (BIG.makeup.includes(p.category)) return 'makeup'; if (p.category === '香水') return 'fragrance'; if (p.category === '保健品') return 'health'; if (BIG.souvenir.includes(p.category) || p.brand === '春秋航空') return 'souvenir'; return 'skincare'; };
const BANNED = ['比专柜', '比代购', '比免税店', '全网最低', '最低价', '最便宜', '手慢无', '爆款', '明星产品', '错过就没有', '仅此一次', '限量', '抢完', '卖完', '不等人', '机会难得', '全网唯一', '行业第一', '绝无仅有'];

function seededRand(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
function pick(arr, rnd) { return arr[Math.floor(rnd() * arr.length)]; }
function shuffle(arr, rnd) { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }

function buildCombos(rnd, n) {
  const byType = {}; products.forEach(p => { const t = typeOf(p); (byType[t] = byType[t] || []).push(p); });
  const types = Object.keys(byType);
  const combos = [];
  let guard = 0;
  while (combos.length < n && guard++ < n * 80) {
    const count = 1 + Math.floor(rnd() * 8); // 1~8 款随机
    const used = new Set(); const chosen = [];
    const tOrder = shuffle(types, rnd);
    for (let i = 0; i < count && chosen.length < count; i++) {
      const t = tOrder[i % tOrder.length];
      const pool = byType[t] || [];
      const cands = shuffle(pool, rnd).filter(p => !used.has(p.id));
      if (cands.length) { const c = cands[0]; chosen.push(c); used.add(c.id); }
    }
    if (chosen.length >= 1) combos.push(chosen);
  }
  return combos;
}
/* 句级切分（按标点）并归一化，统计重复 */
function dupSentences(text) {
  const parts = text.split(/[。！？\n]/).map(s => s.replace(/\s+/g, '').replace(/[－—-]/g, '')).filter(s => s.length >= 8 && !/：$/.test(s));
  const seen = {}; const dups = [];
  parts.forEach(s => { if (seen[s]) { if (seen[s] === 1) dups.push(s); seen[s]++; } else seen[s] = 1; });
  return dups;
}

const SEED = parseInt(process.argv[2] || '20260829', 10);
const DUMP = process.argv.includes('--dump');
const rnd = seededRand(SEED);
const combos = buildCombos(rnd, 24);
const durations = [2, 3, 4, 5, 6, 8, 10, 12];
const failDetails = [];
let ok = 0;

combos.forEach((combo, ci) => {
  const dur = pick(durations, rnd);
  const label = `组合${ci + 1}(${dur}分钟)[${combo.map(p => fullName(p)).join('+')}]`;
  let sc = null;
  /* 句级重复/品牌重复 是概率性毛病：同组合跑 3 次，任一次命中即记失败 */
  let dupErr = null; let brandErr = null;
  for (let run = 0; run < 3; run++) {
    sandbox.state.selectedProductIds = combo.map(p => p.id);
    sandbox.state.duration = dur;
    sandbox.state.showCustomerProfile = rnd() < 0.3;
    try { generateScript(true); } catch (e) { check(label + ' 生成无异常', false, e.message); return; }
    sc = sandbox.state.generatedScript;
    if (!sc) { check(label + ' 生成了脚本', false); return; }
    const fullRun = sc.fullText;
    combo.forEach(p => {
      const b = String(p.brand || '').trim();
      if (b && b !== '机上好物' && !brandErr) {
        if (fullRun.indexOf(b + b) >= 0) brandErr = b + b;
        else if (fullRun.indexOf(b + ' ' + b) >= 0) brandErr = b + ' ' + b;
      }
    });
    const dups = dupSentences(fullRun);
    if (dups.length && !dupErr) dupErr = dups.slice(0, 5).join(' | ');
  }
  const failDetect = (l, name, extra) => { check(name, false, extra); failDetails.push(`${l} ${name} <${extra || ''}>`); };
  if (brandErr) failDetect(label, '品牌重复', brandErr);
  if (dupErr) failDetect(label, '句级重复', dupErr);
  const mods = sc.modules;
  const full = sc.fullText;
  let comboOk = true;
  const fail = (name, extra) => { comboOk = false; check(name, false, extra); failDetails.push(`${label} ${name} <${extra || ''}>`); };

  /* A 模块链路结构 */
  const ids = mods.map(m => m.id);
  if (mods[0].id !== 'opening') fail('首模块应为opening', String(ids[0]));
  if (mods[mods.length - 1].id !== 'closing') fail('末模块应为closing', String(ids[mods.length - 1]));
  mods.forEach((m, mi) => { if (!String(m.content || '').trim()) fail(`模块${m.id}内容为空`, `mi=${mi}`); });

  /* B 开场问候语义 */
  const opening = mods[0].content;
  if (!/各位旅客|旅客朋友们|旅客朋友|大家好|乘坐春秋航空|您的|欢迎/.test(opening)) fail('开场缺问候语', opening.slice(0, 30));

  /* C 收尾下单语义 */
  const closing = mods[mods.length - 1].content;
  if (!/下单|购买|带走|捡漏|落地前|送到家|送到家|配送到家/.test(closing)) fail('收尾缺下单引导', closing.slice(0, 30));

  /* D 违禁词 */
  const hits = BANNED.filter(w => full.includes(w));
  if (hits.length) fail('全文违禁词', hits.join(','));

  /* E 品牌不重复（同一脚本内 brand+brand / brand 空格 brand） */
  combo.forEach(p => {
    const b = String(p.brand || '').trim();
    if (!b || b === '机上好物') return;
    if (full.indexOf(b + b) >= 0) fail(`品牌重复:${b}`, b + b);
    if (full.indexOf(b + ' ' + b) >= 0) fail(`品牌重复(空格):${b}`, b + ' ' + b);
  });

  /* F 句级重复 */
  const dups = dupSentences(full);
  if (dups.length) fail('句级重复', dups.slice(0, 5).join(' | '));

  /* G 每款产品进开场清单（非极短时才有清单） */
  if (dur > 3 && combo.length > 1) {
    combo.forEach(p => { if (!opening.includes(p.name)) fail(`产品未进开场清单:${p.name}`, ''); });
  }

  if (comboOk && !dupErr && !brandErr) ok++;
});

/* ---------- 汇总 ---------- */
const passed = results.filter(r => r.pass).length;
const failed = results.filter(r => !r.pass);
console.log(`\n═══ 全话术链路回归（seed=${SEED}，组合=${combos.length}）═══`);
console.log(`组合级通过 ${ok}/${combos.length}`);
console.log(`检查项通过 ${passed} / 失败 ${failed.length}`);
if (failed.length) { console.log('\n--- 失败明细 ---'); failed.forEach(f => console.log('[FAIL] ' + f.name + (f.extra ? '  <' + f.extra + '>' : ''))); }
console.log('\n--- 硬伤明细 ---');
if (failDetails.length) failDetails.slice(0, 80).forEach(d => console.log('• ' + d));
else console.log('（无）');
process.exit(failed.length ? 1 : 0);