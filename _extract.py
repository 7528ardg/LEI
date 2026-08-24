# -*- coding: utf-8 -*-
"""从融合主文件提取三大系统源码到 _work 目录"""
import base64
import io
import os

MAIN = u'春秋·广州分队全能助手.html'
WORK = u'_work'
os.makedirs(WORK, exist_ok=True)

SOURCES = {
    'quiz': u'广州刷题.html',
    'performance': u'广州综合绩效评定测试系统1.0(3).html',
    'beauty': u'美妆销售话术生成系统.html',
}

def read(path):
    with io.open(path, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    content = read(MAIN)
    start = content.index('const MODULES = {')
    end = content.index('/* ===================== 解码引擎', start)
    block = content[start:end]
    for key, outpath in SOURCES.items():
        marker = '{}: "'.format(key)
        i = block.index(marker) + len(marker)
        j = block.index('"', i)
        b64 = block[i:j]
        raw = base64.b64decode(b64)
        out = os.path.join(WORK, outpath)
        with io.open(out, 'w', encoding='utf-8') as f:
            f.write(raw.decode('utf-8'))
        print('提取 OK: {}  {:.2f} MB'.format(out, len(raw)/1024.0**2))

if __name__ == '__main__':
    main()