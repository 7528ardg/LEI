# -*- coding: utf-8 -*-
"""
「你问我答」能力增强注入器 v1 —— 幂等（strip -> replay）
=================================================================
对应 2026-09-19 审计的 C 组四项：

  C1 语音输入      输入区加麦克风（Web Speech API）。file:// / 不支持的环境**优雅降级**：
                   按钮置灰 + 说明原因，不静默失败。APK(cabin.local) 与 PWA(HTTPS) 下可用。
  C2 跨板块数据    按意图把本机其它板块的数据摘要喂给 AI（绩效库条数/月份范围、培训记录、
                   风险预警状态），写进 user 消息前缀，避免 AI 对“我的绩效/错题”类问题空谈。
  C3 跨域智能引导  未命中且问题其实是“功能操作”时，直接给去对应板块的按钮，
                   而不是只答一句“没有直接命中”。
  C4 场景化推荐    按当前时段 + 当前形态（节气）生成推荐问题，替代固定死列表。

注入位置：紧跟 D2/D4 块的 JS_END（链路 cap -> ux -> memory -> bridge -> 原函数）
⚠️ qa.html 是「源」：改完必须重建壳
⚠️ 首次运行备份 qa.html -> _bak_qa_cap_20260919.html
用法：python _apply_qa_capability_20260919.py [--check]
"""
import io
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
QA = os.path.join(HERE, 'qa.html')
BAK = os.path.join(HERE, '_bak_qa_cap_20260919.html')

CSS_BEGIN = '/*__QA_CAP_CSS__*/'
CSS_END = '/*__QA_CAP_CSS_END__*/'
JS_BEGIN = '/*__QA_CAP_BEGIN__*/'
JS_END = '/*__QA_CAP_END__*/'
MIC_BEGIN = '<!-- QACAP_MIC_BEGIN -->'
MIC_END = '<!-- QACAP_MIC_END -->'
STYLE_OPEN = '<style id="qa-cap-css">'
STYLE_CLOSE = '</style>'

ANCHOR_JS = '/*__QA_UX_END__*/'
ANCHOR_MIC = '<button class="send-btn" id="sendBtn"'

CHECK = '--check' in sys.argv

CSS = u"""
/* ---- C1 语音输入按钮（与发送键同尺寸，44px 触摸达标） ---- */
#qaMic{width:44px;height:44px;flex-shrink:0;border-radius:14px;border:1px solid var(--border,#E5EDE9);
  background:var(--bg-card,#fff);color:var(--text2,#5A6F65);font-size:17px;
  display:inline-flex;align-items:center;justify-content:center;transition:all .18s;cursor:pointer;}
#qaMic:hover{border-color:var(--primary,#148453);color:var(--primary,#148453);background:var(--primary-mist,#F4F9F6);}
#qaMic.rec{background:var(--danger,#C62828);border-color:var(--danger,#C62828);color:#fff;}
#qaMic:disabled{opacity:.5;cursor:not-allowed;}
#qaMic.rec::after{content:'';position:absolute;width:44px;height:44px;border-radius:14px;
  border:2px solid var(--danger,#C62828);animation:qaMicPulse 1.4s ease-out infinite;}
@keyframes qaMicPulse{0%{opacity:.9;transform:scale(1);}100%{opacity:0;transform:scale(1.28);}}
@media (prefers-reduced-motion:reduce){#qaMic.rec::after{animation:none;}}
/* ---- C3 跨域引导条 ---- */
.qa-guide{margin-top:9px;padding-top:9px;border-top:1px dashed var(--border,#E5EDE9);}
.qa-guide .gt{font-size:.75rem;font-weight:800;color:var(--primary-dark,#0C5F3A);margin-bottom:6px;}
/* ---- C4 推荐问题卡 ---- */
#qaSuggest{margin:0 0 11px;padding:10px 12px;border:1px solid var(--border,#E5EDE9);
  border-radius:12px;background:var(--primary-mist,#F4F9F6);}
#qaSuggest .st{font-size:.75rem;font-weight:800;color:var(--primary-dark,#0C5F3A);margin-bottom:7px;}
#qaSuggest .sx{float:right;border:none;background:transparent;color:var(--text3,#9DB0A6);
  font-size:14px;width:30px;height:30px;border-radius:8px;cursor:pointer;}
html[data-theme="dark"] #qaSuggest{background:#142E22;border-color:#1E3A2C;}
"""

MIC = u"""<button class="mic-btn" id="qaMic" type="button" title="语音输入（持续监听，内容累积追加）" aria-label="语音输入">&#127908;</button>
<button class="mic-btn" id="qaTrBtn" type="button" title="翻译模式：说中文自动译成所选语言" aria-label="翻译模式">文A</button>
"""

JS = u"""
(function(){
  function flag(k, v){
    window.__qaCapFlags = window.__qaCapFlags || {};
    if(v === undefined) return !!window.__qaCapFlags[k];
    window.__qaCapFlags[k] = v;
  }
  function $(id){ try{ return document.getElementById(id); }catch(e){ return null; } }
  function esc2(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
  function clip(s, n){ s = String(s == null ? '' : s); return s.length > n ? s.slice(0, n) + '…' : s; }

/* ================= C1 语音输入 PRO（QA_VOICE_PRO_v1：持续监听+累积追加+翻译模式+原生桥） ================= */
/*QA_VOICE_PRO_v1_BEGIN*/
  if(!flag('voicepro')){
  try{
    var mic=$('qaMic'), trBtn=$('qaTrBtn'), trStrip=$('qaTrStrip');
    var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
    var V={mode:'off', lang:(function(){try{return localStorage.getItem('qa_tr_lang_v1')||'en';}catch(e){return 'en';}})(),
      recOn:false, manualStop:false, base:'', finals:[], interim:'', rec:null, restartTimer:null, voiceOwned:false};
    function host(){ try{ var h=window.CabinHost||(window.parent&&window.parent.CabinHost); return (h&&typeof h.voiceStart==='function')?h:null; }catch(e){ return null; } }
    var NATIVE=!!host();
    /* __QA_IOS_MIC_v1__ iOS 适配（2026-09-20）：iOS 的网页语音识别（webkitSpeechRecognition）
       必须先拿到麦克风授权才可能出字，且首次弹窗常被吞——用 getUserMedia 在用户手势内先触发
       系统授权弹窗（拿到后立即停轨），再进 SR；授权失败给出 iPhone 设置路径的定向提示。 */
    var IS_IOS=(function(){ try{ var u=navigator.userAgent||''; return /iP(hone|od|ad)/.test(u)||(/Macintosh/.test(u)&&navigator.maxTouchPoints>1); }catch(e){ return false; } })();
    function iOSMicUnlock(cb){
      if(!(IS_IOS && navigator.mediaDevices && navigator.mediaDevices.getUserMedia)){ cb(); return; }
      try{
        navigator.mediaDevices.getUserMedia({audio:true}).then(function(st){
          try{ st.getTracks().forEach(function(t){ t.stop(); }); }catch(e){}
          cb();
        }).catch(function(){
          voiceHint('麦克风权限未开启：请在 iPhone「设置 > Safari > 麦克风」中允许，或刷新页面并在弹窗中点「允许」');
          voiceOff(true);
        });
      }catch(e){ cb(); }
    }
    function voiceHint(t){ try{ if(window.PET&&PET.say) PET.say(t); }catch(e){} try{ mic.title=t; }catch(e){} }
    function trRender(){
      var ti=$('qaInput'); if(!ti) return;
      var committed=V.finals.map(function(f){ return V.mode==='translate' ? (f.tr||f.zh) : f.zh; }).join(' ');
      ti.value=(V.base? V.base+' ':'') + committed + ((V.interim&&committed)?' ':'') + (V.interim||'');
      V.voiceOwned=true;
      ti.style.height='auto'; ti.style.height=Math.min(ti.scrollHeight,124)+'px';
      if(typeof updateSendBtn==='function') updateSendBtn();
    }
    function translateOne(zh){
      try{
        var eng=window.QA_I18N; if(!eng) return {text:'',score:0,miss:true};
        var r=eng.splitTranslate(zh, V.lang);
        return r;
      }catch(e){ return {text:'',score:0,miss:true}; }
    }
    function commitFinal(text){
      text=String(text||'').trim(); if(!text) return;
      var seg={zh:text, tr:''};
      if(V.mode==='translate'){
        var r=translateOne(text);
        seg.tr=r.text||''; seg.score=r.score;
        if(r.miss || !seg.tr){ seg.tr=''; seg.miss=true; }
      }
      V.finals.push(seg); V.interim='';
      if(seg.miss) voiceHint('这句暂无标准译文，先保留原文，可换个说法试试');
      trRender();
    }
    function uiRec(on){
      try{
        if(on){ mic.classList.add('rec'); mic.textContent='⏹'; mic.setAttribute('aria-pressed','true'); }
        else{ mic.classList.remove('rec'); mic.textContent='🎙'; mic.setAttribute('aria-pressed','false'); }
      }catch(e){}
    }
    function setPlaceholder(){
      try{
        var ti=$('qaInput'); if(!ti) return;
        if(V.mode==='translate'){
          var eng=window.QA_I18N; var nm=(eng&&eng.LANGS[V.lang]&&eng.LANGS[V.lang].name)||V.lang;
          ti.placeholder='翻译模式 · 持续说中文，'+nm+'译文自动累积在此…';
        }else{
          ti.placeholder='问点什么？比如：病假怎么请 / 雅诗兰黛小棕瓶 / 帮我写一段销售话术…';
        }
      }catch(e){}
    }
    function applyLangChips(){
      try{
        if(trStrip) trStrip.querySelectorAll('.qa-tr-chip').forEach(function(b){
          b.classList.toggle('on', b.dataset.lang===V.lang);
        });
      }catch(e){}
    }
    /* —— 模式开关 —— */
    function voiceOn(mode){
      V.mode=mode; V.manualStop=false; V.base='';
      var ti=$('qaInput');
      if(ti && ti.value.trim() && !V.voiceOwned) V.base=ti.value.trim();  /* 只保留用户手打内容 */
      else if(ti){ ti.value=''; }
      V.finals=[]; V.interim='';
      if(trStrip) trStrip.hidden=(mode!=='translate');
      if(trBtn) trBtn.classList.toggle('on', mode==='translate');
      setPlaceholder(); applyLangChips(); uiRec(true);
      if(NATIVE){ try{ host().voiceStart(); }catch(e){ voiceHint('原生语音启动失败'); } }
      else if(SR){ iOSMicUnlock(startWeb); }
      else{ voiceHint(IS_IOS ? '此 iOS 环境不支持网页语音识别：请用 Safari 打开本页使用麦克风，或改用键盘输入' : '当前环境不支持语音输入'); voiceOff(); }
    }
    function voiceOff(silent){
      flushInterim();
      V.manualStop=true; V.mode='off';
      if(V.restartTimer){ clearTimeout(V.restartTimer); V.restartTimer=null; }
      if(NATIVE){ try{ host().voiceStop(); }catch(e){} }
      else if(V.rec){ try{ V.rec.stop(); }catch(e){} }
      if(trStrip) trStrip.hidden=true;
      if(trBtn) trBtn.classList.remove('on');
      uiRec(false); setPlaceholder();
      if(!silent) voiceHint('语音输入已结束');
    }
    function flushInterim(){
      if(V.interim && V.interim.trim()){ var t=V.interim; V.interim=''; commitFinal(t); }
    }
    /* —— Web 识别（浏览器/PWA） —— */
    function startWeb(){
      if(!V.rec){
        V.rec=new SR(); V.rec.lang='zh-CN'; V.rec.interimResults=true; V.rec.continuous=true;
        V.rec.onstart=function(){ V.recOn=true; uiRec(true); };
        V.rec.onresult=function(ev){
          var fin='', mid='';
          for(var i=ev.resultIndex;i<ev.results.length;i++){
            var rs=ev.results[i];
            if(rs.isFinal) fin+=rs[0].transcript; else mid+=rs[0].transcript;
          }
          if(fin.trim()) commitFinal(fin);
          V.interim=mid; trRender();
        };
        V.rec.onerror=function(ev){
          var c=String((ev&&ev.error)||'');
          if(c==='no-speech'||c==='aborted') return;                 /* 交给 onend 自动重启 */
          if(c==='not-allowed'||c==='service-not-allowed'){ voiceHint(IS_IOS ? '麦克风权限被拒绝：请在 iPhone「设置 > Safari > 麦克风」中允许后重试' : '麦克风权限被拒绝，请在浏览器设置里允许后重试'); voiceOff(true); return; }
          if(c==='network') voiceHint('语音识别需要联网（当前环境或代理可能不通）');
          else if(c!=='no-speech') voiceHint('语音识别失败：'+c);
        };
        V.rec.onend=function(){
          V.recOn=false;
          if(!V.manualStop && V.mode!=='off'){
            /* 持续监听核心：识别引擎每次自然结束（停顿/60s上限）后自动重启 */
            if(V.restartTimer) clearTimeout(V.restartTimer);
            V.restartTimer=setTimeout(function(){ try{ V.rec.start(); }catch(e){} }, 300);
          }else{
            flushInterim(); uiRec(false);
          }
        };
      }
      try{ V.rec.start(); }catch(e){ /* already started */ }
    }
    /* —— 原生识别（APK：SpeechRecognizer→__cabinVoice→storage 事件） —— */
    window.__qaVoiceNativeEvent=function(d){
      d=d||{};
      if(d.e==='ready'){ V.recOn=true; uiRec(true); }
      else if(d.e==='partial'){ V.interim=d.text||''; trRender(); }
      else if(d.e==='final'){ commitFinal(d.text||''); trRender(); }
      else if(d.e==='end'){
        V.recOn=false;
        if(!V.manualStop && V.mode!=='off'){
          if(V.restartTimer) clearTimeout(V.restartTimer);
          V.restartTimer=setTimeout(function(){ try{ host().voiceStart(); }catch(e){} }, 300);
        }else{
          flushInterim(); uiRec(false);
        }
      }
      else if(d.e==='error'){
        var c=String(d.code||'');
        if(c==='6'){ /* busy：忽略，等 end */ }
        else if(c==='7'){ /* no-match：等下一轮 */ }
        else if(c==='8'){ voiceHint('本机没有可用的语音识别服务'); voiceOff(true); }
        else if(c==='2'||c==='9'){ voiceHint('识别服务网络不可用，稍后自动重试'); }
        else if(c==='1'){ voiceHint('网络超时，稍后自动重试'); }
      }
    };
    if(!window.__qaVoiceStorageHook__){
      window.__qaVoiceStorageHook__=true;
      window.addEventListener('storage', function(ev){
        if(!ev || ev.key!=='cabin_voice_evt') return;
        var p=null; try{ p=JSON.parse(ev.newValue||'null'); }catch(e){}
        if(p && p.d && typeof window.__qaVoiceNativeEvent==='function') window.__qaVoiceNativeEvent(p.d);
      });
    }
    /* —— 控件事件 —— */
    if(mic){
      mic.onclick=function(){ if(V.mode!=='off'){ voiceOff(); } else { voiceOn('listen'); } };
      mic.title='语音输入：持续监听，内容按顺序累积';
    }
    if(trBtn){
      trBtn.onclick=function(){ if(V.mode==='translate'){ voiceOff(); } else { voiceOn('translate'); } };
    }
    if(trStrip){
      trStrip.querySelectorAll('.qa-tr-chip').forEach(function(b){
        b.onclick=function(){ V.lang=b.dataset.lang; try{ localStorage.setItem('qa_tr_lang_v1', V.lang); }catch(e){} applyLangChips(); setPlaceholder(); };
      });
      applyLangChips();
    }
    /* —— 翻译模式下的发送：译文入对话 + 复制，不打断持续识别 —— */
    window.qaTrCopyTxt=function(btn){
      try{
        var t=btn.getAttribute('data-txt')||'';
        if(navigator.clipboard&&navigator.clipboard.writeText) navigator.clipboard.writeText(t);
        voiceHint('译文已复制');
      }catch(e){}
    };
    if(!flag('sendWrap')){
      try{
        if(typeof window.sendMsg==='function'){
          var _send=window.sendMsg;
          window.sendMsg=function(){
            var ti=$('qaInput');
            var val=ti?ti.value.trim():'';
            if(V.mode==='translate'){
              if(!val && !V.finals.length) return;
              flushInterim();
              var lines='';
              V.finals.forEach(function(f){
                var tr=f.tr||f.zh;
                lines+='<div class="qa-tr-line"><div class="qa-tr-src">原文：'+esc2(f.zh)+'</div><div class="qa-tr-val">'+esc2(tr)+'<button class="qa-tr-copy" type="button" data-txt="'+esc2(tr)+'" onclick="qaTrCopyTxt(this)">📋 复制</button></div></div>';
              });
              if(V.base) lines='<div class="qa-tr-line"><div class="qa-tr-val">'+esc2(V.base)+'<button class="qa-tr-copy" type="button" data-txt="'+esc2(V.base)+'" onclick="qaTrCopyTxt(this)">📋 复制</button></div></div>'+lines;
              try{ if(typeof addMsg==='function'){ addMsg('user', esc2(val||V.finals.map(function(f){return f.zh;}).join(' '))); addMsg('bot', '<b>🌐 译文（'+((window.QA_I18N&&QA_I18N.LANGS[V.lang]&&QA_I18N.LANGS[V.lang].name)||V.lang)+'）</b>'+lines); } }catch(e){}
              if(navigator.clipboard&&navigator.clipboard.writeText){ try{ navigator.clipboard.writeText(val||V.finals.map(function(f){return f.tr||f.zh;}).join(' ')); }catch(e){} }
              V.finals=[]; V.interim=''; V.base=''; V.voiceOwned=false;
              if(ti){ ti.value=''; ti.style.height='auto'; }
              if(typeof updateSendBtn==='function') updateSendBtn();
              try{ ti.blur(); }catch(e){}
              return;
            }
            var r=_send.apply(this, arguments);
            /* 普通模式发送后清空累积，避免清空的输入被 trRender 回填 */
            V.base=''; V.finals=[]; V.interim=''; V.voiceOwned=false;
            return r;
          };
          flag('sendWrap', true);
        }
      }catch(e){}
    }
    /* —— e2e 测试钩子（自动化测试用，无 UI 影响） —— */
    window.QAVoicePro={
      state:function(){ return {mode:V.mode, lang:V.lang, recOn:V.recOn, native:NATIVE, finals:V.finals.map(function(f){return {zh:f.zh,tr:f.tr};}), interim:V.interim}; },
      feedFinal:function(t){ commitFinal(t); },
      feedPartial:function(t){ V.interim=t||''; trRender(); },
      start:function(m){ voiceOn(m||'listen'); },
      stop:function(){ voiceOff(true); }
    };
    setPlaceholder();
  }catch(e){ try{ console.warn('QA_VOICE_PRO init fail', e); }catch(_e){} }
  flag('voicepro', true);
  }
/*QA_VOICE_PRO_v1_END*/
  
  /* ================= C2 跨板块数据进 AI 上下文 ================= */
  var JUMP_FILES = { quiz:'quiz.html', performance:'performance.html', beauty:'beauty.html',
    manual:'manual.html', daily:'daily.html', risk:'risk-lite.html', medical:'medical.html',
    report:'report.html', kbadmin:'kb-admin.html' };

  function perfHint(){
    try{
      var o = JSON.parse(localStorage.getItem('qa_perf_data_v1') || 'null');
      if(!o) return '';
      var rows = (o.rows && o.rows.length) ? o.rows : (Array.isArray(o) ? o : []);
      var latest = '';
      try{
        var ms = rows.map(function(r){ return r && r.月份; }).filter(Boolean).sort();
        latest = ms.length ? ms[ms.length - 1] : '';
      }catch(e){}
      return '绩效库已收录 ' + rows.length + ' 条记录' + (latest ? '，最新月份 ' + latest : '') + '（明细只在本机，需要具体分数请让用户直接问姓名+月份）';
    }catch(e){ return ''; }
  }
  function trainHint(){
    try{
      var recs = JSON.parse(localStorage.getItem('qa_train_records_v1') || '[]');
      if(!recs || !recs.length) return '';
      var last = recs[recs.length - 1] || {};
      return '最近一次在线练习：' + (last.chapter || last.章节 || '未知章节') + '，得分 ' + (last.score != null ? last.score : '未知') + '（共 ' + recs.length + ' 次记录）';
    }catch(e){ return ''; }
  }
  function crossHint(text){
    var t = String(text || '');
    var hints = [];
    try{
      if(/绩效|排名|得分|积分|班组分数|考核结果/.test(t)){ var a = perfHint(); if(a) hints.push(a); }
      if(/练习|错题|刷题|培训|考过|做过的题/.test(t)){ var b = trainHint(); if(b) hints.push(b); }
      if(/天气|台风|预警|风险|颠簸/.test(t)) hints.push('天气与风险预警由「风险预警」板块实时提供，本机缓存可能滞后');
    }catch(e){}
    return hints.length ? ('【本机相关数据】' + hints.join('；') + '\\n\\n') : '';
  }

  /* 在 chatLLM 调用前把 hint 拼到最后一条 user 消息 */
  if(!flag('chatLLM')){
    try{
      if(typeof SpringAI === 'object' && SpringAI && typeof SpringAI.chatLLM === 'function'){
        var _chat = SpringAI.chatLLM;
        SpringAI.chatLLM = function(messages, opts){
          try{
            if(Array.isArray(messages) && !(opts && opts.noCrossData)){
              for(var i = messages.length - 1; i >= 0; i--){
                var m = messages[i];
                if(m && m.role === 'user' && typeof m.content === 'string' && m.content.indexOf('【本机相关数据】') < 0){
                  var h = crossHint(m.content);
                  if(h) messages[i] = { role:'user', content: h + m.content };
                  break;
                }
              }
            }
          }catch(e){}
          return _chat.call(SpringAI, messages, opts);
        };
        flag('chatLLM', true);
      }
    }catch(e){}
  }

  /* ================= C3 跨域智能引导 ================= */
  var DOMAIN = [
    { re:/错题|刷题|练习|题库|考核|考试|培训记录/, mod:'quiz',        name:'培训考核' },
    { re:/排名|绩效|得分|积分|班组分数|考核结果/, mod:'performance', name:'绩效管理' },
    { re:/话术|销售|推销|美妆|化妆品|护肤/,      mod:'beauty',      name:'美妆话术' },
    { re:/急救|CPR|心肺复苏|受伤|医疗/,          mod:'medical',     name:'医疗急救' },
    { re:/奖惩|扣分记录|处分|通报/,              mod:'manual',      name:'手册奖惩' },
    { re:/天气|台风|预警|风险/,                  mod:'risk',        name:'风险预警' },
    { re:/事件|上报|填报告|报告流程/,            mod:'report',      name:'事件报告' }
  ];
  function guideFor(text){
    var t = String(text || '');
    for(var i = 0; i < DOMAIN.length; i++){
      if(DOMAIN[i].re.test(t)) return DOMAIN[i];
    }
    return null;
  }
  function guideHtml(text){
    var g = guideFor(text);
    if(!g) return '';
    return '<div class="qa-guide"><div class="gt">\\uD83E\\uDDED 这更像是功能操作，不用在这儿找答案：</div>'
      + '<div style="display:flex;flex-wrap:wrap;gap:7px">'
      + '<button class="w-chip" onclick="jumpTo(\\'' + g.mod + '\\')">去「' + esc2(g.name) + '」\\u2794</button>'
      + '</div></div>';
  }
  if(!flag('addMsg')){
    try{
      if(typeof window.addMsg === 'function'){
        var _add = window.addMsg;
        window.addMsg = function(role, html, opts){
          if(role === 'bot' && typeof html === 'string' && html.indexOf('还没有直接命中') >= 0){
            try{
              var q = (opts && opts.q) || window.__qaLastQ || '';
              var g = guideHtml(q);
              if(g) arguments[1] = html + g;
            }catch(e){}
          }
          return _add.apply(this, arguments);
        };
        flag('addMsg', true);
      }
    }catch(e){}
  }

  /* ================= C4 场景化推荐问题 ================= */
  function seasonName(){
    try{ if(window.PET && PET.current && PET.current.n) return PET.current.n; }catch(e){}
    return '';
  }
  function suggestPool(){
    var h = new Date().getHours();
    var out = [];
    if(h >= 5 && h < 11)       out = ['签到迟到了怎么办', '病假要交什么材料', '今天广州天气怎样'];
    else if(h >= 11 && h < 17) out = ['颠簸怎么处置', '延误时怎么服务', '尊享飞流程是什么'];
    else if(h >= 17 && h < 23) out = ['夜航注意事项', '落地前要检查什么', '仪容仪表标准'];
    else                       out = ['疲劳管理怎么规定', '红眼航班注意事项', '误机怎么扣分'];
    var s = seasonName();
    if(s) out.push('今天是「' + s + '」，有什么讲究');
    return out.slice(0, 4);
  }
  function renderSuggest(){
    /*__QA_SUGGEST_OFF_20260919__*/ return; /* 顶部常问条已按用户要求下线（2026-09-19） */
    try{
      var host = el('chatScroll');
      if(!host || $('qaSuggest')) return;
      var pool = suggestPool();
      if(!pool.length) return;
      var h = new Date().getHours();
      var slot = h < 5 ? '凌晨' : h < 11 ? '上午' : h < 17 ? '下午' : h < 23 ? '晚间' : '深夜';
      var box = document.createElement('div');
      box.id = 'qaSuggest';
      box.innerHTML = '<button class="sx" type="button" aria-label="不再显示">\\u2715</button>'
        + '<div class="st">\\uD83D\\uDCA1 现在是' + slot + '，同事们常问：</div>'
        + '<div style="display:flex;flex-wrap:wrap;gap:7px">'
        + pool.map(function(q){
            return '<button class="w-chip" type="button" data-q="' + esc2(q) + '">' + esc2(clip(q, 18)) + '</button>';
          }).join('')
        + '</div>';
      box.querySelector('.sx').onclick = function(){ if(box.parentNode) box.parentNode.removeChild(box); };
      Array.prototype.forEach.call(box.querySelectorAll('.w-chip'), function(b){
        b.onclick = function(){ var q = b.getAttribute('data-q') || ''; if(q) try{ ask(q); }catch(e){} };
      });
      host.insertBefore(box, host.firstChild);
    }catch(e){}
  }
  try{ setTimeout(renderSuggest, 700); }catch(e){}

  window.QaCap = { suggest: suggestPool, guide: guideFor, crossHint: crossHint, renderSuggest: renderSuggest };
})();
"""


def strip_all(s):
    pats = [
        re.escape(STYLE_OPEN) + r'.*?' + re.escape(STYLE_CLOSE) + r'\s*',
        re.escape(CSS_BEGIN) + r'.*?' + re.escape(CSS_END) + r'\s*',
        re.escape(JS_BEGIN) + r'.*?' + re.escape(JS_END) + r'\s*',
        re.escape(MIC_BEGIN) + r'.*?' + re.escape(MIC_END) + r'\s*',
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
        'css': src.count(CSS_BEGIN), 'js': src.count(JS_BEGIN), 'mic': src.count(MIC_BEGIN),
        'style_open': src.count(STYLE_OPEN), 'anchor_js': src.count(ANCHOR_JS),
        'anchor_mic': src.count(ANCHOR_MIC),
    }
    print(u'[in] qa.html %d 字符' % n0)
    print(u'[state] ' + u'  '.join(u'%s=%d' % (k, v) for k, v in sorted(state.items())))

    if CHECK:
        ok = (state['css'] == 1 and state['js'] == 1 and state['mic'] == 1
              and state['style_open'] == 1 and state['anchor_js'] == 1 and state['anchor_mic'] == 1)
        print(u'[check] 标记块齐全：%s' % (u'OK' if ok else u'FAIL'))
        return 0 if ok else 1

    for k in ('anchor_js', 'anchor_mic'):
        if state[k] != 1:
            print(u'[ERR] 锚点 %s 出现 %d 次（期望 1），中止' % (k, state[k]))
            return 1
    if not os.path.exists(BAK):
        shutil.copy2(QA, BAK)
        print(u'[bak] 已备份 -> %s' % os.path.basename(BAK))

    s = strip_all(src)
    print(u'[strip] 剥离旧块 %d 字符' % (n0 - len(s)))

    style_block = u'<style id="qa-cap-css">\n' + CSS_BEGIN + CSS + CSS_END + u'\n</style>\n'
    i_head = s.rfind(u'</head>')
    if i_head < 0:
        print(u'[ERR] 找不到 </head>')
        return 1
    s = s[:i_head] + style_block + s[i_head:]

    mic_block = MIC_BEGIN + u'\n' + MIC + MIC_END + u'\n'
    i_mic = s.find(ANCHOR_MIC)
    if i_mic < 0:
        print(u'[ERR] 麦克风锚点定位失败')
        return 1
    s = s[:i_mic] + mic_block + s[i_mic:]

    js_block = u'\n' + JS_BEGIN + JS + JS_END + u'\n'
    i_js = s.find(ANCHOR_JS)
    if i_js < 0:
        print(u'[ERR] JS 锚点定位失败')
        return 1
    i_ins = i_js + len(ANCHOR_JS)
    s = s[:i_ins] + js_block + s[i_ins:]

    checks = {
        u'CSS 块 1 份': s.count(CSS_BEGIN) == 1 and s.count(CSS_END) == 1,
        u'JS 块 1 份': s.count(JS_BEGIN) == 1 and s.count(JS_END) == 1,
        u'麦克风块 1 份': s.count(MIC_BEGIN) == 1 and s.count(MIC_END) == 1,
        u'style 外壳 1 份': s.count(STYLE_OPEN) == 1,
        u'JS 排在 D2/D4 之后': s.find(JS_BEGIN) > s.find(ANCHOR_JS),
        u'麦克风按钮存在': u'id="qaMic"' in s,
        u'语音识别接入': u'webkitSpeechRecognition' in s,
        u'语音优雅降级': u'当前环境不支持语音输入' in s,
        u'语音PRO引擎': u'QA_VOICE_PRO_v1_BEGIN' in s and u'QA_VOICE_PRO_v1_END' in s,
        u'翻译按钮': u'id="qaTrBtn"' in s,
        u'跨板块数据提示': u'【本机相关数据】' in s,
        u'绩效数据读取': u'qa_perf_data_v1' in s,
        u'培训记录读取': u'qa_train_records_v1' in s,
        u'跨域引导表': u'这更像是功能操作' in s,
        u'场景化推荐': u'renderSuggest' in s,
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
    print(u'[done] 已注入。重建壳：python _build_all.py build && python _build_hosted.py && python _check_needles.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
