/* 导航升级守护（20260917）：#1 浮岛吸顶 / #3 面包屑 / #4 二级下拉 / #5 巨型菜单 / #9 滚动收缩
 * 断言：三个壳（index.html / _gzip_build.py TEMPLATE / _build_4in1.py TEMPLATE）四块齐全且内容一致；
 *       12 模块元数据完整；beauty/manual 深跳桥在位；全屏面板遵守限高内滚 + 关闭三路径铁律。
 * 用法：node _verify_nav_20260917.js   （退出码非 0 = 失败）
 */
'use strict';
const fs = require('fs');
const path = require('path');
const HERE = __dirname;
let fails = 0, total = 0;

function t(name, cond) {
  total++;
  if (!cond) { fails++; console.log('  [FAIL] ' + name); }
  else console.log('  [ok] ' + name);
}

function read(name) {
  return fs.readFileSync(path.join(HERE, name), 'utf8');
}
/* 归一化：去注释与空白后比对（与 _sync_shell_js 同思路，容忍模板注释差异） */
function norm(x) {
  return x.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^[ \t]*\/\/.*$/gm, '').replace(/\s+/g, ' ').trim();
}
/* 从壳文件中截取标记块 */
function block(src, beginMark, endMark) {
  const i = src.indexOf(beginMark);
  if (i < 0) return null;
  const j = src.indexOf(endMark, i);
  if (j < 0) return null;
  return src.slice(i, j + endMark.length);
}

const SHELLS = ['index.html', '_gzip_build.py', '_build_4in1.py'];
const CSS_B = '__NAV_DESIGN_20260917_CSS__';
const JS_B = '__NAV_DESIGN_20260917_JS__';
const MOD_IDS = ['home', 'qa', 'quiz', 'performance', 'beauty', 'risk', 'medical', 'daily', 'manual', 'report', 'kbadmin', 'issues'];

console.log('===== 导航升级守护 _verify_nav_20260917 =====');

/* 1) 三壳四块齐全 */
const shells = {};
for (const f of SHELLS) {
  const s = read(f);
  shells[f] = s;
  t(f + ' 含 CSS 标记块', s.includes(CSS_B + 'BEGIN') && s.includes(CSS_B + 'END'));
  t(f + ' 含 JS 标记块', s.includes(JS_B + 'BEGIN') && s.includes(JS_B + 'END'));
  t(f + ' 含面包屑 #shellCrumb', s.includes('id="shellCrumb"'));
  t(f + ' 含巨型菜单按钮 #megaBtn', s.includes('id="megaBtn"'));
  t(f + ' 标记块各只出现一次（幂等）',
    (s.split(CSS_B + 'BEGIN').length - 1) === 1 &&
    (s.split(JS_B + 'BEGIN').length - 1) === 1);
}

/* 2) 三壳 CSS / JS 块内容一致 */
const cssBlocks = SHELLS.map(f => block(shells[f], CSS_B + 'BEGIN', CSS_B + 'END'));
t('三壳 CSS 块归一化一致', cssBlocks.every(b => b && norm(b) === norm(cssBlocks[0])));
const jsBlocks = SHELLS.map(f => block(shells[f], JS_B + 'BEGIN', JS_B + 'END'));
t('三壳 JS 块归一化一致', jsBlocks.every(b => b && norm(b) === norm(jsBlocks[0])));

/* 3) 关键行为断言（取 index.html 块检查） */
const css = cssBlocks[0] || '';
const js = jsBlocks[0] || '';

/* #1 浮岛吸顶 */
t('#1 顶栏浮岛化（圆角+边框+阴影）', css.includes('.topbar{top:10px;left:12px;right:12px;border:1px solid var(--border);border-radius:18px'));
t('#1 内容区让位 sys-area top', css.includes('.sys-area{top:calc(var(--topbar-h) + 16px);}'));
/* #3 面包屑 */
t('#3 面包屑仅宽屏展示', css.includes('@media(min-width:1101px){.shell-crumb{display:flex;}}'));
t('#3 面包屑含模块级+子页级节点', shells['index.html'].includes('id="crumbMod"') && shells['index.html'].includes('id="crumbSub"'));
/* #4 二级下拉 */
t('#4 下拉限高内滚（弹窗铁律精神）', css.includes('.nav-drop{position:fixed;') && css.includes('max-height:min(70vh,460px);overflow-y:auto'));
t('#4 hover 精确指针门槛', js.includes("matchMedia('(hover: hover) and (pointer: fine)')"));
/* #5 巨型菜单 */
t('#5 面板限高内滚（限高 78vh）', css.includes('.mega-panel{position:fixed;') && css.includes('max-height:min(78vh,640px);overflow-y:auto'));
t('#5 关闭三路径（X+遮罩+底部按钮）', js.includes("id=\"megaCloseX\"") && js.includes('id="megaCloseFoot"') && js.includes("megaMask.addEventListener('click', closeMegaMenu)"));
t('#5 Esc 统一关闭', js.includes("'Escape'"));
t('#5 12 模块元数据齐全', MOD_IDS.every(id => js.includes(' ' + id + ':')));
for (const id of MOD_IDS) t('#5 元数据含 ' + id, js.includes(' ' + id + ':'));
/* #9 滚动收缩 */
t('#9 收缩态样式（变实色收紧）', css.includes('html.nav-scrolled .topbar{top:6px;height:48px;'));
t('#9 iframe 滚动绑定（含 .main-scroll-container）', js.includes('.main-scroll-container') && js.includes('__navScrollBound'));
t('#9 滚动迟滞（64 进入 / 12 退出）', js.includes('y > 64') && js.includes('y < 12'));
/* 深跳 */
t('深跳消息 cc:nav-jump', js.includes("type:'cc:nav-jump'"));
t('子页上报通道 cc:crumb', js.includes("type:'cc:crumb'"));

/* 4) 模块深跳桥 */
const beauty = read('beauty.html');
const manual = read('manual.html');
t('beauty 深跳桥在位（幂等唯一）', (beauty.split('__NAV_BRIDGE_20260917__').length - 1) === 1 && beauty.includes("__ccNavBridge") && beauty.includes("cc:nav-jump"));
t('manual 深跳桥在位（幂等唯一）', (manual.split('__NAV_BRIDGE_20260917__').length - 1) === 1 && manual.includes('ccGoView') && manual.includes('cc:nav-jump'));

/* 5) 构建链挂载 */
const buildAll = read('_build_all.py');
t('_build_all 挂载注入步骤', buildAll.includes('_apply_nav_20260917.py'));
t('_build_all 挂载本守护', buildAll.includes('_verify_nav_20260917.js'));

console.log('-----');
console.log(fails ? ('!! 导航守护失败 ' + fails + ' / ' + total) : ('导航守护全部通过（' + total + ' 断言）'));
process.exit(fails ? 1 : 0);
