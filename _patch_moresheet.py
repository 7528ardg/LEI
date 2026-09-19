# -*- coding: utf-8 -*-
"""修复 _moreSheetInst 未定义：closeMoreSheet 读未声明变量 → ReferenceError（resize 触发）
单一来源 index.html，改后由 _sync_shell_js.py 同步到两模板。
用法：python _patch_moresheet.py [--check]
"""
import io, os, sys
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, 'index.html')


def main():
    check = '--check' in sys.argv
    s = io.open(INDEX, encoding='utf-8', newline='').read()
    anchor = 'function closeMoreSheet(){'
    decl = 'var _moreSheetInst = null;\nfunction closeMoreSheet(){'
    if s.find(anchor) < 0:
        raise SystemExit('!! 未找到 closeMoreSheet')
    applied = s.count(decl) > 0
    if check:
        print('  _moreSheetInst 声明:', 'OK' if applied else 'MISSING')
        sys.exit(0 if applied else 1)
    if applied:
        print('  index.html -> UP-TO-DATE'); return
    s = s.replace(anchor, decl, 1)
    io.open(INDEX, 'w', encoding='utf-8', newline='').write(s)
    print('  index.html 已补声明（closeMoreSheet 前）')


if __name__ == '__main__':
    main()