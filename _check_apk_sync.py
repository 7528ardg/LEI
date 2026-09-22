# -*- coding: utf-8 -*-
"""
APK 内容同步检查（轻量，无浏览器）
=================================================================
问题背景：2026-09-19 发现 APK 内的 assets/www 停留在**上一次装配**的状态 ——
本轮全部改动（跨板块带入 / 会话记忆 / 能力增强 / 落地条 / kb-admin 降级链 / 跳转修复）
在 APK 里 0 命中，即「改了源但没重新装配」。壳层有 _check_needles 守护，APK 这一环此前是空白。

做法：拿 www 里的每个 html 与工作区同名源文件比对各「注入标记块」的出现次数。
      次数不等 → 判定 APK 落后，明确提示重新装配。
      只比标记计数、不比整文件 md5：index.html 会被装配脚本注入 APK 专属补丁（APK_FIX3 等），
      本来就不等于源文件，用 md5 会恒报错。

用法：python _check_apk_sync.py [--quiet]
返回值：0 = 同步；1 = 落后或缺失
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
WWW = os.path.join(HERE, 'APK封装', 'CabinAssistant', 'assets', 'www')

QUIET = '--quiet' in sys.argv

# 需要比对的注入标记（源文件与 APK 内都应逐一对应）
MARKS = [
    u'__QA_BRIDGE_BEGIN__',
    u'__QA_MEM_BEGIN__',
    u'__QA_UX_BEGIN__',
    u'__QA_CAP_BEGIN__',
    u'QALANDING_BEGIN',
    u'__UX_POLISH:v1__',
    u'去培训考核练这些题',        # 跳转目标修复的幂等特征
    # 2026-09-19 新增：本地模式 / 首屏快问行 / 话术向导增强（不含则说明 APK 落后）
    u'__AI_RESTORE_20260919__',   # 2026-09-19 深夜：AI 接口恢复（混合模式），替代 NOKEY 标记
    u'__QA_QUICKSTART_BEGIN__',
    u'__QA_WIZARD2_v1',
    u'KBADMIN_LOCALMODE_v1',
    # 2026-09-21 新增：批1 增强三块 + 内置 AI 入口。
    # 加入原因：本清单此前未覆盖这几块，于是 APK 缺少「答案工具条 / 我的面板 / AI 赋魂 / 内置 AI」
    # 时 _check_apk_sync 依旧全绿 —— 守护存在盲区，「改了源没装配」被静默掩盖。
    # 2026-09-21 审查实测：源 8/8 标记命中，APK/PWA 仅 4/8。
    u'__QA_ANSWER_TOOLS_20260921__',
    u'__QA_MYPANEL_20260921__',
    u'__QA_AI_BRAIN_20260921__',
    u'__QA_BUILTIN_AI__',
]

# 只在含该标记的源文件里做比对（避免把"某文件本就没有"误判成缺失）
def read(p):
    try:
        return io.open(p, 'r', encoding='utf-8', newline='').read()
    except Exception:
        return None


def main():
    if not os.path.isdir(WWW):
        print(u'[SKIP] 未找到 APK assets/www（跳过 APK 同步检查）')
        return 0

    htmls = sorted([f for f in os.listdir(WWW) if f.lower().endswith('.html')])
    if not htmls:
        print(u'[SKIP] assets/www 下没有 html')
        return 0

    problems = []
    checked = 0
    for name in htmls:
        src = read(os.path.join(HERE, name))
        apk = read(os.path.join(WWW, name))
        if src is None or apk is None:
            continue
        for m in MARKS:
            cs, ca = src.count(m), apk.count(m)
            if cs == ca:
                if cs and not QUIET:
                    print(u'  OK   %-22s %-24s %d' % (name, m, cs))
                continue
            checked += 1
            problems.append((name, m, cs, ca))

    if not problems:
        print(u'[check] APK 内容与源一致（%d 个 html 比对通过）' % len(htmls))
        return 0

    print(u'!! APK 内容落后于源，共 %d 处不一致：' % len(problems))
    for name, m, cs, ca in problems:
        print(u'  %-22s %-24s 源=%d  APK=%d' % (name, m, cs, ca))
    print(u'')
    print(u'  修复：python _apply_apk_fix_20260918b.py && bash _build_apk.sh')
    print(u'  （在 APK封装/CabinAssistant 目录下执行；PWA 还要 python PWA封装/_build_pwa.py）')
    return 1


if __name__ == '__main__':
    sys.exit(main())
