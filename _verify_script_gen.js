/* 客舱小助手 · 话术生成引擎回归测试（Node）
 * 从 beauty.html 抽取真实 products / vocab / 生成引擎，批量随机组合生成话术，
 * 审计：①产品与文案是否匹配（香水/酒/纪念品段落不得串入护肤话术）
 *      ②上下文承接（产品间过渡、模块过渡）
 * 运行：node _verify_script_gen.js [seed] [--dump]
 */
'use strict';
const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync('beauty.html', 'utf8');
const results = [];
function check(name, cond, extra) { results.push({ name, pass: !!cond, extra: extra || '' }); }

/* ---------- 1. 提取 products（沿用现有脚本的 parseArray 模式） ---------- */
function parseArray(src, re) {
  const m = src.match(re);
  if (!m) throw new Error('数组提取失败: ' + re);
  return eval('([' + m[1] + '])'); // eslint-disable-line no-eval
}
const products = parseArray(html, /const products = \[([\s\S]*?)\n        \];/);

/* 商品显示名（与 beauty.html 引擎 fullName 同逻辑）：name 已含品牌 → 直接用，否则拼品牌 */
const fullName = (p) => {
  const b = String((p && p.brand) || '').trim();
  const n = String((p && p.name) || '').trim();
  if (!n) return b || '机上好物';
  if (!b || b === '机上好物') return n;
  if (n.toLowerCase().indexOf(b.toLowerCase()) === 0) return n;
  return b + n;
};

/* ---------- 2. 提取 vocab（引号感知括号配平） ---------- */
function extractBalanced(src, openIdx) {
  const pairs = { '{': '}', '[': ']', '(': ')' };
  const close = pairs[src[openIdx]];
  let depth = 0, i = openIdx, inStr = null, esc = false;
  for (; i < src.length; i++) {
    const ch = src[i];
    if (inStr) {
      if (esc) esc = false;
      else if (ch === '\\') esc = true;
      else if (ch === inStr) inStr = null;
      continue;
    }
    if (ch === '"' || ch === "'" || ch === '`') { inStr = ch; continue; }
    if (ch === src[openIdx]) depth++;
    else if (ch === close) { depth--; if (depth === 0) return src.slice(openIdx, i + 1); }
  }
  throw new Error('括号未配平 @' + openIdx);
}
const vocabStart = html.indexOf('const vocab = {');
if (vocabStart < 0) throw new Error('vocab 未找到');
const vocab = eval('(' + extractBalanced(html, html.indexOf('{', vocabStart)) + ')');

/* ---------- 3. 提取生成引擎（话术生成引擎 注释行 → generateScript 收尾） ---------- */
const engineStart = html.indexOf('// ========== 话术生成引擎 ==========');
if (engineStart < 0) throw new Error('引擎起始标记未找到');
const fsDef = html.indexOf('window.generateScript = function', engineStart);
if (fsDef < 0) throw new Error('generateScript 未找到');
/* generateScript 函数体配平（从 function( 的 { 开始） */
const fnOpen = html.indexOf('{', html.indexOf('(', fsDef));
const fnBody = extractBalanced(html, fnOpen);
/* 引擎块 = 引擎起始行首 → generateScript 函数体结束（含收尾 ;） */
const lineStart = html.lastIndexOf('\n', engineStart) + 1;
const lineEnd = fnOpen + fnBody.length; // fnBody 不含 function(...) 头，需从 fnOpen 起算到 body 配平结束
const engineCode = html.slice(lineStart, lineEnd + 1);

const sandbox = {
  console, Math, Date, JSON, Set, Map, Array, Object, String, Number, RegExp,
  products,
  vocab,
  state: {
    selectedProductIds: [],
    duration: 8,
    showCustomerProfile: false,
    customerProfile: {},
    scriptConfig: { categories: [], effects: [], brand: 'all', count: 3 },
    generatedScript: null
  },
  showAlert: () => {},
  render: () => {},
  getProductById: (id) => products.find(p => p.id === id),
  getTemplateForProduct: () => null,
  fillTemplate: () => null
};
sandbox.window = sandbox;
vm.createContext(sandbox);
try {
  vm.runInContext(engineCode, sandbox, { filename: 'beauty_engine.js' });
} catch (e) {
  console.error('引擎注入失败:', e.message);
  process.exit(1);
}
const generateScript = sandbox.window.generateScript;
if (typeof generateScript !== 'function') throw new Error('generateScript 未挂载');

/* ---------- 4. 类型与词表 ---------- */
const BIG = {
  souvenir: ['纪念品'],
  alcohol: ['清酒', '红酒', '梅子酒', '烧酒', '酒'],
  makeup: ['粉底液', '口红', '隔离', '彩妆'],
  fragrance: ['香水'],
  health: ['保健品']
};
const bigTypeOf = (p) => {
  if (BIG.alcohol.includes(p.category)) return 'alcohol';
  if (BIG.makeup.includes(p.category)) return 'makeup';
  if (p.category === '香水') return 'fragrance';
  if (p.category === '保健品') return 'health';
  if (BIG.souvenir.includes(p.category) || p.brand === '春秋航空') return 'souvenir';
  return 'skincare';
};
/* 护肤强词：出现在非护肤类产品专属段落 → 判定"货不对板" */
const SKINCARE_WORDS = ['皮肤', '肌肤', '洁面', '补水', '保湿', '渗透', '面部', '面膜', '护肤品', '精华液', '肤质', '痘痘', '毛孔', '胶原', '紧绷', '水乳', '养肤'];
const CONCRETE_WORDS = ['渗透肌肤', '皮肤在变好', '护肤这件事', '带一款靠谱的护肤品', '水乳霜', '洁面后', '每日涂抹', '涂在脸上', '一瓶搞定'];
/* 香调度专用词（香水专属段落应出现） */
const FRAGRANCE_WORDS = ['喷', '香调', '留香', '香气', '味道', '气味'];

function seededRand(seed) {
  let s = seed >>> 0;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}
function pick(arr, rnd) { return arr[Math.floor(rnd() * arr.length)]; }
function shuffle(arr, rnd) { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }

/* 生成一套组合：先按 6 类各至少覆盖一次，再随机补到 3~5 款 */
function buildCombos(rnd, n) {
  const byType = {};
  products.forEach(p => { const t = bigTypeOf(p); (byType[t] = byType[t] || []).push(p); });
  const combos = [];
  const typeCycle = ['skincare', 'makeup', 'fragrance', 'health', 'alcohol', 'souvenir'];
  let round = 0;
  while (combos.length < n) {
    const wantTypes = []; // 每轮从 6 类里抽一个起始类
    const startType = typeCycle[round % 6];
    round++;
    wantTypes.push(startType);
    const extraTypes = shuffle(typeCycle, rnd).filter(t => t !== startType).slice(0, 2 + Math.floor(rnd() * 2));
    wantTypes.push(...extraTypes.slice(0, 3));
    const chosen = [];
    const usedId = new Set();
    for (const t of wantTypes) {
      const pool = byType[t] || [];
      if (!pool.length) continue;
      const cnt = 1 + Math.floor(rnd() * 2);
      const picks = shuffle(pool, rnd).filter(p => !usedId.has(p.id)).slice(0, cnt);
      picks.forEach(p => { chosen.push(p); usedId.add(p.id); });
    }
    if (chosen.length < 1) continue;
    combos.push(chosen);
  }
  return combos;
}

/* ---------- 5. 审计 ---------- */
const SEED = parseInt(process.argv[2] || '20260829', 10);
const DUMP = process.argv.includes('--dump');
const rnd = seededRand(SEED);
const combos = buildCombos(rnd, 12);
const durations = [2, 3, 5, 8, 10, 12];
const failDetails = [];
let dumpLines = [];

function sliceByProduct(fullText, productsList) {
  /* 按 **品牌 名称** 切分 benefitsText 段落（productsList 必须是生成引擎重排后的顺序） */
  const blocks = [];
  const marks = productsList.map(p => '**' + fullName(p) + '**');
  let rest = fullText;
  for (let i = 0; i < marks.length; i++) {
    const mIdx = rest.indexOf(marks[i]);
    if (mIdx < 0) continue;
    const start = mIdx + marks[i].length;
    const end = i + 1 < marks.length ? rest.indexOf(marks[i + 1]) : rest.length;
    if (end < 0) continue;
    const blkText = rest.slice(start, end);
    blocks.push({ name: productsList[i].name, type: bigTypeOf(productsList[i]), cats: [productsList[i].category], text: blkText });
    rest = rest.slice(start, end);
  }
  return blocks;
}
/* 剔除"同品类组合"块（它属于组合推荐段落，不属于单个产品块） */
function sanitizeBlock(t) { return t.split('同属「')[0]; }

combos.forEach((combo, ci) => {
  const dur = pick(durations, rnd);
  sandbox.state.selectedProductIds = combo.map(p => p.id);
  sandbox.state.duration = dur;
  sandbox.state.showCustomerProfile = rnd() < 0.3;
  sandbox.state.customerProfile = {};
  try {
    generateScript(true);
  } catch (e) {
    check(`组合${ci + 1} 生成无异常`, false, e.message);
    return;
  }
  const sc = sandbox.state.generatedScript;
  if (!sc) { check(`组合${ci + 1} 生成了脚本`, false); return; }
  const full = sc.fullText;
  const types = [...new Set(combo.map(p => bigTypeOf(p)))];
  const comboLabel = combo.map(p => fullName(p)).join(' + ') + ` [${dur}分钟]`;
  dumpLines.push(`\n==== 组合${ci + 1}（${dur}分钟）：${comboLabel} ====\n` + full + '\n');

  /* 审计1：产品剁关怀词匹配（benefitsText 即 coreBenefits 模块，按重排后顺序切片） */
  const coreModule = sc.modules.find(m => m.id === 'coreBenefits');
  const coreText = coreModule ? coreModule.content : '';
  const orderedSel = sc.selectedProducts;
  const blocks = sliceByProduct(coreText, orderedSel);
  const banned = SKINCARE_WORDS.concat(CONCRETE_WORDS);
  blocks.forEach(b => {
    const blk = sanitizeBlock(b.text);
    if (b.type === 'fragrance' || b.type === 'alcohol') {
      const hits = banned.filter(w => blk.includes(w));
      if (hits.length) {
        const detail = `产品「${b.name}」（${b.type}）段落出现护肤词：${hits.join(',')} → ${blk.replace(/\s+/g, ' ').slice(0, 90)}`;
        failDetails.push(`组合${ci + 1} ${detail}`);
        check(`组合${ci + 1} ${b.name}文案匹配`, false, detail);
      }
    }
    if (b.type === 'souvenir') {
      const hits = banned.filter(w => blk.includes(w));
      if (hits.length) {
        const detail = `纪念品「${b.name}」段落出现护肤词：${hits.join(',')}`;
        failDetails.push(`组合${ci + 1} ${detail}`);
        check(`组合${ci + 1} ${b.name}文案匹配`, false, detail);
      }
    }
  });

  /* 审计2：香水专属段落应有香调度词（其描述类文案） */
  blocks.forEach(b => {
    const blk = sanitizeBlock(b.text);
    if (b.type === 'fragrance' && dur >= 8) {
      const hasAny = FRAGRANCE_WORDS.some(w => blk.includes(w));
      if (!hasAny) {
        const detail = `香水「${b.name}」长时段落无香调度词`;
        failDetails.push(`组合${ci + 1} ${detail}`);
        check(`组合${ci + 1} ${b.name}香调度词`, false, detail);
      }
    }
  });

  /* 审计3：使用建议板块标题不得硬套「旅途护肤」 */
  const usage = sc.modules.find(m => m.id === 'usage');
  if (usage) {
    const noSkincareTypes = combo.every(p => ['fragrance', 'alcohol', 'souvenir', 'health'].includes(bigTypeOf(p)));
    const allAlcohol = combo.every(p => bigTypeOf(p) === 'alcohol');
    const allFragrance = combo.every(p => bigTypeOf(p) === 'fragrance');
    if (noSkincareTypes && /旅途护肤|护肤/.test(usage.title)) {
      failDetails.push(`组合${ci + 1} 无护肤产品却用护肤标题「${usage.title}」`);
      check(`组合${ci + 1} 使用建议标题匹配`, false, usage.title);
    }
    if (allAlcohol && !/饮用/.test(usage.title)) {
      failDetails.push(`组合${ci + 1} 全酒类组合标题应为饮用建议：「${usage.title}」`);
      check(`组合${ci + 1} 酒类标题`, false, usage.title);
    }
    if (allFragrance && !/香氛|香水/.test(usage.title)) {
      failDetails.push(`组合${ci + 1} 全香水组合标题应含香氛：「${usage.title}」`);
      check(`组合${ci + 1} 香水标题`, false, usage.title);
    }
  }

  /* 审计3.5：品牌名不得重复（name 已含品牌，拼接 brand 会产出「品牌 品牌+名称」） */
  combo.forEach(p => {
    const b = String((p && p.brand) || '').trim();
    if (!b) return;
    const dupNoSpace = b + b;
    const dupWithSpace = b + ' ' + b;
    const hits = [];
    if (full.indexOf(dupNoSpace) >= 0) hits.push(dupNoSpace);
    if (full.indexOf(dupWithSpace) >= 0) hits.push(dupWithSpace);
    if (hits.length) {
      failDetails.push(`组合${ci + 1} 产品「${fullName(p)}」出现品牌重复：${hits.join(',')}`);
      check(`组合${ci + 1} ${fullName(p)} 品牌不重复`, false, hits.join(','));
    }
  });

  /* 审计4：上下文承接 —— 相邻产品段之间应有过渡（非极短时） */
  if (dur > 3 && blocks.length > 1) {
    for (let i = 0; i < blocks.length - 1; i++) {
      const markA = '**' + fullName(orderedSel[i]) + '**';
      const markB = '**' + fullName(orderedSel[i + 1]) + '**';
      const iA = coreText.indexOf(markA);
      const iB = coreText.indexOf(markB, iA + markA.length);
      if (iA < 0 || iB < 0) continue;
      const between = coreText.slice(iA + markA.length, iB).trim();
      if (!between) {
        failDetails.push(`组合${ci + 1} 产品【${orderedSel[i].name}】→【${orderedSel[i + 1].name}】无过渡衔接`);
        check(`组合${ci + 1} 产品间过渡`, false, `${orderedSel[i].name}→${orderedSel[i + 1].name}`);
      }
    }
  }

  /* 审计5：模块间过渡承接 —— 非首个模块开头存在引导语 */
  const noLead = [];
  sc.modules.forEach((m, mi) => {
    if (mi === 0) return;
    const head = (m.content || '').trim();
    if (!head.length) noLead.push(m.id);
  });
  if (noLead.length) {
    failDetails.push(`组合${ci + 1} 空模块：${noLead.join(',')}`);
    check(`组合${ci + 1} 模块非空`, false, noLead.join(','));
  }
});

/* ---------- 汇总 ---------- */
const passed = results.filter(r => r.pass).length;
const failed = results.filter(r => !r.pass);
console.log(`\n═══ 话术生成引擎回归（seed=${SEED}，组合=${combos.length}）═══`);
console.log(`通过 ${passed} 项 / 失败 ${failed.length} 项`);
combos.forEach((c, i) => {
  console.log(`组合${i + 1}: ${c.map(p => fullName(p)).join(' + ')}`);
});
if (failed.length) {
  console.log('\n--- 失败明细 ---');
  failed.forEach(f => console.log('[FAIL] ' + f.name + (f.extra ? '  <' + f.extra + '>' : '')));
}
console.log('\n--- 硬伤明细 ---');
if (failDetails.length) failDetails.slice(0, 60).forEach(d => console.log('• ' + d));
else console.log('（无）');
if (DUMP) fs.writeFileSync('_script_gen_report.txt', dumpLines.join('\n'), 'utf8');

/* ---------- 单点模式：--solo <productId> [duration] 打印完整话术，便于人工审查 ---------- */
if (process.argv.includes('--solo')) {
  const si = process.argv.indexOf('--solo');
  const sid = process.argv[si + 1];
  const sdur = parseInt(process.argv[si + 2] || '12', 10);
  let p = products.find(x => x.id === sid);
  if (!p) p = products.find(x => x.name && (x.name.indexOf(sid) >= 0 || x.id.indexOf(sid) >= 0));
  if (!p) { console.error('未找到产品 ' + sid); process.exit(1); }
  sandbox.state.selectedProductIds = [p.id];
  sandbox.state.duration = sdur;
  generateScript(true);
  const scOut = sandbox.state.generatedScript;
  console.log('\n\n★★★★ 单点复核：' + p.brand + p.name + ' [' + sdur + '分钟] ★★★★');
  console.log(scOut.fullText);
}
process.exit(failed.length ? 1 : 0);