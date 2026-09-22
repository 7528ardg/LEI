# -*- coding: utf-8 -*-
"""将 docs/_fullpack_engine.js「全量数据包引擎」注入 kb-admin.template.html（单一来源，杜绝手抄漂移）

背景：库管理要把「六库 + 话术库 + 产品库」导出成完整数据包，并在导入后验证
      「能被正确识别 + 完整还原」。校验逻辑若与运行时两份实现，必然漂移，
      故与 PACKS 引擎同套路：引擎单一来源在 docs/，由本脚本注入，
      Node 侧构建校验直接 require 同一份文件。

用法：
    python _sync_fullpack.py            # 注入/更新（幂等：有块替换，无块在 </head> 前插入）
    python _sync_fullpack.py --check    # 校验内嵌引擎与源一致（CI 用，退出码 1 表示不一致）
    python _sync_fullpack.py --remove   # 移出注入块（回滚）

标记位约定（沿用 __PAKO_SRC__ 教训：注入点只能是独立注入点，不得出现在注释文本中）：
    //__FULLPACK_ENGINE_START__
    <引擎源码>
    //__FULLPACK_ENGINE_END__
块以 <script> 包裹，插在 </head> 之前，保证 body 内消费代码执行时 FULLPACK 已定义。
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE_SRC = os.path.join(HERE, 'docs', '_fullpack_engine.js')
TARGETS = [
    u'kb-admin.template.html',
]
BLOCK_START = u'//__FULLPACK_ENGINE_START__'
BLOCK_END = u'//__FULLPACK_ENGINE_END__'
HEAD_TAG = u'</head>'


def build_block(src):
    return (u'<script>\n'
            u'/* 客舱小助手全量数据包引擎（_sync_fullpack.py 自动注入；改 docs/_fullpack_engine.js 后重跑 python _sync_fullpack.py） */\n'
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


def find_head_anchor(s):
    """定位「真正的」</head>（与 _sync_packs.py 同口径）.

    不能用 s.find(HEAD_TAG)：单文件模块里可能有第二处 </head> 出现在 JS 模板字符串中。
    判别：</head> 之后只允许水平空白 + 换行 + <body。
    """
    cands = [m.start() for m in re.finditer(r'</head>', s, re.I)
             if re.match(r'[ \t]*\r?\n[ \t]*<body', s[m.end():m.end() + 40], re.I)]
    if cands:
        return cands[-1]
    return s.rfind(HEAD_TAG)


def read_text(p):
    with io.open(p, encoding='utf-8', newline='') as f:
        return f.read()


def sync_file(path, src):
    s = read_text(path)
    block = build_block(src)
    loc = locate_block(s)
    if loc:
        s = s[:loc[0]] + block + s[loc[1]:]
        act = u'替换'
    else:
        head = find_head_anchor(s)
        if head == -1:
            raise ValueError(u'未找到 </head>，无法确定注入位置：' + path)
        s = s[:head] + block + s[head:]
        act = u'注入'
    tmp = path + '.tmp_write'   # 原子写：异常不再把源文件截成半截
    with io.open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(s)
    os.replace(tmp, path)
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
    cur = m.group(1).replace(u'\r', u'').strip()
    src_norm = src.replace(u'\r', u'').strip()
    return u'OK' if cur == src_norm else u'STALE'


def remove_file(path):
    s = read_text(path)
    si = s.find(BLOCK_START)
    if si == -1:
        return False
    ei = s.rfind(BLOCK_END) + len(BLOCK_END)
    script_open = s.rfind(u'<script>', 0, si)
    script_close = s.find(u'</script>', ei)
    if script_open == -1 or script_close == -1:
        raise ValueError(u'回滚失败：标记未包裹在 script 内，需人工处理：' + path)
    s = s[:script_open] + s[script_close + len(u'</script>'):]
    # B1：原子写（tmp_write + os.replace），回滚时也不应把模板截成半截
    tmp = path + '.tmp_write'
    with io.open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(s)
    os.replace(tmp, path)
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
                print(u'%s -> %s' % (t, u'REMOVED' if remove_file(path) else u'NO_BLOCK'))
            else:
                print(u'%s -> %s OK' % (t, sync_file(path, src)))
        except ValueError as e:
            print(u'%s -> ERROR: %s' % (t, e))
            ok = False
    if mode == u'check' and not ok:
        sys.exit(1)


if __name__ == '__main__':
    main()
