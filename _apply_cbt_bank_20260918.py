# -*- coding: utf-8 -*-
"""培训考核 · 题库 = 原系统题库 + 独立分类「CBT练习」（2026-09-18 v2）

v1 曾把 CBT 三源合并的 2654 题**替换**掉原题库第一~八章；v2 按要求改正为：
  · 原系统题库（2181 题 · 第一~十章）**完整保留**，CBT 不再占用任何原有章节；
  · CBT 练习题库（CBT练习题库/cbt_题库_785题.csv 的 **785 题**）作为**独立特殊分类**追加，
    章节目录页多出「🎯 CBT练习」分区，进入时可选 **普通题目 719 / 321 机型题 66**。

CBT 题目的字段约定（供 UI 与成就系统消费）：
  chapter = 'CBT练习·普通题目' | 'CBT练习·321机型题'   → 培训考核「章节专项练习」的 CBT 分区两张卡
  manual  = 'cbt'                                     → manualOf() 分入独立分区（与 crew/csd 并列）
  cbtCh   = 第一章 概述 … 第八章 附录 / 无解析 / 321机型补充  → CBT 十类细目（成就「十门全通」等依赖）
  src     = 'cbt'                                     → 大撤应急页 CBT 答题板块的题目过滤器

原题库快照：_cbt_work/bank_orig.json（首次运行若不存在，自动从
quiz.bak_cbtbank_20260918.html 抽取，该备份即替换前的原题库）。

用法：python _apply_cbt_bank_20260918.py            # 执行
      python _apply_cbt_bank_20260918.py --check    # 校验当前文件是否已是目标内容
"""
import io, json, os, re, sys, shutil

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
QUIZ = os.path.join(HERE, 'quiz.html')
CBT = os.path.join(HERE, '_cbt_work')
SNAP = os.path.join(CBT, 'bank_orig.json')
BACKUP = os.path.join(HERE, 'quiz.bak_cbtbank_20260918.html')

CBT_CH_NORMAL = 'CBT练习·普通题目'
CBT_CH_321 = 'CBT练习·321机型题'
CBT_CH10 = {'第1章': '第一章 概述', '第2章': '第二章 术语和定义', '第3章': '第三章 安全规则',
            '第4章': '第四章 机型设备', '第5章': '第五章 标准操作程序', '第6章': '第六章 应急程序',
            '第7章': '第七章 应急救护', '第8章': '第八章 附录',
            '无解析': '无解析', '321补充': '321机型补充'}
NUM_PREFIX = {'第1章': '1', '第2章': '2', '第3章': '3', '第4章': '4', '第5章': '5',
              '第6章': '6', '第7章': '7', '第8章': '8', '无解析': 'X', '321补充': '321'}

# ---------------- literal scanning ----------------
def find_literal_end(s, start):
    open_ch = s[start]
    close_ch = ']' if open_ch == '[' else '}'
    depth = 0; i = start; n = len(s); in_str = None
    while i < n:
        c = s[i]
        if in_str:
            if c == '\\': i += 2; continue
            if c == in_str: in_str = None
            i += 1; continue
        if c in '"\'`': in_str = c; i += 1; continue
        if c == open_ch: depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0: return i + 1
        i += 1
    return -1

def locate(s):
    m = re.search(r'const\s+sampleQuestions\s*=\s*', s)
    if not m: raise SystemExit('!! 未找到 const sampleQuestions =')
    st = m.end()
    if s[st] != '[': raise SystemExit('!! sampleQuestions 不是数组字面量')
    en = find_literal_end(s, st)
    if en < 0: raise SystemExit('!! 数组字面量未闭合')
    return m.start(), m.end(), st, en

def js_to_py(lit):
    out = []; i = 0; n = len(lit); in_str = None
    while i < n:
        c = lit[i]
        if in_str:
            if c == '\\': out.append(lit[i:i+2]); i += 2; continue
            if c == in_str: out.append('"'); in_str = None; i += 1; continue
            if c == '"' and in_str != '"': out.append('\\"'); i += 1; continue
            out.append('\n' if c == '\n' else ('\r' if c == '\r' else c)); i += 1; continue
        if c in '"\'`': in_str = c; out.append('"'); i += 1; continue
        out.append(c); i += 1
    txt = ''.join(out)
    txt = re.sub(r'([{,]\s*)([A-Za-z_$][\w$]*)\s*:', r'\1"\2":', txt)
    txt = re.sub(r',(\s*[\]}])', r'\1', txt)
    return json.loads(txt)

def js_str(v):
    return json.dumps(v, ensure_ascii=False)

# ---------------- 原题库快照 ----------------
def ensure_snapshot():
    """返回原系统题库（不含 CBT 题目）。快照缺失时从替换前备份中抽取。"""
    if os.path.exists(SNAP):
        return json.load(io.open(SNAP, encoding='utf-8'))
    if not os.path.exists(BACKUP):
        raise SystemExit('!! 原题库快照缺失，且找不到替换前备份 quiz.bak_cbtbank_20260918.html\n'
                         '   请从版本库恢复该备份，或手工生成 _cbt_work/bank_orig.json')
    s = io.open(BACKUP, encoding='utf-8', newline='').read()
    a0, a1, st, en = locate(s)
    items = [q for q in js_to_py(s[st:en]) if q.get('src') != 'cbt']
    io.open(SNAP, 'w', encoding='utf-8', newline='').write(
        json.dumps(items, ensure_ascii=False, indent=1))
    print(f'  原题库快照生成 -> {os.path.relpath(SNAP, HERE)}（{len(items)} 题）')
    return items

def qkey(q):
    return (str(q.get('q', '')).strip(), str(q.get('chapter', '')))

def base_items(live):
    """原题库 = 快照 + 线上非 CBT 题目。线上题量不少于快照时以线上为准（保留应用内新增/编辑）。"""
    snap = ensure_snapshot()
    rest = [q for q in live if q.get('src') != 'cbt']
    if len(rest) >= len(snap):
        return rest
    seen = {qkey(q) for q in snap}
    extra = [q for q in rest if qkey(q) not in seen]
    return snap + extra

# ---------------- CBT 785 题（独立分类） ----------------
def build_cbt_items():
    recs = json.load(io.open(os.path.join(CBT, 'categorized.json'), encoding='utf-8'))
    rows = [r for r in recs if 'csv' in (r.get('src') or [])]      # 只取 cbt_题库_785题.csv 的题
    items = []
    for n, r in enumerate(rows, 1):
        cat = r['cat']
        is321 = (cat == '321补充')
        is_judge = (r['type'] == '判断题')
        raw = [str(o).strip() for o in (r.get('opts') or []) if o and str(o).strip()]
        if is_judge:
            opts = ['A. 对', 'B. 错']
            a = (r.get('answer') or '')[:1].upper()
            if a not in ('A', 'B'):
                a = 'A' if (r.get('answer') or '').startswith('正') else 'B'
        else:
            o = raw[:5]
            if len(o) < 2:                      # 兜底：极少见，用答案文本构造
                o = [r.get('answer_text') or '—']
            opts = [f"{'ABCDE'[i]}. {t}" for i, t in enumerate(o)]
            a = (r.get('answer') or 'A')[:1].upper()
            if a not in 'ABCDE' or 'ABCDE'.index(a) >= len(opts):
                a = 'A'
        if cat == '无解析':
            section, explain = '', ''
        else:
            sec = r.get('sec') or ''
            section = (f"{sec} {r.get('sec_title','')}".strip() if sec else '')
            explain = (r.get('manual_ana') or '').strip()
            v = r.get('verify') or ''
            if v and v not in ('一致', '一致(答案原文命中)'):
                explain += f"（核验：{v}）"
        diff = '易' if is_judge else ('难' if cat == '无解析' else '中')
        items.append({
            'q': r['stem'].strip(), 'type': '判断' if is_judge else ('多选' if r['type'] == '多选题' else '单选'),
            'opts': opts, 'ans': a,
            'chapter': CBT_CH_321 if is321 else CBT_CH_NORMAL,
            'section': section, 'explain': explain, 'diff': diff,
            'origNum': f"{NUM_PREFIX.get(cat, 'X')}.C{n:04d}",
            'src': 'cbt', 'manual': 'cbt', 'cbtCh': CBT_CH10.get(cat, cat),
        })
    return items

def render(items):
    return '[' + ',\n'.join(
        '{' + ', '.join(f'{js_str(k)}: {js_str(v)}' for k, v in it.items()) + '}' for it in items) + ']'

def main():
    check = '--check' in sys.argv
    s = io.open(QUIZ, encoding='utf-8', newline='').read()
    a0, a1, st, en = locate(s)
    live = js_to_py(s[st:en])
    base = base_items(live)
    cbt = build_cbt_items()
    want = base + cbt
    out = s[:st] + render(want) + s[en:]
    if check:
        ok = (out == s)
        print('  quiz.html 题库（原题库 + CBT练习分类） -> ' + ('UP-TO-DATE' if ok else '不一致'))
        sys.exit(0 if ok else 1)
    if out == s:
        print('  quiz.html 题库 -> UP-TO-DATE（无需改动）'); return
    bak = os.path.join(HERE, 'quiz.bak_cbtbank_v2_20260918.html')
    if not os.path.exists(bak):
        shutil.copy2(QUIZ, bak); print('  备份 ->', os.path.basename(bak))
# __ATOMIC_WRITE_20260921__
    _tmp_w = (QUIZ) + ".tmp_write"
    with io.open(_tmp_w, "w", encoding="utf-8", newline="") as _f_w:
        _f_w.write(out)
    os.replace(_tmp_w, (QUIZ))
    from collections import Counter
    print(f"  线上题库 {len(live)} -> 目标 {len(want)} 题 = 原题库 {len(base)} + CBT练习 {len(cbt)}")
    print(f"     CBT 分组：普通 {sum(1 for q in cbt if q['chapter'] == CBT_CH_NORMAL)}"
          f" / 321 机型 {sum(1 for q in cbt if q['chapter'] == CBT_CH_321)}")
    print('     CBT 十类细目：', dict(Counter(q['cbtCh'] for q in cbt).most_common()))
    print('     原题库章节：', dict(Counter(q.get('chapter') for q in base).most_common()))
    print(f"  quiz.html {len(s)} -> {len(out)} chars")

if __name__ == '__main__':
    main()
