# -*- coding: utf-8 -*-
"""CBT 练习场景 · 数据同步（单一来源 docs/_cbt_kb.js → quiz.html 场景库第 10 大场景）

标记块：CBT_KB_BEGIN / CBT_KB_END，注入位置紧接大撤 DC_KB 块之后。

用法：python _sync_cbt.py            # 同步
      python _sync_cbt.py --check    # 校验（内容不一致则非零退出，供 _build_all 守护）
"""
import io, os, sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'docs', '_cbt_kb.js')
TARGET = os.path.join(HERE, 'quiz.html')

BEGIN = '/* CBT_KB_BEGIN（同步标记块，请勿在标记块外修改以下内容） */'
END = '/* CBT_KB_END（同步标记块结束） */'
ANCHOR = '/* DC_KB_END（同步标记块结束） */'


def payload():
    src = io.open(SRC, encoding='utf-8').read()
    i, j = src.find(BEGIN), src.find(END)
    if i < 0 or j < 0 or j < i:
        print('!! docs/_cbt_kb.js 缺少 CBT_KB_BEGIN/END 标记块'); sys.exit(1)
    return src[i:j + len(END)]


def main():
    check = '--check' in sys.argv
    s = io.open(TARGET, encoding='utf-8', newline='').read()
    want = payload()
    a, b = s.find(BEGIN), s.find(END)
    if a >= 0 and b > a:
        cur = s[a:b + len(END)]
        if cur == want:
            print('  quiz.html CBT场景 -> UP-TO-DATE'); return
        if check:
            print('!! quiz.html CBT场景 与 docs/_cbt_kb.js 不一致'); sys.exit(1)
        out = s[:a] + want + s[b + len(END):]
        act = '替换'
    else:
        if check:
            print('!! quiz.html 缺少 CBT_KB 标记块（需先运行 python _sync_cbt.py 植入）'); sys.exit(1)
        k = s.find(ANCHOR)
        if k < 0:
            print('!! quiz.html 未找到大撤 DC_KB_END 锚点，无法确定注入位置'); sys.exit(1)
        ins = k + len(ANCHOR)
        out = s[:ins] + '\n\n/* ===== CBT 练习场景（单一来源 docs/_cbt_kb.js，python _sync_cbt.py 同步） ===== */\n' + want + s[ins:]
        act = '注入'
    io.open(TARGET, 'w', encoding='utf-8', newline='').write(out)
    print(f'  quiz.html CBT场景 {act} {len(s)} -> {len(out)} bytes')


if __name__ == '__main__':
    main()
