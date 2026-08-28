const fs = require('fs');
const c = fs.readFileSync('spring-assistant.html', 'utf8');
const m = c.match(/const MODULES = \{([\s\S]*?)\n\};/);
const names = [...m[1].matchAll(/(\w+): "H4sI/g)].map(x => x[1]);
console.log('模块:', names.join(','));
console.log('pako注入:', c.includes('pako 2.1.0'));
console.log('原生DecompressionStream路径保留:', c.includes("typeof DecompressionStream !== 'undefined'"));
console.log('fallback错误提示:', c.includes('请升级浏览器'));
console.log('EMBED_CSS有risk:', c.includes("risk: '.topbar"));