# -*- coding: utf-8 -*-
"""值班电话占位符去暴露化（2026-10-05）
==========================================
【背景】全站检查 P0-4：{{DUTY_MOBILE}} / {{DUTY_LANDLINE}} 合计 88 处直接显示给用户，
        集中在「值班经理电话」「值班电话」「航空医师电话」等**应急上报**字段。
        _brandify_20261005.py 故意不注入这两个占位符（注释明言「无经核实的真实号码，
        禁止臆造」），但结果是占位符原样露给用户 —— 应急电话显示为{{...}} 仍是交付缺陷。

【方案】不臆造号码，改为**指向权威来源**的表述：
        {{DUTY_MOBILE}} → 「查当班通讯录」
        {{DUTY_LANDLINE}} → 「查当班通讯录」
        并对「电话 X」这类句式做通顺化改写，避免出现「电话查当班通讯录」。

【必须排除的误伤（重要）】
   performance.html 有 1 处 {{DUTY_MOBILE}} 落在 **SHA 哈希校验数组中间**
   （形如 "dfeeef18...{{DUTY_MOBILE}}f367a176..."），是历史去品牌脚本的误伤，
   属数据内容而非展示文本 —— 一旦替换会破坏哈希数组结构。
   本脚本用「前后 20+ 位 hex」判据自动识别并跳过，且对该文件整体跳过。

【文件边界】只改 6 个文件：qa / kb-admin / report / daily / daily.template / quiz
   （performance.html 全文件跳过；template 必须与产物同步，否则产物重建会带回占位符）

【模式】幂等：已是「查当班通讯录」则跳过；原子写（.tmp_write + os.replace）
"""
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

# 这些文件整体跳过（内含哈希数组等数据内容，不能碰）
SKIP_FILES = {u'performance.html'}

FILES = [
    u'qa.html',
    u'kb-admin.html',
    u'report.html',
    u'daily.html',
    u'daily.template.html',
    u'quiz.html',
]

REPL = u'查当班通讯录'

# 先做「电话查当班通讯录」这类不通顺句式的改写（长串优先，避免半途被单串吃掉）
PHRASE_FIXES = [
    # 中文句：电话{{X}} / 手机{{X}} / 电话：{{X}} →去掉冗余引导词
    (u'电话：' + u'{{DUTY_MOBILE}}', u'电话：' + REPL),
    (u'电话：' + u'{{DUTY_LANDLINE}}', u'电话：' + REPL),
    (u'电话' + u'{{DUTY_MOBILE}}', REPL),
    (u'电话' + u'{{DUTY_LANDLINE}}', REPL),
    (u'手机' + u'{{DUTY_MOBILE}}', REPL),
    (u'值班电话' + u'{{DUTY_MOBILE}}', u'值班电话（' + REPL + u'）'),
    (u'值班电话' + u'{{DUTY_LANDLINE}}', u'值班电话（' + REPL + u'）'),
]


def read_text(p):
    with io.open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def write_atomic(p, s):
    tmp = p + '.tmp_write'
    with io.open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(s)
    os.replace(tmp, p)


def is_hash_context(s, i):
    """占位符位置是否落在 hex 串中间（哈希数组误伤）"""
    pre = s[max(0, i - 30):i]
    post = s[i + len(u'{{DUTY_MOBILE}}'):][:30]
    m = re.match(r'^\}\}([0-9a-f]{10,})', post)
    return bool(m) and bool(re.search(r'[0-9a-f]{20,}$', pre))


def count_ph(s):
    return s.count(u'{{DUTY_MOBILE}}') + s.count(u'{{DUTY_LANDLINE}}')


def main():
    total_before = 0
    total_after = 0
    touched = 0
    for rel in FILES:
        if rel in SKIP_FILES:
            print(u'[SKIP] %s（整体跳过）' % rel)
            continue
        p = os.path.join(BASE, rel)
        if not os.path.exists(p):
            print(u'[MISS] %s 不存在' % rel)
            continue
        s = read_text(p)
        n0 = count_ph(s)
        total_before += n0
        if n0 == 0:
            continue

        # 幂等前置：已是通顺表述则跳过
        if n0 and REPL in s and u'{{DUTY_MOBILE}}' not in s and u'{{DUTY_LANDLINE}}' not in s:
            continue

        s2 = s
        # 1) 哈希上下文守卫：占位符落在 hex 串中间 → 属数据内容，整体放弃本文件
        guard = [m.start() for m in re.finditer(r'\{\{DUTY_(?:MOBILE|LANDLINE)\}\}', s2)
                 if is_hash_context(s2, m.start())]
        if guard:
            print(u'[GUARD] %s 有 %d 处落在哈希数组内，整体不处理' % (rel, len(guard)))
            continue

        # 2) 句式改写（长串优先）
        for a, b in PHRASE_FIXES:
            if a in s2:
                s2 = s2.replace(a, b)
        # 3) 兜底：剩余裸占位符
        s2 = s2.replace(u'{{DUTY_MOBILE}}', REPL)
        s2 = s2.replace(u'{{DUTY_LANDLINE}}', REPL)

        n2 = count_ph(s2)
        if s2 == s:
            print(u'[NOOP] %s 无可改写（可能已是目标表述）' % rel)
            continue
        write_atomic(p, s2)
        chk = count_ph(read_text(p))
        total_after += chk
        touched += 1
        print(u'[替换] %-22s 占位符 %2d → %2d' % (rel, n0, chk))

    # 全量复核
    left = 0
    for rel in FILES + list(SKIP_FILES):
        p = os.path.join(BASE, rel)
        if os.path.exists(p):
            left += count_ph(read_text(p))
    print(u'[完成] 替换 %d 个文件；全站剩余占位符 %d 处（含跳过文件）' % (touched, left))
    return 0


if __name__ == '__main__':
    sys.exit(main())
