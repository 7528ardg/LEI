# -*- coding: utf-8 -*-
"""nc/index.html 内嵌 quiz 副本（南昌定制版）考试模式修复回填（2026-10-03）

背景：quiz.html（广州版源）修复了考试/模拟考试模式的 11 处「解析弹窗/答案泄露/
游戏化弹窗」问题；nc/index.html 的 MODULES.quiz 内嵌的是南昌定制版 quiz 副本
（标题"南昌刷题系统"，不能直接用广州版覆盖），但其中存在完全相同的缺陷。

本脚本从 __nc_quiz_extract_tmp.html（已就地修复的南昌副本明文）重新
gzip(mtime=0,等级9)+base64 后原子回填到 nc/index.html 的 quiz: "..." 值。

幂等：重复运行结果一致（回填值仅取决于明文副本内容）。
用法：python _apply_nc_quiz_examfix_20261003.py
"""
import base64
import gzip
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
SHELL = os.path.join(HERE, 'nc', 'index.html')
PLAIN = os.path.join(HERE, '__nc_quiz_extract_tmp.html')

def main():
    if os.path.exists(PLAIN):
        plain = io.open(PLAIN, 'r', encoding='utf-8', newline='').read()
    else:
        # 回退：直接从壳内嵌副本解压（当前 shell 内已含修复版 → 走幂等跳过分支）
        shell_txt = io.open(SHELL, 'r', encoding='utf-8', newline='').read()
        m0 = re.search(r'quiz: "([A-Za-z0-9+/=]+)"', shell_txt)
        if not m0:
            raise SystemExit('[ABORT] 壳内未找到 quiz 副本且明文缺失: ' + PLAIN)
        plain = gzip.decompress(base64.b64decode(m0.group(1))).decode('utf-8')
        print('[INFO] 明文副本缺失，改用壳内自解压（应为修复版）')
    # 守卫：明文副本必须已含修复、不含失效判断
    if 'qz.isExam || qz.isMock' in plain:
        raise SystemExit('[ABORT] 副本仍含失效判断，请先完成修复')
    need = [
        "qz.mode==='exam' || qz.mode==='mock_exam'",
        "bp-feedback show fb-neutral",
        "(_qz.mode==='exam' || _qz.mode==='mock_exam')",
    ]
    for n in need:
        if n not in plain:
            raise SystemExit('[ABORT] 副本缺少修复标记: ' + n)

    raw = plain.encode('utf-8')
    # mtime=0：gzip 头不含时间戳，保证输出确定性（幂等的关键）
    gz = gzip.compress(raw, 9, mtime=0)
    b64 = base64.b64encode(gz).decode('ascii')

    s = io.open(SHELL, 'r', encoding='utf-8', newline='').read()
    # 精确正则 + 长度守卫：只替换 MODULES 里的 quiz 值
    pat = re.compile(r'(quiz: ")([A-Za-z0-9+/=]+)(")')
    ms = list(pat.finditer(s))
    if len(ms) != 1:
        raise SystemExit('[ABORT] quiz 值匹配数异常: %d（期望 1）' % len(ms))
    m = ms[0]
    old_b64 = m.group(2)
    if old_b64 == b64:
        print('[IDEMPOTENT] nc/index.html quiz 副本已是目标内容，跳过')
        return
    # 长度守卫：新值合理范围（明文 3.6MB 级 → b64 约 1.2MB 字符）
    if not (800000 < len(b64) < 3000000):
        raise SystemExit('[ABORT] 新 b64 长度异常: %d' % len(b64))
    s2 = s[:m.start(2)] + b64 + s[m.end(2):]
    tmp = SHELL + '.tmp_write'
    with io.open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(s2)
    os.replace(tmp, SHELL)
    print('[OK] nc/index.html quiz 副本已回填: gz %.2fMB -> b64 %.2fMB 字符'
          % (len(gz) / 1048576.0, len(b64) / 1048576.0))

if __name__ == '__main__':
    main()
