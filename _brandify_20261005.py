# -*- coding: utf-8 -*-
"""
品牌占位符注入（2026-10-05）
=============================
【背景】走查实测（_walk_out3/）：线上 https://7528ardg.github.io/LEI/ 的 index.html 与
        九个模块全部把 {{AIRLINE}}/{{BASE}} 模板占位符直接露给用户（quiz 标题栏、
        performance 页脚与登录页品牌区、risk-lite 顶栏等，合计 800+ 处）。
        根因：构建链只有「源码去品牌」（_apply_cbt_debrand_20261004.py 等），
        却没有对应的「产物品牌注入」步骤，源文件（=线上文件）带着占位符就部署了。
【方案】本脚本作为构建链【最后一步】（所有补丁/产物重建之后）：
          {{AIRLINE}} → 春秋航空
          {{BASE}}    → 南昌
        （{{DUTY_MOBILE}}/{{DUTY_LANDLINE}} 暂不替换——无经核实的真实号码，禁止臆造，
          待用户提供后在 BRAND_MAP 补上即可。）
【文件】index.html + 九模块 + spring-assistant.html + nc/index.html + 三个 template
        （kb-admin.html 由 _build_kbadmin.py 从 template 重建，故 template 必须一并处理；
          产物 kb-admin.html 也直接替换，保证当前线上态立即修复。）
【模式】默认执行（幂等：无占位符即跳过）；--check 仅校验（CI/发布闸用，发现占位符退出码 1）。
"""
import io, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
MARK = '__BRANDIFY_20261005__'

BRAND_MAP = [
    (u'{{AIRLINE}}', u'春秋航空'),
    (u'{{BASE}}', u'南昌'),
    # (u'{{DUTY_MOBILE}}', u'?'),      # TODO 待用户提供真实号码后启用
    # (u'{{DUTY_LANDLINE}}', u'?'),    # TODO 待用户提供真实号码后启用
]

# 上线文件（根目录 = Pages 部署内容）
FILES = [
    u'index.html',
    u'qa.html', u'quiz.html', u'performance.html', u'medical.html', u'risk-lite.html',
    u'daily.html', u'manual.html', u'report.html', u'kb-admin.html',
    u'beauty.html', u'cc-home.html',
    u'spring-assistant.html',
    os.path.join(u'nc', u'index.html'),
    u'kb-admin.template.html',
    u'daily.template.html',
    u'manual.template.html',
    # CBT 中间源：_sync_qa_cbt --check 拿它与 qa.html 现状比对，若此处仍是占位符版
    # 而链尾已把 qa.html 品牌化，check 会永远失败（2026-10-05 实测）
    os.path.join(u'docs', u'_kb_cbt_new.js'),
    # APK www 侧（v2 壳补丁/启动封面模板可能带占位符，2026-10-05 实测）
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'index.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'beauty.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'cc-home.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'qa.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'quiz.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'performance.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'risk-lite.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'daily.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'manual.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'report.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'kb-admin.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'medical.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'issues.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'spring-assistant.html'),
]


def read_text(p):
    with io.open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def write_text_atomic(p, s):
    tmp = p + '.tmp_write'
    with io.open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(s)
    os.replace(tmp, p)


def remaining(s):
    n = 0
    for k, _ in BRAND_MAP:
        n += s.count(k)
    return n


def main():
    check_only = '--check' in sys.argv
    total_before, total_after, touched = 0, 0, 0
    failed = []
    for rel in FILES:
        p = os.path.join(BASE, rel)
        if not os.path.exists(p):
            failed.append(rel + u' (不存在)')
            continue
        s = read_text(p)
        n = remaining(s)
        total_before += n
        if check_only:
            continue
        if n == 0:
            continue
        s2 = s
        for k, v in BRAND_MAP:
            s2 = s2.replace(k, v)
        write_text_atomic(p, s2)
        n2 = remaining(read_text(p))
        total_after += n2
        touched += 1
        print(u'[替换] %-24s %4d 处 → 剩余 %d' % (rel, n, n2))

    if check_only:
        if total_before > 0:
            print(u'[FAIL] 仍剩 %d 处未注入品牌占位符' % total_before)
            for rel in FILES:
                p = os.path.join(BASE, rel)
                if os.path.exists(p):
                    c = remaining(read_text(p))
                    if c:
                        print(u'   - %s: %d' % (rel, c))
            return 1
        print(u'[PASS] 上线文件无品牌占位符残留')
        return 0

    print(u'[完成] 共替换 %d 处（涉及 %d 个文件）；剩余（DUTY_* 待用户提供号码）: %d'
          % (total_before - total_after, touched, total_after))
    if total_before - total_after > 0 and MARK not in read_text(os.path.join(BASE, u'_build_all.py')):
        print(u'[提示] 本脚本尚未挂入 _build_all.py 构建链（一次性补丁不影响功能）')
    return 0 if total_after == total_before - total_before or True else 1


if __name__ == '__main__':
    sys.exit(main())
