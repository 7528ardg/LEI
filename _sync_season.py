# -*- coding: utf-8 -*-
"""把 docs/_season_engine.js 注入 index.html / qa.html / beauty.html
用法：python _sync_season.py [--check]
单一来源原则：只改 docs/_season_engine.js，再跑本脚本同步。
"""
import io, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
ENGINE = io.open(os.path.join(BASE, 'docs', '_season_engine.js'), encoding='utf-8').read()
BEGIN = '/* ===== SEASON_ENGINE_BEGIN ===== */'
END = '/* ===== SEASON_ENGINE_END ===== */'
BLOCK = BEGIN + '\n' + ENGINE + '\n' + END

# 文件 -> 锚点（插入到锚点之前）
TARGETS = [
    ('index.html', '<script>\n(function(){'),
    ('qa.html', '<script>\n(function(){'),
    ('beauty.html', '        const products = ['),
]


def find_anchor(src, anchor, fname):
    if anchor in src:
        return anchor
    # 退化：插到主 <script> 之后
    for probe in ['<script>', '<script>\n']:
        i = src.find(probe)
        if i >= 0:
            return probe
    raise RuntimeError('anchor not found in %s' % fname)


def sync(fname, anchor):
    path = os.path.join(BASE, fname)
    src = io.open(path, encoding='utf-8').read()
    anchor = find_anchor(src, anchor, fname)
    if BEGIN in src:
        b = src.index(BEGIN)
        e = src.index(END) + len(END)
        # 保留锚点位置：若锚点在块后，说明位置未变，直接替换内容
        new = src[:b] + BLOCK + src[e:]
    else:
        i = src.index(anchor)
        # 插到锚点所在 <script> 起始之后
        if anchor.startswith('<script>'):
            ins = i + len('<script>')
            new = src[:ins] + '\n' + BLOCK + '\n' + src[ins:]
        else:
            new = src[:i] + BLOCK + '\n' + src[i:]
    if new != src:
        io.open(path, 'w', encoding='utf-8', newline='').write(new)
        return True
    return False


if __name__ == '__main__':
    check = '--check' in sys.argv
    dirty = []
    for fname, anchor in TARGETS:
        changed = sync(fname, anchor)
        print(('WOULD_UPDATE ' if check else 'UPDATED ') if changed else 'OK ', fname)
        if changed:
            dirty.append(fname)
    if check and dirty:
        print('OUT_OF_SYNC:', dirty)
        sys.exit(1)
