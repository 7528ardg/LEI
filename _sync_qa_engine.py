# -*- coding: utf-8 -*-
"""qa.html 广播引擎同步（2026-09-09）：从 beauty.html 抽取最新 talkShowEngine 整块
重命名 qaTalkEngine 并替换 qa 中的旧块；同时 FEST_OPTS 加「自动匹配」默认 auto。
CRLF 原子写盘。
"""
import io

BEAUTY = r'c:\Users\Admin\Desktop\融合版\beauty.html'
QA = r'c:\Users\Admin\Desktop\融合版\qa.html'
CR = '\r\n'


def crlf(s):
    return s.replace('\n', CR)


with io.open(BEAUTY, 'r', encoding='utf-8', newline='') as f:
    beauty = f.read()
with io.open(QA, 'r', encoding='utf-8', newline='') as f:
    qa = f.read()

# 抽取 beauty 引擎
start_m = 'const talkShowEngine = (function(){'
s = beauty.index(start_m)
end_m = 'window.talkShowEngine = talkShowEngine;'
e = beauty.index(end_m) + len(end_m)
src = beauty[s:e].replace('talkShowEngine', 'qaTalkEngine').replace('beautySceneEngine.complianceClean', 'qaComplianceClean')

# 替换 qa 内旧引擎块（起止标记各只出现一次）
qs = qa.index('const qaTalkEngine = (function(){')
qe = qa.index('window.qaTalkEngine = qaTalkEngine;') + len('window.qaTalkEngine = qaTalkEngine;')
qa = qa[:qs] + src + qa[qe:]

# FEST_OPTS 顶部加「自动」
old_fest = crlf("const FEST_OPTS = [ {k:'none', l:'常规航班'}, {k:'spring', l:'🧧 春节'}, {k:'midautumn', l:'🥮 中秋'}, {k:'national', l:'🇨🇳 国庆'}, {k:'newyear', l:'🎆 元旦跨年'}, {k:'valentine', l:'💝 情人节'}, {k:'mothers', l:'🌸 母亲节'} ];")
n = qa.count(old_fest)
assert n == 1, 'FEST_OPTS 锚点 count=%d' % n
new_fest = crlf("const FEST_OPTS = [ {k:'auto', l:'🎯 自动匹配（今日节假日/节气）'}, {k:'none', l:'常规航班'}, {k:'spring', l:'🧧 春节'}, {k:'midautumn', l:'🥮 中秋'}, {k:'national', l:'🇨🇳 国庆'}, {k:'newyear', l:'🎆 元旦跨年'}, {k:'valentine', l:'💝 情人节'}, {k:'mothers', l:'🌸 母亲节'}, {k:'qingming', l:'🌿 清明'}, {k:'yuanxiao', l:'🏮 元宵节'}, {k:'duanwu', l:'🎋 端午节'}, {k:'qixi', l:'🌌 七夕'}, {k:'chongyang', l:'⛰ 重阳节'}, {k:'laba', l:'🍲 腊八节'}, {k:'xiaonian', l:'🧹 小年'}, {k:'chuxi', l:'🏮 除夕'}, {k:'women', l:'🌷 妇女节'}, {k:'labor', l:'🛠 劳动节'}, {k:'teachers', l:'🍎 教师节'} ];")
qa = qa.replace(old_fest, new_fest, 1)

# wizard 默认 fest auto
old_wz = crlf("const wizard = { active:false, cats:[], dura:'3', budget:'mid', style:'guide', time:'auto', fest:'none' };")
n = qa.count(old_wz)
assert n == 1, 'wizard 锚点 count=%d' % n
qa = qa.replace(old_wz, crlf("const wizard = { active:false, cats:[], dura:'3', budget:'mid', style:'guide', time:'auto', fest:'auto' };"), 1)
# 向导第4步默认选中 auto（FEST 按钮初始高亮）
old_sel = crlf("${d.k==='none'?'sel':''}\" onclick=\"pickWzFest")
n = qa.count(old_sel)
assert n == 1, '向导 FEST 默认选中锚点 count=%d' % n
qa = qa.replace(old_sel, crlf("${d.k==='auto'?'sel':''}\" onclick=\"pickWzFest"), 1)

assert qa.count('const qaTalkEngine = (function(){') == 1
assert qa.count('const SOLAR_TERMS') == 1
assert qa.count("fest:'auto'") >= 2
with io.open(QA, 'w', encoding='utf-8', newline='') as f:
    f.write(qa)
print('OK qa 引擎已同步 + FEST_OPTS 加自动')