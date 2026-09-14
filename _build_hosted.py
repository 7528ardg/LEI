# -*- coding: utf-8 -*-
"""在线部署包构建：产出「瘦壳 + mods/*.gz」的静态托管版（GitHub Pages 等）

原理：离线单文件把所有模块 gzip-base64 内嵌进 HTML（5~6MB，首屏下载慢）。
在线版把内嵌数据全部置空，外壳改为按需 fetch './mods/<id>.gz' + Cache API 缓存，
首屏只需下载几百 KB 的瘦壳，之后切页签按需加载并缓存（二次打开/离线命中缓存）。

用法：python _build_hosted.py
产物：
  在线版/客舱小助手（在线版）.html              —— 9 模块瘦壳（qa..kbadmin）
  在线版/客舱小助手（离线完整版-在线部署）.html —— 10 模块瘦壳（含 risk）
  在线版/mods/*.gz                              —— 各模块 gzip 压缩文件（与瘦壳同目录部署，http(s) 下按需 fetch + Cache API 缓存）
  在线版/mods/*.js                              —— 同内容的 base64(gzip) 脚本副本：供双击 file:// 打开时回退加载
                                                   （浏览器禁止 file:// 下 fetch，改用 <script> 注入；部署到服务器时可删）
  在线版/启动本地服务.bat                        —— 一键起 http 本地服务（推荐用法，功能最完整）
"""
import base64, gzip, io, os, re, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, u'在线版')
MODS_DIR = os.path.join(OUT_DIR, u'mods')

MODULES = ['qa', 'quiz', 'performance', 'beauty', 'medical', 'daily', 'manual', 'report', 'kbadmin', 'issues']
MODULES_4IN1 = ['qa', 'quiz', 'performance', 'beauty', 'medical', 'risk', 'daily', 'manual', 'report', 'kbadmin', 'issues']
SRC = {
    'qa': u'qa.html', 'quiz': u'quiz.html', 'performance': u'performance.html',
    'beauty': u'beauty.html', 'medical': u'medical.html', 'risk': u'risk-lite.html',
    'daily': u'daily.html', 'manual': u'manual.html', 'report': u'report.html',
    'kbadmin': u'kb-admin.html', 'issues': u'issues.html',
}

# 匹配 MODULES 对象里形如  "  key: "H4sI...很长的base64...", "  的整行，把 base64 置空
B64_LINE = re.compile(r'^[ \t]*((?:qa|quiz|performance|beauty|medical|risk|daily|manual|report|kbadmin|issues)\s*:\s*)"[A-Za-z0-9+/=]{120,}"[,]?\s*$', re.MULTILINE)


def strip_modules(html):
    def rep(m):
        tail = ',' if m.group(0).rstrip().endswith(',') else ''
        return m.group(1) + '""' + tail
    return B64_LINE.sub(rep, html)


def build_mods():
    """产出 mods/<id>.gz（http 部署用）与 mods/<id>.js（file:// 双击回退用）"""
    os.makedirs(MODS_DIR, exist_ok=True)
    names = []
    for key, fn in SRC.items():
        if not os.path.exists(os.path.join(BASE, fn)):
            continue
        raw = io.open(os.path.join(BASE, fn), encoding='utf-8').read()
        gz = gzip.compress(raw.encode('utf-8'), 9)
        with io.open(os.path.join(MODS_DIR, key + '.gz'), 'wb') as f:
            f.write(gz)
        # file:// 双击打开时 fetch 被 CORS 拦截，改由经典 <script> 注入该 js（不受 CORS 限制）
        b64 = base64.b64encode(gz).decode('ascii')
        js = u"(function(){window.__MODSRC__=window.__MODSRC__||{};window.__MODSRC__['%s']=\"%s\";})();\n" % (key, b64)
        with io.open(os.path.join(MODS_DIR, key + '.js'), 'w', encoding='utf-8') as f:
            f.write(js)
        names.append((key, len(raw), len(gz)))
    return names


BAT = u'''@echo off
chcp 936 >nul
cd /d "%~dp0"
set PORT=8000
echo.
echo  Local server: http://127.0.0.1:%PORT%/
echo  Keep this window open; close it to stop the server.
echo.
start "" http://127.0.0.1:%PORT%/index.html
where python >nul 2>nul && (python -m http.server %PORT% & goto :eof)
where py >nul 2>nul && (py -3 -m http.server %PORT% & goto :eof)
echo Python not found in PATH. Install Python, or open the HTML from a local web server.
pause
'''

README = u'''# 在线部署包 · 使用说明

## 1. 本地预览（推荐）
双击 **启动本地服务.bat** —— 会起一个 http://127.0.0.1:8000 的本地服务并自动打开页面。
（本包的瘦壳设计是按 http 部署来的：模块按需下载 + 浏览器缓存，功能最完整。）

## 2. 直接双击 HTML（file://）
也可以直接双击 `客舱小助手（在线版）.html`，但浏览器禁止 file:// 下的 fetch/XHR，
此时外壳会自动改走 `<script>` 注入 `mods/<id>.js`，同样能加载全部模块。
前提：**mods 文件夹必须和 HTML 放在同一目录下**（缺了会提示"加载失败"）。

## 3. 部署到服务器 / GitHub Pages
把本目录整体上传即可（**mods/*.js 可以删掉**，那是给 file:// 双击用的副本；
只留 mods/*.gz 能给服务器省 ~6MB）。目录结构：

```
/mods/*.gz
客舱小助手（在线版）.html
index.html
```

## 常见问题
- **模块加载失败 / CORS 报错**：说明你是用 file:// 打开的且 mods 目录不在旁边；
  改用「启动本地服务.bat」，或把 mods 文件夹拷到 HTML 同级目录。
- **想要一个单独文件随身带**：请用根目录的 `客舱小助手（离线完整版）.html`（所有模块已内嵌，双击即用）。
'''


def write_helpers(out9):
    # 本地服务启动器（ASCII/GBK 均可，提示语用英文避免编码问题）
    with io.open(os.path.join(OUT_DIR, u'启动本地服务.bat'), 'w', encoding='utf-8') as f:
        f.write(BAT)
    # index.html：本地服务 / Pages 根路径自动进入在线版
    idx = u'<meta charset="utf-8">\n<meta http-equiv="refresh" content="0;url=./%s">\n' % os.path.basename(out9)
    with io.open(os.path.join(OUT_DIR, u'index.html'), 'w', encoding='utf-8') as f:
        f.write(idx)
    with io.open(os.path.join(OUT_DIR, u'使用说明.txt'), 'w', encoding='utf-8') as f:
        f.write(README)


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

    # 4) mods/*.gz + mods/*.js
    gzs = build_mods()
    # 5) 辅助文件：本地服务启动器 / index 跳转 / 说明
    write_helpers(out9)

    print(u'== 产物 ==')
    for p in (out9, out10):
        print(u'  {}  {:.2f}MB'.format(os.path.basename(p), os.path.getsize(p) / 1048576.0))
    print(u'  mods/ 共 {} 个模块（.gz 部署用 / .js 双击 file:// 回退用）：'.format(len(gzs)))
    for key, raw, g in gzs:
        print(u'    {:<12} raw {:.2f}MB -> gz {:.2f}MB'.format(key + '.gz', raw / 1048576.0, g / 1048576.0))


if __name__ == '__main__':
    main()