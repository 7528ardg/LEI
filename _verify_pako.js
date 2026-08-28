// 验证 pako.min.js 在浏览器式环境中解压模块数据
const fs = require('fs');
const vm = require('vm');

// 1. 读取并执行 pako（UMD：挂到我们提供的全局对象上）
const pakoSrc = fs.readFileSync('_pako.min.js', 'utf8');
const sandbox = { self: {}, window: {} };
sandbox.self = sandbox; sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(pakoSrc, sandbox);
const pako = sandbox.pako || (sandbox.window && sandbox.window.pako);
if (!pako) { console.log('pako 未挂载, keys:', Object.keys(sandbox).slice(0, 10)); process.exit(1); }
console.log('pako 加载成功, inflate:', typeof pako.inflate, 'ungzip:', typeof pako.ungzip);

// 2. 用 pako.ungzip 解压 spring-assistant 中的 manual 模块
const bc = fs.readFileSync('spring-assistant.html', 'utf8');
const m = bc.match(/manual: "([^"]+)"/);
const b64 = m[1];
const bytes = Uint8Array.from(Buffer.from(b64, 'base64'));
const out = pako.ungzip(bytes);
const html = Buffer.from(out).toString('utf8');
console.log('pako 解压 manual 成功:', html.length, 'bytes');
console.log('HTML 开头:', html.slice(0, 50).replace(/\n/g, ' '));
console.log('包含关键内容:', html.includes('手册奖惩') || html.includes('第一章'));