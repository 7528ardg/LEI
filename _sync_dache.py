# -*- coding: utf-8 -*-
"""大撤专项知识库同步（单一来源 docs/_dache_kb.js → qa.html / quiz.html）
用法：python _sync_dache.py            # 同步
      python _sync_dache.py --check    # 校验（内容不一致则非零退出，供 _build_all 守护）
标记块：DC_KB_BEGIN / DC_KB_END

2026-09-13 图片支持：
- 单一来源中撤离程序卡含 <img src="__DACHE_IMG_<名>__"> 占位符；
- quiz.html（场景库）：占位符替换为 `assets/img/<md5(base64)[:8]>.jpg` 站内相对路径
  （把图片以内容寻址方式落盘到 assets/img/，与 `_extract_inline_images_20260921.py`
   完全同口径；**不再内联 data URI**），长图可点击放大；
- qa.html（你问我答）：整块剥离 <div class="dc-imgs">…</div>，保持 qa 轻量（文本知识完整保留）。

2026-09-22 修复「构建顺序互踩」：
  原先 quiz.html 侧替换为 data URI，而构建链第 20 步 `_extract_inline_images_20260921.py`
  又会把这些大图抽成 assets/img/*，导致下一轮 `_sync_dache.py --check` 必然报
  「quiz.html 与单一来源不一致」→ 整条构建链在第 5 步硬停。
  现改为本脚本直接产出「已外置」形态（并按需把图片落盘），与抽取器结果逐字节一致，
  check 稳定、extract 无事可做（幂等）。
"""
import io, os, re, sys, base64, hashlib

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'docs', '_dache_kb.js')
IMG_DIR = os.path.join(HERE, 'docs', 'dache_img')

BEGIN = '/* DC_KB_BEGIN（同步标记块，请勿在标记块外修改以下内容） */'
END = '/* DC_KB_END（同步标记块结束） */'

IMG_RE = re.compile(r'__DACHE_IMG_([A-Za-z0-9_]+)__')
IMGBLOCK_RE = re.compile(r'<div class="dc-imgs">.*?</div></div>', re.S)

def load_images():
    imgs = {}
    if os.path.isdir(IMG_DIR):
        for fn in os.listdir(IMG_DIR):
            if fn.lower().endswith('.jpg'):
                data = io.open(os.path.join(IMG_DIR, fn), 'rb').read()
                imgs[fn[:-4]] = 'data:image/jpeg;base64,' + base64.b64encode(data).decode('ascii')
    return imgs

def rel_url_of(key, imgs):
    """把占位符名解析为站内相对路径 assets/img/<md5(base64)[:8]>.jpg，并按需落盘。

    哈希口径与 `_extract_inline_images_20260921.py` 保持一致：
      hash8 = md5(base64 文本, ascii)[:8]（**不是**原始字节的 md5）。
    内容寻址 → 同一图片重复引用只落一份；文件已存在则不重复写（幂等）。
    """
    uri = imgs[key]
    b64 = uri.split(',', 1)[1]
    h8 = hashlib.md5(b64.encode('ascii')).hexdigest()[:8]
    outdir = os.path.join(HERE, 'assets', 'img')
    out = os.path.join(outdir, h8 + '.jpg')
    if not os.path.exists(out):
        if not os.path.isdir(outdir):
            os.makedirs(outdir)
        with open(out, 'wb') as f:
            f.write(base64.b64decode(b64))
    return 'assets/img/%s.jpg' % h8


def transform(block, target, imgs):
    if target == 'quiz':
        def rep(m):
            key = m.group(1)
            if key in imgs:
                return rel_url_of(key, imgs)
            print('  !! 缺少图片 docs/dache_img/%s.jpg（占位符置空）' % key)
            return ''
        return IMG_RE.sub(rep, block)
    # qa：图片块替换为场景库指引（保持轻量，同时与培训考核·场景库联动）
    hint = ('<div class="kbox" style="background:#f0f9ff;border:1px solid #bae6fd">'
            '📎 本条流程图已内嵌在 <strong>培训考核 → 场景库 → 大撤专项</strong> 对应卡片中，'
            '点击图片可全屏放大查看。</div>')
    return IMGBLOCK_RE.sub(hint, block)

def main():
    check = '--check' in sys.argv
    src = io.open(SRC, encoding='utf-8').read()
    i, j = src.find(BEGIN), src.find(END)
    if i < 0 or j < 0 or j < i:
        print('!! docs/_dache_kb.js 缺少 DC_KB_BEGIN/END 标记块')
        sys.exit(1)
    block = src[i:j + len(END)]
    imgs = load_images()
    fails = 0
    for name in ['qa.html', 'quiz.html']:
        p = os.path.join(HERE, name)
        s = io.open(p, encoding='utf-8', newline='').read()
        a = s.find(BEGIN)
        b = s.find(END)
        if a < 0 or b < 0 or b < a:
            print('!! %s 缺少 DC_KB 标记块（需先手工植入骨架）' % name)
            fails += 1
            continue
        want = transform(block, 'quiz' if name == 'quiz.html' else 'qa', imgs)
        cur = s[a:b + len(END)]
        if cur == want:
            print('  %s -> UP-TO-DATE' % name)
        elif check:
            print('!! %s 与单一来源不一致（需运行 python _sync_dache.py）' % name)
            fails += 1
        else:
            s = s[:a] + want + s[b + len(END):]
            io.open(p, 'w', encoding='utf-8', newline='').write(s)
            print('  %s -> SYNCED' % name)
    if fails:
        sys.exit(1)
    print('大撤专项同步完成。')

if __name__ == '__main__':
    main()
