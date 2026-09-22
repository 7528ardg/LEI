# -*- coding: utf-8 -*-
"""行尾归一：把源与产物文本文件里的 CRLF 统一折回 LF（2026-09-21）
--------------------------------------------------------------------------------
为什么需要它（真实故障复盘）：
  仓库 core.autocrlf=true 且无 .gitattributes。只要有一次 `git checkout -- <文件>`
  （或 GUI 里的「还原/丢弃更改」），工作区文件就会被 git 写成 CRLF。
  而所有补丁脚本都按 LF 匹配标记块边界，例如 _apply_nav_20260917.py 找的是
  '\n/*__NAV_DESIGN_20260917_CSS__BEGIN' … 'END*/\n'。
  CRLF 一旦进来，BEGIN 会因为前面恰好有 \n 而侥幸命中，END 却永远找不到 →
  抛「!! 标记块不完整：缺收口 END*/」→ 整条构建链在导航那一步硬停。

  2026-09-21 实测：index.html / spring-assistant.html / 客舱小助手（离线完整版）.html /
  在线版 两个壳，5 个文件全是 CRLF（mtime 15:56），HEAD 版本却是纯 LF。

它做什么：
  · 把 .html/.htm/.template.html/.py/.js/.css/.md/.json/.csv 里的 \r\n 折成 \n；
  · **不碰** .bat/.cmd/.txt（Windows 脚本与说明文本故意用 CRLF）；
  · 只有真的含 CRLF 才写盘（幂等、零副作用），写盘走原子替换 + newline=''。

用法：
  python _normalize_lf_20260921.py            # 归一
  python _normalize_lf_20260921.py --check    # 只体检（有 CRLF 则 exit 1）
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.abspath(__file__))

EXTS = ('.html', '.htm', '.py', '.js', '.css', '.md', '.json', '.csv')
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', 'dist', 'build', '.workbuddy',
             # 2026-09-21 补：冻结归档/历史备份/第三方仓库/打包产物目录不该被行尾归一改写，
             # 否则每次构建第一步都会悄悄改动"已冻结"的快照内容。
             '_archive_20260921', '_legacy', '_pp_repo', 'PakePlus-iOS-main',
             '_retired_glm47', '_trash_20260915', 'cbt_edge_profile'}
# 前缀匹配：_bak* / _archive_* / _trash_* 一律跳过
SKIP_DIR_PREFIX = ('_bak', '_archive_', '_trash_')
SKIP_SUFFIX = ('.bat', '.cmd', '.txt', '.gz', '.zip', '.png', '.jpg', '.jpeg', '.webp',
               '.ico', '.svg', '.woff', '.woff2', '.ttf', '.mp4', '.glb', '.pdf', '.xlsx')
# 这些是第三方/生成的大文件，折行没有收益也有风险，跳过
SKIP_FILES = {'_serve.tmp.html'}

# 一次性临时文件（原子写产物 .tmp_write、构建中间 _*_tmp*.js / __*_tmp*.js）：
# 体积可能达 20MB+ 且为瞬态生成物，既不纳入行尾归一改写，也不纳入 --check 体检。
SKIP_TEMP = ('.tmp_write',)


def candidates():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS and not d.startswith(SKIP_DIR_PREFIX)]
        for fn in filenames:
            if fn in SKIP_FILES:
                continue
            if fn.endswith(SKIP_SUFFIX):
                continue
            if not fn.endswith(EXTS):
                continue
            # 跳过一次性临时文件（瞬态，无需归一 / 无需体检）
            if fn.endswith(SKIP_TEMP):
                continue
            if fn.endswith('.js') and '_tmp' in fn:
                continue
            yield os.path.join(dirpath, fn)


# D1：字节缓存，scan 与 normalize 复用同一份已读内容，避免每个文件整读两次（双倍内存 + IO）。
_BYTE_CACHE = {}

def _read_bytes(p):
    b = _BYTE_CACHE.get(p)
    if b is None:
        with io.open(p, 'rb') as f:
            b = f.read()
        _BYTE_CACHE[p] = b
    return b


def scan():
    """返回 [(绝对路径, CRLF 行数, 相对路径)]，只列真正含 CRLF 的。单次读取并缓存。"""
    hits = []
    for p in candidates():
        try:
            b = _read_bytes(p)
        except Exception:
            continue
        n = b.count(b'\r\n')
        if n:
            hits.append((p, n, os.path.relpath(p, ROOT)))
    return hits


def normalize(hits):
    done = []
    for p, n, rel in hits:
        try:
            b = _read_bytes(p)
            b2 = b.replace(b'\r\n', b'\n')
            if b2 == b:
                continue
            tmp = p + '.tmp_write'
            with io.open(tmp, 'wb') as f:
                f.write(b2)
            os.replace(tmp, p)
            done.append((rel, n))
        except Exception as e:
            print(u'  [ERR] %s -> %s' % (rel, e))
    return done


def main():
    hits = scan()
    if not hits:
        print(u'[ok] 全仓库文本文件已是 LF，无需处理')
        return 0
    print(u'[!] 发现 %d 个文件含 CRLF：' % len(hits))
    for p, n, rel in hits:
        print(u'    %-46s CRLF=%d' % (rel, n))
    done = normalize(hits)
    print(u'[ok] 已折回 LF：%d 个' % len(done))
    left = scan()
    if left:
        print(u'!! 仍有 %d 个未归一' % len(left))
        return 1
    return 0


if __name__ == '__main__':
    if '--check' in sys.argv:
        h = scan()
        if h:
            print(u'[check] 行尾归一：FAIL（%d 个文件含 CRLF，首个：%s）' % (len(h), h[0][2]))
            raise SystemExit(1)
        print(u'[check] 行尾归一：OK（全部 LF）')
        raise SystemExit(0)
    raise SystemExit(main())
