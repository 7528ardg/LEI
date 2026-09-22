/* 销售话术库入库闸 scriptLibGuard 验证（2026-09-21）
 * 1) 从 beauty.html 真实抽取 guard 引擎块，在 vm 沙箱里执行（不是重写一份逻辑）
 * 2) 单测：硬红线拦截 / 自动改写 / 标签清洗 / 折扣口径 / 长度 / 空值 / 不误伤正常话术
 * 3) 全库扫描：对 1040 条现有话术跑一遍闸，统计拦截数（误伤必须极低）
 * 4) 静态针：入库闸 / 出口闸 / 渲染兜底 / window 挂载 四条路径都在位
 * 用法：node _verify_scriptlib_guard.js     失败即非零退出
 */
'use strict';
const fs = require('fs');
const vm = require('vm');
const B = __dirname + '/';

let pass = 0, fail = 0;
const fails = [];
function ok(name, cond, extra) {
  if (cond) { pass++; console.log('  ✓ ' + name); }
  else { fail++; fails.push(name + (extra ? ' :: ' + extra : '')); console.log('  ✗ ' + name + (extra ? ' :: ' + extra : '')); }
}

const beauty = fs.readFileSync(B + 'beauty.html', 'utf8');

console.log('== 1. 引擎块就位 ==');
const m = beauty.match(/\/\*__SCRIPTLIB_GUARD_20260921__BEGIN__\*\/([\s\S]*?)\/\*__SCRIPTLIB_GUARD_20260921__END__\*\//);
ok('beauty.html 含 guard 引擎块', !!m);
const sandbox = { window: {}, console: console };
vm.createContext(sandbox);
vm.runInContext(m[1], sandbox);
const G = sandbox.window.scriptLibGuard;
const R = sandbox.window.slRender;
ok('window.scriptLibGuard 已挂载', typeof G === 'function');
ok('window.slRender 已挂载', typeof R === 'function');

console.log('\n== 2. 硬红线必须拦下 ==');
const cases = [
  ['医疗宣称', '这款精华可以治疗敏感肌，根治泛红'],
  ['绝对化', '这是唯一的选择，国家级配方'],
  ['饥饿营销', '仅此一次，清仓甩卖'],
  ['伪科学', '促进血液循环加快，排出毒素'],
  ['评判旅客', '大妈您这皮肤，得用这个'],
  ['效果承诺', '三天见效，永久美白'],
  ['折扣口径', '今天打8折，满300立减50'],
  ['会员价', '给您会员价，员工内部价'],
  ['占位符', '还剩{X}份，${name}专享'],
  ['特殊人群', '孕妇也可以放心使用']
];
cases.forEach(function (c) {
  const r = G(c[1]);
  ok('拦截 ' + c[0], !r.ok && r.blocks.length > 0, JSON.stringify(r.blocks.map(x => x.rule)));
});

console.log('\n== 3. 自动改写与清洗 ==');
const r1 = G('这是爆款，明星产品，很多旅客回购');
ok('爆款→人气款、明星产品→人气产品', r1.ok && /人气款/.test(r1.content) && !/爆款/.test(r1.content), r1.content);
const r1b = G('比专柜便宜，手慢无哦');
ok('渠道比价与饥饿营销被自动改写（不打断录入，但已净化）',
  r1b.ok && !/比专柜|手慢无/.test(r1b.content), r1b.content);
ok('自动改写记入 issues 便于回溯', r1b.issues.some(x => x.rule === '已自动改写'), JSON.stringify(r1b.issues.map(x => x.rule)));
const r2 = G('您好，第一次来吗？别担心，我来帮您一步步挑选最适合的产品。');
ok('不误伤「第一次来」（软提示但不拦截）', r2.ok && r2.content.indexOf('第一次来') >= 0, JSON.stringify(r2.blocks));
const r3 = G('这款 <b>精华</b> 很好用\n\n换行也保留成空格');
ok('HTML 标签被清洗且不留残留', r3.ok && !/[<>]/.test(r3.content), r3.content);
ok('标签剥离有提示', r3.issues.some(x => x.rule === '已剥离标签'), JSON.stringify(r3.issues.map(x => x.rule)));
const r6 = G('点这里<script>alert(1)</script> <img onerror=alert(1)>');
ok('注入片段被彻底清洗（不残留可执行结构）', r6.ok && !/[<>]|onerror|script/i.test(r6.content), r6.content);
const r4 = G('长'.repeat(900));
ok('超长截断到 500 字', r4.content.length === 500, String(r4.content.length));
ok('空值安全', G('').ok && G(null).content === '' && G(undefined).content === '' && G(123).content === '123');
const r5 = G('   多余   空白   ');
ok('多余空白压缩', r5.content === '多余 空白', JSON.stringify(r5.content));
ok('渲染兜底会转义且先剥离标签', R('<b>x</b>') === 'x' && R('a & b') === 'a &amp; b',
  JSON.stringify([R('<b>x</b>'), R('a & b')]));

console.log('\n== 4. 全库扫描（现有 1040 条，误伤必须极低） ==');
function grab(text, start, o, c) {
  let d = 0, i = start, inStr = null;
  for (; i < text.length; i++) {
    const ch = text[i];
    if (inStr) { if (ch === '\\') { i++; continue; } if (ch === inStr) inStr = null; continue; }
    if (ch === '"' || ch === "'" || ch === '`') { inStr = ch; continue; }
    if (ch === o) d++;
    else if (ch === c) { d--; if (d === 0) return text.slice(start, i + 1); }
  }
  throw new Error('not closed');
}
const mm = /^\s*const scriptLibraryData = \{/m.exec(beauty);
const lib = new Function('return (' + grab(beauty, mm.index + mm[0].length - 1, '{', '}') + ')')();
let total = 0, blocked = 0, changed = 0, warned = 0;
const samples = [];
Object.keys(lib).forEach(function (k) {
  (lib[k].scripts || []).forEach(function (s) {
    total++;
    const r = G(s.content);
    if (!r.ok) { blocked++; if (samples.length < 5) samples.push(k + '/' + s.id + ' 「' + (r.blocks[0] && r.blocks[0].hit) + '」 ' + (r.blocks[0] && r.blocks[0].rule)); }
    if (r.changed) changed++;
    if (r.issues.some(x => x.level === 'warn')) warned++;
  });
});
ok('库内话术总数 1040', total === 1040, String(total));
ok('硬红线拦截数为 0（库内已治理干净）', blocked === 0, blocked + ' 条：' + samples.join(' | '));
ok('自动改写未改坏现有话术（changed 很少）', changed <= 5, String(changed));
console.log('    软提示（不阻断）' + warned + ' 条');

console.log('\n== 5. 四条路径静态针 ==');
[
  ['入库闸', '话术未通过合规校验'],
  ['出口闸', 'window.scriptLibGuard(content)'],
  ['渲染兜底', 'window.slRender(script.content)'],
  ['复制按 id', "copyScriptById('"],
  ['window 挂载', 'window.copyScriptById = copyScriptById'],
  ['window 挂载·保存', 'window.saveScriptLib = saveScriptLib'],
  ['读入过闸', '已丢弃不合规自定义话术']
].forEach(function (p) { ok(p[0] + ' 在位', beauty.indexOf(p[1]) >= 0); });

console.log('\n===== 汇总 =====');
console.log('通过 ' + pass + ' / ' + (pass + fail));
if (fail) {
  console.log('失败项：');
  fails.forEach(f => console.log('  - ' + f));
  process.exit(1);
}
console.log('话术库入库闸全绿：红线拦得住、改写不误伤、渲染/复制/入库/读入 四道闸都在位。');
