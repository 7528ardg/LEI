# -*- coding: utf-8 -*-
"""gzip 版主文件构建：三大系统 gzip 压缩内嵌，运行时 DecompressionStream 解压，显著减小文件体积提升加载"""
import gzip
import base64
import io
import os

SOURCES = {
    'qa': u'qa.html',
    'quiz': u'quiz.html',
    'performance': u'performance.html',
    'beauty': u'beauty.html',
    'medical': u'medical.html',
    'daily': u'daily.html',
    'manual': u'manual.html',
    'report': u'report.html',
    'kbadmin': u'kb-admin.html',
}
OUTS = [
    u'spring-assistant.html',
]

TEMPLATE = u'''<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#148453">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="客舱小助手">
<meta name="mobile-web-app-capable" content="yes">
<meta name="application-name" content="春秋航空广州分队客舱小助手">
<meta name="description" content="春秋航空广州分队客舱小助手 - 你问我答·培训考核·绩效管理·美妆话术·医疗急救·日常问题·手册奖惩·事件报告 全功能单文件版">
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
.module-tabs{display:flex;align-items:center;gap:6px;flex:1;min-width:0;overflow-x:auto;scrollbar-width:none;padding:4px;}
.module-tabs::-webkit-scrollbar{display:none;}
.mod-tab{padding:8px 16px;border-radius:10px;border:none;background:transparent;cursor:pointer;font-size:.86rem;font-weight:600;color:var(--text2);display:flex;align-items:center;gap:6px;white-space:nowrap;transition:all .2s;font-family:var(--font-sans);}
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
.sys-frame{width:100%;height:100%;border:none;display:block;}
.sys-loader{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;background:var(--bg);z-index:5;transition:opacity .4s;gap:14px;}
.sys-loader.hidden{opacity:0;pointer-events:none;}
.sys-spinner{width:44px;height:44px;border:4px solid var(--primary-soft);border-top-color:var(--primary);border-radius:50%;animation:spin .8s linear infinite;}
.sys-loader .sl-text{font-size:.85rem;color:var(--text2);font-weight:500;}
@keyframes spin{to{transform:rotate(360deg);}}
/* ===== 平板优化（721-1100px） ===== */
@media(min-width:721px) and (max-width:1100px){
  .topbar{padding:0 14px;gap:10px;}
  .brand-name{font-size:.95rem;}
  .mod-tab{padding:8px 12px;font-size:.82rem;gap:6px;}
  .sys-area{top:calc(3px + var(--topbar-h));}
  .toast-container{top:70px;}
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
</style>
</head>
<body>

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
      <div class="brand-name">春秋航空 <span class="brand-sub">客舱小助手</span></div>
    </div>
  </div>

  <nav class="module-tabs" id="moduleTabs">
    <button class="mod-tab" data-mod="qa" onclick="switchModule('qa')">💬 你问我答</button>
    <button class="mod-tab active" data-mod="quiz" onclick="switchModule('quiz')">📚 培训考核</button>
    <button class="mod-tab" data-mod="performance" onclick="switchModule('performance')">📊 绩效管理</button>
    <button class="mod-tab" data-mod="beauty" onclick="switchModule('beauty')">💄 美妆话术</button>
    <button class="mod-tab" data-mod="medical" onclick="switchModule('medical')">🚑 医疗急救</button>
    <button class="mod-tab" data-mod="daily" onclick="switchModule('daily')">❓ 日常问题</button>
    <button class="mod-tab" data-mod="manual" onclick="switchModule('manual')">📕 手册奖惩</button>
    <button class="mod-tab" data-mod="report" onclick="switchModule('report')">🗂 事件报告</button>
    <button class="mod-tab" data-mod="kbadmin" onclick="switchModule('kbadmin')">📇 库管理</button>
  </nav>

  <div class="actions">
    <div class="net-status" id="netStatus"><span class="net-dot"></span><span id="netText">在线</span></div>
    <button class="bk-btn" id="packsBadge" style="display:none" onclick="openPacksModal()" title="有新的数据包可安装">📦<span>新数据包</span></button>
    <button class="bk-btn" onclick="openBackupModal()" title="数据备份 / 恢复">💾<span>备份</span></button>
    <button class="theme-btn" id="themeBtn" onclick="cycleTheme()" title="切换主题">☀️</button>
    <div class="user-chip" id="userChip" onclick="openProfileModal()" title="点击编辑姓名 / 头像">
      <div class="avatar"><div id="avatarLetter">乘</div><img id="avatarImg" alt="" style="display:none"></div>
      <span id="userName">乘务员</span>
    </div>
  </div>
</header>

<main class="sys-area" id="sysArea">
  <div class="sys-wrap" id="wrap-qa">
    <div class="sys-loader" id="loader-qa"><div class="sys-spinner"></div><div class="sl-text">正在进入 你问我答 …</div></div>
    <iframe class="sys-frame" id="frame-qa"></iframe>
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
</main>

<div class="toast-container" id="toastContainer"></div>

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

<!-- ===== 数据包在线更新（M2） ===== -->
<div class="modal-mask" id="packsModal" onclick="if(event.target===this)closePacksModal()">
  <div class="modal-card">
    <h3>📦 发现可用数据包更新</h3>
    <p class="m-sub" id="packsModalBody"></p>
    <div class="m-actions">
      <button class="m-btn primary" id="packsInstallBtn" onclick="installPacksUpdates()">⬇️ 全部安装</button>
      <button class="m-btn ghost" onclick="closePacksModal()">稍后再说</button>
    </div>
    <div class="m-meta" id="packsModalMeta">来源：团队发布 · https + sha256 校验 · 不随个人备份迁移</div>
  </div>
</div>

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
/* ===================== 三大系统完整功能数据（gzip 压缩 base64 内嵌，运行时解压） ===================== */
const MODULES = {
  qa: "__B64_qa__",
  quiz: "__B64_quiz__",
  performance: "__B64_performance__",
  beauty: "__B64_beauty__",
  medical: "__B64_medical__",
  daily: "__B64_daily__",
  manual: "__B64_manual__",
  report: "__B64_report__",
  kbadmin: "__B64_kbadmin__"
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
(function(){
  if(typeof window !== 'undefined' && typeof window.__pako50 !== 'undefined') return;
  var _pako = window.__pako50 = {};
  location.protocol; // no-op 占位，避免压缩器把下方函数当表达式
  _pako.inflate = function(bytes){
    // 纯 JS gzip 解压：jDataView-like 简化版（huffman + LZ77）
    // 实际逻辑由构建脚本内嵌 pako 源码提供
    throw new Error('pako not injected');
  };
})();
__PAKO_SRC__
async function _b64ToHtml(b64){
  const bytes = _b64ToBytes(b64);
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
    var _pk = window.pako || (window.__pako50);
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

/* ===================== 模块切换（懒加载 + 缓存 + 解压） ===================== */
let currentMod = null;
const _modScroll = {};

/* ===== 内嵌模式样式：隐藏各模块自带的顶栏/侧栏，避免"双导航栏" =====
   （模块 Standalone 打开时仍保留自己的导航；嵌入全能助手时由外壳注入 CSS 隐藏） */
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
  kbadmin: 'header.kb-top{display:none!important}.kb-tabs{top:0!important}'
};
function injectEmbedCss(id, frame){
  const css = EMBED_CSS[id];
  if(!css) return;
  try{
    const d = frame.contentDocument;
    if(!d) return;
    const existing = d.getElementById('embed-mode-css');
    if(existing) existing.remove();
    const st = d.createElement('style');
    st.id = 'embed-mode-css';
    st.textContent = css;
    (d.head || d.documentElement).appendChild(st);
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
  // 页签横向滚动时，把当前激活页签自动滚到可视区中部（手机/平板 9 个页签尤其需要）
  var _ab = document.querySelector('.mod-tab.active');
  if(_ab && _ab.scrollIntoView){ try{ _ab.scrollIntoView({behavior:'smooth',inline:'center',block:'nearest'}); }catch(e){ _ab.scrollIntoView(); } }
  document.querySelectorAll('.sys-wrap').forEach(w => w.classList.remove('active'));
  const wrap = document.getElementById('wrap-'+id);
  wrap.classList.add('active');

  if(!_frames[id]){
    const loader = document.getElementById('loader-'+id);
    const frame = document.getElementById('frame-'+id);
    _b64ToHtml(MODULES[id]).then(function(html){
      if(loader) loader.classList.remove('hidden');
      frame.srcdoc = html;
      frame.onload = function(){
        if(loader) loader.classList.add('hidden');
        _frames[id] = frame; // 标记已加载，避免每次切模块重复解压初始化（此前 _frames 从未被赋值）
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
      };
    }).catch(function(e){
      console.error('模块加载失败:', id, e);
      if(loader) loader.querySelector('.sl-text').textContent = '加载失败，请刷新重试';
    });
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
function applyTheme(t){
  hostTheme = t;
  document.documentElement.setAttribute('data-theme', t);
  const btn = document.getElementById('themeBtn');
  btn.textContent = t==='dark' ? '🌙' : '☀️';
  ['qa','quiz','performance','beauty','medical','daily','manual','report','kbadmin'].forEach(id=>{
    const f = _frames[id];
    if(f && f.contentDocument){
      try{ f.contentDocument.documentElement.setAttribute('data-theme', t); }catch(e){}
    }
  });
}
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
function closePacksModal(){ document.getElementById('packsModal').classList.remove('show'); }
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
checkPacksUpdate();
renderUserChip();
switchModule('quiz');
</script>
</body>
</html>
'''

def build():
    t = TEMPLATE
    # 内嵌 pako（保留缩进版，避免占位符处报缩进错误）
    pako_src = io.open(u'_pako.min.js', 'rb').read().decode('utf-8')
    pako_injected = pako_src.replace(u'function(t,e){', u';(function(t){var e=t.exports||{};')
    # pako umd 在浏览器 <script> 中执行时 exports 为 undefined → 直接走 root 分支挂到 window.pako
    # 因此无需改写，直接原样注入到 __PAKO_SRC__ 占位处
    pako_injected = pako_src
    assert '__PAKO_SRC__' in t, 'placeholder missing __PAKO_SRC__'
    t = t.replace('__PAKO_SRC__', pako_injected)
    for key, path in SOURCES.items():
        raw = io.open(path, 'rb').read()
        gz = gzip.compress(raw, 9)
        b64 = base64.b64encode(gz).decode('ascii')
        ph = '__B64_{}__'.format(key)
        assert ph in t, 'placeholder missing ' + ph
        t = t.replace(ph, b64)
        print('{}: raw {:.2f}MB -> gz {:.2f}MB'.format(key, len(raw)/1048576.0, len(gz)/1048576.0))
    for out in OUTS:
        with io.open(out, 'w', encoding='utf-8') as f:
            f.write(t)
        print('写出', out, '{:.2f}MB'.format(os.path.getsize(out)/1048576.0))

if __name__ == '__main__':
    build()