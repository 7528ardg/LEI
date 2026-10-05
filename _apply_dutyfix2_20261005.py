# -*- coding: utf-8 -*-
"""值班电话占位符去暴露化 · 精修（2026-10-05）
=============================================
【背景】_apply_dutyfix_20261005.py 已把88 处 {{DUTY_*}} 改成「查当班通讯录」，
        但截图复核发现 4 类不通顺/无意义残留，本脚本做**逐条精确**精修
        （项目铁律：清文案禁正则批量删，会把句子截断裂 → 全部走精确串替换）。

【四类问题】
  ① 重复占位：同一字段曾填两个号码（MOBILE+LANDLINE）→ 出现
     「查当班通讯录 / 查当班通讯录」「查当班通讯录，查当班通讯录」→ 收敛为一个
  ② 空话：「地址电话勿填错」前出现「电话 查当班通讯录」→ 去掉冗余「电话 」
  ③ 无意义枚举：「航空医师 查当班通讯录 / 查当班通讯录」等全同值罗列 → 合并
  ④ 题库失效：quiz.html「航空医生联系电话」单选题 4 个选项全变成同一句
     → 该题已无区分度，必须整题改写（否则题库出现 4 个相同选项的脏题）

【模式】幂等（已是目标表述则跳过）；原子写
"""
import io
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
REPL = u'查当班通讯录'

# ---- ① 重复值收敛（qa/kb-admin 同步，两者内容同源） ----
DEDUP = [
    (u'<strong>' + REPL + u' / ' + REPL + u'</strong>', u'<strong>' + REPL + u'</strong>'),
    (u'（' + REPL + u'，' + REPL + u'）', u'（' + REPL + u'）'),
    (u'（' + REPL + u' / ' + REPL + u'）', u'（' + REPL + u'）'),
    (u'查当班通讯录' + REPL, REPL),          # 漏了分隔符的粘连
    (REPL + u' / ' + REPL, REPL),
    (REPL + u'，' + REPL, REPL),
]

# ---- ② 空话清理：去掉占位符后残留的冗余引导词 ----
CLEAN = [
    (u'，电话' + REPL, u'，' + REPL),                      # 「，电话 查当班通讯录」
    (u'：电话' + REPL, u'：' + REPL),
    (u'电话' + REPL + u'（24×7）', REPL + u'（24×7）'),
]

# ---- ③ 题库整题改写（quiz.html） ----
QUIZ_OLD_A = (u'{"q": "航空卫生不安全事件中，空勤人员航空医生联系电话是多少？", '
              u'"type": "单选", "opts": ["A. ' + REPL + u'", "B. ' + REPL + u'", "C. ' + REPL + u'", "D. ' + REPL + u'"], '
              u'"ans": "A", "chapter": "第八章 附录", "diff": "中", "origNum": "3.N096", "section": "3.6.5 3.6.5", '
              u'"explain": "3.6.4.2 (1) 当空勤人员在非值勤期发生航空卫生不安全事件时……应立即报告航空医生，电话：' + REPL + u'。3.6.4.2"}')
# 改写为「问报告对象」而非「问电话号码」—— 号码属动态信息，不适合做固定题目
QUIZ_NEW_A = (u'{"q": "航空卫生不安全事件，空勤人员在非值勤期应立即报告谁？", '
              u'"type": "单选", '
              u'"opts": ["A. 航空医生", "B. 乘务长", "C. 地服", "D. 客舱服务部值班经理"], '
              u'"ans": "A", "chapter": "第八章 附录", "diff": "中", "origNum": "3.N096", "section": "3.6.5 3.6.5", '
              u'"explain": "3.6.4.2 (1) 当空勤人员在非值勤期发生航空卫生不安全事件时……应立即报告航空医生（联系方式查当班通讯录）。3.6.4.2"}')

# 第二题：B/C/D 三个干扰项全同值 → 换成有区分度的部门
QUIZ_OLD_B = (u'"opts": ["A. 021-95524", "B. ' + REPL + u'", "C. ' + REPL + u'", "D. ' + REPL + u'"], "ans": "A"}')
QUIZ_NEW_B = (u'"opts": ["A. 021-95524", "B. 客舱服务部值班经理", '
              u'"C. 航空医生", "D. 安监部值班经理"], "ans": "A"}')


def read_text(p):
    with io.open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def write_atomic(p, s):
    tmp = p + '.tmp_write'
    with io.open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(s)
    os.replace(tmp, p)


def apply(path, pairs, label):
    p = os.path.join(BASE, path)
    if not os.path.exists(p):
        print(u'[MISS] %s' % path)
        return 0
    s = read_text(p)
    hit = 0
    for a, b in pairs:
        if a in s:
            n = s.count(a)
            s = s.replace(a, b)
            hit += n
    if hit:
        write_atomic(p, s)
    print(u'[%s] %-22s 精修 %d 处' % (label, path, hit))
    return hit


def main():
    total = 0
    # ① + ② 收敛与清理（qa 与 kb-admin 内容同源，同步处理）
    for f in ('qa.html', 'kb-admin.html'):
        total += apply(f, DEDUP + CLEAN, '精修')
    # report.html 也有重复项
    total += apply('report.html', DEDUP, '精修')
    # ④ 题库整题改写
    total += apply('quiz.html', [(QUIZ_OLD_A, QUIZ_NEW_A), (QUIZ_OLD_B, QUIZ_NEW_B)], '题库')
    print(u'[完成] 合计精修 %d 处' % total)
    return 0


if __name__ == '__main__':
    sys.exit(main())
