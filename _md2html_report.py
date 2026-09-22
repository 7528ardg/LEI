# -*- coding: utf-8 -*-
"""Markdown 报告 → 单文件 HTML（离线可开、浅/深双主题、自带目录）

用法：
  python _md2html_report.py <src.md> [dst.html] [--title "标题"] [--sub "副标题"]
  省略 dst 时输出同名 .html

覆盖的 Markdown 子集（本仓库报告实际用到的全部语法）：
  #/##/###/#### 标题 · 段落 · **粗体** · `行内码` · ``` 代码块 ```
  -/1. 列表（含一层嵌套）· 引用 > · 表格（含 |---| 分隔行）· --- 分隔线
设计约束：
  - 单文件、零外链（不引任何 CDN），双击即可看；
  - 浅色为主，`prefers-color-scheme: dark` 自动切深色；
  - 表格超宽时横向滚动，不撑破页面。
"""
from __future__ import annotations

import html as _h
import os
import re
import sys

CSS = """
:root{
  --bg:#F6F8F7; --card:#FFFFFF; --text:#10231A; --text2:#4E6459; --text3:#8CA096;
  --border:#E2EAE6; --accent:#148453; --accent-soft:#E8F3EE;
  --warn:#B45309; --warn-soft:#FEF3C7; --danger:#C2410C; --danger-soft:#FEE7DE;
  --code-bg:#F2F5F3; --shadow:0 1px 3px rgba(16,35,26,.06),0 8px 24px rgba(16,35,26,.05);
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#0E1713; --card:#151F1A; --text:#E6F0EA; --text2:#9FB5A9; --text3:#6B8076;
    --border:#20302A; --accent:#4CC38A; --accent-soft:#152A20;
    --warn:#F0B429; --warn-soft:#2C2410; --danger:#F87171; --danger-soft:#331914;
    --code-bg:#111B16; --shadow:0 1px 3px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.35);
  }
}
*{box-sizing:border-box;}
body{margin:0;background:var(--bg);color:var(--text);
  font:15px/1.75 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;}
.wrap{max-width:1080px;margin:0 auto;padding:32px 20px 72px;}
header.hero{background:var(--card);border:1px solid var(--border);border-radius:16px;
  padding:26px 28px;box-shadow:var(--shadow);margin-bottom:24px;}
header.hero h1{margin:0 0 6px;font-size:26px;letter-spacing:.2px;}
header.hero .sub{color:var(--text2);font-size:14px;}
main{background:var(--card);border:1px solid var(--border);border-radius:16px;
  padding:8px 28px 32px;box-shadow:var(--shadow);}
h1,h2,h3,h4{line-height:1.35;}
main h1{font-size:24px;margin:26px 0 12px;}
main h2{font-size:20px;margin:32px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--border);}
main h3{font-size:17px;margin:24px 0 10px;}
main h4{font-size:15px;margin:18px 0 8px;color:var(--text2);}
p{margin:10px 0;}
a{color:var(--accent);}
ul,ol{margin:10px 0;padding-left:24px;}
li{margin:5px 0;}
li>ul,li>ol{margin:5px 0;}
code{background:var(--code-bg);border:1px solid var(--border);border-radius:5px;
  padding:1px 5px;font:13px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  word-break:break-word;}
pre{background:var(--code-bg);border:1px solid var(--border);border-radius:10px;
  padding:14px 16px;overflow:auto;}
pre code{background:none;border:none;padding:0;font-size:13px;white-space:pre;}
blockquote{margin:14px 0;padding:10px 16px;border-left:3px solid var(--accent);
  background:var(--accent-soft);border-radius:0 10px 10px 0;color:var(--text2);}
hr{border:none;border-top:1px solid var(--border);margin:28px 0;}
.tablewrap{overflow-x:auto;margin:14px 0;}
table{border-collapse:collapse;width:100%;font-size:14px;}
th,td{border:1px solid var(--border);padding:8px 11px;text-align:left;vertical-align:top;}
th{background:var(--accent-soft);font-weight:600;white-space:nowrap;}
tbody tr:nth-child(even){background:rgba(128,128,128,.04);}
strong{font-weight:600;}
.toc{background:var(--card);border:1px solid var(--border);border-radius:16px;
  padding:16px 24px;box-shadow:var(--shadow);margin-bottom:24px;}
.toc h2{margin:0 0 8px;font-size:15px;color:var(--text2);border:none;padding:0;}
.toc ol{margin:0;padding-left:20px;columns:2;column-gap:28px;}
.toc a{text-decoration:none;font-size:14px;color:var(--text);}
.toc a:hover{color:var(--accent);}
@media(max-width:640px){.toc ol{columns:1;}main{padding:4px 18px 24px;}.wrap{padding:20px 12px 56px;}}
"""


def esc(t: str) -> str:
    return _h.escape(t, quote=False)


def inline(t: str) -> str:
    """行内：先转义，再还原 **粗体** / `行内码` / 链接（裸 URL 不动）。"""
    t = esc(t)
    out, i, n = [], 0, len(t)
    while i < n:
        if t.startswith('**', i):
            j = t.find('**', i + 2)
            if j > 0:
                out.append('<strong>' + t[i + 2:j] + '</strong>')
                i = j + 2
                continue
        if t[i] == '`':
            j = t.find('`', i + 1)
            if j > 0:
                out.append('<code>' + t[i + 1:j] + '</code>')
                i = j + 1
                continue
        out.append(t[i])
        i += 1
    return ''.join(out)


def slug(s: str) -> str:
    s = re.sub(r'[^\w\u4e00-\u9fa5]+', '-', s).strip('-').lower()
    return 'h-' + (s[:48] or 'sec')


def convert(md: str) -> tuple[str, list]:
    lines = md.split('\n')
    out: list[str] = []
    toc: list[tuple[int, str, str]] = []
    i, n = 0, len(lines)

    while i < n:
        ln = lines[i]
        s = ln.strip()

        # 代码块
        if s.startswith('```'):
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith('```'):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append('<pre><code>' + esc('\n'.join(buf)) + '</code></pre>')
            continue

        # 表格
        if s.startswith('|') and i + 1 < n and re.match(r'^\|[\s:\-|]+\|$', lines[i + 1].strip()):
            rows = []
            while i < n and lines[i].strip().startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            head, body = rows[0], rows[2:]
            out.append('<div class="tablewrap"><table><thead><tr>'
                       + ''.join('<th>' + inline(c) + '</th>' for c in head)
                       + '</tr></thead><tbody>')
            for r in body:
                out.append('<tr>' + ''.join('<td>' + inline(c) + '</td>' for c in r) + '</tr>')
            out.append('</tbody></table></div>')
            continue

        # 标题
        m = re.match(r'^(#{1,4})\s+(.*)$', s)
        if m:
            lvl, title = len(m.group(1)), m.group(2)
            sid = slug(title)
            if lvl == 1:
                out.append('<h1 id="' + sid + '">' + inline(title) + '</h1>')
            else:
                out.append('<h%d id="%s">%s</h%d>' % (lvl, sid, inline(title), lvl))
                if lvl == 2:
                    toc.append((lvl, title, sid))
            i += 1
            continue

        # 分隔线
        if re.match(r'^(-{3,}|\*{3,}|_{3,})$', s):
            out.append('<hr>')
            i += 1
            continue

        # 引用
        if s.startswith('>'):
            buf = []
            while i < n and lines[i].strip().startswith('>'):
                buf.append(lines[i].strip().lstrip('>').strip())
                i += 1
            out.append('<blockquote>' + '<br>'.join(inline(x) for x in buf) + '</blockquote>')
            continue

        # 列表
        if re.match(r'^\s*([-*+]|\d+\.)\s+', ln):
            ordered = bool(re.match(r'^\s*\d+\.\s+', ln))
            tag = 'ol' if ordered else 'ul'
            items: list[tuple[int, str]] = []
            while i < n and re.match(r'^\s*([-*+]|\d+\.)\s+', lines[i]):
                cur = lines[i]
                indent = len(cur) - len(cur.lstrip())
                text = re.sub(r'^\s*([-*+]|\d+\.)\s+', '', cur)
                items.append((indent, text))
                i += 1
            base = min(x[0] for x in items)
            buf, open_sub = ['<%s>' % tag], False
            for ind, text in items:
                if ind > base and not open_sub:
                    buf.append('<%s>' % tag)
                    open_sub = True
                elif ind <= base and open_sub:
                    buf.append('</%s>' % tag)
                    open_sub = False
                buf.append('<li>' + inline(text) + '</li>')
            if open_sub:
                buf.append('</%s>' % tag)
            buf.append('</%s>' % tag)
            out.append(''.join(buf))
            continue

        # 空行
        if not s:
            i += 1
            continue

        # 段落（连续非空行合并）
        buf = []
        while i < n and lines[i].strip() and not re.match(
                r'^(#{1,4}\s|\s*([-*+]|\d+\.)\s|>|\||```)', lines[i]):
            buf.append(lines[i].strip())
            i += 1
        out.append('<p>' + '<br>'.join(inline(x) for x in buf) + '</p>')
        continue

    return '\n'.join(out), toc


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = {}
    for a in sys.argv[1:]:
        if a.startswith('--'):
            k, _, v = a[2:].partition('=')
            opts[k] = v
    if not args:
        print(__doc__)
        return 2
    src = args[0]
    dst = args[1] if len(args) > 1 else os.path.splitext(src)[0] + '.html'
    md = open(src, encoding='utf-8').read()

    title = opts.get('title')
    if not title:
        m = re.search(r'^#\s+(.+)$', md, re.M)
        title = m.group(1).strip() if m else os.path.basename(src)
    sub = opts.get('sub', '')

    body, toc = convert(md)
    toc_html = ''
    if len(toc) >= 3:
        toc_html = ('<nav class="toc"><h2>目录</h2><ol>'
                    + ''.join('<li><a href="#%s">%s</a></li>' % (sid, inline(t)) for _, t, sid in toc)
                    + '</ol></nav>')

    html = ('<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            '<title>' + esc(title) + '</title>\n<style>' + CSS + '</style>\n</head>\n<body>\n'
            '<div class="wrap">\n<header class="hero"><h1>' + inline(title) + '</h1>'
            + ('<div class="sub">' + inline(sub) + '</div>' if sub else '')
            + '</div>\n' + toc_html + '<main>\n' + body + '\n</main>\n</div>\n</body>\n</html>\n')

    with open(dst, 'w', encoding='utf-8', newline='') as f:
        f.write(html)
    print('OK  %s -> %s  (%d 字符, 目录 %d 项)' % (os.path.basename(src), os.path.basename(dst), len(html), len(toc)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
