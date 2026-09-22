# -*- coding: utf-8 -*-
"""壳层同步补丁（2026-09-19 · v1.5.0）——把 index.html 的顶栏改造同步到两份内嵌 TEMPLATE。

五件事（全部幂等：标记块 strip→replay + 锚定注入 + 内容比对）：
  1) 顶栏收敛 3 板块：qa/quiz/performance 加 `keep` 类 + keep 白名单 CSS
  2) 顶栏右侧三层重排 CSS（操作/信息/身份），与 index.html 同一份文本
  3) 删除数据包顶栏入口（packsBadge 按钮）与弹窗（packsModal）
  4) checkPacksUpdate 保函数、下线自动轮询调用点
  5) actions 右侧整块同步（以 index.html 为唯一来源，保证三个壳视觉一致）

目标：index.html（幂等复跑安全）、_gzip_build.py、_build_4in1.py
用法：python _apply_shell_sync_20260919.py [--check]
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.abspath(__file__))

MARK = '__SHELL_SYNC_20260919_CSS__'
NEW_CSS = r'''
/*__SHELL_SYNC_20260919_CSS__BEGIN —— 顶栏收敛 3 板块 + 右侧三层重排（源 index.html，勿直接改产物）*/
/* 2026-09-19 设计审核 P0-A/P0-B 修复：
   · 对比度：.sc-date / .uc-role / .uc-caret 原用 --text3(#B5C2BC)，实测对白仅 1.84:1（远低于 AA 4.5:1）。
     --text3 是全局令牌、别处还在用，故只在这三个选择器上改判，不动令牌。
     改用 --text2：浅色 #5A6F65 → 5.39:1；深色 #8FA89C → 6.31:1，两模式均达标。
   · 字号：三者最小 9.6px（.uc-role），低于可读下限，提到 11px / 12px。
   · 触控：顶栏方钮与页签原 36px / 38px，低于 44px 触摸底线，统一到 44px
     （顶栏高 60px，44px 控件放得下，无需改 --topbar-h，也不会挤到内容区）。 */
.module-tabs .mod-tab{display:none!important;}
.module-tabs .mod-tab.keep{display:flex!important;}
/* 触控底线：页签行 46px，44px 页签放得下（原 38px） */
.mod-tab{min-height:44px;}
.actions{display:flex;align-items:center;gap:6px;flex-shrink:0;}
.actions .act-sep{width:1px;height:22px;background:var(--border);margin:0 6px;flex-shrink:0;}
.actions .mega-btn,.actions .bk-btn,.actions .theme-btn{height:44px;border-radius:12px;border:1px solid var(--border);background:transparent;color:var(--text2);flex-shrink:0;
  transition:border-color .18s cubic-bezier(.23,1,.32,1),color .18s cubic-bezier(.23,1,.32,1),background-color .18s cubic-bezier(.23,1,.32,1);}
.actions .bk-btn{padding:0 12px;display:inline-flex;align-items:center;gap:6px;font-size:.78rem;font-weight:700;font-family:var(--font-sans);cursor:pointer;}
.actions .theme-btn{width:44px;font-size:1rem;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;}
.actions .mega-btn:hover,.actions .bk-btn:hover,.actions .theme-btn:hover{border-color:var(--primary);color:var(--primary);background:var(--primary-mist);}
.actions .mega-btn:active,.actions .bk-btn:active,.actions .theme-btn:active{transform:scale(.97);}
.actions .sys-clock{display:inline-flex;flex-direction:column;align-items:flex-end;justify-content:center;gap:0;padding:0 4px;border:none;background:transparent;line-height:1.15;white-space:nowrap;}
.actions .sys-clock .sc-time{font-size:.86rem;font-weight:800;color:var(--text);font-variant-numeric:tabular-nums;letter-spacing:.02em;}
.actions .sys-clock .sc-row{display:flex;align-items:center;gap:6px;}
.actions .sys-clock .sc-date{font-size:.6875rem;font-weight:600;color:var(--text2);}   /* 10.6px → 11px；对比度 1.84 → 5.39:1 */
.actions .sys-clock .sc-tag{font-size:.6875rem;font-weight:700;color:#8A6A00;background:transparent;padding:0;border-radius:0;}  /* 10.2px → 11px */
.actions .sys-clock .sc-tag.none{color:var(--text2);}
html[data-theme="dark"] .actions .sys-clock .sc-tag{color:#E3C56A;}
.actions .net-status{display:inline-flex;align-items:center;gap:5px;height:44px;padding:0 8px;border:none;background:transparent;color:var(--text2);font-size:.72rem;font-weight:600;}
.actions .net-status .net-dot{width:7px;height:7px;border-radius:50%;background:var(--primary);box-shadow:0 0 0 3px rgba(20,132,83,.14);}
.actions .net-status.offline{color:var(--danger);background:transparent;}
.actions .net-status.offline .net-dot{background:var(--danger);box-shadow:0 0 0 3px rgba(230,74,25,.16);}
.actions .user-chip{display:flex;align-items:center;gap:8px;min-height:44px;padding:3px 10px 3px 3px;border-radius:999px;background:var(--primary-soft);border:1px solid transparent;cursor:pointer;
  transition:background-color .18s cubic-bezier(.23,1,.32,1),border-color .18s cubic-bezier(.23,1,.32,1);}
.actions .user-chip:hover{background:var(--primary-mist);border-color:var(--primary);}
.actions .user-chip .avatar{width:34px;height:34px;border-radius:50%;background:var(--grad-primary);display:flex;align-items:center;justify-content:center;color:#fff;font-size:.8rem;font-weight:800;flex-shrink:0;}
.actions .user-chip .uc-tx{display:flex;flex-direction:column;line-height:1.2;}
.actions .user-chip #userName{font-size:.78rem;font-weight:800;color:var(--primary-dark,#0C5F3A);}
.actions .user-chip .uc-role{font-size:.75rem;font-weight:700;color:var(--text2);letter-spacing:.03em;}  /* 9.6px → 12px；对比度 1.84 → 5.39:1 */
.actions .user-chip .uc-caret{color:var(--text2);font-size:.8rem;margin-left:2px;}                      /* 对比度 1.84 → 5.39:1 */
html[data-theme="dark"] .actions .user-chip{background:#1A3D2A;}
html[data-theme="dark"] .actions .user-chip #userName{color:#8FD3B0;}
@media(max-width:1100px){.actions .user-chip .uc-role,.actions .user-chip .uc-caret{display:none;}}
@media(max-width:960px){.actions .sys-clock .sc-date{display:none;}.actions .bk-btn .act-tx{display:none;}.actions .bk-btn{padding:0 10px;}}
@media(max-width:820px){.actions .net-status #netText{display:none;}.actions .net-status{padding:0 6px;}}
@media(max-width:720px){.actions .sys-clock .sc-row{display:none;}.actions .act-sep{display:none;}}
/* --- 宽屏铺满：空间足够时展示全部板块（由壳层 JS fitNavTabs 实测后加 .nav-all） ---
   实测不可行用纯媒体查询：12 个页签 × 中文字宽 + 右侧状态区 ≈ 1600px 起，故用 JS 实测更稳。 */
.module-tabs.nav-all .mod-tab{display:flex!important;}
.module-tabs.nav-all .mod-tab.keep{display:flex!important;}
/* --- 导航「全部应用」入口（其余 9 板块的统一入口，跟随页签排布） --- */
.nav-more-btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;height:44px;padding:0 12px;margin-left:2px;flex-shrink:0;
  border:1px dashed var(--border);border-radius:12px;background:transparent;color:var(--text2);font-size:.8rem;font-weight:700;font-family:var(--font-sans);cursor:pointer;
  transition:border-color .18s cubic-bezier(.23,1,.32,1),color .18s cubic-bezier(.23,1,.32,1),background-color .18s cubic-bezier(.23,1,.32,1);}
.nav-more-btn:hover{border-style:solid;border-color:var(--primary);color:var(--primary);background:var(--primary-mist);}
.nav-more-btn:active{transform:scale(.97);}
.nav-more-btn[aria-expanded="true"]{border-style:solid;border-color:var(--primary);background:var(--grad-primary);color:#fff;}
.nav-more-btn:focus-visible{outline:2px solid var(--primary);outline-offset:2px;}
@media(max-width:1100px){.nav-more-btn .amb-tx{display:none;}.nav-more-btn{padding:0 10px;}}
/* --- 底部「更多」面板：分组小标题 + 与巨型菜单同源的 12 板块 --- */
.m-sheet h4 .ms-sub{font-size:.66rem;font-weight:600;color:var(--text3);margin-left:auto;margin-right:8px;}
.m-sheet-sec{grid-column:1/-1;font-size:.68rem;font-weight:800;color:var(--text3);letter-spacing:.06em;margin:8px 2px 2px;}
.m-sheet-sec:first-child{margin-top:0;}
/*__SHELL_SYNC_20260919_CSS__END*/
'''

# 2026-09-19 第二批（用户要求「其他板块放出来、放不下的收进工具区」）：
#   顶栏常驻 6 个高频板块（keep），其余 6 个收进「🧰 工具区」（⊞ 巨型菜单，含分组与子入口深跳）。
#   顺序即展示顺序：问答 → 培训 → 绩效 → 话术 → 日常 → 手册。
TAB_ORDER = [
    ('qa',          '\U0001F4AC', '你问我答', True,  'ThWuLHNdXekrpR8s6aKg4k'),
    ('quiz',        '\U0001F4DA', '培训考核', True,  'AfTAaJatoJoPJYGMUFg51D'),
    ('performance', '\U0001F4CA', '绩效管理', True,  'cTO8HrxlLuSrzd9nDy4qrp'),
    ('beauty',      '\U0001F484', '美妆话术', True,  'maSEZIZaLq7esXXJABvoUv'),
    ('daily',       '\u2753',     '日常问题', True,  '0ZQKCzL3CGxL5gcbwW8vpU'),
    ('manual',      '\U0001F4D5', '手册奖惩', True,  '16VCdRNReCMYPnJQ1m9LZd'),
    ('home',        '\U0001F3E0', 'CC 之家', False, ''),
    ('medical',     '\U0001F691', '医疗急救', False, 'YKyirJlt3f6LRF1fmROJfP'),
    ('risk',        '\u26A0\uFE0F', '风险预警', False, 'zBc8alWHgO1Jtz1ynUv3Nd'),
    ('report',      '\U0001F5C2', '事件报告', False, 'zuRGGdaicD84fn0TQmDPKC'),
    ('kbadmin',     '\U0001F4C7', '库管理',   False, 'tx5VFathdAJZK2NlztrCsA'),
    ('issues',      '\U0001F41E', '问题反馈', False, ''),
]

PACKS_NOTE = ('\n/* 2026-09-19 数据包更新提示整体下线（用户要求）：入口已删，开机不再轮询 manifest；\n'
              '   checkPacksUpdate 保留原实现供 kbadmin 数据包中心与单测复用。 */')


def read(p):
    with io.open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def write(p, s):
    s.encode('utf-8')
    with io.open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def strip_css(s):
    i = s.find('\n/*' + MARK + 'BEGIN')
    if i < 0:
        return s
    j = s.find('/*' + MARK + 'END*/\n', i)
    if j < 0:
        raise SystemExit('!! CSS 标记块不完整')
    return s[:i] + s[j + len('/*' + MARK + 'END*/\n'):]


def inject_css(s, name):
    s = strip_css(s)
    anchor = s.find('.toast-container{top:64px;}')
    if anchor < 0:
        raise SystemExit('!! %s 缺 CSS 锚点 toast-container' % name)
    j = s.find('</style>', anchor)
    if j < 0:
        raise SystemExit('!! %s 缺 </style> 收口' % name)
    return s[:j] + NEW_CSS + s[j:]


def build_nav():
    """按 TAB_ORDER 生成 module-tabs 的按钮序列（顶栏常驻 keep + 工具区收纳）"""
    out = []
    for mod, icon, label, keep, node in TAB_ORDER:
        cls = 'mod-tab' + (' keep' if keep else '')
        if mod == 'qa':
            cls += ' active'
        node_attr = (' data-page-node-id="%s"' % node) if node else ''
        out.append('    <button class="%s" data-mod="%s" onclick="switchModule(\'%s\')"%s>%s %s</button>'
                   % (cls, mod, mod, node_attr, icon, label))
    return '\n'.join(out)


def reorder_nav(s, nav_block):
    """整块替换 module-tabs 的按钮序列（幂等：一致则跳过）"""
    i = s.find('<nav class="module-tabs"')
    j = s.find('</nav>', i)
    if i < 0 or j < 0:
        raise SystemExit('!! 缺 module-tabs 锚点')
    start = s.find('>', i) + 1
    if s[start:j].strip() == nav_block.strip():
        return s, True
    return s[:start] + '\n' + nav_block + '\n  ' + s[j:], True


def drop_packs_button(s):
    n = s.count('id="packsBadge"')
    if n == 0:
        return s, 0
    s = re.sub(r'[ \t]*<button class="bk-btn" id="packsBadge"[\s\S]*?</button>\n', '', s, count=1)
    return s, n


def drop_packs_modal(s):
    n = s.count('id="packsModal"')
    if n == 0:
        return s, 0
    i = s.find('<!-- ===== 数据包在线更新')
    if i < 0:
        i = s.find('<div class="modal-mask" id="packsModal"')
    j = s.find('<!-- ===== 个人资料', i)
    if j < 0:
        raise SystemExit('!! packsModal 收口锚点缺失')
    seg = s[i:j]
    if len(seg) > 4000:
        raise SystemExit('!! packsModal 段长度异常 %d' % len(seg))
    note = ('<!-- ===== 数据包在线更新（M2）：2026-09-19 按用户要求删除顶栏入口与弹窗。\n'
            '     引擎（window.PACKS）保留：kbadmin 数据包中心与构建链 M3 单测仍依赖它。 ===== -->\n\n')
    return s[:i] + note + s[j:], n


def gate_packs_poll(s):
    if 'function checkPacksUpdate(){' not in s:
        return s, False
    s = re.sub(r"window\.addEventListener\('online', function\(\)\{ updateNetworkStatus\(\); checkPacksUpdate\(\); \}\);",
               "window.addEventListener('online', updateNetworkStatus);  /* 2026-09-19 数据包更新提示整体下线：不再随联网重查 */",
               s, count=1)
    s = re.sub(r"\nwindow\.addEventListener\('focus', checkPacksUpdate\);.*", "", s, count=1)
    if '数据包更新提示整体下线' not in s:
        s = s.replace('\ncheckPacksUpdate();', PACKS_NOTE, 1)
    return s, True


def extract_actions(src):
    """从源壳 index.html 抽 <div class="actions"> … </header> 整块（顶栏右侧唯一来源）"""
    i = src.find('<div class="actions"')
    j = src.find('</header>', i)
    if i < 0 or j < 0:
        raise SystemExit('!! 源壳缺 actions/header 锚点')
    return src[i:j]


def sync_actions(s, block, name):
    """把源壳的 actions 块整块替换进目标壳（幂等：内容相同则跳过）"""
    i = s.find('<div class="actions"')
    j = s.find('</header>', i)
    if i < 0 or j < 0:
        print('    [WARN] %s 缺 actions 锚点，跳过' % name)
        return s, False
    if s[i:j] == block:
        return s, True
    return s[:i] + block + s[j:], True


def block_by_depth(s, start_marker, tag='div'):
    """按标签嵌套深度取整块（从 start_marker 到与之配对的闭合标签），返回 (块, 起, 止)"""
    i = s.find(start_marker)
    if i < 0:
        return None, -1, -1
    j = s.find('>', i)
    if j < 0:
        return None, -1, -1
    depth, k = 1, j + 1
    open_re = re.compile(r'<' + tag + r'\b', re.I)
    close_re = re.compile(r'</' + tag + r'>', re.I)
    while depth > 0:
        no, nc = open_re.search(s, k), close_re.search(s, k)
        if not nc:
            return None, -1, -1
        if no and no.start() < nc.start():
            depth += 1
            k = no.end()
        else:
            depth -= 1
            k = nc.end()
    return s[i:k], i, k


NAV_BLOCKS = [
    ('<nav class="module-tabs" id="moduleTabs"', 'nav'),
    ('<nav class="m-tabbar" id="mTabbar"', 'nav'),
    ('<div class="m-sheet" id="mSheet"', 'div'),
]


def sync_nav_blocks(s, src, name):
    """顶栏页签 / 底部 TabBar / 更多面板 三块整块以 index.html 为唯一来源同步"""
    ok = 0
    for marker, tag in NAV_BLOCKS:
        blk, _, _ = block_by_depth(src, marker, tag)
        cur, i, j = block_by_depth(s, marker, tag)
        if blk is None or cur is None:
            print('    [WARN] %s 缺 %s 锚点，跳过' % (name, marker[:32]))
            continue
        if cur == blk:
            ok += 1
            continue
        if len(blk) > 20000 or len(cur) > 20000:
            print('    [WARN] %s %s 段长度异常，跳过' % (name, marker[:32]))
            continue
        s = s[:i] + blk + s[j:]
        ok += 1
    return s, ok


def main():
    check_only = '--check' in sys.argv
    src_full = read(os.path.join(BASE, 'index.html'))
    src_actions = extract_actions(src_full)
    nav_block = build_nav()
    for name in ['index.html', '_gzip_build.py', '_build_4in1.py']:
        p = os.path.join(BASE, name)
        s = read(p)
        before = len(s)
        s = inject_css(s, name)
        s, keep_n = reorder_nav(s, nav_block)
        s, btn_n = drop_packs_button(s)
        s, md_n = drop_packs_modal(s)
        s, gated = gate_packs_poll(s)
        s, act_ok = sync_actions(s, src_actions, name)
        s, nav_ok = sync_nav_blocks(s, src_full, name)
        if not check_only:
            write(p, s)
        print('  %-18s css+%d 页签重排=%s 删按钮=%d 删弹窗=%d 停轮询=%s actions=%s nav块=%s  (%d -> %d)'
              % (name, len(NEW_CSS), keep_n, btn_n, md_n, gated, act_ok, nav_ok, before, len(s)))
    print('壳层同步完成（幂等）。')


if __name__ == '__main__':
    main()
