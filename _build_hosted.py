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
import base64, fnmatch, gzip, io, os, re, shutil, subprocess, sys

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, u'在线版')
MODS_DIR = os.path.join(OUT_DIR, u'mods')

MODULES = ['qa', 'quiz', 'performance', 'beauty', 'medical', 'daily', 'manual', 'report', 'kbadmin', 'issues']
MODULES_4IN1 = ['qa', 'quiz', 'performance', 'beauty', 'medical', 'risk', 'daily', 'manual', 'report', 'kbadmin', 'issues']
SRC = {
    'qa': u'qa.html', 'home': u'cc-home.html', 'quiz': u'quiz.html', 'performance': u'performance.html',
    'beauty': u'beauty.html', 'medical': u'medical.html', 'risk': u'risk-lite.html',
    'daily': u'daily.html', 'manual': u'manual.html', 'report': u'report.html',
    'kbadmin': u'kb-admin.html', 'issues': u'issues.html',
}

# 匹配 MODULES 对象里形如  "  key: "H4sI...很长的base64..."  的片段，把 base64 置空。
# 2026-09-21 放宽：原正则要求 base64 独占整行（行尾只允许逗号），一旦上游产物把该行折叠/加了尾注，
# 就会静默不替换、瘦壳仍内嵌大块数据。现在只锚定「行首 + key: "长base64"」，行尾内容不受影响。
B64_LINE = re.compile(
    r'^([ \t]*(?:qa|quiz|performance|beauty|medical|risk|daily|manual|report|kbadmin|issues|home)\s*:\s*)'
    r'"[A-Za-z0-9+/=]{120,}"', re.MULTILINE)


def strip_modules(html):
    def rep(m):
        return m.group(1) + '""'
    return B64_LINE.sub(rep, html)


def build_mods():
    """产出 mods/<id>.gz（http 部署用）与 mods/<id>.js（file:// 双击回退用）"""
    os.makedirs(MODS_DIR, exist_ok=True)
    names = []
    for key, fn in SRC.items():
        if not os.path.exists(os.path.join(BASE, fn)):
            continue
        raw = io.open(os.path.join(BASE, fn), encoding='utf-8', newline='').read()
        gz = gzip.compress(raw.encode('utf-8'), 9)
        with io.open(os.path.join(MODS_DIR, key + '.gz'), 'wb') as f:
            f.write(gz)
        # file:// 双击打开时 fetch 被 CORS 拦截，改由经典 <script> 注入该 js（不受 CORS 限制）
        b64 = base64.b64encode(gz).decode('ascii')
        js = u"(function(){window.__MODSRC__=window.__MODSRC__||{};window.__MODSRC__['%s']=\"%s\";})();\n" % (key, b64)
        # newline='' 必须给：否则 Windows 文本模式把 \n 写成 \r\n，工作区行尾不变量被破坏
        # （2026-09-21 实测：这里漏了 newline=''，12 个 mods/*.js 全变 CRLF）
        with io.open(os.path.join(MODS_DIR, key + '.js'), 'w', encoding='utf-8', newline='') as f:
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
/assets/img/*            ← 模块用到的图片（2026-09-22 起从模块内联 base64 抽出，缺了会裂图）
客舱小助手（在线版）.html
index.html
```

> 注意：`assets/` 目录必须和 HTML 同级上传（与 mods 一样是必需的），不要再把图片内联回 HTML。

## 常见问题
- **模块加载失败 / CORS 报错**：说明你是用 file:// 打开的且 mods 目录不在旁边；
  改用「启动本地服务.bat」，或把 mods 文件夹拷到 HTML 同级目录。
- **想要一个单独文件随身带**：请用根目录的 `客舱小助手（离线完整版）.html`（所有模块已内嵌，双击即用）。
'''


def write_helpers(out9):
    # 本地服务启动器（ASCII/GBK 均可，提示语用英文避免编码问题）
    # 2026-09-21：显式指定换行为 CRLF（.bat 在 Windows 上最稳），取代原先依赖文本模式的隐式转换
    with io.open(os.path.join(OUT_DIR, u'启动本地服务.bat'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(BAT)
    # index.html：本地服务 / Pages 根路径自动进入在线版
    idx = u'<meta charset="utf-8">\n<meta http-equiv="refresh" content="0;url=./%s">\n' % os.path.basename(out9)
    with io.open(os.path.join(OUT_DIR, u'index.html'), 'w', encoding='utf-8', newline='') as f:
        f.write(idx)
    with io.open(os.path.join(OUT_DIR, u'使用说明.txt'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(README)


def _sync_tree(src, dst, ignore_files=(), ignore_dirs=()):
    """覆盖式同步：不删目录、不批量删除（批量删除会被文件安全策略拦下），可反复重跑"""
    n = 0
    for r, ds, fs in os.walk(src):
        ds[:] = [d for d in ds if d not in ignore_dirs]
        rel = os.path.relpath(r, src)
        out = dst if rel == '.' else os.path.join(dst, rel)
        if not os.path.isdir(out):
            os.makedirs(out)
        for f in fs:
            if any(fnmatch.fnmatch(f, p) for p in ignore_files):
                continue
            # 2026-09-22 审查 L12：改为「写临时文件 + os.replace」原子落盘，
            # 避免中断/磁盘满时在在线部署包里留下半截文件（与项目落盘铁律一致）。
            _src, _dst = os.path.join(r, f), os.path.join(out, f)
            _tmp = _dst + '.tmp_write'
            shutil.copyfile(_src, _tmp)
            os.replace(_tmp, _dst)
            n += 1
    return n


def sync_assets():
    """把站点图集 assets/img/ 同步进在线部署包（模块 HTML 只保留相对引用）。

    2026-09-22：模块内联 base64 大图已抽成 assets/img/*（`_extract_inline_images_20260921.py`），
    模块以 srcdoc 注入 iframe，相对路径基准是 OUT_DIR → 不拷这份就会全站裂图。
    独立成模块级函数是为了能单独调用验证（`python -c "import _build_hosted as b; b.sync_assets()"`）。
    """
    src = os.path.join(BASE, u'assets', u'img')
    if not os.path.isdir(src):
        print(u'  [跳过] 未找到 assets/img/（模块仍是内联 base64 形态）')
        return 0
    dst = os.path.join(OUT_DIR, u'assets', u'img')
    n = _sync_tree(src, dst)
    sz = sum(os.path.getsize(os.path.join(dst, f)) for f in os.listdir(dst))
    print(u'  assets/img/ 已同步（{} 张，{:.1f}MB）'.format(n, sz / 1048576.0))
    return n


def main():
    # 1) 先构建标准嵌入式产物（在线版 shell 由其改造而来）
    subprocess.check_call([sys.executable, u'_gzip_build.py'], cwd=BASE)
    subprocess.check_call([sys.executable, u'_build_4in1.py'], cwd=BASE)
    # 1.5) 重建会覆写产物并冲掉 UX 美化块，重挂（幂等）
    subprocess.check_call([sys.executable, u'_apply_ux_polish.py'], cwd=BASE)

    os.makedirs(OUT_DIR, exist_ok=True)

    # 2) spring-assistant.html -> 9 模块瘦壳
    shell = io.open(os.path.join(BASE, u'spring-assistant.html'), encoding='utf-8', newline='').read()
    hosted = strip_modules(shell)
    out9 = os.path.join(OUT_DIR, u'客舱小助手（在线版）.html')
    # 瘦壳必须真的被置空：B64_LINE 依赖「base64 独占一行」，若上游产物格式变了会静默不替换
    assert B64_LINE.search(hosted) is None, u'strip_modules 未生效：瘦壳仍内嵌模块载荷'
    assert len(hosted) < len(shell) * 0.9, u'strip_modules 效果异常：瘦壳体积未明显下降'
    tmp9 = out9 + '.tmp_write'
    with io.open(tmp9, 'w', encoding='utf-8', newline='') as f:
        f.write(hosted)
    os.replace(tmp9, out9)

    # 3) 离线完整版 -> 10 模块瘦壳（含 risk）
    shell4 = io.open(os.path.join(BASE, u'客舱小助手（离线完整版）.html'), encoding='utf-8').read()
    hosted4 = strip_modules(shell4)
    out10 = os.path.join(OUT_DIR, u'客舱小助手（离线完整版-在线部署）.html')
    assert len(hosted4) < len(shell4) * 0.9, u'strip_modules 效果异常（4in1）：瘦壳体积未明显下降'
    tmp10 = out10 + '.tmp_write'
    with io.open(tmp10, 'w', encoding='utf-8', newline='') as f:
        f.write(hosted4)
    os.replace(tmp10, out10)

    # 4) mods/*.gz + mods/*.js
    gzs = build_mods()

    # 4.5) 真 3D 形象资产：模块是以 srcdoc 注入 iframe 的，srcdoc 的 base URL 继承父页
    #      （在线版/index.html），所以 CC3D 用的相对路径 形象IP/models/... 必须在
    #      OUT_DIR 下真实存在。http(s) 走 fetch(ccNN.glb)，file:// 走 js/ccNN.js 的 base64 包装。
    md_src = os.path.join(BASE, u'形象IP', u'models')
    md_dst = os.path.join(OUT_DIR, u'形象IP', u'models')
    if os.path.isdir(md_src):
        # 注：lichun-3d.glb / lichun-3d-viewer.html 为早期 3D 试验遗留，文件已不存在（2026-09-15 确认），
        #     此处不再保留失效忽略项，避免误导后续维护者以为它们还在。
        _sync_tree(md_src, md_dst, ignore_files=(u'*_raw.glb',))
        # 背景图已全部 base64 内嵌进页面（`_bd_embed.py`），在线版不再需要外部 backdrops 副本
        print(u'  形象IP/backdrops/ 跳过同步（背景图已内嵌，省约 5MB）')
        n_glb = len([f for f in os.listdir(md_src)
                     if f.startswith('cc') and f.endswith('.glb')])
        sz = sum(os.path.getsize(os.path.join(r, f))
                 for r, d, fs in os.walk(md_dst) for f in fs)
        print(u'  形象IP/models/ 已同步（3D 模型 {} 个，合计 {:.1f}MB）'.format(n_glb, sz / 1048576.0))

    # 4.6) 站点图集：模块 HTML 已把内联 base64 大图抽到 assets/img/（2026-09-22 瘦身），
    #      模块是以 srcdoc 注入 iframe 的，相对路径基准是 OUT_DIR → 必须把 assets/img 真实拷进来，
    #      否则在线版/离线壳全是裂图。
    sync_assets()

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