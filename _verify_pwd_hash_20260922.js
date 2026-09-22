/* =============================================================================
 * 凭据哈希治理 · 回归守护（来源：2026-09-22 系统性代码审查 M1 / M2）
 * -----------------------------------------------------------------------------
 * 背景：
 *   M1 管理员口令（3 位明文，值不在本文件出现）硬编码于 index.html /
 *      _shell_enhance.js（并随构建注入 spring-assistant.html /
 *      客舱小助手（离线完整版）.html）。
 *      本地需要做「种子自洽」校验时，可把真实口令首行写入
 *      （已被 .gitignore 忽略的）_admin_seed_local.txt；缺该文件则自动跳过 B 项。
 *   M2 用户口令、安全问题答案明文落盘（localStorage cabin_users_v1）；
 *      performance.html 的备份加密口令明文落在 sessionStorage。
 *
 * 断言（任一失败即 exit 1）：
 *   A 源码与产物中不存在明文口令/答案字段；ADMIN 仅带 盐 + 密码哈希
 *   B ADMIN 种子哈希与「本文件自身算法」自洽（改了算法忘重算种子 → 立刻失败）
 *   C index.html 与 _shell_enhance.js 两套实现的摘要逐位一致（防双源漂移）
 *   D 行为：注册只存哈希 / 正确口令通过 / 错误口令拒绝 / 旧明文命中后原地升级 /
 *          拒绝时不改动记录 / 盐随机
 *   E performance.html 的加密口令改为内存态（不再落 sessionStorage）
 *
 * 说明：全部临时文件写系统临时目录并「固定名覆盖写」，全程不删除任何文件
 *      （避免累计删除触发沙箱批量删除闸门）。
 * 用法：node _verify_pwd_hash_20260922.js
 * ============================================================================= */
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');

const ROOT = __dirname;
let fail = 0, pass = 0, skip = 0;
const ck = (name, cond, extra) => {
  if (cond) { pass++; console.log('  ✓ ' + name); }
  else { fail++; console.log('  ✗ ' + name + (extra ? ('  → ' + extra) : '')); }
};
const sec = (t) => console.log('\n== ' + t + ' ==');
const rd = (p) => { try { return fs.readFileSync(path.join(ROOT, p), 'utf8'); } catch (e) { return null; } };

/* 管理员口令种子：**刻意不写进源码**（本仓库历史版本已把该口令公开在若干测试夹具里，
   再添一处公开副本只会扩大暴露面）。本机把口令单独放在 `_admin_seed_local.txt`（首行）即可
   启用「种子自洽」强断言；该文件被 .gitignore 的 `/_*` 规则忽略，不会入库。
   缺失时只跳过这一条，其余守护（结构 / 双源一致 / 行为 / 落盘）全部照常执行。 */
function readAdminSeed() {
  try {
    const t = fs.readFileSync(path.join(ROOT, '_admin_seed_local.txt'), 'utf8').split(/\r?\n/)[0].trim();
    return t || null;
  } catch (e) { return null; }
}
const ADMIN_SEED = readAdminSeed();

/* 允许出现「明文口令字段」的例外文件名（历史备份/归档不参与守护） */
const LAYER_MARK = '口令哈希层（2026-09-22 安全审查修复）';
/* 明文口令/答案字段的正则：`密码:'123'`、`安全答案: "x"`（不含 密码哈希 / 安全答案哈希） */
const PLAIN_RE = /(?:^|[^\u4e00-\u9fa5A-Za-z0-9_])(密码|安全答案)\s*:\s*(['"])/g;

/* ---------------------------------------------------------------- A 结构 */
sec('A. 源码与产物：无明文口令字段，ADMIN 仅带 盐 + 密码哈希');

const AUTH_SOURCES = ['index.html', '_shell_enhance.js'];
const AUTH_ARTIFACTS = [
  'spring-assistant.html',
  '客舱小助手（离线完整版）.html',
  path.join('APK封装', 'CabinAssistant', 'assets', 'www', 'index.html'),
  path.join('PWA封装', '客舱小助手', 'index.html'),
];

for (const f of AUTH_SOURCES.concat(AUTH_ARTIFACTS)) {
  const s = rd(f);
  if (s === null) { console.log('  [SKIP] ' + f + '（不存在）'); continue; }
  const hits = [];
  let m;
  PLAIN_RE.lastIndex = 0;
  while ((m = PLAIN_RE.exec(s)) !== null) hits.push(m[0].trim());
  ck(f + ' 无明文口令字段', hits.length === 0, hits.slice(0, 3).join(' | '));

  const adm = /var ADMIN = \{[^}]*\};/.exec(s);
  if (adm) {
    ck(f + ' ADMIN 不含 密码 明文字段', !/(?:^|[{,\s])密码\s*:/.test(adm[0]));
    ck(f + ' ADMIN 带 盐 + 密码哈希', /盐\s*:\s*['"]/.test(adm[0]) && /密码哈希\s*:\s*['"]/.test(adm[0]));
  } else {
    ck(f + ' 含 ADMIN 定义', false);
  }
}

/* --------------------------------------------- 提取哈希层（用于 B / C / D） */
function extractLayer(src, file) {
  const i = src.indexOf(LAYER_MARK);
  if (i < 0) return null;
  const start = src.lastIndexOf('/*', i);
  // 结束锚点：各文件哈希层之后的第一个稳定分隔
  const anchors = ['function lsGet(k)', '/* ---------- 用户库 ---------- */'];
  let end = -1;
  for (const a of anchors) { const j = src.indexOf(a, start); if (j > 0 && (end < 0 || j < end)) end = j; }
  if (end < 0) return null;
  const body = src.slice(start, end);
  return body.includes('function _pwdHash(') ? body : null;
}

function buildSandbox(layerSrc, adminDecl, extra) {
  return [
    '/* 自动生成：凭据哈希层沙箱 */',
    layerSrc,
    adminDecl,
    'var __saved = null;',
    'function saveUsers(u){ __saved = u; }',
    'function lsGet(){ return null; }',
    'function lsSet(){}',
    'function lsDel(){}',
    (extra || ''),
    'module.exports = { _pwdHash: _pwdHash, _randSalt: _randSalt, setUserPwd: setUserPwd,',
    '  verifyUserPwd: verifyUserPwd, ADMIN: ADMIN,',
    '  verifyUserAnswer: (typeof verifyUserAnswer === "function") ? verifyUserAnswer : null,',
    '  getSaved: function(){ return __saved; } };',
  ].join('\n');
}

const tmpDir = os.tmpdir();
function loadSandbox(file, tag) {
  const src = rd(file);
  if (!src) return null;
  const layer = extractLayer(src, file);
  if (!layer) { ck(file + ' 可提取哈希层', false); return null; }
  const adm = /var ADMIN = \{[^}]*\};/.exec(src);
  if (!adm) { ck(file + ' 可提取 ADMIN', false); return null; }
  const p = path.join(tmpDir, '__pwdhash_sandbox_' + tag + '.js');
  fs.writeFileSync(p, buildSandbox(layer, adm[0]), 'utf8');
  delete require.cache[require.resolve(p)];
  return require(p);
}

sec('B. ADMIN 种子哈希与本文件算法自洽（无明文）');
const indexMod = loadSandbox('index.html', 'index');
const shellMod = loadSandbox('_shell_enhance.js', 'shell');

for (const [tag, mod] of [['index.html', indexMod], ['_shell_enhance.js', shellMod]]) {
  if (!mod) { ck(tag + ' 沙箱可加载', false); continue; }
  ck(tag + ' ADMIN 无明文字段', !Object.prototype.hasOwnProperty.call(mod.ADMIN, '密码'));
  ck(tag + ' ADMIN 哈希为 64 位十六进制', /^[0-9a-f]{64}$/.test(String(mod.ADMIN.密码哈希 || '')), mod.ADMIN.密码哈希);
  ck(tag + ' ADMIN 盐非空且 >= 8 位', typeof mod.ADMIN.盐 === 'string' && mod.ADMIN.盐.length >= 8);
  if (ADMIN_SEED) {
    ck(tag + ' ADMIN 哈希 == _pwdHash(种子, 盐)',
      mod._pwdHash(ADMIN_SEED, mod.ADMIN.盐) === mod.ADMIN.密码哈希,
      mod.ADMIN.密码哈希);
  } else {
    skip++;
    console.log('  [SKIP] ' + tag + ' 种子自洽（缺 _admin_seed_local.txt，本机可补一行口令启用强断言）');
  }
}

sec('C. 两套实现摘要逐位一致（防双源漂移）');
if (indexMod && shellMod) {
  const vec = [['seedVec1', 'c0ffee20260922admin'], ['abc123', 'salt-a'], ['中文口令🔒', '盐-中文']];
  let same = true, bad = '';
  for (const [p, s] of vec) {
    const a = indexMod._pwdHash(p, s), b = shellMod._pwdHash(p, s);
    if (a !== b) { same = false; bad = p + ' → ' + a + ' vs ' + b; break; }
    if (!/^[0-9a-f]{64}$/.test(a)) { same = false; bad = p + ' 非 64 位十六进制：' + a; break; }
  }
  ck('SHA-256 实现一致且输出 64 位十六进制', same, bad);
}

sec('D. 行为：注册 / 登录 / 旧明文升级');
if (indexMod) {
  const m = indexMod;
  // 新注册只存哈希
  const nu = { 工号: '028982', 姓名: '张三' };
  m.setUserPwd(nu, 'abc123');
  ck('新用户只存 盐 + 密码哈希', !('密码' in nu) && !!nu.盐 && !!nu.密码哈希);
  const arr = [nu];
  ck('正确口令通过', m.verifyUserPwd(nu, 'abc123', arr) === true);
  ck('错误口令拒绝', m.verifyUserPwd(nu, 'abc124', arr) === false);
  // 旧明文命中后原地升级
  const legacy = { 工号: '028983', 密码: 'legacy-pw-9x' };
  const arr2 = [legacy];
  ck('旧明文正确口令通过', m.verifyUserPwd(legacy, 'legacy-pw-9x', arr2) === true);
  ck('旧明文已升级（无 密码 字段 + 有哈希）', !('密码' in legacy) && !!legacy.密码哈希);
  ck('升级后仍可登录', m.verifyUserPwd(legacy, 'legacy-pw-9x', arr2) === true);
  ck('升级触发 saveUsers 落盘', m.getSaved() === arr2);
  // 旧明文错误口令不得升级
  const legacy2 = { 工号: '028984', 密码: 'secret' };
  ck('旧明文错误口令拒绝', m.verifyUserPwd(legacy2, 'bad', []) === false);
  ck('拒绝时不改动记录', legacy2.密码 === 'secret' && !legacy2.密码哈希);
  // 安全问题同构（仅 index.html 有）
  if (m.verifyUserAnswer) {
    const u2 = { 工号: '028985', 安全答案: '北京' };
    ck('旧明文答案通过并升级', m.verifyUserAnswer(u2, '北京', [u2]) === true && !('安全答案' in u2) && !!u2.安全答案哈希);
    ck('升级后答案仍可校验', m.verifyUserAnswer(u2, '北京', [u2]) === true);
    ck('错误答案拒绝', m.verifyUserAnswer(u2, '上海', [u2]) === false);
  } else {
    console.log('  [SKIP] index.html 无安全问题答案层');
  }
  const s1 = m._randSalt(), s2 = m._randSalt();
  ck('盐随机且长度 >= 16', s1 !== s2 && s1.length >= 16);
} else {
  ck('index.html 沙箱可加载', false);
}

sec('E. performance.html 备份加密口令不落 sessionStorage（M2）');
{
  const p = rd('performance.html');
  if (!p) ck('performance.html 存在', false);
  else {
    ck('不含 sessionStorage 写口令', !/sessionStorage\s*\.\s*setItem\s*\(\s*this\.SESSION_PWD_KEY/.test(p));
    ck('不含 sessionStorage 读口令', !/sessionStorage\s*\.\s*getItem\s*\(\s*this\.SESSION_PWD_KEY/.test(p));
    ck('改用内存字段 _sessionPwd', /_sessionPwd\s*:/.test(p) && /this\._sessionPwd\s*=/.test(p));
    ck('保留历史 sessionStorage 值清理（迁移）', /sessionStorage\s*\.\s*removeItem\s*\(\s*this\.SESSION_PWD_KEY/.test(p));
    ck('三个方法签名仍对外提供', /setSessionPassword\s*\(/.test(p) && /getSessionPassword\s*\(/.test(p) && /clearSessionPassword\s*\(/.test(p));
  }
}

console.log('\n===== 汇总 =====');
console.log('通过 ' + pass + ' / ' + (pass + fail) + (skip ? ('，跳过 ' + skip + '（缺本地种子文件）') : '') + (fail ? ('，失败 ' + fail) : ''));
console.log(fail ? '凭据哈希治理回归：FAILED' : '凭据哈希治理回归：全绿（明文口令/答案已清零，两套实现同源）');
process.exit(fail ? 1 : 0);
