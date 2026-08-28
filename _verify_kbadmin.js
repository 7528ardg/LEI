/* kb-admin.html 核心逻辑功能测试：mock DOM/localStorage，eval 生成产物逻辑脚本 + 断言在同一作用域 */
const fs = require('fs');
const html = fs.readFileSync('kb-admin.html', 'utf8');
// 定位逻辑脚本：以 'use strict' 锚点向前找最近的 <script>（避免注释里的 <script> 字样干扰 lastIndexOf）
const a = html.indexOf("'use strict'");
if (a < 0) { console.log('LOGIC_SCRIPT_NOT_FOUND'); process.exit(1); }
const i0 = html.lastIndexOf('<script>', a);
const j0 = html.indexOf('>', i0) + 1;
const i1 = html.indexOf('</script>', i0);
const logic = html.slice(j0, i1).replace(/^'use strict';\s*/, '');

// ---- mock 浏览器环境（在 eval 作用域可见）----
function mkEl(){
  const el = {};
  let _h = '';
  Object.defineProperty(el, 'innerHTML', { get(){ return _h; }, set(v){ _h = String(v); el.textContent = _h.replace(/<[^>]*>/g,''); } });
  el.textContent = ''; el.className = ''; el.value = ''; el.style = {}; el.dataset = {};
  el.addEventListener = function(){}; el.appendChild = function(){}; el.remove = function(){};
  el.classList = { add(){}, remove(){}, toggle(){} }; el.setAttribute = function(){};
  return el;
}
const els = {};
global.document = {
  getElementById(id){ if(!els[id]) els[id]=mkEl(); return els[id]; },
  querySelectorAll(){ return []; },
  createElement(){ return mkEl(); },
  createTextNode(){ return {textContent:''}; }
};
const store = new Map();
global.localStorage = {
  get length(){ return store.size; },
  key(i){ return [...store.keys()][i]; },
  getItem(k){ return store.has(k) ? store.get(k) : null; },
  setItem(k,v){ store.set(k, String(v)); },
  removeItem(k){ store.delete(k); }
};
global.window = {};
global.window.pdfjsLib = { GlobalWorkerOptions: {} };
global.URL = { createObjectURL: ()=>'blob:mock', revokeObjectURL(){} };
global.Blob = class { constructor(parts){ this.parts=parts; } };
global.navigator = { online: true };
global.toast = function(m, err){};

const harness = `
let pass = 0, fail = 0;
const t = (name, cond, extra) => { console.log((cond?'PASS':'FAIL')+'  '+name + (extra?' : '+extra:'')); cond?pass++:fail++; };

(async () => {
  // 1) BASE_LIBS 数量与 qa 一致
  t('BASE_LIBS daily=32', BASE_LIBS.daily.length === 32, 'got '+BASE_LIBS.daily.length);
  t('BASE_LIBS ccm=256', BASE_LIBS.ccm.length === 256, 'got '+BASE_LIBS.ccm.length);
  t('BASE_LIBS mgm=135', BASE_LIBS.mgm.length === 135, 'got '+BASE_LIBS.mgm.length);
  t('BASE_LIBS svc=66', BASE_LIBS.svc.length === 66, 'got '+BASE_LIBS.svc.length);

  // 2) 章节解析
  S.pdfText = [
    '===PAGE 1===','客舱乘务员手册（演示）',
    '3.1 机组成员职责与资格','3.1.1 适用范围','本手册适用于所有在册客舱乘务员。',
    '3.1.2 主要职责','客舱乘务员负责客舱安全、应急撤离与旅客服务。',
    '3.2 值勤与疲劳管理','3.2.1 签到时间','签到时间要求航前至少90分钟。',
    '3.3 客舱安全','3.3.1 安全带信号灯','起飞与着陆阶段应接通安全带信号灯。',
    '4.1 新增主题（演示）','客舱餐饮服务的新流程与话术要求。',
    '4.2 又一新增章节（演示）','机上儿童旅客服务要点。',
    '12.1 全新章节（演示二）','客舱餐饮服务全流程新标准。'
  ].join('\\n');
  parseSections();
  t('章节识别数 >= 7', S.sections.length >= 7, 'got '+S.sections.length);
  const nums = S.sections.map(s=>s.num);
  t('含 3.1.2 章节', nums.includes('3.1.2'), 'got '+nums.join(','));
  t('含新增章节 4.1', nums.includes('4.1'));
  t('含全新章节 12.1', nums.includes('12.1'));

  // 3) 覆盖率：12.1 与四库现有一切 src 无前缀重叠 → 必为新增
  computeCoverage();
  const cc = S.cover.ccm;
  t('12.1 判定为新增（ccm）', force(cc).news.some(s=>s.num==='12.1'), 'news='+ (cc&&cc.news.map(s=>s.num).join(',')));
  t('ccm 有已覆盖', force(cc).covered.length >= 1, 'covered='+ (cc&&cc.covered.length));

  // 4) 差异审核入库（覆盖层）
  S.diffs = [
    { lib:'ccm', num:'4.1', title:'新增主题演示', text:'餐饮新流程', kind:'new', q:'新增章节的问题？', a:'新流程答案', t:'餐饮,新流程', cat:'饮食服务', checked:true, aiState:0, entry:null },
    { lib:'ccm', num:'3.1.2', title:'主要职责', text:'x', kind:'review', entry:{ src:'CCM 3.1.2', q:'旧问题', a:'旧答案', t:['旧'] }, q:'旧问题改', a:'新答案', t:'新标签', checked:true, aiState:0 }
  ];
  confirmAll();
  const ov = JSON.parse(localStorage.getItem('kb_overlay_v1') || 'null');
  t('覆盖层写入', !!ov && ov.magic==='kb-overlay-v1');
  t('add 条目写入 ccm', !!ov && ov.byLib.ccm.some(e=>e._op==='add' && e.src==='CCM 4.1'));
  t('mod 条目带 _op=mod', !!ov && ov.byLib.ccm.some(e=>e._op==='mod' && e.src==='CCM 3.1.2'));

  // 5) 体检
  runHealth();
  t('健康度数据生成', !!healthData && healthData.totalEntries > 0, 'entries='+ (healthData&&healthData.totalEntries));
  t('弱覆盖标注检出', healthData.weakRows.length > 0, 'weak='+healthData.weakRows.length);

  // 6) AI 降级：fetch 抛错 → aiGen 标记失败不崩溃
  global.fetch = async () => { throw new Error('net'); };
  const diff1 = { lib:'ccm', num:'5.1', title:'测试章', text:'t', kind:'new', q:'', a:'', t:'', checked:false, aiState:0 };
  S.diffs = [diff1];
  try{ await aiGen(0); t('AI 失败降级（无崩溃）', true); }catch(e){ t('AI 失败降级（无崩溃）', false, e.message); }

  console.log('\\nRESULT: ' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail ? 1 : 0);
})();
function force(x){ return x || {}; }
`;
eval(logic + '\n' + harness);