# -*- coding: utf-8 -*-
"""
UX Polish 注入器 v1（幂等）
把统一的「设计令牌 + 交互规范 + 分模块修复」CSS 以标记块注入各模块 HTML 的 </head> 前。
- 规范源：index.html 壳层设计语言（--primary #148453 / --gold #F5B800 / 彩绘渐变 / 暗色变量）
- 幂等：先剥离旧标记块再注入，可重复执行
- beauty 额外做品牌色收拢（Tailwind 翡翠绿 -> 春秋绿系）的字面量替换
用法：python _apply_ux_polish.py          # 执行
      python _apply_ux_polish.py --check  # 仅校验标记块存在（供 _build_all 回归链调用）
"""
import io, os, re, sys, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

BEGIN = '/*__UX_POLISH:v1__*/'
END = '/*__UX_POLISH_END__*/'
BAK = os.path.join(HERE, '_bak_uxpolish_20260915')

# ---------- 公共层：浏览器表面主题化 + 交互反馈 + 动效可及性 ----------
COMMON = """
/* ---- UX Polish v1 · 统一交互规范（规范源：index.html 壳层）---- */
:root{
  --ux-primary:#148453;--ux-primary-dark:#0C5F3A;--ux-primary-light:#1FA56A;
  --ux-gold:#F5B800;--ux-danger:#C62828;--ux-warn:#E64A19;
  --ux-ink:#0F2A1F;--ux-ink2:#5A6F65;--ux-border:#E5EDE9;
  --ux-radius-sm:8px;--ux-radius:12px;--ux-radius-lg:16px;
  /* 嵌入态底部补偿：index 壳层内嵌时由宿主注入实际 TabBar 高度；
     独立打开时回退 0px，模块自身安全区逻辑照旧（2026-09-16 遮挡修复） */
  --embed-bottom:0px;
  --embed-top:0px;
}
::selection{background:rgba(20,132,83,.24);}
*{scrollbar-width:thin;scrollbar-color:rgba(20,132,83,.35) transparent;}
::-webkit-scrollbar{width:8px;height:8px;}
::-webkit-scrollbar-thumb{background:rgba(20,132,83,.30);border-radius:99px;border:2px solid transparent;background-clip:content-box;}
::-webkit-scrollbar-track{background:transparent;}
button,a,[role="button"],input,select,textarea,label{-webkit-tap-highlight-color:transparent;}
button:not(:disabled){transition:transform .15s ease,box-shadow .2s ease,filter .2s ease,background-color .2s ease,border-color .2s ease,opacity .2s ease;}
button:active:not(:disabled){transform:translateY(1px);}
:focus{outline:none;}
:focus-visible{outline:2.5px solid #148453;outline-offset:2px;border-radius:6px;}
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;scroll-behavior:auto!important;}
}
/* ---- 深色模式：滚动条随主题（浅色令牌在 :root，各模块 dark 规则见下）---- */
html[data-theme="dark"] *{scrollbar-color:rgba(255,255,255,.22) transparent;}
html[data-theme="dark"] ::-webkit-scrollbar-thumb{background:rgba(255,255,255,.20);border:2px solid transparent;background-clip:content-box;}
html[data-theme="dark"] ::selection{background:rgba(31,165,106,.34);}
"""

# ---------- 深色模式：通用兜底层（所有模块共用，防「只有边框变深」）----------
# 说明：各模块自带的 --bg/--text 令牌优先；此层负责
# ① 给尚无令牌体系的模块提供最小可用暗色变量
# ② 修正深色下「浅底浅字」造成的不可读
DARK_COMMON = """
/* ---- UX Polish v1 · 深色模式兜底层（2026-09-16）----
   用户反馈：深色模式只有边框在变、美妆与医疗未覆盖、深色下部分文字看不清。
   本层为「无令牌体系」的模块补最小暗色变量，并统一修高对比度问题。 */
html[data-theme="dark"]{
  color-scheme:dark;
  --bg:#0F1A14;--bg-card:#162420;--bg-elev:#1B2E26;
  --text:#E8F3EE;--text2:#9CB3A7;--text3:#6E8479;
  --border:#24402F;--border-strong:#2E5240;
  --primary-soft:#1A3D2A;--primary-mist:#132C21;
  --shadow:0 4px 14px rgba(0,0,0,.42);--shadow-lg:0 14px 36px rgba(0,0,0,.55);
}
html[data-theme="dark"] body{background:var(--bg);color:var(--text);}
/* 输入类：深色下浏览器默认白底白字，必须显式覆盖 */
html[data-theme="dark"] input,
html[data-theme="dark"] select,
html[data-theme="dark"] textarea{
  background:var(--bg-elev);color:var(--text);border-color:var(--border);
}
html[data-theme="dark"] input::placeholder,
html[data-theme="dark"] textarea::placeholder{color:var(--text3);}
/* 深色下「浅色底 + 浅色字」组合的兜底可读性修复 */
html[data-theme="dark"] .bg-white,
html[data-theme="dark"] .bg-gray-50,
html[data-theme="dark"] .bg-gray-100,
html[data-theme="dark"] .bg-slate-50,
html[data-theme="dark"] .bg-slate-100{background:var(--bg-card)!important;}
html[data-theme="dark"] .text-gray-900,
html[data-theme="dark"] .text-gray-800,
html[data-theme="dark"] .text-slate-900,
html[data-theme="dark"] .text-slate-800,
html[data-theme="dark"] .text-black{color:var(--text)!important;}
html[data-theme="dark"] .text-gray-700,
html[data-theme="dark"] .text-gray-600,
html[data-theme="dark"] .text-slate-700,
html[data-theme="dark"] .text-slate-600{color:#C3D6CB!important;}
html[data-theme="dark"] .text-gray-500,
html[data-theme="dark"] .text-gray-400,
html[data-theme="dark"] .text-slate-500,
html[data-theme="dark"] .text-slate-400{color:var(--text2)!important;}
html[data-theme="dark"] .border-gray-100,
html[data-theme="dark"] .border-gray-200,
html[data-theme="dark"] .border-gray-300,
html[data-theme="dark"] .border-slate-200{ border-color:var(--border)!important;}
"""


QA = COMMON + DARK_COMMON + """
/* qa：手机档顶栏按钮防裁切 + 小字下限 */
@media (max-width:760px){
  .t-ai{gap:5px;}
  .t-ai .icon-btn{min-height:34px;font-size:.7rem;padding:0 7px;border-radius:9px;}
  .t-ai .ai-status{font-size:.66rem;}
  .icon-btn{min-height:36px;}
}
small{font-size:11.5px;}
#aiStatus{font-size:11px;}
.lbl{font-size:11px;}

/* qa 深色专项（2026-09-16）：qa 已有完整 :root 令牌，此处只补深色下的可读性微调 */
html[data-theme="dark"]{color-scheme:dark;--bg:#0F1A14;--bg-card:#162420;--border:#1E3A2C;}
html[data-theme="dark"] .bubble{color:#E8F3EE;}
html[data-theme="dark"] .ts{color:#7C9489;}
html[data-theme="dark"] .kb-card,
html[data-theme="dark"] .dc-card{background:#162420;border-color:#1E3A2C;color:#E8F3EE;}

/* ---- qa：手机档（≤640px）排版修复 · 2026-09-15 ----
   用户反馈：手机打开后排版不正确 / 底部对话框与切换栏有黑边。
   注意：本标记块由 _apply_ux_polish.py 幂等重建——规则改这里才不会被冲掉，
   直接改 HTML 里的标记块会在下次构建时丢失（2026-09-15 已发生过一次）。 */
@media (max-width:640px){
  /* ① 欢迎卡整行铺开：不再被 74% 气泡宽度挤成 ~200px 细长条且偏左；
     去头像与气泡壳、时间戳（配合 qa.html renderChat 给含 .welcome 的消息加的 .msg-welcome 标记） */
  #chatWrap .msg.msg-welcome{max-width:100%;}
  #chatWrap .msg.msg-welcome .avatar{display:none;}
  #chatWrap .msg.msg-welcome .bubble{background:transparent;border-color:transparent;box-shadow:none;padding:0;
    backdrop-filter:none;-webkit-backdrop-filter:none;}
  #chatWrap .msg.msg-welcome .ts{display:none;}
  /* ② 顶栏：状态徽章与设置入口在窄屏收起文案（手机一行放不下，360px 会被横向挤爆裁掉） */
  .topbar{padding:7px 10px;gap:8px;}
  .topbar .ai-status{display:none;}
  .t-ai{gap:4px;}
  .t-ai .icon-btn{padding:0 6px;}
  /* ③ 底部提示一行省略号，不折两行顶到屏幕底边 */
  .tip-bar{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  /* ④ 底部功能区贴明度（反馈：对话框/切换栏「黑边」）——形象条 / 五库 / 输入区以 58% 玻璃
     浮在深色原画上会透成暗灰一片；手机档抬到近实底（97% + 轻模糊），玻璃质感只留给聊天气泡 */
  #petBar{background:color-mix(in srgb, var(--bg-card,#fff) 97%, transparent);
    backdrop-filter:blur(10px) saturate(1.1);-webkit-backdrop-filter:blur(10px) saturate(1.1);}
  .input-area{background:color-mix(in srgb, var(--bg-card,#fff) 97%, transparent);
    backdrop-filter:blur(10px) saturate(1.1);-webkit-backdrop-filter:blur(10px) saturate(1.1);}
  .ti-wrap{background:var(--bg-card,#fff);}
  .ti-wrap:focus-within{background:var(--bg-card,#fff);}
  .tip-bar{color:var(--text2,#5A6F65);}
  /* ⑤ 输入框占位文字单行显示：手机档两行折行会被 1 行高的输入框拦腰截断，观感差 */
  .ti::placeholder{white-space:nowrap;overflow:hidden;}
}

/* ---- qa 响应式专项（2026-09-17 审计 / 2026-09-19 触摸达标）----
   形象条按钮 pb-c 实测 25px 高、欢迎词 chips 25px 高、五库切换 src-tab 31px 高，
   触控目标过小；输入框 15px 会触发 iOS 聚焦缩放（含 768 平板档）。
   2026-09-19：三处补到 44px（WCAG 2.5.8 目标尺寸下限），避免移动端误触/漏点。
   2026-09-19 设计审核 P0-B：原条件只有 max-width:760px，导致 761–1020 平板档
   仍是 25/31px（实测平板 10 项不达标）。改挂 pointer:coarse —— 语义上正是「触摸设备」，
   同时覆盖手机与平板；带鼠标的桌面仍走 fine 分支保持紧凑密度。 */
@media (max-width:900px){
  #qaInput{font-size:16px!important;}
}
@media (max-width:760px), (pointer:coarse){
  #petBar .pb-c{min-height:44px;padding:8px 12px;font-size:12px;}
  .w-chip{min-height:44px;padding:9px 14px;}
  .src-tab{min-height:44px;}
}
/* 同批：qa 模块头动作键 32px、欢迎卡关闭 25px、快问行芯片 30px 也不达标 */
@media (pointer:coarse){
  .icon-btn{min-height:44px;padding:8px 12px;}
  .sx{min-width:44px;min-height:44px;}
  .qq-x{min-width:44px;min-height:44px;}
  .qq-c{min-height:44px;padding:8px 12px;}
}
"""

BEAUTY = COMMON + DARK_COMMON + """
/* beauty：令牌对齐壳层（原翡翠绿系已字面量收拢为春秋绿系） */
:root{
  --primary:#148453;--primary-dark:#0C5F3A;--primary-light:#1FA56A;
  --primary-soft:#E8F3EE;--primary-mist:#F4F9F6;
  --gold:#F5B800;--danger:#C62828;
  --bg:#F5F8F6;--bg-card:#fff;--text:#0F2A1F;--text2:#5A6F65;--border:#E5EDE9;
}
/* ---- beauty 深色专项（2026-09-16）----
   beauty 是 Tailwind 类名驱动（bg-white×181 / text-gray-800×347 / bg-gray-50×45…），
   没有令牌体系，因此深色必须做「类名级」映射，否则只有边框变深。 */
html[data-theme="dark"]{
  --bg:#0E1713;--bg-card:#17231E;--text:#E8F3EE;--text2:#9CB3A7;--border:#25402F;
  --primary-soft:#17352a;--primary-mist:#12281F;
}
html[data-theme="dark"] #app{background:var(--bg);}
/* 卡片 / 面板：白底一律转深卡 */
html[data-theme="dark"] .card-shadow,
html[data-theme="dark"] .bg-white\\/95,
html[data-theme="dark"] .bg-white\\/80,
html[data-theme="dark"] .bg-white\\/90,
html[data-theme="dark"] .bg-white\\/70{background:rgba(23,35,30,.96)!important;border-color:var(--border)!important;}
/* 次级底：gray-50/100 转深一档 */
html[data-theme="dark"] .bg-gray-50,
html[data-theme="dark"] .bg-gray-100,
html[data-theme="dark"] .bg-gray-200{background:#1D2C25!important;}
/* 正文 / 次要文字：保证深底上可读（浅色下原为 gray-800/700/600/500/400） */
html[data-theme="dark"] .text-gray-900,
html[data-theme="dark"] .text-gray-800{color:#E8F3EE!important;}
html[data-theme="dark"] .text-gray-700{color:#CFE0D6!important;}
html[data-theme="dark"] .text-gray-600{color:#B4C9BD!important;}
html[data-theme="dark"] .text-gray-500{color:#93ABA0!important;}
html[data-theme="dark"] .text-gray-400{color:#7C9489!important;}
/* 边框 */
html[data-theme="dark"] .border-gray-100,
html[data-theme="dark"] .border-gray-200,
html[data-theme="dark"] .border-gray-300{border-color:var(--border)!important;}
/* 品牌绿在深底上要提亮一档，否则「墨绿压墨绿」看不清 */
html[data-theme="dark"] .text-emerald-600,
html[data-theme="dark"] .text-emerald-700,
html[data-theme="dark"] .text-emerald-800{color:#3FCB8B!important;}
html[data-theme="dark"] .text-emerald-500{color:#4FD79A!important;}
html[data-theme="dark"] .bg-emerald-50,
html[data-theme="dark"] .bg-emerald-100{background:#17352A!important;}
html[data-theme="dark"] .border-emerald-100,
html[data-theme="dark"] .border-emerald-200,
html[data-theme="dark"] .border-emerald-300,
html[data-theme="dark"] .border-emerald-400{border-color:#2C5C43!important;}
/* 语义色（警告/危险/提示）在深底的浅底块同样要压深，否则刺眼且文字发灰 */
html[data-theme="dark"] .bg-red-50,
html[data-theme="dark"] .bg-red-100{background:#3A1D1D!important;}
html[data-theme="dark"] .bg-rose-50{background:#3A1D22!important;}
html[data-theme="dark"] .bg-amber-50,
html[data-theme="dark"] .bg-amber-100{background:#33290F!important;}
html[data-theme="dark"] .bg-orange-50,
html[data-theme="dark"] .bg-orange-100{background:#3A2513!important;}
html[data-theme="dark"] .bg-blue-50,
html[data-theme="dark"] .bg-indigo-50{background:#182B3A!important;}
html[data-theme="dark"] .text-amber-700,
html[data-theme="dark"] .text-amber-800{color:#F0C94A!important;}
html[data-theme="dark"] .text-red-600,
html[data-theme="dark"] .text-rose-700{color:#F98A8A!important;}
html[data-theme="dark"] .text-orange-700{color:#F5A76A!important;}
html[data-theme="dark"] .text-cyan-800{color:#7FD8E8!important;}
html[data-theme="dark"] .text-green-600{color:#4FD79A!important;}
/* 选中态卡片 / 渐变按钮在深色下的可读性 */
html[data-theme="dark"] .selected-product-card{background:linear-gradient(135deg,#16332A 0%,#16332A 100%)!important;}
html[data-theme="dark"] .selected-product-card .text-gray-800,
html[data-theme="dark"] .selected-product-card span{color:#E8F3EE!important;}
/* 顶部 sticky 工具条（原 bg-white/95）与搜索框 */
html[data-theme="dark"] .sticky.top-\\[120px\\]{background:rgba(23,35,30,.94)!important;border-color:var(--border)!important;}
html[data-theme="dark"] #search-input{background:#1D2C25!important;color:var(--text)!important;border-color:var(--border)!important;}
/* 表格 / 分隔线 */
html[data-theme="dark"] .divide-gray-100 > * + *,
html[data-theme="dark"] .divide-gray-200 > * + *{border-color:var(--border)!important;}
@media (max-width:760px){
  button.px-3.py-1\\.5{min-height:36px;}
  select.px-3.py-2{min-height:42px;font-size:16px!important;}
  #search-input{min-height:44px;font-size:16px!important;}
  button.flex.items-center{min-height:38px;}
}
/* ---- beauty 响应式专项（2026-09-17 审计）----
   筛选 chips（护眼/护肝/营养包等）实测 24px 高、弹窗关闭 × 18px 宽、✓全选 28px，
   触控目标过小；表单 12~13px 触发 iOS 聚焦缩放。
   注意：类选择器多类组合不转义（.px-2.py-1），仅 class 名自带点号时转义（.py-1\\.5）。 */
@media (max-width:760px){
  button.px-2.py-1{min-height:34px;padding-top:5px;padding-bottom:5px;}
  button.px-2.py-0\\.5{min-height:34px;padding-top:5px;padding-bottom:5px;}
  button.p-1\\.5{min-width:34px;min-height:34px;justify-content:center;}
  button[aria-label="关闭"]{min-width:40px;min-height:40px;font-size:1.35rem;}
  select,textarea,
  input[type="text"],input[type="search"]{font-size:16px!important;}
}
@media (max-width:900px){
  select.px-3.py-2{font-size:16px!important;}
  #search-input{font-size:16px!important;}
}
/* Tailwind 渐变工具类在本模块静态构建中未生成（教程弹窗标题条等渲染为白底），
   按品牌绿系兜底，同时把渐变上的 gray-800 深字统一为白字保证对比度。 */
.bg-gradient-to-r.from-emerald-500{background-image:linear-gradient(90deg,#1FA56A,#148453)!important;}
.bg-gradient-to-r.from-emerald-600{background-image:linear-gradient(90deg,#148453,#0C5F3A)!important;}
.bg-gradient-to-r.from-emerald-500.text-gray-800,
.bg-gradient-to-r.from-emerald-500 .text-gray-800,
.bg-gradient-to-r.from-emerald-600.text-gray-800,
.bg-gradient-to-r.from-emerald-600 .text-gray-800{color:#fff!important;}
/* ---- 嵌入态底部留白（2026-09-16 遮挡修复）----
   内联 max-height:calc(100vh - 160px) 在壳层内嵌时按模块自身视口算，
   与 iframe 实际高度不符，导致列表底边与 iframe 底边之间出现死带。
   改用 --embed-bottom（宿主注入 TabBar 高度）参与计算。 */
.main-scroll-container{
  max-height:calc(100vh - 160px - var(--embed-bottom,0px))!important;
  padding-bottom:calc(16px + var(--embed-bottom,0px))!important;
}
@media (max-width:760px){
  .main-scroll-container{max-height:calc(100dvh - 150px - var(--embed-bottom,0px))!important;}
}
"""

QUIZ = COMMON + DARK_COMMON + """
/* quiz：手机档顶栏防溢出（+hamburger/logo/面包屑/胶囊 弹性收缩）+ 小字下限 */
@media (max-width:700px){
  .topbar{gap:8px;padding:0 10px;}
  .topbar .brand-sub{display:none;}
  .topbar .net-status{display:none;}
  .topbar .breadcrumb{min-width:0;flex:1 1 auto;overflow:hidden;}
  .topbar .breadcrumb .current{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .topbar .user-chip{flex-shrink:1;min-width:0;max-width:132px;padding:5px 10px 5px 6px;}
  .topbar .user-chip > *:not(.avatar){white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
}
.qt-meta{font-size:12px;}
.qt-tag{font-size:12px;}

/* quiz 响应式专项（2026-09-17 审计）：汉堡按钮实测 20px 宽、开始训练 33px 高，
   触控目标过小；360px 窄屏用户胶囊再收窄防溢出。 */
@media (max-width:700px){
  .hamburger{min-width:44px;}
}
@media (max-width:760px){
  .dgb-action{min-height:44px;}
}
@media (max-width:360px){
  .topbar .user-chip{max-width:96px;padding:5px 8px 5px 5px;}
}
"""

MANUAL = COMMON + DARK_COMMON + """
/* manual：小字下限 + 手机档触控目标 */
small{font-size:12px;}
.f-label,#f-cat-cnt{font-size:11.5px;}
/* manual 响应式专项（2026-09-17 审计）：收藏星标 21x25 触控过小；
   tab 行 320/375 档溢出改紧凑内滚；表单 15/12px 触发 iOS 缩放。 */
@media (max-width:760px){
  .m-tab{min-height:40px;padding:8px 10px;font-size:.78rem;}
  .chip{min-height:34px;}
  input#kw{min-height:42px;font-size:16px!important;}
  #sortSel{min-height:42px;font-size:16px!important;}
  .fav{min-width:34px;min-height:34px;font-size:15px;}
  .expand{min-height:36px;padding:6px 10px;}
}
@media (max-width:900px){
  input#kw,#sortSel{font-size:16px!important;}
}
"""

REPORT = COMMON + DARK_COMMON + """
/* report：手机档触控目标 */
/* report 响应式专项（2026-09-17 审计）：320 档 tab 行溢出改紧凑内滚；
   表单 14~15px 触发 iOS 聚焦缩放，统一抬到 16px（含 768 平板档）。 */
@media (max-width:760px){
  .m-tab{min-height:40px;padding:6px 10px;font-size:.76rem;}
  input#kw{min-height:42px;font-size:16px!important;}
  select.ri,input.ri{min-height:42px;font-size:16px!important;}
}
@media (max-width:900px){
  input#kw,select.ri,input.ri{font-size:16px!important;}
  select,textarea,
  input[type="text"],input[type="date"],input[type="time"]{font-size:16px!important;}
}
"""

MEDICAL = COMMON + DARK_COMMON + """
/* medical：手机档基础触控目标 */
/* medical 响应式专项（2026-09-17 审计）：320/375 档 tab 行溢出改紧凑内滚，
   表单字号统一 16px 防 iOS 聚焦缩放。 */
@media (max-width:760px){
  button{min-height:36px;}
  input,select{min-height:42px;font-size:16px;}
  .m-tab{min-height:40px;padding:8px 10px;font-size:12.5px;}
}
/* ---- medical 深色专项（2026-09-16）----
   medical 为纯十六进制写死的语义类体系（body #f6f8fa / .card #fff / .sec-title #111827…），
   令牌缺失 → 深色下只有边框变化、文字仍为深灰，故按类名精确映射。 */
html[data-theme="dark"] body{background:#0E1713!important;color:#E8F3EE!important;}
html[data-theme="dark"] .card{background:#17231E!important;border-color:#25402F!important;box-shadow:0 4px 14px rgba(0,0,0,.42)!important;}
html[data-theme="dark"] .card-h{color:#E8F3EE!important;}
html[data-theme="dark"] .sec-title{color:#E8F3EE!important;}
html[data-theme="dark"] .menu{background:rgba(23,35,30,.94)!important;border-bottom-color:#25402F!important;}
/* 说明块 / 报告区 / 标签：浅灰底在深色下必须压深，否则浅底浅字不可读 */
html[data-theme="dark"] .hint{background:#1B2B24!important;border-color:#2C4636!important;color:#A7BDB2!important;}
html[data-theme="dark"] .report-area{background:#1B2B24!important;border-color:#25402F!important;color:#CFE0D6!important;}
html[data-theme="dark"] .src-tag{background:#22352C!important;color:#A7BDB2!important;}
html[data-theme="dark"] .chip{background:#22352C!important;color:#CFE0D6!important;}
/* 警示块：橙色系在深色下压深并提亮文字，保留「警示」语义 */
html[data-theme="dark"] .warn-box{background:#3A2513!important;border-color:#7A4A1E!important;color:#F5C08A!important;}
html[data-theme="dark"] ul.pts li{color:#C3D6CB!important;}
html[data-theme="dark"] ul.pts li:before{background:#4A6358!important;}
html[data-theme="dark"] ul.pts li.warn{color:#F98A8A!important;}
/* 红/黄/绿语义 chip 深色适配（原为 #fee2e2+#b91c1c 这类浅底深字） */
html[data-theme="dark"] .chip.red{background:#3A1D1D!important;color:#F98A8A!important;}
html[data-theme="dark"] .chip.yellow{background:#33290F!important;color:#F0C94A!important;}
html[data-theme="dark"] .chip.green{background:#17352A!important;color:#4FD79A!important;}
html[data-theme="dark"] .chip.gray{background:#22352C!important;color:#A7BDB2!important;}
/* 表单控件 */
html[data-theme="dark"] input[type=text],
html[data-theme="dark"] input[type=datetime-local],
html[data-theme="dark"] select,
html[data-theme="dark"] textarea{background:#1B2B24!important;color:#E8F3EE!important;border-color:#2C4636!important;}
html[data-theme="dark"] .fig{color:#A7BDB2!important;}
html[data-theme="dark"] .fig figcaption{background:#1B2B24!important;color:#A7BDB2!important;border:1px solid #2C4636;}
html[data-theme="dark"] .fig b{color:#F98A8A!important;}
html[data-theme="dark"] .fig img{background:#17231E!important;border-color:#25402F!important;}
html[data-theme="dark"] .fig-wrap .fig span{background:#22352C!important;}
/* 页头标题：原文 .title 是 #111827（深字），深色下必须压浅 */
html[data-theme="dark"] .title{color:#F2F8F5!important;}
html[data-theme="dark"] .headbar .sub,
html[data-theme="dark"] .headbar small{color:#A7BDB2!important;}
html[data-theme="dark"] .step-tag{background:#17352A!important;color:#4FD79A!important;}
html[data-theme="dark"] .eq-tag{background:#22352C!important;color:#CFE0D6!important;}
html[data-theme="dark"] .f-label{color:#A7BDB2!important;}
html[data-theme="dark"] .add-row-btn{background:#22352C!important;color:#8FD9B4!important;border-color:#2C4636!important;}
"""

PERF = COMMON + DARK_COMMON + """
/* performance：Bootstrap 令牌收拢为春秋绿系 + 图表小字下限 + 表单触控 */
:root{
  --bs-primary:#148453;--bs-primary-rgb:20,132,83;
  --bs-link-color:#0C5F3A;--bs-link-hover-color:#0A4E30;--bs-border-color:#E5EDE9;
}
.btn-primary{--bs-btn-bg:#148453;--bs-btn-border-color:#148453;--bs-btn-hover-bg:#0C5F3A;--bs-btn-hover-border-color:#0C5F3A;--bs-btn-active-bg:#0A4E30;--bs-btn-active-border-color:#0A4E30;--bs-btn-disabled-bg:#148453;--bs-btn-disabled-border-color:#148453;}
.btn-outline-primary{--bs-btn-color:#148453;--bs-btn-border-color:#148453;--bs-btn-hover-bg:#148453;--bs-btn-hover-border-color:#148453;--bs-btn-active-bg:#148453;--bs-btn-active-border-color:#148453;}
.brand-subtitle{font-size:11px;}
svg text{font-size:10.5px;}
@media (max-width:900px){
  .form-select,.form-control{min-height:42px;font-size:16px!important;}
  #loginUsername,#loginPassword{min-height:46px;font-size:16px!important;}
}
@media (max-width:760px){
  .navbar-toggler{min-width:46px;min-height:46px;}
  .password-toggle{min-width:40px;min-height:40px;}
}
/* ---- performance 深色专项（2026-09-16）----
   该模块是 Bootstrap 5：原生暗色靠 data-bs-theme="dark"（自带 163 条规则），
   但壳层只设了 data-theme，故深色一直没生效。此处把两者打通 + 修绿系在深底的对比度。
   特别注意：performance 内有一条「全局文字颜色统一为黑色」的旧规则
   （body,.card,div,span,p,h1..h6,td,th,li,button{color:#000}），会与暗色互斥，
   必须在暗色下用同等选择器 + !important 明确压回浅色文字。 */
html[data-theme="dark"]{
  --bs-body-bg:#0F1A14;--bs-body-color:#E8F3EE;
  --bs-emphasis-color:#F2F8F5;--bs-secondary-color:#9CB3A7;
  --bs-tertiary-bg:#1B2B24;--bs-secondary-bg:#17231E;
  --bs-border-color:#25402F;--bs-border-color-translucent:rgba(255,255,255,.10);
  --bs-body-bg-rgb:15,26,20;
}
/* 压回旧「全局黑色文字」规则：暗色下这些元素一律用浅色文字 */
html[data-theme="dark"] body,
html[data-theme="dark"] .module-content,
html[data-theme="dark"] div,
html[data-theme="dark"] p,
html[data-theme="dark"] span,
html[data-theme="dark"] label,
html[data-theme="dark"] small,
html[data-theme="dark"] h1,
html[data-theme="dark"] h2,
html[data-theme="dark"] h3,
html[data-theme="dark"] h4,
html[data-theme="dark"] h5,
html[data-theme="dark"] h6,
html[data-theme="dark"] li,
html[data-theme="dark"] dt,
html[data-theme="dark"] dd,
html[data-theme="dark"] td,
html[data-theme="dark"] th,
html[data-theme="dark"] .form-label,
html[data-theme="dark"] .form-text,
html[data-theme="dark"] .metric-label,
html[data-theme="dark"] .module-section-title,
html[data-theme="dark"] .user-info{color:#E8F3EE!important;}
html[data-theme="dark"] .text-muted,
html[data-theme="dark"] .form-text,
html[data-theme="dark"] small{color:#9CB3A7!important;}
/* 按钮：旧规则给 button 也上了黑色文字，但主按钮是绿底白字，需单独排除 */
html[data-theme="dark"] .btn-primary,
html[data-theme="dark"] .btn-success,
html[data-theme="dark"] .btn-danger{color:#fff!important;}
html[data-theme="dark"] button:not(.btn-primary):not(.btn-success):not(.btn-danger):not(.navbar-toggler){color:#E8F3EE;}
/* Bootstrap 组件在深色下的显式兜底（部分版本 dark 变量不覆盖这些） */
html[data-theme="dark"] .card,
html[data-theme="dark"] .card-body,
html[data-theme="dark"] .card-header,
html[data-theme="dark"] .modal-content,
html[data-theme="dark"] .offcanvas,
html[data-theme="dark"] .dropdown-menu,
html[data-theme="dark"] .list-group-item{background:#17231E!important;color:#E8F3EE!important;border-color:#25402F!important;}
html[data-theme="dark"] .card-header{border-bottom-color:#25402F!important;}
html[data-theme="dark"] .modal-header,
html[data-theme="dark"] .modal-footer{border-color:#25402F!important;}
html[data-theme="dark"] .table{--bs-table-color:#E8F3EE;--bs-table-bg:transparent;--bs-table-border-color:#25402F;color:#E8F3EE;}
html[data-theme="dark"] .table-striped>tbody>tr:nth-of-type(odd)>*{--bs-table-accent-bg:#1B2B24;color:#E8F3EE;}
/* 表头：Bootstrap 的 thead 默认背景是 #fafbfc 浅灰，深色下会变浅底浅字 */
html[data-theme="dark"] thead,
html[data-theme="dark"] .table>thead,
html[data-theme="dark"] .table-light>thead,
html[data-theme="dark"] table thead tr{background:#1E2E27!important;}
html[data-theme="dark"] thead th,
html[data-theme="dark"] .table>thead th,
html[data-theme="dark"] table th{background:#1E2E27!important;color:#C3D6CB!important;border-bottom-color:#2C4636!important;}
html[data-theme="dark"] tbody td{color:#E8F3EE;border-color:#22362C;}
/* 顶部状态提示条 / 底部固定页脚（rgba(255,255,255,.8) 半透明白） */
html[data-theme="dark"] .save-status,
html[data-theme="dark"] .status-bar,
html[data-theme="dark"] .toast-bar,
html[data-theme="dark"] .top-status,
html[data-theme="dark"] footer.fixed-bottom,
html[data-theme="dark"] .fixed-bottom{background:rgba(23,35,30,.92)!important;color:#C3D6CB!important;border-color:#25402F!important;}
html[data-theme="dark"] footer.fixed-bottom *,
html[data-theme="dark"] .fixed-bottom *{color:#C3D6CB!important;}
html[data-theme="dark"] footer.fixed-bottom a,
html[data-theme="dark"] .fixed-bottom a{color:#5BD9A0!important;}
html[data-theme="dark"] .form-control,
html[data-theme="dark"] .form-select{background:#1B2B24!important;color:#E8F3EE!important;border-color:#2C4636!important;}
html[data-theme="dark"] .form-control::placeholder{color:#6E8479!important;}
html[data-theme="dark"] .bg-white,
html[data-theme="dark"] .bg-body{background:#17231E!important;}
html[data-theme="dark"] .bg-light{background:#1B2B24!important;}
html[data-theme="dark"] .border{ border-color:#25402F!important;}
/* 登录页：左品牌区是深绿渐变（保持），右表单区 #f8fafc 白底要转深底深字 */
html[data-theme="dark"] .login-container{background:linear-gradient(135deg,#0A2B1D 0%,#0E3B28 35%,#124D34 70%,#155C3E 100%);}
html[data-theme="dark"] .login-form-section{background:#121E19!important;}
html[data-theme="dark"] .login-body,
html[data-theme="dark"] .login-card,
html[data-theme="dark"] .login-wrapper .login-form,
html[data-theme="dark"] .login-right,
html[data-theme="dark"] .form-inner{background:transparent!important;color:#E8F3EE!important;}
html[data-theme="dark"] .login-body h2,
html[data-theme="dark"] .login-body .login-title,
html[data-theme="dark"] .login-sub{color:#E8F3EE!important;}
/* 登录区显式硬编码色全部转深色系（原文：h3 #0f172a / p #64748b / label #334155 / input #fff 底） */
html[data-theme="dark"] .form-welcome h3{color:#F2F8F5!important;}
html[data-theme="dark"] .form-welcome p{color:#A7BCB1!important;}
html[data-theme="dark"] .form-field label{color:#D3E3D9!important;}
html[data-theme="dark"] .label-icon{color:#4FD79A!important;}
html[data-theme="dark"] .input-container input{background:#1B2B24!important;color:#E8F3EE!important;border-color:#2C4636!important;}
html[data-theme="dark"] .input-container input::placeholder{color:#6E8479!important;}
html[data-theme="dark"] .input-container input:hover{border-color:#3A6B52!important;}
html[data-theme="dark"] .input-container input:focus{border-color:#1FA56A!important;box-shadow:0 0 0 4px rgba(31,165,106,0.18)!important;}
/* 游客模式 / 辅助链接 / 底部提示 等浅底浅字 */
html[data-theme="dark"] .guest-btn,
html[data-theme="dark"] .login-footer,
html[data-theme="dark"] .login-divider,
html[data-theme="dark"] .form-tip,
html[data-theme="dark"] .form-hint{color:#A7BCB1!important;}
html[data-theme="dark"] .login-input{background:#1B2B24!important;color:#E8F3EE!important;border-color:#2C4636!important;}
html[data-theme="dark"] .login-input::placeholder{color:#6E8479!important;}
/* error toast / 表单校验提示 的浅底块 */
html[data-theme="dark"] .form-error,
html[data-theme="dark"] .error-msg{background:#3A1F22!important;color:#FFB4B4!important;border-color:#5C2E33!important;}
/* 品牌绿在深底提亮，避免墨绿压墨绿 */
html[data-theme="dark"] .text-success,
html[data-theme="dark"] .text-primary{color:#4FD79A!important;}
html[data-theme="dark"] .btn-outline-primary{--bs-btn-color:#4FD79A;--bs-btn-border-color:#3A6B52;color:#4FD79A!important;}
html[data-theme="dark"] .brand-subtitle{color:#9CB3A7!important;}
/* 图表：深底上刻度线/文字要换成浅色，否则不可见 */
html[data-theme="dark"] svg text{fill:#C3D6CB!important;}
html[data-theme="dark"] canvas{filter:none;}
/* 侧边导航：旧规则用白底下黑字，暗色下转深底 */
html[data-theme="dark"] .sidebar,
html[data-theme="dark"] .module-nav{background:#14201A!important;}
html[data-theme="dark"] .nav-link{color:#CFE0D6!important;}
html[data-theme="dark"] .nav-link.active{background:#1FA56A!important;color:#fff!important;}
/* ---- performance 自定义组件深色映射（2026-09-16 复盘补）----
   这些是本模块自写的白底组件（background:white / #fff 写死），
   Bootstrap 暗色变量覆盖不到，必须按类名逐个压深。 */
html[data-theme="dark"] .batch-toolbar{background:#17231E!important;box-shadow:0 6px 18px rgba(0,0,0,.35)!important;color:#E8F3EE!important;border:1px solid #25402F!important;}
html[data-theme="dark"] .custom-months-panel{background:#17231E!important;border-color:#2C4636!important;color:#E8F3EE!important;}
html[data-theme="dark"] .stat-card{background:#17231E!important;border-color:#25402F!important;}
html[data-theme="dark"] .period-pill{background:#1B2B24!important;color:#CFE0D6!important;border-color:#2C4636!important;}
html[data-theme="dark"] .period-pill.active{background:#1FA56A!important;color:#fff!important;border-color:#1FA56A!important;}
html[data-theme="dark"] .metric-label{color:#A7BCB1!important;}
html[data-theme="dark"] .metric-value{color:#F2F8F5!important;}
/* 登录页辅助元素（游客按钮 / 分隔线 / 提示语） */
html[data-theme="dark"] .btn-guest{background:#1B2B24!important;color:#D3E3D9!important;border-color:#2C4636!important;}
html[data-theme="dark"] .btn-guest:hover{background:#22352C!important;border-color:#3A6B52!important;}
html[data-theme="dark"] .guest-hint{color:#8FA69A!important;}
html[data-theme="dark"] .divider-text{color:#8FA69A!important;}
html[data-theme="dark"] .form-divider:before,
html[data-theme="dark"] .form-divider:after{background-color:#2C4636!important;}
/* Bootstrap 描边按钮：深色下透明底 + 亮字，确保在深底可见 */
html[data-theme="dark"] .btn-outline-secondary,
html[data-theme="dark"] .btn-outline-primary,
html[data-theme="dark"] .btn-outline-warning,
html[data-theme="dark"] .btn-outline-info{background:transparent!important;}
html[data-theme="dark"] .btn-outline-secondary{--bs-btn-color:#C3D6CB;--bs-btn-border-color:#3A5748;--bs-btn-hover-bg:#2A3F35;--bs-btn-hover-color:#E8F3EE;}
html[data-theme="dark"] .btn-outline-primary{--bs-btn-color:#5BD9A0;--bs-btn-border-color:#2C6B4C;--bs-btn-hover-bg:#1FA56A;--bs-btn-hover-color:#fff;}
html[data-theme="dark"] .btn-outline-warning{--bs-btn-color:#F0C94A;--bs-btn-border-color:#6B5417;--bs-btn-hover-bg:#8A6C1A;--bs-btn-hover-color:#141309;}
"""


RISK = COMMON + DARK_COMMON + """
/* risk-lite：stat-pill 内联 min-width 撑破文档流（手机档改为纵向堆叠）+ 顶栏可见性 */
@media (max-width:900px){
  .stat-pill[style]{min-width:0!important;flex:1 1 100%!important;}
}
@media (max-width:760px){
  #appVersionBadge{display:none!important;}
  .topbar{gap:8px!important;padding:6px 12px!important;}
  .topbar .logo span{max-width:44vw;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  #btnGlobalRefresh,.btn-theme-toggle,.btn-briefing{padding:6px 9px!important;font-size:12px!important;}
}
@media (max-width:600px){
  .topbar{flex-wrap:wrap;}
  .topbar .breadcrumb{display:none!important;}
}
/* ---- risk-lite 深色专项（2026-09-16）----
   该模块虽多处带 data-theme 标记，但没有任何暗色规则 → 深色下只有边框变。
   它用的是自定义类 + 深蓝灰（#2D3E5C / #9FB3CC），按语义类补暗色。 */
html[data-theme="dark"]{
  --bg:#0E1622;--bg-card:#151F2E;--text:#E6EDF6;--text2:#95A6BF;--border:#24344A;
}
html[data-theme="dark"] body{background:#0E1622!important;color:#E6EDF6!important;}
html[data-theme="dark"] .topbar{background:#151F2E!important;border-bottom-color:#24344A!important;}
html[data-theme="dark"] .topbar .logo span,
html[data-theme="dark"] .breadcrumb{color:#E6EDF6!important;}
html[data-theme="dark"] .stat-pill{background:#182335!important;border-color:#24344A!important;color:#E6EDF6!important;}
html[data-theme="dark"] .stat-pill .sp-val,
html[data-theme="dark"] .stat-pill b{color:#5FE0A6!important;}
html[data-theme="dark"] .card,
html[data-theme="dark"] .risk-card,
html[data-theme="dark"] .panel{background:#151F2E!important;border-color:#24344A!important;color:#E6EDF6!important;}
html[data-theme="dark"] .panel-h,
html[data-theme="dark"] .card-h{background:#1A2637!important;color:#E6EDF6!important;border-color:#24344A!important;}
html[data-theme="dark"] input,
html[data-theme="dark"] select,
html[data-theme="dark"] textarea{background:#1A2637!important;color:#E6EDF6!important;border-color:#2B3E57!important;}
html[data-theme="dark"] .text-muted,
html[data-theme="dark"] .meta{color:#95A6BF!important;}
html[data-theme="dark"] .bg-white{background:#151F2E!important;}
html[data-theme="dark"] .bg-light,
html[data-theme="dark"] .bg-gray-50{background:#1A2637!important;}
html[data-theme="dark"] .border{ border-color:#24344A!important;}
html[data-theme="dark"] .btn-briefing,
html[data-theme="dark"] .btn-theme-toggle{background:#1A2637!important;color:#E6EDF6!important;border-color:#2B3E57!important;}
/* 风险等级语义色：深底上提亮，保留警示可读性 */
html[data-theme="dark"] .lv-high,
html[data-theme="dark"] .risk-high{color:#FF7A70!important;}
html[data-theme="dark"] .lv-mid,
html[data-theme="dark"] .risk-mid{color:#FFB95E!important;}
html[data-theme="dark"] .lv-low,
html[data-theme="dark"] .risk-low{color:#5FE0A6!important;}

/* ---- risk-lite 响应式专项（2026-09-17 审计：手机/平板页面级横向溢出 272~349px）----
   根因①：顶栏右侧操作组（刷新/黑白切换/简报/天气…）不换行，把布局视口撑到 669px；
   根因②：file:// 协议横幅长文案不换行；根因③：小按钮/冲突弹窗越界。 */
@media (max-width:1024px){
  .topbar{flex-wrap:wrap;height:auto;min-height:var(--topbar-h,52px);row-gap:4px;padding-top:6px;padding-bottom:6px;}
  .topbar .right{flex-wrap:wrap;row-gap:6px;justify-content:flex-end;}
  .weather-update-panel{max-width:min(92vw,360px);}
}
@media (max-width:900px){
  #fileProtocolBanner{padding:8px 12px!important;font-size:12px!important;}
  #fileProtocolBanner span{white-space:normal!important;overflow-wrap:anywhere!important;}
  #fileProtocolBanner button{margin-left:8px!important;margin-top:4px;}
  #weatherFreqSelect,#routeBaseSelect,#mapRouteSelect,
  #settingsBriefingTime,#settingsFeishuUserId{font-size:16px!important;}
  select,textarea,
  input[type="text"],input[type="time"]{font-size:16px!important;}
}
@media (max-width:760px){
  .sched-check-modal{width:min(92vw,560px)!important;max-width:92vw!important;}
  /* 关闭钮/翻页钮/无类名小按钮统一抬触控目标（审计实测 12~32px 难点准） */
  .btn-close{min-width:38px;min-height:38px;font-size:18px;}
  .btn{min-width:38px;min-height:36px;}
  button{min-height:36px;}
  .drawer .head .btn-toggle{min-width:38px;min-height:38px;}
  .icon-btn{min-width:40px;min-height:40px;}
  .leaflet-control-zoom a{width:34px!important;height:34px!important;line-height:30px!important;font-size:18px;}
}
"""

DAILY = COMMON + DARK_COMMON + """
/* daily：快捷标签/品类按钮触控目标（2026-09-17 响应式审计：23~28px 高难点准） */
@media (max-width:760px){
  .tag{min-height:36px;padding:6px 12px;font-size:.78rem;}
  .cat{min-height:36px;}
}
"""

ISSUES = COMMON + DARK_COMMON + """
/* issues：表单字号下限（2026-09-17 审计：14px 会触发 iOS 聚焦缩放；含 768 平板档） */
@media (max-width:900px){
  #issLoc,#issMsg{font-size:16px!important;}
  select,textarea,input{font-size:16px!important;}
}
"""

KBADMIN = COMMON + DARK_COMMON + """
/* kb-admin：tab/工具按钮触控 + 下拉字号（2026-09-17 响应式审计；含 768 平板档） */
@media (max-width:900px){
  select{min-height:42px;font-size:16px!important;}
  #targetLib{font-size:16px!important;}
}
@media (max-width:760px){
  .kb-tab{min-height:40px;padding:8px 10px;}
  .tbtn{min-height:38px;}
}
"""

# 壳层顶栏（index / spring-assistant / 离线完整版 共用 chrome）
SHELL = """
/* ---- 壳层顶栏响应式收纳（2026-09-17 响应式审计）----
   768 档 actions 溢出 +114px：先收节日/节气 chip；320 档 +47px：再收时钟；
   触屏设备补齐 40px+ 触控目标（bk-btn/theme-btn/mega-btn/mod-tab）。 */
@media (max-width:960px){
  .actions .sys-clock .sc-tag{display:none;}
}
@media (max-width:760px){
  .actions .net-status{display:none;}
  .actions{gap:7px;}
}
@media (max-width:480px){
  .actions .sys-clock{display:none;}
}
@media (pointer:coarse){
  /* 2026-09-19 设计审核 P0-B：原 40/42px 低于 44px 触摸底线，统一到 44px。
     非触摸端仍由壳层基础样式控制（视觉更紧凑），此处只兜触摸设备。 */
  .bk-btn{min-width:44px;min-height:44px;}
  .theme-btn{min-width:44px;min-height:44px;}
  #megaBtn{min-width:44px;min-height:44px;}
  .mod-tab{min-height:44px;}
}
"""

# beauty 品牌色收拢映射（Tailwind 翡翠绿 -> 春秋绿系，字面量替换）
BEAUTY_SWAPS = [
    ('#10b981', '#1fa56a'),
    ('#059669', '#148453'),
    ('#047857', '#0c5f3a'),
    ('#ecfdf5', '#f4f9f6'),
    ('#d1fae5', '#e8f3ee'),
    ('#17301f', '#0f2a1f'),
]

TARGETS = {
    'qa.html': QA,
    'beauty.html': BEAUTY,
    'quiz.html': QUIZ,
    'manual.html': MANUAL,
    'report.html': REPORT,
    'issues.html': ISSUES,
    'medical.html': MEDICAL,
    'performance.html': PERF,
    'risk-lite.html': RISK,
    'index.html': SHELL,
    'spring-assistant.html': COMMON + DARK_COMMON + SHELL,
    '客舱小助手（离线完整版）.html': COMMON + DARK_COMMON + SHELL,
    'daily.template.html': DAILY,
    'kb-admin.template.html': KBADMIN,
    'daily.html': DAILY,
    'kb-admin.html': KBADMIN,
    # cc-home.html 刻意跳过：桌面三栏为 2026-09-14 手调定稿，不在本轮范围
}

RX_BLOCK = re.compile(re.escape('<style id="uxPolish">' + BEGIN) + r'.*?' + re.escape(END + '</style>') + r'\n?', re.S)


def read(p):
    return io.open(p, encoding='utf-8').read()


def write(p, s):
    blob = s.encode('utf-8')  # 先校验可编码，防 0 字节事故
    blob.decode('utf-8')
    with io.open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def block(css):
    return '<style id="uxPolish">' + BEGIN + css + END + '</style>\n'


def find_real_head_end(src):
    """结构化扫描：跳过完整的 <script>/<style> 区块后，第一处 </head> 即真实文档头。
    内嵌库（如 SheetJS）的 JS 字符串里含 '</head><body>' 全文档模板，位置启发式必误判。"""
    low = src.lower()
    i, n = 0, len(src)
    rx = re.compile(r'<(/?)(script|style)\b|</head>', re.I)
    while i < n:
        m = rx.search(src, i)
        if not m:
            return -1
        if m.group(0).lower() == '</head>':
            return m.start()
        name = m.group(2).lower()
        close = low.find('</' + name + '>', m.end())
        if close == -1:
            return -1
        i = close + len('</' + name + '>')
    return -1


def main():
    if '--check' in sys.argv:
        missing = [f for f in TARGETS if BEGIN not in read(f)]
        if missing:
            print('[ux-polish][FAIL] 缺少标记块: %s' % ', '.join(missing)); raise SystemExit(1)
        print('[ux-polish] check PASS: %d 个文件均含标记块' % len(TARGETS)); return

    if not os.path.isdir(BAK):
        os.makedirs(BAK)
    total_swaps = 0
    for name, css in TARGETS.items():
        src = read(name)
        n0 = len(src)
        # 1) 剥离旧块（幂等）
        src, nrm = RX_BLOCK.subn('', src)
        # 2) beauty 品牌色收拢
        swaps = []
        if name == 'beauty.html':
            for old, new in BEAUTY_SWAPS:
                cnt = len(re.findall(re.escape(old), src, re.I))
                if cnt:
                    src = re.sub(re.escape(old), new, src, flags=re.I)
                    swaps.append('%s->%s×%d' % (old, new, cnt))
        # 3) 注入：结构化扫描定位真实文档头（先剥离旧块，再扫描干净文本）。
        #    performance.html 真实 </head> 缺失（HTML5 容许省略），退化为文末 </body> 前注入。
        src_base = src  # 剥离旧块后的干净文本
        pos = find_real_head_end(src_base)
        if pos < 0:
            last = None
            for last in re.finditer(re.escape('</body>'), src_base, re.I):
                pass
            pos = last.start() if last else len(src_base)
        src = src_base[:pos] + block(css) + src_base[pos:]
        # 4) 长度守卫：注入后必须恰好比剥离后多出一个块（幂等复跑、新旧块长短不一均可通过）
        n1 = len(src)
        assert n1 == len(src_base) + len(block(css)), '%s: 注入后长度异常' % name
        # 5) 备份 + 写盘
        bpath = os.path.join(BAK, name)
        if not os.path.exists(bpath):
            shutil.copy2(name, bpath)
        write(name, src)
        total_swaps += len(swaps)
        print('[ok] %-24s %8.1fKB -> %8.1fKB  旧块×%d  %s'
              % (name, n0 / 1024.0, n1 / 1024.0, nrm, ('色收拢: ' + ' '.join(swaps)) if swaps else ''))
    print('[done] 注入 %d 个文件，品牌色替换 %d 组' % (len(TARGETS), total_swaps))


if __name__ == '__main__':
    main()
