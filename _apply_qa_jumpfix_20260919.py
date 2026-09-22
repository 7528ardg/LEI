# -*- coding: utf-8 -*-
"""
「你问我答」跳转目标修复 v1 —— 幂等
=================================================================
用户反馈（2026-09-19）：在 CBT 题库里问问题，想跳去练题却发现跳不了。

根因（qa.html 原实现）：
    const isManualPool = qaSource !== 'daily';      // 定义
    const jumpBtn = (k) => {
      if (isManualPool) return '…去日常库再问…';     // ← 第一分支把**所有非日常库**截胡
      if (k.cat==='医疗急救') …
      if (销售相关) …
      return '…手册奖惩详情…';                        // 只有日常库才会走到这里
    };
  ⇒ 在 CBT / 大撤 / 乘务员手册 / 管理手册 里，按钮**恒为「去日常库再问」**，
    与用户当下想干的事（去题库练题）完全无关；日常库则兜底跳「手册奖惩」。

修复：改为「先看当前库该去哪学，再看条目分类」，并给 CBT / 大撤 的回答加顶部练题入口。

用法：python _apply_qa_jumpfix_20260919.py [--check]
⚠️ qa.html 是「源」：改完必须重建壳 + 重新装配 APK
"""
import io
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
QA = os.path.join(HERE, 'qa.html')
BAK = os.path.join(HERE, '_bak_qa_jumpfix_20260919.html')

MARK = u'去培训考核练这些题'          # 幂等特征：修复后必然存在

CHECK = '--check' in sys.argv

OLD_JUMP = u"""    const jumpBtn = (k) => {
      if (isManualPool) return `<button class="jump-btn" onclick="setQaSource('daily',null)">\U0001F4AC 去日常库再问 \u2794</button>`;
      if (k.cat==='医疗急救') return '<button class="jump-btn" onclick="jumpTo(\\'medical\\')">查看医疗急救 \u2794</button>';
      if ((k.cat||'').indexOf('销售')===0 || (k.src||'').indexOf('OJT')>=0) return '<button class="jump-btn" onclick="jumpTo(\\'daily\\')">日常问题详情 \u2794</button>';
      return '<button class="jump-btn" onclick="jumpTo(\\'manual\\')">手册奖惩详情 \u2794</button>';
    };"""

NEW_JUMP = u"""    /* \u3010\u4fee\u590d 2026-09-19\u3011\u539f\u5b9e\u73b0\u7b2c\u4e00\u5206\u652f\u662f if(isManualPool)\uff0c\u800c
       isManualPool = qaSource !== 'daily' \u2014\u2014 \u4e8e\u662f CBT / \u5927\u64a4 / \u624b\u518c \u7b49**\u6240\u6709\u975e\u65e5\u5e38\u5e93**
       \u90fd\u88ab\u5b83\u622a\u80e1\uff0c\u6309\u94ae\u6052\u4e3a\u300c\u53bb\u65e5\u5e38\u5e93\u518d\u95ee\u300d\uff0c\u4e0e\u7528\u6237\u5f53\u4e0b\u60f3\u5e72\u7684\u4e8b\uff08\u53bb\u9898\u5e93\u7ec3\u9898\uff09\u65e0\u5173\u3002
       \u73b0\u6539\u4e3a\u300c\u5148\u770b\u5f53\u524d\u5e93\u8be5\u53bb\u54ea\u5b66\uff0c\u518d\u770b\u6761\u76ee\u5206\u7c7b\u300d\u3002 */
    const jumpBtn = (k) => {
      if (qaSource === 'cbt') return '<button class="jump-btn" onclick="jumpTo(\\'quiz\\')">\U0001F3AF \u53bb\u57f9\u8bad\u8003\u6838\u7ec3\u8fd9\u4e9b\u9898 \u2794</button>';
      if (qaSource === 'dc')  return '<button class="jump-btn" onclick="jumpTo(\\'quiz\\')">\U0001F6A8 \u53bb\u5927\u64a4\u7b54\u9898 \u2794</button>';
      if (qaSource === 'ccm' || qaSource === 'mgm' || qaSource === 'svc') return '<button class="jump-btn" onclick="jumpTo(\\'manual\\')">\U0001F4D5 \u624b\u518c\u5956\u60e9\u8be6\u60c5 \u2794</button>';
      if (k.cat === '\u533b\u7597\u6025\u6551') return '<button class="jump-btn" onclick="jumpTo(\\'medical\\')">\U0001F691 \u67e5\u770b\u533b\u7597\u6025\u6551 \u2794</button>';
      if ((k.cat||'').indexOf('\u9500\u552e')===0 || (k.src||'').indexOf('OJT')>=0) return '<button class="jump-btn" onclick="jumpTo(\\'daily\\')">\U0001F4AC \u65e5\u5e38\u95ee\u9898\u8be6\u60c5 \u2794</button>';
      if (qaSource !== 'daily') return '<button class="jump-btn" onclick="setQaSource(\\'daily\\',null)">\U0001F4AC \u53bb\u65e5\u5e38\u5e93\u518d\u95ee \u2794</button>';
      return '<button class="jump-btn" onclick="jumpTo(\\'manual\\')">\U0001F4D5 \u624b\u518c\u5956\u60e9\u8be6\u60c5 \u2794</button>';
    };
    /* \u9898\u5e93 / \u5927\u64a4 \u7684\u56de\u7b54\u9876\u90e8\u7ed9\u300c\u53bb\u7ec3\u9898\u300d\u5165\u53e3 \u2014\u2014 \u53ea\u770b\u7b54\u6848\u4e0d\u5982\u76f4\u63a5\u53bb\u7ec3 */
    const practiceHint = (qaSource === 'cbt')
      ? '<div class="kbox">\U0001F3AF \u8fd9\u9898\u6765\u81ea CBT \u9898\u5e93\u3002\u60f3\u6210\u4f53\u7cfb\u7ec3\uff1f<button class="w-chip" onclick="jumpTo(\\'quiz\\')">\u53bb\u57f9\u8bad\u8003\u6838 \u2794</button>\u4e5f\u53ef\u4ee5\u76f4\u63a5\u8bf4\u300c\u6765 10 \u9053\u7b2c\u4e09\u7ae0\u7684\u9898\u300d\uff0c\u6211\u5728\u8fd9\u513f\u7ed9\u4f60\u7ec4\u5377\u3002</div>'
      : (qaSource === 'dc'
        ? '<div class="kbox">\U0001F6A8 \u5927\u64a4\u4e13\u9879\u3002\u60f3\u4e0a\u673a\u7ec3\u624b\uff1f<button class="w-chip" onclick="jumpTo(\\'quiz\\')">\u53bb\u5927\u64a4\u7b54\u9898 \u2794</button></div>'
        : '');"""

OLD_RENDER = u"""    addMsg('bot', `<div style="font-size:.7rem;color:var(--text3);margin-bottom:6px">\U0001F50E \u6765\u6e90\uff1a${currentPoolLabel()}</div>` + main.map(x ="""
NEW_RENDER = u"""    addMsg('bot', practiceHint + `<div style="font-size:.7rem;color:var(--text3);margin-bottom:6px">\U0001F50E \u6765\u6e90\uff1a${currentPoolLabel()}</div>` + main.map(x ="""


def main():
    if not os.path.exists(QA):
        print('[ERR] 找不到 qa.html')
        return 1
    src = io.open(QA, 'r', encoding='utf-8', newline='').read()
    n0 = len(src)
    already = MARK in src

    if CHECK:
        ok = already and ('isManualPool) return' not in src) and ('practiceHint' in src)
        print(u'[check] 跳转目标修复：%s' % (u'OK' if ok else u'FAIL'))
        return 0 if ok else 1

    if already:
        print(u'[skip] 已是修复版（幂等跳过）')
        return 0

    n_old = src.count(OLD_JUMP)
    if n_old != 1:
        print(u'[ERR] 旧 jumpBtn 匹配 %d 次（期望 1），中止' % n_old)
        return 1
    if src.count(OLD_RENDER) != 1:
        print(u'[ERR] 渲染行匹配 %d 次（期望 1），中止' % src.count(OLD_RENDER))
        return 1

    if not os.path.exists(BAK):
        shutil.copy2(QA, BAK)
        print(u'[bak] 已备份 -> %s' % os.path.basename(BAK))

    s = src.replace(OLD_JUMP, NEW_JUMP, 1)
    s = s.replace(OLD_RENDER, NEW_RENDER, 1)

    checks = {
        u'新 jumpBtn 到位': u'\u53bb\u57f9\u8bad\u8003\u6838\u7ec3\u8fd9\u4e9b\u9898' in s,
        u'CBT 跳 quiz': u"if (qaSource === 'cbt') return" in s,
        u'大撤跳 quiz': u"if (qaSource === 'dc')" in s,
        u'手册类跳 manual': u"qaSource === 'ccm' || qaSource === 'mgm' || qaSource === 'svc'" in s,
        u'练习提示条': u'practiceHint' in s,
        u'旧截胡分支已移除': u'if (isManualPool) return' not in s,
        u'kbReply 仍在': u'function kbReply(hits, rawText){' in s,
        u'渲染行已接 practiceHint': u"addMsg('bot', practiceHint +" in s,
        u'script 标签平衡': s.count(u'<script') == s.count(u'</script>'),
        u'html 闭合 1 份': s.count(u'</html>') == 1,
    }
    fails = [k for k, v in checks.items() if not v]
    for k, v in checks.items():
        print(u'  [%s] %s' % (u'OK' if v else u'NG', k))
    if fails:
        print(u'!! 自检失败 %d 项，未写盘' % len(fails))
        return 1

    s.encode('utf-8')
# __ATOMIC_WRITE_20260921__
    _tmp_w = (QA) + ".tmp_write"
    with io.open(_tmp_w, "w", encoding="utf-8", newline="") as _f_w:
        _f_w.write(s)
    os.replace(_tmp_w, (QA))
    print(u'[out] qa.html %d -> %d \u5b57\u7b26\uff08%+d\uff09' % (n0, len(s), len(s) - n0))
    print(u'[done] \u8bf7\u91cd\u5efa\uff1apython _build_all.py build && python _build_hosted.py\uff0c\u5e76\u91cd\u65b0\u88c5\u914d APK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
