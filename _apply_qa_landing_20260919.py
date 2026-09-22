# -*- coding: utf-8 -*-
"""
「你问我答」跳转落地页注入器 v1 —— 幂等（strip -> replay）
=================================================================
补完 A4 的**接收侧**。此前只有 qa 单边「发出」（写 spring_jump_ctx + 拼 URL），
目标板块不读，用户跳过去还要重问一遍 —— 功能是半截的。

注入到 qa 可跳转的 9 个板块（含 2 个模板，保证重建后仍在）：
  quiz / performance / beauty / manual / daily / risk-lite / medical / report / kb-admin
落地页行为：
  1. 读 URL `?from=qa&q=xxx`（独立打开场景，优先级高）或 localStorage `spring_jump_ctx`
     （壳层内嵌场景；localStorage 在本项目 file:// 下跨板块共享已实证）
  2. TTL 5 分钟；读 localStorage 后**消费即清**，避免下次手动打开还弹旧提示
  3. 顶部浮动条显示「从『你问我答』带来：<问题>」，
     提供「填入搜索框」（自动找本页第一个可见可编辑输入框并触发 input/change）与「关闭」
  4. 找不到搜索框时给出明确提示，不静默失败

⚠️ 目标板块是活的产品文件，本注入只新增一个独立块（style+div+script 包在同一标记对里），
   不触碰任何既有标记块与业务代码；strip 只按自己的标记对删。
用法：python _apply_qa_landing_20260919.py [--check]
"""
import io
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
BAK = os.path.join(HERE, '_bak_qa_landing_20260919')

BEGIN = '<!-- QALANDING_BEGIN -->'
END = '<!-- QALANDING_END -->'

TARGETS = [
    u'quiz.html',
    u'performance.html',
    u'beauty.html',
    u'manual.html',
    u'daily.html',
    u'daily.template.html',
    u'risk-lite.html',
    u'medical.html',
    u'report.html',
    u'kb-admin.html',
    u'kb-admin.template.html',
]

CHECK = '--check' in sys.argv

BLOCK = u"""<style id="qa-landing-css">
#qaLanding{position:fixed;left:50%;transform:translateX(-50%);top:12px;z-index:600;
  display:flex;align-items:center;gap:9px;max-width:min(660px,92vw);
  padding:10px 12px;border-radius:12px;background:#FEF6DC;border:1px solid #F5B800;
  box-shadow:0 8px 24px rgba(15,42,31,.16);font-size:13px;line-height:1.5;color:#6B5200;}
#qaLanding[hidden]{display:none!important;}
#qaLanding .ql-ico{font-size:15px;flex-shrink:0;}
#qaLanding .ql-tx{min-width:0;}
#qaLanding .ql-tx b{font-weight:700;word-break:break-word;}
#qaLanding button{font-family:inherit;cursor:pointer;flex-shrink:0;min-height:36px;
  border-radius:9px;font-size:12px;font-weight:600;padding:0 11px;}
#qaLandingFill{border:none;background:#148453;color:#fff;}
#qaLandingFill:hover{background:#0C5F3A;}
#qaLandingX{margin-left:auto;border:1px solid #E0C97A;background:transparent;color:#6B5200;min-width:36px;padding:0;}
html[data-theme="dark"] #qaLanding{background:#2A2410;border-color:#6B5200;color:#F5D98A;}
html[data-theme="dark"] #qaLandingX{border-color:#6B5200;color:#F5D98A;}
@media (max-width:760px){
  #qaLanding{top:8px;font-size:12.5px;padding:9px 10px;gap:7px;}
  #qaLanding button{min-height:44px;font-size:12px;}
  #qaLandingX{min-width:44px;}
}
</style>
<div id="qaLanding" role="status" hidden>
  <span class="ql-ico" aria-hidden="true">&#8617;</span>
  <div class="ql-tx">从「你问我答」带来：<b id="qaLandingQ"></b></div>
  <button id="qaLandingFill" type="button">填入搜索框</button>
  <button id="qaLandingX" type="button" aria-label="关闭">&#10005;</button>
</div>
<script>
(function(){
  var KEY = 'spring_jump_ctx';
  var TTL = 5 * 60 * 1000;

  /* 自己是哪个模块 —— 用来认领"点名给我"的上下文。
     必须做这层过滤：storage 事件会广播给**所有**同源文档，壳层里多个 iframe 并存时
     不做归属判断就会「谁先醒谁把上下文消费掉」，真正的目标模块反而拿不到
     （2026-09-19 实战实测抓到的真缺陷）。 */
  var SELF = (function(){
    try{
      var p = String(location.pathname || '').split('/').pop().toLowerCase().replace(/\\.html?$/, '');
      var ALIAS = { 'kb-admin':'kbadmin', 'risk-lite':'risk', 'cc-home':'home' };
      return ALIAS[p] || p;
    }catch(e){ return ''; }
  })();
  function mine(o){
    if(!o || o.from !== 'qa' || !o.q) return false;
    if(!o.to) return true;                 /* 兼容旧数据与 URL 通道 */
    return String(o.to) === SELF;
  }

  function readUrl(){
    try{
      var sp = new URLSearchParams(location.search || '');
      var q = sp.get('q') || '', from = sp.get('from') || '';
      if(from === 'qa' && q) return { q:q, via:'url' };
    }catch(e){}
    return null;
  }
  function readStore(){
    try{
      var o = JSON.parse(localStorage.getItem(KEY) || 'null');
      if(mine(o) && (Date.now() - (o.t || 0)) < TTL) return { q:o.q, via:'store' };
    }catch(e){}
    return null;
  }
  function clearStore(){ try{ localStorage.removeItem(KEY); }catch(e){} }

  function findSearchBox(){
    var sels = ['input[type=search]', 'input[type=text]', 'input[type=searchbox]',
                'input:not([type])', 'textarea'];
    for(var i = 0; i < sels.length; i++){
      var list;
      try{ list = document.querySelectorAll(sels[i]); }catch(e){ continue; }
      for(var j = 0; j < list.length; j++){
        var el = list[j];
        if(el.disabled || el.readOnly) continue;
        if(el.id === 'qaLandingFill' || el.id === 'qaLandingX') continue;
        if(el.offsetParent === null) continue;
        var r = el.getBoundingClientRect();
        if(r.width < 40 || r.height < 16) continue;
        return el;
      }
    }
    return null;
  }

  /* ---- 带进来的问题也交给本页 AI ----
     通用做法：包装 fetch，凡是 chat/completions 请求就给 system 补一句来路上下文。
     刻意不依赖各板块 AI 客户端的实现差异（beauty 的 SpringAI / quiz 的 QuizSpringAI /
     kb-admin 的 aiChat 各写各的），这样新增板块时也不用再改一遍。 */
  function installAiBridge(q){
    try{
      if(window.__qaLandingAiBridge) return;
      var of = window.fetch;
      if(typeof of !== 'function') return;
      window.fetch = function(u, o){
        try{
          var url = String(u || '');
          if(/chat\\/completions/.test(url) && o && typeof o.body === 'string'){
            var body = JSON.parse(o.body);
            if(body && Array.isArray(body.messages) && body.messages.length){
              var note = '\\n\\n【来路】用户是从「你问我答」带着问题跳过来的，原问题：「' + q + '」。'
                + '若本次请求与该问题相关，请优先围绕它作答；无关则忽略这句。';
              var i0 = -1;
              for(var i = 0; i < body.messages.length; i++){
                if(body.messages[i] && body.messages[i].role === 'system'){ i0 = i; break; }
              }
              if(i0 >= 0){
                body.messages[i0] = { role:'system', content: String(body.messages[i0].content || '') + note };
              }else{
                body.messages.unshift({ role:'system', content: '【来路】' + note });
              }
              o = Object.assign({}, o, { body: JSON.stringify(body) });
              arguments[1] = o;
            }
          }
        }catch(e){}
        return of.apply(this, arguments);
      };
      window.__qaLandingAiBridge = true;
    }catch(e){}
  }

  /* 抽出来供两处复用：boot（首次加载）与 storage 事件（上下文后到） */
  function showBar(q){
    var box = document.getElementById('qaLanding');
    if(!box) return false;
    var qEl = document.getElementById('qaLandingQ');
    if(qEl) qEl.textContent = q.length > 42 ? (q.slice(0, 42) + '…') : q;
    box.dataset.q = q;
    box.hidden = false;
    bindButtons();
    return true;
  }

  function bindButtons(){
    var box = document.getElementById('qaLanding');
    if(!box) return;
    var fill = document.getElementById('qaLandingFill');
    if(fill && !fill.__qaBound){
      fill.__qaBound = true;
      var label = fill.textContent;
      fill.onclick = function(){
        var q = box.dataset.q || '';
        var el = findSearchBox();
        if(!el){
          fill.textContent = '没找到搜索框';
          setTimeout(function(){ fill.textContent = label; }, 1800);
          return;
        }
        try{
          el.focus();
          el.value = q;
          el.dispatchEvent(new Event('input', { bubbles:true }));
          el.dispatchEvent(new Event('change', { bubbles:true }));
          try{ el.scrollIntoView({ block:'center', behavior:'smooth' }); }catch(e2){}
          fill.textContent = '已填入';
          setTimeout(function(){ fill.textContent = label; }, 1600);
        }catch(e3){}
      };
    }
    var x = document.getElementById('qaLandingX');
    if(x && !x.__qaBound){ x.__qaBound = true; x.onclick = function(){ box.hidden = true; }; }
  }

  function boot(){
    var ctx = readUrl() || readStore();
    if(!ctx) return;
    if(!showBar(ctx.q)) return;
    if(ctx.via === 'store') clearStore();
    installAiBridge(ctx.q);
  }

  /* ★ 壳层内嵌的关键补丁（2026-09-19 实战实测抓到的真缺陷）：
     目标板块的 iframe 往往**早已加载**（壳层预热 / iframe 池化），DOMContentLoaded
     早就过去了，boot() 根本读不到"之后才写入"的上下文 —— 于是独立打开能用、
     壳层内「带着问题跳过去」却空转。storage 事件是天然的跨文档通知机制
     （同源的不同文档之间会触发），补上这条才真正闭合。 */
  window.addEventListener('storage', function(e){
    try{
      if(!e || e.key !== KEY || !e.newValue) return;
      var o = JSON.parse(e.newValue);
      if(!mine(o)) return;
      if(Date.now() - (o.t || 0) > TTL) return;
      if(showBar(o.q)) clearStore();
    }catch(err){}
  });

  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
  window.QaLanding = { boot:boot, find:findSearchBox, read:function(){ return readUrl() || readStore(); } };
})();
</script>
"""


def strip_block(s):
    return re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END) + r'\s*', '', s, flags=re.S)


def main():
    missing = []
    report = []
    for name in TARGETS:
        p = os.path.join(HERE, name)
        if not os.path.exists(p):
            missing.append(name)
    if missing:
        print(u'[warn] 以下目标不存在，跳过：%s' % u', '.join(missing))

    total_ok = 0
    for name in TARGETS:
        p = os.path.join(HERE, name)
        if not os.path.exists(p):
            continue
        src = io.open(p, 'r', encoding='utf-8', newline='').read()
        has = src.count(BEGIN)

        if CHECK:
            ok = (has == 1 and src.count(END) == 1)
            report.append((name, u'OK' if ok else u'NG', has))
            if ok:
                total_ok += 1
            continue

        if src.count(u'</body>') < 1:
            report.append((name, u'NG(无 </body>)', has))
            continue
        if not os.path.isdir(BAK):
            os.mkdir(BAK)
        bak = os.path.join(BAK, name)
        if not os.path.exists(bak):
            shutil.copy2(p, bak)

        s = strip_block(src)
        i = s.rfind(u'</body>')
        s = s[:i] + BEGIN + u'\n' + BLOCK + END + u'\n' + s[i:]

        raw_delta = src.count(u'<script') - src.count(u'</script>')
        new_delta = s.count(u'<script') - s.count(u'</script>')
        checks = {
            u'标记 1 份': s.count(BEGIN) == 1 and s.count(END) == 1,
            u'落地条 DOM': u'id="qaLanding"' in s,
            u'读 URL 参数': u"sp.get('from')" in s,
            u'读 localStorage': u'localStorage.getItem(KEY)' in s,
            u'消费即清': u'clearStore()' in s,
            u'搜索框定位': u'findSearchBox' in s,
            u'AI 上下文桥': u'__qaLandingAiBridge' in s,
            u'storage 事件补丁（壳层内嵌关键）': u"addEventListener('storage'" in s,
            u'目标模块认领（to 匹配）': u'function mine(o)' in s,
            # 不能用"计数绝对相等"：performance / risk-lite / kb-admin 内含 SheetJS 之类的
            # 内嵌 HTML 字符串，其中本来就带 <script 字样，计数天然不等（自检会假阳）。
            # 只要求「注入前后差值不变」—— 本块自身是一对完整标签，差值不应被改变。
            u'script 差值不变': new_delta == raw_delta,
        }
        fails = [k for k, v in checks.items() if not v]
        if fails:
            report.append((name, u'NG(' + u','.join(fails) + u')', has))
            continue
        s.encode('utf-8')
# __ATOMIC_WRITE_20260921__
        _tmp_w = (p) + ".tmp_write"
        with io.open(_tmp_w, "w", encoding="utf-8", newline="") as _f_w:
            _f_w.write(s)
        os.replace(_tmp_w, (p))
        delta = len(s) - len(src)
        report.append((name, u'INJ +%d' % delta, has))
        total_ok += 1

    print(u'===== 你问我答跳转落地页 =====')
    for name, st, has in report:
        print(u'  %-28s %-16s 旧块×%d' % (name, st, has))
    print(u'[done] %d 个文件%s' % (total_ok, u'（--check 校验通过）' if CHECK else u' 已注入'))
    if CHECK and total_ok != len([t for t in TARGETS if os.path.exists(os.path.join(HERE, t))]):
        print(u'!! 存在未注入/异常文件')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
