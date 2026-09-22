# -*- coding: utf-8 -*-
"""把 index.html 壳层新增的弹窗动效 + 内嵌高度补偿 + 深色打通，
   同步进 _gzip_build.py / _build_4in1.py 的 TEMPLATE 字符串。

源：index.html（唯一来源）
目标块：
  1) CCSheet CSS / JS 块（标记 /*__CC_SHEET*__*/）
  2) fxRecede / fxModal（弹窗动效适配层）
  3) injectEmbedCss（含 EMBED_BASE + applyEmbedVars 调用）
  4) applyTheme（含 ALL_MODS + data-bs-theme + applyEmbedVars）
  5) applyEmbedVars / refreshEmbedVars
  6) openMoreSheet / closeMoreSheet（走 CCSheet 引擎）
  7) closePacksModal 空安全

幂等：重复运行结果一致。
"""
import io, os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(BASE, 'index.html')
TARGETS = ['_gzip_build.py', '_build_4in1.py']

def read(p):
    with io.open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()

def write(p, s):
    # A1：原子写（tmp_write + os.replace），异常不再把目标截成半截；
    #     删掉原 28 行死代码 s.encode('utf-8')（返回值被丢弃，无任何作用）。
    tmp = p + '.tmp_write'
    with io.open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(s)
    os.replace(tmp, p)

def extract_template(src):
    i = src.find("TEMPLATE = u'''")
    if i < 0:
        raise SystemExit('TEMPLATE not found')
    j = src.find("'''", i + 16)
    if j < 0:
        raise SystemExit('TEMPLATE end not found')
    return i + 16, j, src[i + 16:j]

def norm_text(x):
    """归一化：去掉注释与空白，用于内容一致性比对（避免因前导注释差异反复重写）"""
    x = re.sub(r'/\*.*?\*/', '', x, flags=re.S)
    x = re.sub(r'(?m)^\s*//.*$', '', x)
    x = re.sub(r'\s+', ' ', x)
    return x.strip()

def _scan_to_matching_brace(src, start):
    """从 src[start]（必须是 '{'）开始，返回与之配平的右 '}' 索引。

    A2：轻量词法扫描。字符串(' " `)、模板字面量、// 行注释、/* */ 块注释、
    以及正则字面量内的括号都不计入配平。正则判定：仅当 '/' 前的有效字符
    非标识符、非 ')'、非 ']' 时视为正则起始（区分除法）。
    """
    if start < 0 or src[start] != '{':
        return -1
    depth = 0
    i = start
    n = len(src)
    prev = ''  # 上一个「有效字符」（用于正则判定）
    while i < n:
        c = src[i]
        # 行注释
        if c == '/' and i + 1 < n and src[i + 1] == '/':
            j = src.find('\n', i)
            i = n if j < 0 else j
            continue
        # 块注释
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            j = src.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        # 字符串 / 模板字面量（含转义 \）
        if c in ('"', "'", '`'):
            quote = c
            i += 1
            while i < n:
                ch = src[i]
                if ch == '\\':
                    i += 2
                    continue
                if ch == quote:
                    i += 1
                    break
                i += 1
            prev = c
            continue
        # 正则字面量？
        if c == '/':
            is_ident = prev.isalnum() or prev in ('_', '$')
            if not is_ident and prev not in (')', ']'):
                i += 1
                while i < n:
                    ch = src[i]
                    if ch == '\\':
                        i += 2
                        continue
                    if ch == '/':
                        i += 1
                        while i < n and src[i].isalnum():  # 吃掉 gimuy 等标志
                            i += 1
                        break
                    if ch == '\n':  # 正则不允许跨行（非法，稳妥终止）
                        break
                    i += 1
                prev = '/'
                continue
            # 否则当作普通除法
            prev = c
            i += 1
            continue
        # 普通字符
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i
        prev = c
        i += 1
    return -1

def grab_fn(src, name):
    """抓取 `function name(...){ ... }` 完整块（词法花括号配平）"""
    m = re.search(r'(?:^|\n)(function\s+' + re.escape(name) + r'\s*\()', src)
    if not m:
        return None
    start = m.start(1)
    k = src.find('{', m.end(1) - 1)
    if k < 0:
        return None
    end = _scan_to_matching_brace(src, k)
    if end < 0:
        return None
    return src[start:end + 1]

def grab_with_lead(src, name, back=180):
    b = grab_fn(src, name)
    if not b:
        return None
    st = src.find(b)
    # 往前吃注释行
    lead = st
    for _ in range(6):
        ls = src.rfind('\n', 0, lead - 1)
        if ls < 0:
            break
        line = src[ls + 1:lead]
        if line.strip().startswith('/*') or line.strip().startswith('*') or line.strip().startswith('//') or line.strip() == '':
            lead = ls + 1
        else:
            break
    return src[lead:st + len(b)]

def main():
    html = read(INDEX)

    # ---- 1) 标记块 ----
    m_css = re.search(r'/\*__CC_SHEET:v1__\*/(.*?)/\*__CC_SHEET_END__\*/', html, re.S)
    m_js  = re.search(r'/\*__CC_SHEET_JS:v1__\*/(.*?)/\*__CC_SHEET_JS_END__\*/', html, re.S)

    # ---- 2) 函数块（含其前导注释/前置变量声明）----
    FNS = {}
    for fn in ['applyEmbedVars', 'fitEmbedMain', 'watchEmbedMain', 'refreshEmbedVars', 'injectEmbedCss', 'applyTheme', 'openMoreSheet', 'closeMoreSheet']:
        b = grab_with_lead(html, fn)
        if b:
            FNS[fn] = b

    # ALL_MODS 常量 + _moreSheetInst 声明
    m_allmods = re.search(r"const ALL_MODS = \[[^\]]*\];", html)
    if m_allmods:
        FNS['__ALL_MODS'] = m_allmods.group(0)

    # EMBED_BASE 常量（injectEmbedCss 里引用的 --embed-bottom 基底）
    m_embedbase = re.search(r"const EMBED_BASE\s*=\s*'[^']*';", html)
    if m_embedbase:
        FNS['__EMBED_BASE'] = m_embedbase.group(0)

    print('从 index.html 抽到函数块:', ', '.join(sorted(FNS.keys())))
    print('  CCSheet css %d / js %d 字符' % (len(m_css.group(1)) if m_css else 0, len(m_js.group(1)) if m_js else 0))

    for tgt in TARGETS:
        p = os.path.join(BASE, tgt)
        src = read(p)
        ti, tj, tpl = extract_template(src)
        orig_len = len(tpl)
        changed = []

        # --- CCSheet CSS：插在 </style> 前（内容一致则跳过，避免漂移）---
        if m_css:
            want = norm_text(m_css.group(1))
            cur = re.search(r'/\*__CC_SHEET:v1__\*/(.*?)/\*__CC_SHEET_END__\*/', tpl, re.S)
            if not (cur and norm_text(cur.group(1)) == want):
                # 2026-09-21 修复：旧正则只删注释标记、留下空的 <style id="ccSheetCss"></style> 外壳，
                # 随后又插一份新外壳 -> 产物出现「重复 id + 空样式壳」。删除时必须连外壳一起删。
                tpl = re.sub(r'(?:<style id="ccSheetCss">\s*)?/\*__CC_SHEET:v1__\*/.*?/\*__CC_SHEET_END__\*/(?:\s*</style>\n?)?', '', tpl, flags=re.S)
                anchor = tpl.rfind('</style>')
                if anchor < 0:
                    anchor = tpl.rfind('</head>')
                else:
                    # 2026-09-21 修复：必须插在收口「之后」。插在 </style> 之前会把新壳塞进
                    # 上一个 <style> 内部 —— <style> 是 raw-text 元素不嵌套，结果提前收口
                    # 并留下一个游离 </style>（产物 spring-assistant/离线版 已实测出现）。
                    anchor += len('</style>')
                if anchor >= 0:
                    blk = '/*__CC_SHEET:v1__*/' + m_css.group(1) + '/*__CC_SHEET_END__*/'
                    tpl = tpl[:anchor] + '<style id="ccSheetCss">\n' + blk + '\n</style>\n' + tpl[anchor:]
                    changed.append('css')

        # --- CCSheet JS：插在 </body> 前（内容一致则跳过）---
        if m_js:
            want = norm_text(m_js.group(1))
            cur = re.search(r'/\*__CC_SHEET_JS:v1__\*/(.*?)/\*__CC_SHEET_JS_END__\*/', tpl, re.S)
            if not (cur and norm_text(cur.group(1)) == want):
                # 2026-09-21 修复：同上，JS 块删除也要连 <script id="ccSheetJs"> 外壳一起删，避免留空壳。
                tpl = re.sub(r'(?:<script id="ccSheetJs">\s*)?/\*__CC_SHEET_JS:v1__\*/.*?/\*__CC_SHEET_JS_END__\*/(?:\s*</script>\n?)?', '', tpl, flags=re.S)
                anchor = tpl.rfind('</body>')
                if anchor >= 0:
                    blk = '/*__CC_SHEET_JS:v1__*/' + m_js.group(1) + '/*__CC_SHEET_JS_END__*/'
                    tpl = tpl[:anchor] + '\n<script id="ccSheetJs">\n' + blk + '\n</script>\n' + tpl[anchor:]
                    changed.append('js')

        # --- fxRecede / fxModal（内容比对，避免反复插入）---
        fx_r = grab_with_lead(html, 'fxRecede')
        fx_m = grab_with_lead(html, 'fxModal')
        if fx_r and fx_m:
            old_r = grab_with_lead(tpl, 'fxRecede')
            old_m = grab_with_lead(tpl, 'fxModal')
            if old_r and old_m and norm_text(old_r) == norm_text(fx_r) and norm_text(old_m) == norm_text(fx_m):
                pass
            else:
                if old_r:
                    tpl = tpl.replace(old_r, fx_r, 1)
                old_m2 = grab_with_lead(tpl, 'fxModal')
                if old_m2:
                    tpl = tpl.replace(old_m2, fx_m, 1)
                    changed.append('fxModal')
                else:
                    m = re.search(r'function\s+closeModalId\s*\([^)]*\)\s*\{[^}]*\}\s*\n', tpl)
                    if m:
                        tpl = tpl[:m.end()] + fx_r + '\n' + fx_m + '\n' + tpl[m.end():]
                        changed.append('fxModal+')

        # --- 常量替换（内容一致则跳过，避免每轮多插换行）---
        if '__ALL_MODS' in FNS:
            cur = re.search(r"const ALL_MODS = \[[^\]]*\];", tpl)
            if not (cur and norm_text(cur.group(0)) == norm_text(FNS['__ALL_MODS'])):
                tpl2 = re.sub(r"const ALL_MODS = \[[^\]]*\];", '', tpl)
                m = re.search(r"let hostTheme = 'light';", tpl2)
                if m:
                    tpl = tpl2[:m.end()] + '\n' + FNS['__ALL_MODS'] + tpl2[m.end():]
                    changed.append('ALL_MODS')
        if '__EMBED_BASE' in FNS:
            cur = re.search(r"const EMBED_BASE\s*=\s*'[^']*';", tpl)
            if not (cur and norm_text(cur.group(0)) == norm_text(FNS['__EMBED_BASE'])):
                tpl2 = re.sub(r"const EMBED_BASE\s*=\s*'[^']*';", '', tpl)
                m = re.search(r"const EMBED_CSS\s*=\s*\{", tpl2)
                if m:
                    tpl = tpl2[:m.start()] + FNS['__EMBED_BASE'] + '\n' + tpl2[m.start():]
                    changed.append('EMBED_BASE')

        # --- 函数逐个替换（模板里没有定义则插入到 applyTheme 之前）---
        # refreshEmbedVars 统一由下方 ccEmbedRefresh 块注入，此处跳过避免重复定义
        def norm(x):
            return re.sub(r'\s+', ' ', x).strip()
        for fn in ['injectEmbedCss', 'applyTheme', 'applyEmbedVars', 'fitEmbedMain', 'watchEmbedMain', 'openMoreSheet', 'closeMoreSheet']:
            if fn not in FNS:
                continue
            old = grab_with_lead(tpl, fn)
            if old:
                if norm(old) == norm(FNS[fn]):
                    continue
                tpl = tpl.replace(old, FNS[fn], 1)
                changed.append(fn)
            else:
                # 模板里缺失该函数定义 → 插到 applyTheme 定义之前（保证调用前已定义）
                anchor = grab_with_lead(tpl, 'applyTheme')
                if anchor:
                    tpl = tpl.replace(anchor, FNS[fn] + '\n' + anchor, 1)
                    changed.append(fn + '+new')
                else:
                    m2 = re.search(r'/\* =+ 主题 =+ \*/', tpl)
                    if m2:
                        tpl = tpl[:m2.start()] + FNS[fn] + '\n' + tpl[m2.start():]
                        changed.append(fn + '+ins')

        # --- closePacksModal 空安全 ---
        old_cpm = "function closePacksModal(){ document.getElementById('packsModal').classList.remove('show'); }"
        if old_cpm in tpl:
            tpl = tpl.replace(old_cpm, "function closePacksModal(){ const m=document.getElementById('packsModal'); if(m) m.classList.remove('show'); }")
            changed.append('closePacksModal')

        # --- refreshEmbedVars + resize/orientation 监听（内容一致则跳过）---
        if 'refreshEmbedVars' in FNS:
            want = norm_text(FNS['refreshEmbedVars'])
            cur = re.search(r'<script id="ccEmbedRefresh">(.*?)</script>', tpl, re.S)
            if not (cur and norm_text(cur.group(1)).find(want) >= 0):
                tpl = re.sub(r'<script id="ccEmbedRefresh">.*?</script>\s*', '', tpl, flags=re.S)
                anchor = tpl.rfind('</body>')
                if anchor >= 0:
                    blk = ('<script id="ccEmbedRefresh">\n'
                           + FNS['refreshEmbedVars'] + '\n'
                           + "try{\n"
                           + "  window.addEventListener('resize', function(){ refreshEmbedVars(); });\n"
                           + "  window.addEventListener('orientationchange', function(){ setTimeout(refreshEmbedVars, 260); });\n"
                           + "}catch(e){}\n"
                           + '</script>\n')
                    tpl = tpl[:anchor] + blk + tpl[anchor:]
                    changed.append('refreshEmbedVars')

        if not changed:
            print('[skip] %s 无需变更' % tgt)
            continue

        out = src[:ti] + tpl + src[tj:]
        write(p, out)
        print('[ok] %-20s 模板 %d -> %d  (%s)' % (tgt, orig_len, len(tpl), ','.join(changed)))

    print('[done] 壳层模板同步完成')

if __name__ == '__main__':
    main()
