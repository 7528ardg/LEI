# -*- coding: utf-8 -*-
"""你问我答 · 快捷提问「聊天框弹出面板」v2（2026-09-19 用户要求）
--------------------------------------------------------------------------------
v1（当天早些时候）：快捷提问 chip 行插在消息流顶部（#chatScroll 首子元素）。
用户实测后要求：顶部这块不要占消息流，改为**置于聊天框弹出**——
由底部一体式控制台（#qaDeck）弹出面板承载。

v2 行为：
  · 面板 #qaQuickPop 绝对定位于 #qaDeck 正上方（bottom:100%+10px），与控制台同宽；
  · 控制台形象行新增「💡 快问」键（#pbQuick，插在 🐾 形象 前）开合面板；
  · 空会话首次进入自动弹一次；点 ✕ 关闭并本机记住（qa_quick_hide_v1，键沿用 v1）；
  · 发出第一条问题后自动收起（MutationObserver 兼容内部 addMsg 调用链）；
  · 点击面板外区域自动收起；聊过天仍可随时手动打开。

幂等：v1 旧块（id=qaQuick 顶部条）存在则先 strip 再 replay v2；已是 v2 则跳过。
用法：python _apply_qa_quickstart_20260919.py [--check]
"""
import io
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')

def _atomic_write(path, text):
    """先写临时文件再原子替换：任何编码/写入异常都不会破坏源文件。"""
    tmp = path + u'.tmp_write'
    io.open(tmp, 'w', encoding='utf-8', newline='').write(text)
    os.replace(tmp, path)
ROOT = os.path.dirname(os.path.abspath(__file__))
QA = os.path.join(ROOT, u'qa.html')
BAK = os.path.join(ROOT, u'_bak_qa_quickstart_20260919.html')
BEGIN = u'/*__QA_QUICKSTART_BEGIN__*/'
END = u'/*__QA_QUICKSTART_END__*/'
ANCHOR = u'/*__QA_CAP_END__*/'
V2_MARK = u'qaQuickPop'

BLOCK = BEGIN + u'''
/* ===================== 快捷提问 · 聊天框弹出面板 v2（2026-09-19） =====================
   v1 是消息流顶部的 chip 行；用户要求改「置于聊天框弹出」：
   面板挂在底部控制台 #qaDeck 上方弹出，「💡 快问」键开合；
   空会话首进自动弹一次，✕ 记住不再弹（qa_quick_hide_v1），首问后自动收起。 */
(function(){
  var HIDE_KEY = 'qa_quick_hide_v1';
  var QUICK = [
    { ic:'📊', t:'查绩效',   q:'查一下张露2026年7月的绩效' },
    { ic:'📝', t:'在线练习', q:'来10道第三章的题' },
    { ic:'🧴', t:'产品话术', q:'雅诗兰黛小棕瓶' },
    { ic:'🏥', t:'病假流程', q:'病假怎么请？要交什么证件？' },
    { ic:'🔥', t:'辞退红线', q:'哪些行为会被辞退？' },
    { ic:'📍', t:'位置上报', q:'忘记上传位置会不会扣分？' },
    { ic:'🚨', t:'大撤流程', q:'大撤整体流程' },
    { ic:'\\u26C5',       t:'查天气',   q:'今天广州天气怎样' },
    { ic:'🏅', t:'晋级条件', q:'竞聘带班乘务长有什么要求？' },
    { ic:'🤖', t:'AI接口', act:'ai' }
  ];

  function css(){
    if(document.getElementById('qa-quick-css')) return;
    var st = document.createElement('style');
    st.id = 'qa-quick-css';
    st.textContent = ''
      + '#qaQuickPop{position:absolute;left:0;right:0;bottom:calc(100% + 10px);z-index:9;'
      + 'background:var(--bg-card,#fff);border:1px solid var(--border,#E5EDE9);border-radius:16px;'
      + 'padding:10px 12px;box-shadow:0 12px 34px rgba(15,42,31,.18);display:none;}'
      + '#qaQuickPop.open{display:block;animation:qaQuickPopIn .18s ease-out;}'
      + '@keyframes qaQuickPopIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}'
      + '#qaQuickPop .qq-t{font-size:.76rem;font-weight:700;color:var(--text2,#5A6F65);margin-bottom:8px;padding-right:24px;line-height:1.5;}'
      + '#qaQuickPop .qq-row{display:flex;flex-wrap:wrap;gap:6px;}'
      + '#qaQuickPop .qq-c{border:1px solid var(--border,#E5EDE9);background:var(--primary-mist,#F4F9F6);'
      + 'color:#2E6B4F;border-radius:999px;padding:6px 12px;font-size:.76rem;font-weight:700;cursor:pointer;'
      + 'font-family:inherit;min-height:36px;}'
      + '#qaQuickPop .qq-c:hover{border-color:var(--primary,#148453);color:var(--primary,#148453);}'
      + '#qaQuickPop .qq-ai{border-style:dashed;background:transparent;color:var(--text2,#5A6F65);}'
      + '#qaQuickPop .qq-ai:hover{border-color:var(--primary,#148453);color:var(--primary,#148453);background:var(--primary-mist,#F4F9F6);}'
      + 'html[data-theme="dark"] #qaQuickPop .qq-ai{background:transparent;color:#8FD3B0;}'
      + '#qaQuickPop .qq-x{position:absolute;top:8px;right:8px;border:none;background:transparent;color:var(--text3,#B5C2BC);'
      + 'font-size:14px;line-height:1;cursor:pointer;padding:6px;width:32px;height:32px;}'
      + 'html[data-theme="dark"] #qaQuickPop{background:#162420;border-color:#1E3A2C;}'
      + 'html[data-theme="dark"] #qaQuickPop .qq-c{background:#1A3D2A;color:#8FD3B0;border-color:#1E3A2C;}'
      + '#pbQuick.on{border-color:var(--primary,#148453);color:var(--primary,#148453);}';
    (document.head || document.documentElement).appendChild(st);
  }

  function deck(){ return document.getElementById('qaDeck'); }
  function panel(){ return document.getElementById('qaQuickPop'); }

  /* 控制台上的开合键：插在「🐾 形象」前，样式复用 .pb-c */
  function ensureBtn(){
    var d = deck(); if(!d) return null;
    var bar = d.querySelector('#petBar'); if(!bar) return null;
    var b = document.getElementById('pbQuick');
    if(!b){
      b = document.createElement('button');
      b.type = 'button'; b.className = 'pb-c'; b.id = 'pbQuick';
      b.textContent = '💡 快问';
      b.setAttribute('aria-expanded','false');
      var ref = document.getElementById('pbSet');
      if(ref && ref.parentNode === bar) bar.insertBefore(b, ref);
      else bar.appendChild(b);
    }
    if(!b.__wired){
      b.__wired = true;
      b.onclick = function(){
        var p = panel();
        if(p && p.classList.contains('open')) close(false); else open();
      };
    }
    return b;
  }

  function syncBtn(){
    var b = document.getElementById('pbQuick'), p = panel();
    if(b && p) b.classList.toggle('on', p.classList.contains('open'));
  }

  function build(){
    try{
      css();
      if(!ensureBtn()) return null;
      var p = panel();
      if(p) return p;
      var d = deck(); if(!d) return null;
      p = document.createElement('div');
      p.id = 'qaQuickPop';
      p.setAttribute('role','dialog');
      p.setAttribute('aria-label','快捷提问');
      p.innerHTML = '<button class="qq-x" type="button" aria-label="不再显示">\\u2715</button>'
        + '<div class="qq-t">💡 想快点上手？点一个试试，也可以直接说产品名（如「雅诗兰黛小棕瓶」）出话术。</div>'
        + '<div class="qq-row">' + QUICK.map(function(c){
            return '<button class="qq-c' + (c.act ? ' qq-ai' : '') + '" type="button"'
                 + (c.act ? ' data-act="' + c.act + '"' : ' data-q="' + String(c.q).replace(/"/g,'&quot;') + '"')
                 + '>' + c.ic + ' ' + c.t + '</button>';
          }).join('') + '</div>';
      d.appendChild(p);
      p.querySelector('.qq-x').onclick = function(){ close(true); };
      Array.prototype.forEach.call(p.querySelectorAll('.qq-c'), function(b){
        b.onclick = function(){
          if(b.getAttribute('data-act') === 'ai'){
            close(false);
            try{
              if(typeof SpringAI !== 'undefined' && SpringAI.openSettings) SpringAI.openSettings();
              else if(typeof openAiSettings === 'function') openAiSettings();
            }catch(e){}
            return;
          }
          var q = b.getAttribute('data-q') || ''; if(!q) return;
          close(false);
          try{ ask(q); }catch(e){}
        };
      });
      return p;
    }catch(e){ return null; }
  }

  function open(){ var p = build(); if(!p) return; p.classList.add('open'); syncBtn(); }
  function close(remember){
    var p = panel();
    if(p) p.classList.remove('open');
    syncBtn();
    if(remember){ try{ localStorage.setItem(HIDE_KEY, '1'); }catch(e){} }
  }

  /* 空会话首进自动弹一次；点过 ✕ 的不再弹 */
  function autoOpen(){
    if(document.querySelector('#chatWrap .msg.user')) return;
    try{ if(localStorage.getItem(HIDE_KEY) === '1') return; }catch(e){}
    open();
  }

  /* 发出第一条问题后自动收起（监听渲染出的 user 气泡，兼容内部直接 addMsg 的调用链） */
  function watch(){
    try{
      var wrap = document.getElementById('chatWrap');
      if(!wrap || !window.MutationObserver) return;
      new MutationObserver(function(){
        if(document.querySelector('#chatWrap .msg.user')){
          var p = panel();
          if(p && p.classList.contains('open')) close(false);
        }
      }).observe(wrap, { childList:true, subtree:true });
    }catch(e){}
  }

  /* 点面板外自动收起（面板内、开合键上不收） */
  function watchOutside(){
    try{
      document.addEventListener('pointerdown', function(ev){
        var p = panel();
        if(!p || !p.classList.contains('open')) return;
        if(p.contains(ev.target)) return;
        var b = document.getElementById('pbQuick');
        if(b && b.contains(ev.target)) return;
        close(false);
      }, true);
    }catch(e){}
  }

  /* boot 会因 DOMContentLoaded + 900ms 兜底最多跑 3 次：
     build/ensureBtn 自带幂等守卫，可重复；watch/watchOutside/autoOpen 只执行一次，
     避免监听器翻倍与「外点关闭后被兜底 boot 重新弹开」 */
  var __booted = { watch:false, out:false, auto:false };
  function boot(){
    build();
    if(!__booted.watch){ __booted.watch = true; watch(); }
    if(!__booted.out){ __booted.out = true; watchOutside(); }
    if(!__booted.auto){ __booted.auto = true; autoOpen(); }
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
  setTimeout(boot, 900);
  setTimeout(function(){ if(!panel()) build(); }, 2200);
})();
''' + END


def strip_block(s):
    return re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END) + r'\s*', '', s, flags=re.S)


def main():
    if not os.path.exists(QA):
        print(u'[ERR] 找不到 qa.html')
        return 1
    s = io.open(QA, 'r', encoding='utf-8', newline='').read()
    if BEGIN in s:
        seg = s.split(BEGIN, 1)[1].split(END, 1)[0]
        if V2_MARK in seg:
            print(u'[skip] 快问面板已是 v2（幂等）')
            return 0
        print(u'[up] 检测到 v1 顶部快问行 → strip 后 replay v2 弹出面板')
        if not os.path.exists(BAK):
            shutil.copy2(QA, BAK)
            print(u'[bak] -> %s' % os.path.basename(BAK))
        s = strip_block(s)
        s = s.replace(ANCHOR, ANCHOR + u'\n' + BLOCK, 1)
    else:
        if s.count(ANCHOR) != 1:
            print(u'[ERR] 锚点 %s 出现 %d 次' % (ANCHOR, s.count(ANCHOR)))
            return 1
        if not os.path.exists(BAK):
            shutil.copy2(QA, BAK)
            print(u'[bak] -> %s' % os.path.basename(BAK))
        s = s.replace(ANCHOR, ANCHOR + u'\n' + BLOCK, 1)

    checks = {
        u'块恰好 1 份': s.count(BEGIN) == 1 and s.count(END) == 1,
        u'v2 面板标记': s.count(V2_MARK) >= 5,
        u'旧版顶部条已消失': u"id = 'qaQuick'" not in s and u"getElementById('qaQuick')" not in s,
        u'开合键': u"b.id = 'pbQuick'" in s and u"getElementById('pbQuick')" in s,
        u'面板挂 deck': u"d.appendChild(p);" in s,
        u'自动收起': u"document.querySelector('#chatWrap .msg.user')" in s,
        u'9 个快捷问法': s.count(u'{ ic:') >= 9,
        u'挂载锚点唯一': s.count(ANCHOR) == 1,
        u'script 标签平衡': s.count(u'<script') == s.count(u'</script>'),
    }
    fails = [k for k, v in checks.items() if not v]
    for k, v in checks.items():
        print(u'  [%s] %s' % (u'OK' if v else u'NG', k))
    if fails:
        print(u'!! 自检失败，未写盘')
        return 1
    _atomic_write(QA, s)
    print(u'[ok] 快问弹出面板 v2 已就位（%d 字符）' % len(BLOCK))
    return 0


if __name__ == '__main__':
    if '--check' in sys.argv:
        s = io.open(QA, 'r', encoding='utf-8', newline='').read()
        ok = False
        if BEGIN in s:
            seg = s.split(BEGIN, 1)[1].split(END, 1)[0]
            ok = V2_MARK in seg and u"getElementById('pbQuick')" in s
        print(u'[check] 快问弹出面板 v2：%s' % (u'OK' if ok else u'FAIL'))
        raise SystemExit(0 if ok else 1)
    raise SystemExit(main())
