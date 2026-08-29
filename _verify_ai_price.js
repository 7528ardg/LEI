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
   [{ platform: '京东', store: '', size: '50ml', price: 900, note: 'AI估算' }]);
eq('带前后缀文本', api.parseAiPriceJson('以下是价格：\n[{"platform":"日上","size":"100ml","price":880,"note":"免税价"}]\n请查收。'),
   [{ platform: '日上', store: '', size: '100ml', price: 880, note: '免税价' }]);
eq('空数组', api.parseAiPriceJson('[]'), []);
eq('空字符串', api.parseAiPriceJson(''), []);
eq('非法 JSON', api.parseAiPriceJson('这是没有数组的文本'), []);
eq('过滤 price=0/空行', api.parseAiPriceJson('[{"platform":"天猫","size":"30ml","price":0},{"price":100}]'), []);

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
ok('updateTime 带 AI更新', /AI更新/.test(state.competitorPriceOverrides['comp001'].prices[0].updateTime));
ok('原预设数据未被污染', competitorData[0].prices.length === 1 && competitorData[0].prices[0].price === 665);

console.log('[4] applyCompetitorPrices（自定义竞品 -> 直接更新）');
state.competitorProducts = [{ id: 'custom1', name: '某自定义竞品', prices: [] }];
api.applyCompetitorPrices(state.competitorProducts[0], [{ platform: '京东', size: '50ml', price: 700 }]);
eq('自定义竞品 prices 更新', state.competitorProducts[0].prices.length, 1);
ok('自定义竞品不进覆盖层', !state.competitorPriceOverrides['custom1']);

console.log('[5] aiFetchPrices 走 SpringAI.chatLLM 并解析');
let lastPrompt = '';
SpringAI.chatLLM = async (msgs, opts) => { lastPrompt = msgs[1].content; return '```json\n[{"platform":"天猫","size":"30ml","price":665,"note":"日常价"}]\n```'; };
(async () => {
  const c0 = { id: 'comp002', brand: '兰蔻', name: '小黑瓶', category: '精华', prices: [{ platform: '天猫', size: '30ml', price: 700 }] };
  const res = await api.aiFetchPrices(c0);
  eq('aiFetchPrices 解析结果', res, [{ platform: '天猫', store: '', size: '30ml', price: 665, note: '日常价' }]);
  ok('prompt 含产品信息', lastPrompt.indexOf('兰蔻 小黑瓶') !== -1);

  console.log('\nPASS ' + pass + ' / ' + (pass + fail));
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.log('ASYNC_ERR', e); process.exit(1); });
