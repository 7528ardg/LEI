// 竞品分析 AI 更新价格功能 - 单元验证
// 从 beauty.html 抽取 AI 价格函数块，注入最小桩环境后逐项断言
const fs = require('fs');
const path = require('path');

const src = fs.readFileSync(path.join(__dirname, 'beauty.html'), 'utf-8');
const full = src;

// 定位 AI 价格函数块（起始注释 -> copyText 定义前）
const startMark = '// ===== 竞品分析 - AI 更新价格';
const endMark = 'const copyText = (text) => {';
const sIdx = full.indexOf(startMark);
const eIdx = full.indexOf(endMark);
if (sIdx === -1 || eIdx === -1 || eIdx <= sIdx) { console.log('FAIL block not found'); process.exit(1); }
const block = full.slice(sIdx, eIdx);

// 最小桩环境（挂在 globalThis 供测试断言引用）
const stubs = `
globalThis.state = { competitorPriceOverrides: {}, competitorProducts: [] };
globalThis.competitorData = [
  { id: 'comp001', name: '雅诗兰黛小棕瓶精华第七代', brand: '雅诗兰黛', category: '精华', prices: [ { platform: '天猫旗舰店', store: '官方', size: '30ml', price: 665, note: '日常价' } ] }
];
globalThis.saveState = () => {};
globalThis.render = () => {};
globalThis.showAlert = () => {};
globalThis.showConfirm = (t, msg, cb) => { if (cb) cb(true); };
globalThis.editCompetitor = () => {};
globalThis.SpringAI = { isEnabled: () => true, chatLLM: async () => '', openSettings: () => {} };
`;
const code = stubs + '\n' + block;

let api;
try {
  api = new Function('return (function(){' + code + '; return { parseAiPriceJson: parseAiPriceJson, getCompetitorPrices: getCompetitorPrices, applyCompetitorPrices: applyCompetitorPrices, aiFetchPrices: aiFetchPrices }; })()')();
} catch (e) {
  console.log('EVAL_ERR', e.message);
  process.exit(1);
}

const state = globalThis.state, competitorData = globalThis.competitorData, SpringAI = globalThis.SpringAI;

let pass = 0, fail = 0;
const eq = (name, got, want) => {
  const g = JSON.stringify(got), w = JSON.stringify(want);
  if (g === w) { pass++; console.log('  ok  ' + name); }
  else { fail++; console.log('  FAIL ' + name + '\n     got  ' + g + '\n     want ' + w); }
};
const ok = (name, cond) => {
  if (cond) { pass++; console.log('  ok  ' + name); }
  else { fail++; console.log('  FAIL ' + name); }
};

console.log('[1] parseAiPriceJson');
eq('纯 JSON', api.parseAiPriceJson('[{"platform":"天猫","store":"A","size":"30ml","price":665,"note":"日常价"}]'),
   [{ platform: '天猫', store: 'A', size: '30ml', price: 665, note: '日常价' }]);
eq('markdown 代码块', api.parseAiPriceJson('```json\n[{"platform":"京东","size":"50ml","price":900}]\n```'),
   [{ platform: '京东', store: '', size: '50ml', price: 900, note: '联网参考价' }]);
eq('带前后缀文本', api.parseAiPriceJson('以下是价格：\n[{"platform":"日上","size":"100ml","price":880,"note":"免税价"}]\n请查收。'),
   [{ platform: '日上', store: '', size: '100ml', price: 880, note: '免税价' }]);
eq('空数组', api.parseAiPriceJson('[]'), []);
eq('空字符串', api.parseAiPriceJson(''), []);
eq('非法 JSON', api.parseAiPriceJson('这是没有数组的文本'), []);
eq('过滤 price=0/空行', api.parseAiPriceJson('[{"platform":"天猫","size":"30ml","price":0},{"price":100}]'), []);
eq('单对象JSON自动包数组', api.parseAiPriceJson('{"platform":"日上","size":"50ml","price":800}'), [{ platform: '日上', store: '', size: '50ml', price: 800, note: '联网参考价' }]);

console.log('[2] getCompetitorPrices');
eq('无覆盖取原数据', api.getCompetitorPrices(competitorData[0]), competitorData[0].prices);
state.competitorPriceOverrides['comp001'] = { prices: [{ platform: '京东', size: '50ml', price: 800 }], updatedAt: '2026年8月30日' };
eq('有覆盖取覆盖', api.getCompetitorPrices(competitorData[0]), [{ platform: '京东', size: '50ml', price: 800 }]);
state.competitorPriceOverrides = {};

console.log('[3] applyCompetitorPrices（预设竞品 -> 覆盖层，可恢复默认）');
api.applyCompetitorPrices(competitorData[0], [
  { platform: '天猫', store: '官方', size: '50ml', price: 920, note: '日常价' },
  { platform: '日上', size: '100ml', price: 860, note: '免税价' }
]);
eq('覆盖层写入', state.competitorPriceOverrides['comp001'].prices.map(p => [p.platform, p.price, p.note]),
   [['天猫', 920, '日常价'], ['日上', 860, '免税价']]);
ok('updateTime 带 联网更新', /联网更新/.test(state.competitorPriceOverrides['comp001'].prices[0].updateTime));
ok('原预设数据未被污染', competitorData[0].prices.length === 1 && competitorData[0].prices[0].price === 665);

console.log('[4] applyCompetitorPrices（自定义竞品 -> 直接更新）');
state.competitorProducts = [{ id: 'custom1', name: '某自定义竞品', prices: [] }];
api.applyCompetitorPrices(state.competitorProducts[0], [{ platform: '京东', size: '50ml', price: 700 }]);
eq('自定义竞品 prices 更新', state.competitorProducts[0].prices.length, 1);
ok('自定义竞品不进覆盖层', !state.competitorPriceOverrides['custom1']);

console.log('[5] aiFetchPrices：Firecrawl 免费通道（不消耗计费工具）');
let lastPrompt = '', lastOpts = null, lastFetchUrl = '';
globalThis.fetch = async (url, o) => { lastFetchUrl = String(url); return { ok:true, json: async () => ({ success:true, data:{ web:[
  { title:'兰蔻小黑瓶 30ml 价格解析', description:'淘宝 · 原价1100.00元，到手价 980 元', url:'https://taobao.example/x' },
  { title:'兰蔻官方旗舰店 小黑瓶精华肌底液', description:'京东自营 30ml 售价 1080 元', url:'https://jd.example/y' }
]}, creditsUsed:2 }) }; };
SpringAI.chatLLM = async (msgs, opts) => { lastOpts = opts; lastPrompt = msgs[1].content; return '```json\n[{"platform":"淘宝","size":"30ml","price":980,"note":"活动价"},{"platform":"京东","size":"30ml","price":1080,"note":"日常价"}]\n```'; };
(async () => {
  const c0 = { id: 'comp002', brand: '兰蔻', name: '小黑瓶', category: '精华', prices: [{ platform: '天猫', size: '30ml', price: 700 }] };
  const res = await api.aiFetchPrices(c0);
  eq('Firecrawl 通道解析结果', res, [
    { platform: '淘宝', store: '', size: '30ml', price: 980, note: '活动价' },
    { platform: '京东', store: '', size: '30ml', price: 1080, note: '日常价' }
  ]);
  ok('调用 Firecrawl /v2/search', lastFetchUrl.indexOf('api.firecrawl.dev/v2/search') !== -1);
  ok('prompt 含搜索结果真实价格', lastPrompt.indexOf('原价1100.00元') !== -1 || lastPrompt.indexOf('1080') !== -1);
  ok('免费通道不传 tools（不消耗计费）', !(lastOpts && lastOpts.tools && lastOpts.tools.length));

    console.log('[6] aiFetchPrices：Firecrawl 失败自动回退 Tavily Keyless（免费备份源）');
  let fallbackHeader = '', fallbackUrl = '', fallbackBody = '';
  globalThis.fetch = async (url, opt) => {
    if (String(url).indexOf('firecrawl') !== -1) throw new TypeError('Failed to fetch');
    fallbackUrl = String(url); fallbackHeader = String((opt && opt.headers && opt.headers['X-Tavily-Access-Mode']) || ''); fallbackBody = String((opt && opt.body) || '');
    return { ok:true, json: async () => ({ results:[{ title:'日上免税 雅诗兰黛小棕瓶', content:'100ml 售价 860 元', url:'https://dfs.example/a' }] }) };
  };
  SpringAI.chatLLM = async (msgs, opts) => { lastOpts = opts; return '[{"platform":"日上","size":"100ml","price":860,"note":"免税价"}]'; };
  const res2 = await api.aiFetchPrices({ id: 'comp005', brand: '雅诗兰黛', name: '小棕瓶', prices: [] });
  eq('回退 Tavily 解析结果', res2, [{ platform: '日上', store: '', size: '100ml', price: 860, note: '免税价' }]);
  ok('回退调用 Tavily /search', fallbackUrl.indexOf('api.tavily.com/search') !== -1);
  ok('Tavily Keyless 头为 keyless', fallbackHeader === 'keyless');
  ok('回退通道不传计费 tools', !(lastOpts && lastOpts.tools && lastOpts.tools.length));

  console.log('[7] aiFetchPrices：Firecrawl 空结果 + 兜底也为空 -> 抛错不编造');
  globalThis.fetch = async () => ({ ok:true, json: async () => ({ success:true, data:{ web: [] } }) });
  SpringAI.chatLLM = async () => '';
  let errMsg = '';
  try { await api.aiFetchPrices({ id: 'comp006', brand: '某', name: '未知款', prices: [] }); }
  catch(e) { errMsg = String((e && e.message) || e); }
  ok('空结果抛免费通道不可用', errMsg.indexOf('免费搜索通道暂不可用') !== -1);

  globalThis.fetch = undefined;
  console.log('\nPASS ' + pass + ' / ' + (pass + fail));
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('ASYNC_ERR', e); process.exit(1); });
