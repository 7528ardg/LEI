# -*- coding: utf-8 -*-
"""重建「客舱小助手（离线完整版）」离线单文件（9 模块 gzip 内嵌）（临时工具，用后可删）"""
import gzip, base64, io, os, re

BASE = r'c:\Users\Admin\Desktop\融合版'
SOURCES = {
    'qa': u'qa.html',
    'home': u'cc-home.html',
    'quiz': u'quiz.html',
    'performance': u'performance.html',
    'beauty': u'beauty.html',
    'medical': u'medical.html',
    'risk': u'risk-lite.html',
    'daily': u'daily.html',
    'manual': u'manual.html',
    'report': u'report.html',
    'kbadmin': u'kb-admin.html',
    'issues': u'issues.html',
}
OUT = u'客舱小助手（离线完整版）.html'

TEMPLATE = u'''<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover, interactive-widget=resizes-content">
<meta name="theme-color" content="#00A650">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="客舱小助手">
<meta name="mobile-web-app-capable" content="yes">
<meta name="application-name" content="春秋航空广州分队客舱小助手">
<meta name="description" content="春秋航空广州分队客舱小助手（离线完整版）- 你问我答·培训考核·绩效管理·美妆话术·医疗急救·风险预警·日常问题·手册奖惩·事件报告 九大模块单文件离线版">
<meta name="format-detection" content="telephone=no">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>春秋航空 · 广州分队客舱小助手</title>
<style>
:root{
  --font-sans:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
  --topbar-h:60px;
  --primary:#148453;--primary-dark:#0C5F3A;--primary-light:#67AC91;
  --primary-soft:#E8F3EE;--primary-mist:#F4F9F6;
  --gold:#F5B800;--gold-soft:#FEF6DC;
  --danger:#E64A19;--danger-soft:#FEE7DE;
  --grad-primary:linear-gradient(135deg,#148453 0%,#1FA56A 100%);
  --grad-livery:linear-gradient(90deg,#148453 0%,#4FA86C 18%,#8FC85C 35%,#C9D745 52%,#F5B800 68%,#F08A00 85%,#E64A19 100%);
  --bg:#F5F8F6;--bg-card:#fff;--text:#0F2A1F;--text2:#5A6F65;--text3:#B5C2BC;--border:#E5EDE9;
  --shadow:0 4px 14px rgba(20,132,83,.10);
  --shadow-lg:0 12px 32px rgba(20,132,83,.14);
}
html[data-theme="dark"]{
  --bg:#0F1A14;--bg-card:#162420;--text:#E8F3EE;--text2:#8FA89C;--text3:#4A6358;--border:#1E3A2C;
  --primary-soft:#1A3D2A;--primary-mist:#142E22;--gold-soft:#2A2410;
}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:var(--font-sans);background:var(--bg);color:var(--text);min-height:100vh;transition:background .3s,color .3s;}
.livery-stripe{height:3px;background:var(--grad-livery);}
.topbar{position:fixed;top:3px;left:0;right:0;height:var(--topbar-h);background:var(--bg-card);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 20px;z-index:100;gap:14px;transition:background .3s;backdrop-filter:blur(20px);}
.logo-wrap{display:flex;align-items:center;gap:10px;flex-shrink:0;cursor:pointer;}
.logo-wrap svg{width:36px;height:36px;}
.brand-name{font-size:1.05rem;font-weight:800;color:var(--primary);white-space:nowrap;letter-spacing:-.3px;}
.brand-sub{font-size:.66rem;color:var(--primary);font-weight:500;margin-left:2px;padding:2px 8px;border-radius:6px;background:var(--primary-soft);}
.module-tabs{display:flex;align-items:center;gap:6px;flex:1;min-width:0;overflow-x:auto;scrollbar-width:none;padding:4px;scroll-snap-type:x proximity;}
.module-tabs::-webkit-scrollbar{display:none;}
.mod-tab{padding:8px 16px;border-radius:10px;border:none;background:transparent;cursor:pointer;font-size:.86rem;font-weight:600;color:var(--text2);display:flex;align-items:center;gap:6px;white-space:nowrap;transition:all .2s;font-family:var(--font-sans);scroll-snap-align:start;min-height:38px;}
.mod-tab:hover{background:var(--primary-mist);color:var(--primary);}
.mod-tab.active{background:var(--grad-primary);color:#fff;box-shadow:var(--shadow);}
.actions{display:flex;align-items:center;gap:10px;flex-shrink:0;}
.net-status{display:flex;align-items:center;gap:5px;font-size:.76rem;color:var(--text2);padding:5px 10px;border-radius:14px;background:var(--primary-soft);font-weight:500;}
.net-status .net-dot{width:7px;height:7px;border-radius:50%;background:var(--primary);flex-shrink:0;box-shadow:0 0 8px var(--primary);}
.net-status.offline{background:var(--danger-soft);color:var(--danger);}
.net-status.offline .net-dot{background:var(--danger);box-shadow:0 0 8px var(--danger);}
.theme-btn{width:36px;height:36px;border-radius:50%;border:1px solid var(--border);background:var(--bg);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:1.05rem;transition:all .25s cubic-bezier(.34,1.56,.64,1);}
.theme-btn:hover{border-color:var(--primary);background:var(--primary-soft);transform:rotate(30deg) scale(1.1);}
.user-chip{display:flex;align-items:center;gap:8px;padding:4px 12px 4px 5px;border-radius:22px;background:var(--primary-soft);font-size:.8rem;color:var(--primary);font-weight:700;cursor:pointer;}
.user-chip .avatar{width:28px;height:28px;border-radius:50%;background:var(--grad-primary);display:flex;align-items:center;justify-content:center;color:#fff;font-size:.74rem;font-weight:800;}
.sys-area{position:fixed;top:calc(3px + var(--topbar-h));left:0;right:0;bottom:0;background:var(--bg);}
.sys-wrap{width:100%;height:100%;display:none;position:relative;}
.sys-wrap.active{display:block;animation:sysFade .22s ease-out;}
@keyframes sysFade{from{opacity:.35;}to{opacity:1;}}
@media (prefers-reduced-motion:reduce){.sys-wrap.active{animation:none}.theme-btn,.mod-tab,.net-status,.user-chip{-webkit-transition:none!important;transition:none!important}}
.mod-tab:focus-visible,.theme-btn:focus-visible,.user-chip:focus-visible,.jump-btn:focus-visible{outline:2px solid var(--primary);outline-offset:2px}
.sys-frame{width:100%;height:100%;border:none;display:block;}
.sys-loader{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;background:var(--bg);z-index:5;transition:opacity .4s;gap:14px;}
.sys-loader.hidden{opacity:0;pointer-events:none;}
.sys-spinner{width:44px;height:44px;border:4px solid var(--primary-soft);border-top-color:var(--primary);border-radius:50%;animation:spin .8s linear infinite;}
.sys-loader .sl-text{font-size:.85rem;color:var(--text2);font-weight:500;}
@keyframes spin{to{transform:rotate(360deg);}}
@media(min-width:721px) and (max-width:1100px){
  .topbar{padding:0 14px;gap:10px;}
  .brand-name{font-size:.95rem;}
  .mod-tab{padding:8px 12px;font-size:.82rem;gap:6px;}
  .module-tabs{-webkit-mask-image:linear-gradient(to right,transparent 0,#000 16px,#000 calc(100% - 16px),transparent 100%);mask-image:linear-gradient(to right,transparent 0,#000 16px,#000 calc(100% - 16px),transparent 100%);}
}
@media(max-width:720px){
  .logo-wrap svg{width:30px;height:30px;}
  .brand-name{font-size:.84rem;letter-spacing:-.2px;}
  .brand-sub{font-size:.58rem;padding:1px 6px;}
  .net-status{display:none;}
  .mod-tab{padding:7px 10px;font-size:.8rem;gap:6px;}
  .user-chip span{display:none;}
  /* 手机端 9 个模块页签横向滚动：左右边缘淡出提示可滑动，避免误以为内容被截断 */
  .module-tabs{-webkit-mask-image:linear-gradient(to right,transparent 0,#000 16px,#000 calc(100% - 16px),transparent 100%);mask-image:linear-gradient(to right,transparent 0,#000 16px,#000 calc(100% - 16px),transparent 100%);}
  /* 手机端 Toast 全宽展示，避免 min-width 溢出小屏 */
  .toast-container{left:12px;right:12px;top:68px;}
  .toast{min-width:0;width:100%;}
}
:root{--tabbar-h:58px;}
/* ===== 手机端 APP 化：底部 TabBar + 更多面板（与 index.html 壳同步） ===== */
.m-tabbar,.m-sheet{display:none;}
.m-sheet-mask{display:none;}
@media(max-width:720px){
  .brand-main{display:none;}
  .brand-name{font-size:.92rem;}
  .topbar{gap:8px;padding:0 10px;}
  .module-tabs{display:none;}
  .sys-clock{padding:4px 8px;font-size:.7rem;}
  .sys-clock .sc-tag{display:none;}
  .sys-area{bottom:calc(var(--tabbar-h) + env(safe-area-inset-bottom,0px));}
  .m-tabbar{display:flex;position:fixed;left:0;right:0;bottom:0;height:calc(var(--tabbar-h) + env(safe-area-inset-bottom,0px));padding:0 4px env(safe-area-inset-bottom,0px);background:var(--bg-card);border-top:1px solid var(--border);z-index:200;box-shadow:0 -4px 16px rgba(15,42,31,.06);backdrop-filter:blur(20px);}
  .m-tab{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;border:none;background:transparent;cursor:pointer;font-family:var(--font-sans);color:var(--text2);font-size:.62rem;font-weight:700;padding:6px 0 4px;border-radius:12px;transition:color .2s;}
  .m-tab .mi{font-size:1.28rem;line-height:1.15;transition:transform .2s;}
  .m-tab.active{color:var(--primary);}
  .m-tab.active .mi{transform:translateY(-1px) scale(1.1);}
  .m-tab.active .mi::after{content:'';display:block;width:14px;height:3px;border-radius:2px;background:var(--grad-primary);margin:2px auto 0;}
  .m-tab:active .mi{transform:scale(.9);}
  .m-sheet-mask{display:block;position:fixed;inset:0;background:rgba(0,0,0,.42);z-index:300;opacity:0;pointer-events:none;transition:opacity .25s;}
  .m-sheet-mask.show{opacity:1;pointer-events:auto;}
  .m-sheet{display:block;position:fixed;left:0;right:0;bottom:calc(var(--tabbar-h) + env(safe-area-inset-bottom,0px));z-index:301;background:var(--bg-card);border-radius:20px 20px 0 0;border-top:1px solid var(--border);padding:12px 14px calc(14px + env(safe-area-inset-bottom,0px));transform:translateY(115%);visibility:hidden;pointer-events:none;transition:transform .3s cubic-bezier(.32,.72,.34,1),visibility 0s linear .32s;box-shadow:0 -12px 32px rgba(15,42,31,.18);max-height:72vh;overflow-y:auto;-webkit-overflow-scrolling:touch;}
  .m-sheet.show{transform:translateY(0);visibility:visible;pointer-events:auto;transition:transform .3s cubic-bezier(.32,.72,.34,1);}
  .m-sheet h4{font-size:.86rem;color:var(--text);margin:2px 4px 10px;font-weight:800;display:flex;align-items:center;justify-content:space-between;}
  .m-sheet-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;}
  .m-sheet-item{display:flex;flex-direction:column;align-items:center;gap:6px;padding:12px 4px;border:1px solid var(--border);border-radius:14px;background:var(--bg);cursor:pointer;font-size:.74rem;font-weight:700;color:var(--text);font-family:var(--font-sans);transition:all .15s;}
  .m-sheet-item:active{transform:scale(.95);}
  .m-sheet-item .mi{font-size:1.4rem;line-height:1;}
  .m-sheet-item.active{border-color:var(--primary);background:var(--primary-soft);color:var(--primary);}
  .toast-container{top:64px;}
}
.toast-container{position:fixed;top:76px;right:20px;z-index:300;display:flex;flex-direction:column;gap:8px;}
.toast{padding:11px 18px;border-radius:8px;background:var(--bg-card);border:1px solid var(--border);box-shadow:0 4px 16px rgba(0,0,0,.1);font-size:.86rem;display:flex;align-items:center;gap:10px;animation:slideIn .3s;min-width:240px;border-left:4px solid var(--primary);}
.toast.toast-info{border-left-color:var(--primary);}
@keyframes slideIn{from{transform:translateX(100%);opacity:0;}to{transform:translateX(0);opacity:1;}}
/* ===== 全局数据备份/恢复 ===== */
.bk-btn{display:flex;align-items:center;gap:6px;padding:6px 12px;border-radius:14px;border:1px solid var(--border);background:var(--bg);color:var(--text2);cursor:pointer;font-size:.8rem;font-weight:600;transition:all .2s;font-family:var(--font-sans);flex-shrink:0;}
.bk-btn:hover{border-color:var(--primary);color:var(--primary);background:var(--primary-soft);}
.modal-mask{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.45);z-index:400;display:none;align-items:center;justify-content:center;padding:20px;}
.modal-mask.show{display:flex;}
.modal-card{background:var(--bg-card);border:1px solid var(--border);border-radius:16px;box-shadow:var(--shadow-lg);width:100%;max-width:400px;padding:24px;box-sizing:border-box;}
.modal-card h3{margin:0 0 6px;font-size:1.05rem;color:var(--text);}
.modal-x{width:28px;height:28px;border-radius:8px;border:none;background:var(--primary-mist);color:var(--text2);font-size:.9rem;line-height:1;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;transition:all .2s;font-family:var(--font-sans);margin-left:8px}
.modal-x:hover{background:var(--danger-soft);color:var(--danger)}
.modal-card .m-sub{font-size:.82rem;color:var(--text2);line-height:1.7;margin:0 0 16px;}
.m-actions{display:flex;flex-direction:column;gap:10px;}
.m-btn{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;padding:12px;border-radius:10px;border:none;cursor:pointer;font-size:.9rem;font-weight:700;font-family:var(--font-sans);transition:all .2s;}
.m-btn.primary{background:var(--grad-primary);color:#fff;box-shadow:var(--shadow);}
.m-btn.ghost{background:var(--primary-soft);color:var(--primary);border:1px solid var(--primary-light);}
.m-btn:hover{transform:translateY(-1px);}
.m-meta{font-size:.74rem;color:var(--text3);text-align:center;margin-top:14px;line-height:1.6;}
@media(max-width:720px){.bk-btn span{display:none;}.bk-btn{padding:6px 9px;}}
/* ===== 个人资料（姓名 / 头像） ===== */
.user-chip .avatar img{width:100%;height:100%;border-radius:50%;object-fit:cover;display:block;}
.user-chip .avatar div{width:100%;height:100%;display:flex;align-items:center;justify-content:center;border-radius:50%;}
.profile-avatar-preview{width:88px;height:88px;border-radius:50%;margin:0 auto 6px;background:var(--grad-primary);display:flex;align-items:center;justify-content:center;color:#fff;font-size:1.8rem;font-weight:800;overflow:hidden;cursor:pointer;position:relative;}
.profile-avatar-preview img{width:100%;height:100%;object-fit:cover;display:block;}
.profile-avatar-preview .cam{position:absolute;left:0;right:0;bottom:0;background:rgba(0,0,0,.45);color:#fff;font-size:.62rem;padding:3px 0;text-align:center;opacity:0;transition:opacity .2s;}
.profile-avatar-preview:hover .cam{opacity:1;}
.pf-del{display:inline-flex;align-items:center;gap:4px;margin:2px auto 12px;padding:4px 10px;font-size:.74rem;color:var(--danger);background:none;border:none;cursor:pointer;font-family:var(--font-sans);}
.pf-field{margin-bottom:14px;}
.pf-field label{display:block;font-size:.78rem;color:var(--text2);margin-bottom:6px;font-weight:600;}
.pf-field input[type=text]{width:100%;padding:10px 12px;border-radius:10px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:.9rem;outline:none;box-sizing:border-box;font-family:var(--font-sans);}
.pf-field input[type=text]:focus{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-soft);}

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

/*__SHELL_SYNC_20260919_CSS__BEGIN —— 顶栏收敛 3 板块 + 右侧三层重排（源 index.html，勿直接改产物）*/
/* 2026-09-19 设计审核 P0-A/P0-B 修复：
   · 对比度：.sc-date / .uc-role / .uc-caret 原用 --text3(#B5C2BC)，实测对白仅 1.84:1（远低于 AA 4.5:1）。
     --text3 是全局令牌、别处还在用，故只在这三个选择器上改判，不动令牌。
     改用 --text2：浅色 #5A6F65 → 5.39:1；深色 #8FA89C → 6.31:1，两模式均达标。
   · 字号：三者最小 9.6px（.uc-role），低于可读下限，提到 11px / 12px。
   · 触控：顶栏方钮与页签原 36px / 38px，低于 44px 触摸底线，统一到 44px
     （顶栏高 60px，44px 控件放得下，无需改 --topbar-h，也不会挤到内容区）。 */
.module-tabs .mod-tab{display:none!important;}
.module-tabs .mod-tab.keep{display:flex!important;}
/* 触控底线：页签行 46px，44px 页签放得下（原 38px） */
.mod-tab{min-height:44px;}
.actions{display:flex;align-items:center;gap:6px;flex-shrink:0;}
.actions .act-sep{width:1px;height:22px;background:var(--border);margin:0 6px;flex-shrink:0;}
.actions .mega-btn,.actions .bk-btn,.actions .theme-btn{height:44px;border-radius:12px;border:1px solid var(--border);background:transparent;color:var(--text2);flex-shrink:0;
  transition:border-color .18s cubic-bezier(.23,1,.32,1),color .18s cubic-bezier(.23,1,.32,1),background-color .18s cubic-bezier(.23,1,.32,1);}
.actions .bk-btn{padding:0 12px;display:inline-flex;align-items:center;gap:6px;font-size:.78rem;font-weight:700;font-family:var(--font-sans);cursor:pointer;}
.actions .theme-btn{width:44px;font-size:1rem;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;}
.actions .mega-btn:hover,.actions .bk-btn:hover,.actions .theme-btn:hover{border-color:var(--primary);color:var(--primary);background:var(--primary-mist);}
.actions .mega-btn:active,.actions .bk-btn:active,.actions .theme-btn:active{transform:scale(.97);}
.actions .sys-clock{display:inline-flex;flex-direction:column;align-items:flex-end;justify-content:center;gap:0;padding:0 4px;border:none;background:transparent;line-height:1.15;white-space:nowrap;}
.actions .sys-clock .sc-time{font-size:.86rem;font-weight:800;color:var(--text);font-variant-numeric:tabular-nums;letter-spacing:.02em;}
.actions .sys-clock .sc-row{display:flex;align-items:center;gap:6px;}
.actions .sys-clock .sc-date{font-size:.6875rem;font-weight:600;color:var(--text2);}   /* 10.6px → 11px；对比度 1.84 → 5.39:1 */
.actions .sys-clock .sc-tag{font-size:.6875rem;font-weight:700;color:#8A6A00;background:transparent;padding:0;border-radius:0;}  /* 10.2px → 11px */
.actions .sys-clock .sc-tag.none{color:var(--text2);}
html[data-theme="dark"] .actions .sys-clock .sc-tag{color:#E3C56A;}
.actions .net-status{display:inline-flex;align-items:center;gap:5px;height:44px;padding:0 8px;border:none;background:transparent;color:var(--text2);font-size:.72rem;font-weight:600;}
.actions .net-status .net-dot{width:7px;height:7px;border-radius:50%;background:var(--primary);box-shadow:0 0 0 3px rgba(20,132,83,.14);}
.actions .net-status.offline{color:var(--danger);background:transparent;}
.actions .net-status.offline .net-dot{background:var(--danger);box-shadow:0 0 0 3px rgba(230,74,25,.16);}
.actions .user-chip{display:flex;align-items:center;gap:8px;min-height:44px;padding:3px 10px 3px 3px;border-radius:999px;background:var(--primary-soft);border:1px solid transparent;cursor:pointer;
  transition:background-color .18s cubic-bezier(.23,1,.32,1),border-color .18s cubic-bezier(.23,1,.32,1);}
.actions .user-chip:hover{background:var(--primary-mist);border-color:var(--primary);}
.actions .user-chip .avatar{width:34px;height:34px;border-radius:50%;background:var(--grad-primary);display:flex;align-items:center;justify-content:center;color:#fff;font-size:.8rem;font-weight:800;flex-shrink:0;}
.actions .user-chip .uc-tx{display:flex;flex-direction:column;line-height:1.2;}
.actions .user-chip #userName{font-size:.78rem;font-weight:800;color:var(--primary-dark,#0C5F3A);}
.actions .user-chip .uc-role{font-size:.75rem;font-weight:700;color:var(--text2);letter-spacing:.03em;}  /* 9.6px → 12px；对比度 1.84 → 5.39:1 */
.actions .user-chip .uc-caret{color:var(--text2);font-size:.8rem;margin-left:2px;}                      /* 对比度 1.84 → 5.39:1 */
html[data-theme="dark"] .actions .user-chip{background:#1A3D2A;}
html[data-theme="dark"] .actions .user-chip #userName{color:#8FD3B0;}
@media(max-width:1100px){.actions .user-chip .uc-role,.actions .user-chip .uc-caret{display:none;}}
@media(max-width:960px){.actions .sys-clock .sc-date{display:none;}.actions .bk-btn .act-tx{display:none;}.actions .bk-btn{padding:0 10px;}}
@media(max-width:820px){.actions .net-status #netText{display:none;}.actions .net-status{padding:0 6px;}}
@media(max-width:720px){.actions .sys-clock .sc-row{display:none;}.actions .act-sep{display:none;}}
/* --- 宽屏铺满：空间足够时展示全部板块（由壳层 JS fitNavTabs 实测后加 .nav-all） ---
   实测不可行用纯媒体查询：12 个页签 × 中文字宽 + 右侧状态区 ≈ 1600px 起，故用 JS 实测更稳。 */
.module-tabs.nav-all .mod-tab{display:flex!important;}
.module-tabs.nav-all .mod-tab.keep{display:flex!important;}
/* --- 导航「全部应用」入口（其余 9 板块的统一入口，跟随页签排布） --- */
.nav-more-btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;height:44px;padding:0 12px;margin-left:2px;flex-shrink:0;
  border:1px dashed var(--border);border-radius:12px;background:transparent;color:var(--text2);font-size:.8rem;font-weight:700;font-family:var(--font-sans);cursor:pointer;
  transition:border-color .18s cubic-bezier(.23,1,.32,1),color .18s cubic-bezier(.23,1,.32,1),background-color .18s cubic-bezier(.23,1,.32,1);}
.nav-more-btn:hover{border-style:solid;border-color:var(--primary);color:var(--primary);background:var(--primary-mist);}
.nav-more-btn:active{transform:scale(.97);}
.nav-more-btn[aria-expanded="true"]{border-style:solid;border-color:var(--primary);background:var(--grad-primary);color:#fff;}
.nav-more-btn:focus-visible{outline:2px solid var(--primary);outline-offset:2px;}
@media(max-width:1100px){.nav-more-btn .amb-tx{display:none;}.nav-more-btn{padding:0 10px;}}
/* --- 底部「更多」面板：分组小标题 + 与巨型菜单同源的 12 板块 --- */
.m-sheet h4 .ms-sub{font-size:.66rem;font-weight:600;color:var(--text3);margin-left:auto;margin-right:8px;}
.m-sheet-sec{grid-column:1/-1;font-size:.68rem;font-weight:800;color:var(--text3);letter-spacing:.06em;margin:8px 2px 2px;}
.m-sheet-sec:first-child{margin-top:0;}
/*__SHELL_SYNC_20260919_CSS__END*/
</style>
<script>
/* 客舱小助手数据包引擎（_sync_packs.py 自动注入；改 docs/_packs_engine.js 后重跑 python _sync_packs.py） */
//__PACKS_ENGINE_START__
/* =============================================================================
 * 客舱小助手 · 数据包引擎 v1（M1.1 单一来源）
 * -----------------------------------------------------------------------------
 * 目的：让"内容数据包"（知识库/销售/题库）以 JSON 覆盖层形式覆盖内嵌基线，
 *       实现"改内容不改代码"。本文件为纯逻辑、零 DOM 依赖，
 *       浏览器挂 window.PACKS / Node 挂 module.exports（供单测与构建校验）。
 *
 * 覆盖语义（与方案文档一致）：
 *   1. 优先级：数据包覆盖层 > 内嵌基线
 *   2. 合并：按 packs_index 中 installedAt 升序逐包执行，同 key 后装者胜
 *   3. delete：从最终视图移除该 key（对基线与已 upsert 的覆盖均生效）
 *   4. 过期：appliedUntil < 今天 → 不参与合并但保留在索引（expired 标记，不删数据）
 *   5. 损坏防护：magic 不符 / JSON 损坏 → 静默忽略该包（控制台仅 warn）
 *
 * 存储抽象：所有函数首参为 store，接口 { getItem(k)->string|null,
 *           setItem(k,v), removeItem(k) }；浏览器传 localStorage，测试传内存实现。
 * -----------------------------------------------------------------------------
 * 数据包 JSON 结构（存 localStorage 键 pack:{packId}）：
 * {
 *   magic: 'cabin-data-pack-v1',
 *   packId: 'sales-2026-09',      // 全局唯一；同 packId 重装 = 整包覆盖升级
 *   type: 'kb' | 'sales' | 'quiz' | 'notice',   // notice 消费端 M2 接入
 *   lib: '',                       // 仅 kb 包：空=全库应用，'ccm'|'mgm'|'svc'|'daily'=单库
 *   title: '秋季机上销售包',
 *   version: 3,                    // 展示用；排序靠 installedAt
 *   issuedAt: '2026-08-29',
 *   appliedUntil: '2026-12-31',    // 缺省=永不过期
 *   items: [ { op:'upsert'|'delete', key:'estee-007', data:{...} } ]
 * }
 * packs_index 索引（存 localStorage 键 packs_index）：
 * { magic:'cabin-packs-index-v1', packs:[ {packId,type,title,version,installedAt,source} ] }
 * ============================================================================= */
(function (global) {
  'use strict';

  var PACKS_MAGIC = 'cabin-data-pack-v1';
  var PACKS_INDEX_MAGIC = 'cabin-packs-index-v1';
  var PACKS_INDEX_KEY = 'packs_index';
  var PACK_KEY_PREFIX = 'pack:';

  function fmtDay(d) {
    var y = d.getFullYear();
    var m = d.getMonth() + 1;
    var dd = d.getDate();
    return y + '-' + (m < 10 ? '0' + m : '' + m) + '-' + (dd < 10 ? '0' + dd : '' + dd);
  }

  /* ---------------- 索引读写 ---------------- */
  function readIndex(store) {
    try {
      var raw = store.getItem(PACKS_INDEX_KEY);
      if (!raw) return null;
      var idx = JSON.parse(raw);
      if (!idx || idx.magic !== PACKS_INDEX_MAGIC || !Array.isArray(idx.packs)) return null;
      return idx;
    } catch (e) { return null; }
  }
  function writeIndex(store, packs) {
    try {
      store.setItem(PACKS_INDEX_KEY, JSON.stringify({ magic: PACKS_INDEX_MAGIC, packs: packs }));
      return true;
    } catch (e) { return false; }
  }
  /* ---------------- 包读写 ---------------- */
  function readPack(store, packId) {
    try {
      var raw = store.getItem(PACK_KEY_PREFIX + packId);
      if (!raw) return null;
      var p = JSON.parse(raw);
      if (!p || p.magic !== PACKS_MAGIC || p.packId !== packId) return null;
      return p;
    } catch (e) { return null; }
  }
  /* 写入原始包数据（不校验语义，供 installPack 内部使用；失败抛给调用方判定） */
  function writePackRaw(store, pack) {
    store.setItem(PACK_KEY_PREFIX + pack.packId, JSON.stringify(pack));
  }

  /* ---------------- 包索引元信息列表 ---------------- */
  /* optType 为空返回全部类型；now 注入当前时间（测试固定日期用） */
  function listPacks(store, optType, now) {
    var idx = readIndex(store);
    if (!idx) return [];
    var today = fmtDay(now || new Date());
    var out = [];
    for (var i = 0; i < idx.packs.length; i++) {
      var e = idx.packs[i];
      if (optType && e.type !== optType) continue;
      var p = readPack(store, e.packId);
      var until = p && p.appliedUntil ? String(p.appliedUntil) : '';
      out.push({
        packId: e.packId,
        type: e.type,
        title: e.title || e.packId,
        version: e.version != null ? e.version : 1,
        installedAt: e.installedAt || '',
        source: e.source || 'import',
        appliedUntil: until,
        expired: !!(until && until < today),
        itemCount: p && Array.isArray(p.items) ? p.items.length : 0,
        valid: !!p
      });
    }
    return out;
  }
  function countPackType(store, type, now) {
    var list = listPacks(store, type, now);
    var active = 0, expired = 0;
    for (var i = 0; i < list.length; i++) {
      if (list[i].expired) expired++; else active++;
    }
    return { total: list.length, active: active, expired: expired, packs: list };
  }

  /* ---------------- 核心：构建某类型的最终覆盖视图 ---------------- */
  /* opts: { now:Date, lib:string }；lib 仅对 kb 包生效（空=全库，'ccm' 等=单库）
   * 返回 { map:{key:data}, kills:[keys], expired:[packIds] }
   *   map   = 所有 upsert 后最终生效的数据（已按后装者胜消解）
   *   kills = 声明过 delete 的 key 集合（对基线生效）
   *   expired = 因过期而未参与合并的 packId 列表 */
  function buildPackMap(store, type, opts) {
    opts = opts || {};
    var today = fmtDay(opts.now || new Date());
    var queryLib = opts.lib || '';
    var map = {};
    var kills = [];
    var expired = [];
    var idx = readIndex(store);
    if (!idx) return { map: map, kills: kills, expired: expired };
    var pending = [];
    for (var i = 0; i < idx.packs.length; i++) {
      var e = idx.packs[i];
      if (e.type !== type) continue;
      var p = readPack(store, e.packId);
      if (!p || !Array.isArray(p.items)) continue;
      if (p.lib && queryLib && p.lib !== queryLib) continue;  // 包声明单库且与查询库不符
      if (p.appliedUntil && String(p.appliedUntil) < today) { expired.push(e.packId); continue; }
      pending.push({ p: p, installedAt: e.installedAt || '' });
    }
    pending.sort(function (a, b) {
      return a.installedAt < b.installedAt ? -1 : (a.installedAt > b.installedAt ? 1 : 0);
    });
    for (var j = 0; j < pending.length; j++) {
      var items = pending[j].p.items;
      for (var k = 0; k < items.length; k++) {
        var it = items[k];
        if (!it || !it.key) continue;
        if (it.op === 'delete') {
          delete map[it.key];
          if (kills.indexOf(it.key) < 0) kills.push(it.key);
        } else if (it.op === 'upsert') {
          map[it.key] = it.data;  // 后装者胜；同 key 被重新 upsert 时"复活"，kills 仍记录
        }
      }
    }
    return { map: map, kills: kills, expired: expired };
  }

  /* ---------------- 消费端辅助：把覆盖视图应用到基线数组 ---------------- */
  /* arr: 内嵌基线数组（必须可原地修改——splice/下标赋值，绝不重建，保持外部引用）
   * res: buildPackMap 返回结果
   * keyOf: item -> key 字符串
   * 顺序：先按 kills 移除基线命中项，再按 map upsert（命中就地替换并去重，缺失 push） */
  function applyMapToArray(arr, res, keyOf) {
    keyOf = keyOf || function (it) { return it && it.id ? String(it.id) : ''; };
    var map = res.map || {};
    var kills = res.kills || [];
    var upserted = 0, deleted = 0;
    if (kills.length) {
      for (var i = arr.length - 1; i >= 0; i--) {
        if (kills.indexOf(keyOf(arr[i])) >= 0) { arr.splice(i, 1); deleted++; }
      }
    }
    var keys = Object.keys(map);
    if (!keys.length) return { upserted: upserted, deleted: deleted };
    var idxByKey = {};
    for (var j2 = 0; j2 < arr.length; j2++) {
      var kj = keyOf(arr[j2]);
      if (!idxByKey.hasOwnProperty(kj)) idxByKey[kj] = [];
      idxByKey[kj].push(j2);
    }
    for (var m = 0; m < keys.length; m++) {
      var mk = keys[m];
      var hit = idxByKey.hasOwnProperty(mk) ? idxByKey[mk] : null;
      if (hit && hit.length) {
        arr[hit[0]] = map[mk];
        for (var r = hit.length - 1; r >= 1; r--) arr.splice(hit[r], 1);  // 去重（保留首个位置）
      } else {
        arr.push(map[mk]);
      }
      upserted++;
    }
    return { upserted: upserted, deleted: deleted };
  }

  /* ---------------- 安装 / 移除 / 迁移 ---------------- */
  function installPack(store, pack, source, now) {
    if (!pack || pack.magic !== PACKS_MAGIC) return { ok: false, reason: 'magic' };
    if (!pack.packId || typeof pack.packId !== 'string') return { ok: false, reason: 'packId' };
    if (!pack.type) return { ok: false, reason: 'type' };
    if (!Array.isArray(pack.items)) return { ok: false, reason: 'items' };
    var idx = readIndex(store) || { packs: [] };
    var ts = (now || new Date()).toISOString();
    // 同 packId 重装 = 整包覆盖升级（删除旧索引条目再追加，保持时间序）
    idx.packs = idx.packs.filter(function (e) { return e.packId !== pack.packId; });
    idx.packs.push({
      packId: pack.packId,
      type: pack.type,
      title: pack.title || pack.packId,
      version: pack.version != null ? pack.version : 1,
      installedAt: ts,
      source: source || 'import'
    });
    try { writePackRaw(store, pack); } catch (e) { return { ok: false, reason: 'storage' }; }
    if (!writeIndex(store, idx.packs)) return { ok: false, reason: 'index' };
    return { ok: true, packId: pack.packId, installedAt: ts };
  }
  function removePack(store, packId) {
    var idx = readIndex(store);
    if (!idx) return { ok: false, reason: 'no-index' };
    var n0 = idx.packs.length;
    idx.packs = idx.packs.filter(function (e) { return e.packId !== packId; });
    if (idx.packs.length === n0) return { ok: false, reason: 'not-found' };
    try { store.removeItem(PACK_KEY_PREFIX + packId); } catch (e) {}
    writeIndex(store, idx.packs);
    return { ok: true };
  }
  /* 旧版知识覆盖层（kb_overlay_v1）→ kb-legacy 数据包（幂等，已迁移则跳过）
   * opts: { legacyKey, legacyMagic, now }；成功后删除旧键 */
  function migrateLegacyOverlay(store, opts) {
    opts = opts || {};
    var key = opts.legacyKey || 'kb_overlay_v1';
    var magic = opts.legacyMagic || 'kb-overlay-v1';
    // 幂等优先：已迁移过（无论旧键是否仍在）→ already，不再重复建包
    var idx0 = readIndex(store);
    var already0 = idx0 && idx0.packs.some(function (e) { return e.packId === 'kb-legacy'; });
    if (already0) return { ok: false, reason: 'already' };
    var raw;
    try { raw = store.getItem(key); } catch (e) { return { ok: false, reason: 'read' }; }
    if (!raw) return { ok: false, reason: 'empty' };
    var ov;
    try { ov = JSON.parse(raw); } catch (e) { return { ok: false, reason: 'corrupt' }; }
    if (!ov || ov.magic !== magic || !ov.byLib || typeof ov.byLib !== 'object') return { ok: false, reason: 'magic' };
    var items = [];
    for (var lib in ov.byLib) {
      if (!Object.prototype.hasOwnProperty.call(ov.byLib, lib)) continue;
      var arr = ov.byLib[lib];
      if (!Array.isArray(arr)) continue;
      for (var i = 0; i < arr.length; i++) {
        var e = arr[i];
        if (!e || !e.q) continue;
        items.push({ op: 'upsert', key: e.src || (lib + '-' + i), data: e });
      }
    }
    if (!items.length) return { ok: false, reason: 'empty-items' };
    var pack = {
      magic: PACKS_MAGIC,
      packId: 'kb-legacy',
      type: 'kb',
      lib: '',
      title: '旧版知识覆盖层（自动迁移）',
      version: 1,
      issuedAt: '',
      appliedUntil: '',
      items: items
    };
    var r = installPack(store, pack, 'migrate', opts.now);
    if (!r.ok) return r;
    try { store.removeItem(key); } catch (e) {}
    return { ok: true, itemCount: items.length };
  }

  var PACKS = {
    MAGIC: PACKS_MAGIC,
    INDEX_MAGIC: PACKS_INDEX_MAGIC,
    INDEX_KEY: PACKS_INDEX_KEY,
    readIndex: readIndex,
    writeIndex: writeIndex,
    readPack: readPack,
    listPacks: listPacks,
    countPackType: countPackType,
    buildPackMap: buildPackMap,
    applyMapToArray: applyMapToArray,
    installPack: installPack,
    removePack: removePack,
    migrateLegacyOverlay: migrateLegacyOverlay
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = PACKS;           // Node（单测 / 构建校验）
  }
  if (typeof window !== 'undefined') {
    window.PACKS = PACKS;             // 浏览器（qa / beauty / quiz / kb-admin）
  } else if (typeof globalThis !== 'undefined') {
    globalThis.PACKS = PACKS;
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
//__PACKS_ENGINE_END__
</script>
<style id="mobile-ux-patch">
/* ===== 移动端统一设计规范补丁（2026-09-12）：主色 #00A650 / 圆角 12px / 点击态 ===== */
:root{
  --primary:#00A650;--primary-dark:#00793C;--primary-light:#2FB877;
  --primary-soft:#E5F6EE;--primary-mist:#F2FAF6;
  --grad-primary:linear-gradient(135deg,#00A650 0%,#22BE79 100%);
  --radius:12px;
  --shadow:0 4px 14px rgba(0,120,64,.10);--shadow-lg:0 12px 32px rgba(0,120,64,.14);
}
.m-tab{transition:color .2s,background-color .15s,transform .12s;}
.m-tab:active{background:var(--primary-mist);transform:scale(.94);}
.m-tab .mi{transition:transform .2s;}
.m-sheet-item{transition:all .15s;}
.m-sheet-item:active{transform:scale(.94);background:var(--primary-soft);}
.mod-tab,.theme-btn,.user-chip,.bk-btn,.m-btn{transition:transform .12s ease,background-color .18s ease,color .18s ease,border-color .18s ease;}
.mod-tab:active,.theme-btn:active,.user-chip:active,.bk-btn:active,.m-btn:active{transform:scale(.95);}
button:active{transform:scale(.96);}
button:disabled:active{transform:none;}
@media (hover:none){
  .mod-tab:hover{background:transparent;color:var(--text2);}
  .mod-tab.active:hover{background:var(--grad-primary);color:#fff;}
}
</style>
<!--__A11Y_20260919__BEGIN__-->
<style id="a11y20260919">
/* 2026-09-19 设计审核 P0-C：屏幕阅读器专用工具类 + 跳到主内容 */
.a11y-sr{position:absolute!important;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0;}
.skip-link{position:absolute;left:8px;top:-64px;z-index:9999;background:var(--primary,#148453);color:#fff;padding:10px 16px;border-radius:0 0 10px 10px;font-size:.875rem;font-weight:700;font-family:var(--font-sans,sans-serif);text-decoration:none;transition:top .18s cubic-bezier(.23,1,.32,1);}
.skip-link:focus{top:0;outline:2px solid #fff;outline-offset:-4px;}
@media (prefers-reduced-motion:reduce){.skip-link{transition:none;}}
</style>
<!--__A11Y_20260919__END__-->
</head>
<body>
<!--__A11Y_20260919__BEGIN__-->
<a class="skip-link" href="#sysArea">跳到主要内容</a>
<h1 class="a11y-sr">客舱小助手 · 客舱服务一线工具融合平台</h1>
<!--__A11Y_20260919__END__-->


















<div class="livery-stripe"></div>

<header class="topbar">
  <div class="logo-wrap" onclick="switchModule('quiz')">
    <svg viewBox="0 0 40 40" width="36" height="36">
      <defs><linearGradient id="lg" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="#148453"/><stop offset="33%" stop-color="#4FA86C"/><stop offset="66%" stop-color="#F5B800"/><stop offset="100%" stop-color="#E64A19"/></linearGradient></defs>
      <path d="M8 28 Q12 8 20 18 Q28 8 32 28" fill="none" stroke="url(#lg)" stroke-width="4" stroke-linecap="round"/>
      <path d="M5 30 Q14 14 20 22 Q26 14 35 30" fill="none" stroke="url(#lg)" stroke-width="3" stroke-linecap="round" opacity=".5"/>
      <path d="M11 26 Q16 12 20 20 Q24 12 29 26" fill="none" stroke="url(#lg)" stroke-width="2.5" stroke-linecap="round" opacity=".7"/>
    </svg>
    <div>
      <div class="brand-name"><span class="brand-main">春秋航空</span> <span class="brand-sub">客舱小助手</span></div>
    </div>
  </div>

  
  
  <nav class="shell-crumb" id="shellCrumb" aria-label="当前位置"><span class="cr-item cr-mod" id="crumbMod">你问我答</span><span class="cr-sep" id="crumbSep2" style="display:none">›</span><span class="cr-item cr-sub" id="crumbSub" style="display:none"></span></nav>
  <nav class="module-tabs" id="moduleTabs" data-page-node-id="BsxJNHUQnwWWkzX8mQ7PdA">
    <button class="mod-tab active keep" data-mod="qa" onclick="switchModule('qa')" data-page-node-id="ThWuLHNdXekrpR8s6aKg4k">💬 你问我答</button>
    <button class="mod-tab keep" data-mod="quiz" onclick="switchModule('quiz')" data-page-node-id="AfTAaJatoJoPJYGMUFg51D">📚 培训考核</button>
    <button class="mod-tab keep" data-mod="performance" onclick="switchModule('performance')" data-page-node-id="cTO8HrxlLuSrzd9nDy4qrp">📊 绩效管理</button>
    <button class="mod-tab keep" data-mod="beauty" onclick="switchModule('beauty')" data-page-node-id="maSEZIZaLq7esXXJABvoUv">💄 美妆话术</button>
    <button class="mod-tab keep" data-mod="daily" onclick="switchModule('daily')" data-page-node-id="0ZQKCzL3CGxL5gcbwW8vpU">❓ 日常问题</button>
    <button class="mod-tab keep" data-mod="manual" onclick="switchModule('manual')" data-page-node-id="16VCdRNReCMYPnJQ1m9LZd">📕 手册奖惩</button>
    <button class="mod-tab" data-mod="home" onclick="switchModule('home')">🏠 CC 之家</button>
    <button class="mod-tab" data-mod="medical" onclick="switchModule('medical')" data-page-node-id="YKyirJlt3f6LRF1fmROJfP">🚑 医疗急救</button>
    <button class="mod-tab" data-mod="risk" onclick="switchModule('risk')" data-page-node-id="zBc8alWHgO1Jtz1ynUv3Nd">⚠️ 风险预警</button>
    <button class="mod-tab" data-mod="report" onclick="switchModule('report')" data-page-node-id="zuRGGdaicD84fn0TQmDPKC">🗂 事件报告</button>
    <button class="mod-tab" data-mod="kbadmin" onclick="switchModule('kbadmin')" data-page-node-id="tx5VFathdAJZK2NlztrCsA">📇 库管理</button>
    <button class="mod-tab" data-mod="issues" onclick="switchModule('issues')">🐞 问题反馈</button>
  
    <!-- 2026-09-19：其余 9 个板块的统一入口。放在页签之后（它属于导航，不是右侧工具），
         宽屏带文字「全部应用」，窄屏只留图标；点击展开分组面板（12 板块 + 子入口深跳）。 -->
    <button class="nav-more-btn" id="megaBtn" onclick="toggleMegaMenu(event)" title="工具区 · 其余 6 个板块（医疗急救 / 风险预警 / 事件报告 / 库管理 / CC 之家 / 问题反馈）" aria-haspopup="true" aria-expanded="false" aria-label="工具区"><svg width="15" height="15" viewBox="0 0 15 15" fill="currentColor" aria-hidden="true"><rect x="0" y="0" width="6.4" height="6.4" rx="1.6"/><rect x="8.6" y="0" width="6.4" height="6.4" rx="1.6"/><rect x="0" y="8.6" width="6.4" height="6.4" rx="1.6"/><rect x="8.6" y="8.6" width="6.4" height="6.4" rx="1.6"/></svg><span class="amb-tx">全部应用</span></button></nav>

  <div class="actions" data-page-node-id="xvsfdyRVOsuES5oDEHTAxU">
    <!-- 2026-09-19：右侧工具组不再放 ⊞（避免与页签行的「全部应用」重复入口），
         工具区入口统一由页签行的 nav-more-btn 承担 -->
        <!-- 2026-09-19 右侧重排：操作层（⊞ / 备份 / 主题）｜信息层（时间·日期·节日 / 在线）｜身份层（头像+姓名+角色）
     数据包入口（📦）已按用户要求删除；功能引擎保留但不再有顶栏入口。 -->
    <button class="bk-btn" onclick="openBackupModal()" title="数据备份 / 恢复" data-page-node-id="yJEzRlHehPesFrCYNcuR2w">💾<span class="act-tx" data-page-node-id="D8dPr7NsCFVzN5sv77yABH">备份</span></button>
    <button class="theme-btn" id="themeBtn" onclick="cycleTheme()" title="切换主题" data-page-node-id="nKFuYQoLJzNJX7tUXNbM92">☀️</button>
    <span class="act-sep" aria-hidden="true"></span>
    <div class="sys-clock" id="sysClock" title="跟随本机系统时间；自动匹配今日节气/节假日" data-page-node-id="YcWUcjjvl8tXBH9OHVEJmv"><span class="sc-time" id="scTime" data-page-node-id="QIGEHR28sZNyYPC6CXIxDB">--:--</span><span class="sc-row" data-page-node-id="YcWUcjjvl8tXBH9OHVEJmw"><span class="sc-date" id="scDate" data-page-node-id="KvFc3yOf1fd3eZ4Z6E1mCb"></span><span class="sc-tag none" id="scTag" data-page-node-id="riZ1tAMXHe3AbUojpRyaeC"></span></span></div>
    <div class="net-status" id="netStatus" data-page-node-id="vkrxK1uBwhkYGKD0uhiCmp"><span class="net-dot" data-page-node-id="tCVfoaLMzGGyADvUivJb33"></span><span id="netText" data-page-node-id="bTFVLcLuAOrQnh9aLGPNvP">在线</span></div>
    <span class="act-sep" aria-hidden="true"></span>
    <div class="user-chip" id="userChip" onclick="openProfileModal()" title="点击编辑姓名 / 头像" data-page-node-id="Ur7gOsSYWSPqAs1rVeKZdU">
      <div class="avatar" data-page-node-id="55JJfKYQLvolbLuBnShvLA"><div id="avatarLetter" data-page-node-id="d9A7oxFJVUcBBdYXREsfH7">乘</div><img id="avatarImg" alt="" style="display:none" data-page-node-id="QUb2UZh2NTAzjpTGTVYi1C"></div>
      <div class="uc-tx">
        <span id="userName" data-page-node-id="kapg4qXiKzfZXEKqnDjuMq">乘务员</span>
        <span class="uc-role" id="userRole"></span>
      </div>
      <span class="uc-caret" aria-hidden="true">›</span>
    </div>
    <script>/* 身份层兜底（2026-09-19）：不依赖各壳的增强脚本，独立读会话填角色。
       放在 actions 块内 → 随壳层同步补丁一起进两份内嵌 TEMPLATE，三个壳行为一致。 */
    (function(){try{var s=JSON.parse(localStorage.getItem('cabin_session_v1')||'null');var r=document.getElementById('userRole');
      if(r&&s)r.textContent=(s.role==='admin'||s.工号==='028981')?'管理员':'乘务员';}catch(e){}})();
    </script>
  </div>
</header>

<main class="sys-area" id="sysArea" tabindex="-1">
  <div class="sys-wrap" id="wrap-qa">
    <div class="sys-loader" id="loader-qa"><div class="sys-spinner"></div><div class="sl-text">正在进入 你问我答 …</div></div>
    <iframe class="sys-frame" id="frame-qa"></iframe>
  </div>
  <div class="sys-wrap" id="wrap-home">
    <div class="sys-loader" id="loader-home"><div class="sys-spinner"></div><div class="sl-text">正在进入 CC 之家 …</div></div>
    <iframe class="sys-frame" id="frame-home"></iframe>
  </div>
  <div class="sys-wrap active" id="wrap-quiz">
    <div class="sys-loader" id="loader-quiz"><div class="sys-spinner"></div><div class="sl-text">正在进入 培训考核 …</div></div>
    <iframe class="sys-frame" id="frame-quiz"></iframe>
  </div>
  <div class="sys-wrap" id="wrap-performance">
    <div class="sys-loader" id="loader-performance"><div class="sys-spinner"></div><div class="sl-text">正在进入 绩效管理 …</div></div>
    <iframe class="sys-frame" id="frame-performance"></iframe>
  </div>
  <div class="sys-wrap" id="wrap-beauty">
    <div class="sys-loader" id="loader-beauty"><div class="sys-spinner"></div><div class="sl-text">正在进入 美妆话术 …</div></div>
    <iframe class="sys-frame" id="frame-beauty"></iframe>
  </div>
  <div class="sys-wrap" id="wrap-medical">
    <div class="sys-loader" id="loader-medical"><div class="sys-spinner"></div><div class="sl-text">正在进入 医疗急救 …</div></div>
    <iframe class="sys-frame" id="frame-medical"></iframe>
  </div>
  <div class="sys-wrap" id="wrap-risk">
    <div class="sys-loader" id="loader-risk"><div class="sys-spinner"></div><div class="sl-text">正在进入 风险预警（精简版）…</div></div>
    <iframe class="sys-frame" id="frame-risk"></iframe>
  </div>
  <div class="sys-wrap" id="wrap-daily">
    <div class="sys-loader" id="loader-daily"><div class="sys-spinner"></div><div class="sl-text">正在进入 日常问题 …</div></div>
    <iframe class="sys-frame" id="frame-daily"></iframe>
  </div>
  <div class="sys-wrap" id="wrap-manual">
    <div class="sys-loader" id="loader-manual"><div class="sys-spinner"></div><div class="sl-text">正在进入 手册奖惩 …</div></div>
    <iframe class="sys-frame" id="frame-manual"></iframe>
  </div>
  <div class="sys-wrap" id="wrap-report">
    <div class="sys-loader" id="loader-report"><div class="sys-spinner"></div><div class="sl-text">正在进入 事件报告 …</div></div>
    <iframe class="sys-frame" id="frame-report"></iframe>
  </div>
  <div class="sys-wrap" id="wrap-kbadmin">
    <div class="sys-loader" id="loader-kbadmin"><div class="sys-spinner"></div><div class="sl-text">正在进入 库管理 …</div></div>
    <iframe class="sys-frame" id="frame-kbadmin"></iframe>
  </div>
  <div class="sys-wrap" id="wrap-issues">
    <div class="sys-loader" id="loader-issues"><div class="sys-spinner"></div><div class="sl-text">正在进入 问题反馈 …</div></div>
    <iframe class="sys-frame" id="frame-issues"></iframe>
  </div>
</main>

<div class="toast-container" id="toastContainer"></div>

<!-- ===== 手机端底部 TabBar（APP 式主导航） ===== -->
<nav class="m-tabbar" id="mTabbar" aria-label="底部导航">
  <button class="m-tab" data-mod="qa" onclick="mGo('qa')"><span class="mi">💬</span>问答</button>
  <button class="m-tab" data-mod="quiz" onclick="mGo('quiz')"><span class="mi">📚</span>培训</button>
  <button class="m-tab" data-mod="performance" onclick="mGo('performance')"><span class="mi">📊</span>绩效</button>
  <button class="m-tab" data-mod="beauty" onclick="mGo('beauty')"><span class="mi">💄</span>美妆</button>
  <button class="m-tab" data-mod="more" onclick="mGo('more')"><span class="mi">☰</span>更多</button>
</nav>

<!-- 「更多」底部面板 -->
<div class="m-sheet-mask" id="mSheetMask" onclick="closeMoreSheet()"></div>
<div class="m-sheet" id="mSheet" role="dialog" aria-label="全部板块">
  <h4>全部板块 <span class="ms-sub">12 个板块 · 与顶栏「全部应用」同源</span><button class="modal-x" onclick="closeMoreSheet()" aria-label="关闭">✕</button></h4>
  <div class="m-sheet-grid">
    <div class="m-sheet-sec">乘务服务</div>
    <button class="m-sheet-item" data-mod="home" onclick="mGoMod('home')"><span class="mi">🏠</span>CC 之家</button>
    <button class="m-sheet-item" data-mod="qa" onclick="mGoMod('qa')"><span class="mi">💬</span>你问我答</button>
    <button class="m-sheet-item" data-mod="medical" onclick="mGoMod('medical')"><span class="mi">🚑</span>医疗急救</button>
    <button class="m-sheet-item" data-mod="daily" onclick="mGoMod('daily')"><span class="mi">❓</span>日常问题</button>
    <div class="m-sheet-sec">训练成长</div>
    <button class="m-sheet-item" data-mod="quiz" onclick="mGoMod('quiz')"><span class="mi">📚</span>培训考核</button>
    <button class="m-sheet-item" data-mod="performance" onclick="mGoMod('performance')"><span class="mi">📊</span>绩效管理</button>
    <button class="m-sheet-item" data-mod="beauty" onclick="mGoMod('beauty')"><span class="mi">💄</span>美妆话术</button>
    <div class="m-sheet-sec">运营管理</div>
    <button class="m-sheet-item" data-mod="risk" onclick="mGoMod('risk')"><span class="mi">⚠️</span>风险预警</button>
    <button class="m-sheet-item" data-mod="manual" onclick="mGoMod('manual')"><span class="mi">📕</span>手册奖惩</button>
    <button class="m-sheet-item" data-mod="report" onclick="mGoMod('report')"><span class="mi">🗂</span>事件报告</button>
    <button class="m-sheet-item" data-mod="kbadmin" onclick="mGoMod('kbadmin')"><span class="mi">📇</span>库管理</button>
    <button class="m-sheet-item" data-mod="issues" onclick="mGoMod('issues')"><span class="mi">🐞</span>问题反馈</button>
  </div>
</div>

<!-- ===== 全局数据备份 / 恢复 ===== -->
<div class="modal-mask" id="backupModal" onclick="if(event.target===this)closeBackupModal()">
  <div class="modal-card">
    <h3>💾 数据备份与恢复</h3>
    <p class="m-sub">备份包含：错题本与成绩、绩效数据、美妆收藏与定制话术、AI 配置、手册收藏、风险预警设置等全部本地数据。<br>内容数据包（知识/销售/题库）随团队发布更新，不随个人备份迁移。<br><br>换手机时：导出备份文件 → 通过微信「文件传输助手」或网盘发送给自己 → 在新手机打开助手后导入。</p>
    <div class="m-actions">
      <button class="m-btn primary" onclick="exportBackup()">⬇️ 导出备份文件</button>
      <button class="m-btn ghost" onclick="document.getElementById('bkFile').click()">⬆️ 从文件恢复备份</button>
    </div>
    <input type="file" id="bkFile" accept=".json,application/json" style="display:none" onchange="importBackup(this.files[0])">
    <div class="m-meta" id="bkMeta"></div>
  </div>
</div>

<!-- ===== 数据包在线更新（M2）：2026-09-19 按用户要求删除顶栏入口与弹窗。
     引擎（window.PACKS）保留：kbadmin 数据包中心与构建链 M3 单测仍依赖它。 ===== -->

<!-- ===== 个人资料（姓名 / 头像） ===== -->
<div class="modal-mask" id="profileModal" onclick="if(event.target===this)closeProfileModal()">
  <div class="modal-card">
    <h3>👤 个人资料</h3>
    <p class="m-sub">设置顶栏显示的姓名与头像，本地保存，并随 💾 备份恢复迁移。</p>
    <div class="profile-avatar-preview" id="profileAvatar" onclick="document.getElementById('pfFile').click()" title="点击选择图片">
      <img id="profileAvatarImg" alt="" style="display:none">
      <span id="profileAvatarLetter">乘</span>
      <div class="cam">📷 更换</div>
    </div>
    <div style="text-align:center">
      <button class="pf-del" type="button" onclick="clearAvatar()">🗑 删除头像</button>
    </div>
    <div class="pf-field">
      <label for="pfName">姓名</label>
      <input type="text" id="pfName" maxlength="12" placeholder="请输入姓名">
    </div>
    <div class="m-actions">
      <button class="m-btn primary" onclick="saveProfile()">💾 保存</button>
      <button class="m-btn ghost" onclick="closeProfileModal()">取消</button>
    </div>
    <input type="file" id="pfFile" accept="image/*" style="display:none" onchange="handleAvatarFile(this.files[0])">
  </div>
</div>

<script>
/* ===================== 四大系统完整功能数据（gzip 压缩 base64 内嵌，运行时解压） ===================== */
const MODULES = {
  home: "__B64_home__",
  qa: "__B64_qa__",
  quiz: "__B64_quiz__",
  performance: "__B64_performance__",
  beauty: "__B64_beauty__",
  medical: "__B64_medical__",
  risk: "__B64_risk__",
  daily: "__B64_daily__",
  manual: "__B64_manual__",
  report: "__B64_report__",
  kbadmin: "__B64_kbadmin__",
  issues: "__B64_issues__"
};

/* ===================== 解码引擎（gzip 解压；兼容未压缩旧数据回退） ===================== */
const _frames = {};
function _b64ToBytes(b64){
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for(let i=0;i<bin.length;i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}
// 内嵌 pako 解压库（约 47KB）：DecompressionStream 不可用的旧浏览器（Safari < 16.4 等）降级用
__PAKO_SRC__
async function _bytesToHtml(bytes){
  // gzip 数据头部：0x1f 0x8b
  if(bytes[0] === 0x1f && bytes[1] === 0x8b){
    // 优先使用原生 DecompressionStream（Chrome 80+ / Safari 16.4+ / Firefox 113+）
    if(typeof DecompressionStream !== 'undefined'){
      try{
        const ds = new DecompressionStream('gzip');
        const stream = new Blob([bytes]).stream().pipeThrough(ds);
        const ab = await new Response(stream).arrayBuffer();
        return new TextDecoder('utf-8').decode(ab);
      }catch(e){ /* 原生解压失败，降级到 pako */ }
    }
    // 降级：pako 纯 JS 解压（兼容 Safari < 16.4 / 旧 Android WebView）
    var _pk = window.pako;
    if(_pk && typeof _pk.inflate === 'function'){
      try{
        const out = _pk.inflate(bytes);
        return new TextDecoder('utf-8').decode(out);
      }catch(e){ /* 降级解压失败，回退原文解码 */ }
    }
    // 无任何解压手段：返回明确错误而不是乱码
    throw new Error('当前浏览器不支持 gzip 解压（DecompressionStream 需 iOS 16.4+ / Chrome 80+），请升级浏览器');
  }
  return new TextDecoder('utf-8').decode(bytes);
}
async function _b64ToHtml(b64){
  return _bytesToHtml(_b64ToBytes(b64));
}
/* ===================== 在线模式：瘦壳按需拉取 mods/<id>.gz + Cache API 缓存 =====================
   （离线单文件 MODULES 内嵌数据非空时不受影响；GitHub Pages 等静态托管部署时首屏只需下载瘦壳，
    各模块按需加载并缓存到 Cache Storage，二次打开/切页签秒开）
   兼容：双击本地文件用 file:// 打开时 fetch 会被浏览器 CORS 拦截（origin null），
   此时自动回退到经典 <script> 注入 mods/<id>.js（脚本标签不受 CORS 限制），本地双击同样可用。 */
var _IS_FILE = (location.protocol === 'file:');
async function _fetchModule(id){
  const url = './mods/' + id + '.gz';
  try{
    if('caches' in window){
      const cache = await caches.open('kz-mod-v1');
      let r = await cache.match(url);
      if(!r){
        const resp = await fetch(url, {cache:'no-cache'});
        if(!resp.ok) throw new Error('HTTP ' + resp.status);
        await cache.put(url, resp.clone());
        r = resp;
      }
      return await _bytesToHtml(new Uint8Array(await r.arrayBuffer()));
    }
  }catch(e){ /* 缓存链路失败，直接拉取，不缓存 */ }
  const resp = await fetch(url);
  if(!resp.ok) throw new Error('模块 [' + id + '] 下载失败（HTTP ' + resp.status + '）。请检查网络连接，或确认已上传 mods 目录（对应在线版部署包）。');
  return await _bytesToHtml(new Uint8Array(await resp.arrayBuffer()));
}
/* file:// 回退：经典脚本标签加载 mods/<id>.js（其内容为 base64(gzip)，载入后写入 window.__MODSRC__） */
function _loadLocalScript(id){
  return new Promise(function(resolve, reject){
    var s = document.createElement('script');
    s.src = './mods/' + id + '.js';
    s.async = true;
    s.onload = function(){
      var b64 = (window.__MODSRC__ || {})[id];
      if(!b64){ reject(new Error('本地模块 [' + id + '] 脚本已加载但内容为空')); return; }
      _b64ToHtml(b64).then(resolve, reject);
    };
    s.onerror = function(){
      _fetchModule(id).then(resolve, function(){
        reject(new Error('本地模块 [' + id + '] 加载失败：请确认 mods 文件夹与本页面放在同一目录下'));
      });
    };
    (document.head || document.documentElement).appendChild(s);
  });
}
async function _loadModule(id){
  if(MODULES[id]) return await _b64ToHtml(MODULES[id]);      // 离线单文件：内嵌数据直接解压
  if(_IS_FILE) return await _loadLocalScript(id);             // file:// 双击打开：脚本注入回退
  return await _fetchModule(id);                             // 在线瘦壳：按需加载并缓存
}
/* 在线模式空闲预取：首屏尽量轻，进入后悄悄缓存其余模块，切换页签时秒开 */
(function(){
  var hasEmbed = Object.keys(MODULES).some(function(k){ return !!MODULES[k]; });
  if(hasEmbed) return;
  if(!_IS_FILE && !('caches' in window)) return;   // file:// 下 Cache API 不可用，但仍可脚本预取
  setTimeout(function(){
    var keys = Object.keys(MODULES).filter(function(k){ return !MODULES[k]; });
    var i = 0;
    (function next(){
      if(i >= keys.length) return;
      var id = keys[i++];
      _loadModule(id).catch(function(){});
      setTimeout(next, _IS_FILE ? 300 : 700);
    })();
  }, _IS_FILE ? 2500 : 1500);
})();

/* ===================== 模块切换（懒加载 + 缓存 + 解压） ===================== */
let currentMod = null;
const _loadBusy = {};
const _modScroll = {};

/* ===== 内嵌模式样式：隐藏各模块自带的顶栏/侧栏，避免"双导航栏" =====
   （模块 Standalone 打开时仍保留自己的导航；嵌入全能助手时由外壳注入 CSS 隐藏） */
const EMBED_BASE = ':root{--embed-bottom:0px;}';
const EMBED_CSS = {
  qa: '.livery-stripe,header.topbar{display:none!important}',
  quiz: '.livery-stripe,.topbar{display:none!important}.sidebar{top:0!important;height:100vh!important}.main{margin-top:0!important;min-height:100vh!important}@media(max-width:720px){.topbar{display:flex!important;position:fixed!important;top:8px!important;right:8px!important;left:auto!important;width:auto!important;height:auto!important;padding:0!important;background:transparent!important;border:none!important;box-shadow:none!important;gap:0!important;z-index:130!important}.topbar>*{display:none!important}.topbar>.hamburger{display:flex!important;width:40px!important;height:40px!important;align-items:center!important;justify-content:center!important;border:1px solid #E5EDE9!important;background:#fff!important;box-shadow:0 2px 10px rgba(0,0,0,.15)!important}}',
  performance: '.livery-stripe{display:none!important}.module-nav{position:static!important;z-index:auto!important}.module-nav .navbar-brand{display:none!important}.module-nav .navbar-toggler{display:none!important}.module-nav .navbar-collapse{display:flex!important;flex-basis:auto!important;flex-grow:1!important}.module-nav .navbar-nav{flex-wrap:wrap!important}.module-content{margin-top:0!important;padding-top:12px!important}',
  daily: '.livery-stripe,header.topbar{display:none!important}',
  manual: 'header.top .t-top{display:none!important}header.top{position:static!important}.menu{position:static!important;top:auto!important}',
  report: '.top .t-title{display:none!important}.top{position:static!important}.menu{position:static!important;top:auto!important}',
  beauty: 'header[class*="bg-gradient-to-r"]{display:none!important}nav[class*="bg-white/80"]{top:0!important}div[class*="top-[120px]"]{top:52px!important}',
  medical: '.headbar{display:none!important}',
  risk: '.topbar .logo,.topbar .user-chip,#appVersionBadge,#btnBackup,#btnGlobalRefresh,button[onclick="logout()"]{display:none!important}.topbar .breadcrumb{flex:1!important;min-width:0!important}',
  kbadmin: 'header.kb-top{display:none!important}.kb-tabs{top:0!important}',
  issues: '.livery-stripe,header.topbar{display:none!important}'
};
function injectEmbedCss(id, frame){
  const css = EMBED_CSS[id];
  const EMBED_BASE = ':root{--embed-bottom:0px;}';
  try{
    const d = frame.contentDocument;
    if(!d) return;
    const existing = d.getElementById('embed-mode-css');
    if(existing) existing.remove();
    const st = d.createElement('style');
    st.id = 'embed-mode-css';
    // 内嵌态公共补偿 + 模块专属隐藏规则：
    // ① 移动端底部 TabBar 会覆盖 iframe 底部，模块自身 max-height:calc(100vh-…)
    //    是按模块视口算的，与 iframe 实际高度不符 → 出现「死带」遮挡（2026-09-16 修复）
    //    这里把真实 TabBar 高度写进 --embed-bottom，由模块 CSS 参与计算。
    // ② 深色模式：Bootstrap 系模块认 data-bs-theme，需一并设置。
    st.textContent = EMBED_BASE + (css || '');
    (d.head || d.documentElement).appendChild(st);
    applyEmbedVars(id, frame);
  }catch(e){}
}

/* ===== 把模块 HTML 填进 iframe =====
   file:// 双击打开时 srcdoc 文档是 opaque origin（origin null），模块内的 localStorage /
   跨窗访问可能被浏览器拦截；此时改为写入 about:blank 文档（继承外壳 origin），并补一个
   <base> 保证相对路径资源仍能解析。http(s) 部署时保持 srcdoc（与历史版本表现一致）。 */
function _fillFrame(frame, html){
  if(_IS_FILE){
    try{
      var d = frame.contentDocument;
      if(d){
        if(/<head[^>]*>/i.test(html)){
          html = html.replace(/<head[^>]*>/i, function(m){ return m + '<base href="' + location.href + '">'; });
        }
        d.open(); d.write(html); d.close();
        return true;            // 同步写入完成，不会再触发 onload
      }
    }catch(e){ /* 写入失败则回退 srcdoc */ }
  }
  frame.srcdoc = html;
  return false;
}
function _onFrameReady(id, frame, loader){
  if(loader) loader.classList.add('hidden');
  _frames[id] = frame;          // 标记已加载，避免每次切模块重复解压初始化
  injectEmbedCss(id, frame);
  if(_modScroll[id] != null){
    requestAnimationFrame(function(){
      try{
        const _sc = frame.contentDocument && frame.contentDocument.querySelector('.main-scroll-container');
        if(_sc) _sc.scrollTop = _modScroll[id];
        else if(frame.contentWindow) frame.contentWindow.scrollTo(0, _modScroll[id]);
      }catch(e){}
    });
  }
  try{
    const doc = frame.contentDocument;
    const t = document.documentElement.getAttribute('data-theme');
    if(doc && doc.documentElement) doc.documentElement.setAttribute('data-theme', t);
  }catch(e){}
}

function switchModule(id){
  if(currentMod === id) return; // 点击当前模块不重进，避免触发 display 切换导致移动端滚动位置丢失

  // 记录当前模块的内部滚动位置
  if(currentMod){
    const _f = document.getElementById('frame-'+currentMod);
    try{
      if(_f && _f.contentDocument){
        const _sc = _f.contentDocument.querySelector('.main-scroll-container');
        _modScroll[currentMod] = _sc ? _sc.scrollTop : (_f.contentWindow ? _f.contentWindow.scrollY : 0);
      }
    }catch(e){}
  }

  currentMod = id;
  document.querySelectorAll('.mod-tab').forEach(b => b.classList.toggle('active', b.dataset.mod===id));
  if(typeof syncMTabbar === 'function') syncMTabbar();
  // 页签横向滚动时，把当前激活页签自动滚到可视区中部（手机/平板 9 个页签尤其需要）
  var _ab = document.querySelector('.mod-tab.active');
  if(_ab && _ab.scrollIntoView){ try{ _ab.scrollIntoView({behavior:'smooth',inline:'center',block:'nearest'}); }catch(e){ _ab.scrollIntoView(); } }
  document.querySelectorAll('.sys-wrap').forEach(w => w.classList.remove('active'));
  const wrap = document.getElementById('wrap-'+id);
  wrap.classList.add('active');

  if(!_frames[id]){
    // 防重入：同一模块加载中再次触发直接忽略，避免对同一 iframe 并发 document.write
    // 造成全局重复声明（如 quiz 模块的 const sampleQuestions）或内容串写
    if(_loadBusy[id]) return;
    _loadBusy[id] = true;
    const loader = document.getElementById('loader-'+id);
    const frame = document.getElementById('frame-'+id);
    _loadModule(id).then(function(html){
      if(loader) loader.classList.remove('hidden');
      var wrote = _fillFrame(frame, html);
      frame.onload = function(){ _onFrameReady(id, frame, loader); };
      if(wrote) _onFrameReady(id, frame, loader);
    }).catch(function(e){
      console.error('模块加载失败:', id, e);
      if(loader) loader.querySelector('.sl-text').textContent = _IS_FILE
        ? '加载失败：请把 mods 文件夹与本页放在同一目录'
        : '加载失败，请刷新重试';
    }).then(function(){ _loadBusy[id] = false; });
  } else if(_modScroll[id] != null){
    const frame = _frames[id];
    requestAnimationFrame(function(){
      try{
        const _sc = frame.contentDocument && frame.contentDocument.querySelector('.main-scroll-container');
        if(_sc) _sc.scrollTop = _modScroll[id];
        else if(frame.contentWindow) frame.contentWindow.scrollTo(0, _modScroll[id]);
      }catch(e){}
    });
  }
}

/* ===================== 主题 ===================== */
let hostTheme = 'light';
const ALL_MODS = ['qa','home','quiz','performance','beauty','risk','medical','daily','manual','report','kbadmin','issues'];
function applyEmbedVars(id, frame){
  if(!frame) return;
  try{
    const d = frame.contentDocument, w = frame.contentWindow;
    if(!d || !d.documentElement) return;
    const tb = document.getElementById('mTabbar');
    let h = 0;
    if(tb && w && w.innerWidth <= 720){
      const r = tb.getBoundingClientRect();
      h = Math.round(r.height) || 0;
    }
    d.documentElement.style.setProperty('--embed-bottom', h + 'px');
    const t = document.documentElement.getAttribute('data-theme') || 'light';
    d.documentElement.setAttribute('data-theme', t);
    // Bootstrap 5.3 原生暗色走 data-bs-theme
    d.documentElement.setAttribute('data-bs-theme', t === 'dark' ? 'dark' : 'light');
    if(d.body) d.body.setAttribute('data-bs-theme', t === 'dark' ? 'dark' : 'light');
  }catch(e){}
}
function applyTheme(t){
  hostTheme = t;
  document.documentElement.setAttribute('data-theme', t);
  document.documentElement.setAttribute('data-bs-theme', t === 'dark' ? 'dark' : 'light');
  const btn = document.getElementById('themeBtn');
  if(btn) btn.textContent = t==='dark' ? '🌙' : '☀️';
  // 同步已加载的模块（含 data-bs-theme，Bootstrap 系模块据此切换原生暗色）
  ALL_MODS.forEach(id=>{
    const f = document.getElementById('frame-'+id);
    if(f && f.contentDocument){ try{ applyEmbedVars(id, f); }catch(e){} }
  });
}
function frameObj(id){ return document.getElementById('frame-'+id); }
function cycleTheme(){
  hostTheme = hostTheme==='light' ? 'dark' : 'light';
  applyTheme(hostTheme);
  toast(hostTheme==='dark' ? '已切换深色模式' : '已切换浅色模式');
}

/* ===================== TOAST ===================== */
function toast(msg, type){
  type = type || 'info';
  const c = document.getElementById('toastContainer');
  const t = document.createElement('div');
  t.className = 'toast toast-'+type;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(()=>{ t.style.animation='slideIn .3s reverse forwards'; setTimeout(()=>t.remove(),300); }, 2600);
}

/* ===================== 全局数据备份 / 恢复 ===================== */
const BACKUP_MAGIC = 'spring-cabin-assistant-backup';
const BACKUP_VER = 1;
// 易失/临时类键不随备份恢复（缓存、首次引导标记等，恢复后会自动重建）
const BACKUP_EXCLUDE = {
  'cabin_first_time_seen': 1,   // 首次使用引导标记
  'cabin_session_v1': 1,        // 登录会话（不随备份迁移，避免换机恢复旧登录态）
  'cabin_users_v1': 1,          // 本机账号（个人凭证不随备份迁移）
  '_app_last_version': 1,       // 风险模块版本标记（用于版本更新清缓存）
  'filtered_overview_v1': 1,    // 风险模块首页概览缓存
  'briefing_today_v1_cache': 1,  // 今日简报缓存
  'packs_index': 1               // 数据包索引（内容层）
};
// 内容层（数据包 / 新旧覆盖层）属"团队发布的内容"，不随个人备份迁移——避免换机或回滚时覆盖他人发布的数据
const BACKUP_EXCLUDE_PREFIX = ['pack:', 'kb_overlay_v1'];
function isBackupExcluded(k){
  if(!k) return true;
  if(BACKUP_EXCLUDE[k]) return true;
  for(let i = 0; i < BACKUP_EXCLUDE_PREFIX.length; i++) if(k.indexOf(BACKUP_EXCLUDE_PREFIX[i]) === 0) return true;
  return false;
}
function collectBackupKeys(){
  const keys = [];
  try{
    for(let i = 0; i < localStorage.length; i++){
      const k = localStorage.key(i);
      if(!isBackupExcluded(k)) keys.push(k);
    }
  }catch(e){}
  return keys;
}
function openBackupModal(){
  document.getElementById('backupModal').classList.add('show');
  const meta = document.getElementById('bkMeta');
  try{
    const keys = collectBackupKeys();
    let bytes = 0;
    for(let i = 0; i < keys.length; i++) bytes += (localStorage.getItem(keys[i]) || '').length * 2;
    meta.textContent = '本机共 ' + localStorage.length + ' 项数据（含 ' + keys.length + ' 项）· ' + (bytes/1048576).toFixed(2) + ' MB';
  }catch(e){ meta.textContent = ''; }
}
function closeBackupModal(){
  document.getElementById('backupModal').classList.remove('show');
}
function exportBackup(){
  try{
    const keys = collectBackupKeys();
    const data = {};
    for(let i = 0; i < keys.length; i++) data[keys[i]] = localStorage.getItem(keys[i]);
    const payload = {
      magic: BACKUP_MAGIC,
      version: BACKUP_VER,
      app: '客舱小助手',
      exportedAt: new Date().toISOString(),
      keyCount: keys.length,
      keys: data
    };
    const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    const d = new Date();
    const pad = n => (n < 10 ? '0' + n : '' + n);
    a.download = '客舱小助手备份_' + d.getFullYear() + pad(d.getMonth()+1) + pad(d.getDate()) + '.json';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    toast('备份已导出（' + keys.length + ' 项数据）');
  }catch(e){
    toast('导出失败：' + e.message);
  }
}
function importBackup(file){
  const input = document.getElementById('bkFile');
  const reset = () => { input.value = ''; };
  if(!file){ reset(); return; }
  const reader = new FileReader();
  reader.onload = function(ev){
    try{
      const payload = JSON.parse(ev.target.result);
      if(!payload || payload.magic !== BACKUP_MAGIC || typeof payload.keys !== 'object' || payload.keys === null){
        toast('不是有效的备份文件'); reset(); return;
      }
      if(payload.version > BACKUP_VER){
        toast('备份来自更新版本，请先升级助手再恢复'); reset(); return;
      }
      const entries = Object.keys(payload.keys);
      if(!entries.length){ toast('备份文件为空'); reset(); return; }
      let ok = 0;
      for(let i = 0; i < entries.length; i++){
        try{ localStorage.setItem(entries[i], payload.keys[entries[i]]); ok++; }catch(e){}
      }
      if(ok){
        toast('已恢复 ' + ok + ' 项数据，正在刷新…');
        setTimeout(() => location.reload(), 800);
      }else{
        toast('恢复失败：存储空间不足或浏览器限制');
        reset();
      }
    }catch(e){
      toast('备份文件解析失败');
      reset();
    }
  };
  reader.onerror = function(){ toast('读取文件失败'); reset(); };
  reader.readAsText(file);
}

/* ===================== 数据包在线更新（M2）：manifest 拉取 + 顶栏提示 + 一键安装 =====================
 * 加固：①所有请求带超时（AbortController），弱网不再无限等待；
 *       ②源站 github.io 不可达时自动回源 jsdelivr 镜像（中国大陆可访问），manifest/数据包均支持；
 *       ③manifest 本地缓存 1 小时，避免每次打开都慢速拉取；
 *       ④下载失败给出可操作提示（不再出现"联系管理员"的歧义文案）。
 */
const PACKS_MANIFEST_URL = 'https://7528ardg.github.io/LEI/packs/manifest.json';
const PACKS_MANIFEST_KEY = 'packs_manifest_url';
const PACKS_MANIFEST_CACHE_KEY = 'packs_manifest_cache';
const PACKS_MANIFEST_TTL = 60 * 60 * 1000;   // manifest 本地缓存有效期（1 小时）
const PACKS_MIRROR_BASE = 'https://cdn.jsdelivr.net/gh/7528ardg/LEI@main/'; // 中国大陆可访问镜像
const PACKS_FETCH_TIMEOUT = 8000;            // 单次请求超时（毫秒）
const PACKS_TYPE_LABEL = { kb:'知识包', sales:'销售包', quiz:'题库包', notice:'通知识包' };
var packsUpdateReady = [];
function getPacksManifestUrl(){
  try{ const u = localStorage.getItem(PACKS_MANIFEST_KEY); if(u) return u; }catch(e){}
  return PACKS_MANIFEST_URL;
}
/* 可覆盖源站基址：默认 github.io；若用户自定义 manifest 地址则按其目录推导，保证相对 url 可解析 */
function getPacksBase(){
  try{
    const u = localStorage.getItem(PACKS_MANIFEST_KEY);
    if(u){ const i = u.lastIndexOf('/'); if(i > 0) return u.slice(0, i + 1); }
  }catch(e){}
  return 'https://7528ardg.github.io/LEI/';
}
function absPackUrl(rel){
  if(/^https?:\/\//i.test(rel)) return rel;
  return getPacksBase() + String(rel).replace(/^\.?\//,'');
}
function escHtml(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
/* 带超时的 fetch：ms 内未返回即中断（AbortError），防止弱网下无限等待 */
function fetchWithTimeout(url, ms){
  const ctrl = (typeof AbortController !== 'undefined') ? new AbortController() : null;
  let timer = null;
  if(ctrl) timer = setTimeout(function(){ ctrl.abort(); }, ms || PACKS_FETCH_TIMEOUT);
  return new Promise(function(resolve, reject){
    fetch(url, { cache:'no-store', signal: ctrl ? ctrl.signal : undefined })
      .then(function(r){ if(timer) clearTimeout(timer); resolve(r); })
      .catch(function(e){ if(timer) clearTimeout(timer); reject(e); });
  });
}
/* 依次尝试多个地址（源站 → 镜像），全部失败才 reject */
function fetchFirst(urls, ms){
  const list = Array.isArray(urls) ? urls.slice() : [urls];
  let i = 0;
  function next(){
    if(i >= list.length) return Promise.reject(new Error('所有下载地址均不可达'));
    const u = list[i++];
    return fetchWithTimeout(u, ms).catch(function(){ return next(); });
  }
  return next();
}
/* 纯函数：manifest + 本地索引 → 待更新包列表（版本号更高或本机未装） */
function computePackUpdates(man, idx){
  const ready = [];
  if(!man || man.magic !== 'cabin-packs-manifest-v1' || !Array.isArray(man.packs)) return ready;
  man.packs.forEach(p=>{
    if(!p || !p.packId || !p.url) return;
    const local = idx && idx.packs ? idx.packs.find(e=>e.packId === p.packId) : null;
    if(!local){ ready.push(p); return; }
    if(p.version != null && (local.version == null || p.version > local.version)) ready.push(p);
  });
  return ready;
}
function showPacksBadge(ready){
  const b = document.getElementById('packsBadge');
  if(!b) return;
  b.style.display = '';
  const span = b.querySelector('span');
  if(span) span.textContent = '新数据包(' + ready.length + ')';
  try{ toast('发现 ' + ready.length + ' 个新数据包，点击顶栏 📦 可查看安装'); }catch(e){}
}
function readManifestCache(){
  try{
    const s = localStorage.getItem(PACKS_MANIFEST_CACHE_KEY);
    if(!s) return null;
    const c = JSON.parse(s);
    if(!c || !c.man || !c.t) return null;
    return c;
  }catch(e){ return null; }
}
function writeManifestCache(man){
  try{ localStorage.setItem(PACKS_MANIFEST_CACHE_KEY, JSON.stringify({ t: Date.now(), man: man })); }catch(e){}
}
function applyManifest(man){
  const idx = window.PACKS ? PACKS.readIndex(localStorage) : null;
  const ready = computePackUpdates(man, idx);
  if(!ready.length) return;
  packsUpdateReady = ready;
  showPacksBadge(ready);
}
function fetchManifest(){
  const urls = [getPacksManifestUrl()];
  const primary = urls[0];
  // 镜像与源站同相对路径；加 ?cb= 强制回源，避免 CDN 缓存旧版清单
  if(primary.indexOf(PACKS_MIRROR_BASE) !== 0){
    urls.push(PACKS_MIRROR_BASE + 'packs/manifest.json?cb=' + Date.now());
  }
  return fetchFirst(urls, PACKS_FETCH_TIMEOUT).then(function(r){
    if(!r.ok) throw new Error('manifest HTTP ' + r.status);
    return r.json();
  });
}
function checkPacksUpdate(){
  if(typeof navigator !== 'undefined' && !navigator.onLine) return;
  const cached = readManifestCache();
  if(cached && (Date.now() - cached.t < PACKS_MANIFEST_TTL)){ applyManifest(cached.man); return; }
  fetchManifest()
    .then(function(man){ writeManifestCache(man); applyManifest(man); })
    .catch(function(){ /* 网络不可达：有缓存（即使过期）也展示，弱网/离线仍能看到待装包 */ if(cached) applyManifest(cached.man); });
}
function openPacksModal(){
  if(!packsUpdateReady.length) return;
  const body = document.getElementById('packsModalBody');
  if(!body) return;
  body.innerHTML = '团队发布了 <b>' + packsUpdateReady.length + '</b> 个数据包，安装后 qa·美妆·考核立即生效（不随个人备份迁移）：<br>'
    + packsUpdateReady.map(p=>'· <b>' + escHtml(p.title || p.packId) + '</b>（' + (PACKS_TYPE_LABEL[p.type] || p.type) + ' v' + (p.version != null ? p.version : 1) + ' · ' + escHtml(p.updatedAt || '') + '）').join('<br>');
  document.getElementById('packsModal').classList.add('show');
}
function closePacksModal(){ const m=document.getElementById('packsModal'); if(m) m.classList.remove('show'); }
function closeModalId(id){ const m=document.getElementById(id); if(m) m.classList.remove('show'); }
/* ④ 背景退后：安全读写宿主 <html> 的 .csn-recede（无头环境/宿主 documentElement 缺失时不报错） */
function fxRecede(on){
  try{
    const el = document.documentElement;
    if(!el || !el.classList) return;
    el.classList[on ? 'add' : 'remove']('csn-recede');
  }catch(e){}
}
function fxModal(mask, opts){
  if(!mask || !mask.classList || mask._fxReady) return mask;
  opts = opts || {};
  const card = mask.querySelector('.modal-card') || mask.firstElementChild;
  mask._fxReady = true;
  mask._fxCard = card;

  // 定位方向：按触发点的水平位置给出 origin
  function directionFor(ev){
    if(!card) return '';
    try{
      const r = card.getBoundingClientRect();
      const x = (ev && ev.clientX) ? ev.clientX : (window.innerWidth / 2);
      return x < r.left + r.width / 2 ? 'from-left' : 'from-right';
    }catch(e){ return ''; }
  }
  // 安全读写卡片类名（无头测试桩可能不含 classList）
  function cardCls(on, name){
    try{ if(card && card.classList) card.classList[on ? 'add' : 'remove'](name); }catch(e){}
  }

  const origAdd = mask.classList.add.bind(mask.classList);
  mask.classList.add = function(){
    const args = Array.prototype.slice.call(arguments);
    origAdd.apply(null, args);
    if(args.indexOf('show') >= 0){
      /* __FOG_GUARD_20260919__：开弹窗前先收掉可能残留的新手教程雾层，
         避免「教程雾层(z=5200) × 弹窗雾层(z=400)」叠加成整屏雾、或教程卡片缺失时只见雾不见卡片 */
      try{
        const _tour = document.querySelector('.tour-overlay.show');
        if(_tour) _tour.classList.remove('show');
      }catch(e){}
      fxRecede(true);
      if(card){
        cardCls(false, 'fx-out');
        try{ void card.offsetWidth; }catch(e){}
        cardCls(true, 'fx-in');
        if(mask._fxDir) cardCls(true, mask._fxDir);
        /* 兜底：任何情况下卡片必须可见——只出现雾不见卡片即视为故障观感 */
        try{ card.style.opacity = ''; }catch(e){}
      }
    }
  };
  const origRemove = mask.classList.remove.bind(mask.classList);
  mask.classList.remove = function(){
    const args = Array.prototype.slice.call(arguments);
    origRemove.apply(null, args);
    if(args.indexOf('show') >= 0){
      fxRecede(false);
      cardCls(false, 'fx-in');
    }
  };
  mask._fxSetDir = function(ev){ const d = directionFor(ev); mask._fxDir = d; };
  return mask;
}
document.addEventListener('keydown',function(e){ if(e.key==='Escape'){ ['packsModal','backupModal','profileModal'].forEach(function(id){ closeModalId(id); }); } });
async function fetchPackText(p, sha256){
  // p 为清单条目；依次尝试 源站 → 镜像，sha256 校验通过才返回（镜像缓存过期自动跳过）
  const rel = p && p.url;
  if(!rel) throw new Error('缺少下载地址');
  const urls = [absPackUrl(rel)];
  const relClean = String(rel).replace(/^\.?\//,'');
  if(urls[0].indexOf(PACKS_MIRROR_BASE) !== 0){
    urls.push(PACKS_MIRROR_BASE + relClean + '?cb=' + Date.now());
  }
  let lastErr = null;
  for(const u of urls){
    try{
      const r = await fetchWithTimeout(u, PACKS_FETCH_TIMEOUT * 3);
      if(!r.ok) throw new Error('下载失败 HTTP ' + r.status);
      const buf = await r.arrayBuffer();
      if(sha256 && globalThis.crypto && crypto.subtle && crypto.subtle.digest){
        const h = await crypto.subtle.digest('SHA-256', buf);
        const hex = Array.from(new Uint8Array(h)).map(b=>b.toString(16).padStart(2,'0')).join('');
        if(hex !== String(sha256).toLowerCase()) throw new Error('sha256 校验失败');
      }
      return new TextDecoder('utf-8').decode(buf);
    }catch(e){ lastErr = e; }
  }
  throw lastErr || new Error('下载失败');
}
async function installPacksUpdates(){
  const btn = document.getElementById('packsInstallBtn');
  if(btn) btn.disabled = true;
  try{
    let ok = 0, fail = 0;
    for(const p of packsUpdateReady){
      try{
        const text = await fetchPackText(p, p.sha256);
        const pack = JSON.parse(text);
        if(!pack || pack.magic !== (window.PACKS ? PACKS.MAGIC : 'cabin-data-pack-v1')) throw new Error('数据包 magic 不符');
        if(pack.packId !== p.packId) throw new Error('packId 与清单不符');
        const r = window.PACKS ? PACKS.installPack(localStorage, pack, 'url') : { ok:false, reason:'引擎未就绪' };
        if(!r.ok) throw new Error('安装失败：' + r.reason);
        ok++;
      }catch(e){
        fail++;
        toast('「' + (p.title || p.packId) + '」下载失败：' + (e && e.message || e), true);
      }
    }
    if(ok) toast('已安装 ' + ok + ' 个数据包，qa·美妆·考核已自动生效');
    else if(fail) toast('数据包下载失败，请检查网络后重试', true);
    packsUpdateReady = [];
    const b = document.getElementById('packsBadge'); if(b) b.style.display = 'none';
  }finally{
    if(btn) btn.disabled = false;
  }
  closePacksModal();
}

/* ===================== 网络状态 ===================== */
function updateNetworkStatus(){
  const el = document.getElementById('netStatus');
  const txt = document.getElementById('netText');
  if(navigator.onLine){ el.classList.remove('offline'); txt.textContent='在线'; }
  else { el.classList.add('offline'); txt.textContent='离线'; }
}

/* ===================== 模块间跳转（你问我答板块内跳转到其他板块） ===================== */
window.addEventListener('message', function(e){
  const d = e.data;
  if(d && d.type === 'spring-switch' && MODULES[d.module] !== undefined){
    switchModule(d.module);
  }
});

/* ===================== 个人资料（姓名 / 头像） ===================== */
const USER_PROFILE_KEY = 'user_profile';
let pfAvatar = null; // 本次编辑暂存头像；null=未新选（保存沿用已存头像），''=已删除
function readUserProfile(){
  try{
    const raw = localStorage.getItem(USER_PROFILE_KEY);
    if(!raw) return { name:'乘务员', avatar:'' };
    const p = JSON.parse(raw);
    return {
      name: (typeof p.name === 'string' && p.name.trim()) ? p.name.trim() : '乘务员',
      avatar: (typeof p.avatar === 'string') ? p.avatar : ''
    };
  }catch(e){ return { name:'乘务员', avatar:'' }; }
}
function writeUserProfile(name, avatar){
  localStorage.setItem(USER_PROFILE_KEY, JSON.stringify({ name:name, avatar:avatar||'', updatedAt:Date.now() }));
}
function renderUserChip(){
  const p = readUserProfile();
  const letter = document.getElementById('avatarLetter');
  const img = document.getElementById('avatarImg');
  const name = document.getElementById('userName');
  if(!letter || !name) return;
  if(p.avatar && img){
    letter.style.display = 'none';
    img.src = p.avatar;
    img.style.display = '';
  }else{
    letter.textContent = (p.name || '乘').charAt(0);
    letter.style.display = '';
    if(img) img.style.display = 'none';
  }
  name.textContent = p.name;
}
function openProfileModal(){
  pfAvatar = null;
  const p = readUserProfile();
  document.getElementById('pfName').value = p.name;
  const letter = document.getElementById('profileAvatarLetter');
  const img = document.getElementById('profileAvatarImg');
  letter.textContent = (p.name || '乘').charAt(0);
  if(p.avatar){ letter.style.display = 'none'; img.src = p.avatar; img.style.display = ''; }
  else { letter.style.display = ''; img.style.display = 'none'; }
  document.getElementById('profileModal').classList.add('show');
}
function closeProfileModal(){ document.getElementById('profileModal').classList.remove('show'); }
function handleAvatarFile(file){
  const input = document.getElementById('pfFile');
  if(input) input.value = '';
  if(!file) return;
  if(!/^image\//.test(file.type)){ toast('请选择图片文件（JPG/PNG 等）', true); return; }
  const reader = new FileReader();
  reader.onload = function(ev){
    const img = new Image();
    img.onload = function(){
      if(img.naturalWidth > 8192 || img.naturalHeight > 8192){ toast('图片尺寸过大，请选择较小图片', true); return; }
      const size = 96;
      const side = Math.min(img.naturalWidth, img.naturalHeight);
      const sx = (img.naturalWidth - side) / 2, sy = (img.naturalHeight - side) / 2;
      const c = document.createElement('canvas');
      c.width = size; c.height = size;
      const ctx = c.getContext('2d');
      ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, size, size);
      ctx.drawImage(img, sx, sy, side, side, 0, 0, size, size);
      const dataUrl = c.toDataURL('image/jpeg', 0.85);
      pfAvatar = dataUrl;
      const letter = document.getElementById('profileAvatarLetter');
      const av = document.getElementById('profileAvatarImg');
      letter.style.display = 'none';
      av.src = dataUrl; av.style.display = '';
    };
    img.onerror = function(){ toast('图片解析失败，请换一张', true); };
    img.src = ev.target.result;
  };
  reader.onerror = function(){ toast('读取文件失败', true); };
  reader.readAsDataURL(file);
}
function clearAvatar(){
  pfAvatar = '';
  const cur = readUserProfile();
  const letter = document.getElementById('profileAvatarLetter');
  const img = document.getElementById('profileAvatarImg');
  letter.textContent = ((document.getElementById('pfName').value || '').trim() || cur.name || '乘').charAt(0);
  letter.style.display = '';
  img.style.display = 'none';
}
function saveProfile(){
  try{
    const name = (document.getElementById('pfName').value || '').trim() || '乘务员';
    const avatar = (typeof pfAvatar === 'string') ? pfAvatar : readUserProfile().avatar;
    if(avatar && avatar.length > 180000){ toast('头像数据过大，请重新选择较小的图片', true); return; }
    writeUserProfile(name, avatar);
    pfAvatar = null;
    renderUserChip();
    closeProfileModal();
    toast('个人资料已保存');
  }catch(e){
    if(e && e.name === 'QuotaExceededError') toast('存储空间不足，请更换较小的头像', true);
    else toast('保存失败：' + ((e && e.message) || e), true);
  }
}

/* ===================== 启动 ===================== */
applyTheme('light');
updateNetworkStatus();
window.addEventListener('online', updateNetworkStatus);
window.addEventListener('offline', updateNetworkStatus);
/* 2026-09-19 数据包更新提示整体下线（用户要求）：入口已删，开机不再轮询 manifest；
   checkPacksUpdate 保留原实现供 kbadmin 数据包中心与单测复用。 */
renderUserChip();
switchModule('qa');
/* ===================== 手机端底部 TabBar（APP 式导航） ===================== */
function mGo(id){
  if(id === 'more'){ openMoreSheet(); return; }
  closeMoreSheet();
  switchModule(id);
}
function mGoMod(id){ closeMoreSheet(); switchModule(id); }
function openMoreSheet(){
  syncMoreSheet();
  /* 「更多」面板：优先走 CCSheet 引擎
     —— 弹性出现(先抬后落) + 背景退后 + 跟随点击方向滑出 + 拖拽关闭 + 多档磁吸 */
  if(window.CCSheet){
    const items = [
      { key:'home',     icon:'🏠', label:'CC 之家' },
      { key:'risk',     icon:'⚠️', label:'风险预警' },
      { key:'medical',  icon:'🚑', label:'医疗急救' },
      { key:'daily',    icon:'❓', label:'日常问题' },
      { key:'manual',   icon:'📕', label:'手册奖惩' },
      { key:'report',   icon:'🗂', label:'事件报告' },
      { key:'kbadmin',  icon:'📇', label:'库管理' },
      { key:'issues',   icon:'🐞', label:'问题反馈' }
    ].map(function(it){
      it.variant = (it.key === currentMod) ? 'primary' : '';
      it.onClick = function(){ setTimeout(function(){ mGoMod(it.key); }, 60); };
      return it;
    });
    const tb = document.getElementById('mTabbar');
    let ox = null;
    if(tb){
      const r = tb.getBoundingClientRect();
      ox = r.left + r.width * 0.9;   // 「更多」按钮在右下角 → 抽屉从右侧方向滑出
    }
    _moreSheetInst = window.CCSheet.actions({
      title: '全部板块',
      items: items,
      snaps: [0.62, 1],
      originX: ox
    });
    return;
  }
  const sh = document.getElementById('mSheet'), mk = document.getElementById('mSheetMask');
  if(!sh) return;
  sh.classList.add('show'); mk.classList.add('show');
}
var _moreSheetInst = null;
function closeMoreSheet(){
  if(_moreSheetInst){ try{ _moreSheetInst.close('api'); }catch(e){} _moreSheetInst = null; }
  const sh = document.getElementById('mSheet'), mk = document.getElementById('mSheetMask');
  if(sh) sh.classList.remove('show');
  if(mk) mk.classList.remove('show');
}
function syncMoreSheet(){
  document.querySelectorAll('.m-sheet-item').forEach(b => b.classList.toggle('active', b.dataset.mod === currentMod));
}
function syncMTabbar(){
  const pri = ['qa','quiz','performance','beauty'];
  document.querySelectorAll('#mTabbar .m-tab').forEach(b => {
    const m = b.dataset.mod;
    b.classList.toggle('active', m === 'more' ? pri.indexOf(currentMod) < 0 : m === currentMod);
  });
  if(document.getElementById('mSheet')) syncMoreSheet();
}
(function(){
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', function(){ syncMTabbar(); });
  } else { syncMTabbar(); }
  window.addEventListener('resize', function(){
    if(!window.matchMedia('(max-width:720px)').matches) closeMoreSheet();
  });
})();
</script>
<script>__SHELL_ENHANCE__</script>
<style id="mobile-native-hardening">
/* === mobile-native-hardening 2026-09-14 · finesse-ui h5-mobile + impeccable === */
html{-webkit-text-size-adjust:100%;text-size-adjust:100%}
*{-webkit-tap-highlight-color:transparent}
a,button,input,select,textarea,label,summary,[onclick],[role=button]{touch-action:manipulation}
button,[onclick],[role=button]{-webkit-user-select:none;user-select:none}
img{max-width:100%}
button:active,[onclick]:active,a:active,summary:active,[role=button]:active{filter:brightness(.93)}
@media (pointer:coarse){
  input,select,textarea{font-size:16px}
  *{scrollbar-width:none}
  *::-webkit-scrollbar{width:0;height:0;display:none}
}
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}
}
<style id="ccSheetCss">

</style>
<style id="ccSheetCss">
/*__CC_SHEET:v1__*/
/* =============================================================
 * CCSheet · 统一弹窗 / 抽屉交互引擎（2026-09-16）
 * 十种交互：底部抽屉 · 半屏停住 · 全屏展开 · 背景退后 · 弹性出现
 *           拖拽关闭 · 拖拽扩展(磁吸) · 嵌套抽屉 · 抽屉变页面 · 弹窗变成功
 * 用法：CCSheet.open({ id, title, body, actions, snaps:[.5,1], ... })
 * ============================================================= */
:root{
  --csn-snap-half:52vh;
  --csn-radius:22px;
  --csn-ease-elastic:cubic-bezier(.22,1.28,.36,1);   /* 先抬后落 */
  --csn-ease-out:cubic-bezier(.32,.72,.34,1);
  --csn-scrim:rgba(9,20,15,.44);
  --csn-grabber:#D6E2DA;
}
html[data-theme="dark"]{
  --csn-scrim:rgba(0,0,0,.62);
  --csn-grabber:#3A5748;
}
/* ---------- 遮罩：背景退后（变暗 + 模糊 + 轻微缩小）---------- */
.csn-mask{
  position:fixed; inset:0; z-index:520;
  background:var(--csn-scrim);
  opacity:0; pointer-events:none;
  transition:opacity .28s ease;
  -webkit-backdrop-filter:blur(0px); backdrop-filter:blur(0px);
  transition:opacity .28s ease, backdrop-filter .3s ease, -webkit-backdrop-filter .3s ease;
}
.csn-mask.show{opacity:1; pointer-events:auto;}
/* 背景退后：给主内容加类，产生「层级后退」观感 */
.csn-recede .sys-area,
.csn-recede .m-tabbar,
.csn-recede .topbar,
.csn-recede .livery-stripe{
  transform:scale(.955);
  transform-origin:50% 30%;
  transition:transform .34s var(--csn-ease-out), filter .34s ease, opacity .34s ease;
  filter:blur(2.5px) saturate(.92);
}
.csn-recede .csn-mask{ -webkit-backdrop-filter:blur(7px); backdrop-filter:blur(7px); }
/* ---------- 抽屉本体 ---------- */
.csn-sheet{
  position:fixed; left:0; right:0; bottom:0; z-index:530;
  background:var(--bg-card,#fff); color:var(--text,#0F2A1F);
  border-radius:var(--csn-radius) var(--csn-radius) 0 0;
  border-top:1px solid var(--border,#E5EDE9);
  box-shadow:0 -18px 48px rgba(10,30,22,.22);
  display:flex; flex-direction:column;
  max-height:92vh;
  padding-bottom:env(safe-area-inset-bottom,0px);
  transform:translate3d(0,102%,0);
  visibility:hidden;
  will-change:transform;
  touch-action:none;                 /* 由引擎接管手势，避免与页面滚动打架 */
  overscroll-behavior:contain;
}
.csn-sheet.csn-open{visibility:visible;}
.csn-sheet.csn-dragging{transition:none!important;}
/* 弹性出现：先抬后落（overshoot）*/
.csn-sheet.csn-anim-in{transition:transform .42s var(--csn-ease-elastic);}
.csn-sheet.csn-anim-out{transition:transform .26s cubic-bezier(.4,0,1,1);}
/* 抓手 —— 半屏/全屏/抽屉态圆角联动 */
.csn-grab{
  flex:none; padding:9px 0 5px; display:flex; justify-content:center;
  cursor:grab; touch-action:none;
}
.csn-grab i{
  display:block; width:42px; height:4.5px; border-radius:99px;
  background:var(--csn-grabber);
  transition:width .3s var(--csn-ease-out), height .3s var(--csn-ease-out), opacity .3s;
}
.csn-sheet.csn-at-full .csn-grab i{width:30px;opacity:.7;}
/* 标题栏 */
.csn-head{
  flex:none; display:flex; align-items:center; gap:10px;
  padding:2px 18px 12px; border-bottom:1px solid var(--border,#E5EDE9);
}
.csn-head h3{
  margin:0; font-size:1rem; font-weight:800; color:var(--text,#0F2A1F);
  flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
}
.csn-head .csn-sub{font-size:.72rem;color:var(--text2,#5A6F65);font-weight:600;}
.csn-x{
  width:30px;height:30px;border-radius:9px;border:none;flex:none;
  background:var(--primary-mist,#F4F9F6); color:var(--text2,#5A6F65);
  font-size:.9rem; line-height:1; cursor:pointer;
  display:inline-flex; align-items:center; justify-content:center;
  transition:background .2s,color .2s,transform .2s;
}
.csn-x:hover{background:var(--primary-soft,#E8F3EE);color:var(--primary,#148453);}
.csn-x:active{transform:scale(.92);}
/* 内容区 */
.csn-body{
  flex:1 1 auto; min-height:0; overflow-y:auto;
  -webkit-overflow-scrolling:touch;
  padding:14px 18px 8px;
  overscroll-behavior:contain;
  touch-action:pan-y;
}
/* 动作区 */
.csn-foot{
  flex:none; padding:10px 18px 16px; display:flex; gap:10px;
  border-top:1px solid var(--border,#E5EDE9);
}
.csn-foot:empty{display:none;}
.csn-btn{
  flex:1; min-height:44px; border-radius:12px; border:1px solid var(--border,#E5EDE9);
  background:var(--bg,#F5F8F6); color:var(--text,#0F2A1F);
  font-size:.88rem; font-weight:700; cursor:pointer;
  font-family:var(--font-sans,system-ui);
  display:inline-flex; align-items:center; justify-content:center; gap:6px;
  transition:transform .16s, background .2s, color .2s, box-shadow .2s;
}
.csn-btn:active{transform:translateY(1px) scale(.99);}
.csn-btn.primary{
  background:linear-gradient(135deg,#148453 0%,#1FA56A 100%);
  color:#fff; border-color:transparent;
  box-shadow:0 6px 18px rgba(20,132,83,.28);
}
.csn-btn.ghost{background:transparent;}
/* ---------- ① 底部抽屉：跟随点击方向滑出 ---------- */
/* 由 JS 设置 --csn-origin-x，让出场方向跟随触发点水平位置 */
.csn-sheet.csn-slide-dir{
  transform-origin:var(--csn-origin-x,50%) 100%;
}
/* ---------- ② 半屏停住 / ⑦ 拖拽扩展：磁吸档位 ---------- */
.csn-sheet.csn-snap-half{ max-height:var(--csn-snap-half); }
/* ---------- ⑩ 弹窗变成功：按钮形变 + 连贯收尾 ---------- */
.csn-success{
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  gap:12px; padding:26px 18px 30px; text-align:center;
}
.csn-success .csn-tick{
  width:64px;height:64px;border-radius:50%;
  background:linear-gradient(135deg,#148453,#1FA56A); color:#fff;
  display:flex;align-items:center;justify-content:center;font-size:1.9rem;
  transform:scale(.3); opacity:0;
  animation:csnPop .5s var(--csn-ease-elastic) forwards;
}
@keyframes csnPop{ to{transform:scale(1);opacity:1;} }
.csn-success h4{margin:0;font-size:1.02rem;font-weight:800;color:var(--text,#0F2A1F);}
.csn-success p{margin:0;font-size:.82rem;color:var(--text2,#5A6F65);line-height:1.6;}
/* 主按钮形变（宽 -> 圆 -> 复位）*/
.csn-btn.csn-morphing{
  animation:csnMorph .62s var(--csn-ease-out) forwards;
  pointer-events:none;
}
@keyframes csnMorph{
  0%{transform:scale(1);}
  38%{transform:scale(.9);border-radius:12px;}
  62%{transform:scale(1.02);border-radius:52px;}
  100%{transform:scale(1);border-radius:12px;}
}
/* ---------- ⑨ 抽屉变页面：原生过渡，无动画断层 ---------- */
.csn-sheet.csn-to-page{
  transition:transform .34s var(--csn-ease-out), border-radius .34s var(--csn-ease-out);
  border-radius:0;
  max-height:100vh;
  height:100vh;
  top:0;
}
/* 抽屉展开为全屏时的圆角联动 */
.csn-sheet.csn-at-full{border-radius:18px 18px 0 0;}
/* ---------- ⑧ 嵌套抽屉：上层弹出，底层后退缩小变暗 ---------- */
.csn-sheet.csn-nested-behind{
  transform:translate3d(0,0,0) scale(.94);
  filter:brightness(.86) saturate(.94);
  transition:transform .3s var(--csn-ease-out), filter .3s ease;
}
.csn-mask.csn-nested-mask{z-index:540;}
.csn-sheet.csn-nested-top{z-index:550;}
/* ---------- 拖拽提示条（拖拽中显示距离判定进度）---------- */
.csn-hint{
  position:absolute; left:50%; transform:translateX(-50%);
  bottom:calc(100% + 8px);
  padding:5px 12px; border-radius:99px;
  background:rgba(15,42,31,.82); color:#fff;
  font-size:.72rem; font-weight:700; white-space:nowrap;
  opacity:0; transition:opacity .2s; pointer-events:none;
}
.csn-hint.show{opacity:1;}
/* ---------- 兼容：手机档把「更多」面板也纳入引擎视觉 ---------- */
@media (max-width:720px){
  .m-sheet{cursor:grab;}
}
/* =============================================================
 * 既有 .modal-mask / .modal-card 弹窗的动效适配
 * 让旧结构也获得：弹性出现 + 方向性 + 背景退后 + 手机档半屏停靠
 * ============================================================= */
.modal-mask{
  background:var(--csn-scrim);
  -webkit-backdrop-filter:blur(0px); backdrop-filter:blur(0px);
  transition:opacity .26s ease, backdrop-filter .3s ease, -webkit-backdrop-filter .3s ease;
  opacity:0;
}
.modal-mask.show{opacity:1;}
.modal-mask.show{ -webkit-backdrop-filter:blur(6px); backdrop-filter:blur(6px); }
.csn-recede .modal-mask.show{ -webkit-backdrop-filter:blur(9px); backdrop-filter:blur(9px); }

.modal-card{
  transform:translate3d(0,14px,0) scale(.96);
  opacity:0;
  transition:transform .34s var(--csn-ease-elastic), opacity .24s ease;
}
.modal-card.fx-in{transform:none;opacity:1;}
.modal-card.fx-in.from-left{animation:fxInL .4s var(--csn-ease-elastic);}
.modal-card.fx-in.from-right{animation:fxInR .4s var(--csn-ease-elastic);}
@keyframes fxInL{ from{transform:translate3d(-16px,12px,0) scale(.95);opacity:0;} to{transform:none;opacity:1;} }
@keyframes fxInR{ from{transform:translate3d(16px,12px,0) scale(.95);opacity:0;} to{transform:none;opacity:1;} }
.modal-card.fx-out{transform:translate3d(0,10px,0) scale(.97);opacity:0;}

/* 手机档：弹窗改为「底部抽屉 + 半屏停住」形态，更贴近原生 App 手感 */
@media (max-width:720px){
  .modal-mask{align-items:flex-end;padding:0;}
  .modal-card{
    max-width:100%; width:100%;
    border-radius:22px 22px 0 0;
    border-bottom:none;
    padding:20px 18px calc(20px + env(safe-area-inset-bottom,0px));
    max-height:88vh; overflow-y:auto;
    transform:translate3d(0,102%,0);
    transition:transform .42s var(--csn-ease-elastic);
    touch-action:pan-y;
  }
  .modal-card.fx-in{transform:translate3d(0,0,0);}
  .modal-card.fx-in.from-left,
  .modal-card.fx-in.from-right{animation:none;transform:translate3d(0,0,0);}
  /* 手机档拖拽把手提示 */
  .modal-card::before{
    content:''; display:block; width:42px; height:4.5px; border-radius:99px;
    background:var(--csn-grabber); margin:-8px auto 12px;
  }
}
/* __FOG_GUARD_20260919__ 雾状遮罩兜底（① 头像弹窗雾层修复同源）：
   动效 JS 一旦未生效（早期脚本报错 / 老 WebView / 安装时序异常），
   .modal-card 常态是 opacity:0（手机档还停在屏幕外）——
   用户就会看到「整屏雾状半透明遮罩、却没有弹窗卡片」。
   这里给 .show 状态加纯 CSS 兜底：无 fx-in 时卡片也强制可见。 */
.modal-mask.show .modal-card:not(.fx-in){ opacity:1; }
@media (max-width:720px){
  .modal-mask.show .modal-card:not(.fx-in){ transform:translate3d(0,0,0); }
}
@media (prefers-reduced-motion:reduce){
  .csn-mask,.csn-sheet,.csn-recede .sys-area,.csn-recede .m-tabbar{transition-duration:.01ms!important;}
  .csn-success .csn-tick{animation-duration:.01ms!important;}
}
/*__CC_SHEET_END__*/
</style>
</style>
<script id="mobile-native-js">
(function(){
  'use strict';
  if(!window.matchMedia||!matchMedia('(pointer:coarse)').matches)return;
  /* 1) 触感反馈（Android 原生手感；iOS/Safari 自动忽略 vibrate） */
  if(navigator.vibrate){
    addEventListener('pointerdown',function(e){
      var t=e.target;
      if(t&&t.closest&&t.closest('button,[onclick],a,[role="button"]')){
        try{navigator.vibrate(8)}catch(_){}
      }
    },{passive:true,capture:true});
  }
  /* 2) 安全区自动注入：贴边的 fixed/sticky 条补 env(safe-area-inset-*)；
        无贴边条的页面则给 body 补，保证内容不钻进刘海/小白条 */
  var px=function(v){return parseFloat(v)||0};
  function patchOne(el,edge){
    var cs=getComputedStyle(el);
    if(edge==='top'){el.style.paddingTop='calc('+px(cs.paddingTop)+'px + env(safe-area-inset-top,0px))';}
    else{el.style.paddingBottom='calc('+px(cs.paddingBottom)+'px + env(safe-area-inset-bottom,0px))';}
  }
  function walk(){
    var vw=innerWidth,vh=innerHeight,gotTop=false,gotBot=false;
    var els=document.querySelectorAll('body *');
    for(var i=0;i<els.length;i++){
      var el=els[i];if(el.dataset.msa)continue;el.dataset.msa='1';
      var cs=getComputedStyle(el),pos=cs.position;
      if(pos!=='fixed'&&pos!=='sticky')continue;
      var r=el.getBoundingClientRect();
      if(r.width===0||r.height===0)continue;
      if(r.width>=vw*0.95&&r.height>=vh*0.9)continue; /* 全屏遮罩类不碰 */
      var wide=(r.width>=vw*0.9);
      if(!wide)continue;
      if(pos==='fixed'){
        var t=px(cs.top),b=px(cs.bottom);
        if(t>=0&&t<=6){patchOne(el,'top');gotTop=true;}
        else if(b>=0&&b<=2){patchOne(el,'bot');gotBot=true;}
      }else{
        var st=px(cs.top),sb=px(cs.bottom);
        if(cs.top!=='auto'&&st<=6){patchOne(el,'top');gotTop=true;}
        else if(cs.bottom!=='auto'&&sb<=2){patchOne(el,'bot');gotBot=true;}
      }
    }
    var b=document.body,bs=getComputedStyle(b);
    if(!gotTop){b.style.paddingTop='calc('+px(bs.paddingTop)+'px + env(safe-area-inset-top,0px))';}
    if(!gotBot){b.style.paddingBottom='calc('+px(bs.paddingBottom)+'px + env(safe-area-inset-bottom,0px))';}
  }
  function safe(){try{walk()}catch(_){}}
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',safe)}else{safe()}
  addEventListener('load',safe);
  setTimeout(safe,800);
})();
</script>

<script id="ccSheetJs">

</script>
<script id="ccEmbedRefresh">
/* 重新把当前 TabBar 高度与主题写进所有已加载模块 */
function refreshEmbedVars(){
  ['qa','home','quiz','performance','beauty','risk','medical','daily','manual','report','kbadmin','issues'].forEach(function(id){
    const f = document.getElementById('frame-'+id);
    if(f && f.contentDocument){ try{ applyEmbedVars(id, f); }catch(e){} }
  });
}
try{
  window.addEventListener('resize', function(){ refreshEmbedVars(); });
  window.addEventListener('orientationchange', function(){ setTimeout(refreshEmbedVars, 260); });
}catch(e){}
</script>

<script id="ccSheetJs">
/*__CC_SHEET_JS:v1__*/
/* =============================================================
 * CCSheet 引擎实现 —— 十种弹窗交互
 * 设计要点：
 *  - 手势判定：位移距离 + 瞬时速度「双阈值」，快滑（速度够）不等距离即关
 *  - 磁吸：多档位（half / full / closed）就近吸附，中间不停留
 *  - 背景退后：宿主加 .csn-recede，底层缩放+模糊+变暗
 *  - 连动：抓手宽度、圆角、高度随档位同步形变
 * ============================================================= */
(function(){
  'use strict';
  if(window.CCSheet) return;

  var VEL = 0.45;          // px/ms，超过即视为「快滑」
  var DIST_RATIO = 0.28;   // 拖拽超过面板高度的 28% 即关闭（慢速）
  var stack = [];          // 嵌套抽屉栈

  function el(tag, cls, html){
    var e = document.createElement(tag);
    if(cls) e.className = cls;
    if(html != null) e.innerHTML = html;
    return e;
  }
  function prefersReduce(){
    try{ return window.matchMedia('(prefers-reduced-motion:reduce)').matches; }catch(e){ return false; }
  }
  /* ④ 背景退后：安全读写宿主 <html> 上的 .csn-recede（宿主 documentElement 可能缺失） */
  function recede(on){
    try{
      var el = document.documentElement;
      if(!el || !el.classList) return;
      el.classList[on ? 'add' : 'remove']('csn-recede');
    }catch(e){}
  }

  /* ---------------- 抽屉实例 ---------------- */
  function Sheet(opt){
    this.opt = opt || {};
    this.id = this.opt.id || ('csn-' + Math.random().toString(36).slice(2, 8));
    this.snaps = (this.opt.snaps && this.opt.snaps.length) ? this.opt.snaps.slice().sort(function(a,b){return a-b;}) : [1];
    this.snapIdx = 0;
    this.speedSnap = !!this.opt.speedSnap;  // ⑨ 抽屉变页面：快滑直接到整页
    this.dy = 0;
    this.build();
  }

  Sheet.prototype.build = function(){
    var o = this.opt;
    var mask = el('div', 'csn-mask');
    mask.addEventListener('click', function(){
      if(o.maskClosable === false) return;
      this.close('mask');
    }.bind(this));

    var sh = el('div', 'csn-sheet');
    sh.setAttribute('role', 'dialog');
    sh.setAttribute('aria-modal', 'true');
    var head = '';
    if(o.title !== false){
      head = '<div class="csn-head">' +
        '<h3>' + (o.title || '') + '</h3>' +
        (o.subtitle ? '<span class="csn-sub">' + o.subtitle + '</span>' : '') +
        '<button class="csn-x" aria-label="关闭">✕</button></div>';
    }
    sh.innerHTML =
      (o.grabber === false ? '' : '<div class="csn-grab"><i></i></div>') +
      head +
      '<div class="csn-body"></div>' +
      '<div class="csn-foot"></div>';
    this.node = sh; this.maskNode = mask;
    this.body = sh.querySelector('.csn-body');
    this.foot = sh.querySelector('.csn-foot');
    this.grab = sh.querySelector('.csn-grab');
    var x = sh.querySelector('.csn-x');
    if(x) x.addEventListener('click', function(){ this.close('x'); }.bind(this));

    this.setBody(o.body);
    this.setActions(o.actions);
    document.body.appendChild(mask);
    document.body.appendChild(sh);
    this.bindDrag();
  };

  Sheet.prototype.setBody = function(html){
    if(html == null) return this;
    if(typeof html === 'string') this.body.innerHTML = html;
    else { this.body.innerHTML = ''; this.body.appendChild(html); }
    return this;
  };
  Sheet.prototype.setActions = function(acts){
    this.foot.innerHTML = '';
    if(!acts || !acts.length) return this;
    acts.forEach(function(a){
      var b = el('button', 'csn-btn ' + (a.variant || ''), (a.icon ? a.icon + ' ' : '') + (a.label || ''));
      b.addEventListener('click', function(ev){
        if(a.onClick) a.onClick(ev, this);
        if(a.close) this.close('action');
      }.bind(this));
      this.foot.appendChild(b);
    }, this);
    return this;
  };

  /* ---------------- 拖拽：距离 + 速度双判定 ---------------- */
  Sheet.prototype.bindDrag = function(){
    var self = this, sh = this.node;
    var startY = 0, startT = 0, lastY = 0, lastT = 0, v = 0, dragging = false, fromGrab = false, bodyTop = 0;

    function panelH(){ return sh.getBoundingClientRect().height || 1; }
    function onDown(ev){
      var p = ev.touches ? ev.touches[0] : ev;
      // 内容区只在其滚动到顶时才接管下拉手势（避免抢走正常滚动）
      if(!fromGrab){
        var sc = self.body;
        if(sc && sc.scrollTop > 2) return;
      }
      dragging = true;
      startY = lastY = p.clientY; startT = lastT = performance.now(); v = 0;
      sh.classList.add('csn-dragging');
      document.addEventListener('mousemove', onMove, { passive: false });
      document.addEventListener('mouseup', onUp);
      document.addEventListener('touchmove', onMove, { passive: false });
      document.addEventListener('touchend', onUp);
      document.addEventListener('touchcancel', onUp);
      ev.preventDefault();
    }
    function onMove(ev){
      if(!dragging) return;
      var p = ev.touches ? ev.touches[0] : ev;
      var now = performance.now();
      var dt = now - lastT;
      if(dt > 0){ v = (p.clientY - lastY) / dt; lastY = p.clientY; lastT = now; }
      var d = p.clientY - startY;
      // 只允许向下拖（或从半屏向上扩展到全屏）
      self.dy = d;
      if(self.canExpand() && d < 0){
        // 向上：向全屏吸附
        var h = panelH();
        var upLimit = -(h * (1 - (self.snapVal() || 1)) * 0.5);
        if(d < upLimit) d = upLimit;
      }
      if(d < 0 && !self.canExpand()) d = d * 0.25; // 阻尼
      sh.style.transform = 'translate3d(0,' + Math.max(d, -(panelH() * 0.5)) + 'px,0)';
      self.updateHint(d);
      ev.preventDefault();
    }
    function onUp(){
      if(!dragging) return;
      dragging = false;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      document.removeEventListener('touchmove', onMove);
      document.removeEventListener('touchend', onUp);
      document.removeEventListener('touchcancel', onUp);
      sh.classList.remove('csn-dragging');
      self.hideHint();
      sh.style.transform = '';
      var h = panelH();
      var fast = Math.abs(v) >= VEL;
      var far = self.dy > h * DIST_RATIO;
      // ⑥ 快滑直接关闭（不看距离）；慢速需拖够距离
      if((fast && self.dy > 12) || far){ self.close('drag'); return; }
      if(fast && self.dy < -12 && self.canExpand()){ self.snapTo(self.snaps[self.snaps.length - 1]); return; }
      if(self.dy < -h * 0.16 && self.canExpand()){ self.snapToNextUp(); return; }
      self.snapTo(self.snapVal()); // ⑧ 回弹磁吸，不等中间态
    }

    (this.grab || sh).addEventListener('mousedown', function(e){ fromGrab = true; onDown(e); fromGrab = false; });
    (this.grab || sh).addEventListener('touchstart', function(e){ fromGrab = true; onDown(e); fromGrab = false; }, { passive: false });
    // 内容区也允许下拉关闭（滚到顶时）
    this.body.addEventListener('touchstart', function(e){ fromGrab = false; onDown(e); }, { passive: false });
  };

  Sheet.prototype.canExpand = function(){ return this.snaps.length > 1; };
  Sheet.prototype.snapVal = function(){ return this.snaps[this.snapIdx]; };
  Sheet.prototype.snapToNextUp = function(){
    if(this.snapIdx < this.snaps.length - 1) this.snapTo(this.snaps[++this.snapIdx]);
  };
  Sheet.prototype.updateHint = function(d){
    if(!this.hint){
      this.hint = el('div', 'csn-hint', '');
      this.node.appendChild(this.hint);
    }
    var h = this.node.getBoundingClientRect().height || 1;
    if(d > h * DIST_RATIO) this.hint.textContent = '松开即关闭';
    else if(d < -h * 0.16 && this.canExpand()) this.hint.textContent = '松开展开全屏';
    else { this.hint.classList.remove('show'); return; }
    this.hint.classList.add('show');
  };
  Sheet.prototype.hideHint = function(){ if(this.hint) this.hint.classList.remove('show'); };

  /* ---------------- 打开 / 关闭 / 档位 ---------------- */
  Sheet.prototype.open = function(opts){
    opts = opts || {};
    var self = this;
    // ② 半屏停住 / ⑦ 多档磁吸：按 snaps 决定初始档
    this.snapIdx = 0;
    var v = this.snapVal();
    this.node.classList.toggle('csn-snap-half', v < 1);
    this.node.classList.add('csn-open');
    if(this.opt.slideFromPoint && opts.originX != null){
      this.node.style.setProperty('--csn-origin-x', opts.originX + 'px');
      this.node.classList.add('csn-slide-dir');
    }
    // ④ 背景退后
    recede(true);
    this.maskNode.classList.add('show');
    // ⑧ 嵌套：已有抽屉时，底层后退缩小变暗
    if(stack.length){
      var below = stack[stack.length - 1];
      below.node.classList.add('csn-nested-behind');
      below.maskNode.classList.add('csn-nested-mask');
      this.node.classList.add('csn-nested-top');
      this.maskNode.classList.add('csn-nested-mask');
    }
    stack.push(this);
    // ⑤ 弹性出现：先抬后落
    this.node.classList.remove('csn-anim-out');
    void this.node.offsetHeight;
    this.node.classList.add('csn-anim-in');
    var t = prefersReduce() ? 0 : 20;
    setTimeout(function(){ self.node.style.transform = 'translate3d(0,0,0)'; }, t);
    try{ if(navigator.vibrate) navigator.vibrate(6); }catch(e){}
    if(this.opt.onOpen) this.opt.onOpen(this);
    return this;
  };

  Sheet.prototype.close = function(reason){
    var self = this;
    if(this._closing) return;
    this._closing = true;
    this.node.classList.remove('csn-anim-in');
    this.node.classList.add('csn-anim-out');
    this.node.style.transform = 'translate3d(0,102%,0)';
    this.maskNode.classList.remove('show');
    // 出栈 + 恢复下层
    var i = stack.indexOf(this);
    if(i >= 0) stack.splice(i, 1);
    var below = stack[stack.length - 1];
    if(below){
      below.node.classList.remove('csn-nested-behind','csn-nested-top');
      below.maskNode.classList.remove('csn-nested-mask');
    } else {
      recede(false);
    }
    setTimeout(function(){
      if(!stack.length) recede(false);
      self.node.classList.remove('csn-open','csn-at-full','csn-to-page','csn-slide-dir','csn-nested-top');
      self.maskNode.classList.remove('csn-nested-mask');
      self.node.style.transform = '';
      self._closing = false;
    }, prefersReduce() ? 0 : 300);
    if(this.opt.onClose) this.opt.onClose(reason, this);
    return this;
  };

  /* ⑦ 拖拽扩展：磁吸到指定档（half=0.52, full=1）*/
  Sheet.prototype.snapTo = function(v){
    var self = this;
    this.snaps.sort(function(a,b){return a-b;});
    var idx = 0, best = 1e9;
    this.snaps.forEach(function(s, k){ var dd = Math.abs(s - v); if(dd < best){ best = dd; idx = k; } });
    this.snapIdx = idx;
    var val = this.snaps[idx];
    // 圆角 + 抓手 同步形变（③ 全屏展开联动）
    this.node.classList.toggle('csn-at-full', val >= 1);
    this.node.classList.toggle('csn-snap-half', val < 1);
    this.node.style.maxHeight = val >= 1 ? '92vh' : (val * 100) + 'vh';
    this.node.style.transform = 'translate3d(0,0,0)';
    if(!prefersReduce()){
      this.node.classList.add('csn-anim-in');
      setTimeout(function(){ self.node.classList.remove('csn-anim-in'); }, 440);
    }
    return this;
  };

  /* ⑨ 抽屉变页面：平滑过渡到整页（无断层）*/
  Sheet.prototype.toPage = function(){
    this.node.classList.add('csn-to-page');
    this.node.classList.add('csn-at-full');
    this.node.style.maxHeight = '100vh';
    this.node.style.height = '100vh';
    return this;
  };
  Sheet.prototype.fromPage = function(){
    this.node.classList.remove('csn-to-page');
    this.node.style.height = '';
    return this;
  };

  /* ⑩ 弹窗变成功：按钮形变 -> 内容切换为成功态 -> 自动收尾 */
  Sheet.prototype.succeed = function(o){
    var self = this;
    o = o || {};
    var btn = this.foot.querySelector('.csn-btn.primary') || this.foot.querySelector('.csn-btn');
    var finish = function(){
      self.body.innerHTML =
        '<div class="csn-success">' +
          '<div class="csn-tick">✓</div>' +
          '<h4>' + (o.title || '操作成功') + '</h4>' +
          '<p>' + (o.desc || '') + '</p>' +
        '</div>';
      self.foot.innerHTML = '';
      self.setActions([{ label: o.okLabel || '完成', variant: 'primary', close: true }]);
      if(self.grab) self.grab.style.display = 'none';
      try{ if(navigator.vibrate) navigator.vibrate([8, 30, 12]); }catch(e){}
      if(o.after) o.after(self);
      if(o.autoClose !== false){
        setTimeout(function(){ self.close('success'); }, o.hold || 1500);
      }
    };
    if(btn && !prefersReduce()){
      btn.classList.add('csn-morphing');
      setTimeout(finish, 620);
    } else finish();
    return this;
  };

  /* ⑧ 嵌套抽屉：从当前抽屉内再开一层 */
  Sheet.prototype.openNested = function(opt){
    var child = new Sheet(opt);
    child.parent = this;
    child.open(opt || {});
    return child;
  };

  /* ---------------- 对外 API ---------------- */
  window.CCSheet = {
    open: function(opt){ var s = new Sheet(opt); s.open(opt); return s; },
    Sheet: Sheet,
    /* 便捷：确认型弹窗，确认后「弹窗变成功」*/
    confirm: function(o){
      o = o || {};
      var s = new Sheet({
        title: o.title || '确认操作',
        body: o.body || '',
        snaps: [1],
        grabber: false,
        maskClosable: o.maskClosable !== false,
        actions: [
          { label: o.cancelLabel || '取消', variant: 'ghost', close: true, onClick: o.onCancel },
          { label: o.okLabel || '确定', variant: 'primary',
            onClick: function(ev, sheet){
              var r = o.onOk ? o.onOk(ev, sheet) : null;
              if(r === false) return;
              var done = (r && r.success) || o.success;
              if(done) sheet.succeed(typeof done === 'object' ? done : { title: o.okLabel || '操作成功', desc: o.successDesc || '' });
              else sheet.close('ok');
            } }
        ]
      });
      s.open({});
      return s;
    },
    /* 便捷：底部操作抽屉（① 底部抽屉 + ⑥ 拖拽关闭）*/
    actions: function(o){
      o = o || {};
      var list = o.items || [];
      // key 缺省时用下标兜底，避免 data-k="undefined" 导致点击匹配失败
      var items = list.map(function(it, i){
        var k = (it.key != null ? it.key : ('__i' + i));
        return '<button class="csn-btn ' + (it.variant || '') + '" style="margin-bottom:8px" data-k="' + k + '">' +
          (it.icon ? it.icon + ' ' : '') + it.label + '</button>';
      }).join('');
      var s = new Sheet({
        title: o.title || '选择操作',
        body: '<div style="display:flex;flex-direction:column">' + items + '</div>',
        snaps: o.snaps || [0.52, 1],
        grabber: true,
        slideFromPoint: true,
        actions: []
      });
      s.open({ originX: o.originX });
      s.body.addEventListener('click', function(e){
        var b = e.target.closest('[data-k]');
        if(!b) return;
        var k = b.dataset.k;
        var it = list.filter(function(x, i){ return String(x.key != null ? x.key : ('__i' + i)) === k; })[0];
        if(it && it.onClick) it.onClick(s);
        if(!it || it.close !== false) s.close('pick');
      });
      return s;
    },
    /* 便捷：信息详情（② 半屏停住 + ⑦ 拖拽扩展）*/
    detail: function(o){
      o = o || {};
      var s = new Sheet({
        title: o.title || '详情',
        subtitle: o.subtitle || '',
        body: o.body || '',
        snaps: o.snaps || [0.52, 1],
        grabber: true,
        footer: false,
        actions: o.actions || []
      });
      s.open({});
      return s;
    },
    closeTop: function(){ if(stack.length) stack[stack.length - 1].close('api'); },
    isOpen: function(){ return stack.length > 0; },
    _stack: stack
  };

  // Esc / 返回键关闭最上层
  document.addEventListener('keydown', function(e){
    if(e.key === 'Escape' && stack.length){ stack[stack.length - 1].close('esc'); }
  });
  window.addEventListener('popstate', function(){
    if(stack.length){ stack[stack.length - 1].close('back'); }
  });

  /* =============================================================
   * 既有 .modal-card 弹窗的拖拽关闭（⑥ 距离 + 速度双判定）
   * 手机档「抽屉形态」下，向下拖拽即关闭，快滑不看距离。
   * ============================================================= */
  function bindModalDrag(){
    var MV = 0.45, DR = 0.26;
    document.addEventListener('touchstart', function(ev){
      var mask = ev.target.closest && ev.target.closest('.modal-mask.show');
      if(!mask) return;
      if(window.innerWidth > 720) return;
      var card = mask.querySelector('.modal-card') || mask.firstElementChild;
      if(!card) return;
      var t0 = ev.touches[0], sy = t0.clientY, ly = sy, lt = performance.now(), v = 0, moved = false;
      var sc = card.scrollTop > 2;
      if(sc) return;

      function mv(e2){
        var p = e2.touches[0];
        var now = performance.now(), dt = now - lt;
        if(dt > 0){ v = (p.clientY - ly) / dt; ly = p.clientY; lt = now; }
        var d = p.clientY - sy;
        if(d < 0) d = d * 0.22;   // 向上阻尼
        if(d > 6){ moved = true; card.style.transition = 'none'; }
        card.style.transform = 'translate3d(0,' + Math.max(d, -40) + 'px,0)';
        e2.preventDefault();
      }
      function up(){
        document.removeEventListener('touchmove', mv);
        document.removeEventListener('touchend', up);
        document.removeEventListener('touchcancel', up);
        card.style.transition = '';
        card.style.transform = '';
        if(!moved) return;
        var h = card.getBoundingClientRect().height || 1;
        var d = ly - sy;
        var fast = Math.abs(v) >= MV;
        if((fast && d > 12) || d > h * DR){
          try{ mask.classList.remove('show'); }catch(e){}
        }
      }
      document.addEventListener('touchmove', mv, { passive: false });
      document.addEventListener('touchend', up);
      document.addEventListener('touchcancel', up);
    }, { passive: true });
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bindModalDrag);
  else bindModalDrag();
})();

/* =============================================================
 * __FOG_GUARD_20260919__ 雾状遮罩清扫守卫（低频自愈，正常路径零打扰）
 * 治理三类「只剩雾」残留：
 *   A) .csn-recede 残留 —— 弹窗/抽屉都关了，底层却还缩放+模糊+变暗（雾感主源）
 *   B) .tour-overlay.show 残留 —— 新手教程卡片缺失/渲染失败时整屏只剩雾（z=5200 无解）
 *   C) .mega-mask.show 残留 —— 巨型菜单面板已收但遮罩未收
 * 实现：1.5s 周期 + visibilitychange 触发；全部只读判断、命中才动一次 class，
 *       不碰任何业务状态；幂等标记 window.__CC_FOG_GUARD__。
 * ============================================================= */
(function(){
  'use strict';
  if(window.__CC_FOG_GUARD__) return;
  window.__CC_FOG_GUARD__ = true;

  function anyModalOpen(){
    var m = document.querySelectorAll('.modal-mask.show');
    return m && m.length > 0;
  }
  function sheetOpen(){
    try{
      if(window.CCSheet && typeof CCSheet.isOpen === 'function' && CCSheet.isOpen()) return true;
    }catch(e){}
    var sh = document.querySelector('.csn-overlay.show, .csn-sheet.show, .m-sheet.show');
    return !!sh;
  }
  function megaOpen(){
    var mask = document.querySelector('.mega-mask.show');
    if(!mask) return false;
    var btn = document.getElementById('megaBtn');
    if(btn && btn.getAttribute('aria-expanded') === 'true') return true;
    /* 无按钮参照（其他壳）时看面板本体是否可见 */
    var panel = document.getElementById('megaPanel') || document.querySelector('.mega-panel');
    return !!(panel && panel.getBoundingClientRect().height > 0);
  }
  function sweep(){
    try{
      /* A) csn-recede 残留 */
      var root = document.documentElement;
      if(root.classList.contains('csn-recede') && !anyModalOpen() && !sheetOpen()){
        root.classList.remove('csn-recede');
      }
      /* B) 新手教程雾层残留：声明为 show，但卡片看不见（缺失/高度为 0） */
      var tour = document.querySelector('.tour-overlay.show');
      if(tour){
        var cardEl = tour.querySelector('#tourCard') || tour.querySelector('.tour-card');
        var vis = false;
        if(cardEl){
          var r = cardEl.getBoundingClientRect();
          vis = r.height > 8 && getComputedStyle(cardEl).visibility !== 'hidden';
        }
        if(!vis) tour.classList.remove('show');
      }
      /* C) 巨型菜单遮罩残留：面板已收但遮罩还在 */
      var mm = document.querySelector('.mega-mask.show');
      if(mm && !megaOpen()) mm.classList.remove('show');
    }catch(e){}
  }
  setInterval(sweep, 1500);
  document.addEventListener('visibilitychange', function(){ if(!document.hidden) sweep(); });
  document.addEventListener('DOMContentLoaded', sweep);
})();
/*__CC_SHEET_JS_END__*/
</script>

<script>
/*__NAV_DESIGN_20260917_JS__BEGIN —— 导航升级（源 index.html，勿直接改产物）*/
(function(){
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
      try{ f.contentWindow.postMessage({type:'cc:nav-jump', view:view, mod:mod}, '*'); }catch(e){}
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
})();
/*__NAV_DESIGN_20260917_JS__END*/
</script>
</body>
</html>
'''

def inline_risk_deps(raw):
    """将 risk-lite.html 中对 risk/ 子目录的相对引用内联，确保单文件版离线可用。"""
    base = BASE
    # 1) favicon -> data URI
    icon_b64 = base64.b64encode(
        io.open(os.path.join(base, 'risk', 'favicon.svg'), 'rb').read()).decode('ascii')
    raw = raw.replace(
        '<link rel="icon" href="risk/favicon.svg" type="image/svg+xml">',
        '<link rel="icon" href="data:image/svg+xml;base64,{}" type="image/svg+xml">'.format(icon_b64))
    # 2) leaflet.css -> <style>
    css = io.open(os.path.join(base, 'risk', 'leaflet.css'), 'rb').read().decode('utf-8')
    raw = raw.replace(
        '<link rel="stylesheet" href="risk/leaflet.css" />',
        '<style>\n' + css + '\n</style>')
    # 3) 其余 JS -> <script>（leaflet.js / data-cache.js / mock-server.js / api-client.js）
    for src_pat, rel_path in [
            (r'<script src="risk/leaflet\.js"></script>', 'risk/leaflet.js'),
            (r'<script src="risk/js/data-cache\.js"></script>', 'risk/js/data-cache.js'),
            (r'<script src="risk/api/mock-server\.js\?[^"]*"></script>', 'risk/api/mock-server.js'),
            (r'<script src="risk/api/api-client\.js\?[^"]*"></script>', 'risk/api/api-client.js'),
    ]:
        js = io.open(os.path.join(base, *rel_path.split('/')), 'rb').read().decode('utf-8')
        raw = re.sub(src_pat, lambda m: '<script>\n' + js + '\n</script>', raw)
    leftover = re.findall(r'(?:src|href)="risk/', raw)
    assert not leftover, 'risk 相对引用未完全内联: {}'.format(leftover)
    return raw

def build():
    t = TEMPLATE
    # 内嵌 pako 解压库：旧浏览器（Safari < 16.4）降级用（纯 JS，无网络依赖）
    pako_src = io.open(os.path.join(BASE, u'_pako.min.js'), 'rb').read().decode('utf-8')
    assert '__PAKO_SRC__' in t, 'placeholder missing __PAKO_SRC__'
    t = t.replace('__PAKO_SRC__', pako_src)
    enhance_src = io.open(os.path.join(BASE, u'_shell_enhance.js'), 'rb').read().decode('utf-8')
    t = t.replace('__SHELL_ENHANCE__', enhance_src)
    for key, path in SOURCES.items():
        raw = io.open(os.path.join(BASE, path), 'rb').read()
        if key == 'risk':
            raw = inline_risk_deps(raw.decode('utf-8')).encode('utf-8')
        gz = gzip.compress(raw, 9)
        b64 = base64.b64encode(gz).decode('ascii')
        ph = '__B64_{}__'.format(key)
        assert ph in t, 'placeholder missing ' + ph
        t = t.replace(ph, b64)
        print('{}: raw {:.2f}MB -> gz {:.2f}MB'.format(key, len(raw)/1048576.0, len(gz)/1048576.0))
    out = os.path.join(BASE, OUT)
    # newline=''：禁用通用换行转换，避免 Windows 下把产物里的 \n 改写成 \r\n
    with io.open(out, 'w', encoding='utf-8', newline='') as f:
        f.write(t)
    print('写出', OUT, '{:.2f}MB'.format(os.path.getsize(out)/1048576.0))

if __name__ == '__main__':
    build()