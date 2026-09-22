# -*- coding: utf-8 -*-
"""你问我答 · 琴模块副本去重（2026-09-19，一次性清理 + 幂等）
--------------------------------------------------------------------------------
问题：_apply_pet.py 注入的琴模块（_piano_player.js）是**无 id 的裸 <script>**，
      而 --replace 的剥离规则只按 id 剥 `pet-stage-js`，抓不到琴模块 →
      每跑一次 --replace 净增一份，qa.html 实测累积 6 份（43.9KB 死代码；
      同名 window.CCPiano 后者覆盖前者，只有最后一份生效）。

修法：只保留最后一份（最新版，带 short 字段），并补上 id="piano-player-js"，
      与 _apply_pet.py 新加的剥离规则对齐 —— 从此该块恰好 1 份。
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

def _atomic_write(path, text):
    """先写临时文件再原子替换：任何编码/写入异常都不会破坏源文件。"""
    tmp = path + u'.tmp_write'
    io.open(tmp, 'w', encoding='utf-8', newline='').write(text)
    os.replace(tmp, path)
ROOT = os.path.dirname(os.path.abspath(__file__))
QA = os.path.join(ROOT, u'qa.html')
PID = u'id="piano-player-js"'
PAT = re.compile(r'<script(?:\s+id="piano-player-js")?>\s*/\*[^*]*秋分琴房[\s\S]*?</script>')


def main():
    if not os.path.exists(QA):
        print(u'[ERR] 找不到 qa.html')
        return 1
    s = io.open(QA, 'r', encoding='utf-8', newline='').read()
    ms = list(PAT.finditer(s))
    print(u'[in] 琴模块副本 %d 份' % len(ms))
    if not ms:
        print(u'[ERR] 未找到琴模块，中止（避免误删）')
        return 1
    if len(ms) == 1 and PID in ms[0].group(0):
        print(u'[skip] 已是 1 份且带 id，无需处理')
        return 0

    keep = ms[-1]
    body = keep.group(0)
    if PID not in body:
        body = body.replace(u'<script>', u'<script ' + PID + u'>', 1)

    # ⚠️ 只能删除「被匹配到的副本本身」，副本之间的内容必须原样保留
    #    （2026-09-19 踩坑：曾用 head+body+tail 合并，把夹在琴模块之间的
    #      pet-stage-js 5.5MB 形象/3D 区块一并删掉，文件 7.30MB → 1.82MB）
    parts, last = [], 0
    for i, m in enumerate(ms):
        parts.append(s[last:m.start()])
        if i == len(ms) - 1:
            parts.append(body)          # 仅保留最后一份，并带上 id
        last = m.end()
    parts.append(s[last:])
    new = (u'').join(parts)
    new = re.sub(r'\n{3,}', u'\n\n', new)

    # 长度守卫：只该少掉 5 份琴模块，净减必须远小于文件的一半
    if len(s) - len(new) > 60000:
        print(u'[ERR] 净减 %d 字符，超出预期（5 份琴模块约 37KB），未写盘' % (len(s) - len(new)))
        return 1

    n_after = len(PAT.findall(new))
    if n_after != 1:
        print(u'[ERR] 去重后仍有 %d 份，未写盘' % n_after)
        return 1
    if u'window.CCPiano' not in new or new.count(u'window.CCPiano = (function()') != 1:
        print(u'[ERR] CCPiano 定义份数异常，未写盘')
        return 1
    _atomic_write(QA, new)
    print(u'[ok] qa.html %.2f MB -> %.2f MB（琴模块 6 份 -> 1 份）'
          % (len(s) / 1048576, len(new) / 1048576))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
