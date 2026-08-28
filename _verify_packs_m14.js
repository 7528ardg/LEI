/* 客舱小助手 · M1.4 备份排除内容层验证（Node）
 * 1) vm 真实执行 index.html 的备份键收集逻辑，断言内容层键（pack前缀 / packs_index / kb_overlay_v1）被排除
 * 2) 三个外壳（index.html / _gzip_build.py 模板 / _build_4in1.py 模板）文案与排除逻辑一致性
 * 运行：node _verify_packs_m14.js
 */
'use strict';
const fs = require('fs');
const vm = require('vm');

const results = [];
function check(name, cond, extra) { results.push({ name, pass: !!cond, extra: extra || '' }); }

/* ---------- 1. index.html 备份逻辑真实执行 ---------- */
const html = fs.readFileSync('index.html', 'utf8');
const block = html.match(/\/\/ 易失\/临时类键不随备份恢复[\s\S]*?\nfunction collectBackupKeys\(\)\{[\s\S]*?\n\}/);
check('index.html 存在备份排除代码块', !!block);
if (block) {
  const storeMap = {
    'spring_quiz_data': 'x',        // 用户数据，应保留
    'spring_perf_data': 'x',        // 用户数据，应保留
    'pack:sales-2026-09': '{}',     // 内容层，应排除
    'pack:kb-legacy': '{}',         // 内容层，应排除
    'packs_index': '{}',            // 内容索引，应排除
    'kb_overlay_v1': '{}',          // 旧覆盖层（内容），应排除
    'cabin_first_time_seen': '1'    // 易失键，应排除
  };
  const keys = Object.keys(storeMap);
  const sandbox = {
    console,
    localStorage: {
      length: keys.length,
      key: (i) => keys[i] || null
    }
  };
  vm.createContext(sandbox);
  vm.runInContext(block[0], sandbox, { filename: 'backup-exclude.js' });
  const P = sandbox;
  check('isBackupExcluded(pack:*) = true', P.isBackupExcluded('pack:sales-2026-09') === true);
  check('isBackupExcluded(packs_index) = true', P.isBackupExcluded('packs_index') === true);
  check('isBackupExcluded(kb_overlay_v1 前缀) = true', P.isBackupExcluded('kb_overlay_v1') === true);
  check('isBackupExcluded(kb_overlay_v1 其他键) = false', P.isBackupExcluded('spring_perf_data') === false);
  check('isBackupExcluded(cabin_first_time_seen) = true', P.isBackupExcluded('cabin_first_time_seen') === true);
  const collected = P.collectBackupKeys().sort();
  check('collectBackupKeys 只含用户数据', JSON.stringify(collected) === JSON.stringify(['spring_perf_data', 'spring_quiz_data']), JSON.stringify(collected));
}

/* ---------- 2. 三外壳一致性 ---------- */
const files = ['index.html', '_gzip_build.py', '_build_4in1.py'];
const SENTENCE = '内容数据包（知识/销售/题库）随团队发布更新，不随个人备份迁移';
const FN = "BACKUP_EXCLUDE_PREFIX = ['pack:', 'kb_overlay_v1']";
for (const f of files) {
  const s = fs.readFileSync(f, 'utf8');
  check(f + ' 含排除前缀定义', s.indexOf(FN) >= 0);
  check(f + ' 含备份文案提示', s.indexOf(SENTENCE) >= 0);
}
/* 排除前缀定义三处文本完全一致 */
const prefixes = files.map(f => {
  const s = fs.readFileSync(f, 'utf8');
  const m = s.match(/const BACKUP_EXCLUDE_PREFIX = \[[^\]]*\]/);
  return m ? m[0] : '';
});
check('三处排除前缀定义一致', new Set(prefixes).size === 1, JSON.stringify(prefixes));

let pass = 0, fail = 0;
for (const r of results) {
  if (r.pass) { pass++; console.log('PASS  ' + r.name); }
  else { fail++; console.log('FAIL  ' + r.name + (r.extra ? '   [' + r.extra + ']' : '')); }
}
console.log('\n结果: ' + pass + ' 通过 / ' + fail + ' 失败 / 共 ' + results.length);
process.exit(fail ? 1 : 0);