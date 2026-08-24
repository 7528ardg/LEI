# -*- coding: utf-8 -*-
"""禁用绩效 initApp 中的 Excel 人员自动同步（消除缺失文件导致的 fetch ERR_ABORTED）"""
import io
import re

PATH = u'_work\\广州综合绩效评定测试系统1.0(3).html'
with io.open(PATH, 'r', encoding='utf-8', newline='') as f:
    s = f.read()
was = ('\r' in s)
s = re.sub(r'\r+\n', '\n', s)
s = s.replace('\r', '\n')

old = "// Excel人员同步\n                try { await syncPersonnelFromExcel(); } catch(e) { console.warn('[initApp] 人员同步失败:', e); }"
new = "// Excel人员同步（默认关闭：避免启动时对不存在的【广州人员清单.xlsx】发起请求而产生网络错误）\n                // 如需启用自动同步，在页面运行前执行 window.AUTO_SYNC_PERSONNEL = true\n                if (typeof window.AUTO_SYNC_PERSONNEL !== 'undefined' && window.AUTO_SYNC_PERSONNEL) {\n                    try { await syncPersonnelFromExcel(); } catch(e) { console.warn('[initApp] 人员同步失败:', e); }\n                }"

if old in s:
    s = s.replace(old, new, 1)
    print('已禁用自动 Excel 同步')
else:
    # 宽松匹配（可能多行/不同换行）
    pat = re.compile(r'// Excel人员同步\s*\n\s*try \{ await syncPersonnelFromExcel\(\); \} catch\(e\) \{ console\.warn\([^\n]*\); \}', re.S)
    s2, n = pat.subn("// Excel人员同步（默认关闭：避免对不存在的【广州人员清单.xlsx】发起请求产生网络错误）\n                if (typeof window.AUTO_SYNC_PERSONNEL !== 'undefined' && window.AUTO_SYNC_PERSONNEL) {\n                    try { await syncPersonnelFromExcel(); } catch(e) { console.warn('[initApp] 人员同步失败:', e); }\n                }", s)
    if n:
        s = s2
        print('已禁用自动 Excel 同步（regex）')
    else:
        print('WARN 未匹配')

if was:
    s = s.replace('\n', '\r\n')
with io.open(PATH, 'w', encoding='utf-8', newline='') as f:
    f.write(s)