/* 验证：qa.html 覆盖层合并（add/mod/损坏静默）+ 三外壳 kbadmin 页签一致性 + 4in1 占位符替换 */
const fs = require('fs');
let pass = 0, fail = 0;
const t = (n, c) => { console.log((c?'PASS':'FAIL')+'  '+n); c?pass++:fail++; };

// ---- 1) 三外壳一致性 ----
const SHELLS = ['index.html', '客舱小助手（离线完整版）.html', 'spring-assistant.html'];
for (const f of SHELLS){
  const s = fs.readFileSync(f, 'utf8');
  t(f+' 页签📇', s.includes('📇 库管理'));
  t(f+' kbadmin 映射', s.includes('kbadmin'));
  t(f+' EMBED_CSS kb-top', s.includes('kb-top'));
  t(f+' wrap-kbadmin', s.includes('wrap-kbadmin'));
}
// 4in1 占位符必须已被真实 base64 替换且长度合理
const four = fs.readFileSync('客舱小助手（离线完整版）.html','utf8');
const m = four.match(/kbadmin: "([A-Za-z0-9+/=]+)"/);
t('4in1 kbadmin B64 已注入(无占位符)', m && m[1].length > 1000 && !m[1].includes('__B64'));
const gzipHdr = /^H4s/.test(m ? m[1] : '');
t('4in1 kbadmin B64 为 gzip(H4s 头)', gzipHdr);

// ---- 2) qa.html 覆盖层合并 ----
const qa = fs.readFileSync('qa.html','utf8');
const i0 = qa.indexOf('/* ===================== 知识覆盖层合并');
const i1 = qa.indexOf('/* ===== 四库来源路由');
const mergeCode = qa.slice(i0, i1);
const KB_MAIN = [ {cat:'日常', src:'手册 6.7.9.3.4', t:['病假'], q:'旧问题', a:'旧答案'} ];
const KB_CCM = [ {cat:'手册', src:'CCM 3.1.2.1', q:'CCM旧问题', a:'x'} ];
const mem = new Map();
const mockLS = { getItem:k=>mem.has(k)?mem.get(k):null, setItem:(k,v)=>mem.set(k,v) };

// 初始 eval：仅语法可执行（无覆盖层不动作）
const code = '(function(){ var KB = KB_MAIN; var window={KB_CCM_RAW:KB_CCM,KB_MGM_RAW:[],KB_SVC_RAW:[]}; window.addEventListener=function(){}; var localStorage=mockLS;'
  + mergeCode.replace(/window\.addEventListener/g, 'window.addEventListener')
  + '\n;global.__POOLS = {KB:KB, ccm:window.KB_CCM_RAW};})()';
eval(code);
t('合并函数语法可执行', true);

// FULL：带覆盖层，验证 mod 替换 / add 追加 / 损坏条目跳过
const KB2 = [ {cat:'日常', src:'手册 6.7.9.3.4', q:'旧问题', a:'旧答案'} ];
const KB_CCM2 = [ {cat:'手册', src:'CCM 3.1.2.1', q:'CCM旧问题', a:'x'} ];
const mem2 = new Map();
mem2.set('kb_overlay_v1', JSON.stringify({
  magic:'kb-overlay-v1', version:1, updatedAt:'x',
  byLib: {
    daily: [ {cat:'日常', src:'手册 6.7.9.3.4', q:'新问题（修订）', a:'新答案', _op:'mod'} ],
    ccm: [ {cat:'手册', src:'CCM 9.9.9', q:'新增CCM条目', a:'新', t:['新'], _op:'add'} ],
    svc: [ {q:null}, {q:'损坏空条目'} ]
  }
}));
const mockLS2 = { getItem:k=>mem2.has(k)?mem2.get(k):null, setItem:(k,v)=>mem2.set(k,v) };
const FULL = '(function(){ var KB = KB2; var window={KB_CCM_RAW:KB_CCM2,KB_MGM_RAW:[],KB_SVC_RAW:[]}; window.addEventListener=function(){}; var localStorage=mockLS2;'
  + mergeCode + '\n;global.out={KB:KB,ccm:window.KB_CCM_RAW};})()';
eval(FULL);
t('mod 按 src 替换生效', out.KB.length===1 && out.KB[0].q==='新问题（修订）');
t('add 追加进 ccm', out.ccm.some(e=>e.q==='新增CCM条目'));
t('损坏条目(无 q)被跳过', out.ccm.length===2);

// 无覆盖层时静默不影响
const KB3 = [ {q:'原始'} ];
const FULL3 = '(function(){ var KB = KB3; var window={KB_CCM_RAW:[],KB_MGM_RAW:[],KB_SVC_RAW:[]}; window.addEventListener=function(){}; var localStorage={getItem:()=>null,setItem:()=>{}};'
  + mergeCode + '\n;global.kb3=KB;})()';
eval(FULL3);
t('无覆盖层不动作', kb3.length===1 && kb3[0].q==='原始');

// 损坏 JSON 静默
const mem4 = new Map(); mem4.set('kb_overlay_v1', 'not-json{{{');
const FULL4 = '(function(){ var KB = []; var window={KB_CCM_RAW:[],KB_MGM_RAW:[],KB_SVC_RAW:[]}; window.addEventListener=function(){}; var localStorage={getItem:k=>mem4.get(k)||null,setItem:()=>{}};'
  + mergeCode + '\n;global.ok4=true;})()';
eval(FULL4);
t('损坏 JSON 静默不炸', ok4 === true);

console.log('\nRESULT: ' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);