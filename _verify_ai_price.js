// 竞品分析「价格更新」· AI 混合模式守护（2026-09-19 晚重写，对齐 __AI_HYBRID_20260919__）
// 口径沿革：
//   · v1（本地模式守护）：断言 beauty.html 零联网、isEnabled 恒 false —— 已过期。
//   · v2（本版）：用户 2026-09-19 晚指令「beauty 改 AI 混合模式」——免Key搜索（Firecrawl/Tavily）
//     + 本地解析为默认兜底，GLM-4-Flash 为可选增强（Key 运行时粘贴存 localStorage，源码零内置密钥）。
//     禁用清单口径与 _check_needles BAN_RX / _apply_nokey_all_mods / _verify_nokey_all 三处同步：
//     放行 bigmodel/tavily/firecrawl/spring_ai_cfg/运行时 Bearer；仍禁内置 Key/glm-4.7/siliconflow/Gist。
// 做法：从 beauty.html 抽取价格函数块，注入最小桩环境后逐项断言（桩 fetch 断网，验证优雅降级与域名放行）。
const fs = require('fs');
const path = require('path');

const SRC = fs.readFileSync(path.join(__dirname, 'beauty.html'), 'utf-8');

let pass = 0, fail = 0;
const ok = (n, c, extra) => { if (c) { pass++; console.log('  \u2713 ' + n); } else { fail++; console.log('  \u2717 ' + n + (extra ? '  :: ' + extra : '')); } };

console.log('=== 竞品价格更新 · AI 混合模式守护 ===');

/* ---------- 1. 源码级：混合模式在位 + 内置密钥零容忍 ---------- */
console.log('\n[1] 源码守护（混合模式口径）');
ok('混合模式标记 __AI_HYBRID_20260919__ 在位', SRC.indexOf('__AI_HYBRID_20260919__') >= 0, '缺失（被本地模式掏空？）');
const ALLOW = [
  ['api.firecrawl.dev', 'Firecrawl 免Key 搜索源'],
  ['api.tavily.com', 'Tavily 免Key 搜索源'],
  ['open.bigmodel.cn', '智谱 GLM-4-Flash 可选增强'],
];
for (const [kw, name] of ALLOW) {
  const n = SRC.split(kw).length - 1;
  ok('beauty.html 保留 ' + name, n > 0, '出现 0 次（混合模式被误掏空）');
}
const BAN = [
  ['4986b927', '内置共享 Key'],
  ['BUILTIN_AI_KEY', 'BUILTIN_AI_KEY 常量'],
  ['glm-4.7', 'glm-4.7 引用'],
  ['glm47', 'glm47 引用'],
  ['api.siliconflow.cn', '硅基流动端点'],
  ['api.github.com', 'Gist 云同步'],
];
for (const [kw, name] of BAN) {
  const n = SRC.split(kw).length - 1;
  ok('beauty.html 不含 ' + name, n === 0, '出现 ' + n + ' 次');
}
ok('isEnabled 动态判定（keyless 或用户 Key）在位', /p\.keyless\s*\|\|/.test(SRC) && /\.length\s*>=\s*8/.test(SRC));
ok('Tavily 免Key 头在位（X-Tavily-Access-Mode: keyless）', SRC.indexOf('X-Tavily-Access-Mode') >= 0);
{
  const i = SRC.indexOf('api.firecrawl.dev');
  const win = i >= 0 ? SRC.slice(i, i + 600) : '';
  ok('Firecrawl 请求不带 Authorization（免Key）', i >= 0 && win.indexOf('Authorization') === -1);
}

/* ---------- 2. 抽取价格函数块，注入桩环境 ---------- */
const startMark = '// ===== 竞品分析 - AI 更新价格';
const endMark = 'const copyText = (text) => {';
const sIdx = SRC.indexOf(startMark);
const eIdx = SRC.indexOf(endMark);
if (sIdx === -1 || eIdx === -1 || eIdx <= sIdx) { console.log('FAIL block not found'); process.exit(1); }
const block = SRC.slice(sIdx, eIdx);

/* 最小 document 桩：进度弹窗（showAiLoading/hideAiLoading）会触达 DOM */
const mkEl = () => ({ style: {}, appendChild() {}, remove() {}, addEventListener() {},
  querySelector() { return {}; }, querySelectorAll() { return []; }, closest() { return null; },
  classList: { contains() { return false; } } });
globalThis.document = {
  getElementById: () => null,
  createElement: () => { globalThis.__docCreates = (globalThis.__docCreates || 0) + 1; return mkEl(); },
  body: { appendChild() {} },
};

const stubs = `
globalThis.state = { competitorPriceOverrides: {}, competitorProducts: [],
  competitorCategoryFilter: 'all', competitorBrandFilter: 'all', competitorSearchQuery: '' };
globalThis.competitorData = [
  { id: 'comp001', name: '雅诗兰黛小棕瓶精华第七代', brand: '雅诗兰黛', category: '精华', prices: [ { platform: '天猫旗舰店', store: '官方', size: '30ml', price: 665, note: '日常价' } ] },
  { id: 'comp002', name: 'SK-II 神仙水', brand: 'SK-II', category: '精华水', prices: [ { platform: '专柜', store: '官方', size: '230ml', price: 1450, note: '日常价' } ] }
];
globalThis.saveState = () => {};
globalThis.render = () => {};
globalThis.__alerts = [];
globalThis.__confirms = [];
globalThis.__editCalled = false;
globalThis.showAlert = (m) => { globalThis.__alerts.push(String(m)); };
globalThis.showConfirm = (t, msg, cb) => { globalThis.__confirms.push(String(t) + '|' + String(msg)); if (globalThis.__confirmAuto) cb(true); };
globalThis.editCompetitor = () => { globalThis.__editCalled = true; };
globalThis.SpringAI = { isEnabled: () => false, chatLLM: async () => { throw new Error('桩：不接外部 AI'); }, openSettings: () => {} };
/* 桩 fetch = 断网：记录被请求的 URL 后抛错，用于验证「只碰放行域名」与优雅降级 */
globalThis.__fetchHosts = [];
globalThis.fetch = async (url) => { globalThis.__fetchHosts.push(String(url)); throw new Error('桩：断网'); };
`;
const code = stubs + '\n' + block
  + '\n;globalThis.__api = { aiFetchPrices, aiUpdateCompetitorPrice, aiUpdateAllCompetitorPrices, searchPriceText };';
try {
  new Function(code)();
} catch (e) {
  console.log('FAIL 块加载失败：' + e.message);
  process.exit(1);
}
const api = globalThis.__api;
const HOST_OK = /api\.firecrawl\.dev|api\.tavily\.com/;

(async () => {
  /* ---------- 3. 免Key 搜索链路：断网下优雅失败、只碰放行域名 ---------- */
  console.log('\n[3] 免Key 搜索链路（桩断网）');
  globalThis.__fetchHosts = [];
  let threw = null;
  try {
    await api.aiFetchPrices({ id: 'comp003', brand: '兰蔻', name: '小黑瓶', prices: [{ platform: '天猫', size: '30ml', price: 700 }] });
  } catch (e) { threw = String((e && e.message) || e); }
  ok('aiFetchPrices 搜索全失败时优雅报错（不静默、不编造）', !!threw && /免费搜索渠道|暂不可用/.test(threw), threw || '未抛错');
  ok('失败前确实尝试过免Key 源（非静默跳过）', globalThis.__fetchHosts.length > 0, 'fetch 调用 0 次');
  ok('网络请求全部指向放行域名（Firecrawl/Tavily）', globalThis.__fetchHosts.every(u => HOST_OK.test(u)),
    '越界域名: ' + globalThis.__fetchHosts.filter(u => !HOST_OK.test(u)).join(', '));
  ok('单次检索只覆盖两个免Key 源', new Set(globalThis.__fetchHosts.map(u => u.replace(/^https?:\/\//, '').split('/')[0])).size === 2);
  ok('searchPriceText 双词尾合并检索在位', /QUERIES\s*=\s*\[/.test(block) && block.split('QUERIES = [').length === 2);

  /* ---------- 4. 单款入口：失败 → 引导 AI 设置/手动编辑，绝不写脏数据 ---------- */
  console.log('\n[4] 单款入口（搜索失败路径）');
  globalThis.__confirms = [];
  globalThis.__fetchHosts = [];
  globalThis.__confirmAuto = false;
  globalThis.__docCreates = 0;
  await api.aiUpdateCompetitorPrice('comp001');
  const joined = globalThis.__confirms.join(' ');
  ok('单款入口先出进度弹窗', (globalThis.__docCreates || 0) >= 1);
  ok('失败后引导「AI 更新失败」并提示 AI 设置/手动编辑', /AI 更新失败/.test(joined) && /(AI 设置|手动编辑)/.test(joined), joined.slice(0, 90));
  ok('失败路径不写入价格覆盖层', Object.keys(globalThis.state.competitorPriceOverrides).length === 0);
  ok('失败路径网络请求仍全部放行域名', globalThis.__fetchHosts.every(u => HOST_OK.test(u)),
    '越界域名: ' + globalThis.__fetchHosts.filter(u => !HOST_OK.test(u)).join(', '));

  /* ---------- 5. 批量入口：确认后逐款尝试，全失败有汇总、不中断 ---------- */
  console.log('\n[5] 批量入口（搜索失败路径）');
  globalThis.__confirms = [];
  globalThis.__alerts = [];
  globalThis.__fetchHosts = [];
  globalThis.__confirmAuto = true;
  await api.aiUpdateAllCompetitorPrices();
  /* 批量确认是回调式：等 cb(true) 里的逐款异步循环跑完再断言 */
  await new Promise(r => setTimeout(r, 80));
  ok('批量入口先弹确认（含停止说明）', /批量/.test(globalThis.__confirms.join(' ')), globalThis.__confirms.join(' ').slice(0, 90));
  ok('全部失败有汇总提示（成功 0 款）', /批量更新完成/.test(globalThis.__alerts.join(' ')) && /成功 0 款/.test(globalThis.__alerts.join(' ')), globalThis.__alerts.join(' ').slice(0, 90));
  ok('批量路径网络请求全部放行域名', globalThis.__fetchHosts.length > 0 && globalThis.__fetchHosts.every(u => HOST_OK.test(u)),
    '越界域名: ' + globalThis.__fetchHosts.filter(u => !HOST_OK.test(u)).join(', '));
  ok('全失败不写覆盖层', Object.keys(globalThis.state.competitorPriceOverrides).length === 0);

  /* ---------- 6. 手动填价路径完好（核心业务没被砍） ---------- */
  console.log('\n[6] 手动路径与成功链路在位');
  ok('applyCompetitorPrices 空数组防御在位', /applyCompetitorPrices\s*=/.test(SRC) && /if \(!Array\.isArray\(prices\) \|\| !prices\.length\) return;/.test(SRC));
  ok('手动编辑入口仍在（editCompetitor）', /editCompetitor\s*\(/.test(SRC));
  ok('失败引导可打开 AI 设置（openSettings）', /SpringAI\.openSettings\(\)/.test(SRC));
  ok('成功链路：搜索 → AI 抽取（可选）→ 本地解析兜底 → 预览确认', /renderAiPricePreview\(comp, prices/.test(SRC) && /applyCompetitorPrices\(comp, finalPrices\)/.test(SRC));
  ok('AI 不可用自动回落本地解析（isEnabled 判断 + parseSearchPrices 兜底）', /if \(SpringAI\.isEnabled\(\)\)/.test(SRC) && /parseSearchPrices\(search\.text, comp\)/.test(SRC));

  console.log('\n=== 结果：' + pass + ' 通过 / ' + fail + ' 失败 ===');
  process.exit(fail ? 1 : 0);
})();
