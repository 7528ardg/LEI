# -*- coding: utf-8 -*-
"""你问我答 · 控制台「我的」面板（2026-09-21 · 批1-B）
--------------------------------------------------------------------------------
提案编号：N1 收藏星标（列表侧）/ L5 成绩趋势曲线 / P1 字号三档

依赖：批1-A（_apply_qa_answer_tools_20260921.py）提供的 window.QAAT（stars/listStars/saveStars）
      —— 本补丁锚定在 A 的 END 标记之后，A 不在就直接失败，不做静默降级。

为什么做成「一个面板 + 一个控制台键」而不是三个按键：
  #petBar 已有 换形态 / 🐾 形象 / 🧊 3D / 💡 快问 四个胶囊，窄屏再加三个会换行把控制台撑高。
  收纳成一个『👤 我的』入口（收藏 / 练习 / 字号 三块），既省横向空间，也正对提案 O2
  「我的成长档案」的方向。

幂等：块由 /*__QA_MYPANEL_20260921__*/ 守卫；window.__QA_MYPANEL_20260921__ 运行时去重。
用法：python _apply_qa_mypanel_20260921.py [--check]
"""
import io
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.abspath(__file__))
QA = os.path.join(ROOT, 'qa.html')
BAK = os.path.join(ROOT, '_bak_qa_mypanel_20260921.html')
BEGIN = '/*__QA_MYPANEL_20260921_BEGIN__*/'
END = '/*__QA_MYPANEL_20260921_END__*/'
ANCHOR = '/*__QA_ANSWER_TOOLS_20260921_END__*/'
DEP = '__QA_ANSWER_TOOLS_20260921__'
GUARD = '__QA_MYPANEL_20260921__'
TRAIN_KEY = 'qa_train_records_v1'


def _atomic_write(path, text):
    tmp = path + '.tmp_write'
    io.open(tmp, 'w', encoding='utf-8', newline='').write(text)
    os.replace(tmp, path)


BLOCK = BEGIN + r'''
/* ===================== 控制台「我的」面板（2026-09-21） =====================
   N1 收藏列表 · L5 练习成绩趋势 · P1 字号三档
   纯本机数据：收藏读 qa_star_v1（批1-A 写入），练习读 qa_train_records_v1，零联网。 */
(function(){
  if (window.__QA_MYPANEL_20260921__) return;
  window.__QA_MYPANEL_20260921__ = true;

  var FS = [
    { k: 'std', px: '16px',   l: '标准' },
    { k: 'lg',  px: '17.5px', l: '大' },
    { k: 'xl',  px: '19px',   l: '特大' }
  ];
  var tab = 'star';
  /* 清空收藏用「两段式内联确认」而不是 window.confirm：
     安卓壳层 WebView 未实现 onJsConfirm，confirm 会静默返回 false（点了没反应）。 */
  var clearArm = false;

  function escH(s){
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function toast(t){
    try{
      if (window.QAAT && window.QAAT.toast) { window.QAAT.toast(t); return; }
      var d = document.getElementById('qa-at-toast');
      if (!d){ d = document.createElement('div'); d.id = 'qa-at-toast'; d.className = 'qa-at-toast'; document.body.appendChild(d); }
      d.textContent = t; d.classList.add('on');
      clearTimeout(d.__t); d.__t = setTimeout(function(){ d.classList.remove('on'); }, 1600);
    }catch(e){}
  }

  /* ---------------- 样式 ---------------- */
  function css(){
    if (document.getElementById('qa-mp-css')) return;
    var st = document.createElement('style');
    st.id = 'qa-mp-css';
    st.textContent = [
      '#qaMinePop{position:absolute;left:0;right:0;bottom:calc(100% + 10px);z-index:9;background:var(--bg-card,#fff);',
      'border:1px solid var(--border,#E5EDE9);border-radius:16px;padding:12px 14px 10px;box-shadow:0 12px 34px rgba(15,42,31,.18);display:none;max-height:min(62vh,520px);overflow:auto;}',
      '#qaMinePop.open{display:block;animation:qaMineIn .18s ease-out;}',
      '@keyframes qaMineIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}',
      '#qaMinePop .mp-h{display:flex;align-items:center;gap:6px;padding-right:26px;margin-bottom:10px;}',
      '#qaMinePop .mp-tab{border:1px solid var(--border,#E5EDE9);background:transparent;color:var(--text2,#5A6F65);',
      'border-radius:999px;padding:5px 12px;font-size:.75rem;font-weight:800;cursor:pointer;font-family:inherit;min-height:30px;}',
      '#qaMinePop .mp-tab.on{background:var(--primary,#148453);color:#fff;border-color:var(--primary,#148453);}',
      '#qaMinePop .mp-x{position:absolute;top:9px;right:9px;border:none;background:transparent;color:var(--text3,#B5C2BC);',
      'font-size:14px;line-height:1;cursor:pointer;padding:6px;width:32px;height:32px;}',
      '#qaMinePop .mp-empty{font-size:.78rem;color:var(--text2,#5A6F65);line-height:1.7;padding:6px 2px 8px;}',
      '#qaMinePop .mp-row{display:flex;align-items:stretch;gap:6px;border-bottom:1px dashed var(--border,#E5EDE9);padding:6px 0;}',
      '#qaMinePop .mp-row:last-child{border-bottom:none;}',
      '#qaMinePop .mp-t2{flex:1;text-align:left;border:none;background:transparent;color:var(--text,#0F2A1F);',
      'font:inherit;font-size:.79rem;font-weight:700;cursor:pointer;padding:4px 2px;line-height:1.5;}',
      '#qaMinePop .mp-t2 small{display:block;font-weight:600;font-size:.68rem;color:var(--text3,#8C9C94);margin-top:2px;}',
      '#qaMinePop .mp-x2{border:1px solid var(--border,#E5EDE9);background:transparent;color:var(--text2,#5A6F65);',
      'border-radius:8px;padding:2px 8px;font-size:.72rem;cursor:pointer;font-family:inherit;align-self:center;}',
      '#qaMinePop .mp-foot{display:flex;justify-content:flex-end;margin-top:8px;}',
      '#qaMinePop .mp-clear{border:none;background:transparent;color:#C62828;font-size:.72rem;font-weight:700;cursor:pointer;font-family:inherit;padding:4px;}',
      '#qaMinePop .mp-stat{display:flex;gap:14px;flex-wrap:wrap;font-size:.75rem;color:var(--text2,#5A6F65);margin:2px 0 8px;}',
      '#qaMinePop .mp-stat b{color:var(--primary-dark,#0F7B3F);font-size:.95rem;}',
      '#qaMinePop .mp-spark{display:block;width:100%;height:56px;margin:2px 0 8px;}',
      '#qaMinePop .mp-rows{display:flex;flex-direction:column;}',
      '#qaMinePop .mp-tr{display:flex;align-items:center;gap:10px;font-size:.74rem;color:var(--text2,#5A6F65);',
      'padding:5px 0;border-bottom:1px dashed var(--border,#E5EDE9);}',
      '#qaMinePop .mp-tr:last-child{border-bottom:none;}',
      '#qaMinePop .mp-tr b{color:var(--text,#0F2A1F);font-size:.82rem;width:56px;}',
      '#qaMinePop .mp-tr span{width:96px;color:var(--text3,#8C9C94);}',
      '#qaMinePop .mp-fsbar{display:flex;align-items:center;gap:6px;margin-top:10px;padding-top:9px;border-top:1px solid var(--border,#E5EDE9);font-size:.72rem;color:var(--text2,#5A6F65);font-weight:700;}',
      '#qaMinePop .mp-fs{border:1px solid var(--border,#E5EDE9);background:var(--primary-mist,#F4F9F6);color:#2E6B4F;',
      'border-radius:999px;padding:5px 13px;font-size:.73rem;font-weight:700;cursor:pointer;font-family:inherit;min-height:30px;}',
      '#qaMinePop .mp-fs.on{background:var(--primary,#148453);color:#fff;border-color:var(--primary,#148453);}',
      '#pbMine.on{border-color:var(--primary,#148453);color:var(--primary,#148453);}',
      'html[data-theme="dark"] #qaMinePop{background:#162420;border-color:#1E3A2C;}',
      'html[data-theme="dark"] #qaMinePop .mp-t2{color:#DFEDE5;}',
      'html[data-theme="dark"] #qaMinePop .mp-fs{background:#1A3D2A;color:#8FD3B0;border-color:#1E3A2C;}',
      'html[data-theme="dark"] #qaMinePop .mp-tr b{color:#DFEDE5;}',
      '@media(max-width:420px){ #qaDeck #petBar .pb-c{font-size:.7rem;padding:5px 9px;} }'
    ].join('');
    (document.head || document.documentElement).appendChild(st);
  }

  /* ---------------- 字号三档（P1） ---------------- */
  function applyFs(k){
    var i = 0;
    for (var n = 0; n < FS.length; n++){ if (FS[n].k === k){ i = n; break; } }
    try{
      if (i === 0) document.documentElement.style.removeProperty('font-size');
      else document.documentElement.style.fontSize = FS[i].px;
    }catch(e){}
    try{ localStorage.setItem('qa_font_v1', FS[i].k); }catch(e){}
    Array.prototype.forEach.call(document.querySelectorAll('#qaMinePop .mp-fs'), function(b){
      b.classList.toggle('on', b.getAttribute('data-fs') === FS[i].k);
    });
  }
  function loadFs(){
    var k = 'std';
    try{ k = localStorage.getItem('qa_font_v1') || 'std'; }catch(e){}
    applyFs(k);
  }

  /* ---------------- 收藏（N1） ---------------- */
  function stars(){
    try{ if (window.QAAT && window.QAAT.listStars) return window.QAAT.listStars() || []; }catch(e){}
    return [];
  }
  function renderStar(){
    var a = stars();
    if (!a.length){
      return '<div class="mp-empty">\u2606 还没有收藏。<br>在任意回答下方点「\u2606 收藏」，这条问答就会收在这里，随时点回来重问。</div>';
    }
    var rows = a.map(function(x, i){ return { x: x, i: i }; }).reverse().slice(0, 40).map(function(o){
      var x = o.x, i = o.i;
      var sub = escH(x.pool || '') + (x.src ? ' · ' + escH(x.src) : '') + (x.ts ? ' · ' + escH(String(x.ts).slice(0, 10)) : '');
      return '<div class="mp-row">'
        + '<button class="mp-t2" type="button" data-ask="' + i + '">' + escH(x.t || x.q || '未命名') + '<small>' + sub + '</small></button>'
        + '<button class="mp-x2" type="button" data-del="' + i + '" title="取消收藏">\u2715</button>'
        + '</div>';
    }).join('');
    return rows
      + '<div class="mp-foot"><button class="mp-clear" type="button" data-clear="1">'
      + (clearArm ? '再点一次确认清空' : '清空收藏')
      + '</button></div>';
  }

  /* ---------------- 练习成绩趋势（L5） ---------------- */
  function recs(){
    try{ var a = JSON.parse(localStorage.getItem('qa_train_records_v1') || '[]'); return (a && a.length) ? a : []; }catch(e){ return []; }
  }
  function fmtTime(iso){
    var s = String(iso || '');
    return s.length >= 16 ? (s.slice(5, 10) + ' ' + s.slice(11, 16)) : s.slice(0, 10);
  }
  function spark(vals){
    var W = 260, H = 56, P = 5;
    var n = vals.length;
    var y0 = H - P - (H - P * 2) * 0.6;
    var pts = vals.map(function(v, i){
      var x = (n <= 1) ? W / 2 : P + (W - P * 2) * (i / (n - 1));
      var y = H - P - (H - P * 2) * (Math.max(0, Math.min(100, v)) / 100);
      return x.toFixed(1) + ',' + y.toFixed(1);
    }).join(' ');
    return '<svg class="mp-spark" viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" aria-hidden="true">'
      + '<line x1="' + P + '" y1="' + y0.toFixed(1) + '" x2="' + (W - P) + '" y2="' + y0.toFixed(1) + '" stroke="#C9D6CF" stroke-width="1" stroke-dasharray="4 4"/>'
      + '<polyline points="' + pts + '" fill="none" stroke="#00A650" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
      + '</svg>';
  }
  function renderTrain(){
    var a = recs();
    if (!a.length){
      return '<div class="mp-empty">\uD83D\uDCDD 还没有练习记录。<br>直接说一句「来 10 道第三章的题」，交卷批改后成绩就会记在这里（虚线为 60 分及格线）。</div>';
    }
    var avg = Math.round(a.reduce(function(s, r){ return s + (r.score || 0); }, 0) / a.length);
    var best = Math.max.apply(null, a.map(function(r){ return r.score || 0; }));
    var tail = a.slice(-20);
    var rows = a.slice().reverse().slice(0, 8).map(function(r){
      return '<div class="mp-tr"><span>' + escH(fmtTime(r.at)) + '</span><b>' + (r.score || 0) + ' 分</b><small>' + (r.correct || 0) + '/' + (r.total || 0) + ' 题</small></div>';
    }).join('');
    return '<div class="mp-stat"><span>共 <b>' + a.length + '</b> 次</span><span>平均 <b>' + avg + '</b> 分</span><span>最好 <b>' + best + '</b> 分</span></div>'
      + spark(tail.map(function(r){ return r.score || 0; }))
      + '<div class="mp-rows">' + rows + '</div>';
  }

  /* ---------------- 面板 ---------------- */
  function panel(){ return document.getElementById('qaMinePop'); }
  function deck(){ return document.getElementById('qaDeck'); }

  function render(){
    var p = panel();
    if (!p) return;
    var ns = stars().length, nt = recs().length;
    p.innerHTML = '<button class="mp-x" type="button" aria-label="收起">\u2715</button>'
      + '<div class="mp-h">'
      + '<button class="mp-tab' + (tab === 'star' ? ' on' : '') + '" type="button" data-tab="star">\u2605 收藏' + (ns ? ' ' + ns : '') + '</button>'
      + '<button class="mp-tab' + (tab === 'train' ? ' on' : '') + '" type="button" data-tab="train">\uD83D\uDCC8 练习' + (nt ? ' ' + nt : '') + '</button>'
      + '</div>'
      + '<div class="mp-body">' + (tab === 'star' ? renderStar() : renderTrain()) + '</div>'
      + '<div class="mp-fsbar">\uD83D\uDD24 字号'
      + FS.map(function(f){ return '<button class="mp-fs" type="button" data-fs="' + f.k + '">' + f.l + '</button>'; }).join('')
      + '</div>';
    p.querySelector('.mp-x').onclick = function(){ close(); };
    Array.prototype.forEach.call(p.querySelectorAll('.mp-tab'), function(b){
      b.onclick = function(){ tab = b.getAttribute('data-tab'); clearArm = false; render(); };
    });
    Array.prototype.forEach.call(p.querySelectorAll('.mp-fs'), function(b){
      b.onclick = function(){ applyFs(b.getAttribute('data-fs')); toast('字号已切换（本机记住）'); };
    });
    Array.prototype.forEach.call(p.querySelectorAll('.mp-t2'), function(b){
      b.onclick = function(){
        var i = parseInt(b.getAttribute('data-ask'), 10);
        var x = stars()[i];
        if (!x) return;
        if (!x.q){ toast('这条没有留下原始问法，请在聊天里翻到它'); return; }
        close();
        try{ ask(x.q); }catch(e){}
      };
    });
    Array.prototype.forEach.call(p.querySelectorAll('.mp-x2'), function(b){
      b.onclick = function(){
        var i = parseInt(b.getAttribute('data-del'), 10);
        try{ if (window.QAAT && window.QAAT.removeStar) window.QAAT.removeStar(i); }catch(e){}
        render(); toast('已取消收藏');
      };
    });
    var cl = p.querySelector('.mp-clear');
    if (cl) cl.onclick = function(){
      if (!clearArm){
        clearArm = true;
        render();
        var p2 = panel();
        if (p2){ var c2 = p2.querySelector('.mp-clear'); if (c2) c2.focus(); }
        setTimeout(function(){ if (clearArm){ clearArm = false; try{ render(); }catch(e){} } }, 5000);
        return;
      }
      clearArm = false;
      try{ if (window.QAAT && window.QAAT.clearStars) window.QAAT.clearStars(); }catch(e){}
      render(); toast('收藏已清空');
    };
    applyFs((function(){ try{ return localStorage.getItem('qa_font_v1') || 'std'; }catch(e){ return 'std'; } })());
  }

  function ensureBtn(){
    var d = deck(); if (!d) return null;
    var bar = d.querySelector('#petBar'); if (!bar) return null;
    var b = document.getElementById('pbMine');
    if (!b){
      b = document.createElement('button');
      b.type = 'button'; b.className = 'pb-c'; b.id = 'pbMine';
      b.textContent = '\uD83D\uDC64 我的';
      b.title = '我的收藏 / 练习成绩 / 字号';
      b.setAttribute('aria-expanded', 'false');
      var ref = document.getElementById('pbQuick') || document.getElementById('pbSet');
      if (ref && ref.parentNode === bar) bar.insertBefore(b, ref);
      else bar.appendChild(b);
    }
    if (!b.__wired){
      b.__wired = true;
      b.onclick = function(){
        var p = panel();
        if (p && p.classList.contains('open')) close(); else open();
      };
    }
    return b;
  }

  function syncBtn(){
    var b = document.getElementById('pbMine'), p = panel();
    if (b && p) b.classList.toggle('on', p.classList.contains('open'));
  }

  function build(){
    try{
      css();
      if (!ensureBtn()) return null;
      var p = panel();
      if (p) return p;
      var d = deck(); if (!d) return null;
      p = document.createElement('div');
      p.id = 'qaMinePop';
      p.setAttribute('role', 'dialog');
      p.setAttribute('aria-label', '我的');
      d.appendChild(p);
      render();
      return p;
    }catch(e){ return null; }
  }

  function open(){
    var p = build(); if (!p) return;
    try{ var q = document.getElementById('qaQuickPop'); if (q) q.classList.remove('open'); }catch(e){}
    render();
    p.classList.add('open');
    syncBtn();
  }
  function close(){
    var p = panel();
    if (p) p.classList.remove('open');
    syncBtn();
  }

  /* 点面板外收起 */
  function watchOutside(){
    try{
      document.addEventListener('pointerdown', function(ev){
        var p = panel();
        if (!p || !p.classList.contains('open')) return;
        if (p.contains(ev.target)) return;
        var b = document.getElementById('pbMine');
        if (b && b.contains(ev.target)) return;
        close();
      }, true);
    }catch(e){}
  }

  var __booted = { out: false };
  function boot(){
    build();
    if (!__booted.out){ __booted.out = true; watchOutside(); }
  }
  loadFs();
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
  setTimeout(boot, 900);
  setTimeout(function(){ if (!panel()) build(); }, 2200);
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
        if ANCHOR not in s:
            print('[ERR] 依赖未就位：找不到批1-A 的锚点 %s（先跑 _apply_qa_answer_tools_20260921.py）' % ANCHOR)
            return 1
        if s.count(ANCHOR) != 1:
            print('[ERR] 锚点 %s 出现 %d 次（应为 1）' % (ANCHOR, s.count(ANCHOR)))
            return 1
        if not os.path.exists(BAK):
            shutil.copy2(QA, BAK)
            print('[bak] -> %s' % os.path.basename(BAK))
        s = s.replace(ANCHOR, ANCHOR + '\n' + BLOCK, 1)
        print('[+] 已插入「我的」面板块（%d 字符）' % len(BLOCK))

    checks = {
        '块恰好 1 份': s.count(BEGIN) == 1 and s.count(END) == 1,
        '依赖块仍在': s.count(ANCHOR) == 1 and DEP in s,
        '运行时守卫': GUARD in s,
        '控制台键': "b.id = 'pbMine'" in s,
        '面板挂 deck': "d.appendChild(p);" in s,
        '两个页签': 'data-tab="star"' in s and 'data-tab="train"' in s,
        '读音练习记录键': TRAIN_KEY in s,
        '趋势图': 'polyline' in s and 'mp-spark' in s,
        '字号三档': "'17.5px'" in s and "'19px'" in s and "qa_font_v1" in s,
        '外点关闭': 'watchOutside' in s,
        '不用原生 confirm': re.search(r'window\.confirm\s*\(', s) is None,
        '两段式清空': '再点一次确认清空' in s,
        '块内无 \\U 长转义': '\\U0001F' not in BLOCK,
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
    print('[ok] 「我的」面板已就位（+%d 字符）' % (len(s) - n_before))
    return 0


if __name__ == '__main__':
    if '--check' in sys.argv:
        s = io.open(QA, 'r', encoding='utf-8', newline='').read()
        ok = BEGIN in s and GUARD in s and s.count(BEGIN) == 1
        print('[check] 我的面板：%s' % ('OK' if ok else 'FAIL'))
        raise SystemExit(0 if ok else 1)
    raise SystemExit(main())
