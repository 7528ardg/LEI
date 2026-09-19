# -*- coding: utf-8 -*-
"""问题反馈模块（issues.html）加入「扫码联系」卡片：SMP 联系雷炜豪 + 微信二维码 + 动力文案
用法：python _patch_issues_qr.py [--check]
"""
import base64, io, os, sys
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = r'c:\Users\Admin\.trae-cn\attachments\6aacd138521a525d0f899fb8\e66b106e-add2-4175-81cf-9adb57c74f6e_b9a8abab-1497-4373-b3a1-96e179479dba_127b6aeccb01f6eac342cef4b1313bb9.jpg'
ISSUES = os.path.join(HERE, 'issues.html')
B64 = base64.b64encode(io.open(IMG, 'rb').read()).decode('ascii')

ANCHOR = '<div class="legend">💡 提示：提交后记录将留存于「记录监控」中，随时可查看与追踪处理状态；系统运行异常也会自动记录在这里。</div>'
CARD = (ANCHOR + '\n'
        '<div class="card">'
        '<div class="card-title">📮 扫码联系 · 专属反馈</div>'
        '<div class="field">'
        '<label>问题也可通过以下渠道直接联系：</label>'
        '<div class="legend" style="margin-top:0">'
        '· 请 <b>SMP 联系雷炜豪</b>；<br>'
        '· 也可 <b>微信扫码</b> 添加（二维码见下方）。'
        '</div>'
        '<div style="text-align:center;margin:12px 0 4px">'
        '<img src="data:image/jpeg;base64,' + B64 + '" alt="微信二维码" style="width:180px;height:180px;border-radius:12px;box-shadow:0 4px 14px rgba(0,0,0,.14)">'
        '</div>'
        '<div style="text-align:center;font-weight:700;color:var(--primary);font-size:.92rem">您的反馈就是我们最大的动力 🌱</div>'
        '</div>'
        '</div>')


def main():
    check = '--check' in sys.argv
    s = io.open(ISSUES, encoding='utf-8', newline='').read()
    if '扫码联系' in s:
        print('  issues.html -> UP-TO-DATE')
        sys.exit(0 if check else 0)
    if ANCHOR not in s:
        raise SystemExit('!! 未找到 legend 锚点')
    s = s.replace(ANCHOR, CARD, 1)
    if not check:
        io.open(ISSUES, 'w', encoding='utf-8', newline='').write(s)
        print('  issues.html 已插入扫码联系卡片（+%d 字节）' % (len(s)))
    else:
        print('  未应用')


if __name__ == '__main__':
    main()