# -*- coding: utf-8 -*-
"""
「你问我答」跨板块桥接注入器 v1 —— 幂等（strip -> replay）
=================================================================
解决 2026-09-19 审计确认的 P0 断点：壳层 `cc:nav-jump` 深跳通道早已就绪
（index.html:3805 navJumpTo，3 次补发容错），但 qa 只监听 theme-changed，
导致「其它板块 / 首页 / 教程 带着问题跳进问答」这条路根本不通。

注入内容：
  <style id="qa-bridge-css">  上下文条样式（浅色 + 深色）
  /*__QA_BRIDGE_BEGIN__*/     桥接逻辑（插在既有 message 监听之后、同一 <script> 内）

能力：
  A1 监听 cc:nav-jump         —— 接收 {q, src, from, view}，静默切库 + 预置问题
  A2 URL 深链 ?q=&src=&from=  —— 独立打开 / 壳层转发均可
  A3 上抛 cc:crumb            —— 壳层顶栏显示「你问我答 › 当前库」
  A4 jumpTo 带上下文          —— 原问题写 sessionStorage（同页切换）+ 新标签 URL 参数

⚠️ qa.html 是「源」不是产物：本脚本改完必须重建壳
   python _build_all.py build   （内含 _gzip_build / _build_4in1 / _apply_ux_polish）
   python _build_hosted.py
   python _check_needles.py
⚠️ 首次运行备份 qa.html -> _bak_qa_bridge_20260919.html
用法：python _apply_qa_bridge_20260919.py [--check]
"""
import io
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
QA = os.path.join(HERE, 'qa.html')
BAK = os.path.join(HERE, '_bak_qa_bridge_20260919.html')

CSS_BEGIN = '/*__QA_BRIDGE_CSS__*/'
CSS_END = '/*__QA_BRIDGE_CSS_END__*/'
JS_BEGIN = '/*__QA_BRIDGE_BEGIN__*/'
JS_END = '/*__QA_BRIDGE_END__*/'
STYLE_OPEN = '<style id="qa-bridge-css">'
STYLE_CLOSE = '</style>'

# 注入锚点：既有 message 监听的收尾（qa.html:9538-9541）
ANCHOR = u"  if(d && d.type === 'theme-changed') updateAiStatus();\n});"

CHECK = '--check' in sys.argv

CSS = u"""
/* 2026-09-19 用户要求：上下文条「置于聊天框弹出」——与底部控制台 #qaDeck 同宽，
   弹在控制台正上方，不再占据消息流顶部 */
#qaCtxBar{display:flex;align-items:center;gap:9px;margin:0 auto 10px;padding:10px 12px;
  width:100%;max-width:calc(var(--midW,860px) - 40px);box-sizing:border-box;
  background:var(--gold-soft,#FEF6DC);border:1px solid var(--gold,#F5B800);border-radius:12px;
  font-size:12.5px;color:#6B5200;line-height:1.55;}
#qaCtxBar .qa-ctx-ico{font-size:15px;flex-shrink:0;}
#qaCtxBar .qa-ctx-tx{min-width:0;}
#qaCtxBar b{font-weight:700;}
#qaCtxBar .qa-ctx-x{margin-left:auto;border:none;background:transparent;color:#6B5200;
  font-size:15px;width:34px;height:34px;min-width:34px;border-radius:9px;flex-shrink:0;
  display:inline-flex;align-items:center;justify-content:center;transition:background .16s;}
#qaCtxBar .qa-ctx-x:hover{background:rgba(107,82,0,.12);}
#qaCtxBar .qa-ctx-x:focus-visible{outline:2px solid var(--gold,#F5B800);outline-offset:1px;}
html[data-theme="dark"] #qaCtxBar{background:#2A2410;border-color:#6B5200;color:#F5D98A;}
html[data-theme="dark"] #qaCtxBar .qa-ctx-x{color:#F5D98A;}
html[data-theme="dark"] #qaCtxBar .qa-ctx-x:hover{background:rgba(245,217,138,.14);}
@media (min-width:761px){
  #qaCtxBar{max-width:calc(var(--midW,860px) - 64px);}
}
@media (max-width:760px){
  #qaCtxBar{font-size:12.5px;padding:10px 11px;margin-left:8px;margin-right:8px;width:auto;}
  #qaCtxBar .qa-ctx-x{width:44px;height:44px;min-width:44px;}
}
"""

JS = u"""
(function(){
  var JUMP_CTX_KEY = 'spring_jump_ctx';
  var FROM_NAMES = {
    performance:'绩效管理', quiz:'培训考核', beauty:'美妆话术', manual:'手册奖惩',
    medical:'医疗急救', daily:'日常问题', risk:'风险预警', report:'事件报告',
    kbadmin:'库管理', home:'CC 之家', issues:'问题反馈'
  };

  function escHtml(s){
    return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  /* ---- A3：把「当前库」上报壳层顶栏面包屑（壳层已有 cc:crumb 接收端） ---- */
  function pushCrumb(){
    try{
      if(!(window.parent && window.parent !== window)) return;
      var lbl = '';
      try{ lbl = (typeof currentPoolLabel === 'function') ? currentPoolLabel() : ''; }catch(e){}
      window.parent.postMessage({ type:'cc:crumb', mod:'qa', text: lbl ? ('你问我答 › ' + lbl) : '你问我答' }, (typeof ccParentOrigin === 'function' ? ccParentOrigin() : '*'));
    }catch(e){}
  }

  /* ---- 上下文条：可关闭。2026-09-19 用户要求「置于聊天框弹出」：
     弹在底部控制台 #qaDeck 正上方（同一父容器 #qaFlow），不再插消息流顶部；
     无控制台（异常态）时回落到消息流最上方。不进入 chatWrap，避免被 renderChat 重写。 ---- */
  function renderCtxBar(from, q, src){
    try{
      var old = document.getElementById('qaCtxBar');
      if(old && old.parentNode) old.parentNode.removeChild(old);
      var host = el('chatScroll');
      if(!host) return;
      var fromName = FROM_NAMES[from] || '';
      var title;
      if(fromName && q)      title = '从 <b>' + escHtml(fromName) + '</b> 带来一个问题，已填到输入框，可改写成自己的问法再发送。';
      else if(fromName)      title = '从 <b>' + escHtml(fromName) + '</b> 跳转过来。';
      else if(q)             title = '已带入问题，可直接发送。';
      else                   title = '已切换到 <b>' + escHtml(SRC_CFG[src] ? SRC_CFG[src].name : src) + '</b>。';

      var bar = document.createElement('div');
      bar.id = 'qaCtxBar';
      bar.className = 'qa-ctx-bar';
      bar.setAttribute('role','status');
      bar.innerHTML = '<span class="qa-ctx-ico" aria-hidden="true">&#8617;</span>'
        + '<div class="qa-ctx-tx">' + title + '</div>'
        + '<button class="qa-ctx-x" type="button" aria-label="忽略带入">&#10005;</button>';
      bar.querySelector('.qa-ctx-x').onclick = function(){
        if(bar.parentNode) bar.parentNode.removeChild(bar);
      };
      var deckEl = document.getElementById('qaDeck');
      if(deckEl && deckEl.parentNode){ deckEl.parentNode.insertBefore(bar, deckEl); }
      else{ host.insertBefore(bar, host.firstChild); }
    }catch(e){}
  }

  /* ---- A1/A2：带入问题 + 静默切库 + 提示条 ---- */
  function applyIncoming(payload){
    if(!payload) return false;
    var q   = String(payload.q   || '').trim();
    var src = String(payload.src || '').trim();
    var from= String(payload.from|| '').trim();
    if(!q && !src) return false;

    if(src && SRC_CFG[src] && src !== qaSource){
      try{ setQaSourceSilent(src); }catch(e){}
    }

    renderCtxBar(from, q, src);

    if(q){
      try{
        var ti = el('qaInput');
        if(ti){
          ti.value = q;
          ti.style.height = 'auto';
          ti.style.height = Math.min(ti.scrollHeight, 124) + 'px';
          if(typeof updateSendBtn === 'function') updateSendBtn();
        }
      }catch(e){}
    }
    pushCrumb();
    return true;
  }

  /* ---- A2：读 URL 深链参数 ---- */
  function readUrlCtx(){
    try{
      var sp = new URLSearchParams(location.search || '');
      var o = { q: sp.get('q') || '', src: sp.get('src') || '', from: sp.get('from') || '' };
      return (o.q || o.src) ? o : null;
    }catch(e){ return null; }
  }

  /* ---- A1：接收壳层深跳 ---- */
  /* 2026-09-22 安全审查修复：深跳消息此前不校验来源，跨源父页可注入上下文驱动本模块切库/预置问题。
     现只接受同源（http/https）或 file:// 本地文档发来的消息，与 index.html 的 ccMsgTrusted 同口径。 */
  function _ccMsgTrustedQa(e){
    try{
      if(e.origin && e.origin !== 'null') return e.origin === location.origin;
      if(location.protocol === 'file:') return true;
      var fr = document.querySelectorAll('iframe');
      for(var i=0;i<fr.length;i++){ if(fr[i].contentWindow === e.source) return true; }
    }catch(err){}
    return false;
  }
  window.addEventListener('message', function(e){
    if(!_ccMsgTrustedQa(e)) return;
    var d = e.data || {};
    if(d.type !== 'cc:nav-jump') return;
    if(d.mod && d.mod !== 'qa') return;
    var p = d.ctx || {};
    if(typeof d.q    === 'string') p.q    = d.q;
    if(typeof d.src  === 'string') p.src  = d.src;
    if(typeof d.from === 'string') p.from = d.from;
    if(typeof d.view === 'string' && !p.src && SRC_CFG[d.view]) p.src = d.view;
    applyIncoming(p);
  });

  /* ---- A4：jumpTo 带上下文（发出侧） ----
     ⚠️ 通道选 localStorage 而非 sessionStorage：本项目 file:// 下 localStorage 跨板块
     共享**已被实证**（kb_overlay_v1 / qa_perf_dirty 等本机键都靠它互通），
     而 sessionStorage 在 file:// 的同目录不同文件之间是否共享没有保证。
     ⚠️ 必须带 `to`（目标模块名）：storage 事件会广播给**所有**同源文档，
     壳层里多个 iframe 并存时，若不指明目标，谁先响应谁就把上下文消费掉，
     真正的目标模块反而看不到（2026-09-19 实战实测抓到）。
     目标板块侧由 _apply_qa_landing_20260919.py 认领（TTL 5 分钟 + 消费即清）。 */
  function rememberJumpCtx(q, mod){
    if(!q) return;
    try{
      localStorage.setItem(JUMP_CTX_KEY, JSON.stringify({
        from:'qa', q:String(q).slice(0,200), to:String(mod || ''), t:Date.now()
      }));
    }catch(e){}
  }
  var JUMP_FILES = { quiz:'quiz.html', performance:'performance.html', beauty:'beauty.html',
    manual:'manual.html', daily:'daily.html', risk:'risk-lite.html', medical:'medical.html',
    report:'report.html', kbadmin:'kb-admin.html' };

  /* 记住最后一次原问题（包装 ask，内联 onclick 仍走全局同名函数）
     ⚠️ 幂等标志不能挂在包装函数上：_apply_pet.py 注入的形象包装位于本文档之后（PET_STAGE 段），
     会再次覆盖 window.ask，把函数上的属性一并抹掉（2026-09-19 实测踩到，与「ready.js 累积」
     「__apkFreeMemory 被覆盖」同属一类：同文档多处赋值，最后执行者赢）。
     故改用独立全局标志记录，调用链仍成立：pet 包装 → 本包装 → 原 ask，__qaLastQ 照常写入。 */
  if(!(window.__qaBridgeFlags && window.__qaBridgeFlags.ask)){
    try{
      if(typeof window.ask === 'function'){
        var _ask = window.ask;
        window.ask = function(q){
          try{ window.__qaLastQ = String(q || '').slice(0,200); }catch(e){}
          return _ask.apply(this, arguments);
        };
        window.__qaBridgeFlags = window.__qaBridgeFlags || {};
        window.__qaBridgeFlags.ask = true;
      }
    }catch(e){}
  }

  /* 包装 jumpTo：内嵌时交给壳层切换（上下文已写 sessionStorage）；
     独立打开时把原问题拼进 URL，目标模块可直接读取 */
  if(!(window.__qaBridgeFlags && window.__qaBridgeFlags.jumpTo)){
    try{
      if(typeof window.jumpTo === 'function'){
        var _jump = window.jumpTo;
        window.jumpTo = function(mod, opts){
          var q = (opts && opts.q) || window.__qaLastQ || '';
          if(q) rememberJumpCtx(q, mod);
          try{
            var standalone = !(window.parent && window.parent !== window);
            if(standalone && mod && q && JUMP_FILES[mod]){
              window.open(JUMP_FILES[mod] + '?from=qa&q=' + encodeURIComponent(q), '_blank', 'noopener');
              return;
            }
          }catch(e){}
          return _jump.apply(this, arguments);
        };
        window.__qaBridgeFlags = window.__qaBridgeFlags || {};
        window.__qaBridgeFlags.jumpTo = true;
      }
    }catch(e){}
  }

  /* ---- 开场：URL 深链优先，否则只汇报面包屑 ---- */
  try{
    var u = readUrlCtx();
    if(u) applyIncoming(u); else pushCrumb();
  }catch(e){}

  window.QaBridge = { apply: applyIncoming, crumb: pushCrumb, readUrl: readUrlCtx };
})();
"""


def strip_css(s):
    s = re.sub(re.escape(STYLE_OPEN) + r'.*?' + re.escape(STYLE_CLOSE) + r'\s*', '', s, flags=re.S)
    s = re.sub(re.escape(CSS_BEGIN) + r'.*?' + re.escape(CSS_END) + r'\s*', '', s, flags=re.S)
    return s


def strip_js(s):
    return re.sub(re.escape(JS_BEGIN) + r'.*?' + re.escape(JS_END) + r'\s*', '', s, flags=re.S)


def count(s, needle):
    return s.count(needle)


def main():
    if not os.path.exists(QA):
        print('[ERR] 找不到 qa.html')
        return 1
    src = io.open(QA, 'r', encoding='utf-8', newline='').read()
    n0 = len(src)

    # ---------- 状态盘点 ----------
    state = {
        'css_begin': count(src, CSS_BEGIN), 'css_end': count(src, CSS_END),
        'js_begin': count(src, JS_BEGIN), 'js_end': count(src, JS_END),
        'style_open': count(src, STYLE_OPEN), 'style_close': count(src, STYLE_CLOSE),
        'anchor': count(src, ANCHOR),
    }
    print(u'[in] qa.html %d 字节' % n0)
    print(u'[state] ' + u'  '.join(u'%s=%d' % (k, v) for k, v in sorted(state.items())))

    if CHECK:
        ok = (state['css_begin'] == 1 and state['css_end'] == 1
              and state['js_begin'] == 1 and state['js_end'] == 1
              and state['style_open'] == 1 and state['anchor'] == 1)
        print(u'[check] 标记块与锚点齐全：%s' % (u'OK' if ok else u'FAIL'))
        return 0 if ok else 1

    if state['anchor'] != 1:
        print(u'[ERR] 注入锚点出现 %d 次（期望 1），中止以免误伤' % state['anchor'])
        return 1
    if state['style_close'] < 1:
        print(u'[ERR] 找不到 </style> 外壳，中止')
        return 1
    if not os.path.exists(BAK):
        shutil.copy2(QA, BAK)
        print(u'[bak] 已备份 -> %s' % os.path.basename(BAK))

    # ---------- 剥离旧块（幂等） ----------
    s = strip_css(src)
    s = strip_js(s)
    stripped = n0 - len(s)
    print(u'[strip] 剥离旧块 %d 字节' % stripped)

    # ---------- 注入 CSS（</head> 取最后一个，防内嵌字符串里出现同名标签） ----------
    style_block = u'<style id="qa-bridge-css">\n' + CSS_BEGIN + CSS + CSS_END + u'\n</style>\n'
    i_head = s.rfind(u'</head>')
    if i_head < 0:
        print(u'[ERR] 找不到 </head>')
        return 1
    s = s[:i_head] + style_block + s[i_head:]

    # ---------- 注入 JS（锚点之后） ----------
    js_block = u'\n' + JS_BEGIN + JS + JS_END + u'\n'
    i_anchor = s.find(ANCHOR)
    if i_anchor < 0:
        print(u'[ERR] 锚点定位失败')
        return 1
    i_ins = i_anchor + len(ANCHOR)
    s = s[:i_ins] + js_block + s[i_ins:]

    # ---------- 自检（每类注入块必须恰好 1 份） ----------
    checks = {
        u'CSS 标记 1 份': count(s, CSS_BEGIN) == 1 and count(s, CSS_END) == 1,
        u'JS 标记 1 份': count(s, JS_BEGIN) == 1 and count(s, JS_END) == 1,
        u'style 外壳 1 份': count(s, STYLE_OPEN) == 1,
        u'锚点仍在 1 份': count(s, ANCHOR) == 1,
        u'JS 在锚点之后': s.find(JS_BEGIN) > s.find(ANCHOR),
        u'QaBridge 导出': u'window.QaBridge' in s,
        u'cc:nav-jump 监听': u"d.type !== 'cc:nav-jump'" in s,
        u'cc:crumb 上报': u"type:'cc:crumb'" in s,
        u'URL 深链读取': u'URLSearchParams' in s,
        u'跳转上下文走 localStorage': u'localStorage.setItem(JUMP_CTX_KEY' in s,
        u'ask 包装标志': u'window.__qaBridgeFlags.ask = true' in s,
        u'jumpTo 包装标志': u'window.__qaBridgeFlags.jumpTo = true' in s,
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
    print(u'[out] qa.html %d -> %d 字节（+%d）' % (n0, len(s), len(s) - n0))
    print(u'[done] 桥接已注入。请重建壳：python _build_all.py build && python _build_hosted.py && python _check_needles.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
