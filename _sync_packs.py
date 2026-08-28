# -*- coding: utf-8 -*-
"""将 docs/_packs_engine.js 数据包引擎注入到 4 个消费端源文件（单一来源，杜绝手抄漂移）

用法：
    python _sync_packs.py            # 注入/更新（幂等：有块替换，无块在 </head> 前插入）
    python _sync_packs.py --check    # 校验各文件内嵌引擎与源一致（CI 用，退出码 1 表示不一致）
    python _sync_packs.py --remove   # 移出注入块（回滚，用于测试）

标记位约定（沿用 __PAKO_SRC__ 教训：注入点只能是独立注入点，不得出现在注释文本中）：
    //__PACKS_ENGINE_START__
    <引擎源码>
    //__PACKS_ENGINE_END__
块以 <script> 包裹，插在 </head> 之前，保证 body 内任何消费代码执行时 PACKS 已定义。
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE_SRC = os.path.join(HERE, 'docs', '_packs_engine.js')
TARGETS = [
    u'qa.html',
    u'beauty.html',
    u'quiz.html',
    u'kb-admin.template.html',
]
BLOCK_START = u'//__PACKS_ENGINE_START__'
BLOCK_END = u'//__PACKS_ENGINE_END__'
HEAD_TAG = u'</head>'


def build_block(src):
    return (u'<script>\n'
            u'/* 客舱小助手数据包引擎（_sync_packs.py 自动注入；改 docs/_packs_engine.js 后重跑 python _sync_packs.py） */\n'
            + BLOCK_START + u'\n'
            + src.rstrip(u'\n') + u'\n'
            + BLOCK_END + u'\n'
            + u'</script>\n')


def locate_block(s):
    """返回 (start, end) 块区间（含前后 <script>…</script>），未找到返回 None；脏状态抛 ValueError"""
    si = s.find(BLOCK_START)
    ei = s.find(BLOCK_END)
    if si == -1 and ei == -1:
        return None
    if si == -1 or ei == -1:
        raise ValueError(u'标记位不完整（只存在一个标记），需人工处理')
    if ei < si:
        raise ValueError(u'标记位顺序异常（END 在 START 前），需人工处理')
    script_open = s.rfind(u'<script>', 0, si)
    script_close = s.find(u'</script>', ei)
    if script_open == -1 or script_close == -1:
        raise ValueError(u'标记位未包裹在 script 标签内，需人工处理')
    return (script_open, script_close + len(u'</script>'))


def read_text(p):
    return io.open(p, encoding='utf-8', newline='').read()


def sync_file(path, src):
    s = read_text(path)
    block = build_block(src)
    loc = locate_block(s)
    if loc:
        s = s[:loc[0]] + block + s[loc[1]:]
        act = u'替换'
    else:
        head = s.find(HEAD_TAG)
        if head == -1:
            raise ValueError(u'未找到 </head>，无法确定注入位置：' + path)
        s = s[:head] + block + s[head:]
        act = u'注入'
    io.open(path, 'w', encoding='utf-8', newline='').write(s)
    return act


def check_file(path, src):
    s = read_text(path)
    loc = locate_block(s)
    if not loc:
        return u'MISSING'
    inner = s[loc[0]:loc[1]]
    m = re.search(re.escape(BLOCK_START) + r'(.*?)' + re.escape(BLOCK_END), inner, re.S)
    if not m:
        return u'DIRTY'
    cur = m.group(1).strip()
    return u'OK' if cur == src.strip() else u'STALE'


def remove_file(path):
    s = read_text(path)
    m = re.search(re.escape(BLOCK_START) + r'[\s\S]*?' + re.escape(BLOCK_END), s)
    if not m:
        return False
    # 找到包裹该标记的最外层 <script>…</script> 一并删除
    si = s.find(BLOCK_START)
    ei = s.rfind(BLOCK_END) + len(BLOCK_END)
    script_open = s.rfind(u'<script>', 0, si)
    script_close = s.find(u'</script>', ei)
    if script_open == -1 or script_close == -1:
        raise ValueError(u'回滚失败：标记未包裹在 script 内，需人工处理：' + path)
    s = s[:script_open] + s[script_close + len(u'</script>'):]
    io.open(path, 'w', encoding='utf-8', newline='').write(s)
    return True


def main():
    mode = u'sync'
    if u'--check' in sys.argv:
        mode = u'check'
    elif u'--remove' in sys.argv:
        mode = u'remove'
    src = read_text(ENGINE_SRC)
    ok = True
    for t in TARGETS:
        path = os.path.join(HERE, t)
        try:
            if mode == u'check':
                st = check_file(path, src)
                print(u'%s -> %s' % (t, st))
                if st != u'OK':
                    ok = False
            elif mode == u'remove':
                removed = remove_file(path)
                print(u'%s -> %s' % (t, u'REMOVED' if removed else u'NO_BLOCK'))
            else:
                act = sync_file(path, src)
                print(u'%s -> %s OK' % (t, act))
        except ValueError as e:
            print(u'%s -> ERROR: %s' % (t, e))
            ok = False
    if mode == u'check' and not ok:
        sys.exit(1)


if __name__ == '__main__':
    main()