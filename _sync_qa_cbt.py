# -*- coding: utf-8 -*-
"""你问我答 · 新增「CBT题库」资源库（2026-09-18）

把 CBT 练习题库（逐题对齐《客舱乘务员手册》01.10 的 10 类题库）接入「你问我答」，
作为可切换的第 6 个来源库（🎯 CBT题库），使问答题可直接命中题库题目 + 手册原文解析。

产物：
  docs/_kb_cbt_new.js  —— 单一来源（window.KB_CBT_RAW）
  qa.html              —— 注入 KB_CBT 块 + SRC_CFG/currentKbPool/来源按钮 三处补丁（幂等）

注意：**不加入 _qaPools()**（跨库候选/切库路径），以免影响 qa 既有跨库回归不变量；
CBT 库通过来源按钮显式选择使用。

用法：python _sync_qa_cbt.py            # 生成 + 注入
      python _sync_qa_cbt.py --check    # 校验（不一致则非零退出）
"""
import io, json, os, re, sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
SRC_OUT = os.path.join(HERE, 'docs', '_kb_cbt_new.js')
QA = os.path.join(HERE, 'qa.html')
CBT = os.path.join(HERE, '_cbt_work')

KB_B = '/* KB_CBT_BEGIN（同步标记块，请勿在标记块外修改以下内容） */'
KB_E = '/* KB_CBT_END（同步标记块结束） */'
CB = '/* QA_CBT_PATCH_BEGIN（_sync_qa_cbt.py 注入；改动请改脚本后重跑） */'
CE = '/* QA_CBT_PATCH_END */'

SRC_ANCHOR = "\n};\nfunction currentKbPool(){"
SRC_NEW = ("""%%SRC%%
};
function currentKbPool(){""")
POOL_ANCHOR = "  if(qaSource==='dc') return (window.DC_KB && window.DC_KB.length) ? window.DC_KB : KB;"
POOL_NEW = POOL_ANCHOR + """
  if(qaSource==='cbt') return window.KB_CBT_RAW || KB;"""
TAB_ANCHOR = """<button class="src-tab" data-src="dc" onclick="setQaSource('dc',this)"><span class="t-full">🚨 大撤专项</span><span class="t-short">🚨 大撤</span></button>"""
TAB_NEW = TAB_ANCHOR + """
    <button class="src-tab" data-src="cbt" onclick="setQaSource('cbt',this)"><span class="t-full">🎯 CBT题库</span><span class="t-short">🎯 CBT</span><small>手册核验</small></button>"""
INJECT_ANCHOR = 'const SRC_CFG = {'

sys.path.insert(0, CBT)
import ccm_match as M  # noqa

SECS = json.load(open(os.path.join(CBT, "ccm_index.json"), encoding="utf-8"))['secs']
RECS = json.load(open(os.path.join(CBT, "categorized.json"), encoding="utf-8"))


def page_of(sec):
    s = SECS.get(sec) or {}
    return s.get('page_label') or (f"PDF第{s['pdf_page']}页" if s.get('pdf_page') else '')


def build_pool():
    items = []
    for r in RECS:
        cat = r['cat']
        is_judge = (r['type'] == '判断题')
        raw = [str(o).strip() for o in (r.get('opts') or []) if o and str(o).strip()]
        if is_judge:
            ans = 'A. 对' if (r.get('answer_text') or '').strip() == '正确' else 'B. 错'
        else:
            hidden = r.get('answer_text') or ''
            ans = hidden
            if r.get('answer') and raw:
                idx = 'ABCDE'.index(r['answer'][:1].upper()) if r['answer'][:1].upper() in 'ABCDE' else -1
                if 0 <= idx < len(raw):
                    ans = f"{r['answer'][:1].upper()}. {raw[idx]}"
        body = []
        body.append(f"<b>✅ 答案：{ans}</b>")
        if raw:
            body.append("选项：" + '　'.join(raw[:5]))
        sec = r.get('sec')
        if sec and sec in SECS and cat != '无解析':
            cite = f"📘 手册依据 <b>{sec} {r.get('sec_title','')}</b>"
            if page_of(sec):
                cite += f"（{page_of(sec)}）"
            body.append(cite)
            ana = re.sub(r'^【[^】]*】', '', (r.get('manual_ana') or '').strip())
            if ana:
                body.append(ana[:220])
            v = r.get('verify') or ''
            if v and v not in ('一致', '一致(答案原文命中)'):
                body.append(f"<i>核验：{v}</i>")
        else:
            body.append("<i>⚠️ 手册中未检索到与该题直接对应的正文内容，仅保留题干与答案供对照。</i>")
        kw = []
        for w in M.salient_words(r['stem'])[:10]:
            if 2 <= len(w) <= 6 and w not in kw:
                kw.append(w)
        srct = f"CBT {sec}" if sec else f"CBT {cat}"
        items.append({
            'cat': cat, 'icon': '🎯', 'src': srct, 't': kw[:8],
            'q': r['stem'].strip(), 'a': '<br>'.join(body),
        })
    return items


def js_lit(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))


def write_source(items):
    hdr = (f"""/* ============================================================
 * 你问我答 · CBT题库 资源库（单一来源）
 * 来源：CBT 练习题库（{len(items)} 题），逐题对照《客舱乘务员手册》01.10 正文重建章节库核验：
 *       章节号全部有效、选项与答案内部一致 0 错位；解析一律带精确章节号。
 * 消费方：qa.html（你问我答 → 来源库「🎯 CBT题库」）
 * 同步：python _sync_qa_cbt.py（--check 守护），标记块 KB_CBT_BEGIN/END。
 * ============================================================ */
""")
    block = (KB_B + "\n" + "window.KB_CBT_RAW = " + js_lit(items) + ";\n" + KB_E + "\n")
    os.makedirs(os.path.dirname(SRC_OUT), exist_ok=True)
    io.open(SRC_OUT, 'w', encoding='utf-8', newline='').write(hdr + block)


def load_source():
    s = io.open(SRC_OUT, encoding='utf-8').read()
    i, j = s.find(KB_B), s.find(KB_E)
    if i < 0 or j < 0:
        raise SystemExit('!! docs/_kb_cbt_new.js 缺少 KB_CBT_BEGIN/END')
    return s[i:j + len(KB_E)]


def patch_qa(s, block, n):
    # 0) 幂等修复：确保 cbt 条目与前一条之间是「逗号+换行」（历史版本漏逗号）
    s2 = re.sub(r"\}\s*cbt:\s*\{ label:'CBT题库'", "},\n  cbt:  { label:'CBT题库'", s)
    if s2 != s:
        s = s2; n += 1

    # 1) 数据块注入
    a, b = s.find(KB_B), s.find(KB_E)
    if a >= 0 and b > a:
        if s[a:b + len(KB_E)] != block:
            s = s[:a] + block + s[b + len(KB_E):]; n += 1
    elif INJECT_ANCHOR not in s:
        raise SystemExit('!! 未找到 SRC_CFG 注入锚点')
    else:
        k = s.find(INJECT_ANCHOR)
        s = s[:k] + block + "\n\n" + s[k:]; n += 1

    # 2) SRC_CFG 追加 cbt
    if "label:'CBT题库'" not in s:
        if SRC_ANCHOR not in s:
            raise SystemExit('!! 未找到 SRC_CFG 结尾锚点')
        s = s.replace(SRC_ANCHOR, SRC_NEW.replace('%%SRC%%', ""","""
"""  cbt:  { label:'CBT题库', name:'🎯 CBT 练习题库（逐题对齐《客舱乘务员手册》01.10）', tips:'可问：任一 CBT 练习题的原题（如「旋转座椅取出需旋转多少度」「A321机型最低配置数」）——答: 直接给出手册原文依据与精确章节号' },"""), 1)
        n += 1

    # 3) currentKbPool
    if "qaSource==='cbt'" not in s:
        if POOL_ANCHOR not in s:
            raise SystemExit('!! 未找到 currentKbPool 锚点')
        s = s.replace(POOL_ANCHOR, POOL_NEW, 1); n += 1

    # 4) 来源按钮
    if 'data-src="cbt"' not in s:
        if TAB_ANCHOR not in s:
            raise SystemExit('!! 未找到来源按钮锚点')
        s = s.replace(TAB_ANCHOR, TAB_NEW, 1); n += 1
    return s, n


def main():
    check = '--check' in sys.argv
    if not check:
        items = build_pool()
        write_source(items)
        print(f"  写出 docs/_kb_cbt_new.js：{len(items)} 条 / {os.path.getsize(SRC_OUT)} bytes")
    block = load_source()
    s = io.open(QA, encoding='utf-8', newline='').read()
    out, n = patch_qa(s, block, 0)
    if check:
        if out == s:
            print('  qa.html CBT题库 -> UP-TO-DATE'); return
        print('!! qa.html CBT题库与单一来源不一致'); sys.exit(1)
    if out == s:
        print('  qa.html CBT题库 -> UP-TO-DATE（无需改动）'); return
    io.open(QA, 'w', encoding='utf-8', newline='').write(out)
    print(f'  qa.html CBT题库 应用 {n} 处补丁（{len(s)} -> {len(out)} chars）')


if __name__ == '__main__':
    main()
