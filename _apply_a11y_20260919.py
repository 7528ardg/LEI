# -*- coding: utf-8 -*-
"""可访问性与语义结构补丁（2026-09-19 · 设计审核 P0-C）。

背景（实测）：壳层 h1 = 0；qa / daily / manual / medical / report / kb-admin 六个模块
h1 也 = 0；全站无 skip-link、无 sr-only 工具类。屏幕阅读器无法按标题跳转，
键盘用户无法跳过顶栏直达内容。

本补丁做四件事（全部幂等：标记块 strip→replay）：
  1) 壳层（index.html / _gzip_build.py / _build_4in1.py）注入 sr-only + skip-link 样式
  2) 壳层注入 skip-link（指向既有 <main id="sysArea">）与屏幕阅读器可见的 h1
  3) 六个缺 h1 的模块各补 1 个 sr-only h1（只加语义，不改视觉）
  4) 给 <main id="sysArea"> 补 tabindex="-1"，使 skip-link 能真正移焦

刻意不做的事：不给模块硬塞凑数的 h2。quiz 的 14 个 <h1> 是「一视图一标题」的
SPA 结构，同时只有一个可见，不计为缺陷；beauty/performance/cc-home/issues 的 h1 已合规。

目标：index.html、_gzip_build.py、_build_4in1.py、qa/daily/manual/medical/report/kb-admin(.template)
用法：python _apply_a11y_20260919.py [--check]
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.abspath(__file__))

BEGIN = '<!--__A11Y_20260919__BEGIN__-->'
END = '<!--__A11Y_20260919__END__-->'
CSS_ID = 'a11y20260919'

CSS = (BEGIN + '\n<style id="%s">\n' % CSS_ID +
       '/* 2026-09-19 设计审核 P0-C：屏幕阅读器专用工具类 + 跳到主内容 */\n'
       '.a11y-sr{position:absolute!important;width:1px;height:1px;padding:0;margin:-1px;'
       'overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0;}\n'
       '.skip-link{position:absolute;left:8px;top:-64px;z-index:9999;background:var(--primary,#148453);'
       'color:#fff;padding:10px 16px;border-radius:0 0 10px 10px;font-size:.875rem;font-weight:700;'
       'font-family:var(--font-sans,sans-serif);text-decoration:none;transition:top .18s cubic-bezier(.23,1,.32,1);}\n'
       '.skip-link:focus{top:0;outline:2px solid #fff;outline-offset:-4px;}\n'
       '@media (prefers-reduced-motion:reduce){.skip-link{transition:none;}}\n'
       '</style>\n' + END + '\n')

SHELL_BODY = (BEGIN + '\n'
              '<a class="skip-link" href="#sysArea">跳到主要内容</a>\n'
              '<h1 class="a11y-sr">客舱小助手 · 客舱服务一线工具融合平台</h1>\n'
              + END + '\n')

# 需要补 h1 的模块（已合规者不在列：quiz 一视图一 h1、beauty/performance/cc-home/issues 已有）
MODULES = [
    ('qa.html', '你问我答 · 五库知识问答'),
    ('daily.html', '日常问题速查'),
    ('daily.template.html', '日常问题速查'),
    ('manual.html', '手册奖惩速查'),
    ('manual.template.html', '手册奖惩速查'),
    ('medical.html', '医疗急救速查'),
    ('report.html', '事件报告流程'),
    ('kb-admin.html', '知识库管理'),
    ('kb-admin.template.html', '知识库管理'),
]
SHELLS = ['index.html', '_gzip_build.py', '_build_4in1.py']


def read(p):
    with io.open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def write(p, s):
    s.encode('utf-8')
    tmp = p + '.tmp_write'
    with io.open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(s)
    os.replace(tmp, p)


def strip(s):
    """去掉本补丁此前注入的两类标记块（幂等基础）"""
    for b, e in ((CSS, None), (SHELL_BODY, None)):
        i = s.find(b)
        if i >= 0:
            s = s[:i] + s[i + len(b):]
    # 模块式 body 块（含模块 h1）
    s = re.sub(re.escape(BEGIN) + r'\n<h1 class="a11y-sr">[^<]*</h1>\n' + re.escape(END) + r'\n', '', s)
    return s


def head_anchor(s):
    """真正的 </head>：取 <body 之前的最后一个（performance 等文件内嵌字符串里还有 </head>）"""
    b = s.find('<body')
    if b < 0:
        raise SystemExit('!! 缺 <body 锚点')
    j = s.rfind('</head>', 0, b)
    if j < 0:
        raise SystemExit('!! 缺 </head> 锚点')
    return j


def body_anchor(s):
    m = re.search(r'<body[^>]*>', s)
    if not m:
        raise SystemExit('!! 缺 <body> 开标签')
    return m.end()


def inject_css(s):
    j = head_anchor(s)
    return s[:j] + CSS + s[j:]


def inject_shell_body(s):
    k = body_anchor(s)
    return s[:k] + '\n' + SHELL_BODY + s[k:]


def inject_module_h1(s, title):
    k = body_anchor(s)
    blk = BEGIN + '\n<h1 class="a11y-sr">%s</h1>\n' % title + END + '\n'
    return s[:k] + '\n' + blk + s[k:]


def main():
    check_only = '--check' in sys.argv
    print('可访问性补丁（幂等）：')

    # ---- 壳层：CSS + skip-link + h1 + <main tabindex> ----
    for name in SHELLS:
        p = os.path.join(BASE, name)
        if not os.path.exists(p):
            print('  [WARN] %s 不存在，跳过' % name)
            continue
        s0 = read(p)
        s = strip(s0)
        s = inject_css(s)
        s = inject_shell_body(s)
        # 2026-09-20 修复：tabindex="-1" 曾因前缀 replace 每次构建追加一份（最多堆到 11 份）。
        # 先清历史堆叠，再用「标签内尚无 tabindex」负向断言注入，保证幂等。
        import re as _re
        s = _re.sub(r'(id="sysArea")(?:\s+tabindex="-1")+', r'\1', s)
        s = _re.sub(r'(<main class="sys-area" id="sysArea")(?![^>]*tabindex=)',
                    r'\1 tabindex="-1"', s)
        n_main = s.count('<main class="sys-area" id="sysArea" tabindex="-1"')
        n_main2 = n_main
        if not check_only:
            write(p, s)
        ok = ('skip-link×%d h1×%d main-tabindex×%d' %
              (s.count('class="skip-link"'), s.count('<h1 class="a11y-sr">'), n_main2))
        print('  %-20s %s  (%d -> %d)' % (name, ok, len(s0), len(s)))

    # ---- 六个模块：sr-only h1 ----
    for name, title in MODULES:
        p = os.path.join(BASE, name)
        if not os.path.exists(p):
            print('  [WARN] %s 不存在，跳过' % name)
            continue
        s0 = read(p)
        s = strip(s0)
        s = inject_css(s)
        s = inject_module_h1(s, title)
        n = s.count('<h1 class="a11y-sr">%s</h1>' % title)
        if not check_only:
            write(p, s)
        print('  %-24s h1=%d  (%d -> %d)' % (name, n, len(s0), len(s)))

    print('完成。复核命令：python _apply_a11y_20260919.py --check')


if __name__ == '__main__':
    main()
