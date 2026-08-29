// 提取 beauty.html 的 competitorData 数组到 competitors.json
// 运行：node _extract_competitors.js
'use strict';
const fs = require('fs');
const path = require('path');

const src = fs.readFileSync(path.join(__dirname, 'beauty.html'), 'utf8');
const startMark = 'const competitorData = [';
const sIdx = src.indexOf(startMark);
if (sIdx === -1) { console.log('FAIL startMark not found'); process.exit(1); }
// 从起点找配对的结束 ]：逐字符扫描，统计 [ ] 深度（从外层 [ 本身开始计数）
let depth = 0, eIdx = -1;
for (let i = sIdx + startMark.length - 1; i < src.length; i++) {
  const ch = src[i];
  if (ch === '[') depth++;
  else if (ch === ']') { depth--; if (depth <= 0) { eIdx = i + 1; break; } }
}
if (eIdx === -1) { console.log('FAIL end not found'); process.exit(1); }
const blockText = src.slice(sIdx, eIdx);
let arr;
try {
  arr = new Function('return ' + blockText.replace('const competitorData = ', ''))();
} catch (e) { console.log('EVAL_ERR', e.message); process.exit(1); }
if (!Array.isArray(arr)) { console.log('FAIL not array'); process.exit(1); }
fs.writeFileSync(path.join(__dirname, 'competitors.json'), JSON.stringify(arr, null, 2), 'utf8');
console.log('OK total=' + arr.length + ' ids=' + arr.map(c => c.id).join(','));
console.log('示例字段: ' + Object.keys(arr[0]).join(','));
console.log('comp001 价格数=' + arr[0].prices.length);
