/* 客舱小助手 · M1.5 产物收尾验证（Node）
 * 对两个单文件产物（spring-assistant.html / 客舱小助手（离线完整版）.html）：
 * 1) 外壳本身含备份排除特征（BACKUP_EXCLUDE_PREFIX）
 * 2) 解 base64 → gunzip 还原每个模块，断言数据包新特征串存在
 * 运行：node _verify_packs_m15.js
 */
'use strict';
const fs = require('fs');
const zlib = require('zlib');

const results = [];
function check(name, cond, extra) { results.push({ name, pass: !!cond, extra: extra || '' }); }

const MODULE_FEATURES = {
  qa: ['cabin-data-pack-v1', 'window.PACKS = PACKS', 'applyPacks', 'kb_overlay_v1'],
  beauty: ['cabin-data-pack-v1', '数据包销售覆盖', 'applySales'],
  quiz: ['cabin-data-pack-v1', '数据包题库覆盖', 'applyQuiz'],
  kbadmin: ['cabin-data-pack-v1', '数据包中心', 'PACK_COMPLIANCE', 'renderPacks', 'makeSamplePack']
};
const PRODUCTS = ['spring-assistant.html', '客舱小助手（离线完整版）.html'];

for (const prod of PRODUCTS) {
  const src = fs.readFileSync(prod, 'utf8');
  check(prod + ' 外壳含备份排除前缀', src.indexOf("BACKUP_EXCLUDE_PREFIX = ['pack:', 'kb_overlay_v1']") >= 0);
  for (const mod of Object.keys(MODULE_FEATURES)) {
    let inner = null;
    const m = src.match(new RegExp(mod + ':\\s*"([A-Za-z0-9+/=]+)"'));
    if (m) {
      try {
        inner = zlib.gunzipSync(Buffer.from(m[1], 'base64')).toString('utf8');
      } catch (e) { inner = null; }
    }
    if (!inner) { check(prod + ' ' + mod + ' 内嵌可解压', false, '未解出'); continue; }
    check(prod + ' ' + mod + ' 内嵌可解压', true);
    for (const feat of MODULE_FEATURES[mod]) {
      check(prod + ' ' + mod + ' 内嵌特征 [' + feat + ']', inner.indexOf(feat) >= 0);
    }
  }
}

let pass = 0, fail = 0;
for (const r of results) {
  if (r.pass) { pass++; console.log('PASS  ' + r.name); }
  else { fail++; console.log('FAIL  ' + r.name + (r.extra ? '   [' + r.extra + ']' : '')); }
}
console.log('\n结果: ' + pass + ' 通过 / ' + fail + ' 失败 / 共 ' + results.length);
process.exit(fail ? 1 : 0);