// 合并 8 批联网查价结果并回写 beauty.html 的 competitorData
// 运行：node _merge_competitors.js
'use strict';
const fs = require('fs');
const path = require('path');
const HERE = __dirname;

const FILE = path.join(HERE, 'beauty.html');
let raw = fs.readFileSync(FILE, 'utf8');
const hasBOM = raw.charCodeAt(0) === 0xFEFF;
if (hasBOM) raw = raw.slice(1);

const startMark = 'const competitorData = [';
const sIdx = raw.indexOf(startMark);
if (sIdx === -1) { console.log('FAIL startMark not found'); process.exit(1); }
let depth = 0, eIdx = -1;
for (let i = sIdx + startMark.length - 1; i < raw.length; i++) {
  const ch = raw[i];
  if (ch === '[') depth++;
  else if (ch === ']') { depth--; if (depth <= 0) { eIdx = i + 1; break; } }
}
if (eIdx === -1) { console.log('FAIL end not found'); process.exit(1); }
const oldBlock = raw.slice(sIdx, eIdx);
let original;
try { original = new Function('return ' + oldBlock.replace('const competitorData = ', ''))(); }
catch (e) { console.log('PARSE_ORIG_ERR', e.message); process.exit(1); }

// 读取 8 个结果文件
const updateMap = {}; // id -> {prices:[...], source}
for (let i = 1; i <= 8; i++) {
  const f = path.join(HERE, '_cmp_result_' + i + '.json');
  let d;
  try { d = JSON.parse(fs.readFileSync(f, 'utf8')); }
  catch (e) { console.log('FAIL result' + i + ' parse: ' + e.message); process.exit(1); }
  if (!d || !Array.isArray(d.competitors)) { console.log('FAIL result' + i + ' no competitors'); process.exit(1); }
  for (const c of d.competitors) {
    if (!c || !c.id) continue;
    updateMap[c.id] = { prices: Array.isArray(c.prices) ? c.prices : [], source: c.source || '' };
  }
}

// 校验覆盖
const missing = original.filter(c => !updateMap[c.id]).map(c => c.id);
if (missing.length) { console.log('FAIL 无结果覆盖: ' + missing.join(',')); process.exit(1); }
const unknown = Object.keys(updateMap).filter(id => !original.some(c => c.id === id));
if (unknown.length) { console.log('WARN 结果含未知 id: ' + unknown.join(',')); }

const PRICE_UT = '2026年08月30日 联网更新';
const TOP_UT = '2026-08-30';

// 归一化价格行
const normPrice = (p) => {
  const price = parseInt(p.price);
  if (!(price > 0)) return null;
  return {
    platform: String(p.platform || '').trim(),
    store: String(p.store || '').trim(),
    size: String(p.size || '').trim(),
    price: price,
    note: String(p.note || '日常价').trim(),
    updateTime: PRICE_UT
  };
};

let changedCount = 0, keptCount = 0, rowAdd = 0, rowDel = 0;
const merged = original.map((c) => {
  const res = updateMap[c.id];
  let newPrices = (res ? res.prices : []).map(normPrice).filter(Boolean);
  const oldPrices = c.prices || [];
  const oldStr = oldPrices.map(p => p.price).join(',');
  if (!newPrices.length) {
    // 结果为空：保留原价格，仅刷新 updateTime
    newPrices = oldPrices.map(p => ({ ...p, updateTime: PRICE_UT }));
    keptCount++;
  } else {
    rowAdd += Math.max(0, newPrices.length - oldPrices.length);
    rowDel += Math.max(0, oldPrices.length - newPrices.length);
    if (newPrices.map(p => p.price).join(',') !== oldStr) changedCount++;
    else keptCount++;
  }
  return {
    id: c.id, name: c.name, brand: c.brand, category: c.category,
    prices: newPrices,
    ingredients: c.ingredients || [],
    advantages: c.advantages || [],
    disadvantages: c.disadvantages || [],
    complianceNote: c.complianceNote || '',
    updateTime: TOP_UT
  };
});

// 序列化为与原文件一致格式（4 空格缩进、单引号键、CRLF）
const esc = (s) => String(s).replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\r/g, '').replace(/\n/g, '\\n');
const IND = '    ';
const PRICE_ORDER = ['platform', 'store', 'size', 'price', 'note', 'updateTime'];

function serArray(arr, indent) {
  if (!arr.length) return indent + '[]';
  const inner = indent + IND;
  const lines = arr.map((el) => {
    if (Array.isArray(el)) return serArray(el, inner);
    if (el !== null && typeof el === 'object') return serObj(el, inner, PRICE_ORDER);
    if (typeof el === 'number') return inner + String(el);
    return inner + "'" + esc(el) + "'";
  });
  return indent + '[\n' + lines.join(',\n') + '\n' + indent + ']';
}
function serObj(obj, indent, order) {
  const inner = indent + IND;
  const keys = order || Object.keys(obj);
  const lines = keys.filter((k) => obj[k] !== undefined).map((k) => {
    const v = obj[k];
    let vs;
    if (Array.isArray(v)) vs = serArray(v, inner);
    else if (typeof v === 'number') vs = String(v);
    else vs = "'" + esc(v) + "'";
    return inner + "'" + k + "': " + vs;
  });
  return indent + '{\n' + lines.join(',\n') + '\n' + indent + '}';
}

const fieldOrder = ['id', 'name', 'brand', 'category', 'prices', 'ingredients', 'advantages', 'disadvantages', 'complianceNote', 'updateTime'];
const bodyLines = merged.map((c) => serObj(c, IND, fieldOrder));
const newBlock = 'const competitorData = [\n' + bodyLines.join(',\n') + '\n];';

// 校验回读
let back;
try { back = new Function('return ' + newBlock.replace('const competitorData = ', ''))(); }
catch (e) { console.log('NEWBLOCK_PARSE_ERR', e.message); process.exit(1); }
if (!Array.isArray(back) || back.length !== original.length) { console.log('FAIL 回读数量不符 ' + back.length + ' vs ' + original.length); process.exit(1); }
const idOk = back.every((c, i) => c.id === original[i].id);
if (!idOk) { console.log('FAIL 回读 id 顺序不一致'); process.exit(1); }
const priceOk = back.every(c => Array.isArray(c.prices) && c.prices.every(p => p.price > 0));
if (!priceOk) { console.log('FAIL 存在非法价格行'); process.exit(1); }

// 写回
const out = raw.slice(0, sIdx) + newBlock + raw.slice(eIdx);
fs.writeFileSync(FILE, (hasBOM ? '\uFEFF' : '') + out, 'utf8');

console.log('OK 已回写 beauty.html');
console.log('总竞品 ' + merged.length + '，覆盖 ' + Object.keys(updateMap).length + ' 款');
console.log('价格有变化 ' + changedCount + ' 款，保留原价 ' + keptCount + ' 款');
console.log('新增价格行 ' + rowAdd + '，删除价格行 ' + rowDel);
console.log('updateTime=' + PRICE_UT);
