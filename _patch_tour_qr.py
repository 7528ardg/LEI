# -*- coding: utf-8 -*-
"""新手教程追加「联系与反馈」步骤（微信二维码 + SMP 联系雷炜豪 + 动力文案）
两份教程：_shell_enhance.js（注入 spring/4in1）与 index.html（在线瘦壳/独立壳）。
二维码图片 base64 内嵌（常量 TOUR_QR_B64，data URI 渲染），单文件离线可用。
用法：python _patch_tour_qr.py 或 --check
"""
import base64, io, os, sys
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = r'c:\Users\Admin\.trae-cn\attachments\6aacd138521a525d0f899fb8\e66b106e-add2-4175-81cf-9adb57c74f6e_b9a8abab-1497-4373-b3a1-96e179479dba_127b6aeccb01f6eac342cef4b1313bb9.jpg'
ENHANCE = os.path.join(HERE, '_shell_enhance.js')
INDEX = os.path.join(HERE, 'index.html')

TOUR_B64 = base64.b64encode(io.open(IMG, 'rb').read()).decode('ascii')
CONST_LINE = "var TOUR_QR_B64 = '" + TOUR_B64 + "';"

NEW_STEP = ("{ mod:null, icon:'📮', title:'联系与反馈', desc:'如有问题、反馈或更好的建议：<br>· 请 <b>SMP 联系雷炜豪</b>；<br>· 也可 <b>微信扫码</b> 添加（二维码见下方）："
            "<div class=\"tour-qr\"><img src=\"data:image/jpeg;base64,' + TOUR_QR_B64 + '\" alt=\"微信二维码\" style=\"width:180px;height:180px;border-radius:12px;display:block;margin:12px auto;box-shadow:0 4px 14px rgba(0,0,0,.14)\"></div>"
            "<div style=\"text-align:center;color:#148453;font-weight:700\">您的反馈就是我们最大的动力 🌱</div>' }")


def read(p):
    return io.open(p, encoding='utf-8', newline='').read()


def patch(src, const_anchor_comment):
    """在教程注释块后插常量，并在 TOUR_STEPS 数组尾插新步骤。幂等。"""
    n = 0
    if 'var TOUR_QR_B64' not in src:
        # 插常量：锚定「新手教程」注释块后的 var TOUR_STEPS
        i = src.find('var TOUR_STEPS = [')
        if i < 0:
            raise SystemExit('未找到 var TOUR_STEPS')
        src = src[:i] + CONST_LINE + '\n' + src[i:]
        n += 1
    else:
        print('  常量已在位')
    if '联系与反馈' in src:
        print('  步骤已在位')
        return src, n
    # 在数组结束标记 ]; 前插入（取最后一个 ];\n 前的换行上下文，安全定位到教程数组结尾）
    j = src.find('];\nvar tourStep')
    if j < 0:
        # 兜底：找 '];\nfunction maybeStartTour'
        j = src.find('];\nfunction maybeStartTour')
    if j < 0:
        raise SystemExit('未找到 TOUR_STEPS 数组结尾')
    src = src[:j] + ',\n' + NEW_STEP + src[j:]
    n += 1
    return src, n


def main():
    check = '--check' in sys.argv
    for path, label in [(ENHANCE, '_shell_enhance.js'), (INDEX, 'index.html')]:
        s = read(path)
        out, n = patch(s, None)
        if check:
            if n or 'var TOUR_QR_B64' not in out or '联系与反馈' not in out:
                print('!! %s 尚未应用（%d 处）' % (label, n)); sys.exit(1)
            print('  %s -> UP-TO-DATE' % label)
            continue
        if n:
            io.open(path, 'w', encoding='utf-8', newline='').write(out)
            print('  %s 应用 %d 处（+%d 字节）' % (label, n, len(out) - len(s)))
        else:
            print('  %s -> UP-TO-DATE（无需改动）' % label)


if __name__ == '__main__':
    main()