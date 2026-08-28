# -*- coding: utf-8 -*-
"""全量 JS 语法校验：提取各 html 的 <script> 块拼接后 node --check（M1-M3 全源 + 产物）"""
import io, re, subprocess, os, shutil

FILES = [
    u'index.html',
    u'qa.html',
    u'quiz.html',
    u'performance.html',
    u'beauty.html',
    u'medical.html',
    u'daily.html',
    u'manual.html',
    u'report.html',
    u'risk-lite.html',
    u'kb-admin.template.html',
    u'kb-admin.html',
    u'spring-assistant.html',
    u'客舱小助手（离线完整版）.html',
]
node = shutil.which('node')
if not node:
    print('NODE_NOT_FOUND')
else:
    for p in FILES:
        if not os.path.exists(p):
            print(os.path.basename(p), '->', 'NO_FILE')
            continue
        s = io.open(p, encoding='utf-8', newline='').read()
        parts = re.findall(r'<script[^>]*>(.*?)</script>', s, re.S)
        js = '\n;\n'.join(parts)
        tmp = u'__check_tmp.js'
        with io.open(tmp, 'w', encoding='utf-8') as f:
            f.write(js)
        cmd = [node, '--check', tmp]
        r = subprocess.run(cmd, capture_output=True, text=True)
        print(os.path.basename(p), '->', 'OK' if r.returncode == 0 else 'SYNTAX_ERR')
        if r.returncode != 0:
            print(r.stderr[:1500])
        try:
            os.remove(u'__check_tmp.js')
        except OSError:
            pass