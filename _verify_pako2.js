// 用 pako 解压 spring-assistant.html 中所有模块，模拟降级路径
const fs = require('fs');
const vm = require('vm');

const pakoSrc = fs.readFileSync('_pako.min.js', 'utf8');
const sandbox = { self: {}, window: {} };
sandbox.self = sandbox; sandbox.window = sandbox;
vm.createContext(sandbox);
vm.runInContext(pakoSrc, sandbox);
const pako = sandbox.pako;

function testFile(file) {
  console.log('\n===== ' + file + ' =====');
  const c = fs.readFileSync(file, 'utf8');
  const m = c.match(/const MODULES = \{([\s\S]*?)\n\};/);
  const re = /(\w+): "([^"]+)"/g;
  let x, fail = 0, total = 0;
  while ((x = re.exec(m[1]))) {
    const name = x[1], b64 = x[2];
    if (!b64.startsWith('H4sI')) continue;
    total++;
    const bytes = Uint8Array.from(Buffer.from(b64, 'base64'));
    try {
      const out = pako.inflate(bytes);
      const html = Buffer.from(out).toString('utf8');
      // 检查是否为合法 HTML（不是乱码）：应含 <html 或 <!DOCTYPE 或含</body>
      const ok = /<\s*(html|!DOCTYPE|body)/i.test(html.slice(0, 300)) && html.length > 500;
      if (!ok) { fail++; console.log('  [' + name + '] ⚠️ 解压内容可疑，前80字符:', html.slice(0, 80).replace(/[^\x20-\x7e]/g, '?')); }
    } catch (e) {
      fail++; console.log('  [' + name + '] ❌ pako解压失败: ' + e.message);
    }
  }
  console.log('结果: ' + (total - fail) + '/' + total + ' 模块解压成功');
  return fail === 0;
}

testFile('spring-assistant.html');
testFile('春秋·广州分队全能助手（4合1）.html');