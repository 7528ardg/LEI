# -*- coding: utf-8 -*-
"""你问我答 · AI 赋魂批 α（2026-09-21）
--------------------------------------------------------------------------------
提案编号：A3 问法改写 / A4 指代消解 / A5 未明示需求 / A6 强制溯源

设计要点（为什么这样接）：
  · 现状是「本地检索全失败 → 才轮到 AI」（qa.html:8442），AI 注定是备胎。本批把 AI 提到
    **主链路调度位**：本地弱命中时先用 AI 改写问法再检索一次，命中就走库内直答（可信、可溯源）。
  · A6 强制溯源**不额外消耗 AI 调用**——用库内上下文（kbCtx）做本地事实核对：
    把回答里「查不到库内依据的数值/章节号」标出来，并明确告知本条回答有无库内支撑。
    理由：AI 生成能力放开之后，最大的风险不是答不出，而是「看起来很专业但查不到依据」。
  · A5 的推荐芯片取自 kbCtx（库内真实条目），而不是让 AI 自由编问法——芯片点进去必然有答案。
  · 三处 in-place 改动都带唯一标记，重跑时按标记跳过；块本体走 strip→replay。
  · 内置 Key 只预留注入位（window.__QA_BUILTIN_AI__），源码不含任何密钥，构建链守护不受影响。

幂等：块由 /*__QA_AI_BRAIN_20260921__*/ 守卫；window.__QA_AI_BRAIN_20260921__ 运行时去重。
用法：python _apply_qa_ai_brain_20260921.py [--check]
"""
import io
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.abspath(__file__))
QA = os.path.join(ROOT, 'qa.html')
BAK = os.path.join(ROOT, '_bak_qa_ai_brain_20260921.html')
BEGIN = '/*__QA_AI_BRAIN_20260921_BEGIN__*/'
END = '/*__QA_AI_BRAIN_20260921_END__*/'
GUARD = '__QA_AI_BRAIN_20260921__'
ANCHOR = '/*__QA_QUICKSTART_END__*/'


def _atomic_write(path, text):
    tmp = path + '.tmp_write'
    io.open(tmp, 'w', encoding='utf-8', newline='').write(text)
    os.replace(tmp, path)


BLOCK = BEGIN + r'''
/* ===================== 你问我答 · AI 赋魂（2026-09-21 批 α） =====================
   A3 问法改写 · A4 指代消解 · A5 未明示需求 · A6 强制溯源
   口径：AI 可用时增强，AI 不可用 / 断网时全量回落原链路，不改变任何既有行为。
   源码不含任何密钥；内置 Key 仅预留注入位 window.__QA_BUILTIN_AI__。 */
(function(){
  if (window.__QA_AI_BRAIN_20260921__) return;
  window.__QA_AI_BRAIN_20260921__ = true;

  var lastQ = '';
  var rwAt = 0;

  /* ---------------- 样式（浅色 + 深色双主题） ---------------- */
  function css(){
    if (document.getElementById('qa-gr-css')) return;
    var st = document.createElement('style');
    st.id = 'qa-gr-css';
    st.textContent = [
      '.qa-gr-wrap{display:block;}',
      /* 用 block + 单文本容器，不用 flex：flex 会把文本节点与 <b> 当成各自独立的 flex item，
         结果是正文被切成多栏（实测截图复现）。 */
      '.qa-gr-bar{display:block;margin:0 0 9px;padding:7px 10px;border-radius:9px;',
      'font-size:.72rem;line-height:1.55;font-weight:600;overflow-wrap:anywhere;}',
      '.qa-gr-bar .qa-gr-ico{margin-right:4px;}',
      '.qa-gr-ok{background:#E8F5EC;color:#0F7B3F;border:1px solid #B9E3CB;}',
      '.qa-gr-warn{background:#FFF6E5;color:#946200;border:1px solid #F0DCB0;}',
      '.qa-gr-miss{background:#F1F3F2;color:#5A6F65;border:1px solid #DDE5E1;}',
      '.qa-gr-unv{text-decoration:underline;text-decoration-style:wavy;text-underline-offset:3px;',
      'text-decoration-color:var(--gold,#D98324);}',
      '.qa-gr-chips{margin-top:11px;padding-top:10px;border-top:1px dashed var(--border,#E5EDE9);}',
      '.qa-gr-chips .qa-gr-t{font-size:.72rem;font-weight:800;color:var(--primary-dark,#0F7B3F);margin-bottom:6px;}',
      /* 长问法芯片必须能换行，否则会顶破气泡宽度（kbCtx 里的条目 q 最长可达数十字） */
      '.qa-gr-chips .w-chip{max-width:100%;overflow-wrap:anywhere;text-align:left;line-height:1.45;}',
      /* 答案卡工具键在粗指针设备上补齐 44px（原 30px 低于本项目自身移动端标准） */
      '@media (pointer:coarse){.qa-at-b{min-height:44px;padding:9px 13px;}}',
      'html[data-theme="dark"] .qa-gr-ok{background:#123524;color:#8FD3B0;border-color:#1E4A31;}',
      'html[data-theme="dark"] .qa-gr-warn{background:#3A2E12;color:#E8C77A;border-color:#5A4620;}',
      'html[data-theme="dark"] .qa-gr-miss{background:#1B2622;color:#9FB3AA;border-color:#2A3B34;}',
      'html[data-theme="dark"] .qa-gr-unv{text-decoration-color:var(--gold,#E8C77A);}',
      'html[data-theme="dark"] .qa-gr-chips .qa-gr-t{color:#8FD3B0;}'
    ].join('');
    (document.head || document.documentElement).appendChild(st);
  }

  function escH(s){
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function plain(s){
    return String(s == null ? '' : s).replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ')
      .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"').replace(/&#39;/g, "'");
  }
  function squeeze(s){ return String(s || '').replace(/[\s\u3000]/g, '').toLowerCase(); }

  /* ==================== A4 · 指代消解 ====================
     把「那这个呢 / 还有呢 / 多久内 / 为什么」这类承接式追问还原成完整问句。
     保守判据：长度 ≤ 10 且（裸疑问词 或 含指代/承接词）。「这是什么设备」这类
     以「这」开头的完整新问题不会被误判（不含 那这个/那个/它/还有/再/呢）。 */
  var RX_DEIXIS = /(呢|那这个|那个|它们?|还有|再(说|讲|问|查)?|接着|然后|具体|详细|展开|继续|上面|刚才)/;
  var RX_BARE = /^(多久|多长时间|几天|几年|几个月|多少|几个|怎么办|怎么处理|什么标准|啥要求|注意什么|有影响吗|为什么|为啥|凭什么)/;

  function isFollowUp(t){
    if (!t || t.length > 10) return false;
    if (RX_BARE.test(t)) return true;
    return RX_DEIXIS.test(t);
  }

  function resolveFollowUp(text){
    try{
      var t = String(text == null ? '' : text).trim();
      if (!t) return text;
      if (t.charAt(0) === '/') { lastQ = t; return text; }        // 命令不参与承接
      if (!lastQ || lastQ.length < 2 || !isFollowUp(t)) { lastQ = t; return text; }
      var merged = lastQ + ' ' + t;
      if (merged.length > 64) merged = lastQ.slice(0, 44) + ' ' + t;
      toast('↩︎ 已承接上文理解');
      return merged;
    }catch(e){ return text; }
  }

  /* ==================== A3 · 问法改写 ====================
     本地检索弱命中时，用 AI 把口语问法改写成库内可能的检索式，再检索一次。
     命中即走库内直答（可信、可溯源）；未命中则原样回落原链路（候选追问 / AI 兜底）。 */
  var RW_SYS = '你是民航客舱乘务知识库的检索助手。用户会给你一个口语化提问，'
    + '请改写成最多 2 条更可能命中《客舱乘务员手册》《管理手册》《客舱服务规范》知识库的检索式，'
    + '使用乘务员与民航手册里的标准说法，保留关键实体与动作。'
    + '只输出检索式，一行一条，不要编号、不要引号、不要任何解释说明；每条不超过 14 个字；'
    + '如果原问题本身已经接近标准条文表述，就原样输出它。';

  /* 重要：SpringAI 在 qa.html 里是**顶层 const**——顶层 const 不会挂到 window 上，
     所以 window.SpringAI 恒为 undefined。必须用 bare 引用 + typeof 兜底（实测踩过这个坑：
     写成 window.SpringAI 会导致 A3 永不触发且静默无声）。 */
  function ai(){
    try{ return (typeof SpringAI !== 'undefined' && SpringAI) ? SpringAI : null; }catch(e){ return null; }
  }
  function toast(t){
    try{
      var T = (typeof QAAT !== 'undefined' && QAAT) ? QAAT : window.QAAT;
      if (T && typeof T.toast === 'function'){ T.toast(t); return true; }
    }catch(e){}
    return false;
  }

  async function rewriteAndSearch(text){
    try{
      var A = ai();
      if (!A || typeof A.isEnabled !== 'function' || !A.isEnabled()) return null;
      if (typeof kbSearch !== 'function' || typeof kbStrong !== 'function' || typeof currentKbPool !== 'function') return null;
      if (Date.now() - rwAt < 4000) return null;                  // 防抖：连续弱命中只改写一次
      rwAt = Date.now();
      var resp = '';
      try{
        resp = await A.chatLLM(
          [{ role:'system', content: RW_SYS }, { role:'user', content: String(text) }],
          { temperature:0.2, maxTokens:70, noHistory:true, noCrossData:true }
        );
      }catch(e){ return null; }
      var raw = String(text || '').trim();
      var lines = String(resp || '').split(/\n+/).map(function(s){
        return s.replace(/^[\s\-•·*]*\d{0,2}[.、)）]?\s*/, '').replace(/[《》「」"“”'']/g, '').trim();
      }).filter(function(s){ return s.length >= 2 && s.length <= 24 && s !== raw; }).slice(0, 2);
      if (!lines.length) return null;
      var pool = currentKbPool();
      if (!pool || !pool.length) return null;
      var best = null;
      for (var i = 0; i < lines.length; i++){
        var h = kbSearch(lines[i], 3, pool);
        if (h && h.length && (!best || h[0].s > best.hits[0].s)) best = { hits: h, q: lines[i] };
      }
      return best;
    }catch(e){ return null; }
  }

  /* ==================== A6 · 强制溯源 ====================
     事实 token：章节号（3.1 / 6.7.9.3.4 / CCM 4.4）+ 带单位数值（4 小时 / 100 分 / 30%）。
     与库内上下文（kbCtx）比对，查不到依据的 token 打波浪线 + 悬浮说明。
     只在「非标签」文本段做替换，避免动到 HTML 属性。 */
  var RX_SEC = /(?:CCM|CQH-CCM|手册)?\s?\d+(?:\.\d+){1,4}/g;
  var RX_NUM = /\d+(?:\.\d+)?\s*(?:小时|分钟|秒钟|秒|个|名|位|分|米|厘米|毫米|公斤|千克|克|毫升|升|度|次|天|日|周|月|年|倍|%|％)/g;

  function factsOf(kbCtx){
    var buf = [];
    (kbCtx || []).forEach(function(x){
      var k = x && x.k; if (!k) return;
      buf.push(plain(k.q) + ' ' + plain(k.a) + ' ' + plain(k.src || ''));
    });
    return buf.join(' \n ');
  }
  function inFacts(tok, factsSq, factsRaw){
    var n = squeeze(tok).replace(/^(ccm|cqh-ccm)/, '').replace(/^手册/, '');
    if (!n) return true;
    if (factsSq.indexOf(n) >= 0) return true;
    return factsRaw.indexOf(n) >= 0;
  }

  function auditAnswer(resp, kbCtx){
    var html;
    try{ html = (typeof mdToHtml === 'function') ? mdToHtml(resp) : '<p>' + escH(resp) + '</p>'; }
    catch(e){ html = '<p>' + escH(resp) + '</p>'; }
    var factsRaw = factsOf(kbCtx);
    var factsSq = squeeze(factsRaw);
    var hasFacts = factsSq.length > 0;
    var bad = 0;

    var parts = String(html).split(/(<[^>]*>)/);
    var badToks = [];
    if (hasFacts){
      var mark = function(m){
        if (inFacts(m, factsSq, factsRaw)) return m;
        bad++;
        if (badToks.length < 6 && badToks.indexOf(m) < 0) badToks.push(m);
        /* 只用波浪线做「不可信」的非颜色提示；章节号/数值加 translate=no 防自动翻译改写。
           原实现用 title 承载说明——触屏（本项目主战场）永远看不到 title，故改为写进下方文案。 */
        return '<span class="qa-gr-unv" translate="no">' + m + '</span>';
      };
      for (var i = 0; i < parts.length; i++){
        if (!parts[i] || parts[i].charAt(0) === '<') continue;
        parts[i] = parts[i].replace(RX_SEC, mark).replace(RX_NUM, mark);
      }
    }
    var body = parts.join('');

    var bar;
    if (!hasFacts){
      bar = '<div class="qa-gr-bar qa-gr-miss" role="status">'
          + '<span class="qa-gr-ico" aria-hidden="true">🔍</span>'
          + '<span class="qa-gr-c">这条回答<b>没有库内条目作为依据</b>（六库均未命中），内容来自 AI 通用知识。'
          + '涉及数值、时限、流程请务必核对手册原文或咨询值班经理。</span></div>';
    }else if (bad > 0){
      var list = badToks.map(escH).join('、') + (bad > badToks.length ? ' 等' : '');
      bar = '<div class="qa-gr-bar qa-gr-warn" role="status">'
          + '<span class="qa-gr-ico" aria-hidden="true">🔍</span>'
          + '<span class="qa-gr-c">本回答参考了库内 ' + (kbCtx || []).length + ' 条资料，其中 <b>' + bad
          + ' 处数值 / 章节号未能在库内找到对应</b>（' + list + '，已用波浪线标出），请核对手册原文。</span></div>';
    }else{
      bar = '<div class="qa-gr-bar qa-gr-ok" role="status">'
          + '<span class="qa-gr-ico" aria-hidden="true">✓</span>'
          + '<span class="qa-gr-c">本回答参考了库内 ' + (kbCtx || []).length + ' 条资料，'
          + '其中出现的数值与章节号均可在库内找到对应。</span></div>';
    }
    return '<div class="qa-gr-wrap">' + bar + body + chipsOf(resp, kbCtx) + '</div>';
  }

  /* ==================== A5 · 未明示需求（库内推荐） ====================
     AI 回答此前没有任何推荐出口（库内直答才有「你可能还想了解」）。
     这里从 kbCtx 里挑最多 3 条未被回答提及的条目，做成芯片——点进去必然有库内答案。 */
  function chipsOf(resp, kbCtx){
    try{
      var txt = plain(resp);
      var picked = [];
      (kbCtx || []).forEach(function(x){
        var k = x && x.k;
        if (!k || !k.q || picked.length >= 3) return;
        var qKey = String(k.q).slice(0, 8);
        var aKey = plain(k.a || '').slice(0, 12);
        if (qKey.length >= 4 && txt.indexOf(qKey) >= 0) return;   // 回答里已提过这个问题
        if (aKey.length >= 8 && txt.indexOf(aKey) >= 0) return;   // 这条就是回答的出处，不必再推荐
        if (picked.indexOf(k.q) >= 0) return;
        picked.push(k.q);
      });
      if (!picked.length) return '';
      return '<div class="qa-gr-chips"><div class="qa-gr-t"><span aria-hidden="true">🔗</span> 顺着这条，你也许还想问：</div>'
        + '<div style="display:flex;flex-wrap:wrap;gap:7px">'
        + picked.map(function(q){
            return '<button class="w-chip" onclick="ask(\'' + escH(q).replace(/&#39;/g, "\\'") + '\')">'
              + escH(q) + '</button>';
          }).join('')
        + '</div></div>';
    }catch(e){ return ''; }
  }

  /* ==================== 内置 Key 注入位（预留，源码不含密钥） ====================
     2026-09-21 用户决定放开「源码零内置密钥」。实现姿势取**构建时注入**：
     打包脚本可从环境变量读 Key 后写入 window.__QA_BUILTIN_AI__，源码里始终只有占位。
     当前为空串 → isEnabled() 仍只看用户自填 Key，行为与今天完全一致。 */
  (function(){
    try{
      if (!window.__QA_BUILTIN_AI__) window.__QA_BUILTIN_AI__ = '';
      var A = ai();
      if (!A || typeof A.getCfg !== 'function' || typeof A.setCfg !== 'function') return;
      var b = String(window.__QA_BUILTIN_AI__ || '');
      if (b.length < 10) return;
      var c = A.getCfg();
      if (!String(c.apiKey || '').trim()){ c.apiKey = b; c._builtin = 1; A.setCfg(c); }
    }catch(e){}
  })();

  window.QABRAIN = {
    resolveFollowUp: resolveFollowUp,
    rewriteAndSearch: rewriteAndSearch,
    auditAnswer: auditAnswer,
    version: '20260921a'
  };

  css();
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', css);
})();
''' + END


# ---------- 三处 in-place 改动：(标记, 原文, 新文) ----------
EDIT_FOLLOW = (
    'QABRAIN.resolveFollowUp(text)',
    u'''  // 【增强】待补要素承接（绩效/练习追问）优先处理
  if(qaPending && qaFillPending(text)) return;''',
    u'''  /* __QA_AI_BRAIN_20260921__ A4 指代消解：把「那这个呢 / 还有呢 / 多久内」这类承接式
     追问还原成完整问句，避免多轮对话在这里断链。纯本地词表判定，不额外消耗 AI 调用。 */
  try{ if (window.QABRAIN) text = QABRAIN.resolveFollowUp(text); }catch(e){}
  // 【增强】待补要素承接（绩效/练习追问）优先处理
  if(qaPending && qaFillPending(text)) return;'''
)

EDIT_REWRITE = (
    'QABRAIN.rewriteAndSearch(text)',
    u'''  // 【候选追问（2026-09-15）】当前库弱命中 / 跨库无强证据时''',
    u'''  /* __QA_AI_BRAIN_20260921__ A3 问法改写：本地弱命中时先用 AI 把口语问法改写成库内
     可能的检索式再检索一次。命中即走库内直答（可信、可溯源），未命中原样回落原链路。
     这一步把 AI 从「兜底备胎」提到「主链路调度位」——库内直答仍然优先。 */
  if (intent === 'kb' && window.QABRAIN){
    try{
      const rw = await QABRAIN.rewriteAndSearch(text);
      if (rw && rw.hits && kbStrong(rw.hits)){
        await typing(''); clearTyping();
        if (rw.q && rw.q !== String(text).trim()){
          addMsg('bot', '<div class="kbox">🔎 换个说法查到了：<b>' + esc(rw.q) + '</b></div>');
        }
        kbReply(rw.hits, text);
        return;
      }
    }catch(e){}
  }
  // 【候选追问（2026-09-15）】当前库弱命中 / 跨库无强证据时'''
)

EDIT_AUDIT = (
    'QABRAIN.auditAnswer(resp, kbCtx)',
    u'''      const resp = await SpringAI.chatLLM([{ role:'system', content: sys }].concat(messages), { temperature:0.75, maxTokens:700 });
      aiLastResp = resp;
      addMsg('bot', mdToHtml(resp), { answer:true, q: text });''',
    u'''      const resp = await SpringAI.chatLLM([{ role:'system', content: sys }].concat(messages), { temperature:0.75, maxTokens:700 });
      aiLastResp = resp;
      /* __QA_AI_BRAIN_20260921__ A6 强制溯源 + A5 未明示需求：AI 回答渲染前用库内上下文
         做一次本地事实核对（把查不到依据的数值/章节号标出来），并补上库内推荐芯片。
         全部本地完成，不额外消耗 AI 调用。 */
      addMsg('bot', (window.QABRAIN ? QABRAIN.auditAnswer(resp, kbCtx) : mdToHtml(resp)), { answer:true, q: text });'''
)

EDITS = [EDIT_FOLLOW, EDIT_REWRITE, EDIT_AUDIT]


def strip_block(s):
    return re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END) + r'\s*', '', s, flags=re.S)


def main():
    if not os.path.exists(QA):
        print('[ERR] 找不到 qa.html')
        return 1
    s = io.open(QA, 'r', encoding='utf-8', newline='').read()
    n_before = len(s)

    if not os.path.exists(BAK):
        shutil.copy2(QA, BAK)
        print('[bak] -> %s' % os.path.basename(BAK))

    # 1) 块本体：strip → replay
    if BEGIN in s:
        print('[up] 旧块存在 → strip 后 replay')
        s = strip_block(s)
    if s.count(ANCHOR) != 1:
        print('[ERR] 锚点 %s 出现 %d 次（应为 1）' % (ANCHOR, s.count(ANCHOR)))
        return 1
    s = s.replace(ANCHOR, ANCHOR + '\n' + BLOCK, 1)
    print('[+] AI 赋魂块已就位（%d 字符）' % len(BLOCK))

    # 2) 三处 in-place 改动：标记已存在则跳过（幂等）
    for mark, old, new in EDITS:
        if mark in s:
            print('[=] 已应用，跳过：%s' % mark)
            continue
        cnt = s.count(old)
        if cnt != 1:
            print('[ERR] 锚点不唯一（%d 次）：%s' % (cnt, old[:56].replace('\n', '\\n')))
            return 1
        s = s.replace(old, new, 1)
        print('[+] 已改：%s' % mark)

    checks = {
        '块恰好 1 份': s.count(BEGIN) == 1 and s.count(END) == 1,
        '运行时守卫': GUARD in s,
        '对外接口 QABRAIN': 'window.QABRAIN = {' in s,
        'A4 已接': 'QABRAIN.resolveFollowUp(text)' in s,
        'A3 已接': 'QABRAIN.rewriteAndSearch(text)' in s,
        'A6/A5 已接': 'QABRAIN.auditAnswer(resp, kbCtx)' in s,
        '原 process 定义未动': 'async function process(text){' in s,
        '原 AI 兜底 addMsg 已被替换': u"addMsg('bot', mdToHtml(resp), { answer:true, q: text });" not in s,
        '情绪共情 addMsg 未受影响': u"addMsg('bot', mdToHtml(resp), { answer:true, q:text });" in s,
        '原 kbStrong 定义未动': 'function kbStrong(hits){' in s,
        '原 kbReply 定义未动': 'function kbReply(hits, rawText){' in s,
        '注入位预留': '__QA_BUILTIN_AI__' in s,
        '无内置密钥字面量': ('4986b927' not in s) and ('BUILTIN_AI_KEY' not in s),
        'script 标签平衡': s.count('<script') == s.count('</script>'),
        '体积未异常变化': abs(len(s) - n_before) < 60000,
    }
    fails = [k for k, v in checks.items() if not v]
    for k, v in checks.items():
        print('  [%s] %s' % ('OK' if v else 'NG', k))
    if fails:
        print('!! 自检失败，未写盘')
        return 1
    _atomic_write(QA, s)
    print('[ok] AI 赋魂已就位（%+d 字符）' % (len(s) - n_before))
    return 0


if __name__ == '__main__':
    if '--check' in sys.argv:
        s = io.open(QA, 'r', encoding='utf-8', newline='').read()
        ok = (BEGIN in s and GUARD in s and s.count(BEGIN) == 1
              and all(m in s for m, _o, _n in EDITS))
        print('[check] AI 赋魂：%s' % ('OK' if ok else 'FAIL'))
        raise SystemExit(0 if ok else 1)
    raise SystemExit(main())
