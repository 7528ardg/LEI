# -*- coding: utf-8 -*-
"""同步 qa.html 的 qaTalkEngine = beauty.html 最新 talkShowEngine（幂等，只替换引擎块）
用法：python _sync_qa_talk_engine.py [--check]
"""
import io, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
BEAUTY = os.path.join(HERE, 'beauty.html')
QA = os.path.join(HERE, 'qa.html')

def read(p):
    return io.open(p, encoding='utf-8', newline='').read()

def extract_beauty_engine(beauty):
    st = beauty.index('const talkShowEngine = (function(){')
    en = beauty.index('window.talkShowEngine = talkShowEngine;') + len('window.talkShowEngine = talkShowEngine;')
    src = beauty[st:en]
    src = src.replace('talkShowEngine', 'qaTalkEngine')
    src = src.replace('beautySceneEngine.complianceClean', 'qaComplianceClean')
    assert 'const qaTalkEngine' in src and 'qaComplianceClean' in src
    return src

def newline_of(s):
    return '\r\n' if '\r\n' in s else '\n'

def main():
    check = '--check' in sys.argv
    beauty = read(BEAUTY)
    qa = read(QA)
    new_engine = extract_beauty_engine(beauty)
    nl = newline_of(qa)
    new_engine = new_engine.replace('\r\n', '\n').replace('\n', nl)

    st = qa.find('const qaTalkEngine = (function(){')
    if st < 0:
        raise SystemExit('!! qa.html 未找到 qaTalkEngine 起始')
    en = qa.find('window.qaTalkEngine = qaTalkEngine;', st)
    if en < 0:
        raise SystemExit('!! qa.html 未找到 qaTalkEngine 结束')
    en += len('window.qaTalkEngine = qaTalkEngine;')
    old = qa[st:en]
    if old == new_engine:
        print('  qa.html qaTalkEngine -> UP-TO-DATE')
        return
    print('  qa.html qaTalkEngine 替换 %d -> %d chars' % (len(old), len(new_engine)))
    if not check:
        io.open(QA, 'w', encoding='utf-8', newline='').write(qa[:st] + new_engine + qa[en:])
        print('  qa.html 已写入')
    else:
        print('  !! 不一致（--check 模式不落盘）')
        sys.exit(1)

if __name__ == '__main__':
    main()