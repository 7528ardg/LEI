/* 静态守护：壳层（index.html 与两个构建模板）必须携带
   - CCSheet 引擎（CSS/JS 标记块 + window.CCSheet 对外 API）
   - 弹窗动效适配层（fxRecede / fxModal 存在且 documentElement 已加保护）
   - 内嵌高度补偿（--embed-bottom：EMBED_BASE + applyEmbedVars + refreshEmbedVars）
   - 深色打通（applyEmbedVars 写 data-bs-theme）
   - 「更多」面板走 CCSheet 引擎
   零依赖、零网络，可挂进 _build_all.py。
   运行：node _verify_ccsheet_static.js
*/
'use strict';
const fs = require('fs');
const results = [];
const check = (n, c, x) => results.push({ n, pass: !!c, x: x === undefined ? '' : String(x) });

// 从构建脚本里抽出 TEMPLATE 字符串
function templateOf(file) {
  const s = fs.readFileSync(file, 'utf8');
  const a = s.indexOf("TEMPLATE = u'''");
  if (a < 0) return null;
  const b = s.indexOf("'''", a + 16);
  if (b < 0) return null;
  return s.slice(a + 16, b);
}

const shells = [
  { name: 'index.html', body: fs.readFileSync('index.html', 'utf8') },
  { name: '_gzip_build.py', body: templateOf('_gzip_build.py') || '' },
  { name: '_build_4in1.py', body: templateOf('_build_4in1.py') || '' },
];

for (const sh of shells) {
  const t = sh.body;
  const tag = sh.name;
  check(tag + ' 非空', t.length > 1000, t.length);

  // 1) CCSheet 引擎
  check(tag + ' 含 CCSheet CSS 标记', t.indexOf('/*__CC_SHEET:v1__*/') >= 0);
  check(tag + ' 含 CCSheet JS 标记', t.indexOf('/*__CC_SHEET_JS:v1__*/') >= 0);
  check(tag + ' 暴露 window.CCSheet', t.indexOf('window.CCSheet') >= 0);
  check(tag + ' 有 Sheet 构造器', /function Sheet\s*\(/.test(t));
  check(tag + ' 十种交互：磁吸 snapTo', /snapTo\s*[:=]|prototype\.snapTo/.test(t));
  check(tag + ' 十种交互：嵌套 openNested', /openNested/.test(t));
  check(tag + ' 十种交互：变页面 toPage', /toPage/.test(t));
  check(tag + ' 十种交互：变成功 succeed', /succeed/.test(t));
  check(tag + ' 十种交互：背景退后 csn-recede', t.indexOf('csn-recede') >= 0);
  check(tag + ' 拖拽阈值（速度+距离）', /VEL\s*=/.test(t) && /DIST_RATIO\s*=/.test(t));

  // 2) 弹窗动效适配层 + documentElement 保护
  check(tag + ' 含 fxRecede 安全写入', /function\s+fxRecede\s*\(/.test(t));
  check(tag + ' fxRecede 有 classList 守卫', /!el\s*\|\|\s*!el\.classList/.test(t));
  check(tag + ' 含 fxModal', /function\s+fxModal\s*\(/.test(t));
  check(tag + ' fxModal 有 mask.classList 守卫', /!mask\.classList/.test(t));
  check(tag + ' fxModal 有 card.classList 守卫', /cardCls|card\.classList/.test(t));

  // 3) 内嵌高度补偿
  check(tag + ' 含 EMBED_BASE(--embed-bottom)', t.indexOf('--embed-bottom') >= 0);
  check(tag + ' 含 applyEmbedVars 定义', /function\s+applyEmbedVars\s*\(/.test(t));
  check(tag + ' 含 refreshEmbedVars 定义', /function\s+refreshEmbedVars\s*\(/.test(t));
  check(tag + ' refreshEmbedVars 仅 1 处定义', (t.match(/function\s+refreshEmbedVars\s*\(/g) || []).length === 1);
  check(tag + ' applyEmbedVars 仅 1 处定义', (t.match(/function\s+applyEmbedVars\s*\(/g) || []).length === 1);
  check(tag + ' resize/orientation 触发重算', /orientationchange/.test(t) && /refreshEmbedVars/.test(t));

  // 4) 深色打通：applyEmbedVars 写 data-bs-theme
  const av = t.match(/function\s+applyEmbedVars\s*\([\s\S]{0,900}?\n\}/);
  check(tag + ' applyEmbedVars 写 data-theme', !!av && /setAttribute\(\s*[\'"]data-theme/.test(av[0]));
  check(tag + ' applyEmbedVars 写 data-bs-theme', !!av && /data-bs-theme/.test(av[0]));

  // 5) 更多面板走引擎
  check(tag + ' openMoreSheet 调 CCSheet', /function\s+openMoreSheet[\s\S]{0,1200}?CCSheet\.actions/.test(t));
  check(tag + ' closeMoreSheet 关引擎实例', t.indexOf('_moreSheetInst') >= 0);

  // 6) 空安全
  check(tag + ' closePacksModal 空安全', /function\s+closePacksModal\(\)\{\s*const m=document\.getElementById/.test(t));
}

let p = 0, f = 0;
for (const r of results) { if (r.pass) p++; else { f++; console.log('FAIL  ' + r.n + (r.x ? '  [' + r.x + ']' : '')); } }
console.log('\n结果: ' + p + ' 通过 / ' + f + ' 失败 / 共 ' + results.length);
process.exit(f ? 1 : 0);
