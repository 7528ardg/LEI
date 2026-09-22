# -*- coding: utf-8 -*-
"""校验在线版瘦壳：MODULES 已置空、fetch 逻辑存在、JS 语法通过、mods 可解压（2026-09-21 重写）

改动点：
  1) 「已置空」不再用 s.count('""') >= 10 这种脆弱启发式，改为用与 _build_hosted.py 完全相同的
     B64_LINE 正则判定「是否还有 ≥120 字符的模块 base64 残留」；
  2) 补退出码：任何一项失败即非零退出，可被 _build_all 阻断（原先只 print，永远是成功）；
  3) 文件缺失/解压失败按 FAIL 处理而不是抛异常中断；
  4) 临时 JS 用 with + newline='' 写，句柄不泄漏。
"""
import gzip, io, os, re, subprocess, sys, tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, u'在线版')
QUIET = '--quiet' in sys.argv
names = [u'客舱小助手（在线版）.html', u'客舱小助手（离线完整版-在线部署）.html']

# 与 _build_hosted.B64_LINE 同源口径：key: "长base64"
B64_LINE = re.compile(
    r'^([ \t]*(?:qa|quiz|performance|beauty|medical|risk|daily|manual|report|kbadmin|issues|home)\s*:\s*)'
    r'"[A-Za-z0-9+/=]{120,}"', re.MULTILINE)

fails = []


def check(label, ok, extra=''):
    if not ok:
        fails.append(label)
    if not QUIET or not ok:
        print('  %-28s %s %s' % (label, 'OK' if ok else 'FAIL', extra))


def rd(p):
    with io.open(p, encoding='utf-8', newline='') as f:
        return f.read()


for name in names:
    p = os.path.join(OUT, name)
    print(name)
    if not os.path.exists(p):
        check(u'瘦壳存在', False, p)
        continue
    s = rd(p)
    check(u'模块 base64 已置空', B64_LINE.search(s) is None,
          '' if B64_LINE.search(s) is None else '仍残留 %d 处' % len(B64_LINE.findall(s)))
    check(u'fetch 逻辑在位', '_fetchModule' in s and "caches.open('kz-mod-v1')" in s)
    check(u'mods 路径在位', "'./mods/' + id + '.gz'" in s)
    check(u'预取逻辑在位', 'var hasEmbed' in s)
    js = '\n;\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', s, re.S))
    fd, tmp = tempfile.mkstemp(suffix='.js', prefix='__online_shell_check_')
    os.close(fd)
    try:
        with io.open(tmp, 'w', encoding='utf-8', newline='') as f:
            f.write(js)
        r = subprocess.run(['node', '--check', tmp], capture_output=True, text=True)
        check(u'内联 JS 语法', r.returncode == 0, '' if r.returncode == 0 else r.stderr[:400])
    except FileNotFoundError:
        check(u'内联 JS 语法', False, 'node 不可用，已跳过')
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

mods_dir = os.path.join(OUT, 'mods')
print('== mods 抽查解压 ==')
for fn in ['qa.gz', 'beauty.gz', 'kbadmin.gz']:
    fp = os.path.join(mods_dir, fn)
    if not os.path.exists(fp):
        check(u'mods/%s 可解压' % fn, False, '文件缺失')
        continue
    try:
        with io.open(fp, 'rb') as f:
            raw = gzip.decompress(f.read())
        # 2026-09-21：预览用 'replace' 而非 'ignore' —— 非法字节会显示成 U+FFFD，
        # 不至于被静默吞掉后看不出异常。
        head = raw.decode('utf-8', 'replace')[:46].replace('\n', ' ')
        check(u'mods/%s 可解压' % fn, len(raw) > 1000, '%d bytes | %s' % (len(raw), head))
    except Exception as e:
        check(u'mods/%s 可解压' % fn, False, str(e)[:120])

print('SUMMARY: %d 项失败' % len(fails))
raise SystemExit(1 if fails else 0)
