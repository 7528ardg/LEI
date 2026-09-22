# -*- coding: utf-8 -*-
"""
「你问我答」状态与反馈注入器 v1 —— 幂等（strip -> replay）
=================================================================
对应 2026-09-19 审计的 D2「加载与错误态」与 D4「形象状态联动」残余缺口：

  D2a 等待期标注 aria-busy（typing / clearTyping 包装，读屏器可知“正在忙”）
  D2b AI 失败不再只留一句「连不上」——给出三条明确出路：
        🔁 重试这个问题 / 🔄 换备用模型再试 / ⚙️ 打开 AI 设置，
        并把原始报错收进 <details>，不占版面也不丢信息。
  D4  AI 失败把形象切到 miss；跨板块带入问题时让形象说一句并进 think。

不做的事（有意取舍）：不引入骨架屏——qa 的等待几乎只在 AI 调用（秒级到数十秒），
三点动画 + aria-busy 已符合“加载反馈与预期时长匹配”的规范；骨架更适合内容占位型布局。

注入位置：紧跟会话记忆块的 JS_END（同一 <script> 内），链路 = ux -> memory -> bridge -> 原函数

⚠️ qa.html 是「源」：改完必须重建壳
⚠️ 首次运行备份 qa.html -> _bak_qa_ux_20260919.html
用法：python _apply_qa_ux_20260919.py [--check]
"""
import io
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
QA = os.path.join(HERE, 'qa.html')
BAK = os.path.join(HERE, '_bak_qa_ux_20260919.html')

JS_BEGIN = '/*__QA_UX_BEGIN__*/'
JS_END = '/*__QA_UX_END__*/'
ANCHOR = '/*__QA_MEM_END__*/'

CHECK = '--check' in sys.argv

JS = u"""
(function(){
  function flag(k, v){
    window.__qaUxFlags = window.__qaUxFlags || {};
    if(v === undefined) return !!window.__qaUxFlags[k];
    window.__qaUxFlags[k] = v;
  }
  function setBusy(on){
    try{ var sc = el('chatScroll'); if(sc) sc.setAttribute('aria-busy', on ? 'true' : 'false'); }catch(e){}
  }
  function petSay(t, st){
    try{
      if(window.PET && typeof PET.say === 'function') PET.say(t);
      if(window.PET && typeof PET.setState === 'function' && st) PET.setState(st, true);
    }catch(e){}
  }

  /* ---------- D2a 等待期 aria-busy ---------- */
  if(!flag('typing')){
    try{
      if(typeof window.typing === 'function'){
        var _typing = window.typing;
        window.typing = function(){ setBusy(true); return _typing.apply(this, arguments); };
      }
      if(typeof window.clearTyping === 'function'){
        var _clear = window.clearTyping;
        window.clearTyping = function(){ setBusy(false); return _clear.apply(this, arguments); };
      }
      flag('typing', true);
    }catch(e){}
  }

  /* ---------- D2b 未命中 / 本地模式的两条出路 ----------
     2026-09-19：外部 AI 与密钥已全部移除，原「AI 失败三条出路」改为本地模式口径
     （重试这个问题 / 查看模式说明）；换模型入口 qaUxSwitchModel 保留为空转兼容实现。 */
  function failCard(original){
    var q = '';
    try{ q = window.__qaLastQ || ''; }catch(e){}
    return '<div class="kbox gold">&#128218; 本地知识库模式：这个问题没有命中内置六库，问答与话术都在本机完成，不接外部 AI。你可以：</div>'
      + '<div style="display:flex;flex-wrap:wrap;gap:7px;margin:8px 0">'
      + (q ? '<button class="w-chip" onclick="qaUxRetry()">&#128257; 重试这个问题</button>' : '')
      + '<button class="w-chip" onclick="qaUxOpenAi()">&#8505;&#65039; 查看模式说明</button>'
      + '</div>'
      + '<details style="font-size:.75rem;color:var(--text2);margin-top:2px">'
      + '<summary style="cursor:pointer">查看原始报错</summary>'
      + '<div style="margin-top:4px;word-break:break-all">'
      + String(original == null ? '' : original).replace(/</g, '&lt;') + '</div></details>';
  }
  window.qaUxRetry = function(){
    var q = '';
    try{ q = window.__qaLastQ || ''; }catch(e){}
    if(q) try{ ask(q); }catch(e){}
  };
  window.qaUxSwitchModel = function(){
    var q = '';
    try{ q = window.__qaLastQ || ''; }catch(e){}
    try{
      var c = SpringAI.getCfg();
      c.model = 'glm-4-flash-250414';
      SpringAI.setCfg(c);
      if(typeof updateAiStatus === 'function') updateAiStatus();
    }catch(e){}
    if(q) try{ ask(q); }catch(e){}
  };
  window.qaUxOpenAi = function(){
    try{ openAiSettings(); }catch(e){}
  };

  if(!flag('addMsg')){
    try{
      if(typeof window.addMsg === 'function'){
        var _add = window.addMsg;
        window.addMsg = function(role, html, opts){
          if(role === 'bot' && typeof html === 'string' && html.indexOf('本地知识库模式：这个问题没有命中') >= 0){
            try{ arguments[1] = failCard(html); }catch(e){}
            petSay('本地模式：先翻翻内置六库，换个说法再问我。', 'miss');
          }
          return _add.apply(this, arguments);
        };
        flag('addMsg', true);
      }
    }catch(e){}
  }

  /* ---------- D4 跨板块带入时的形象联动 ---------- */
  if(!flag('bridgeApply')){
    try{
      if(window.QaBridge && typeof window.QaBridge.apply === 'function'){
        var _apply = window.QaBridge.apply;
        window.QaBridge.apply = function(){
          var r = _apply.apply(this, arguments);
          if(r) petSay('从别的板块带来的问题，我先看看。', 'think');
          return r;
        };
        flag('bridgeApply', true);
      }
    }catch(e){}
  }

  window.QaUx = { failCard: failCard, setBusy: setBusy, retry: window.qaUxRetry };
})();
"""


def strip_js(s):
    return re.sub(re.escape(JS_BEGIN) + r'.*?' + re.escape(JS_END) + r'\s*', '', s, flags=re.S)


def main():
    if not os.path.exists(QA):
        print('[ERR] 找不到 qa.html')
        return 1
    src = io.open(QA, 'r', encoding='utf-8', newline='').read()
    n0 = len(src)

    state = {'js': src.count(JS_BEGIN), 'anchor': src.count(ANCHOR)}
    print(u'[in] qa.html %d 字符' % n0)
    print(u'[state] ' + u'  '.join(u'%s=%d' % (k, v) for k, v in sorted(state.items())))

    if CHECK:
        ok = (state['js'] == 1 and state['anchor'] == 1)
        print(u'[check] 标记块与锚点：%s' % (u'OK' if ok else u'FAIL'))
        return 0 if ok else 1

    if state['anchor'] != 1:
        print(u'[ERR] 锚点出现 %d 次（期望 1），中止' % state['anchor'])
        return 1
    if not os.path.exists(BAK):
        shutil.copy2(QA, BAK)
        print(u'[bak] 已备份 -> %s' % os.path.basename(BAK))

    s = strip_js(src)
    print(u'[strip] 剥离旧块 %d 字符' % (n0 - len(s)))

    js_block = u'\n' + JS_BEGIN + JS + JS_END + u'\n'
    i = s.find(ANCHOR)
    if i < 0:
        print(u'[ERR] 锚点定位失败')
        return 1
    i_ins = i + len(ANCHOR)
    s = s[:i_ins] + js_block + s[i_ins:]

    checks = {
        u'JS 块 1 份': s.count(JS_BEGIN) == 1 and s.count(JS_END) == 1,
        u'排在 memory 之后': s.find(JS_BEGIN) > s.find(ANCHOR),
        u'aria-busy 标注': u"setAttribute('aria-busy'" in s,
        u'重试入口': u'qaUxRetry' in s,
        u'换模型入口': u'qaUxSwitchModel' in s,
        u'打开 AI 设置入口': u'qaUxOpenAi' in s,
        u'失败卡片': u'查看原始报错' in s,
        u'形象联动': u"petSay('本地模式：先翻翻内置六库" in s,
        u'幂等标志独立': u'__qaUxFlags' in s,
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
