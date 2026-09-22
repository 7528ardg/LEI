# -*- coding: utf-8 -*-
"""把 docs/_date_match.js 注入 index.html / qa.html / beauty.html
用法：python _sync_date_match.py [--check]
单一来源原则：只改 docs/_date_match.js，再跑本脚本同步。
注入位置：紧跟 SEASON_ENGINE_END 之后（保证 DateMatch 能读到 SeasonEngine）；
          没有该标记时退化为各文件自己的锚点。
"""
import io, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
ENGINE = io.open(os.path.join(BASE, 'docs', '_date_match.js'), encoding='utf-8').read()
BEGIN = '/* ===== DATE_MATCH_BEGIN ===== */'
END = '/* ===== DATE_MATCH_END ===== */'
BLOCK = BEGIN + '\n' + ENGINE + '\n' + END

SEASON_END = '/* ===== SEASON_ENGINE_END ===== */'

# 文件 -> 退化锚点（无 SEASON_ENGINE_END 时插到锚点之前）
TARGETS = [
    ('index.html', '<script>\n(function(){'),
    ('qa.html', '<script>\n(function(){'),
    ('beauty.html', '        const products = ['),
]


def sync(fname, anchor):
    path = os.path.join(BASE, fname)
    src = io.open(path, encoding='utf-8').read()
    if BEGIN in src:
        b = src.index(BEGIN)
        e = src.index(END) + len(END)
        new = src[:b] + BLOCK + src[e:]
    else:
        if SEASON_END in src:
            i = src.index(SEASON_END) + len(SEASON_END)
            new = src[:i] + '\n' + BLOCK + src[i:]
        else:
            i = src.index(anchor)
            new = src[:i] + BLOCK + '\n' + src[i:]
    if new != src:
        io.open(path, 'w', encoding='utf-8', newline='').write(new)
        return True
    return False


if __name__ == '__main__':
    check = '--check' in sys.argv
    dirty = []
    for fname, anchor in TARGETS:
        try:
            changed = sync(fname, anchor)
        except ValueError:
            print('ANCHOR_MISSING', fname)
            dirty.append(fname)
            continue
        print(('WOULD_UPDATE ' if check else 'UPDATED ') if changed else 'OK ', fname)
        if changed:
            dirty.append(fname)
    if check and dirty:
        print('OUT_OF_SYNC:', dirty)
        sys.exit(1)
