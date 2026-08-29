/* 客舱小助手 · 过渡话术套装测试（Node）
 * 一、静态词库审计：扩充后的过渡句池（SKIN_SUB_TRANSITIONS / TYPE_TRANSITIONS /
 *      模块间 transitions / GENERIC 兜底）校验：
 *      01 词条非空且以中文标点收尾；02 合规（比价/绝对化/饥饿营销违禁词清零）；
 *      03 科学性（"吸收通道/打通/趁热打铁"类表述只允许出现在 水类(化妆水/精华水)→精华，
 *          洁面/面霜/眼霜等不得做"打通吸收通道"表述）；04 全库去重；05 六类两两组合覆盖闭环。
 * 二、套装测试（设计组合 ≥10 套，覆盖 ≥6 种类型组合模式）：8/10/12 分钟档为主
 *      A1 生成无异常、模块齐全、无空模块；A2 品类出场顺序（护肤→彩妆→香氛→保健→酒→纪念品）
 *         及护肤内部顺序（卸妆→洁面→水→精华→眼霜→面霜→防晒）；
 *      A3 产品段落文案匹配（香水/酒/纪念品不得串护肤词）；
 *      A4 产品间过渡句合法性（必须来自该品类对合法池）+ 科学性（吸收通道表述的前序品类必须为水类）；
 *      A5 使用建议标题品类匹配；A6 不适合人群提示存在；
 *      A7 生成全文违禁词清零；
 * 三、仓库试运行：--repo N 从仓库随机生成 N 套（数量 2~8、类型随机）执行相同审计。
 * 用法:
 *   node _verify_suite_test.js                 # 套件测试（14 套设计组合）
 *   node _verify_suite_test.js --repo 50       # 仓库试运行 50 套
 *   node _verify_suite_test.js --dump          # 连同完整话术落盘 _suite_report.txt
 *   node _verify_suite_test.js --solo <id> [dur]  # 单点打印完整话术（人工审查用）
 */
'use strict';
const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync('beauty.html', 'utf8');
const results = [];
function check(name, cond, extra) { results.push({ name, pass: !!cond, extra: extra || '' }); }

/* ---------- 1. 提取 products（沿用 _verify_script_gen.js 的 parseArray 模式） ---------- */
function parseArray(src, re) {
  const m = src.match(re);
  if (!m) throw new Error('数组提取失败: ' + re);
  return eval('([' + m[1] + '])'); // eslint-disable-line no-eval
}
const products = parseArray(html, /const products = \[([\s\S]*?)\n        \];/);

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
const fnOpen = html.indexOf('{', html.indexOf('(', fsDef));
const fnBody = extractBalanced(html, fnOpen);
const lineStart = html.lastIndexOf('\n', engineStart) + 1;
const lineEnd = fnOpen + fnBody.length + 1;
const engineCode = html.slice(lineStart, lineEnd);

/* ---------- 3.5 提取模块内 transitions 词库（generateScript 内部常量，从源码解析） ---------- */
const tStart = html.indexOf('const transitions = {', engineStart);
if (tStart < 0) throw new Error('模块 transitions 未找到');
const moduleTransitions = eval('(' + extractBalanced(html, html.indexOf('{', tStart)) + ')');

/* ---------- 测试用合成纪念品（仓库正档无纪念品类，补齐六类覆盖测试） ---------- */
const SYNTHETIC = [
  { id: 'test-sou-01', name: '春秋航空定制飞机模型', brand: '春秋航空', category: '纪念品', volume: '1:200', origin: '春秋航空', stock: 'in_stock',
    description: '以春秋航空机身涂装为原型的合金飞机模型，精铸工艺复刻机身线条，含展示底座，适合桌面摆放或收藏留念。',
    coreBenefits: ['机身涂装复刻', '合金精铸', '含展示底座', '收藏纪念'], targetSkinTypes: ['航空爱好者', '收藏纪念需求'],
    keyIngredients: [{ commonName: '锌合金机身', mechanism: '精铸工艺，还原机身原型线条' }, { commonName: '树脂底座', mechanism: '平稳摆放，便于展示' }],
    unsuitable: [], tags: ['纪念品', '春秋航空', '飞机模型'], reviewCount: 1234 },
  { id: 'test-sou-02', name: '春秋航空Q版钥匙扣', brand: '春秋航空', category: '纪念品', volume: '单只', origin: '春秋航空', stock: 'in_stock',
    description: 'Q版飞机造型钥匙扣，合金材质轻巧便携，春秋标志清晰，适合自用或随手送人。',
    coreBenefits: ['Q版造型', '合金材质', '轻巧便携', '送礼贴心'], targetSkinTypes: ['航空爱好者', '伴手礼需求'],
    keyIngredients: [{ commonName: '锌合金', mechanism: '耐磨损，光泽度高' }], unsuitable: [], tags: ['纪念品', '春秋航空', '钥匙扣'], reviewCount: 876 },
  { id: 'test-sou-03', name: '春秋航空刺绣丝巾', brand: '春秋航空', category: '纪念品', volume: '90×90cm', origin: '春秋航空', stock: 'in_stock',
    description: '真丝材质丝巾，春秋航空标志刺绣工艺，手工包边，配色经典，适合出行搭配或作为伴手礼。',
    coreBenefits: ['真丝材质', '品牌刺绣', '手工包边', '送人体面'], targetSkinTypes: ['商务出行者', '伴手礼需求'],
    keyIngredients: [{ commonName: '桑蚕丝', mechanism: '柔软亲肤，光泽细腻' }, { commonName: '品牌刺绣', mechanism: '精致工艺，辨识度高' }],
    unsuitable: [], tags: ['纪念品', '春秋航空', '丝巾'], reviewCount: 1502 }
];
products.push(...SYNTHETIC);

/* 商品显示名（与 beauty.html 引擎 fullName 同逻辑）：name 已含品牌 → 直接用，否则拼品牌 */
const fullName = (p) => {
  const b = String((p && p.brand) || '').trim();
  const n = String((p && p.name) || '').trim();
  if (!n) return b || '机上好物';
  if (!b || b === '机上好物') return n;
  if (n.toLowerCase().indexOf(b.toLowerCase()) === 0) return n;
  return b + n;
};

const sandbox = {
  console, Math, Date, JSON, Set, Map, Array, Object, String, Number, RegExp,
  products,
  vocab,
  state: {
    selectedProductIds: [], duration: 8, showCustomerProfile: false, customerProfile: {},
    scriptConfig: { categories: [], effects: [], brand: 'all', count: 3 }, generatedScript: null
  },
  showAlert: () => {}, render: () => {},
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

/* ---------- 4. 词池 & 类型工具 ---------- */
const SUB = vm.runInContext('SKIN_SUB_TRANSITIONS', sandbox);
const SUBFALL = vm.runInContext('SKIN_SUB_FALLBACK', sandbox);
const TT = vm.runInContext('TYPE_TRANSITIONS', sandbox);
const GEN = vm.runInContext('GENERIC_TRANSITIONS', sandbox);

const CAT_TYPE = {
  skincare: ['洁面', '化妆水', '精华水', '精华', '眼霜', '眼膜', '面霜', '乳液', '防晒', '面膜', '卸妆', '护手霜', '身体护理', '唇部护理'],
  makeup: ['粉底液', '口红', '隔离', '彩妆'],
  fragrance: ['香水'],
  health: ['保健品'],
  alcohol: ['清酒', '红酒', '梅子酒', '烧酒', '酒']
};
const typeOf = (p) => {
  if (!p) return 'other';
  for (const [t, cats] of Object.entries(CAT_TYPE)) if (cats.includes(p.category)) return t;
  if (p.category === '纪念品' || p.brand === '春秋航空') return 'souvenir';
  return 'skincare';
};
const SKIN_ORDER = { '卸妆': 0, '洁面': 1, '面膜': 2, '化妆水': 3, '精华水': 3, '精华': 4, '眼霜': 5, '眼膜': 6, '乳液': 7, '面霜': 8, '防晒': 9, '精油': 10, '身体护理': 11, '唇部护理': 12, '护手霜': 13 };
const TYPE_ORDER = { skincare: 0, makeup: 1, fragrance: 2, health: 3, alcohol: 4, souvenir: 5, other: 6 };
const sortForStory = (arr) => [...arr].sort((a, b) => {
  const ta = TYPE_ORDER[typeOf(a)], tb = TYPE_ORDER[typeOf(b)];
  if (ta !== tb) return ta - tb;
  if (ta === 0) return (SKIN_ORDER[a.category] || 4) - (SKIN_ORDER[b.category] || 4);
  return 0;
});

/* ---------- 5. 静态词库审计 ---------- */
const BANNED = ['比专柜', '比代购', '比免税店', '全网最低', '最低价', '最便宜', '手慢无', '爆款', '明星产品', '错过就没有', '仅此一次', '限量', '抢完', '卖完', '不等人', '机会难得', '全网唯一', '行业第一', '绝无仅有'];
const ABSORB_WORDS = ['吸收通道', '打开通道', '打通', '趁热打铁'];
const ENDCHARS = ['。', '！', '？', '…', '～'];

function auditStaticPool() {
  const seen = new Set();
  const labeled = [];
  const collect = (label, arr) => arr.forEach((s, i) => labeled.push({ label: label + '[' + i + ']', s }));
  Object.entries(SUB).forEach(([k, arr]) => collect('SUB:' + k, arr));
  collect('SUBFALL', SUBFALL);
  Object.entries(TT).forEach(([k, arr]) => collect('TT:' + k, arr));
  collect('GEN', GEN);
  Object.entries(moduleTransitions).forEach(([k, arr]) => collect('MOD:' + k, arr));

  /* 01 词条非空且以中文标点收尾 */
  labeled.forEach(e => {
    check('词条 ' + e.label + ' 非空且标点收尾', typeof e.s === 'string' && e.s.trim().length > 0 && ENDCHARS.some(c => e.s.trim().endsWith(c)), e.s.trim().slice(0, 40));
  });
  /* 02 合规 */
  labeled.forEach(e => {
    const hits = BANNED.filter(w => e.s.includes(w));
    check('词条 ' + e.label + ' 合规', hits.length === 0, e.s.trim().slice(0, 40) + ' → 命中:' + hits.join(','));
  });
  /* 03 科学性：吸收通道类只出现在 水类→* 的子品类池 */
  labeled.forEach(e => {
    const hasAbsorb = ABSORB_WORDS.some(w => e.s.includes(w));
    if (!hasAbsorb) return;
    const key = e.label.split(':')[1] || '';       // 形如 化妆水|精华[3]
    const prevCat = (key.split('|')[0] || '').split('[')[0];
    const inWaterSub = e.label.indexOf('SUB:') === 0 && ['化妆水', '精华水'].includes(prevCat);
    check('科学 ' + e.label + ' 吸收通道限定水类', inWaterSub, e.s.trim().slice(0, 40));
  });
  /* 04 全库去重 */
  labeled.forEach(e => {
    const s = e.s.trim();
    check('去重 ' + e.label, !seen.has(s), '与已存在词条重复: ' + s.slice(0, 30));
    seen.add(s);
  });
  /* 05 六类组合覆盖闭环（两两无向对 + 自身对 至少一个方向存在） */
  const types = ['skincare', 'makeup', 'fragrance', 'health', 'alcohol', 'souvenir'];
  let miss = [];
  for (let i = 0; i < types.length; i++) {
    for (let j = i; j < types.length; j++) {
      const a = types[i], b = types[j];
      if (TT[a + '|' + b] || TT[b + '|' + a]) continue;
      miss.push(a + '↔' + b);
    }
  }
  check('词库六类两两衔接覆盖', miss.length === 0, miss.join(','));
  /* 06 每组词条数量下限（避免单调） */
  Object.entries(TT).forEach(([k, arr]) => { if (k !== 'skincare|skincare') check('TT:' + k + ' ≥2条', arr.length >= 2, String(arr.length)); });
  check('TT:skincare|skincare ≥3条', TT['skincare|skincare'].length >= 3, String(TT['skincare|skincare'].length));
  Object.entries(moduleTransitions).forEach(([k, arr]) => { check('MOD:' + k + ' ≥6条', arr.length >= 6, String(arr.length)); });
}

/* ---------- 6. 动态审计工具 ---------- */
const legalPoolFor = (prevP, nextP) => {
  const pt = typeOf(prevP), nt = typeOf(nextP);
  if (pt === 'skincare' && nt === 'skincare') {
    const c1 = prevP.category, c2 = nextP.category;
    const arr = [];
    if (SUB[c1 + '|' + c2]) arr.push(...SUB[c1 + '|' + c2]);
    if (SUB[c2 + '|' + c1]) arr.push(...SUB[c2 + '|' + c1]);
    arr.push(...TT['skincare|skincare'], ...SUBFALL);
    return arr;
  }
  const arr = [];
  if (TT[pt + '|' + nt]) arr.push(...TT[pt + '|' + nt]);
  if (TT[nt + '|' + pt]) arr.push(...TT[nt + '|' + pt]);
  arr.push(...GEN);
  return arr;
};
const endWithPunct = (t) => ENDCHARS.some(c => t.endsWith(c));

/* 提取相邻产品块之间的过渡句（coreBenefits 模块内，取每块最后一行） */
function extractTransitions(coreText, orderedSel) {
  const marks = orderedSel.map(p => '**' + fullName(p) + '**');
  const outs = [];
  for (let i = 0; i < orderedSel.length - 1; i++) {
    const iA = coreText.indexOf(marks[i]);
    const nextM = marks[i + 1];
    const iB = iA < 0 ? -1 : coreText.indexOf(nextM, iA + marks[i].length);
    if (iA < 0 || iB < 0) { outs.push({ prevId: orderedSel[i].id, nextId: orderedSel[i + 1].id, text: '', raw: '' }); continue; }
    const between = coreText.slice(iA + marks[i].length, iB);
    const lines = between.split('\n').map(s => s.trim()).filter(s => s.length);
    outs.push({ prevId: orderedSel[i].id, nextId: orderedSel[i + 1].id, text: lines.length ? lines[lines.length - 1] : '', raw: between });
  }
  return outs;
}
const SKINCARE_WORDS = ['皮肤', '肌肤', '洁面', '补水', '保湿', '渗透', '面部', '面膜', '护肤品', '精华液', '肤质', '痘痘', '毛孔', '胶原', '紧绷', '水乳', '养肤'];
const CONCRETE_WORDS = ['渗透肌肤', '皮肤在变好', '护肤这件事', '带一款靠谱的护肤品', '水乳霜', '洁面后', '每日涂抹', '涂在脸上', '一瓶搞定'];
/* 香水正当"贴肤"类表述（伪体香/贴近肌肤 等属于香调控词，不算护肤串词） */
const LEGIT_PHRASES = ['贴近肌肤', '贴合肌肤', '贴肤', '伪体香'];
const FRAGRANCE_WORDS = ['喷', '香调', '留香', '香气', '味道', '气味'];

function sanitizeBlock(t) { return t.split('同属「')[0]; }
function sliceByProduct(fullText, productsList) {
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
    blocks.push({ name: productsList[i].name, type: typeOf(productsList[i]), text: blkText });
    rest = rest.slice(start, end);
  }
  return blocks;
}

const failDetails = [];
let dumpLines = [];
const REPORT = [];

/* ---------- 7. 单套审计 ---------- */
function auditCombo(combo, dur, label, depth) {
  sandbox.state.selectedProductIds = combo.map(p => p.id);
  sandbox.state.duration = dur;
  sandbox.state.showCustomerProfile = false;
  sandbox.state.customerProfile = {};
  let sc;
  try { generateScript(true); } catch (e) { check(label + ' 生成无异常', false, e.message); return; }
  sc = sandbox.state.generatedScript;
  if (!sc) { check(label + ' 生成了脚本', false); return; }
  const full = sc.fullText;
  const orderedSel = sc.selectedProducts;
  const comboLabel = combo.map(p => `${p.brand || ''}${p.name}`).join(' + ') + ` [${dur}分钟]`;
  dumpLines.push(`\n==== ${label}（${comboLabel}） ====\n` + full + '\n');

  /* A1 模块齐全且非空 */
  const ids = sc.modules.map(m => m.id);
  const needIds = ['opening', 'coreBenefits', 'closing'];
  needIds.forEach(id => { check(`${label} 模块[${id}]存在`, ids.includes(id)); });
  sc.modules.forEach((m, mi) => {
    if (mi === 0) return;
    if (!(m.content || '').trim()) { failDetails.push(`${label} 空模块：${m.id}`); check(`${label} 模块[${m.id}]非空`, false, m.id); }
  });

  /* A2 顺序：大类型非递减 + 护肤内部非递减 */
  const typeSeq = orderedSel.map(p => TYPE_ORDER[typeOf(p)]);
  let orderOk = true;
  for (let i = 1; i < typeSeq.length; i++) if (typeSeq[i] < typeSeq[i - 1]) orderOk = false;
  check(`${label} 品类顺序(护肤→彩妆→香氛→保健→酒→纪念品)`, orderOk, orderedSel.map(p => `${p.name}(${typeOf(p)})`).join('→'));
  const skinIdx = orderedSel.map((p, i) => typeOf(p) === 'skincare' ? i : -1).filter(i => i >= 0);
  let skinOk = true;
  for (let k = 1; k < skinIdx.length; k++) {
    const a = orderedSel[skinIdx[k - 1]], b = orderedSel[skinIdx[k]];
    if ((SKIN_ORDER[a.category] || 4) > (SKIN_ORDER[b.category] || 4)) skinOk = false;
  }
  if (skinIdx.length >= 2) check(`${label} 护肤内部顺序(洁面→水→精华→眼霜→面霜→防晒)`, skinOk, orderedSel.filter(p => typeOf(p) === 'skincare').map(p => p.name).join('→'));
  const expectedSorted = sortForStory(combo).map(p => p.id).join(',');
  const actualSorted = orderedSel.map(p => p.id).join(',');
  check(`${label} 引擎重排与期望排序一致`, expectedSorted === actualSorted, actualSorted);

  const coreModule = sc.modules.find(m => m.id === 'coreBenefits');
  const coreText = coreModule ? coreModule.content : '';

  /* A3 产品段落文案匹配（香水/酒/纪念品不得串护肤词） */
  const banned = SKINCARE_WORDS.concat(CONCRETE_WORDS);
  const blocks = sliceByProduct(coreText, orderedSel.map(p => ({ ...p, brand: p.brand, name: p.name })));
  blocks.forEach(b => {
    const blk = sanitizeBlock(b.text);
    if (['fragrance', 'alcohol', 'souvenir'].includes(b.type)) {
      const clipped = LEGIT_PHRASES.reduce((acc, fp) => acc.split(fp).join(''), blk); // 剔除香调控词再查护肤词
      const hits = banned.filter(w => clipped.includes(w));
      if (hits.length) {
        const detail = `产品「${b.name}」段落出现护肤词: ${hits.join(',')} → ${blk.replace(/\s+/g, ' ').slice(0, 80)}`;
        failDetails.push(`${label} ${detail}`); check(`${label} ${b.name}文案匹配`, false, detail);
      }
    }
  });

  /* A4 产品间过渡句：合法性 + 科学性 */
  if (dur > 5 && orderedSel.length > 1) {
    const trans = extractTransitions(coreText, orderedSel.map(p => ({ id: p.id, brand: p.brand, name: p.name, category: p.category })));
    const usedSet = Object.create(null);
    let dupNote = [];
    trans.forEach(t => {
      const prevP = combo.find(x => x.id === t.prevId);
      const nextP = combo.find(x => x.id === t.nextId);
      if (!prevP || !nextP) return;
      if (!endWithPunct(t.text)) { failDetails.push(`${label} ${prevP.name}→${nextP.name} 过渡句标点异常：「${t.text}」`); check(`${label} 过渡句标点`, false, t.text); return; }
      const legal = legalPoolFor(prevP, nextP);
      const isLegal = legal.includes(t.text);
      check(`${label} 过渡句合法(${prevP.name}→${nextP.name})`, isLegal, `「${t.text}」`);
      if (!isLegal) failDetails.push(`${label} ${prevP.name}→${nextP.name} 过渡句不在合法池:「${t.text}」`);
      /* 科学性：吸收通道类 → 前序品类必须为水类 */
      if (ABSORB_WORDS.some(w => t.text.includes(w))) {
        const prevIsWater = ['化妆水', '精华水'].includes(prevP.category);
        check(`${label} 吸收通道科学限定(${prevP.name}→${nextP.name})`, prevIsWater, `「${t.text}」prev=${prevP.category}`);
        if (!prevIsWater) failDetails.push(`${label} ${prevP.name}→${nextP.name} 出现吸收通道类表述但前序为${prevP.category}:「${t.text}」`);
      }
      /* 软提示：同组合内过渡句重复 */
      if (usedSet[t.text]) dupNote.push(t.text);
      usedSet[t.text] = true;
    });
    if (dupNote.length) REPORT.push(`${label} 提示：组合内过渡句出现重复 ${dupNote.length} 处`);
  }

  /* A5 使用建议标题品类匹配 */
  const usageTitle = (sc.modules.find(m => m.id === 'usage') || {}).title || '';
  const allAlcohol = combo.every(p => typeOf(p) === 'alcohol');
  const allFragrance = combo.every(p => typeOf(p) === 'fragrance');
  const noSkincare = combo.every(p => ['fragrance', 'alcohol', 'souvenir', 'health'].includes(typeOf(p)));
  if (allAlcohol && dur > 3) check(`${label} 酒类标题含饮用`, /饮用/.test(usageTitle), usageTitle);
  if (allFragrance && dur > 3) check(`${label} 香水标题含香氛/香水`, /香氛|香水/.test(usageTitle), usageTitle);
  if (noSkincare && dur > 3) check(`${label} 无护肤产品不得套护肤标题`, !/护肤/.test(usageTitle), usageTitle);

  /* A6 不适合人群提示（时长≥8，通用模板路径会渲染） */
  if (dur >= 8) {
    combo.filter(p => p.unsuitable && p.unsuitable.length).forEach(p => {
      const has = coreText.includes('需要注意的是') || /谨慎|咨询医生|提醒/.test(coreText);
      check(`${label} ${p.name} 不适合人群提示`, has);
      if (!has) failDetails.push(`${label} ${p.name} 缺少不适合人群提示`);
    });
  }

  /* A7 全文违禁词 */
  const hits = BANNED.filter(w => full.includes(w));
  check(`${label} 全文违禁词清零`, hits.length === 0, hits.join(','));
  if (hits.length) failDetails.push(`${label} 全文违禁词: ${hits.join(',')}`);
}

/* ---------- 8. 设计套装（≥10 套，覆盖 ≥6 种类型组合模式） ---------- */
const SUITES = [
  { name: 'S1 全护肤流程（洁面→化妆水→精华→面霜）', ids: ['estee-005', 'estee-004', 'estee-001', 'estee-002'], dur: 8 },
  { name: 'S2 洁面→精华（复现用户示例：爱马仕洁面→精华）', ids: ['hermes-001', 'estee-001'], dur: 10 },
  { name: 'S3 洁面→精华水→精华（SK-II 三件套）', ids: ['skii-007', 'skii-001', 'skii-003'], dur: 10 },
  { name: 'S4 护肤+彩妆', ids: ['estee-005', 'estee-007', 'chanel-003'], dur: 8 },
  { name: 'S5 护肤+香水', ids: ['estee-004', 'hermes-003'], dur: 8 },
  { name: 'S6 彩妆+香水+酒', ids: ['chanel-003', 'ysl-001', 'plum-001'], dur: 10 },
  { name: 'S7 全酒类三款', ids: ['sake-002', 'wine-001', 'plum-001'], dur: 8 },
  { name: 'S8 保健+护肤', ids: ['swisse-001', 'estee-001'], dur: 8 },
  { name: 'S9 护肤+保健+酒+纪念品（大套装）', ids: ['estee-004', 'dhc-003v', 'sake-002', 'test-sou-01'], dur: 12 },
  { name: 'S10 全纪念品两款', ids: ['test-sou-01', 'test-sou-02'], dur: 8 },
  { name: 'S11 酒+纪念品', ids: ['wine-001', 'test-sou-03'], dur: 8 },
  { name: 'S12 六类全类型套装', ids: ['estee-005', 'estee-007', 'hermes-003', 'dhc-002v', 'wine-001', 'test-sou-01'], dur: 12 },
  { name: 'S13 短档5分钟混合（覆盖短时长路径）', ids: ['estee-005', 'estee-001', 'estee-002'], dur: 5 },
  { name: 'S14 双精华+面霜（同品类合并路径）', ids: ['estee-001', 'lancome-001', 'estee-002'], dur: 10 },
];
function runSuites() {
  let missing = [];
  SUITES.forEach(s => {
    const combo = s.ids.map(id => products.find(p => p.id === id)).filter(Boolean);
    if (combo.length !== s.ids.length) missing.push(s.name + ' 缺:' + s.ids.filter(id => !products.find(p => p.id === id)).join(','));
    auditCombo(combo, s.dur, s.name, 0);
  });
  if (missing.length) console.log('[WARN] 设计组合缺产品:', missing.join('; '));
  /* 模式覆盖统计 */
  const patterns = new Set();
  SUITES.forEach(s => { patterns.add(s.ids.map(id => { const p = products.find(x => x.id === id); return typeOf(p); }).join('|')); });
  check(`套装数量≥10（实际 ${SUITES.length} 套）`, SUITES.length >= 10);
  check(`套装覆盖≥6种类型组合模式（实际 ${patterns.size} 种）`, patterns.size >= 6);
}

/* ---------- 9. 仓库试运行：随机 N 套 ---------- */
function seededRand(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
function pick(arr, rnd) { return arr[Math.floor(rnd() * arr.length)]; }
function shuffle(arr, rnd) { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
function buildRepoCombos(rnd, n) {
  const byType = {};
  products.forEach(p => { const t = typeOf(p); (byType[t] = byType[t] || []).push(p); });
  const combos = [];
  let guard = 0;
  while (combos.length < n && guard++ < n * 60) {
    const count = 2 + Math.floor(rnd() * 7); // 2~8 款
    const types = shuffle(Object.keys(byType), rnd);
    const usedId = new Set();
    const picked = [];
    for (const t of types) {
      if (picked.length >= count) break;
      const pool = byType[t].filter(p => !usedId.has(p.id));
      if (!pool.length) continue;
      const cnt = Math.min(1 + Math.floor(rnd() * 2), count - picked.length);
      const ps = shuffle(pool, rnd).slice(0, cnt);
      ps.forEach(p => { picked.push(p); usedId.add(p.id); });
    }
    while (picked.length < count) {
      const rest = products.filter(p => !usedId.has(p.id));
      if (!rest.length) break;
      const q = pick(rest, rnd); picked.push(q); usedId.add(q.id);
    }
    if (picked.length >= 2) combos.push(picked);
  }
  return combos;
}
function runRepo(n, seed) {
  const rnd = seededRand(seed);
  const combos = buildRepoCombos(rnd, n);
  const durations = [2, 3, 5, 8, 10, 12];
  const patterns = new Set();
  combos.forEach((combo, ci) => {
    const dur = pick(durations, rnd);
    patterns.add(combo.map(p => typeOf(p)).join('|'));
    auditCombo(combo, dur, `R${ci + 1}`, 0);
  });
  check(`仓库试运行 ${n} 套`, combos.length === n, `实际 ${combos.length}`);
  const typesCovered = new Set();
  combos.forEach(c => c.forEach(p => typesCovered.add(typeOf(p))));
  check(`试运行覆盖全部6大类型`, typesCovered.size === 6, [...typesCovered].join(','));
  REPORT.push(`试运行 ${combos.length} 套，覆盖类型组合模式 ${patterns.size} 种`);
}

/* ---------- 10. 主流程 ---------- */
const args = process.argv.slice(2);
const REPO = args.includes('--repo') ? parseInt(args[args.indexOf('--repo') + 1] || '50', 10) : 0;
const DUMP = args.includes('--dump');
const SEED = parseInt(args[args.indexOf('--seed') + 1] || '20260829', 10);

auditStaticPool();
if (REPO > 0) runRepo(REPO, SEED); else runSuites();

/* ---------- 汇总 ---------- */
const passed = results.filter(r => r.pass).length;
const failed = results.filter(r => !r.pass);
console.log(`\n═══ 过渡话术套装测试 ${REPO > 0 ? `(仓库试运行 ${REPO} 套 seed=${SEED})` : '(设计套装 ' + SUITES.length + ' 套)'} ═══`);
console.log(`通过 ${passed} 项 / 失败 ${failed.length} 项`);
if (REPORT.length) console.log('\n--- 提示 ---\n' + REPORT.map(r => '• ' + r).join('\n'));
if (failed.length) {
  console.log('\n--- 失败明细 ---');
  failed.forEach(f => console.log('[FAIL] ' + f.name + (f.extra ? '  <' + f.extra + '>' : '')));
}
console.log('\n--- 硬伤明细 ---');
if (failDetails.length) failDetails.slice(0, 80).forEach(d => console.log('• ' + d));
else console.log('（无）');
if (DUMP) fs.writeFileSync('_suite_report.txt', dumpLines.join('\n'), 'utf8');

/* ---------- 单点模式 ---------- */
if (args.includes('--solo')) {
  const si = args.indexOf('--solo');
  const sid = args[si + 1];
  const sdur = parseInt(args[si + 2] || '12', 10);
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