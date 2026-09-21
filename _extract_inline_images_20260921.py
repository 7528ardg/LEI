# -*- coding: utf-8 -*-
"""把模块 HTML 里的内联 base64 图片抽成独立文件（幂等）。

用法：
  python _extract_inline_images_20260921.py --dry-run     # 只看统计，不落盘
  python _extract_inline_images_20260921.py               # 执行抽取
  python _extract_inline_images_20260921.py --inline X.html  # 反向：把 assets/img/* 还原成 data URL（给单文件离线版用）

设计要点：
- 只抽大图（默认 base64 载荷 > 6000 字符 ≈ 4.4KB），小图标继续内联，避免请求数暴增
- 图片按内容 md5 去重，统一放 assets/img/<hash>.<ext>；所有模块 HTML 都在站点根目录，
  故相对路径 assets/img/... 在 iframe 内、单页直开两种场景都能解析
- 先备份原文件到 _bak_inlineimg_20260921/，再原子写（.tmp_write + os.replace）
- 幂等：文件里没有 data:image 大图就跳过；manifest 记 _inline_img_manifest.json
"""
import os, re, sys, json, shutil, hashlib, base64

ROOT = os.path.dirname(os.path.abspath(__file__))
BAK = os.path.join(ROOT, '_bak_inlineimg_20260921')
OUTDIR = os.path.join(ROOT, 'assets', 'img')
MANIFEST = os.path.join(ROOT, '_inline_img_manifest.json')

TARGETS = [
    'qa.html', 'cc-home.html', 'daily.html', 'beauty.html', 'risk-lite.html',
    'medical.html', 'quiz.html', 'performance.html', 'kb-admin.html',
    'manual.html', 'report.html', 'issues.html',
]
MIN_PAYLOAD = 6000

RX = re.compile(r'data:image/(png|jpeg|jpg|gif|webp|svg\+xml);base64,([A-Za-z0-9+/=]+)')
EXT = {'png': 'png', 'jpeg': 'jpg', 'jpg': 'jpg', 'gif': 'gif', 'webp': 'webp', 'svg+xml': 'svg'}


def rel_url(hash8, ext):
    return 'assets/img/%s.%s' % (hash8, ext)


def scan(path):
    s = open(path, encoding='utf-8', newline='').read()
    hits = []
    for m in RX.finditer(s):
        payload = m.group(2)
        if len(payload) < MIN_PAYLOAD:
            continue
        hits.append((m.start(), m.end(), m.group(1), payload))
    return s, hits


def extract(args):
    total_saved = 0
    manifest = {}
    if os.path.exists(MANIFEST):
        try:
            manifest = json.load(open(MANIFEST, encoding='utf-8'))
        except Exception:
            manifest = {}

    for name in TARGETS:
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            continue
        s, hits = scan(path)
        if not hits:
            if args.verbose:
                print('%-18s 无大图（跳过）' % name)
            continue
        before = len(s)
        saved = sum(len(h[3]) for h in hits)
        if args.dry_run:
            print('%-18s 大图 %2d 张  base64 %8.2f MB  原文件 %8.2f MB' %
                  (name, len(hits), saved / 1048576.0, before / 1048576.0))
            total_saved += saved
            continue

        if not os.path.isdir(BAK):
            os.makedirs(BAK)
        bak = os.path.join(BAK, name)
        if not os.path.exists(bak):
            shutil.copy2(path, bak)
        if not os.path.isdir(OUTDIR):
            os.makedirs(OUTDIR)

        pieces = []
        pos = 0
        for start, end, mime, payload in hits:
            hash8 = hashlib.md5(payload.encode('ascii')).hexdigest()[:8]
            ext = EXT[mime]
            url = rel_url(hash8, ext)
            fpath = os.path.join(ROOT, url.replace('/', os.sep))
            if not os.path.exists(fpath):
                try:
                    raw = base64.b64decode(payload)
                except Exception:
                    continue
                tmp = fpath + '.tmp_write'
                with open(tmp, 'wb') as f:
                    f.write(raw)
                os.replace(tmp, fpath)
            manifest.setdefault(url, {'bytes': len(payload) * 3 // 4, 'src': name, 'mime': mime})
            pieces.append(s[pos:start])
            pieces.append(url)
            pos = end
        pieces.append(s[pos:])
        new = ''.join(pieces)

        tmp = path + '.tmp_write'
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            f.write(new)
        os.replace(tmp, path)
        after = len(new)
        print('%-18s 抽 %2d 张 → 文件 %8.2f MB → %8.2f MB（-%.2f MB，-%.0f%%）' %
              (name, len(hits), before / 1048576.0, after / 1048576.0,
               (before - after) / 1048576.0, (before - after) * 100.0 / before))
        total_saved += saved

    if not args.dry_run:
        tmp = MANIFEST + '.tmp_write'
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)
        os.replace(tmp, MANIFEST)
        print('manifest: %d 个文件 → %s' % (len(manifest), MANIFEST))
    print('合计抽出 base64 %.2f MB' % (total_saved / 1048576.0))


def inline_back(path):
    """把 assets/img/* 还原成 data URL（给单文件离线版用）。"""
    s = open(path, encoding='utf-8', newline='').read()
    mani = json.load(open(MANIFEST, encoding='utf-8')) if os.path.exists(MANIFEST) else {}
    rx = re.compile(r'assets/img/([0-9a-f]{8})\.(png|jpg|jpeg|gif|webp|svg)')
    n = 0

    def rep(m):
        nonlocal n
        url = m.group(0)
        f = os.path.join(ROOT, url.replace('/', os.sep))
        if not os.path.exists(f):
            return url
        mime = 'image/' + (m.group(2) if m.group(2) != 'jpg' else 'jpeg')
        if m.group(2) == 'svg':
            mime = 'image/svg+xml'
        b64 = base64.b64encode(open(f, 'rb').read()).decode('ascii')
        n += 1
        return 'data:%s;base64,%s' % (mime, b64)

    out = rx.sub(rep, s)
    tmp = path + '.tmp_write'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(out)
    os.replace(tmp, path)
    print('%s 内嵌回 %d 张，%8.2f MB' % (os.path.basename(path), n, len(out) / 1048576.0))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--verbose', action='store_true')
    ap.add_argument('--inline', default=None, help='把某文件里的 assets/img/* 还原成 data URL')
    args = ap.parse_args()
    if args.inline:
        inline_back(args.inline if os.path.isabs(args.inline) else os.path.join(ROOT, args.inline))
        return
    extract(args)


if __name__ == '__main__':
    main()
