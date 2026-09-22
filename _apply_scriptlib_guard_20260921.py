# -*- coding: utf-8 -*-
"""销售话术库入库闸 scriptLibGuard()（2026-09-21）

背景（审查遗留待办）：
    话术库 scriptLibraryData 是**独立数据块**，不在话术生成引擎的治理范围内 ——
    tsSanitize 只在生成路径（beauty.html:26692）生效，话术库的「渲染 / 复制 / 保存」
    三条路径都不清洗，引擎已治理的红线仍会留在库里，人工新增的话术更是零校验。

本补丁补三道闸（幂等，可重复执行）：
    1) 入库闸   saveScriptLib() 保存前过闸：违规直接拒绝并列出「规则 / 命中 / 建议」；
                自动改写高置信表述（爆款→人气款 等）后入库
    2) 出口闸   copyScriptContent() 复制前过闸（复制出去的就是对客话术）
    3) 渲染兜底 卡片正文由 ${script.content} 改为 ${window.slRender(script.content)}
                —— 既做 HTML 转义（防内容里的 <> 破坏 DOM / 注入），也做红线兜底

顺带修掉的真实缺陷：
    · 话术库的 copyScriptContent / saveScriptLib / editScriptLib / deleteScriptLib /
      openScriptLibForm / closeScriptLibForm 都是块级 const，**从未挂 window**，
      而模板字符串里的 onclick 走的是全局作用域 → 这些按钮实际会 ReferenceError。
      本补丁统一挂 window。
    · 复制按钮把整段话术塞进 onclick 属性（`script.content.replace(/'/g,"\\'")`），
      内容含换行/反斜杠/双引号即破串 → 改为按 id 查找（copyScriptById）。
    · loadUserScripts() 从 localStorage 读入后不做任何校验 → 补清洗与丢弃。

用法：
    python _apply_scriptlib_guard_20260921.py          # 应用
    python _apply_scriptlib_guard_20260921.py --check  # 校验标记块在位（CI）
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = u'beauty.html'
BLOCK_START = u'/*__SCRIPTLIB_GUARD_20260921__BEGIN__*/'
BLOCK_END = u'/*__SCRIPTLIB_GUARD_20260921__END__*/'
HOOK = u'/*__SL_GUARD_HOOK_20260921__*/'

GUARD_JS = r"""/*__SCRIPTLIB_GUARD_20260921__BEGIN__*/
/* 销售话术库入库闸 scriptLibGuard（2026-09-21）
 * 判据来源：SPEC §四 合规红线 + beauty.html 主流程取证的对客口径
 *   · 赔付=假一赔四 / 退货=7天无理由 / 物流=落地前下单 3-7 天到家
 *   · 价格=机上专享价、统一核定、乘务员无降价权限 → 任何折扣/满减/会员价均冲突
 * 三道闸：入库(save)、出口(复制)、渲染兜底。零 DOM 依赖，纯函数便于单测。 */
(function () {
  'use strict';
  if (window.__slGuardReady) return;
  window.__slGuardReady = true;

  var MAX_LEN = 500;

  /* ---- 自动改写：可安全修正的高置信表述，入库不打断，但记入 fixed 供回溯 ---- */
  var SAFE_RE = [
    [/爆款/g, '人气款'],
    [/明星产品/g, '人气产品'],
    [/明星单品/g, '人气单品'],
    [/全网最低/g, '价格实在'],
    [/最低价/g, '划算的价格'],
    [/最便宜/g, '价格实惠'],
    [/手慢无/g, '很多旅客回购'],
    [/错过就没有/g, ''],
    [/错过再等一年/g, ''],
    [/最好的选择|市面上最好|同类最好|最好的一款/g, '很合适的一款'],
    [/最好的/g, '很合适的'],
    [/最佳选择|市面上最佳/g, '很合适的选择'],
    [/第一品牌|行业第一|全国第一|全网第一/g, '人气很高'],
    [/显老/g, '显干'],
    [/脸垮/g, '看着没精神'],
    [/黄脸婆/g, ''],
    [/年纪大了|上了年纪/g, '岁数上来以后'],
    [/皮肤很差|皮肤差|皮肤不好/g, '皮肤状态一般'],
    [/不修边幅|赘肉|发福|没文化|土气|没品位/g, ''],
    [/买不起|舍不得|斤斤计较|小气/g, ''],
    [/掉价/g, '失礼'],
    [/廉价/g, '平价'],
    [/比专柜|比代购|比免税店|比免税|比官网|比旗舰店/g, ''],
    [/绝对/g, ''],
    [/100%|百分百/g, '']
  ];

  /* ---- 硬红线：无法安全改写（改了会语义残缺或属原则问题），必须人工修改后入库 ---- */
  var RULES = [
    { rule: '医疗与功效宣称', re: /治疗|治愈|根治|包治|药到病除|无副作用|消炎|杀菌|注射|填充|医美|水光针|热玛吉|干细胞/, suggest: '只描述使用场景与感受，不做医疗宣称' },
    { rule: '绝对化用语', re: /唯一|顶级|国家级|立竿见影|极致/, suggest: '改为客观描述，如「人气款」「很合适」' },
    { rule: '饥饿营销', re: /仅此一次|最后一天|清仓|甩卖|跳楼价/, suggest: '删除催促与清仓表述' },
    { rule: '伪科学机理', re: /排毒|排浊|毒素|血液循环加快|吸收营养最好|黄金时间/, suggest: '删除无依据的机理描述' },
    { rule: '评判旅客本人', re: /大妈|大爷|老人家|黄脸婆/g, suggest: '只描述场景与需求，不评价旅客本人' },
    { rule: '效果与时间承诺', re: /永久|一劳永逸|彻底解决|7天美白|三天见效|一次见效|立刻见效|马上见效/, suggest: '删除时间与效果承诺' },
    { rule: '与官方价格口径冲突', re: /打\s?[0-9一二三四五六七八九]\s?折|[0-9]+\s?折|立减|满减|买一送一|买二送一|半价|会员价|员工价|内部价/, suggest: '机上专享价统一核定，乘务员无降价权限，勿写折扣/促销/内部价' },
    { rule: '占位符残留', re: /\{[^}]{1,12}\}|\$\{|还有\s*[XxＮＮ]\s*份/, suggest: '补全为具体文案' },
    { rule: '特殊人群适用', re: /婴幼儿可用|宝宝可用|孕妇可用|孕妇也可以|术后可用/, suggest: '删除特殊人群适用宣称' }
  ];

  /* ---- 软提示：不阻断，仅提示 ---- */
  var WARNS = [
    { rule: '软绝对化', re: /最好|最佳|最强|最优|独家|极致|行业领先|遥遥领先/ },
    { rule: '数据承诺', re: /[0-9]+\s*%|[0-9]+\s*倍|提升了?\s*[0-9]+/ }
  ];

  var MEMO = {};
  var MEMO_N = 0;

  function sanitize(t) {
    var s = String(t == null ? '' : t);
    s = s.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, '');
    s = s.replace(/<[^>]*>/g, '');
    s = s.replace(/\s+/g, ' ').trim();
    if (s.length > MAX_LEN) s = s.slice(0, MAX_LEN);
    return s;
  }

  function guard(text) {
    var orig = String(text == null ? '' : text);
    var t = sanitize(orig);
    var issues = [];
    if (/<[^>]*>|on[a-z]+\s*=/i.test(orig)) {
      issues.push({ level: 'warn', rule: '已剥离标签', hit: 'HTML 标签或事件属性', suggest: '话术为纯文本，已自动剥离' });
    }
    var fixed = [];
    SAFE_RE.forEach(function (p) {
      var before = t;
      t = t.replace(p[0], p[1]);
      if (t !== before) fixed.push(p[1] || '（删除）');
      t = t.replace(/\s{2,}/g, ' ').trim();
    });
    if (fixed.length) {
      issues.push({ level: 'warn', rule: '已自动改写', hit: fixed.join('、'), suggest: '入库前已按合规口径自动修正，请确认语意仍通顺' });
    }
    RULES.forEach(function (r) {
      var m = t.match(r.re);
      if (m) issues.push({ level: 'block', rule: r.rule, hit: m[0], suggest: r.suggest });
    });
    WARNS.forEach(function (r) {
      var m = t.match(r.re);
      if (m) issues.push({ level: 'warn', rule: r.rule, hit: m[0], suggest: '建议改为客观描述' });
    });
    var blocks = issues.filter(function (x) { return x.level === 'block'; });
    return {
      ok: blocks.length === 0,
      content: t,
      issues: issues,
      blocks: blocks,
      fixed: fixed,
      changed: t !== orig
    };
  }

  function memoGuard(text) {
    var k = String(text == null ? '' : text);
    if (MEMO.hasOwnProperty(k)) return MEMO[k];
    var g = guard(k);
    if (MEMO_N < 4000) { MEMO[k] = g; MEMO_N++; }
    return g;
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  window.scriptLibGuard = guard;
  window.scriptLibGuardMemo = memoGuard;
  window.slEsc = esc;
  window.slRender = function (c) { return esc(memoGuard(c).content); };
})();
/*__SCRIPTLIB_GUARD_20260921__END__*/"""


def read_text(p):
    with io.open(p, encoding='utf-8', newline='') as f:
        return f.read()


def write_text(p, s):
    tmp = p + '.tmp_write'
    with io.open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(s)
    os.replace(tmp, p)


def find_head_anchor(s):
    cands = [m.start() for m in re.finditer(r'</head>', s, re.I)
             if re.match(r'[ \t]*\r?\n[ \t]*<body', s[m.end():m.end() + 40], re.I)]
    if cands:
        return cands[-1]
    return s.rfind(u'</head>')


def apply_guard_block(s):
    """注入/替换 guard 引擎块（幂等）"""
    si = s.find(BLOCK_START)
    ei = s.find(BLOCK_END)
    if si >= 0 and ei >= 0:
        script_open = s.rfind(u'<script>', 0, si)
        script_close = s.find(u'</script>', ei)
        if script_open == -1 or script_close == -1:
            raise ValueError(u'guard 标记块未包裹在 script 内')
        return s[:script_open] + u'<script>\n' + GUARD_JS + u'\n</script>' + s[script_close + len(u'</script>'):]
    if si >= 0 or ei >= 0:
        raise ValueError(u'guard 标记位不完整，需人工处理')
    head = find_head_anchor(s)
    if head == -1:
        raise ValueError(u'未找到 </head>')
    return s[:head] + u'<script>\n' + GUARD_JS + u'\n</script>\n' + s[head:]


# 闸上线后扫出的库内漏网口径（与「机上专享价、统一核定、乘务员无降价权限」冲突）
FIXES = [
    (u'感谢您一直以来对春秋航空的支持，作为回馈，这款产品给您会员内部价。',
     u'感谢您一直以来对春秋航空的支持，这款产品按机上专享价给您，价格统一核定、含税一价全包。'),
    (u'我能帮您在商城里看看有没有满减券可以用，这样算下来更合适。',
     u'我帮您在商城里看看这款的机上专享价，机上价格统一核定，已经是含税一价全包。'),
]

PAIRS = [
    # 1) 渲染兜底：卡片正文转义 + 红线兜底
    (
        u'<p class="text-sm text-gray-800 leading-relaxed break-words">${script.content}</p>',
        u'<p class="text-sm text-gray-800 leading-relaxed break-words">${window.slRender(script.content)}</p>',
        u'window.slRender(script.content)'
    ),
    # 2) 复制按钮：不再把整段话术塞进 onclick（含换行/引号即破串），改为按 id 查找
    (
        u"""onclick="copyScriptContent('${script.content.replace(/'/g, "\\\\'")}')" """.strip(),
        u"""onclick="copyScriptById('${catKey}','${script.id}')" """.strip(),
        u"copyScriptById('"
    ),
]

OLD_COPY = u"""        const copyScriptContent = (content) => {
            if (navigator.clipboard) {
                navigator.clipboard.writeText(content).then(() => {"""
NEW_COPY = u"""        """ + HOOK + u"""
        const copyScriptContent = (content) => {
            /* 2026-09-22 安全审查修复（fail-closed）：出口闸缺失时不再放行（复制出去的就是对客话术） */
            if (!window.scriptLibGuard) {
                showAlert('合规校验未加载', '出口闸未就绪，为避免复制未过闸话术，本次复制已阻止。请刷新页面后重试。');
                return;
            }
            const _g = window.scriptLibGuard(content);
            const _text = _g.content;
            if (_g.issues && _g.issues.length) { try { console.warn('[话术库闸] 复制出口已清洗', _g.issues); } catch (_e) {} }
            if (navigator.clipboard) {
                navigator.clipboard.writeText(_text).then(() => {"""

OLD_COPY_FALLBACK = u"""                    const textarea = document.createElement('textarea');
                    textarea.value = content;"""
NEW_COPY_FALLBACK = u"""                    const textarea = document.createElement('textarea');
                    textarea.value = _text;"""

OLD_SAVE = u"""        const saveScriptLib = (scriptId) => {
            const content = (document.getElementById('scriptlib-content')?.value || '').trim();
            if (!content) { showAlert('提示', '请输入话术内容'); return; }"""
NEW_SAVE = u"""        """ + HOOK + u"""
        const saveScriptLib = (scriptId) => {
            const _raw = (document.getElementById('scriptlib-content')?.value || '').trim();
            if (!_raw) { showAlert('提示', '请输入话术内容'); return; }
            /* 2026-09-22 安全审查修复（fail-closed）：闸缺失时此前走 `{ok:true}` 静默放行 */
            if (!window.scriptLibGuard) {
                showAlert('合规校验未加载', '入库闸未就绪，为安全起见本次保存已阻止。请刷新页面后重试。');
                return;
            }
            const _g = window.scriptLibGuard(_raw);
            if (!_g.ok) {
                showAlert('话术未通过合规校验', (_g.blocks || []).map(function (x) {
                    return '· ' + x.rule + '：命中「' + x.hit + '」' + (x.suggest ? '，建议：' + x.suggest : '');
                }).join('\\n'));
                return;
            }
            const content = _g.content;"""

OLD_LOAD = u"""        const loadUserScripts = () => {
            try {
                const s = localStorage.getItem('userScripts');
                if (s) {
                    state.userScripts = JSON.parse(s);
                } else {
                    state.userScripts = [];
                }
            } catch(e) {
                state.userScripts = [];
            }
        };"""
NEW_LOAD = u"""        """ + HOOK + u"""
        const loadUserScripts = () => {
            try {
                const s = localStorage.getItem('userScripts');
                let arr = [];
                if (s) { try { arr = JSON.parse(s) || []; } catch (_e2) { arr = []; } }
                if (!Array.isArray(arr)) arr = [];
                let dropped = 0;
                state.userScripts = arr.filter(function (u) {
                    if (!u || typeof u.content !== 'string' || !u.content.trim()) { dropped++; return false; }
                    const g = window.scriptLibGuard ? window.scriptLibGuard(u.content) : { ok: true, content: u.content };
                    if (!g.ok) { dropped++; return false; }
                    u.content = g.content;
                    return true;
                });
                if (dropped) { try { console.warn('[话术库闸] 已丢弃不合规自定义话术 ' + dropped + ' 条'); } catch (_e3) {} }
            } catch(e) {
                state.userScripts = [];
            }
        };"""

OLD_COPY_TAIL = u"""        const copyScriptContent = (content) => {"""
EXPORTS = u"""
        /* 话术库函数挂 window：模板串里的 onclick 走全局作用域，块级 const 调用不到（2026-09-21 修复）
           —— 2026-09-22 审查修复：此块原先被误插进 copyScriptById 函数体（永不执行），现放回顶层；
           位置必须在 copyScriptContent 声明之后，否则 const 的 TDZ 会在加载期抛 ReferenceError。 */
        window.copyScriptById = copyScriptById;
        window.copyScriptContent = copyScriptContent;
        window.saveScriptLib = saveScriptLib;
        window.editScriptLib = editScriptLib;
        window.deleteScriptLib = deleteScriptLib;
        window.openScriptLibForm = openScriptLibForm;
        window.closeScriptLibForm = closeScriptLibForm;"""

NEW_BY_ID = u"""        const copyScriptById = (catKey, scriptId) => {
            let s = null;
            const _cat = scriptLibraryData && scriptLibraryData[catKey];
            if (_cat && _cat.scripts) s = _cat.scripts.find(function (x) { return x.id === scriptId; }) || null;
            if (!s && state.userScripts) s = state.userScripts.find(function (x) { return x.id === scriptId; }) || null;
            if (!s) { showAlert('提示', '未找到该话术'); return; }
            copyScriptContent(s.content);
        };"""


def main():
    path = os.path.join(HERE, TARGET)
    s = read_text(path)
    before = s
    acts = []

    s = apply_guard_block(s)
    acts.append(u'guard 引擎块')

    for old, new, marker in PAIRS:
        if marker in s:
            continue
        if old not in s:
            raise ValueError(u'锚点未命中（源文件已改动？）：' + marker)
        s = s.replace(old, new, 1)
        acts.append(marker)

    for old, new in FIXES:
        if old in s:
            s = s.replace(old, new, 1)
            acts.append(u'口径修复：' + old[:12] + u'…')

    if HOOK not in s.split(u'const copyScriptContent')[0][-400:]:
        pass

    if u'const copyScriptById' not in s:
        idx = s.find(OLD_COPY_TAIL)
        if idx == -1:
            raise ValueError(u'未找到 copyScriptContent 定义')
        s = s[:idx] + NEW_BY_ID + u'\n' + s[idx:]
        acts.append(u'copyScriptById')

    if OLD_COPY in s:
        s = s.replace(OLD_COPY, NEW_COPY, 1)
        acts.append(u'复制出口过闸')
    if OLD_COPY_FALLBACK in s:
        s = s.replace(OLD_COPY_FALLBACK, NEW_COPY_FALLBACK, 1)
        acts.append(u'复制兜底路径')
    if OLD_SAVE in s:
        s = s.replace(OLD_SAVE, NEW_SAVE, 1)
        acts.append(u'入库闸')
    if OLD_LOAD in s:
        s = s.replace(OLD_LOAD, NEW_LOAD, 1)
        acts.append(u'本地话术读入过闸')
    if u'window.copyScriptById' not in s:
        # 2026-09-22 结构修正：原实现把导出块插在 `copyScriptContent(s.content);` 之后，
        # 而那句在 copyScriptById 的函数体里 → 导出永不执行（CRUD 按钮全 ReferenceError）。
        # 现插到顶层锚点 `const insertEmotionResponse` 之前 —— 该处所有被导出的 const
        # （含 copyScriptContent）均已声明，既不落进函数体也不会踩 const 的 TDZ。
        anchor = s.find(u'const insertEmotionResponse')
        if anchor == -1:
            raise ValueError(u'未找到 insertEmotionResponse 锚点，无法挂 window')
        s = s[:anchor] + EXPORTS.strip(u'\n') + u'\n\n        ' + s[anchor:]
        acts.append(u'挂 window')

    if s == before:
        print(u'%s -> 无变化（已全部应用）' % TARGET)
        return
    write_text(path, s)
    print(u'%s -> 已应用：%s' % (TARGET, u'、'.join(acts)))


def check():
    path = os.path.join(HERE, TARGET)
    s = read_text(path)
    need = [
        (u'guard 引擎块', BLOCK_START),
        (u'渲染兜底', u'window.slRender(script.content)'),
        (u'复制按 id', u"copyScriptById('"),
        (u'copyScriptById 定义', u'const copyScriptById'),
        (u'复制出口过闸', u'window.scriptLibGuard(content)'),
        (u'入库闸', u'话术未通过合规校验'),
        (u'读入过闸', u'已丢弃不合规自定义话术'),
        (u'挂 window', u'window.copyScriptById = copyScriptById'),
        (u'库内无内部价', None),
        (u'库内无满减券', None),
    ]
    ok = True
    for label, needle in need:
        if needle is None:
            continue
        got = needle in s
        print(u'  %s %s' % (u'OK ' if got else u'MISS', label))
        if not got:
            ok = False
    for bad, label in [(u'给您会员内部价', u'库内无内部价'), (u'满减券可以用', u'库内无满减券')]:
        got = bad not in s
        print(u'  %s %s' % (u'OK ' if got else u'MISS', label))
        if not got:
            ok = False
    if not ok:
        sys.exit(1)
    print(u'%s -> 全部在位' % TARGET)


if __name__ == '__main__':
    if u'--check' in sys.argv:
        check()
    else:
        main()
