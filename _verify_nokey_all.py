# -*- coding: utf-8 -*-
"""全链路零密钥审计（2026-09-19 起常驻回归）
--------------------------------------------------------------------------------
背景：用户决定「彻底无密钥」，要求「确认无残留引用」。源码 grep 干净不等于产物干净 ——
      发布物有五层：① 模块源 ② 在线版 mods/*.gz ③ 两份离线单文件的 base64 内嵌载荷
      ④ APK assets/www ⑤ PWA 目录；再加 ⑥ APK 二进制本体。
本脚本逐层取证，任何一层出现密钥/外部端点即失败（非零退出）。

用法：python _verify_nokey_all.py            # 全量审计
      python _verify_nokey_all.py --quiet    # 只输出结论
"""
import base64
import gzip
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
QUIET = '--quiet' in sys.argv

# 禁用的字面量（2026-09-19 晚随 AI 混合模式恢复调整口径）：
#   仍禁：内置共享 Key、Key 常量、硅基流动端点、Gist 云同步、已删除的 4.7 引用
#   放行：open.bigmodel.cn（GLM-4-Flash 免费模型端点）、api.tavily.com / api.firecrawl.dev
#         （免Key搜索）、spring_ai_cfg（运行时 localStorage 键名）、Bearer（运行时拼接，无内置令牌）
BAN = [u'4986b927', u'BUILTIN_AI_KEY',
       u'api.siliconflow.cn', u'api.github.com', u'glm-4.7', u'glm47']
# 2026-09-21 口径对齐（原先只查上面的字面量子串，会漏掉「字面量形式的 Key 值」与「内置 Bearer 令牌」，
# 而 _check_needles.py 一直有这两条正则 —— 两处守护口径不一致，等于留了后门）：
#   APIKEY_RX：apiKey/APIKEY 后跟 8 字符以上的字面量字符串（空串、变量取值不算）
#   BEARER_RX：Bearer 后跟 20 字符以上的令牌（源码里运行时拼接的裸词 Bearer 不算，故不误报）
APIKEY_RX = re.compile(r"apiKey\s*:\s*['\"][^'\"]{8,}")
BEARER_RX = re.compile(r"Bearer\s+[A-Za-z0-9_\.\-]{20,}")
SRC_FILES = [u'qa.html', u'beauty.html', u'quiz.html', u'cc-home.html',
             u'kb-admin.template.html', u'kb-admin.html', u'performance.html',
             u'index.html', u'_build_home.py']
B64 = re.compile(r'\b(qa|quiz|performance|beauty|medical|risk|daily|manual|report|kbadmin|issues|home)'
                 r'\s*:\s*"([A-Za-z0-9+/=]{120,})"')   # 2026-09-21：补全模块键（原先只 4 个，漏层=留死角）

res = []


def scan(label, text):
    h = [b for b in BAN if b in text]
    if APIKEY_RX.search(text):
        h.append(u'apiKey 有字面量值')
    if BEARER_RX.search(text):
        h.append(u'内置 Bearer 令牌')
    res.append((label, h))
    if not QUIET:
        print(u'  %-52s %s' % (label, (u'残留 ' + u','.join(h)) if h else u'OK'))


def rd(p):
    with io.open(p, encoding='utf-8', errors='ignore', newline='') as f:
        return f.read()


def main():
    print(u'== ① 模块源 ==')
    for f in SRC_FILES:
        if os.path.exists(f):
            scan(f, rd(f))
    print(u'== ② 在线版 mods/*.gz ==')
    d = os.path.join('在线版', 'mods')
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.endswith('.gz'):
                try:
                    with io.open(os.path.join(d, f), 'rb') as fh:
                        body = gzip.decompress(fh.read()).decode('utf-8', 'ignore')
                    scan(u'在线版/mods/' + f, body)
                except Exception as e:
                    res.append((u'在线版/mods/' + f, [u'解码失败 ' + str(e)]))
    else:
        res.append((u'在线版/mods', [u'目录缺失']))
    print(u'== ③ 离线单文件（壳本体 + base64 内嵌载荷）==')
    for sh in (u'spring-assistant.html', u'客舱小助手（离线完整版）.html'):
        if not os.path.exists(sh):
            res.append((sh, [u'缺失'])); continue
        s = rd(sh)
        scan(sh + u' · 壳本体', s)
        for m in B64.finditer(s):
            try:
                body = gzip.decompress(base64.b64decode(m.group(2))).decode('utf-8', 'ignore')
            except Exception:
                continue
            scan(u'%s · 内嵌载荷 %s' % (sh, m.group(1)), body)
    print(u'== ④ APK www / PWA ==')
    for d in (os.path.join('APK封装', 'CabinAssistant', 'assets', 'www'),
              os.path.join('PWA封装', '客舱小助手')):
        if not os.path.isdir(d):
            res.append((d, [u'目录缺失'])); continue
        for f in sorted(os.listdir(d)):
            if f.endswith('.html'):
                scan(u'%s/%s' % (os.path.basename(os.path.dirname(d)) + u'/' + os.path.basename(d), f), rd(os.path.join(d, f)))
    print(u'== ⑤ APK 二进制 ==')
    apk = os.path.join('APK封装', 'CabinAssistant', u'客舱小助手.apk')
    if os.path.exists(apk):
        with io.open(apk, 'rb') as fh:
            raw = fh.read()
        h = [b for b in (u'4986b927', u'BUILTIN_AI_KEY', u'glm-4.7')
             if b.encode('utf-8') in raw]   # spring_ai_cfg 已放行：运行时自存 Key 的键名，非内置密钥
        res.append((u'客舱小助手.apk (%.1f MB)' % (len(raw) / 1048576.0), h))
        if not QUIET:
            print(u'  %-52s %s' % (u'APK 二进制', (u'残留 ' + u','.join(h)) if h else u'OK'))
    else:
        res.append((u'客舱小助手.apk', [u'缺失']))

    bad = [(k, v) for k, v in res if v]
    print(u'\n===== 零密钥审计汇总 =====')
    print(u'检查 %d 项 / 残留 %d 项' % (len(res), len(bad)))
    for k, v in bad:
        print(u'  FAIL %s :: %s' % (k, u', '.join(v)))
    print(u'结论：%s' % (u'全链路零密钥 ✔' if not bad else u'存在残留，必须修复'))
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
