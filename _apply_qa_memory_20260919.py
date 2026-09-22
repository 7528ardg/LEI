# -*- coding: utf-8 -*-
"""
「你问我答」会话记忆注入器 v1 —— 幂等（strip -> replay）
=================================================================
对应 2026-09-19 审计的 P0「会话不持久」与 P1「多轮上下文弱」：

  B1 会话持久化   chat.msgs 落 localStorage('qa_history_v1')，刷新 / 切模块 /
                  LRU 回收后回来不再空白；条数与总量双封顶，防超限。
  B2 多轮上下文   包装 SpringAI.chatLLM，所有调用点自动带上最近 3 轮历史
                  （每条截 280 字、总量 1800 字封顶），追问「那第 3 条呢」不再断链。
  B3 记忆管理抽屉 顶栏「🕘 历史」按钮 → 右侧抽屉：最近提问可点击重问、
                  联想记忆逐条撤销、导出 JSON、清空对话记录。

注入位置（均在文档末尾，保证在 bridge 之后执行）：
  <style id="qa-mem-css">         </head> 前
  <!-- QAMEM_BTN_BEGIN -->        顶栏「⚙️ AI设置」按钮之后（2026-09-20 起；旧锚「🔄 新对话」已移入形象控制条）
  <!-- QAMEM_ASIDE_BEGIN -->      </div><!-- /#qaFlow --> 之前（抽屉 DOM）
  /*__QA_MEM_BEGIN__*/            紧跟 bridge 的 JS_END（同一 <script> 内）

⚠️ qa.html 是「源」：改完必须重建壳
   python _build_all.py build && python _build_hosted.py && python _check_needles.py
⚠️ 首次运行备份 qa.html -> _bak_qa_mem_20260919.html
用法：python _apply_qa_memory_20260919.py [--check]
"""
import io
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
QA = os.path.join(HERE, 'qa.html')
BAK = os.path.join(HERE, '_bak_qa_mem_20260919.html')

CSS_BEGIN = '/*__QA_MEM_CSS__*/'
CSS_END = '/*__QA_MEM_CSS_END__*/'
JS_BEGIN = '/*__QA_MEM_BEGIN__*/'
JS_END = '/*__QA_MEM_END__*/'
BTN_BEGIN = '<!-- QAMEM_BTN_BEGIN -->'
BTN_END = '<!-- QAMEM_BTN_END -->'
ASIDE_BEGIN = '<!-- QAMEM_ASIDE_BEGIN -->'
ASIDE_END = '<!-- QAMEM_ASIDE_END -->'
STYLE_OPEN = '<style id="qa-mem-css">'
STYLE_CLOSE = '</style>'

ANCHOR_JS = '/*__QA_BRIDGE_END__*/'          # 紧跟桥接块之后
# 2026-09-20 双保险锚点：优先插在顶栏「⚙️ AI设置」按钮之后（视觉正确位）；
# 若补丁链顺序导致该按钮尚未注入（_restore_ai 在后），回退插到 </header> 之前。
# 自检（main 内）保证按钮必须位于 </header> 之前，落在外面会直接报错。
ANCHOR_BTN = '<button class="icon-btn" onclick="openAiSettings()">⚙️ AI设置</button>'
ANCHOR_BTN_FALLBACK = '</header>'
ANCHOR_ASIDE = u'</div><!-- /#qaFlow -->'

CHECK = '--check' in sys.argv

CSS = u"""
/* ---- B3 历史 / 记忆抽屉 ---- */
#qaDrawer{position:fixed;inset:0;z-index:400;display:none;}
#qaDrawer.on{display:block;}
#qaDrawer .qd-mask{position:absolute;inset:0;background:rgba(15,42,31,.34);}
#qaDrawer .qd-box{position:absolute;top:0;right:0;height:100%;width:min(340px,88vw);
  background:var(--bg-card,#fff);border-left:1px solid var(--border,#E5EDE9);
  box-shadow:-10px 0 30px rgba(15,42,31,.16);display:flex;flex-direction:column;}
#qaDrawer .qd-h{display:flex;align-items:center;gap:8px;padding:12px 14px;
  border-bottom:1px solid var(--border,#E5EDE9);font-size:.9rem;font-weight:800;color:var(--text,#0F2A1F);}
#qaDrawer .qd-x{margin-left:auto;border:none;background:var(--primary-mist,#F4F9F6);color:var(--text2,#5A6F65);
  width:36px;height:36px;border-radius:10px;font-size:15px;display:inline-flex;align-items:center;justify-content:center;}
#qaDrawer .qd-x:hover{background:var(--primary-soft,#E8F3EE);color:var(--primary,#148453);}
#qaDrawer .qd-b{flex:1;min-height:0;overflow-y:auto;padding:12px 14px 24px;-webkit-overflow-scrolling:touch;}
#qaDrawer .qd-sec{font-size:.68rem;font-weight:800;color:var(--text3,#9DB0A6);letter-spacing:.6px;
  margin:14px 0 7px;text-transform:uppercase;}
#qaDrawer .qd-sec:first-child{margin-top:0;}
#qaDrawer .qd-sec small{font-weight:600;letter-spacing:0;text-transform:none;}
#qaDrawer .qd-item{display:flex;align-items:center;gap:8px;padding:9px 10px;border:1px solid var(--border,#E5EDE9);
  border-radius:10px;margin-bottom:6px;font-size:.8rem;color:var(--text2,#5A6F65);line-height:1.5;
  background:var(--bg-card,#fff);text-align:left;width:100%;min-height:44px;cursor:pointer;}
#qaDrawer .qd-item:hover{border-color:var(--primary,#148453);color:var(--primary,#148453);background:var(--primary-mist,#F4F9F6);}
#qaDrawer .qd-item .t{margin-left:auto;font-size:.68rem;color:var(--text3,#9DB0A6);flex-shrink:0;}
#qaDrawer .qd-mem{padding:9px 10px;border:1px dashed var(--border,#E5EDE9);border-radius:10px;
  margin-bottom:7px;font-size:.78rem;line-height:1.55;color:var(--text2,#5A6F65);}
#qaDrawer .qd-mem b{display:block;color:var(--text,#0F2A1F);font-weight:700;margin-bottom:2px;}
#qaDrawer .qd-mem .m{font-size:.7rem;color:var(--text3,#9DB0A6);margin-top:3px;}
#qaDrawer .qd-mem .ops{margin-top:7px;}
#qaDrawer .qd-mem .ops button{border:1px solid var(--border,#E5EDE9);background:transparent;color:var(--text3,#9DB0A6);
  font-size:.7rem;padding:6px 11px;border-radius:8px;min-height:34px;}
#qaDrawer .qd-mem .ops button:hover{border-color:var(--danger,#C62828);color:var(--danger,#C62828);}
#qaDrawer .qd-ops{display:flex;flex-direction:column;gap:7px;}
#qaDrawer .qd-ops button{border:1px solid var(--border,#E5EDE9);background:var(--bg-card,#fff);color:var(--text2,#5A6F65);
  font-size:.8rem;padding:11px 12px;border-radius:10px;min-height:44px;text-align:left;}
#qaDrawer .qd-ops button:hover{border-color:var(--primary,#148453);color:var(--primary,#148453);background:var(--primary-mist,#F4F9F6);}
#qaDrawer .qd-empty{font-size:.78rem;color:var(--text3,#9DB0A6);padding:6px 2px;}
html[data-theme="dark"] #qaDrawer .qd-box{background:#162420;border-color:#1E3A2C;}
html[data-theme="dark"] #qaDrawer .qd-mask{background:rgba(0,0,0,.5);}
html[data-theme="dark"] #qaDrawer .qd-h{color:#E8F3EE;border-color:#1E3A2C;}
html[data-theme="dark"] #qaDrawer .qd-item,html[data-theme="dark"] #qaDrawer .qd-ops button{background:#162420;border-color:#1E3A2C;}
@media (max-width:760px){ #qaDrawer .qd-box{width:92vw;} }
/* ---- __QA_RESTORE_PILL_v2__ 恢复提示胶囊：对话流内居中、随消息滚动（含深色模式与触控 44px） ---- */
.qa-restore-pill{display:flex;align-items:center;gap:8px;margin:4px auto 12px;padding:7px 8px 7px 14px;
  width:fit-content;max-width:min(92%,560px);box-sizing:border-box;
  background:var(--gold-soft,#FEF6DC);border:1px solid var(--gold,#F5B800);border-radius:999px;
  font-size:12px;color:#6B5200;line-height:1.5;box-shadow:0 2px 8px rgba(107,82,0,.08);}
.qa-restore-pill .qa-ctx-ico{font-size:14px;flex-shrink:0;}
.qa-restore-pill .qa-ctx-tx{min-width:0;}
.qa-restore-pill b{font-weight:700;}
.qa-restore-pill .qa-ctx-x{margin-left:2px;border:none;background:transparent;color:#6B5200;cursor:pointer;
  font-size:14px;width:30px;height:30px;min-width:30px;border-radius:50%;flex-shrink:0;
  display:inline-flex;align-items:center;justify-content:center;transition:background .16s;}
.qa-restore-pill .qa-ctx-x:hover{background:rgba(107,82,0,.12);}
.qa-restore-pill .qa-ctx-x:focus-visible{outline:2px solid var(--gold,#F5B800);outline-offset:1px;}
html[data-theme="dark"] .qa-restore-pill{background:#2A2410;border-color:#6B5200;color:#F5D98A;box-shadow:none;}
html[data-theme="dark"] .qa-restore-pill .qa-ctx-x{color:#F5D98A;}
html[data-theme="dark"] .qa-restore-pill .qa-ctx-x:hover{background:rgba(245,217,138,.14);}
@media (max-width:760px){
  .qa-restore-pill{max-width:calc(100% - 24px);}
  .qa-restore-pill .qa-ctx-x{width:44px;height:44px;min-width:44px;}
}
"""

BTN = u"""<button class="icon-btn" onclick="qaOpenDrawer()" title="查看历史对话与联想记忆">&#128340; 历史</button>
"""

ASIDE = u"""<aside id="qaDrawer" role="dialog" aria-label="历史与记忆" aria-modal="true">
  <div class="qd-mask"></div>
  <div class="qd-box">
    <div class="qd-h"><b>&#128340; 历史 / 记忆</b><button class="qd-x" type="button" aria-label="关闭">&#10005;</button></div>
    <div class="qd-b">
      <div class="qd-sec">最近提问（点一条重新问）</div>
      <div id="qdHist"></div>
      <div class="qd-sec">联想记忆 <small id="qdMemCount"></small></div>
      <div id="qdMem"></div>
      <div class="qd-sec">操作</div>
      <div class="qd-ops">
        <button id="qdExport" type="button">&#128229; 导出全部记忆（JSON）</button>
        <button id="qdClearHist" type="button">&#128465; 清空对话记录</button>
      </div>
    </div>
  </div>
</aside>
"""

JS = u"""
(function(){
  var HIST_KEY = 'qa_history_v1';
  var HIST_MAX_MSGS = 60;
  var HIST_MAX_CHARS = 180000;
  var CTX_TURNS = 3;
  var CTX_MAX_CHARS = 1800;
  var suppressUntil = 0;

  function flag(k, v){
    window.__qaMemFlags = window.__qaMemFlags || {};
    if(v === undefined) return !!window.__qaMemFlags[k];
    window.__qaMemFlags[k] = v;
  }
  function htmlToText(h){
    try{
      var d = document.createElement('div');
      d.innerHTML = String(h == null ? '' : h);
      return (d.textContent || '').replace(/\\s+/g, ' ').trim();
    }catch(e){ return String(h == null ? '' : h); }
  }
  function clip(s, n){ s = String(s == null ? '' : s); return s.length > n ? s.slice(0, n) + '…' : s; }
  function fmtWhen(ts){
    try{
      var d = new Date(ts || Date.now());
      return (d.getMonth() + 1) + ' 月 ' + d.getDate() + ' 日 ' +
        String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0');
    }catch(e){ return ''; }
  }

  /* ================= B1 会话持久化 ================= */
  function saveNow(){
    if(Date.now() < suppressUntil) return;
    try{
      var msgs = (chat && Array.isArray(chat.msgs)) ? chat.msgs : [];
      if(!msgs.length) return;
      var tail = msgs.slice(-HIST_MAX_MSGS);
      var payload = { v:1, t:Date.now(), msgs: tail };
      var s = JSON.stringify(payload);
      while(s.length > HIST_MAX_CHARS && tail.length > 4){
        tail = tail.slice(Math.ceil(tail.length / 8));
        payload.msgs = tail;
        s = JSON.stringify(payload);
      }
      localStorage.setItem(HIST_KEY, s);
    }catch(e){}
  }
  var saveTimer = null;
  function saveSoon(){
    if(Date.now() < suppressUntil) return;
    if(saveTimer) return;
    saveTimer = setTimeout(function(){ saveTimer = null; saveNow(); }, 600);
  }
  function clearSaved(){
    suppressUntil = Date.now() + 1500;
    try{ localStorage.removeItem(HIST_KEY); }catch(e){}
  }
  function loadSaved(){
    try{
      var o = JSON.parse(localStorage.getItem(HIST_KEY) || 'null');
      if(o && Array.isArray(o.msgs) && o.msgs.length) return o;
    }catch(e){}
    return null;
  }
  function restoreHistory(){
    var o = loadSaved();
    if(!o || !o.msgs.length) return false;
    if(!chat || !Array.isArray(chat.msgs)) return false;
    if(chat.msgs.length > 1) return false;      /* 本次已产生新内容 → 不覆盖 */
    chat.msgs = chat.msgs.concat(o.msgs);
    try{ renderChat(); }catch(e){}
    /* __QA_RESTORE_PILL_v2__（2026-09-20 重设计）：恢复提示改为对话流内的居中胶囊，随消息一起滚动。
       旧版把条插在聊天流顶部且复用 .qa-ctx-bar——但 .qa-ctx-bar 本身无基础样式（#qaCtxBar 的
       金色样式只命中桥接条），实际渲染成一条灰色裸横幅；现改走独立胶囊样式并落在消息末尾。 */
    var host = el('chatScroll');
    if(host){
      var bar = document.createElement('div');
      bar.id = 'qaRestoreBar';
      bar.className = 'qa-restore-pill';
      bar.setAttribute('role','status');
      bar.innerHTML = '<span class="qa-ctx-ico" aria-hidden="true">&#8635;</span>'
        + '<div class="qa-ctx-tx">已恢复 <b>' + fmtWhen(o.t) + '</b> 的对话（' + o.msgs.length + ' 条），接着问就行。</div>'
        + '<button class="qa-ctx-x" type="button" aria-label="清空并重开">&#10005;</button>';
      bar.querySelector('.qa-ctx-x').onclick = function(){
        clearSaved();
        if(bar.parentNode) bar.parentNode.removeChild(bar);
        try{ resetChat(); }catch(e){}
      };
      host.appendChild(bar);
      try{ host.scrollTop = host.scrollHeight; }catch(e){}
    }
    return true;
  }

  /* 每次落消息即持久化（节流） */
  if(!flag('addMsg')){
    try{
      if(typeof window.addMsg === 'function'){
        var _addMsg = window.addMsg;
        window.addMsg = function(){
          var r = _addMsg.apply(this, arguments);
          saveSoon();
          return r;
        };
        flag('addMsg', true);
      }
    }catch(e){}
  }
  /* 「新对话 / 清空对话」同时清掉持久化历史（并短期抑制回写，避免刚清又存） */
  ['resetChat','qaClearChat'].forEach(function(fn){
    if(flag(fn)) return;
    try{
      if(typeof window[fn] === 'function'){
        var _f = window[fn];
        window[fn] = function(){
          try{ clearSaved(); }catch(e){}
          var r = _f.apply(this, arguments);
          return r;
        };
        flag(fn, true);
      }
    }catch(e){}
  });

  /* ================= B2 多轮上下文 ================= */
  function recentTurns(n){
    try{
      var msgs = (chat && Array.isArray(chat.msgs)) ? chat.msgs : [];
      var hist = [];
      for(var i = msgs.length - 1; i >= 0 && hist.length < n * 2; i--){
        var m = msgs[i];
        if(!m || (m.role !== 'user' && m.role !== 'bot')) continue;
        var txt = htmlToText(m.html);
        if(!txt) continue;
        /* 用户提问保留更多字（追问要能对上），机器人长答案压短（避免历史压过当前上下文） */
        var isUser = (m.role === 'user');
        hist.unshift({ role: isUser ? 'user' : 'assistant', content: clip(txt, isUser ? 280 : 180) });
      }
      var total = 0, out = [];
      for(var j = hist.length - 1; j >= 0; j--){
        total += hist[j].content.length;
        if(total > CTX_MAX_CHARS) break;
        out.unshift(hist[j]);
      }
      return out;
    }catch(e){ return []; }
  }
  /* 摘要式历史：把更早的提问压成一行「此前还聊过 A / B / C」。
     比"把原文全塞进去"省 token，又保留了话题线索（追问时常要往回找）。 */
  var CTX_DIGEST_MAX = 6;
  function historyDigest(excludeTurns){
    try{
      var msgs = (chat && Array.isArray(chat.msgs)) ? chat.msgs : [];
      var stop = msgs.length - (excludeTurns || 0) * 2;
      var asks = [];
      for(var i = stop - 1; i >= 0 && asks.length < CTX_DIGEST_MAX; i--){
        var m = msgs[i];
        if(!m || m.role !== 'user') continue;
        var t = htmlToText(m.html).replace(/\\s+/g, '');
        if(!t || t.length < 2) continue;
        asks.unshift(clip(t, 16));
      }
      return asks.length ? ('【此前还聊过】' + asks.join(' / ')) : '';
    }catch(e){ return ''; }
  }

  /* 历史文本比对（忽略空白，只比前缀——足够识别"同一条"） */
  function _sameText(a, b){
    var x = String(a == null ? '' : a).replace(/\\s+/g, '').slice(0, 40);
    var y = String(b == null ? '' : b).replace(/\\s+/g, '').slice(0, 40);
    return !!x && !!y && (x === y || x.indexOf(y) >= 0 || y.indexOf(x) >= 0);
  }
  /* 注入历史前必须先和解调用方的自带消息：
     ① process 的 AI 兜底会塞 {assistant: aiLastResp}（上一次回答），历史里往往也有同一条
        → 重复占位会白烧 token，还可能让模型以为"要重答"；
     ② 天气点缀 / 情绪共情两处 system 都带「【当前语境】」，历史对它们是噪音 → 整体跳过。 */
  function injectHistory(messages){
    if(!Array.isArray(messages) || !messages.length) return messages;

    var sysText = '';
    for(var s = 0; s < messages.length; s++){
      if(messages[s] && messages[s].role === 'system') sysText += String(messages[s].content || '') + '\\n';
    }
    if(sysText.indexOf('【当前语境】') >= 0) return messages;

    var hist = recentTurns(CTX_TURNS);
    if(!hist.length) return messages;

    var owned = [];
    for(var i = 0; i < messages.length; i++){
      var mm = messages[i];
      if(mm && mm.role !== 'system') owned.push(mm.content);
    }
    if(owned.length){
      hist = hist.filter(function(h){
        for(var j = 0; j < owned.length; j++){ if(_sameText(h.content, owned[j])) return false; }
        return true;
      });
    }
    if(hist.length && hist[hist.length - 1].role === 'user'){
      for(var k = 0; k < messages.length; k++){
        if(messages[k] && messages[k].role === 'user'){
          if(_sameText(hist[hist.length - 1].content, messages[k].content)) hist.pop();
          break;
        }
      }
    }
    if(!hist.length) return messages;

    /* 摘要式补充：更早的提问压成一行，合并进首条（不新增同角色连续消息，兼容性更稳） */
    var digest = historyDigest(CTX_TURNS);
    if(digest){
      if(hist[0].role === 'user') hist[0] = { role:'user', content: digest + '\\n' + hist[0].content };
      else hist.unshift({ role:'user', content: digest });
    }

    var sys = [], rest = [];
    messages.forEach(function(m){ ((m && m.role === 'system') ? sys : rest).push(m); });
    return sys.concat(hist).concat(rest);
  }
  if(!flag('chatLLM')){
    try{
      if(typeof SpringAI === 'object' && SpringAI && typeof SpringAI.chatLLM === 'function'){
        var _chatLLM = SpringAI.chatLLM;
        SpringAI.chatLLM = function(messages, opts){
          try{
            if(!(opts && opts.noHistory)) messages = injectHistory(messages);
          }catch(e){}
          return _chatLLM.call(SpringAI, messages, opts);
        };
        flag('chatLLM', true);
      }
    }catch(e){}
  }

  /* ================= B3 历史 / 记忆抽屉 ================= */
  var drawer = null;
  function dEl(id){ try{ return document.getElementById(id); }catch(e){ return null; } }

  function assocList(){
    try{
      var o = JSON.parse(localStorage.getItem('qa_assoc_v1') || 'null');
      var map = (o && o.map && typeof o.map === 'object') ? o.map : {};
      return Object.keys(map).map(function(k){
        return { key:k, q:map[k].q || '', pool:map[k].pool || '', n:map[k].n || 0, o:map[k].o || k, t:map[k].t || 0 };
      }).sort(function(a, b){ return (b.t || 0) - (a.t || 0); });
    }catch(e){ return []; }
  }
  function poolLabel(p){
    try{ return (SRC_CFG[p] && SRC_CFG[p].label) ? SRC_CFG[p].label : (p || ''); }catch(e){ return p || ''; }
  }
  function renderDrawer(){
    var histHost = dEl('qdHist'), memHost = dEl('qdMem'), cnt = dEl('qdMemCount');
    if(histHost){
      var msgs = (chat && Array.isArray(chat.msgs)) ? chat.msgs : [];
      var asks = msgs.filter(function(m){ return m && m.role === 'user'; }).slice(-8).reverse();
      histHost.innerHTML = asks.length ? asks.map(function(m){
        var t = clip(htmlToText(m.html), 60);
        return '<button class="qd-item" type="button" data-q="' + esc(t) + '">'
          + '<span>' + esc(t) + '</span><span class="t">' + esc(m.ts || '') + '</span></button>';
      }).join('') : '<div class="qd-empty">还没有提问记录。</div>';
      Array.prototype.forEach.call(histHost.querySelectorAll('.qd-item'), function(btn){
        btn.onclick = function(){
          var q = btn.getAttribute('data-q') || '';
          closeDrawer();
          if(q) try{ ask(q); }catch(e){}
        };
      });
    }
    var list = assocList();
    if(cnt) cnt.textContent = list.length ? ('共 ' + list.length + ' 条 / 上限 200') : '';
    if(memHost){
      memHost.innerHTML = list.length ? list.map(function(it){
        return '<div class="qd-mem"><b>' + esc(it.o || it.key) + '</b>→ ' + esc(it.q)
          + '<div class="m">' + esc(poolLabel(it.pool)) + ' · 命中 ' + (it.n || 0) + ' 次'
          + (it.t ? ' · ' + fmtWhen(it.t) : '') + '</div>'
          + '<div class="ops"><button type="button" data-forget="' + esc(it.o || it.key) + '">撤销这条</button></div></div>';
      }).join('') : '<div class="qd-empty">还没有记住任何问法。未命中时点一个候选，CC 就会记住。</div>';
      Array.prototype.forEach.call(memHost.querySelectorAll('[data-forget]'), function(btn){
        btn.onclick = function(){
          var raw = btn.getAttribute('data-forget') || '';
          var done = false;
          try{ done = qaAssocForget(raw); }catch(e){}
          if(!done){ try{ done = qaAssocForget(qaAssocNorm(raw)); }catch(e){} }
          renderDrawer();
        };
      });
    }
  }
  function openDrawer(){
    if(!drawer) drawer = dEl('qaDrawer');
    if(!drawer) return;
    renderDrawer();
    drawer.classList.add('on');
    try{ window.__qaDrawerOpen = true; }catch(e){}
  }
  function closeDrawer(){
    if(!drawer) drawer = dEl('qaDrawer');
    if(drawer) drawer.classList.remove('on');
    try{ window.__qaDrawerOpen = false; }catch(e){}
  }
  window.qaOpenDrawer = openDrawer;
  window.qaCloseDrawer = closeDrawer;
  try{
    if(drawer === null) drawer = dEl('qaDrawer');
    if(drawer){
      var x = drawer.querySelector('.qd-x'), mask = drawer.querySelector('.qd-mask');
      if(x) x.onclick = closeDrawer;
      if(mask) mask.onclick = closeDrawer;
      var ex = dEl('qdExport'), ch = dEl('qdClearHist');
      if(ex) ex.onclick = function(){
        var data = { exported: new Date().toISOString(), assoc: assocList(), history: (function(){
          try{ var o = JSON.parse(localStorage.getItem(HIST_KEY) || 'null'); return (o && o.msgs) ? o.msgs.length : 0; }catch(e){ return 0; }
        })() };
        try{
          var blob = new Blob([JSON.stringify(data, null, 2)], { type:'application/json' });
          var a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = '你问我答-记忆导出.json';
          document.body.appendChild(a); a.click();
          setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); }, 0);
        }catch(e){}
      };
      if(ch) ch.onclick = function(){
        clearSaved();
        var bar = dEl('qaRestoreBar');
        if(bar && bar.parentNode) bar.parentNode.removeChild(bar);
        try{ qaClearChat(); }catch(e){}
        renderDrawer();
      };
    }
  }catch(e){}
  window.addEventListener('keydown', function(e){
    if(e.key === 'Escape' || e.keyCode === 27){
      if(drawer && drawer.classList.contains('on')){ closeDrawer(); }
    }
  });

  /* ================= 启动 ================= */
  try{ restoreHistory(); }catch(e){}

  window.QaMemory = {
    save: saveNow, clear: clearSaved, load: loadSaved,
    restore: restoreHistory, turns: recentTurns, open: openDrawer, close: closeDrawer,
    /* 2026-09-19：暴露注入器便于回归取证（本地模式下已无真实 AI 请求，
       只能在函数级断言"历史是否真被拼进 messages"） */
    injectHistory: injectHistory, digest: historyDigest
  };
})();
"""


def strip_all(s):
    pats = [
        re.escape(STYLE_OPEN) + r'.*?' + re.escape(STYLE_CLOSE) + r'\s*',
        re.escape(CSS_BEGIN) + r'.*?' + re.escape(CSS_END) + r'\s*',
        re.escape(JS_BEGIN) + r'.*?' + re.escape(JS_END) + r'\s*',
        re.escape(BTN_BEGIN) + r'.*?' + re.escape(BTN_END) + r'\s*',
        re.escape(ASIDE_BEGIN) + r'.*?' + re.escape(ASIDE_END) + r'\s*',
    ]
    for p in pats:
        s = re.sub(p, '', s, flags=re.S)
    return s


def main():
    if not os.path.exists(QA):
        print('[ERR] 找不到 qa.html')
        return 1
    src = io.open(QA, 'r', encoding='utf-8', newline='').read()
    n0 = len(src)

    state = {
        'css': src.count(CSS_BEGIN), 'js': src.count(JS_BEGIN),
        'btn': src.count(BTN_BEGIN), 'aside': src.count(ASIDE_BEGIN),
        'style_open': src.count(STYLE_OPEN),
        'anchor_js': src.count(ANCHOR_JS),
        'anchor_btn': src.count(ANCHOR_BTN),
        'anchor_aside': src.count(ANCHOR_ASIDE),
    }
    print(u'[in] qa.html %d 字符' % n0)
    print(u'[state] ' + u'  '.join(u'%s=%d' % (k, v) for k, v in sorted(state.items())))

    if CHECK:
        ok = (state['css'] == 1 and state['js'] == 1 and state['btn'] == 1 and state['aside'] == 1
              and state['style_open'] == 1 and state['anchor_js'] == 1)
        print(u'[check] 标记块齐全：%s' % (u'OK' if ok else u'FAIL'))
        return 0 if ok else 1

    for k in ('anchor_js', 'anchor_btn', 'anchor_aside'):
        if state[k] != 1:
            print(u'[ERR] 锚点 %s 出现 %d 次（期望 1），中止' % (k, state[k]))
            return 1
    if not os.path.exists(BAK):
        shutil.copy2(QA, BAK)
        print(u'[bak] 已备份 -> %s' % os.path.basename(BAK))

    s = strip_all(src)
    print(u'[strip] 剥离旧块 %d 字符' % (n0 - len(s)))

    style_block = u'<style id="qa-mem-css">\n' + CSS_BEGIN + CSS + CSS_END + u'\n</style>\n'
    i_head = s.rfind(u'</head>')
    if i_head < 0:
        print(u'[ERR] 找不到 </head>')
        return 1
    s = s[:i_head] + style_block + s[i_head:]

    btn_block = BTN_BEGIN + u'\n' + BTN + BTN_END + u'\n'
    i_btn = s.find(ANCHOR_BTN)
    if i_btn >= 0:
        # 首选：插在「⚙️ AI设置」按钮之后（.t-ai 内，视觉正确）
        i_btn_after = i_btn + len(ANCHOR_BTN)
        s = s[:i_btn_after] + u'\n    ' + btn_block.rstrip(u'\n') + s[i_btn_after:]
    else:
        # 回退：AI设置按钮尚未注入（补丁链顺序），插到 </header> 之前
        i_btn = s.find(ANCHOR_BTN_FALLBACK)
        if i_btn < 0:
            print(u'[ERR] 顶栏按钮锚点定位失败')
            return 1
        s = s[:i_btn] + u'    ' + btn_block.rstrip(u'\n') + u'\n' + s[i_btn:]
    # 自检：按钮必须仍在 </header> 之前（曾在某轮重建中被移出 .t-ai，导致入口不可见）
    i_hdr = s.find('</header>', s.find('t-ai'))
    assert i_hdr > 0 and s.find('QAMEM_BTN_END') < i_hdr, 'QAMEM 按钮落在了 </header> 之后'

    aside_block = ASIDE_BEGIN + u'\n' + ASIDE + ASIDE_END + u'\n'
    i_aside = s.find(ANCHOR_ASIDE)
    if i_aside < 0:
        print(u'[ERR] 抽屉锚点定位失败')
        return 1
    s = s[:i_aside] + aside_block + s[i_aside:]

    js_block = u'\n' + JS_BEGIN + JS + JS_END + u'\n'
    i_js = s.find(ANCHOR_JS)
    if i_js < 0:
        print(u'[ERR] JS 锚点定位失败')
        return 1
    i_js_ins = i_js + len(ANCHOR_JS)
    s = s[:i_js_ins] + js_block + s[i_js_ins:]

    checks = {
        u'CSS 块 1 份': s.count(CSS_BEGIN) == 1 and s.count(CSS_END) == 1,
        u'JS 块 1 份': s.count(JS_BEGIN) == 1 and s.count(JS_END) == 1,
        u'按钮块 1 份': s.count(BTN_BEGIN) == 1 and s.count(BTN_END) == 1,
        u'抽屉块 1 份': s.count(ASIDE_BEGIN) == 1 and s.count(ASIDE_END) == 1,
        u'style 外壳 1 份': s.count(STYLE_OPEN) == 1,
        u'JS 排在 bridge 之后': s.find(JS_BEGIN) > s.find(ANCHOR_JS),
        u'抽屉 DOM 存在': u'id="qaDrawer"' in s,
        u'顶栏历史按钮': u'onclick="qaOpenDrawer()"' in s,
        u'持久化键 qa_history_v1': u"qa_history_v1" in s,
        u'历史恢复逻辑': u'restoreHistory' in s,
        u'多轮上下文注入': u'injectHistory' in s,
        u'摘要式上下文': u'historyDigest' in s,
        u'场景跳过（天气/情绪不带历史）': u'【当前语境】' in s,
        u'与调用方消息去重': u'_sameText' in s,
        u'chatLLM 已包装': u'SpringAI.chatLLM = function' in s,
        u'联想记忆撤销': u'qaAssocForget' in s,
        u'记忆导出': u'你问我答-记忆导出.json' in s,
        u'幂等标志独立': u'__qaMemFlags' in s,
        u'script 标签平衡': s.count(u'<script') == s.count(u'</script>'),
        u'html 闭合 1 份': s.count(u'</html>') == 1,
    }
    fails = [k for k, v in checks.items() if not v]
    for k, v in checks.items():
        print(u'  [%s] %s' % (u'OK' if v else u'NG', k))
    if fails:
        print(u'!! 自检失败 %d 项，未写盘' % len(fails))
        return 1

    s.encode('utf-8')
# __ATOMIC_WRITE_20260921__
    _tmp_w = (QA) + ".tmp_write"
    with io.open(_tmp_w, "w", encoding="utf-8", newline="") as _f_w:
        _f_w.write(s)
    os.replace(_tmp_w, (QA))
    print(u'[out] qa.html %d -> %d 字符（+%d）' % (n0, len(s), len(s) - n0))
    print(u'[done] 会话记忆已注入。重建壳：python _build_all.py build && python _build_hosted.py && python _check_needles.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
