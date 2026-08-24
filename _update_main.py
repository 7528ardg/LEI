# -*- coding: utf-8 -*-
"""将 _work 中修改后的系统重新封装回主文件（仅替换 quiz/beauty，performance 保持不变）"""
import base64
import io
import os

MAIN = u'春秋·广州分队全能助手.html'
SOURCES = {
    'quiz': u'_work\\广州刷题.html',
    'beauty': u'_work\\美妆销售话术生成系统.html',
}

def read(path, binary=False):
    mode = 'rb' if binary else 'r'
    with io.open(path, mode, encoding=None if binary else 'utf-8') as f:
        return f.read()

def write(path, content):
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    s = read(MAIN)
    start = s.index('const MODULES = {')
    end = s.index('/* ===================== 解码引擎', start)
    block = s[start:end]
    for key, src in SOURCES.items():
        raw = read(src, binary=True)
        b64 = base64.b64encode(raw).decode('ascii')
        marker = '{}: "'.format(key)
        i = block.index(marker) + len(marker)
        j = block.index('"', i)
        old = block[i:j]
        block = block[:i] + b64 + block[j:]
        print('updated', key, '{:.2f} MB'.format(len(raw)/1024.0**2), 'len b64', len(b64))
    s = s[:start] + block + s[end:]
    write(MAIN, s)
    print('saved', os.path.getsize(MAIN))

if __name__ == '__main__':
    main()