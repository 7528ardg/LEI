# -*- coding: utf-8 -*-
"""日常问题板块图片注入构建：压缩 PPT 截图 -> base64 -> 注入 daily.template.html 生成 daily.html"""
import base64
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(HERE, 'ppt_images')
TPL = os.path.join(HERE, 'daily.template.html')
OUT = os.path.join(HERE, 'daily.html')

MAX_SIDE = 1000
JQ = 85

# key -> 源文件名 映射（16 张内容图，跳过装饰/logo/重复/素材图）
MAPPING = {
    'm04z1': '04yue_s03.jpg',
    'm04z2': '04yue_s03_71783.png',
    'm04b1': '04yue_s04_3665.jpg',
    'm04g1': '04yue_s06_89210.png',
    'm04g2': '04yue_s06_74323.png',
    'm04j1': '04yue_s06_74057.png',
    'm04x1': '04yue_s06_83314.png',
    'm05p1': '05yue_s03_12140.png',
    'm05s1': '05yue_s07_78443.png',
    'm05x1': '05yue_s09_4404.jpg',
    'm07k1': '07yue_s05_72925.png',
    'm07s1': '07yue_s07_84783.png',
    'm07s2': '07yue_s07_26100.png',
    'm07s3': '07yue_s07_8761.png',
    'm08t1': '08yue_s04_56162.png',
}

def compress_to_jpeg(path):
    from PIL import Image
    im = Image.open(path)
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA')
        bg = Image.new('RGB', im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert('RGB')
    w, h = im.size
    if max(w, h) > MAX_SIDE:
        ratio = MAX_SIDE / float(max(w, h))
        im = im.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=JQ, optimize=True)
    return buf.getvalue()

def build():
    from PIL import Image
    imgs = {}
    total = 0
    for key, fn in MAPPING.items():
        p = os.path.join(IMG_DIR, fn)
        if not os.path.exists(p):
            print('MISSING:', fn)
            continue
        data = compress_to_jpeg(p)
        total += len(data)
        imgs[key] = 'data:image/jpeg;base64,' + base64.b64encode(data).decode('ascii')
        print('{:<8} {:>8.1f} KB'.format(key, len(data) / 1024))
    print('images total: {:.2f} MB'.format(total / 1048576.0))

    t = io.open(TPL, 'r', encoding='utf-8').read()
    placeholder = '__IMG_DATA__'
    assert placeholder in t, 'placeholder missing!'
    repl = json.dumps(imgs, ensure_ascii=False)
    t = t.replace(placeholder, repl)
    with io.open(OUT, 'w', encoding='utf-8') as f:
        f.write(t)
    print('写出', OUT, '{:.2f} MB'.format(os.path.getsize(OUT) / 1048576.0))

if __name__ == '__main__':
    build()