# -*- coding: utf-8 -*-
"""你问我答 · 答案卡增强（2026-09-21 · 批1-A）
--------------------------------------------------------------------------------
提案编号：N3 一键复制答案 / N5 答案朗读 / N1 收藏星标 / M1 置信度徽标

设计要点（为什么这样接，而不是改 kbReply / renderChat）：
  · 命中分数的唯一可得处是 kbReply(hits, rawText) 的入参 —— 因此**包一层** window.kbReply
    抓取 {top, n, src, pool}，不改原函数一行（kbReply 是顶层 function 声明，本就在 window 上）。
  · 工具条与徽标**在 addMsg 时写进 html 字符串**，而不是渲染后用 MutationObserver 补 DOM。
    理由：renderChat 是「整体重写 innerHTML」，DOM 装饰每次渲染都会丢；而 html 字符串会进
    chat.msgs 并随 qa_history_v1 持久化 → 重渲染 / 刷新恢复后依然在，也不需要监听器。
  · 复制走「临时 display:none 掉自己的工具条，再取 innerText」——保证复制到的正文干净。

幂等：块由 /*__QA_ANSWER_TOOLS_20260921__*/ 守卫；window.__QA_ANSWER_TOOLS_20260921__ 运行时去重。
用法：python _apply_qa_answer_tools_20260921.py [--check]
"""
import io
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.abspath(__file__))
QA = os.path.join(ROOT, 'qa.html')
BAK = os.path.join(ROOT, '_bak_qa_answer_tools_20260921.html')
BEGIN = '/*__QA_ANSWER_TOOLS_20260921_BEGIN__*/'
END = '/*__QA_ANSWER_TOOLS_20260921_END__*/'
ANCHOR = '/*__QA_QUICKSTART_END__*/'
GUARD = '__QA_ANSWER_TOOLS_20260921__'


def _atomic_write(path, text):
    """先写临时文件再原子替换：任何编码/写入异常都不会破坏源文件。"""
    tmp = path + '.tmp_write'
    io.open(tmp, 'w', encoding='utf-8', newline='').write(text)
    os.replace(tmp, path)


BLOCK = BEGIN + r'''
/* ===================== 答案卡增强（2026-09-21） =====================
   N3 一键复制答案 · N5 答案朗读 · N1 收藏星标 · M1 置信度徽标
   全部本机完成：复制用 Clipboard API，朗读用浏览器本地 speechSynthesis，零联网零外发。 */
(function(){
  if (window.__QA_ANSWER_TOOLS_20260921__) return;
  window.__QA_ANSWER_TOOLS_20260921__ = true;

  var STAR_KEY = 'qa_star_v1';
  var CONF_KEY = 'qa_conf_on_v1';
  var confOn = true;
  try { confOn = localStorage.getItem(CONF_KEY) !== '0'; } catch(e){}

  /* 最近一次 kbReply 的命中信息（由下面的包装捕获） */
  var last = { top: 0, n: 0, src: '', pool: '', used: true, at: 0 };

  /* ---------------- 样式 ---------------- */
  function css(){
    if (document.getElementById('qa-at-css')) return;
    var st = document.createElement('style');
    st.id = 'qa-at-css';
    st.textContent = [
      '.qa-at{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:10px;padding-top:9px;border-top:1px dashed var(--border,#E5EDE9);}',
      '.qa-at-b{border:1px solid var(--border,#E5EDE9);background:var(--primary-mist,#F4F9F6);color:#2E6B4F;border-radius:999px;',
      'padding:5px 11px;font-size:.72rem;font-weight:700;cursor:pointer;font-family:inherit;min-height:30px;line-height:1;white-space:nowrap;}',
      '.qa-at-b:hover{border-color:var(--primary,#148453);color:var(--primary,#148453);}',
      '.qa-at-b.on{background:var(--primary,#148453);color:#fff;border-color:var(--primary,#148453);}',
      '.qa-at-b.sp{color:#946200;border-color:#F0DCB0;background:#FFF9EE;}',
      '.qa-at-b.sp.on{background:#946200;color:#fff;border-color:#946200;}',
      '.qa-at-conf{display:inline-flex;align-items:center;gap:4px;border-radius:999px;padding:3px 9px;font-size:.68rem;font-weight:800;margin:0 0 8px;}',
      '.qa-at-conf.h{background:#E8F5EC;color:#0F7B3F;border:1px solid #B9E3CB;}',
      '.qa-at-conf.m{background:#FFF6E5;color:#946200;border:1px solid #F0DCB0;}',
      '.qa-at-conf.l{background:#F1F3F2;color:#5A6F65;border:1px solid #DDE5E1;}',
      'html[data-theme="dark"] .qa-at-conf.h{background:#123524;color:#8FD3B0;border-color:#1E4A31;}',
      'html[data-theme="dark"] .qa-at-conf.m{background:#3A2E12;color:#E8C77A;border-color:#5A4620;}',
      'html[data-theme="dark"] .qa-at-conf.l{background:#1B2622;color:#9FB3AA;border-color:#2A3B34;}',
      'html[data-theme="dark"] .qa-at-b{background:#1A3D2A;color:#8FD3B0;border-color:#1E3A2C;}',
      'html[data-theme="dark"] .qa-at-b.sp{background:#3A2E12;color:#E8C77A;border-color:#5A4620;}',
      '.qa-at-toast{position:fixed;left:50%;top:calc(env(safe-area-inset-top,0px) + 62px);transform:translateX(-50%);z-index:99;',
      'background:#0F2A1F;color:#fff;padding:8px 16px;border-radius:999px;font-size:.78rem;font-weight:700;',
      'box-shadow:0 8px 22px rgba(0,0,0,.25);opacity:0;pointer-events:none;transition:opacity .2s;max-width:82vw;text-align:center;}',
      '.qa-at-toast.on{opacity:.94;}'
    ].join('');
    (document.head || document.documentElement).appendChild(st);
  }

  /* ---------------- 小工具 ---------------- */
  function toast(t){
    try{
      var d = document.getElementById('qa-at-toast');
      if (!d){ d = document.createElement('div'); d.id = 'qa-at-toast'; d.className = 'qa-at-toast'; document.body.appendChild(d); }
      d.textContent = t; d.classList.add('on');
      clearTimeout(d.__t); d.__t = setTimeout(function(){ d.classList.remove('on'); }, 1600);
    }catch(e){}
  }

  function stripTags(s){
    return String(s || '').replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").trim();
  }

  /* 从答案卡 html 里取标题（.qa-title 的第二个 span），用于收藏列表显示 */
  function titleOf(html){
    var m = String(html).match(/class="qa-title"[\s\S]*?<span class="qi">([\s\S]*?)<\/span>\s*<span>([\s\S]*?)<\/span>/);
    if (!m) return '';
    return stripTags(m[2]).replace(/\s+/g, ' ').slice(0, 60);
  }

  /* ---------------- 收藏（qa_star_v1，上限 200，与联想记忆同款存储模式） ---------------- */
  function stars(){
    try{ var a = JSON.parse(localStorage.getItem(STAR_KEY) || '[]'); return (a && a.length) ? a : []; }catch(e){ return []; }
  }
  function saveStars(a){
    try{ localStorage.setItem(STAR_KEY, JSON.stringify((a || []).slice(-200))); }catch(e){}
  }
  function starKeyOf(item){ return String(item.q || '') + '||' + String(item.t || ''); }

  function isStarred(rec){
    var k = starKeyOf(rec);
    return stars().some(function(x){ return starKeyOf(x) === k; });
  }

  function toggleStar(rec){
    var a = stars(), k = starKeyOf(rec);
    var i = -1;
    for (var n = 0; n < a.length; n++){ if (starKeyOf(a[n]) === k){ i = n; break; } }
    if (i >= 0){ a.splice(i, 1); toast('已取消收藏'); }
    else { a.push({ q: rec.q || '', t: rec.t || '', src: rec.src || '', pool: rec.pool || '', ts: new Date().toISOString() }); toast('已收藏 · 可在控制台「★ 收藏」里找回'); }
    saveStars(a);
    refreshStars();
    return i < 0;
  }

  function refreshStars(){
    try{
      Array.prototype.forEach.call(document.querySelectorAll('.qa-at-b[data-act="star"]'), function(b){
        var rec = { q: b.getAttribute('data-q') || '', t: b.getAttribute('data-t') || '' };
        b.classList.toggle('on', isStarred(rec));
        b.textContent = isStarred(rec) ? '\u2605 已收藏' : '\u2606 收藏';
      });
    }catch(e){}
  }

  /* ---------------- 置信度（M1） ---------------- */
  function confOf(html, fresh){
    var s = String(html);
    var miss = s.indexOf('\uD83E\uDD37') >= 0 || s.indexOf('切换知识库') >= 0;
    if (miss) return { k: 'l', label: '置信度 低', why: '当前知识库没有直接命中，下面是相近条目或引导。建议换个关键词，或切换到对应库再问。' };
    if (fresh && fresh.top){
      var t = fresh.top;
      var extra = (fresh.n > 1) ? ('，另有 ' + (fresh.n - 1) + ' 条相近条目') : '';
      if (t >= 20) return { k: 'h', label: '置信度 高', why: '命中证据充分（总分 ' + t + '，来源 ' + (fresh.pool || '当前库') + extra + '）。' };
      return { k: 'm', label: '置信度 中', why: '命中证据中等（总分 ' + t + '，来源 ' + (fresh.pool || '当前库') + extra + '），关键数值请以手册原文为准。' };
    }
    return { k: 'h', label: '库内直答', why: '来自知识库条目直答，含出处标注。' };
  }

  /* ---------------- 复制 / 朗读 ----------------
     复制给同事的是「能直接转发的答案」：形象口播（立春给你翻到了—— / 还有想问的随时喊我。）、
     推荐芯片与跳转按钮、自己的工具条与徽标，全部排除。临时 display:none 后取 innerText，
     取完立刻还原（不靠克隆——克隆节点脱离文档后 innerText 拿不到换行）。 */
  function cleanText(inner){
    var hides = [];
    function hide(n){ if (n){ hides.push([n, n.style.display]); n.style.display = 'none'; } }
    hide(inner.querySelector('.qa-at'));
    hide(inner.querySelector('.qa-at-conf'));
    Array.prototype.forEach.call(inner.querySelectorAll('.pet-voice'), hide);
    Array.prototype.forEach.call(inner.querySelectorAll('button'), hide);
    Array.prototype.forEach.call(inner.children, function(c){
      var t = String(c.textContent || '').replace(/\s+/g, '');
      /* 💡 你可能想问 / 📎 你可能还想了解 —— 这两个推荐段整块去掉。
         注意用 slice(0,2)：emoji 是代理对，charAt(0) 只拿到高代理位，比较恒为假。 */
      if (t.slice(0, 2) === '\uD83D\uDCA1' || t.slice(0, 2) === '\uD83D\uDCCE') hide(c);
    });
    var t = '';
    try { t = inner.innerText || inner.textContent || ''; } catch(e){ t = inner.textContent || ''; }
    hides.forEach(function(h){ try{ h[0].style.display = h[1]; }catch(e){} });
    return String(t).replace(/[ \t]+$/gm, '').replace(/\n{3,}/g, '\n\n').trim();
  }

  function copy(btn){
    var inner = btn.closest('.bubble-inner');
    if (!inner) return;
    var t = cleanText(inner);
    if (!t){ toast('这条没有可复制的正文'); return; }
    var done = function(){ toast('已复制 · 可直接粘贴给同事'); };
    try{
      if (navigator.clipboard && navigator.clipboard.writeText){
        navigator.clipboard.writeText(t).then(done, function(){ legacyCopy(t) && done(); });
        return;
      }
    }catch(e){}
    if (legacyCopy(t)) done(); else toast('复制失败，请长按选中文字');
  }

  function legacyCopy(t){
    try{
      var ta = document.createElement('textarea');
      ta.value = t;
      ta.setAttribute('readonly', 'readonly');
      ta.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0;';
      document.body.appendChild(ta);
      ta.select(); ta.setSelectionRange(0, t.length);
      var ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return ok;
    }catch(e){ return false; }
  }

  function zhVoice(){
    try{
      var vs = window.speechSynthesis ? (speechSynthesis.getVoices() || []) : [];
      for (var i = 0; i < vs.length; i++){ if (/^zh/i.test(vs[i].lang || '')) return vs[i]; }
    }catch(e){}
    return null;
  }

  function speak(btn){
    try{
      if (!window.speechSynthesis){ toast('当前环境不支持朗读'); return; }
      var inner = btn.closest('.bubble-inner');
      if (!inner) return;
      if (btn.classList.contains('on')){
        speechSynthesis.cancel();
        refreshSpeakBtns();
        return;
      }
      var t = cleanText(inner);
      if (!t){ toast('这条没有可朗读的正文'); return; }
      Array.prototype.forEach.call(document.querySelectorAll('.qa-at-b[data-act="speak"]'), function(b){ b.classList.remove('on'); });
      var u = new SpeechSynthesisUtterance(t);
      u.lang = 'zh-CN'; u.rate = 1; u.pitch = 1;
      var v = zhVoice(); if (v) u.voice = v;
      u.onend = u.onerror = function(){ refreshSpeakBtns(); };
      speechSynthesis.cancel();
      speechSynthesis.speak(u);
      btn.classList.add('on'); btn.textContent = '\u23F9 停止朗读';
    }catch(e){ toast('朗读启动失败'); }
  }

  function refreshSpeakBtns(){
    try{
      Array.prototype.forEach.call(document.querySelectorAll('.qa-at-b[data-act="speak"]'), function(b){
        if (!b.classList.contains('on')) return;
        b.classList.remove('on'); b.textContent = '\uD83D\uDD0A 朗读';
      });
    }catch(e){}
  }

  /* ---------------- 答案卡装饰（在 addMsg 时写进 html，随会话持久化） ---------------- */
  function hasTools(html){ return String(html).indexOf('class="qa-at"') >= 0; }

  function decorate(html, q){
    if (hasTools(html)) return html;
    var fresh = (last && !last.used && (Date.now() - last.at) < 6000) ? last : null;
    if (fresh) fresh.used = true;
    var conf = confOf(html, fresh);
    var title = titleOf(html) || stripTags(q).slice(0, 60);
    var src = (fresh && fresh.src) ? fresh.src : '';
    var pool = (fresh && fresh.pool) ? fresh.pool : '';
    var qa = String(q || '').replace(/"/g, '&quot;');
    var ta = String(title).replace(/"/g, '&quot;');

    var confHtml = confOn
      ? ('<span class="qa-at-conf ' + conf.k + '" title="' + conf.why.replace(/"/g, '&quot;') + '">' + conf.label + '</span>')
      : '';
    var tools = '<div class="qa-at">'
      + '<button class="qa-at-b" type="button" data-act="copy" onclick="window.QAAT.copy(this)">\uD83D\uDCCB 复制</button>'
      + '<button class="qa-at-b" type="button" data-act="speak" onclick="window.QAAT.speak(this)">\uD83D\uDD0A 朗读</button>'
      + '<button class="qa-at-b" type="button" data-act="star" data-q="' + qa + '" data-t="' + ta + '" data-src="' + String(src).replace(/"/g, '&quot;') + '" data-pool="' + String(pool).replace(/"/g, '&quot;') + '" onclick="window.QAAT.star(this)">\u2606 收藏</button>'
      + '</div>';
    return confHtml + html + tools;
  }

  /* ---------------- 接管 addMsg（不改原函数） ---------------- */
  var _addMsg = window.addMsg;
  if (typeof _addMsg === 'function'){
    window.addMsg = function(role, html, opts){
      try{
        if (role === 'bot' && opts && opts.answer){
          html = decorate(String(html), opts.q || '');
        }
      }catch(e){}
      return _addMsg.call(this, role, html, opts);
    };
  }

  /* ---------------- 包一层 kbReply，捕获本次命中分数 ---------------- */
  var _kbReply = window.kbReply;
  if (typeof _kbReply === 'function'){
    window.kbReply = function(hits, rawText){
      try{
        var h = (hits && hits[0]) || null;
        last = {
          top: h ? (h.s || 0) : 0,
          n: (hits || []).length,
          src: (h && h.k) ? (h.k.src || '') : '',
          pool: (typeof window.currentPoolLabel === 'function') ? String(window.currentPoolLabel() || '') : '',
          used: false,
          at: Date.now()
        };
      }catch(e){}
      return _kbReply.apply(this, arguments);
    };
  }

  /* ---------------- 对外接口（供批1-B 的收藏面板调用） ---------------- */
  window.QAAT = {
    copy: copy,
    speak: speak,
    star: function(btn){
      var rec = {
        q: btn.getAttribute('data-q') || '',
        t: btn.getAttribute('data-t') || '',
        src: btn.getAttribute('data-src') || '',
        pool: btn.getAttribute('data-pool') || ''
      };
      toggleStar(rec);
      return false;
    },
    listStars: stars,
    saveStars: saveStars,
    starKeyOf: starKeyOf,
    removeStar: function(idx){
      var a = stars();
      if (idx < 0 || idx >= a.length) return;
      a.splice(idx, 1); saveStars(a); refreshStars();
    },
    clearStars: function(){ saveStars([]); refreshStars(); },
    refresh: function(){ refreshStars(); },
    confLabel: function(){
      return confOn ? '置信度徽标 开' : '置信度徽标 关';
    },
    setConf: function(on){
      confOn = !!on;
      try{ localStorage.setItem(CONF_KEY, confOn ? '1' : '0'); }catch(e){}
      toast(confOn ? '置信度徽标已开启（对新回答生效）' : '置信度徽标已关闭（对新回答生效）');
    }
  };

  function boot(){
    css();
    refreshStars();
    /* 兜底：会话恢复出来的旧答案（早于本补丁）也给补上工具条 —— 仅在确认没有工具条的答案卡上做 */
    try{
      Array.prototype.forEach.call(document.querySelectorAll('#chatWrap .msg.bot .bubble-inner'), function(inner){
        if (inner.querySelector('.qa-at')) return;
        if (!/📚|🤷|切换知识库/.test(inner.textContent || '')) return;
        var wrap = document.createElement('div');
        wrap.innerHTML = decorate(inner.innerHTML, '');
        var node = wrap.firstChild;
        while (node){
          var nx = node.nextSibling;
          inner.appendChild(node);
          node = nx;
        }
      });
      refreshStars();
    }catch(e){}
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
  setTimeout(boot, 1200);
})();
''' + END


def strip_block(s):
    return re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END) + r'\s*', '', s, flags=re.S)


def main():
    if not os.path.exists(QA):
        print('[ERR] 找不到 qa.html')
        return 1
    s = io.open(QA, 'r', encoding='utf-8', newline='').read()
    n_before = len(s)

    if BEGIN in s:
        print('[up] 旧块存在 → strip 后 replay（块内容升级）')
        if not os.path.exists(BAK):
            shutil.copy2(QA, BAK)
            print('[bak] -> %s' % os.path.basename(BAK))
        s = strip_block(s)
        if s.count(ANCHOR) != 1:
            print('[ERR] strip 后锚点 %s 出现 %d 次（应为 1）' % (ANCHOR, s.count(ANCHOR)))
            return 1
        s = s.replace(ANCHOR, ANCHOR + '\n' + BLOCK, 1)
    else:
        if s.count(ANCHOR) != 1:
            print('[ERR] 锚点 %s 出现 %d 次（应为 1）' % (ANCHOR, s.count(ANCHOR)))
            return 1
        if not os.path.exists(BAK):
            shutil.copy2(QA, BAK)
            print('[bak] -> %s' % os.path.basename(BAK))
        s = s.replace(ANCHOR, ANCHOR + '\n' + BLOCK, 1)
        print('[+] 已插入答案卡增强块（%d 字符）' % len(BLOCK))

    checks = {
        '块恰好 1 份': s.count(BEGIN) == 1 and s.count(END) == 1,
        '锚点仍唯一': s.count(ANCHOR) == 1,
        '运行时守卫': GUARD in s,
        '包装 kbReply': 'window.kbReply = function(hits, rawText){' in s,
        '包装 addMsg': 'window.addMsg = function(role, html, opts){' in s,
        '未改原 kbReply 定义': 'function kbReply(hits, rawText){' in s,
        '未改原 addMsg 定义': 'function addMsg(role, html, opts){' in s,
        '四个工具条动作': all(x in s for x in ['data-act="copy"', 'data-act="speak"', 'data-act="star"', 'qa-at-conf']),
        '收藏存储键': "'qa_star_v1'" in s,
        '复制降级通道': 'execCommand' in s,
        '排除形象口播': "querySelectorAll('.pet-voice')" in s,
        '排除推荐芯片段': "t.slice(0, 2) === '\\uD83D\\uDCA1'" in s,
        '朗读走本地合成': 'SpeechSynthesisUtterance' in s,
        '对外接口 QAAT': 'window.QAAT = {' in s,
        'script 标签平衡': s.count('<script') == s.count('</script>'),
        # 幂等重跑走的是 strip→replay 路径，体积会基本持平（只随块内容增减）→ 用容差而非「必须增长」
        '体积未异常变化': abs(len(s) - n_before) < 60000,
    }
    fails = [k for k, v in checks.items() if not v]
    for k, v in checks.items():
        print('  [%s] %s' % ('OK' if v else 'NG', k))
    if fails:
        print('!! 自检失败，未写盘')
        return 1
    _atomic_write(QA, s)
    print('[ok] 答案卡增强已就位（+%d 字符）' % (len(s) - n_before))
    return 0


if __name__ == '__main__':
    if '--check' in sys.argv:
        s = io.open(QA, 'r', encoding='utf-8', newline='').read()
        ok = BEGIN in s and GUARD in s and s.count(BEGIN) == 1
        print('[check] 答案卡增强：%s' % ('OK' if ok else 'FAIL'))
        raise SystemExit(0 if ok else 1)
    raise SystemExit(main())
