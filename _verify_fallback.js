// 端到端验证：从构建产物中提取内嵌 pako + _b64ToHtml，在屏蔽 DecompressionStream 环境下验证降级
const fs = require('fs');
const vm = require('vm');

const file = '春秋·广州分队全能助手（4合1）.html';
const c = fs.readFileSync(file, 'utf8');

// 1. 提取内嵌 pako 源码（完整 UMD 块，到 _b64ToHtml 函数定义之前）
const pakoStart = c.indexOf('/*! pako 2.1.0');
const fnMarker = 'async function _b64ToHtml(b64){';
const pakoEnd = c.indexOf(fnMarker, pakoStart);
if (pakoStart === -1 || pakoEnd === -1) { console.log('未找到内嵌 pako'); process.exit(1); }
const pakoSrc = c.slice(pakoStart, pakoEnd);

// 2. 提取 _b64ToHtml 函数体（到下一个 "/* ===================== 模块切换" 前）
const fnStart = pakoEnd;
const nextSeg = c.indexOf('/* ===================== 模块切换', fnStart);
const b64ToHtmlSrc = c.slice(fnStart, nextSeg);

// 3. 构造沙箱环境：浏览器全局，但 DecompressionStream 被屏蔽（模拟旧 Safari）
const sandbox = {};
sandbox.window = sandbox;
Object.assign(sandbox, {
  self: sandbox,
  atob: (s) => Buffer.from(s, 'base64').toString('binary'),
  TextDecoder: function(enc){ 
    const encName = (enc || 'utf-8').toLowerCase();
    return { decode: (u8) => Buffer.from(u8).toString(encName) };
  },
  TextEncoder: function(){ return { encode: (s) => Buffer.from(s, 'utf8') }; },
  Uint8Array: Uint8Array,
  Blob: function(parts){ return { stream: () => { throw new Error('no blob stream'); } }; },
  Response: function(){ throw new Error('no Response'); },
  DecompressionStream: undefined,  // ← 关键：屏蔽原生解压
  console: console,
});
vm.createContext(sandbox);

// 4. 执行 pako（UMD 挂到 window.pako）
vm.runInContext(pakoSrc, sandbox);
console.log('pako 在沙箱中挂载: ', typeof sandbox.pako !== 'undefined' || typeof sandbox.window.pako !== 'undefined');
console.log('sandbox.pako:', typeof sandbox.pako);
console.log('sandbox.window.pako:', typeof sandbox.window.pako);
console.log('window 属性:', Object.keys(sandbox.window).filter(k => k.includes('pako') || k.includes('inflate')).join(',') || '(没有pako相关)');
console.log('顶层属性:', Object.keys(sandbox).filter(k => k.includes('pako')).join(',') || '(没有)');

// 5. 分析内嵌 pako 挂载到哪个全局：跑 UMD 后检查
let pakoGlobal = null;
for (const k of ['pako']) { if (sandbox[k]) pakoGlobal = sandbox[k]; }
console.log('pako 全局可访问: ', !!pakoGlobal, pakoGlobal ? Object.keys(pakoGlobal).filter(k => k.includes('inflate')).join(',') : '');

// 5. 将 _b64ToBytes 和 _b64ToHtml 一起注入沙箱执行
const bytesFn = c.slice(c.indexOf('function _b64ToBytes(b64){'), c.indexOf('async function _b64ToHtml(b64){'));
console.log('b64ToHtmlSrc 尾部200字符:', JSON.stringify(b64ToHtmlSrc.slice(-200)));
vm.runInContext(bytesFn + '\n' + b64ToHtmlSrc, sandbox);

// 7. 取一个模块 base64 实测
const m = c.match(/const MODULES = \{([\s\S]*?)\n\};/);
const re = /(\w+): "([^"]+)"/g;
let x = re.exec(m[1]); // qa
const b64 = x[2];

(async () => {
  // 最终验证：屏蔽 DecompressionStream 时 _b64ToHtml 走 pako 降级且解码正确
  try {
    const dbg4 = vm.runInContext(`(async function(){
      const b64 = ` + JSON.stringify(b64) + `;
      try {
        const h = await _b64ToHtml(b64);
        console.log('dbg4: ✅ 降级解压成功, len=', h.length, ', html头=', h.slice(0,40).replace(/\\n/g,' '));
        return h;
      } catch (e) { console.log('dbg4: ❌ 失败:', String(e && e.message || e)); return null; }
    })()`, sandbox);
    const h = await dbg4;
    console.log('降级路径结果:', h ? 'PASS（无 DecompressionStream 也能正常解压）' : 'FAIL');
  } catch (e) { console.log('dbg4 失败:', e.message); }
})();