# -*- coding: utf-8 -*-
"""kb-admin · AI 客户端本地化（2026-09-19，替代原「AI 降级链 v3 对齐」）
=================================================================
背景：原脚本把 kb-admin 的 aiChat/aiChatOnce 换成 v3 降级链（含内置共享 Key 默认值、
      glm-4.7-flash 服务商表）。用户 2026-09-19 决定「彻底无密钥」+「删除 4.7 flash」，
      于是本脚本职责改为：把这套外部 AI 客户端整体替换为**本地模式**实现。

改动：
  ① 删除 aiChat / aiChatOnce 的外部调用与一切密钥常量（含内置 Key、服务商端点表、模型表）
  ② hasAICfg() 恒 false → 上层「AI 生成候选」按钮走既有的失败分支（人工补写/覆盖层导入）
  ③ 保留函数名与调用方签名不变，避免动到业务代码

⚠️ 目标 kb-admin.html 由 _build_kbadmin.py 从本模板生成 → 改完必须重建（_build_all.py build）
用法：python _apply_kbadmin_ai_chain_20260919.py [--check]
"""
import io
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')


def _atomic_write(path, text):
    tmp = path + u'.tmp_write'
    io.open(tmp, 'w', encoding='utf-8', newline='').write(text)
    os.replace(tmp, path)


HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(HERE, 'kb-admin.template.html')
BAK = os.path.join(HERE, '_bak_kbadmin_ai_20260919.html')

END = u'async function aiGenCandidate(diff){'
MARK = u'/*__KBADMIN_LOCALMODE_v1__*/'
# 可能出现的三种历史形态的段首（原文 / v3 注释头 / v3 常量行）
START_CANDS = [
    u'/* ===== AI 降级链 v3（2026-09-19 与 qa / beauty / quiz 对齐）=====',
    u'var AI_FALLBACK_MODELS = ',
    u'async function aiChat(messages){',
]

HAS_OLD = u"function hasAICfg(){ try{ const c=JSON.parse(localStorage.getItem('spring_ai_cfg')||'{}'); return !!(c.apiKey); }catch(e){ return false; } }"
HAS_NEW = u"function hasAICfg(){ return false; /* 本地模式：不读取任何密钥，AI 生成候选改走人工补写 */ }"

TOAST_OLD = u"  if(!hasAICfg()){ toast('未配置 AI（spring_ai_cfg），无法批量生成', true); return; }"
TOAST_NEW = u"  if(!hasAICfg()){ toast('本版本为本地知识库模式：不接入外部 AI，请手动补写后勾选入库', true); return; }"

NEW = u'''/*__KBADMIN_LOCALMODE_v1__*/
/* ===== 本地模式（2026-09-19：彻底无密钥）=====
   该模块的「AI 生成候选 Q/A」不再调用任何外部模型：源码零密钥、运行时零外发。
   保留同名函数（aiChat / aiChatOnce），调用方签名不变；调用即抛出明确提示，
   由上层原有的失败分支回落到「人工补写 / 覆盖层导入」路径。
   本块由 _apply_kbadmin_ai_chain_20260919.py 维护，直接改 kb-admin.html 会被重建冲掉。 */
var AI_LOCAL_ONLY = true;
async function aiChat(messages){
  throw new Error('本地知识库模式：本版本不接入外部 AI，请手动补写 Q/A 或从覆盖层导入');
}
async function aiChatOnce(messages, modelOverride){
  throw new Error('本地知识库模式：本版本不接入外部 AI');
}
'''


def main():
    if not os.path.exists(TPL):
        print(u'[ERR] 找不到 kb-admin.template.html')
        return 1
    src = io.open(TPL, 'r', encoding='utf-8', newline='').read()

    if u'--check' in sys.argv:
        ok = (MARK in src and u'aiChat' in src and u'4986b927' not in src
              and u'glm-4.7' not in src and u'AI_FALLBACK_MODELS' not in src)
        print(u'[check] kb-admin AI 本地化：%s' % (u'OK' if ok else u'FAIL'))
        return 0 if ok else 1

    if MARK in src and u'4986b927' not in src:
        print(u'[skip] 已是本地模式（幂等跳过）')
        return 0

    j = src.find(END)
    if j < 0:
        print(u'[ERR] 找不到 %s' % END)
        return 1
    starts = [src.find(s) for s in START_CANDS if src.find(s) >= 0 and src.find(s) < j]
    if not starts:
        print(u'[ERR] 找不到 AI 段落起点')
        return 1
    i = min(starts)
    if u'aiChat' not in src[i:j]:
        print(u'[ERR] 待替换段落不含 aiChat 特征，中止以免误伤')
        return 1

    if not os.path.exists(BAK):
        shutil.copy2(TPL, BAK)
        print(u'[bak] -> %s' % os.path.basename(BAK))

    s = src[:i] + NEW + src[j:]
    n_has = s.count(HAS_OLD)
    if n_has == 1:
        s = s.replace(HAS_OLD, HAS_NEW, 1)
    n_toast = s.count(TOAST_OLD)
    if n_toast == 1:
        s = s.replace(TOAST_OLD, TOAST_NEW, 1)

    checks = {
        u'本地模式块 1 份': s.count(MARK) == 1,
        u'零内置 Key': u'4986b927' not in s,
        u'零 4.7 引用': u'glm-4.7' not in s and u'glm47' not in s,
        u'降级链常量已移除': u'AI_FALLBACK_MODELS' not in s,
        u'hasAICfg 恒 false': u'function hasAICfg(){ return false;' in s,
        u'aiGenCandidate 仍在': END in s,
        u'调用方签名未变': u"await aiChat([{ role:'system', content: sys }" in s,
        u'batch toast 已本地化': u'本版本为本地知识库模式' in s,
        u'script 配对不变': (s.count(u'<script') - s.count(u'</script>')) == (src.count(u'<script') - src.count(u'</script>')),
    }
    fails = [k for k, v in checks.items() if not v]
    for k, v in checks.items():
        print(u'  [%s] %s' % (u'OK' if v else u'NG', k))
    print(u'  （hasAICfg 命中 %d / batch toast 命中 %d）' % (n_has, n_toast))
    if fails:
        print(u'!! 自检失败 %d 项，未写盘' % len(fails))
        return 1
    _atomic_write(TPL, s)
    print(u'[ok] kb-admin.template.html %d -> %d 字符（已本地化）' % (len(src), len(s)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
