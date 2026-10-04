# -*- coding: utf-8 -*-
"""
逆向重建 _cbt_work/categorized.json（2026-10-05）
==================================================
【背景】categorized.json 是 CBT 题库的"生成器输入"，但该离线生成脚本未入库，
        文件又被 gitignore（.gitignore 规则）→ 换机/清理后 _build_all 链在
        _apply_cbt_bank_20260918.py 处必然失败（本机实测已两次阻断构建链）。
【方案】quiz.html 的题库块已含完整 CBT 785 题（_apply_cbt_bank 的产物态），
        按 build_cbt_items 的映射【逐字段逆向】还原 categorized.json：
          src=['csv']、cat（由 cbtCh 反查 CBT_CH10）、type（判断/多选/单选 → 判断题/多选题/单选题）、
          stem/opts（剥 'A. ' 前缀）/answer/answer_text/sec+sec_title（拆 section）/
          manual_ana+verify（拆 explain 的「（核验：…）」后缀）。
【自验证】重建后重新执行 build_cbt_items，断言产出与 quiz.html 现有 CBT 题逐字段一致。
"""
import io, os, re, json, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding='utf-8')

import importlib.util
spec = importlib.util.spec_from_file_location('cbtbank', os.path.join(HERE, '_apply_cbt_bank_20260918.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

CBT_CH10_REV = {v: k for k, v in m.CBT_CH10.items()}
NUM_PREFIX_REV = {v: k for k, v in m.NUM_PREFIX.items()}
VERIFY_RE = re.compile(u'（核验：(.+?)）\\s*$')


def reverse_one(q, n):
    cat = CBT_CH10_REV.get(q.get('cbtCh'), q.get('cbtCh') or '')
    is321 = (q.get('chapter') == m.CBT_CH_321)
    if is321 and cat != u'321补充':
        cat = u'321补充'
    typ = q.get('type')
    rtype = {u'判断': u'判断题', u'多选': u'多选题'}.get(typ, u'单选题')
    opts = []
    for o in (q.get('opts') or []):
        s = re.sub(u'^[A-E]\\.\\s*', '', str(o))
        opts.append(s)
    rec = {
        'src': ['csv'],
        'cat': cat,
        'type': rtype,
        'stem': q.get('q', ''),
        'opts': opts,
        'answer': q.get('ans', 'A'),
    }
    explain = (q.get('explain') or '').strip()
    v = ''
    mm = VERIFY_RE.search(explain)
    if mm:
        v = mm.group(1)
        explain = explain[:mm.start()].strip()
    if cat == u'无解析':
        rec['sec'] = ''
        rec['sec_title'] = ''
        rec['manual_ana'] = ''
    else:
        sec = (q.get('section') or '').strip()
        sm = re.match(u'^(\\S+)\\s+(.*)$', sec)
        if sm and len(sm.group(1)) <= 4:
            rec['sec'] = sm.group(1)
            rec['sec_title'] = sm.group(2)
        else:
            rec['sec'] = ''
            rec['sec_title'] = sec
        rec['manual_ana'] = explain
        rec['verify'] = v
    if rtype == u'判断题':
        rec['answer'] = 'A'
    rec['_origNum'] = q.get('origNum', '')
    return rec


def main():
    s = io.open(m.QUIZ, encoding='utf-8', newline='').read()
    a0, a1, st, en = m.locate(s)
    live = m.js_to_py(s[st:en])
    cbt_live = [q for q in live if q.get('src') == 'cbt']
    print(u'quiz.html 现有 CBT 题：%d' % len(cbt_live))

    recs = [reverse_one(q, i + 1) for i, q in enumerate(cbt_live)]
    os.makedirs(m.CBT, exist_ok=True)
    out_path = os.path.join(m.CBT, 'categorized.json')
    io.open(out_path, 'w', encoding='utf-8', newline='').write(
        json.dumps(recs, ensure_ascii=False, indent=1))
    print(u'已写出 %s（%d 条）' % (out_path, len(recs)))

    # ---- 自验证：重建 CBT 题并与 quiz.html 现有题逐字段比对 ----
    rebuilt = m.build_cbt_items()
    same = len(rebuilt) == len(cbt_live)
    if same:
        for i, (a, b) in enumerate(zip(rebuilt, cbt_live)):
            if a != b:
                same = False
                diff_keys = [k for k in set(list(a.keys()) + list(b.keys())) if a.get(k) != b.get(k)]
                print(u'[差异] 第 %d 题：%s' % (i + 1, diff_keys))
                for k in diff_keys[:4]:
                    print(u'   %s: 重建=%r vs 现有=%r' % (k, a.get(k), b.get(k)))
                break
    if same:
        print(u'[PASS] 重建自验证：%d 题逐字段一致' % len(rebuilt))
        return 0
    print(u'[FAIL] 重建自验证不一致')
    return 1


if __name__ == '__main__':
    sys.exit(main())
