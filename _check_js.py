# -*- coding: utf-8 -*-
import io, re, subprocess, os, shutil

FILES = [
    u'_work\\美妆销售话术生成系统.html',
    u'_work\\广州刷题.html',
    u'_work\\广州综合绩效评定测试系统1.0(3).html',
    u'春秋·广州分队全能助手.html',
]
node = shutil.which('node')
if not node:
    print('NODE_NOT_FOUND')
else:
    for p in FILES:
        s = io.open(p, encoding='utf-8', newline='').read()
        parts = re.findall(r'<script[^>]*>(.*?)</script>', s, re.S)
        js = '\n;\n'.join(parts)
        tmp = u'_work\\__check_tmp.js'
        with io.open(tmp, 'w', encoding='utf-8') as f:
            f.write(js)
        r = subprocess.run([node, '--check', tmp], capture_output=True, text=True)
        print(os.path.basename(p), '->', 'OK' if r.returncode == 0 else 'SYNTAX_ERR')
        if r.returncode != 0:
            print(r.stderr[:1500])
    try:
        os.remove(u'_work\\__check_tmp.js')
    except OSError:
        pass