# -*- coding: utf-8 -*-
"""重建主文件：_work 中已修复的三系统 + 三tab宿主模板，base64 封装"""
import base64
import io
import os

OUTPUT = u'春秋·广州分队全能助手.html'
SOURCES = {
    'quiz': u'_work\\广州刷题.html',
    'performance': u'_work\\广州综合绩效评定测试系统1.0(3).html',
    'beauty': u'_work\\美妆销售话术生成系统.html',
}

TEMPLATE = u'''<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#148453">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="春秋全能助手">
<meta name="mobile-web-app-capable" content="yes">
<meta name="application-name" content="春秋·广州分队全能助手">
<meta name="description" content="春秋航空广州分队综合管理平台 - 刷题·绩效·美妆话术 全功能单文件版">
<meta name="format-detection" content="telephone=no">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>春秋航空 · 广州分队全能助手</title>
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
.sys-wrap.active{display:block;}
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
}
@media(max-width:720px){
  .brand-name{font-size:.9rem;}
  .brand-sub{font-size:.6rem;padding:1px 6px;}
  .net-status{display:none;}
  .mod-tab{padding:7px 10px;font-size:.8rem;gap:6px;}
  .user-chip span{display:none;}
}
.toast-container{position:fixed;top:76px;right:20px;z-index:300;display:flex;flex-direction:column;gap:8px;}
.toast{padding:11px 18px;border-radius:8px;background:var(--bg-card);border:1px solid var(--border);box-shadow:0 4px 16px rgba(0,0,0,.1);font-size:.86rem;display:flex;align-items:center;gap:10px;animation:slideIn .3s;min-width:240px;border-left:4px solid var(--primary);}
.toast.toast-info{border-left-color:var(--primary);}
@keyframes slideIn{from{transform:translateX(100%);opacity:0;}to{transform:translateX(0);opacity:1;}}
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
      <div class="brand-name">春秋航空 <span class="brand-sub">全能助手</span></div>
    </div>
  </div>

  <nav class="module-tabs" id="moduleTabs">
    <button class="mod-tab active" data-mod="quiz" onclick="switchModule('quiz')">📚 培训考核</button>
    <button class="mod-tab" data-mod="performance" onclick="switchModule('performance')">📊 绩效管理</button>
    <button class="mod-tab" data-mod="beauty" onclick="switchModule('beauty')">💄 美妆话术</button>
  </nav>

  <div class="actions">
    <div class="net-status" id="netStatus"><span class="net-dot"></span><span id="netText">在线</span></div>
    <button class="theme-btn" id="themeBtn" onclick="cycleTheme()" title="切换主题">☀️</button>
    <div class="user-chip" onclick="toast('春秋航空广州分队 · 全能助手')">
      <div class="avatar">乘</div>
      <span>乘务员</span>
    </div>
  </div>
</header>

<main class="sys-area" id="sysArea">
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
</main>

<div class="toast-container" id="toastContainer"></div>

<script>
/* ===================== 三大系统完整功能数据（base64 内嵌） ===================== */
const MODULES = {
  quiz: "__BASE64_QUIZ__",
  performance: "__BASE64_PERFORMANCE__",
  beauty: "__BASE64_BEAUTY__"
};

/* ===================== 解码引擎（srcdoc 内嵌，兼容 file:// 下的 localStorage） ===================== */
const _frames = {};
function _b64ToHtml(b64){
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for(let i=0;i<bin.length;i++) bytes[i] = bin.charCodeAt(i);
  return new TextDecoder('utf-8').decode(bytes);
}

/* ===================== 模块切换（懒加载 + 缓存） ===================== */
let currentMod = null;
function switchModule(id){
  currentMod = id;
  document.querySelectorAll('.mod-tab').forEach(b => b.classList.toggle('active', b.dataset.mod===id));
  document.querySelectorAll('.sys-wrap').forEach(w => w.classList.remove('active'));
  const wrap = document.getElementById('wrap-'+id);
  wrap.classList.add('active');

  if(!_frames[id]){
    const loader = document.getElementById('loader-'+id);
    const frame = document.getElementById('frame-'+id);
    try{
      if(loader) loader.classList.remove('hidden');
      frame.srcdoc = _b64ToHtml(MODULES[id]);
      frame.onload = function(){
        if(loader) loader.classList.add('hidden');
        // 同步宿主主题到子系统
        try{
          const doc = frame.contentDocument;
          const t = document.documentElement.getAttribute('data-theme');
          if(doc && doc.documentElement){ doc.documentElement.setAttribute('data-theme', t); }
        }catch(e){}
      };
    }catch(e){
      console.error('模块加载失败:', id, e);
      if(loader){ loader.querySelector('.sl-text').textContent = '加载失败，请刷新重试'; }
    }
  }
}

/* ===================== 主题（宿主 + 同步子系统） ===================== */
let hostTheme = 'light';
function applyTheme(t){
  hostTheme = t;
  document.documentElement.setAttribute('data-theme', t);
  const btn = document.getElementById('themeBtn');
  btn.textContent = t==='dark' ? '🌙' : '☀️';
  ['quiz','performance','beauty'].forEach(id=>{
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
function toast(msg, type='info'){
  const c = document.getElementById('toastContainer');
  const t = document.createElement('div');
  t.className = 'toast toast-'+type;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(()=>{ t.style.animation='slideIn .3s reverse forwards'; setTimeout(()=>t.remove(),300); }, 2600);
}

/* ===================== 网络状态 ===================== */
function updateNetworkStatus(){
  const el = document.getElementById('netStatus');
  const txt = document.getElementById('netText');
  if(navigator.onLine){ el.classList.remove('offline'); txt.textContent='在线'; }
  else { el.classList.add('offline'); txt.textContent='离线'; }
}

/* ===================== 启动 ===================== */
applyTheme('light');
updateNetworkStatus();
window.addEventListener('online', updateNetworkStatus);
window.addEventListener('offline', updateNetworkStatus);
switchModule('quiz'); // 默认直接进入培训考核模块
</script>
</body>
</html>'''

def main():
    t = TEMPLATE
    for key, path in SOURCES.items():
        with io.open(path, 'rb') as f:
            raw = f.read()
        b64 = base64.b64encode(raw).decode('ascii')
        ph = '__BASE64_{}__'.format(key.upper())
        assert ph in t, '缺少占位符 ' + ph
        t = t.replace(ph, b64)
        print('{} {:.2f} MB'.format(key, len(raw)/1024.0**2))
    with io.open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(t)
    print('重建完成 -> {:.2f} MB {}'.format(os.path.getsize(OUTPUT)/1024.0**2, OUTPUT))

if __name__ == '__main__':
    main()