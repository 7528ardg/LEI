# -*- coding: utf-8 -*-
"""在线部署包构建：产出「瘦壳 + mods/*.gz」的静态托管版（GitHub Pages 等）

原理：离线单文件把所有模块 gzip-base64 内嵌进 HTML（5~6MB，首屏下载慢）。
在线版把内嵌数据全部置空，外壳改为按需 fetch './mods/<id>.gz' + Cache API 缓存，
首屏只需下载几百 KB 的瘦壳，之后切页签按需加载并缓存（二次打开/离线命中缓存）。

用法：python _build_hosted.py
产物：
  在线版/客舱小助手（在线版）.html              —— 9 模块瘦壳（qa..kbadmin）
  在线版/客舱小助手（离线完整版-在线部署）.html —— 10 模块瘦壳（含 risk）
  在线版/mods/*.gz                              —— 各模块 gzip 压缩文件（与瘦壳同目录部署）
"""
import gzip, io, os, re, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, u'在线版')
MODS_DIR = os.path.join(OUT_DIR, u'mods')

MODULES = ['qa', 'quiz', 'performance', 'beauty', 'medical', 'daily', 'manual', 'report', 'kbadmin']
MODULES_4IN1 = ['qa', 'quiz', 'performance', 'beauty', 'medical', 'risk', 'daily', 'manual', 'report', 'kbadmin']
SRC = {
    'qa': u'qa.html', 'quiz': u'quiz.html', 'performance': u'performance.html',
    'beauty': u'beauty.html', 'medical': u'medical.html', 'risk': u'risk-lite.html',
    'daily': u'daily.html', 'manual': u'manual.html', 'report': u'report.html',
    'kbadmin': u'kb-admin.html',
}

# 匹配 MODULES 对象里形如  "  key: "H4sI...很长的base64...", "  的整行，把 base64 置空
B64_LINE = re.compile(r'^[ \t]*((?:qa|quiz|performance|beauty|medical|risk|daily|manual|report|kbadmin)\s*:\s*)"[A-Za-z0-9+/=]{120,}"[,]?\s*$', re.MULTILINE)


def strip_modules(html):
    def rep(m):
        tail = ',' if m.group(0).rstrip().endswith(',') else ''
        return m.group(1) + '""' + tail
    return B64_LINE.sub(rep, html)


def build_mods():
    os.makedirs(MODS_DIR, exist_ok=True)
    names = []
    for key, fn in SRC.items():
        if not os.path.exists(os.path.join(BASE, fn)):
            continue
        raw = io.open(os.path.join(BASE, fn), encoding='utf-8').read()
        gz = gzip.compress(raw.encode('utf-8'), 9)
        with io.open(os.path.join(MODS_DIR, key + '.gz'), 'wb') as f:
            f.write(gz)
        names.append((key, len(raw), len(gz)))
    return names


def main():
    # 1) 先构建标准嵌入式产物（在线版 shell 由其改造而来）
    subprocess.check_call([sys.executable, u'_gzip_build.py'], cwd=BASE)
    subprocess.check_call([sys.executable, u'_build_4in1.py'], cwd=BASE)

    os.makedirs(OUT_DIR, exist_ok=True)

    # 2) spring-assistant.html -> 9 模块瘦壳
    shell = io.open(os.path.join(BASE, u'spring-assistant.html'), encoding='utf-8').read()
    hosted = strip_modules(shell)
    out9 = os.path.join(OUT_DIR, u'客舱小助手（在线版）.html')
    with io.open(out9, 'w', encoding='utf-8') as f:
        f.write(hosted)

    # 3) 离线完整版 -> 10 模块瘦壳（含 risk）
    shell4 = io.open(os.path.join(BASE, u'客舱小助手（离线完整版）.html'), encoding='utf-8').read()
    hosted4 = strip_modules(shell4)
    out10 = os.path.join(OUT_DIR, u'客舱小助手（离线完整版-在线部署）.html')
    with io.open(out10, 'w', encoding='utf-8') as f:
        f.write(hosted4)

    # 4) mods/*.gz
    gzs = build_mods()

    print(u'== 产物 ==')
    for p in (out9, out10):
        print(u'  {}  {:.2f}MB'.format(os.path.basename(p), os.path.getsize(p) / 1048576.0))
    print(u'  mods/ 共 {} 个模块：'.format(len(gzs)))
    for key, raw, g in gzs:
        print(u'    {:<12} raw {:.2f}MB -> gz {:.2f}MB'.format(key + '.gz', raw / 1048576.0, g / 1048576.0))


if __name__ == '__main__':
    main()