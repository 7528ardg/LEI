# -*- coding: utf-8 -*-
"""客舱小助手 · 导航升级注入（20260917）
--------------------------------------------------------------------------------
9 种常用导航因地制宜落地（壳层唯一来源 index.html，同步两份内嵌 TEMPLATE）：
  #1 悬浮吸顶导航  顶栏浮岛化：圆角悬浮卡片 + 毛玻璃 + 滚动后阴影加深
  #3 面包屑导航    顶栏内轻面包屑：客舱小助手 › 模块 › 子页（子页可由模块上报）
  #4 二级下拉导航  桌面 hover 模块页签：弹出该模块简介 + 快捷子入口（可深跳）
  #5 巨型菜单      「⊞ 全部应用」多列分组面板：12 模块 3 大组，卡片含子入口
  #9 滚动收缩导航  监听活动模块 iframe 滚动：下滑顶栏收缩变实色，回顶还原
  （#2 侧边栏 / #6 汉堡抽屉 / #7 全屏遮罩 / #8 锚点导航：系统已有等效实现，
    见 _audit_nav_20260917.md 分析，不重复引入）

同步目标：
  - index.html        壳层唯一来源
  - _gzip_build.py    TEMPLATE（9 模块单文件壳）
  - _build_4in1.py    TEMPLATE（10 模块离线壳）
  - beauty.html       深跳桥：cc:nav-jump → switchTab(view)
  - manual.html       深跳桥：cc:nav-jump → ccGoView(view)

幂等：重复运行结果一致（标记块 + 锚定注入 + 长度守卫）。
用法：python _apply_nav_20260917.py [--check]
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.abspath(__file__))

MARK_CSS = '__NAV_DESIGN_20260917_CSS__'
MARK_JS = '__NAV_DESIGN_20260917_JS__'
MARK_BRIDGE = '__NAV_BRIDGE_20260917__'

SHELL_FILES = ['index.html', '_gzip_build.py', '_build_4in1.py']

# ============================================================================
# CSS 块：#1 浮岛 / #3 面包屑 / #4 二级下拉 / #5 巨型菜单 / #9 滚动收缩
# 全部使用壳层既有 CSS 变量，深色主题自动跟随；仅补阴影类暗色微调
# ============================================================================
CSS_BLOCK = r'''
/*__NAV_DESIGN_20260917_CSS__BEGIN —— 导航升级（源 index.html，勿直接改产物）*/
/* --- #1 悬浮吸顶：顶栏浮岛化（圆角悬浮卡片，始终吸顶） --- */
.topbar{top:10px;left:12px;right:12px;border:1px solid var(--border);border-radius:18px;box-shadow:0 6px 24px rgba(15,42,31,.08);transition:background .3s,box-shadow .3s,height .28s cubic-bezier(.32,.72,.34,1),top .28s cubic-bezier(.32,.72,.34,1),left .28s,right .28s;}
html[data-theme="dark"] .topbar{box-shadow:0 8px 26px rgba(0,0,0,.5);}
.sys-area{top:calc(var(--topbar-h) + 16px);}
/* --- #9 滚动收缩：模块内容下滑后顶栏收紧变实色，回到顶部还原 --- */
html.nav-scrolled .topbar{top:6px;height:48px;border-radius:14px;box-shadow:0 12px 30px rgba(15,42,31,.18);}
html[data-theme="dark"] .nav-scrolled .topbar{box-shadow:0 12px 30px rgba(0,0,0,.55);}
html.nav-scrolled .brand-sub,html.nav-scrolled .cr-root,html.nav-scrolled .cr-sep-first{display:none;}
html.nav-scrolled .net-status,html.nav-scrolled .sys-clock{padding:3px 8px;font-size:.7rem;}
/* --- #3 面包屑：安静的位置指示（无底框、窄上限；仅宽屏展示） ---
   2026-09-19：顶栏只剩 3 个板块，当前板块若在顶栏可见则面包屑纯属重复 → 由 syncCrumb 隐藏 */
.shell-crumb{display:none;align-items:center;flex-shrink:0;padding:7px 6px;font-size:.78rem;color:var(--text2);white-space:nowrap;max-width:22vw;overflow:hidden;transition:opacity .2s;}
@media(min-width:1101px){.shell-crumb{display:flex;}}
.shell-crumb .cr-item{font-weight:700;overflow:hidden;text-overflow:ellipsis;}
.shell-crumb .cr-item.link{cursor:pointer;color:var(--primary);}
.shell-crumb .cr-item.link:hover{text-decoration:underline;}
.shell-crumb .cr-mod{color:var(--text);}
.shell-crumb .cr-sep{color:var(--text3);margin:0 6px;flex-shrink:0;}
.shell-crumb .cr-sub{color:var(--gold);font-weight:700;}
/* --- #4 二级下拉：模块页签 hover 弹出简介 + 快捷子入口（桌面精确指针） --- */
.nav-drop{position:fixed;z-index:180;width:300px;max-height:min(70vh,460px);overflow-y:auto;-webkit-overflow-scrolling:touch;background:var(--bg-card);border:1px solid var(--border);border-radius:16px;box-shadow:0 18px 48px rgba(15,42,31,.18);padding:14px;opacity:0;transform:translateY(-6px);pointer-events:none;transition:opacity .18s ease,transform .18s ease;}
.nav-drop.show{opacity:1;transform:translateY(0);pointer-events:auto;}
.nav-drop .nd-name{font-weight:800;color:var(--text);font-size:.92rem;display:flex;align-items:center;gap:8px;}
.nav-drop .nd-desc{font-size:.74rem;color:var(--text2);line-height:1.65;margin:7px 0 9px;}
.nav-drop .nd-sub{display:flex;align-items:center;gap:7px;width:100%;padding:7px 10px;border-radius:10px;border:none;background:transparent;cursor:pointer;font-size:.78rem;font-weight:600;color:var(--text);font-family:var(--font-sans);transition:background .15s,color .15s;text-align:left;}
.nav-drop .nd-sub:hover{background:var(--primary-mist);color:var(--primary);}
/* --- #5 巨型菜单：「⊞ 全部应用」分组多列面板（桌面点击展开） --- */
.mega-btn{display:none;align-items:center;justify-content:center;width:36px;height:36px;border-radius:12px;border:1px solid var(--border);background:var(--bg);cursor:pointer;color:var(--text2);flex-shrink:0;transition:all .2s;font-family:var(--font-sans);}
.mega-btn:hover{border-color:var(--primary);color:var(--primary);background:var(--primary-soft);transform:scale(1.06);}
@media(min-width:721px){.mega-btn{display:flex;}}
@media(max-width:720px){.topbar{left:6px;right:6px;top:6px;border-radius:14px;}.sys-area{top:calc(var(--topbar-h) + 10px);}}
.mega-mask{position:fixed;inset:0;background:rgba(9,20,15,.44);z-index:150;opacity:0;pointer-events:none;transition:opacity .25s;-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px);}
.mega-mask.show{opacity:1;pointer-events:auto;}
html[data-theme="dark"] .mega-mask{background:rgba(0,0,0,.62);}
.mega-panel{position:fixed;z-index:160;top:calc(var(--topbar-h) + 26px);left:50%;transform:translate(-50%,-12px) scale(.985);width:min(920px,94vw);max-height:min(78vh,640px);overflow-y:auto;-webkit-overflow-scrolling:touch;background:var(--bg-card);border:1px solid var(--border);border-radius:20px;box-shadow:0 24px 64px rgba(15,42,31,.22);padding:16px 18px 6px;opacity:0;visibility:hidden;pointer-events:none;transition:opacity .2s ease,transform .2s ease,visibility 0s linear .2s;}
.mega-panel.show{opacity:1;visibility:visible;pointer-events:auto;transform:translate(-50%,0) scale(1);transition:opacity .22s ease,transform .3s cubic-bezier(.22,1.28,.36,1);}
html[data-theme="dark"] .mega-panel{box-shadow:0 24px 64px rgba(0,0,0,.55);}
.mega-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;}
.mega-title{font-size:1rem;font-weight:800;color:var(--text);}
.mega-group-label{font-size:.72rem;font-weight:800;color:var(--text3);letter-spacing:1px;margin:12px 4px 8px;display:flex;align-items:center;gap:8px;}
.mega-group-label::after{content:'';flex:1;height:1px;background:var(--border);}
.mega-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;}
@media(max-width:1100px){.mega-grid{grid-template-columns:repeat(2,1fr);}}
.mega-card{display:flex;flex-direction:column;gap:5px;padding:12px;border:1px solid var(--border);border-radius:14px;background:var(--bg);cursor:pointer;transition:all .18s;text-align:left;font-family:var(--font-sans);}
.mega-card:hover{border-color:var(--primary);background:var(--primary-mist);transform:translateY(-2px);box-shadow:var(--shadow);}
.mega-card.active{border-color:var(--primary);background:var(--primary-soft);}
.mega-card .mc-top{display:flex;align-items:center;gap:8px;font-weight:800;color:var(--text);font-size:.9rem;}
.mega-card .mc-ic{font-size:1.2rem;line-height:1;}
.mega-card .mc-desc{font-size:.72rem;color:var(--text2);line-height:1.55;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.mega-subs{display:flex;flex-wrap:wrap;gap:4px;margin-top:3px;}
.mega-sub{font-size:.68rem;padding:3px 9px;border-radius:8px;background:var(--primary-soft);color:var(--primary);border:none;cursor:pointer;font-weight:700;font-family:var(--font-sans);transition:all .15s;}
.mega-sub:hover{background:var(--grad-primary);color:#fff;}
.mega-foot{padding:12px 4px 8px;display:flex;justify-content:center;}
/*__NAV_DESIGN_20260917_CSS__END*/
'''

# ============================================================================
# HTML：#3 面包屑（插在 module-tabs 之前）
# ============================================================================
# 2026-09-19 改版：顶栏去品牌 + 只显 3 板块后，面包屑降级为「安静的位置指示」
# （去掉「客舱小助手 ›」前缀——它与品牌区重复，且宽度吃紧；只留 当前模块 › 子页）
CRUMB_HTML = r'''<nav class="shell-crumb" id="shellCrumb" aria-label="当前位置"><span class="cr-item cr-mod" id="crumbMod">你问我答</span><span class="cr-sep" id="crumbSep2" style="display:none">›</span><span class="cr-item cr-sub" id="crumbSub" style="display:none"></span></nav>
  '''

# ============================================================================
# HTML：#5 巨型菜单触发按钮（插在 .actions 首位）
# ============================================================================
MEGA_BTN_HTML = ''   # 2026-09-19：右侧工具组不再放 ⊞（与页签行的「全部应用」重复入口）；
                    # 保留 strip 逻辑用于清理历史产物，不再注入新按钮。

# ============================================================================
# JS 块：元数据 + 巨型菜单 + 二级下拉 + 面包屑 + 滚动收缩
# ============================================================================
JS_BODY = r'''(function(){
'use strict';
if(window.__CC_NAV_DESIGN__) return; window.__CC_NAV_DESIGN__ = true;

/* ---- 12 模块元数据（#5 巨型菜单 / #4 二级下拉共用；subs 为可深跳子入口） ---- */
var MODS = {
  home:        {name:'CC 之家',   icon:'🏠', group:'乘务服务', desc:'24 位角色乘务员房间、互动对话与钢琴角。', subs:[]},
  qa:          {name:'你问我答',  icon:'💬', group:'乘务服务', desc:'知识库问答：跨库强证据、联想记忆与 AI 兜底。', subs:[]},
  quiz:        {name:'培训考核',  icon:'📚', group:'训练成长', desc:'题库练习、模拟考核与错题回顾。', subs:[]},
  performance: {name:'绩效管理',  icon:'📊', group:'训练成长', desc:'个人与分队绩效视图。', subs:[]},
  beauty:      {name:'美妆话术',  icon:'💄', group:'训练成长', desc:'跨境美妆产品库与销售话术工作台。', subs:[
                 {k:'browse',label:'产品浏览'},{k:'recommend',label:'需求推荐'},{k:'skin',label:'肤质筛选'},{k:'compare',label:'同品比拼'},
                 {k:'script',label:'话术生成'},{k:'scriptLib',label:'话术库管理'},{k:'aiChat',label:'AI 对话练习'},
                 {k:'competitor',label:'竞品分析'},{k:'customer',label:'客户管理'},{k:'favorites',label:'我的收藏'}]},
  risk:        {name:'风险预警',  icon:'⚠️', group:'运营管理', desc:'总部—分队—板块三级风险驾驶舱。', subs:[]},
  medical:     {name:'医疗急救',  icon:'🚑', group:'乘务服务', desc:'机上医疗事件处置速查。', subs:[]},
  daily:       {name:'日常问题',  icon:'❓', group:'乘务服务', desc:'销售·配送·病假·体检·电子发票速查。', subs:[]},
  manual:      {name:'手册奖惩',  icon:'📕', group:'运营管理', desc:'《客舱服务部管理手册》奖惩条款速查。', subs:[
                 {k:'query',label:'扣分查询'},{k:'scores',label:'分数说明'},{k:'promo',label:'晋级降级'},{k:'fav',label:'我的收藏'}]},
  report:      {name:'事件报告',  icon:'🗂', group:'运营管理', desc:'机上事件结构化上报。', subs:[]},
  kbadmin:     {name:'库管理',    icon:'📇', group:'运营管理', desc:'知识库 / 商品库维护与数据包中心。', subs:[]},
  issues:      {name:'问题反馈',  icon:'🐞', group:'运营管理', desc:'向开发者反馈问题与建议。', subs:[]}
};
var GROUPS = ['乘务服务','训练成长','运营管理'];

function curMod(){ var m=''; try{ m = currentMod; }catch(e){ try{ m = window.currentMod; }catch(e2){} } return m||''; }

/* ---------- #3 面包屑 ---------- */
function setCrumbSub(text){
  var el = document.getElementById('crumbSub');
  var sep = document.getElementById('crumbSep2');
  if(!el) return;
  if(text){ el.textContent = text; el.style.display = ''; if(sep) sep.style.display = ''; }
  else { el.textContent = ''; el.style.display = 'none'; if(sep) sep.style.display = 'none'; }
}
function syncCrumb(modId){
  var el = document.getElementById('crumbMod');
  if(!el) return;
  var m = MODS[modId];
  el.textContent = m ? (m.icon + ' ' + m.name) : modId;
  setCrumbSub('');   /* 子页由 navJumpTo 延迟补写（等页签观察者微任务结束后） */
  /* 2026-09-19：顶栏只保留 3 个板块。当前板块若在顶栏可见，面包屑与页签重复且挤占宽度 → 隐藏；
     只有在顶栏看不到的板块（美妆话术/日常问题/手册奖惩…）才用面包屑提示位置。 */
  var bar = document.getElementById('shellCrumb');
  if(bar){
    var t = document.querySelector('.module-tabs .mod-tab[data-mod="' + modId + '"]');
    var visibleInTabs = !!(t && t.getBoundingClientRect().width > 0);
    bar.style.display = visibleInTabs ? 'none' : '';
  }
}
function subLabel(modId, view){
  var m = MODS[modId]; if(!m) return '';
  for(var i=0;i<m.subs.length;i++){ if(m.subs[i].k === view) return m.subs[i].label; }
  return '';
}
/* 模块切换 → 面包屑与收缩态同步（MutationObserver 监听页签 active 变化，不动壳层原函数） */
function watchTabs(){
  var tabs = document.getElementById('moduleTabs');
  if(!tabs || !window.MutationObserver) { setTimeout(syncInit, 600); return; }
  var mo = new MutationObserver(function(){
    var act = document.querySelector('.mod-tab.active');
    if(act) syncCrumb(act.getAttribute('data-mod')||'');
  });
  mo.observe(tabs, {attributes:true, attributeFilter:['class'], subtree:true});
  syncInit();
}
function syncInit(){
  var act = document.querySelector('.mod-tab.active');
  if(act) syncCrumb(act.getAttribute('data-mod')||'');
  setTimeout(function(){ /* 模块切换后滚动位置恢复完毕再校准收缩态 */
    var sc = activeScrollY();
    document.documentElement.classList.toggle('nav-scrolled', sc > 64);
  }, 380);
}

/* ---------- #4 二级下拉（桌面精确指针设备） ---------- */
var dropEl = null, dropHideTimer = null, dropShowTimer = null;
function hoverCapable(){
  try{ return window.matchMedia('(hover: hover) and (pointer: fine)').matches && window.innerWidth > 1100; }
  catch(e){ return false; }
}
function buildDrop(){
  if(dropEl) return dropEl;
  dropEl = document.createElement('div');
  dropEl.className = 'nav-drop'; dropEl.id = 'navDrop';
  dropEl.addEventListener('mouseenter', function(){ if(dropHideTimer){ clearTimeout(dropHideTimer); dropHideTimer = null; } });
  dropEl.addEventListener('mouseleave', scheduleDropHide);
  /* 子入口点击 → 深跳（事件委托；必须在 buildDrop 内绑定——dropEl 首次 hover 才存在） */
  dropEl.addEventListener('click', function(ev){
    var b = ev.target.closest ? ev.target.closest('.nd-sub') : null;
    if(!b) return;
    var mod = b.getAttribute('data-mod'), view = b.getAttribute('data-view');
    dropEl.classList.remove('show');
    if(view) navJumpTo(mod, view); else { try{ switchModule(mod); }catch(e){} }
  });
  document.body.appendChild(dropEl);
  return dropEl;
}
function showDropFor(tab){
  var id = tab.getAttribute('data-mod')||''; var m = MODS[id];
  if(!m) return;
  var d = buildDrop();
  var h = '<div class="nd-name">' + m.icon + ' ' + m.name + '</div>';
  h += '<div class="nd-desc">' + m.desc + '</div>';
  if(m.subs && m.subs.length){
    for(var i=0;i<m.subs.length;i++){
      h += '<button class="nd-sub" data-mod="' + id + '" data-view="' + m.subs[i].k + '">' + m.subs[i].label + '<span style="margin-left:auto;opacity:.55">›</span></button>';
    }
  } else {
    h += '<button class="nd-sub" data-mod="' + id + '" data-view="">进入模块<span style="margin-left:auto;opacity:.55">›</span></button>';
  }
  d.innerHTML = h;
  var r = tab.getBoundingClientRect();
  var left = Math.min(r.left, window.innerWidth - 316);
  d.style.left = Math.max(12, left) + 'px';
  d.style.top = (r.bottom + 10) + 'px';
  d.classList.add('show');
}
function scheduleDropHide(){
  if(dropHideTimer) clearTimeout(dropHideTimer);
  dropHideTimer = setTimeout(function(){ if(dropEl) dropEl.classList.remove('show'); }, 240);
}
function bindDrops(){
  if(!hoverCapable()) return;
  var tabs = document.querySelectorAll('.mod-tab');
  for(var i=0;i<tabs.length;i++){
    (function(t){
      t.addEventListener('mouseenter', function(){
        if(dropShowTimer) clearTimeout(dropShowTimer);
        dropShowTimer = setTimeout(function(){ showDropFor(t); }, 90);
      });
      t.addEventListener('mouseleave', function(){
        if(dropShowTimer){ clearTimeout(dropShowTimer); dropShowTimer = null; }
        scheduleDropHide();
      });
    })(tabs[i]);
  }
  document.addEventListener('click', function(ev){
    if(dropEl && dropEl.classList.contains('show')){
      var inDrop = false;
      try{ inDrop = dropEl.contains(ev.target) || ev.target.closest && ev.target.closest('.mod-tab') !== null; }catch(e){}
      if(!inDrop) dropEl.classList.remove('show');
    }
  });
}

/* ---------- #5 巨型菜单 ---------- */
var megaMask = null, megaPanel = null;
function buildMega(){
  if(megaPanel) return megaPanel;
  megaMask = document.createElement('div');
  megaMask.className = 'mega-mask'; megaMask.id = 'megaMask';
  megaMask.addEventListener('click', closeMegaMenu);
  megaPanel = document.createElement('div');
  megaPanel.className = 'mega-panel'; megaPanel.id = 'megaPanel';
  megaPanel.setAttribute('role', 'dialog'); megaPanel.setAttribute('aria-label', '全部应用');
  var cm = curMod();
  var h = '<div class="mega-head"><div class="mega-title">🧰 工具区 · 全部板块与设置（' + Object.keys(MODS).length + ' 个模块 / ' + GROUPS.length + ' 组）</div>';
  h += '<button class="modal-x" id="megaCloseX" title="关闭" aria-label="关闭">✕</button></div>';
  for(var g=0; g<GROUPS.length; g++){
    var grp = GROUPS[g];
    h += '<div class="mega-group-label">' + grp + '</div><div class="mega-grid">';
    for(var id in MODS){
      var m = MODS[id]; if(m.group !== grp) continue;
      h += '<div class="mega-card' + (id === cm ? ' active' : '') + '" data-mod="' + id + '">';
      h += '<div class="mc-top"><span class="mc-ic">' + m.icon + '</span>' + m.name + '</div>';
      h += '<div class="mc-desc">' + m.desc + '</div>';
      if(m.subs && m.subs.length){
        h += '<div class="mega-subs">';
        for(var i=0;i<m.subs.length;i++){
          h += '<button class="mega-sub" data-mod="' + id + '" data-view="' + m.subs[i].k + '">' + m.subs[i].label + '</button>';
        }
        h += '</div>';
      }
      h += '</div>';
    }
    h += '</div>';
  }
  h += '<div class="mega-foot"><button class="m-btn ghost" id="megaCloseFoot" style="max-width:220px">收起面板</button></div>';
  megaPanel.innerHTML = h;
  document.body.appendChild(megaMask);
  document.body.appendChild(megaPanel);
  /* 关闭三路径：标题栏 ✕ + 遮罩点按 + 底部「收起面板」（另支持 Esc） */
  var x = document.getElementById('megaCloseX'); if(x) x.addEventListener('click', closeMegaMenu);
  var ft = document.getElementById('megaCloseFoot'); if(ft) ft.addEventListener('click', closeMegaMenu);
  megaPanel.addEventListener('click', function(ev){
    if(ev.target.closest){
      var sub = ev.target.closest('.mega-sub');
      if(sub){ ev.stopPropagation(); closeMegaMenu(); navJumpTo(sub.getAttribute('data-mod'), sub.getAttribute('data-view')); return; }
      var card = ev.target.closest('.mega-card');
      if(card){ closeMegaMenu(); var id = card.getAttribute('data-mod'); try{ switchModule(id); }catch(e){} }
    }
  });
  return megaPanel;
}
function openMegaMenu(){
  buildMega();
  var cm = curMod();
  var cards = megaPanel.querySelectorAll('.mega-card');
  for(var i=0;i<cards.length;i++){ cards[i].classList.toggle('active', cards[i].getAttribute('data-mod') === cm); }
  if(dropEl) dropEl.classList.remove('show');
  megaMask.classList.add('show');
  megaPanel.classList.add('show');
  var btn = document.getElementById('megaBtn'); if(btn) btn.setAttribute('aria-expanded','true');
}
function closeMegaMenu(){
  if(megaMask) megaMask.classList.remove('show');
  if(megaPanel) megaPanel.classList.remove('show');
  var btn = document.getElementById('megaBtn'); if(btn) btn.setAttribute('aria-expanded','false');
}
function toggleMegaMenu(ev){
  if(ev && ev.stopPropagation) ev.stopPropagation();
  if(megaPanel && megaPanel.classList.contains('show')) closeMegaMenu(); else openMegaMenu();
}
window.toggleMegaMenu = toggleMegaMenu;
window.closeMegaMenu = closeMegaMenu;

/* ---------- 深跳：切换模块并向 iframe 内模块发 cc:nav-jump ---------- */
function navJumpTo(mod, view){
  try{ switchModule(mod); }catch(e){ return; }
  var label = subLabel(mod, view) || view;
  /* 子页补写两次：立即 + 80ms 后（页签 MutationObserver 微任务会先清一次，之后补回） */
  setCrumbSub(label);
  setTimeout(function(){
    try{
      var act = document.querySelector('.mod-tab.active');
      if(act && act.getAttribute('data-mod') === mod) setCrumbSub(label);
    }catch(e){}
  }, 80);
  var tries = 0;
  (function fire(){
    tries++;
    var f = null; try{ f = document.getElementById('frame-' + mod); }catch(e){}
    if(f && f.contentWindow){
      var _tgt='*'; try{ var _u=new URL(f.src||'', location.href); if(_u.origin && _u.origin!=='null') _tgt=_u.origin; }catch(e){}
      try{ f.contentWindow.postMessage({type:'cc:nav-jump', view:view, mod:mod}, _tgt); }catch(e){}
      if(tries < 3) setTimeout(fire, 500);   /* 模块脚本可能晚就绪，补发 */
    } else if(tries < 20){ setTimeout(fire, 400); }
  })();
}

/* ---------- 模块子页上报通道（保留：模块可 postMessage {type:'cc:crumb', mod, text}） ---------- */
window.addEventListener('message', function(e){
  try{
    var d = e.data || {};
    if(d.type === 'cc:crumb' && typeof d.text === 'string' && d.text){
      var act = document.querySelector('.mod-tab.active');
      if(act && (!d.mod || d.mod === act.getAttribute('data-mod'))){
        /* 2026-09-19：只取「›」后最后一段非空文本并限长 12 字，避免整串库名撑爆顶栏，
           也避免模块上报 "... ›" 时留下孤零零的分隔符。 */
        var parts = String(d.text).split('›').map(function(x){ return x.trim(); }).filter(Boolean);
        var sub = parts.length ? parts[parts.length - 1] : '';
        if(sub.length > 12) sub = sub.slice(0, 12) + '…';
        setCrumbSub(sub);
      }
    }
  }catch(err){}
});

/* ---------- 宽屏铺满：空间够就展示全部板块（2026-09-19 用户要求） ----------
   做法：先把全部页签显形量一遍总宽（读 offsetWidth 会强制回流，测量有效），
   与「顶栏可用宽度 - 右侧状态区 - 面包屑」比较，够则保留 .nav-all，否则退回 keep 白名单。 */
function fitNavTabs(){
  try{
    var nav = document.getElementById('moduleTabs');
    if(!nav) return;
    var bar = nav.closest ? nav.closest('.topbar') : null;
    if(!bar) bar = nav.parentNode;
    var actions = bar.querySelector('.actions');
    var crumb = document.getElementById('shellCrumb');
    var pad = 40;
    var avail = (bar.clientWidth || 0) - pad - (actions ? actions.offsetWidth : 0)
              - ((crumb && crumb.offsetWidth) ? crumb.offsetWidth : 0) - 12;
    if(avail <= 0) return;
    nav.classList.add('nav-all');
    var tabs = nav.querySelectorAll('.mod-tab'), need = 0;
    for(var i = 0; i < tabs.length; i++){
      var w = tabs[i].offsetWidth;
      if(w > 0) need += w + 6;
    }
    if(need <= avail) nav.classList.add('nav-all');
    else nav.classList.remove('nav-all');
  }catch(e){}
}
window.fitNavTabs = fitNavTabs;
/* ---------- #9 滚动收缩：绑定活动模块 iframe 滚动（同源，含 .main-scroll-container） ---------- */
function activeScrollY(){
  try{
    var act = document.querySelector('.sys-wrap.active'); if(!act) return 0;
    var f = act.querySelector('.sys-frame'); if(!f) return 0;
    var y = 0;
    try{ y = f.contentWindow ? (f.contentWindow.pageYOffset || 0) : 0; }catch(e){}
    try{
      var doc = f.contentDocument;
      if(doc){
        var sc = doc.querySelector('.main-scroll-container');
        if(sc && sc.scrollTop) y = sc.scrollTop;
      }
    }catch(e){}
    return y;
  }catch(e){ return 0; }
}
function bindFrameScrolls(){
  setInterval(function(){
    var act = document.querySelector('.sys-wrap.active'); if(!act) return;
    var f = act.querySelector('.sys-frame'); if(!f || !f.contentWindow) return;
    if(f.__navScrollBound) return;
    f.__navScrollBound = true;
    var w = f.contentWindow;
    var onScroll = function(){
      try{
        var y = w.pageYOffset || 0;
        var doc = null; try{ doc = f.contentDocument; }catch(e){}
        if(doc){
          var sc = doc.querySelector('.main-scroll-container');
          if(sc && sc.scrollTop) y = sc.scrollTop;
        }
        if(y > 64) document.documentElement.classList.add('nav-scrolled');
        else if(y < 12) document.documentElement.classList.remove('nav-scrolled');
      }catch(e){}
    };
    try{ w.addEventListener('scroll', onScroll, {passive:true}); }catch(e){}
    /* scroll 事件不冒泡：容器滚动模块必须直接绑 .main-scroll-container */
    try{
      var doc = f.contentDocument;
      if(doc){
        var sc = doc.querySelector('.main-scroll-container');
        if(sc) sc.addEventListener('scroll', onScroll, {passive:true});
      }
    }catch(e){}
  }, 900);
}

/* ---------- Esc 统一关闭 ---------- */
document.addEventListener('keydown', function(e){
  if(e && (e.key === 'Escape' || e.keyCode === 27)){ closeMegaMenu(); if(dropEl) dropEl.classList.remove('show'); }
});
window.addEventListener('resize', function(){ if(dropEl) dropEl.classList.remove('show'); });

function init(){
  watchTabs();
  bindDrops();
  bindFrameScrolls();
  fitNavTabs();
  setTimeout(fitNavTabs, 600);           /* 字体/emoji 落位后复测 */
  var _fitTimer = null;
  window.addEventListener('resize', function(){
    if(_fitTimer) clearTimeout(_fitTimer);
    _fitTimer = setTimeout(fitNavTabs, 120);
  });
}
if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
else init();
})();'''

JS_BLOCK = '\n<script>\n/*' + MARK_JS + 'BEGIN —— 导航升级（源 index.html，勿直接改产物）*/\n' + JS_BODY + '\n/*' + MARK_JS + 'END*/\n</script>\n'

# ============================================================================
# 模块深跳桥
# ============================================================================
BRIDGE_BEAUTY = r'''<script>/*__NAV_BRIDGE_20260917__ 深跳桥：壳层 postMessage(cc:nav-jump) → 切换美妆板块（幂等）*/
(function(){
  if(window.__ccNavBridge) return; window.__ccNavBridge = true;
  function goView(v){
    v = String(v||''); if(!v) return;
    try{ if(typeof window.switchTab === 'function'){ window.switchTab(v); return; } }catch(e){}
    try{ var f = window.eval('switchTab'); if(typeof f === 'function'){ f(v); return; } }catch(e){}
    try{
      var btns = document.querySelectorAll('button[onclick]');
      var needle = "switchTab('" + v + "')";
      for(var i=0;i<btns.length;i++){
        var oc = btns[i].getAttribute('onclick')||'';
        if(oc.indexOf(needle) >= 0){ btns[i].click(); return; }
      }
    }catch(e){}
  }
  window.addEventListener('message', function(e){
    try{ var d = e.data||{}; if(d.type === 'cc:nav-jump' && d.view){ goView(d.view); } }catch(err){}
  });
})();
</script>
'''

BRIDGE_MANUAL = r'''<script>/*__NAV_BRIDGE_20260917__ 深跳桥：壳层 postMessage(cc:nav-jump) → 切换手册视图（幂等）*/
(function(){
  if(window.__ccNavBridge) return; window.__ccNavBridge = true;
  window.ccGoView = function(v){
    try{
      var btn = document.querySelector('.m-tab[data-v="' + String(v||'') + '"]');
      if(btn) btn.click();
    }catch(e){}
  };
  window.addEventListener('message', function(e){
    try{ var d = e.data||{}; if(d.type === 'cc:nav-jump' && d.view){ window.ccGoView(d.view); } }catch(err){}
  });
})();
</script>
'''


def read(p):
    with io.open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def write(p, s):
    s.encode('utf-8')  # 文本先 encode 校验（项目铁律）
    # 原子写（2026-09-21）：原先是原地覆盖，异常会把被改写的壳截成半截
    tmp = p + '.tmp_write'
    with io.open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(s)
    os.replace(tmp, p)


def strip_between(s, begin, end):
    """按标记边界剥除旧块（支持块内容更新后重放）；无则原样返回"""
    i = s.find(begin)
    if i < 0:
        return s
    j = s.find(end, i)
    if j < 0:
        raise SystemExit('!! 标记块不完整：缺收口 ' + end[:40])
    return s[:i] + s[j + len(end):]


def strip_crumb(s):
    """剥除面包屑块及其注入尾随缩进（CRUMB_HTML 尾部为 '\n  '），恢复原状避免重放累积"""
    return re.sub(r'<nav class="shell-crumb" id="shellCrumb"[\s\S]*?</nav>\n  ', '', s, count=1)


def strip_megabtn(s):
    """剥除巨型按钮块及其注入尾随缩进（MEGA_BTN_HTML 尾部为 '\n    '）"""
    return re.sub(r'<button class="mega-btn" id="megaBtn"[\s\S]*?</button>\n    ', '', s, count=1)


def strip_js_block(s):
    return strip_between(s, '\n<script>\n/*' + MARK_JS + 'BEGIN', '*/\n</script>\n')


def strip_css_block(s):
    return strip_between(s, '\n/*' + MARK_CSS + 'BEGIN', 'END*/\n')


def strip_bridge(s):
    return strip_between(s, '<script>/*' + MARK_BRIDGE, '</script>\n')


def inject_css(s, name):
    """剥旧块→插到首个 .toast-container{top:64px;} 所在样式块结束（</style>）之前"""
    s = strip_css_block(s)
    anchor = s.find('.toast-container{top:64px;}')
    if anchor < 0:
        raise SystemExit('!! %s 缺 CSS 锚点 toast-container{top:64px;}' % name)
    j = s.find('</style>', anchor)
    if j < 0:
        raise SystemExit('!! %s 缺 </style> 收口' % name)
    return s[:j] + CSS_BLOCK + s[j:], 'ok'


def inject_crumb(s, name):
    """#3 面包屑：剥旧块→插在 <nav class="module-tabs" 之前"""
    s = strip_crumb(s)
    anchor = s.find('<nav class="module-tabs" id="moduleTabs"')
    if anchor < 0:
        raise SystemExit('!! %s 缺面包屑锚点 moduleTabs' % name)
    return s[:anchor] + CRUMB_HTML + s[anchor:], 'ok'


def inject_megabtn(s, name):
    """#5 触发按钮：2026-09-19 起只清理旧产物、不再注入（工具区入口改由页签行 nav-more-btn 承担）"""
    s = strip_megabtn(s)
    if not MEGA_BTN_HTML.strip():
        return s, 'removed'
    m = re.search(r'<div class="actions"[^>]*>\r?\n', s)
    if not m:
        raise SystemExit('!! %s 缺 actions 锚点' % name)
    return s[:m.end()] + MEGA_BTN_HTML + s[m.end():], 'ok'


def inject_js(s, name):
    """JS 块：剥旧块→插到 </body> 之前"""
    s = strip_js_block(s)
    anchor = s.rfind('</body>')
    if anchor < 0:
        raise SystemExit('!! %s 缺 </body>' % name)
    return s[:anchor] + JS_BLOCK + s[anchor:], 'ok'


def inject_bridge(s, name, bridge):
    s = strip_bridge(s)
    anchor = s.rfind('</body>')
    if anchor < 0:
        raise SystemExit('!! %s 缺 </body>' % name)
    return s[:anchor] + bridge + s[anchor:], 'ok'


def main():
    check_only = '--check' in sys.argv
    results = []
    for name in SHELL_FILES:
        p = os.path.join(BASE, name)
        s = read(p)
        before = len(s)
        s, a = inject_css(s, name)
        s, b = inject_crumb(s, name)
        s, c = inject_megabtn(s, name)
        s, d = inject_js(s, name)
        if not check_only:
            write(p, s)
        results.append('%s: css=%s crumb=%s megabtn=%s js=%s (%d -> %d bytes)' % (name, a, b, c, d, before, len(s)))
    for name, bridge in [('beauty.html', BRIDGE_BEAUTY), ('manual.html', BRIDGE_MANUAL)]:
        p = os.path.join(BASE, name)
        s = read(p)
        before = len(s)
        s, st = inject_bridge(s, name, bridge)
        if not check_only:
            write(p, s)
        results.append('%s: bridge=%s (%d -> %d bytes)' % (name, st, before, len(s)))
    for line in results:
        print('  ' + line)
    print('导航升级注入完成（幂等）。')


if __name__ == '__main__':
    main()
