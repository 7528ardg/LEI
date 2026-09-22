# -*- coding: utf-8 -*-
"""生成自包含 kb-admin.html（第 10 模块 · 手册知识库管理 + 库管理总台）
1) 从 qa.html 提取六库数组（日常 KB / CCM / MGM / SVC / 大撤 DC_KB / CBT 题库）-> 替换模板 __BASE_*_ARR__ 占位符，保证数据与 qa 同步
2) 从 beauty.html 提取销售话术库 scriptLibraryData（__BASE_SCRIPT_OBJ__）与产品库 products（__BASE_PRODUCT_ARR__），
   使「🗂 库管理」能在一个板块内集中查看/编辑/导出全部话术数据与相关手册数据
3) 内联 libs/pdf.js（UMD <script>）与 libs/pdf.worker.js（独立 <script>，提前挂 window.pdfjsWorker 供 fake worker 降级）
4) 内联 libs/cmaps/*.bcmap 中文字典（base64 JSON，离线解析 CID 字体必需）
产物 kb-admin.html 为完全自包含单文件，三处外壳构建脚本直接按普通模块 gzip 打包即可。
"""
import io, os, re, json, base64

BASE = os.path.dirname(os.path.abspath(__file__))   # 2026-09-21：不再硬编码绝对路径（原为小写 c 盘符）
TPL = u'kb-admin.template.html'
OUT = u'kb-admin.html'
QA = u'qa.html'
BEAUTY = u'beauty.html'
LIBS = {u'pdfjs': u'libs/pdf.js', u'worker': u'libs/pdf.worker.js'}


def extract_bracket(text, start, open_ch=u'[', close_ch=u']'):
    """从 start 处（已定位到 '['）做括号配平，返回直到匹配 ']' 的完整数组源码。
    2026-09-21：泛化为任意成对括号（对象用 {}），供话术库对象字面量提取复用。"""
    depth = 0
    i = start
    n = len(text)
    in_str = None
    while i < n:
        c = text[i]
        if in_str:
            if c == '\\':
                i += 2
                continue
            if c == in_str:
                in_str = None
        else:
            if c in ('"', "'", '`'):
                in_str = c
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        i += 1
    raise ValueError('bracket not closed')


def extract_lib_array(qa_src, pattern):
    m = re.search(pattern, qa_src)
    if not m:
        raise ValueError('lib array placeholder not found: ' + pattern)
    return extract_bracket(qa_src, m.end() - 1)


def safe_inline(src):
    """数据内联前的 </script> 转义：源码字符串里出现 </script> 会提前闭合脚本块。
    JS 中 <\\/script> 与 </script> 等价（\\/ 即 /），不影响数据内容。"""
    return src.replace(u'</script>', u'<\\/script>').replace(u'</SCRIPT>', u'<\\/SCRIPT>')


def build():
    qa_src = io.open(os.path.join(BASE, QA), encoding='utf-8').read()
    beauty_src = io.open(os.path.join(BASE, BEAUTY), encoding='utf-8').read()
    arrays = {
        u'__BASE_DAILY_ARR__': extract_lib_array(qa_src, r'(?m)^const KB = \['),
        u'__BASE_CCM_ARR__': extract_lib_array(qa_src, r'(?m)^window\.KB_CCM_RAW = \['),
        u'__BASE_MGM_ARR__': extract_lib_array(qa_src, r'(?m)^window\.KB_MGM_RAW = \['),
        u'__BASE_SVC_ARR__': extract_lib_array(qa_src, r'(?m)^window\.KB_SVC_RAW = \['),
        u'__BASE_DC_ARR__': extract_lib_array(qa_src, r'(?m)^window\.DC_KB = \['),
        u'__BASE_CBT_ARR__': extract_lib_array(qa_src, r'(?m)^window\.KB_CBT_RAW = \['),
        u'__BASE_PRODUCT_ARR__': extract_lib_array(beauty_src, r'(?m)^\s*const products = \['),
    }
    # 销售话术库是「栏目 → scripts」的嵌套对象，整块取出后在模板里展平为条目列表
    m_script = re.search(r'(?m)^\s*const scriptLibraryData = \{', beauty_src)
    if not m_script:
        raise ValueError('scriptLibraryData not found in ' + BEAUTY)
    arrays[u'__BASE_SCRIPT_OBJ__'] = extract_bracket(beauty_src, m_script.end() - 1, u'{', u'}')

    tpl = io.open(os.path.join(BASE, TPL), encoding='utf-8', newline='').read()
    for ph, arr in arrays.items():
        assert ph in tpl, 'placeholder missing ' + ph
        # 占位符只允许出现一次且独立为注入点
        assert tpl.count(ph) == 1, 'placeholder not unique: ' + ph
        tpl = tpl.replace(ph, safe_inline(arr))

    pdfjs_src = io.open(os.path.join(BASE, LIBS[u'pdfjs']), encoding='utf-8', newline='').read()
    worker_raw = io.open(os.path.join(BASE, LIBS[u'worker']), 'rb').read().decode('utf-8')
    assert '__PDFJS_SRC__' in tpl, 'placeholder missing __PDFJS_SRC__'
    assert tpl.count('__PDFJS_SRC__') == 1, 'placeholder not unique: __PDFJS_SRC__'
    tpl = tpl.replace('__PDFJS_SRC__', pdfjs_src)
    # worker 源码内联为独立 <script>（提前挂 window.pdfjsWorker，供 fake worker 降级使用）
    # 防御：源码字符串中出现 </script> 会提前闭合脚本块，统一转义（JS 中 \/ 等价 /）
    assert '__PDFWORKER_SRC__' in tpl, 'placeholder missing __PDFWORKER_SRC__'
    assert tpl.count('__PDFWORKER_SRC__') == 1, 'placeholder not unique: __PDFWORKER_SRC__'
    safe_worker = worker_raw.replace(u'</script>', u'<\\/script>').replace(u'</SCRIPT>', u'<\\/SCRIPT>')
    tpl = tpl.replace('__PDFWORKER_SRC__', safe_worker)
    # CMap 中文字典 -> base64 JSON（离线解析 CID 字体必需）
    cmaps = {}
    cmap_dir = os.path.join(BASE, u'libs', u'cmaps')
    for fn in sorted(os.listdir(cmap_dir)):
        if fn.endswith(u'.bcmap'):
            name = fn[:-len(u'.bcmap')]
            cmaps[name] = base64.b64encode(io.open(os.path.join(cmap_dir, fn), 'rb').read()).decode('ascii')
    assert '__INLINE_CMAPS__' in tpl, 'placeholder missing __INLINE_CMAPS__'
    assert tpl.count('__INLINE_CMAPS__') == 1, 'placeholder not unique: __INLINE_CMAPS__'
    tpl = tpl.replace('__INLINE_CMAPS__', json.dumps(cmaps, ensure_ascii=False))

    out = os.path.join(BASE, OUT)
    tmp = out + '.tmp_write'
    with io.open(tmp, 'w', encoding='utf-8', newline='') as f:   # 原子写 + 固定 LF
        f.write(tpl)
    os.replace(tmp, out)
    print(u'写出', OUT, u'{:.2f}MB'.format(os.path.getsize(out) / 1048576.0))


if __name__ == '__main__':
    build()