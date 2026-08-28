# -*- coding: utf-8 -*-
"""客舱小助手 · 一键构建 / 一键回归（M1-M3 收尾工具）
--------------------------------------------------------------------------------
用法：
  python _build_all.py            # 默认 all：构建 → 全套回归
  python _build_all.py build      # 只构建（sync check → kb-admin → spring → 4合1，任一步失败即停）
  python _build_all.py verify     # 只回归（全量语法检查 + 7 套逻辑验证）
--------------------------------------------------------------------------------
规则：
  - 构建链任一步失败立即终止并返回非零
  - 回归任一脚本失败则最终汇总显示 FAILED 并返回非零
"""
import io
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))

BUILD_STEPS = [
    (u'同步数据包引擎(4源)', u'python _sync_packs.py --check'),
    (u'构建 kb-admin(库管理)', u'python _build_kbadmin.py'),
    (u'构建 spring(9模块单文件)', u'python _gzip_build.py'),
    (u'构建 4合1(10模块离线版)', u'python _build_4in1.py'),
]

# M1-M3 逻辑验证套件（Node 先行、Python 收尾）
VERIFY_SCRIPTS = [
    u'node _verify_packs.js',      # 引擎单测 46
    u'node _verify_packs_e2e.js',  # 消费端真实数据 23
    u'node _verify_packs_m13.js',  # kb-admin 数据包中心 30
    u'node _verify_packs_m14.js',  # 备份内容层隔离 14
    u'node _verify_packs_m15.js',  # 产物内嵌特征 40
    u'node _verify_packs_m2.js',   # 在线更新 27
    u'python _verify_packs_m3.py', # 发布管线 19
]

# 全量语法检查覆盖：全部模块源 + 三外壳/产物（排除 .tmp_ 调试文件）
SYNTAX_FILES = [
    u'index.html',
    u'qa.html', u'quiz.html', u'performance.html', u'beauty.html',
    u'medical.html', u'daily.html', u'manual.html', u'report.html',
    u'risk-lite.html', u'kb-admin.html', u'kb-admin.template.html',
    u'spring-assistant.html', u'客舱小助手（离线完整版）.html',
]


def run(cmd, label, fail_on_err=True):
    print(u'\n==> ' + label)
    print(u'    ' + cmd)
    r = subprocess.run(cmd, shell=True, cwd=HERE)
    if r.returncode != 0:
        print(u'!! %s 失败（exit=%d）' % (label, r.returncode))
        if fail_on_err:
            sys.exit(r.returncode)
    return r.returncode


def syntax_check():
    print(u'\n===== 全量语法检查 =====')
    node = 'node'
    fails = 0
    for name in SYNTAX_FILES:
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            print(u'  [SKIP] %s（文件不存在）' % name)
            continue
        s = io.open(path, encoding='utf-8', newline='').read()
        parts = re.findall(r'<script[^>]*>(.*?)</script>', s, re.S)
        js = '\n;\n'.join(parts)
        tmp = os.path.join(HERE, '__all_check_tmp.js')
        with io.open(tmp, 'w', encoding='utf-8') as f:
            f.write(js)
        r = subprocess.run([node, '--check', tmp], capture_output=True, text=True)
        os.remove(tmp)
        ok = r.returncode == 0
        print(u'  %s -> %s' % (name, 'SYNTAX_OK' if ok else 'SYNTAX_ERR'))
        if not ok:
            fails += 1
            print(r.stderr[:1200])
    if fails:
        print(u'!! 语法检查 %d 个文件失败' % fails)
        sys.exit(1)
    print(u'  语法检查通过（%d 文件）' % len(SYNTAX_FILES))


def build_all():
    print(u'===== 构建链 =====')
    for label, cmd in BUILD_STEPS:
        run(cmd, label)
    for name in [u'spring-assistant.html', u'客舱小助手（离线完整版）.html', u'kb-admin.html']:
        p = os.path.join(HERE, name)
        if os.path.exists(p):
            print(u'  %s %.2f MB' % (name, os.path.getsize(p) / 1048576))
    print(u'构建链完成。')


def verify_all():
    print(u'\n===== 逻辑回归 =====')
    fails = 0
    for script in VERIFY_SCRIPTS:
        print(u'\n--- ' + script + ' ---')
        r = run(script, script, fail_on_err=False)
        if r != 0:
            fails += 1
    print(u'\n===== 汇总 =====')
    print(u'语法：OK')
    print(u'逻辑：%d 套失败 / 共 %d 套' % (fails, len(VERIFY_SCRIPTS)))
    if fails:
        sys.exit(1)
    print(u'VO 全部通过：构建产物与数据包体系（M1-M3）回归 199+ 项全绿。')


def main():
    mode = u'all'
    if len(sys.argv) > 1 and sys.argv[1] in (u'build', u'verify'):
        mode = sys.argv[1]
    print(u'客舱小助手 一键工具 —— 模式：%s' % (u'构建+回归' if mode == u'all' else (u'构建' if mode == u'build' else u'回归')))
    if mode in (u'build', u'all'):
        build_all()
    if mode in (u'verify', u'all'):
        syntax_check()
        verify_all()


if __name__ == '__main__':
    main()