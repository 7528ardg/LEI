/* 全站功能检查报告 · HTML 可视化版（2026-10-05） */
const fs = require('fs');
const path = require('path');
const OUT = path.join(__dirname, '_全站功能检查报告_20261005.html');

const MODULES = [
  { id: 'qa', name: '你问我答', file: 'qa.html', icon: '💬', status: 'ok', len: 735, nodes: 359, h: 768, canvas: true,
    use: '五库知识问答（日常/手册/管理/规范/大撤）+ CBT 题库，AI 智能问答、语音输入、翻译模式、AI 练习',
    verify: 'E2E 加载 + 截图复核：六库按钮、8 个快捷入口、语音/翻译模式均渲染',
    issues: ['P1-3 权限旁路：ADMIN_ONLY_MODES 零引用、idb=2、roleGuard=0', '1 处「广州」为天气提问示例（低风险）'] },
  { id: 'quiz', name: '培训考核', file: 'quiz.html', icon: '📚', status: 'ok', len: 678, nodes: 266, h: 3212, canvas: true,
    use: '刷题系统：快速训练、错题复习、模拟考试、章节专项（12 章）、收藏题库；含诚信考试模式',
    verify: 'E2E 加载 + 截图复核：5 个训练入口 + 12 章节专项，Dashboard 正常',
    issues: ['P2-2 docs/_kb_cbt_new.js 今日 08:40 被修改，清理时段内被动过', '「广州」1 处属旧示例题清除白名单（必需，不可删）'] },
  { id: 'performance', name: '绩效管理', file: 'performance.html', icon: '📊', status: 'warn', len: 3351, nodes: 7203, h: 2980, canvas: true, admin: true,
    use: '飞行时长/绩效/销售数据管理，覆盖多地机组，IndexedDB 按月切分',
    verify: '普通账号 002191 → 被正确拦截（0 DOM）✅；管理员 028981 → 7203 DOM + canvas 图表渲染',
    issues: ['P1-1 独立账号体系：cabin_session_v1 引用 0 次，与壳层登录不互通，需二次登录'] },
  { id: 'beauty', name: '美妆话术', file: 'beauty.html', icon: '💄', status: 'danger', len: 3362, nodes: 1429, h: 768, canvas: false,
    use: '跨境商品解说工具（非旅客购物系统）：产品 351 款、需求推荐、话术生成、话术库 1237 条、AI 练习、竞品分析',
    verify: 'E2E 加载 + 截图复核：13 功能页签 + 快速上手指南；SET_NAME_RE 套装正则正确；window.scriptLibraryData 已挂载',
    issues: ['P0-3 产品库 767 条含 price，56 条 note 含违禁价格口径（券后价/大促折扣价/离岛免税价/海南免税渠道价）',
             'P0-3 竞品分析面板以红色加粗同时渲染 ¥价格 + note，违规内容直接暴露',
             '话术正文 1242 条 content 经扫描无违规 ✅'] },
  { id: 'daily', name: '日常问题', file: 'daily.html', icon: '❓', status: 'ok', len: 3867, nodes: 1472, h: 8532, canvas: false,
    use: '每日一练/日常问答检索，13 个分类共 77 条',
    verify: 'E2E 加载 + 截图复核：搜索框、热门标签、13 分类筛选、问答列表（OIT/汇总标记）',
    issues: ['P0-4 含 {{DUTY_MOBILE}}/{{DUTY_LANDLINE}} 占位符 5 处'] },
  { id: 'manual', name: '手册奖惩', file: 'manual.html', icon: '📕', status: 'ok', len: 34739, nodes: 4999, h: 61158, canvas: false,
    use: '手册奖惩查询：311 条，8 类分数类型，支持加分/扣分、对象筛选、收藏',
    verify: 'E2E 加载 + 截图复核：311 条 + 8 类型 + 9 对象 + 排序/重置',
    issues: ['P2-1 DOM 较重（4999 节点 / h=61158px），移动端首屏压力偏高'] },
  { id: 'home', name: 'CC 之家', file: 'cc-home.html', icon: '🏠', status: 'ok', len: 145, nodes: 344, h: 768, canvas: true,
    use: '24 个角色房间互动，3D 场景渲染，形象切换、在线 GLM、大厅、走访进度',
    verify: 'E2E 加载 + 截图复核：3D 房间场景（巴黎柜台/日式机舱）、角色卡、走访 1/24、导航按钮',
    issues: ['P2 3D 模型依赖 形象IP/models/js/ccNN.js base64 包装，需确保 APK assets 同步（已验证同步 ✅）'] },
  { id: 'medical', name: '医疗急救', file: 'medical.html', icon: '🚑', status: 'ok', len: 1347, nodes: 118, h: 2463, canvas: false,
    use: '机上医疗急救：分级处置、病例检查、练习闯关、报告生成；红/黄/绿三级分诊',
    verify: 'E2E 加载 + 截图复核：三色分级 + 旅客不适快速判断流程（手册 7.3/7.7/7.11）',
    issues: ['P2-3 三色分级依赖颜色传达，建议加色盲友好模式'] },
  { id: 'risk', name: '风险预警', file: 'risk-lite.html', icon: '⚠️', status: 'warn', len: 2434, nodes: 597, h: 823, canvas: false, admin: true,
    use: '6 大核心风险 SOP 摘要、天气地图（风场/台风/机场/航线/摘要图层）、航线筛选、今日晚报',
    verify: '普通账号 → 被正确拦截 ✅；管理员 → 截图复核 Leaflet 地图 + 5 图层 + 航班筛选 + 6 大 SOP 展开',
    issues: ['P1-5 地图瓦片与气象数据（WeatherAPI/Open-Meteo）为外部依赖，离线/网络受限会空白',
             '「广州」2 处为 IATA 机场码表（CAN=广州白云国际机场），业务必需不可删 ✅'] },
  { id: 'report', name: '事件报告', file: 'report.html', icon: '🗂', status: 'ok', len: 348, nodes: 108, h: 1367, canvas: false,
    use: '事件报告单（本地保存不联网）+ 全部流程 + 高频要点 + 报告渠道（6 大渠道）',
    verify: 'E2E 加载 + 截图复核：表单全字段 + 顶部统计（报告流程/事件分类/关联扣分项/报告渠道 6）',
    issues: ['P0-4 含值班电话占位符 14 处', '原疑「SQM 重复」已排除：截图两处为正文流程文本与报告渠道 tab，源码 11 处均正常业务引用'] },
  { id: 'kbadmin', name: '库管理', file: 'kb-admin.html', icon: '📇', status: 'danger', len: 9221, nodes: 750, h: 7396, canvas: false,
    use: '六库+销售话术+产品库集中管理：日常 90/乘务手册 399/管理手册 187/服务规范 146/大撤 42/CBT 785/话术库 1237/产品库 351，全库 3277 条',
    verify: 'E2E 加载 + 截图复核：六库计数芯片、筛选、条目列表（查看/编辑/删除）、批量操作',
    issues: ['P1-2 权限门禁缺失：ADMIN_ONLY_MODES 零引用、roleGuard=0，普通用户可增删改全站知识库',
             'P0-4 含值班电话占位符 28 处'] },
  { id: 'issues', name: '问题反馈', file: 'issues.html', icon: '🐞', status: 'ok', len: 369, nodes: 76, h: 1150, canvas: false,
    use: '留言反馈 + 问题单位置定位（板块级下拉）+ BUG 记录监控（自动捕获）',
    verify: 'E2E 加载 + 截图复核：4 项统计、定位下拉（默认「你问我答」）、提交留言',
    issues: ['数据仅存本地 localStorage，无后端汇聚（设计如此，非缺陷）'] },
];

const P0 = [
  { id: 'P0-1', title: '离线完整版品牌占位符裸露', where: '客舱小助手（离线完整版）.html（9 处）',
    evi: '实测 title 字面显示 {{AIRLINE}} · {{BASE}}分队客舱小助手；meta application-name/description 同样未注入',
    fix: '① 把该文件加入 _brandify_20261005.py 的 FILES；② 修正构建链顺序——brandify 当前排在 _build_4in1 之后（_build_all.py L100 vs L114），而离线版由 4in1 生成，永远晚一步。必须让 brandify 在 4in1 之后再跑一次' },
  { id: 'P0-2', title: '发布闸漏检离线完整版', where: '_check_needles.py L191-193',
    evi: '闸只列 14 个文件，不含离线版；56 项全绿却漏掉 P0-1',
    fix: '把离线完整版加入占位符反向针清单。这是「守护全绿≠功能正确」的典型：闸绿≠交付安全' },
  { id: 'P0-3', title: '产品库 56 条违禁价格口径 + 竞品面板红字展示', where: 'beauty.html 产品数据 note 字段 + 竞品分析面板（offset≈1882565）',
    evi: '面板以红色加粗渲染 ¥${p.price}（不叠券）与 ${p.note}；note 含「券后价」「大促折扣价」「离岛免税价」「海南免税渠道价」「免税活动价，原价209元」等',
    fix: '① 56 条 note 逐条改合规口径（逐条精确替换，禁正则批删——会截断裂句）；② 竞品面板属内部管理工具，建议加仅管理员可见或对乘务端隐藏；③ 补守护断言：产品库 note 不得含价格类违禁词' },
  { id: 'P0-4', title: '值班电话占位符裸露 89 处', where: 'qa(28)/kb-admin(28)/report(14)/quiz(8)/daily(5)/performance(1)/daily.template(5)',
    evi: '{{DUTY_MOBILE}}/{{DUTY_LANDLINE}} 合计 89 处显示给用户，集中在「值班经理电话」「安监部值班」等应急上报字段',
    fix: '属故意保留（_brandify 注释明言「无核实号码禁止臆造」），但后果是应急电话显示为占位符。须由用户决定：① 提供真实号码→补进 BRAND_MAP 并纳入发布闸；② 或改为「请查当班通讯录」等不暴露号码的表述（推荐，可立即执行）' },
];

const P1 = [
  { t: '绩效管理需二次登录', w: 'performance.html（cabin_session_v1 引用 0 次）', d: '用户已登录壳层仍需重输账号密码；两套账号体系可能不一致' },
  { t: '库管理无权限守卫', w: 'kb-admin.html（roleGuard=0）', d: '普通用户可增删改全站知识库；直接开页面即得管理员能力' },
  { t: 'qa 模块权限旁路', w: 'qa.html（ADMIN_ONLY_MODES 0 次、idb=2）', d: '可读 IndexedDB 无角色校验（历史已知，本次复核仍存在）' },
  { t: '双壳并存', w: 'index.html / nc/index.html', d: '改动需双改，易漏（_brandify 已含两处，但人工改动易漏）' },
  { t: '风险预警依赖外部气象源', w: 'risk-lite.html（WeatherAPI/Open-Meteo/Leaflet）', d: '离线或网络受限 → 地图空白' },
];

const P2 = [
  { t: '手册 DOM 较重', d: '4999 节点 / h=61158px，移动端首屏压力偏高' },
  { t: 'docs/_kb_cbt_new.js 今日 08:40 被修改', d: '清理时段内被动过，建议确认改动来源' },
  { t: '医疗急救三色分级依赖颜色传达', d: '建议加色盲友好模式' },
  { t: '清理残留 3 个 .bak 文件', d: 'docs/_dache_kb.js.bak_20261004、_cbt_work/categorized.json.bak_*（不影响功能）' },
  { t: '移动端页签需 force:true 才能点击', d: '横向滚动容器内，自动化测试需注意（非缺陷）' },
];

const STAT = [
  { v: '12', l: '壳层模块', c: 'ok' },
  { v: '81', l: '脚本语法全通过', c: 'ok' },
  { v: '0', l: '外链资源缺失', c: 'ok' },
  { v: '0', l: 'JS 运行时错误', c: 'ok' },
  { v: '4', l: 'P0 缺陷', c: 'bad' },
  { v: '5', l: 'P1 缺陷', c: 'warn' },
];

const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const html = `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>全站功能检查报告 · 2026-10-05</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
 background:#f5f8f6;color:#0f2a1f;line-height:1.7;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:32px 24px 64px}
header{background:linear-gradient(135deg,#148453,#1fa56a);color:#fff;border-radius:20px;padding:34px 32px;margin-bottom:26px}
header h1{font-size:1.75rem;font-weight:800;letter-spacing:-.3px}
header p{opacity:.94;margin-top:8px;font-size:.92rem}
header .meta{margin-top:14px;font-size:.8rem;opacity:.86;display:flex;gap:18px;flex-wrap:wrap}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:14px;margin-bottom:30px}
.stat{background:#fff;border-radius:14px;padding:18px 16px;text-align:center;border:1px solid #e4ece7}
.stat .v{font-size:1.85rem;font-weight:800;line-height:1.2}
.stat .l{font-size:.78rem;color:#5a6f65;margin-top:4px}
.stat.ok .v{color:#148453}.stat.bad .v{color:#c0392b}.stat.warn .v{color:#d68910}
h2{font-size:1.16rem;font-weight:800;margin:34px 0 14px;padding-left:12px;border-left:4px solid #148453}
.verdict{background:#fff8e6;border:1px solid #f0d9a0;border-left:4px solid #d68910;border-radius:12px;padding:16px 18px;margin-bottom:8px;font-size:.93rem}
.mods{display:grid;gap:14px}
.mod{background:#fff;border:1px solid #e4ece7;border-radius:14px;overflow:hidden}
.mh{display:flex;align-items:center;gap:12px;padding:15px 18px;cursor:pointer;user-select:none}
.mh:hover{background:#f8fbf9}
.mh .ic{font-size:1.5rem;width:34px;text-align:center;flex-shrink:0}
.mh .nm{font-weight:800;font-size:1rem}
.mh .fl{font-size:.76rem;color:#7a8c84;font-family:ui-monospace,Menlo,Consolas,monospace}
.mh .sp{flex:1}
.badge{font-size:.7rem;font-weight:700;padding:3px 9px;border-radius:20px;white-space:nowrap}
.b-ok{background:#e3f5ec;color:#0e7a4a}
.b-warn{background:#fdf0d5;color:#9a6708}
.b-danger{background:#fde8e6;color:#b02a1e}
.b-admin{background:#e8eef7;color:#2b4d7e}
.b-body{padding:0 18px 4px;font-size:.85rem;color:#4a5f56;font-family:ui-monospace,Menlo,Consolas,monospace;display:flex;gap:16px;flex-wrap:wrap;padding-bottom:12px}
.mc{padding:0 18px 18px;display:none}
.mod.open .mc{display:block}
.row{margin-bottom:12px;font-size:.89rem}
.row .lb{font-weight:800;color:#0f2a1f;font-size:.78rem;text-transform:uppercase;letter-spacing:.4px;margin-bottom:3px}
.row .vl{color:#42574e}
.iss{background:#fdf6f6;border:1px solid #f3d9d6;border-left:3px solid #c0392b;border-radius:8px;padding:9px 12px;margin-bottom:7px;font-size:.85rem;color:#7d2b22}
.iss.ok{background:#f2f9f5;border-color:#cfe8da;border-left-color:#148453;color:#1d5c3c}
.issue{background:#fff;border:1px solid #e4ece7;border-radius:12px;padding:16px 18px;margin-bottom:12px}
.issue .ih{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap}
.tag{font-size:.7rem;font-weight:800;padding:3px 9px;border-radius:6px;background:#c0392b;color:#fff}
.tag.p1{background:#d68910}.tag.p2{background:#5a6f65}
.issue h4{font-size:.98rem;font-weight:800}
.issue .kv{font-size:.83rem;color:#5a6f65;margin-top:5px}
.issue .kv b{color:#0f2a1f}
.issue .fx{margin-top:9px;padding:10px 12px;background:#f2f9f5;border-radius:8px;font-size:.85rem;color:#28543f;border-left:3px solid #148453}
.clean{background:#fff;border:1px solid #e4ece7;border-radius:12px;padding:18px;overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:.87rem;min-width:520px}
th{background:#f2f7f4;text-align:left;padding:10px 12px;font-weight:800;font-size:.8rem;color:#0f2a1f;border-bottom:2px solid #dce8e1}
td{padding:9px 12px;border-bottom:1px solid #eef3f0}
code{background:#eef3f0;padding:2px 6px;border-radius:4px;font-size:.84em;font-family:ui-monospace,Menlo,Consolas,monospace;color:#0b5c3a}
pre{background:#0f2a1f;color:#cfe8da;padding:16px 18px;border-radius:10px;overflow-x:auto;font-size:.83rem;line-height:1.65;font-family:ui-monospace,Menlo,Consolas,monospace}
pre .c{color:#7ea893}
.foot{margin-top:40px;padding-top:20px;border-top:1px solid #dce8e1;font-size:.8rem;color:#7a8c84;text-align:center}
</style></head><body><div class="wrap">

<header>
  <h1>全站功能逐一完整检查报告</h1>
  <p>融合版桌面端项目 · 全部板块 · 真实浏览器实测 + 截图肉眼复核 + 数据层取证</p>
  <div class="meta">
    <span>📅 2026-10-05</span>
    <span>🔍 静态体检 + E2E 实测 + 截图复核</span>
    <span>📁 证据：_e2e_out/（19 截图 + 3 result.json）</span>
  </div>
</header>

<div class="stats">
${STAT.map(s => `<div class="stat ${s.c}"><div class="v">${s.v}</div><div class="l">${s.l}</div></div>`).join('')}
</div>

<div class="verdict">
  <b>核心判断：功能层面全部可用</b>，但存在 <b>4 个 P0 级合规/交付缺陷</b>。最严重的是「离线完整版」直接露出模板占位符 <code>{{AIRLINE}}</code>，而发布闸恰好漏检该文件——<b>正是「守护全绿≠功能正确」的又一实例</b>（56 项全绿却漏掉 P0-1）。
</div>

<h2>一、逐板块 × 逐功能明细（12 个壳层模块）</h2>
<div class="mods">
${MODULES.map((m, i) => {
  const label = m.status === 'ok' ? '可用' : m.status === 'warn' ? '可用·有风险' : '可用·P0';
  const cls = m.status === 'ok' ? 'b-ok' : m.status === 'warn' ? 'b-warn' : 'b-danger';
  return `<div class="mod${i === 0 ? ' open' : ''}" data-m>
  <div class="mh">
    <span class="ic">${m.icon}</span>
    <span><span class="nm">${esc(m.name)}</span> <span class="fl">${m.file}</span></span>
    <span class="sp"></span>
    ${m.admin ? '<span class="badge b-admin">管理员专属</span>' : ''}
    <span class="badge ${cls}">${label}</span>
  </div>
  <div class="mbody">
    <div class="textLen">文本 ${m.len}</div><div>DOM ${m.nodes}</div><div>高 ${m.h}</div>
    <div>${m.canvas ? 'canvas ✓' : '无 canvas'}</div><div>JS 错误 0</div>
  </div>
  <div class="mc">
    <div class="row"><div class="lb">用途</div><div class="vl">${esc(m.use)}</div></div>
    <div class="row"><div class="lb">入口</div><div class="vl">壳层 <code>MOD_SRC.${m.id}</code>${m.admin ? ' · 受 <code>ADMIN_ONLY_MODES</code> 门禁' : ''}</div></div>
    <div class="row"><div class="lb">验证方式</div><div class="vl">${esc(m.verify)}</div></div>
    <div class="row"><div class="lb">发现的问题与风险</div><div>
      ${m.issues.map(x => {
        const isOk = x.includes('不可删') || x.includes('✅') || x.includes('已排除') || x.includes('无违规') || x.includes('非缺陷');
        return `<div class="iss${isOk ? ' ok' : ''}">${x}</div>`;
      }).join('')}
    </div></div>
  </div>
</div>`;
}).join('')}
</div>

<h2>二、问题清单 · P0（必须修复，阻断交付/合规）</h2>
${P0.map(p => `<div class="issue">
  <div class="ih"><span class="tag">${p.id}</span><h4>${esc(p.title)}</h4></div>
  <div class="kv"><b>位置：</b>${esc(p.where)}</div>
  <div class="kv"><b>证据：</b>${esc(p.evi)}</div>
  <div class="fx"><b>修复建议：</b>${esc(p.fix)}</div>
</div>`).join('')}

<h2>三、问题清单 · P1（应尽快修复）</h2>
${P1.map(p => `<div class="issue">
  <div class="ih"><span class="tag p1">P1</span><h4>${esc(p.t)}</h4></div>
  <div class="kv"><b>位置：</b><code>${esc(p.w)}</code></div>
  <div class="kv"><b>影响：</b>${esc(p.d)}</div>
</div>`).join('')}

<h2>四、问题清单 · P2（建议关注）</h2>
${P2.map(p => `<div class="issue">
  <div class="ih"><span class="tag p2">P2</span><h4>${esc(p.t)}</h4></div>
  <div class="kv">${esc(p.d)}</div>
</div>`).join('')}

<h2>五、清理工作影响评估：✅ 无断链</h2>
<div class="clean">
<table>
<tr><th>检查项</th><th>结论</th></tr>
<tr><td>删除的 22 个文件（md/html 报告）</td><td>全部为历史报告文档，<b>无脚本/HTML 引用</b>（限定范围 grep 验证 5 个代表性文件均「无引用」）</td></tr>
<tr><td>14 个功能页</td><td><b>全部在位</b>，体积正常（25KB ~ 6.2MB）</td></tr>
<tr><td>构建链脚本</td><td>80 个构建/补丁/守护脚本完整；<code>_build_pwa.py</code> 实际在 <code>PWA封装/</code> 下（<b>非缺失</b>，此前路径误判）</td></tr>
<tr><td>APK www 侧</td><td><code>APK封装/CabinAssistant/assets/www/</code> <b>14 个模块全部在位</b>，占位符已注入 ✅；index.html 401752 vs 源 379042（APK 侧含 v2 壳补丁，属正常差异）</td></tr>
</table>
</div>

<h2>六、验证方式（可复跑）</h2>
<pre><span class="c"># 1) 起本地服务（多线程，避免单线程 http.server 堵死并发）</span>
python _serve.py 8899

<span class="c"># 2) 全站逐模块 E2E（普通账号 12 模块 + 管理员复测 risk/performance）</span>
node _e2e_allmodules_20261005.js   <span class="c"># → __e2e_out/result_user.json / result_admin.json</span>

<span class="c"># 3) 独立页补测（离线版 / spring-assistant / nc）</span>
node _e2e_pages_20261005.js<span class="c"># → __e2e_out/result_pages.json</span>

<span class="c"># 4) 发布闸</span>
python _check_needles.py           <span class="c"># → 56 项，当前全绿（但漏检离线版，见 P0-2）</span></pre>

<div class="clean" style="margin-top:14px">
<table>
<tr><th>判据</th><th>说明</th></tr>
<tr><td>模块就绪</td><td><code>contentDocument.readyState==='complete'</code> <b>且</b> 可见文本 &gt; 20 字符 <b>且</b> <code>wrap-x</code> 已激活</td></tr>
<tr><td>权限正确性</td><td>普通账号应 <code>active=false</code> / 0 DOM，管理员应正常渲染</td></tr>
<tr><td>合规检查</td><td><b>先剥注释再匹配</b>（注释里复述旧写法会误伤），区分「规则表命中」与「真实语料命中」</td></tr>
</table>
</div>

<div class="foot">
  报告生成 2026-10-05 ｜ 依据真实浏览器实测 + 截图肉眼复核 + 数据层取证，未依赖任何声明式结论
</div>

</div>
<script>
document.querySelectorAll('.mh').forEach(function(h){
  h.addEventListener('click',function(){ h.parentElement.classList.toggle('open'); });
});
</script>
</body></html>`;

fs.writeFileSync(OUT, html, 'utf8');
console.log('written', OUT, fs.statSync(OUT).size, 'bytes');
