# -*- coding: utf-8 -*-
"""生成自包含 kb-admin.html（第 10 模块 · 手册知识库管理）
1) 从 qa.html 提取四库数组（日常 KB / CCM / MGM / SVC）-> 替换模板 __BASE_*_ARR__ 占位符，保证数据与 qa 同步
2) 内联 libs/pdf.js（UMD <script>）与 libs/pdf.worker.js（独立 <script>，提前挂 window.pdfjsWorker 供 fake worker 降级）
3) 内联 libs/cmaps/*.bcmap 中文字典（base64 JSON，离线解析 CID 字体必需）
产物 kb-admin.html 为完全自包含单文件，三处外壳构建脚本直接按普通模块 gzip 打包即可。
"""
import io, os, re, json, base64

BASE = r'c:\Users\Admin\Desktop\融合版'
TPL = u'kb-admin.template.html'
OUT = u'kb-admin.html'
QA = u'qa.html'
LIBS = {u'pdfjs': u'libs/pdf.js', u'worker': u'libs/pdf.worker.js'}


def extract_bracket(text, start):
    """从 start 处（已定位到 '['）做括号配平，返回直到匹配 ']' 的完整数组源码。"""
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
            elif c == '[':
                depth += 1
            elif c == ']':
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


def build():
    qa_src = io.open(os.path.join(BASE, QA), encoding='utf-8').read()
    arrays = {
        u'__BASE_DAILY_ARR__': extract_lib_array(qa_src, r'(?m)^const KB = \['),
        u'__BASE_CCM_ARR__': extract_lib_array(qa_src, r'(?m)^window\.KB_CCM_RAW = \['),
        u'__BASE_MGM_ARR__': extract_lib_array(qa_src, r'(?m)^window\.KB_MGM_RAW = \['),
        u'__BASE_SVC_ARR__': extract_lib_array(qa_src, r'(?m)^window\.KB_SVC_RAW = \['),
    }
    tpl = io.open(os.path.join(BASE, TPL), encoding='utf-8').read()
    for ph, arr in arrays.items():
        assert ph in tpl, 'placeholder missing ' + ph
        # 占位符只允许出现一次且独立为注入点
        assert tpl.count(ph) == 1, 'placeholder not unique: ' + ph
        tpl = tpl.replace(ph, arr)

    pdfjs_src = io.open(os.path.join(BASE, LIBS[u'pdfjs']), encoding='utf-8').read()
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
    with io.open(out, 'w', encoding='utf-8') as f:
        f.write(tpl)
    print(u'写出', OUT, u'{:.2f}MB'.format(os.path.getsize(out) / 1048576.0))


if __name__ == '__main__':
    build()