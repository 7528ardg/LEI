# -*- coding: utf-8 -*-
"""Markdown -> HTML（复用 exam_system/scripts/_md2html.py 的转换逻辑，仅换输入输出路径）"""
import os
import re
import html
import io

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '公网暴露方案_培训考核系统_20261012.md')
DST = os.path.join(HERE, '公网暴露方案_培训考核系统_20261012.html')


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    return s


def convert(md):
    out = []
    lines = md.split('\n')
    i = 0
    in_code = False
    in_ul = in_ol = False
    in_quote = False

    def close_lists():
        nonlocal in_ul, in_ol, in_quote
        if in_ul:
            out.append('</ul>'); in_ul = False
        if in_ol:
            out.append('</ol>'); in_ol = False
        if in_quote:
            out.append('</blockquote>'); in_quote = False

    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith('```'):
            if not in_code:
                close_lists(); out.append('<pre><code>'); in_code = True
            else:
                out.append('</code></pre>'); in_code = False
            i += 1
            continue
        if in_code:
            out.append(html.escape(ln))
            i += 1
            continue

        s = ln.strip()
        if s.startswith('|') and i + 1 < len(lines) and re.match(r'^\|[\s:\-|]+\|$', lines[i + 1].strip()):
            close_lists()
            header = [c.strip() for c in s.strip('|').split('|')]
            out.append('<div class="tw"><table><thead><tr>' + ''.join('<th>%s</th>' % inline(c) for c in header) + '</tr></thead><tbody>')
            i += 2
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                cells += [''] * (len(header) - len(cells))
                out.append('<tr>' + ''.join('<td>%s</td>' % inline(c) for c in cells[:len(header)]) + '</tr>')
                i += 1
            out.append('</tbody></table></div>')
            continue

        if not s:
            close_lists(); i += 1; continue

        m = re.match(r'^(#{1,6})\s+(.*)$', s)
        if m:
            close_lists()
            lvl = len(m.group(1))
            out.append('<h%d>%s</h%d>' % (lvl, inline(m.group(2)), lvl))
            i += 1; continue

        if re.match(r'^(-{3,}|\*{3,})$', s):
            close_lists(); out.append('<hr>'); i += 1; continue

        if s.startswith('> '):
            if not in_quote:
                close_lists(); out.append('<blockquote>'); in_quote = True
            out.append('<p>%s</p>' % inline(s[2:]))
            i += 1; continue

        m = re.match(r'^[-*]\s+(.*)$', s)
        if m:
            if in_ol:
                out.append('</ol>'); in_ol = False
            if not in_ul:
                out.append('<ul>'); in_ul = True
            out.append('<li>%s</li>' % inline(m.group(1)))
            i += 1; continue

        m = re.match(r'^\d+\.\s+(.*)$', s)
        if m:
            if in_ul:
                out.append('</ul>'); in_ul = False
            if not in_ol:
                out.append('<ol>'); in_ol = True
            out.append('<li>%s</li>' % inline(m.group(1)))
            i += 1; continue

        close_lists()
        out.append('<p>%s</p>' % inline(s))
        i += 1

    close_lists()
    if in_code:
        out.append('</code></pre>')
    return '\n'.join(out)


CSS = """
:root{--bg:#f6f8fa;--card:#fff;--tx:#1f2328;--tx2:#57606a;--bd:#d0d7de;--acc:#0969da;--ok:#1a7f37;--bad:#cf222e;--warn:#9a6700}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.72 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:32px 26px 80px}
h1{font-size:1.7rem;border-bottom:2px solid var(--bd);padding-bottom:12px;margin-top:8px}
h2{font-size:1.32rem;margin-top:40px;border-left:4px solid var(--acc);padding-left:12px;scroll-margin-top:20px}
h3{font-size:1.08rem;margin-top:28px;color:var(--tx2);scroll-margin-top:20px}
p,li{color:var(--tx)}
code{background:#eef1f4;border:1px solid var(--bd);border-radius:5px;padding:1px 5px;font:13px/1.5 "Cascadia Mono",Consolas,monospace;color:#7a2e0e}
pre{background:#0d1117;color:#e6edf3;padding:14px 16px;border-radius:10px;overflow:auto}
pre code{background:none;border:none;color:#e6edf3;padding:0;font-size:12.5px}
.tw{overflow-x:auto;margin:14px 0}
table{border-collapse:collapse;width:100%;background:var(--card);font-size:13.5px}
th,td{border:1px solid var(--bd);padding:7px 10px;text-align:left;vertical-align:top}
th{background:#eaeef2;font-weight:700;white-space:nowrap}
tbody tr:nth-child(even){background:#fafbfc}
blockquote{margin:14px 0;padding:10px 16px;background:#fff8e6;border-left:4px solid #d4a72c;color:#5c4a12}
blockquote p{margin:6px 0}
h1+h2{margin-top:22px}
ul,ol{padding-left:26px}
li{margin:4px 0}
hr{border:none;border-top:1px solid var(--bd);margin:30px 0}
@media print{body{background:#fff}.wrap{max-width:none}}
"""


def main():
    md = io.open(SRC, encoding='utf-8').read()
    body = convert(md)
    page = ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>局域网服务公网暴露 · 完整落地方案</title><style>%s</style></head>'
            '<body><div class="wrap">%s</div></body></html>' % (CSS, body))
    io.open(DST, 'w', encoding='utf-8').write(page)
    print('HTML ->', DST, os.path.getsize(DST), 'bytes')


if __name__ == '__main__':
    main()
