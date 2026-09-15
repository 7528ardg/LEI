# -*- coding: utf-8 -*-
"""
UX Polish 注入器 v1（幂等）
把统一的「设计令牌 + 交互规范 + 分模块修复」CSS 以标记块注入各模块 HTML 的 </head> 前。
- 规范源：index.html 壳层设计语言（--primary #148453 / --gold #F5B800 / 彩绘渐变 / 暗色变量）
- 幂等：先剥离旧标记块再注入，可重复执行
- beauty 额外做品牌色收拢（Tailwind 翡翠绿 -> 春秋绿系）的字面量替换
用法：python _apply_ux_polish.py          # 执行
      python _apply_ux_polish.py --check  # 仅校验标记块存在（供 _build_all 回归链调用）
"""
import io, os, re, sys, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

BEGIN = '/*__UX_POLISH:v1__*/'
END = '/*__UX_POLISH_END__*/'
BAK = os.path.join(HERE, '_bak_uxpolish_20260915')

# ---------- 公共层：浏览器表面主题化 + 交互反馈 + 动效可及性 ----------
COMMON = """
/* ---- UX Polish v1 · 统一交互规范（规范源：index.html 壳层）---- */
:root{
  --ux-primary:#148453;--ux-primary-dark:#0C5F3A;--ux-primary-light:#1FA56A;
  --ux-gold:#F5B800;--ux-danger:#C62828;--ux-warn:#E64A19;
  --ux-ink:#0F2A1F;--ux-ink2:#5A6F65;--ux-border:#E5EDE9;
  --ux-radius-sm:8px;--ux-radius:12px;--ux-radius-lg:16px;
}
::selection{background:rgba(20,132,83,.24);}
*{scrollbar-width:thin;scrollbar-color:rgba(20,132,83,.35) transparent;}
::-webkit-scrollbar{width:8px;height:8px;}
::-webkit-scrollbar-thumb{background:rgba(20,132,83,.30);border-radius:99px;border:2px solid transparent;background-clip:content-box;}
::-webkit-scrollbar-track{background:transparent;}
button,a,[role="button"],input,select,textarea,label{-webkit-tap-highlight-color:transparent;}
button:not(:disabled){transition:transform .15s ease,box-shadow .2s ease,filter .2s ease,background-color .2s ease,border-color .2s ease,opacity .2s ease;}
button:active:not(:disabled){transform:translateY(1px);}
:focus{outline:none;}
:focus-visible{outline:2.5px solid #148453;outline-offset:2px;border-radius:6px;}
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;scroll-behavior:auto!important;}
}
"""

QA = COMMON + """
/* qa：手机档顶栏按钮防裁切 + 小字下限 */
@media (max-width:760px){
  .t-ai{gap:5px;}
  .t-ai .icon-btn{min-height:34px;font-size:.7rem;padding:0 7px;border-radius:9px;}
  .t-ai .ai-status{font-size:.66rem;}
  .icon-btn{min-height:36px;}
}
small{font-size:11.5px;}
#aiStatus{font-size:11px;}
.lbl{font-size:11px;}
"""

BEAUTY = COMMON + """
/* beauty：令牌对齐壳层（原翡翠绿系已字面量收拢为春秋绿系） */
:root{
  --primary:#148453;--primary-dark:#0C5F3A;--primary-light:#1FA56A;
  --primary-soft:#E8F3EE;--primary-mist:#F4F9F6;
  --gold:#F5B800;--danger:#C62828;
  --bg:#F5F8F6;--bg-card:#fff;--text:#0F2A1F;--text2:#5A6F65;--border:#E5EDE9;
}
@media (max-width:760px){
  button.px-3\\.py-1\\.5{min-height:36px;}
  select.px-3\\.py-2{min-height:42px;font-size:15px;}
  #search-input{min-height:44px;font-size:15px;}
  button.flex.items-center{min-height:38px;}
}
"""

QUIZ = COMMON + """
/* quiz：手机档顶栏防溢出（+hamburger/logo/面包屑/胶囊 弹性收缩）+ 小字下限 */
@media (max-width:700px){
  .topbar{gap:8px;padding:0 10px;}
  .topbar .brand-sub{display:none;}
  .topbar .net-status{display:none;}
  .topbar .breadcrumb{min-width:0;flex:1 1 auto;overflow:hidden;}
  .topbar .breadcrumb .current{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .topbar .user-chip{flex-shrink:1;min-width:0;max-width:132px;padding:5px 10px 5px 6px;}
  .topbar .user-chip > *:not(.avatar){white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
}
.qt-meta{font-size:12px;}
.qt-tag{font-size:12px;}
"""

MANUAL = COMMON + """
/* manual：小字下限 + 手机档触控目标 */
small{font-size:12px;}
.f-label,#f-cat-cnt{font-size:11.5px;}
@media (max-width:760px){
  .m-tab{min-height:40px;}
  .chip{min-height:34px;}
  input#kw{min-height:42px;font-size:15px;}
}
"""

REPORT = COMMON + """
/* report：手机档触控目标 */
@media (max-width:760px){
  .m-tab{min-height:40px;}
  input#kw{min-height:42px;font-size:15px;}
  select.ri,input.ri{min-height:42px;font-size:15px;}
}
"""

MEDICAL = COMMON + """
/* medical：手机档基础触控目标 */
@media (max-width:760px){
  button{min-height:36px;}
  input,select{min-height:42px;font-size:15px;}
}
"""

PERF = COMMON + """
/* performance：Bootstrap 令牌收拢为春秋绿系 + 图表小字下限 + 表单触控 */
:root{
  --bs-primary:#148453;--bs-primary-rgb:20,132,83;
  --bs-link-color:#0C5F3A;--bs-link-hover-color:#0A4E30;--bs-border-color:#E5EDE9;
}
.btn-primary{--bs-btn-bg:#148453;--bs-btn-border-color:#148453;--bs-btn-hover-bg:#0C5F3A;--bs-btn-hover-border-color:#0C5F3A;--bs-btn-active-bg:#0A4E30;--bs-btn-active-border-color:#0A4E30;--bs-btn-disabled-bg:#148453;--bs-btn-disabled-border-color:#148453;}
.btn-outline-primary{--bs-btn-color:#148453;--bs-btn-border-color:#148453;--bs-btn-hover-bg:#148453;--bs-btn-hover-border-color:#148453;--bs-btn-active-bg:#148453;--bs-btn-active-border-color:#148453;}
.brand-subtitle{font-size:11px;}
svg text{font-size:10.5px;}
@media (max-width:760px){
  .form-select,.form-control{min-height:42px;font-size:15px;}
  #loginUsername,#loginPassword{min-height:46px;}
  .navbar-toggler{min-width:46px;min-height:46px;}
}
"""

RISK = COMMON + """
/* risk-lite：stat-pill 内联 min-width 撑破文档流（手机档改为纵向堆叠）+ 顶栏可见性 */
@media (max-width:900px){
  .stat-pill[style]{min-width:0!important;flex:1 1 100%!important;}
}
@media (max-width:760px){
  #appVersionBadge{display:none!important;}
  .topbar{gap:8px!important;padding:6px 12px!important;}
  .topbar .logo span{max-width:44vw;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  #btnGlobalRefresh,.btn-theme-toggle,.btn-briefing{padding:6px 9px!important;font-size:12px!important;}
}
@media (max-width:600px){
  .topbar{flex-wrap:wrap;}
  .topbar .breadcrumb{display:none!important;}
}
"""

# beauty 品牌色收拢映射（Tailwind 翡翠绿 -> 春秋绿系，字面量替换）
BEAUTY_SWAPS = [
    ('#10b981', '#1fa56a'),
    ('#059669', '#148453'),
    ('#047857', '#0c5f3a'),
    ('#ecfdf5', '#f4f9f6'),
    ('#d1fae5', '#e8f3ee'),
    ('#17301f', '#0f2a1f'),
]

TARGETS = {
    'qa.html': QA,
    'beauty.html': BEAUTY,
    'quiz.html': QUIZ,
    'manual.html': MANUAL,
    'report.html': REPORT,
    'issues.html': COMMON,
    'medical.html': MEDICAL,
    'performance.html': PERF,
    'risk-lite.html': RISK,
    'spring-assistant.html': COMMON,
    'daily.template.html': COMMON,
    'kb-admin.template.html': COMMON,
    'daily.html': COMMON,
    'kb-admin.html': COMMON,
    # cc-home.html 刻意跳过：桌面三栏为 2026-09-14 手调定稿，不在本轮范围
}

RX_BLOCK = re.compile(re.escape('<style id="uxPolish">' + BEGIN) + r'.*?' + re.escape(END + '</style>') + r'\n?', re.S)


def read(p):
    return io.open(p, encoding='utf-8').read()


def write(p, s):
    blob = s.encode('utf-8')  # 先校验可编码，防 0 字节事故
    blob.decode('utf-8')
    with io.open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def block(css):
    return '<style id="uxPolish">' + BEGIN + css + END + '</style>\n'


def find_real_head_end(src):
    """结构化扫描：跳过完整的 <script>/<style> 区块后，第一处 </head> 即真实文档头。
    内嵌库（如 SheetJS）的 JS 字符串里含 '</head><body>' 全文档模板，位置启发式必误判。"""
    low = src.lower()
    i, n = 0, len(src)
    rx = re.compile(r'<(/?)(script|style)\b|</head>', re.I)
    while i < n:
        m = rx.search(src, i)
        if not m:
            return -1
        if m.group(0).lower() == '</head>':
            return m.start()
        name = m.group(2).lower()
        close = low.find('</' + name + '>', m.end())
        if close == -1:
            return -1
        i = close + len('</' + name + '>')
    return -1


def main():
    if '--check' in sys.argv:
        missing = [f for f in TARGETS if BEGIN not in read(f)]
        if missing:
            print('[ux-polish][FAIL] 缺少标记块: %s' % ', '.join(missing)); raise SystemExit(1)
        print('[ux-polish] check PASS: %d 个文件均含标记块' % len(TARGETS)); return

    if not os.path.isdir(BAK):
        os.makedirs(BAK)
    total_swaps = 0
    for name, css in TARGETS.items():
        src = read(name)
        n0 = len(src)
        # 1) 剥离旧块（幂等）
        src, nrm = RX_BLOCK.subn('', src)
        # 2) beauty 品牌色收拢
        swaps = []
        if name == 'beauty.html':
            for old, new in BEAUTY_SWAPS:
                cnt = len(re.findall(re.escape(old), src, re.I))
                if cnt:
                    src = re.sub(re.escape(old), new, src, flags=re.I)
                    swaps.append('%s->%s×%d' % (old, new, cnt))
        # 3) 注入：结构化扫描定位真实文档头（先剥离旧块，再扫描干净文本）。
        #    performance.html 真实 </head> 缺失（HTML5 容许省略），退化为文末 </body> 前注入。
        src_base = src  # 剥离旧块后的干净文本
        pos = find_real_head_end(src_base)
        if pos < 0:
            last = None
            for last in re.finditer(re.escape('</body>'), src_base, re.I):
                pass
            pos = last.start() if last else len(src_base)
        src = src_base[:pos] + block(css) + src_base[pos:]
        # 4) 长度守卫：注入后必须恰好比剥离后多出一个块（幂等复跑、新旧块长短不一均可通过）
        n1 = len(src)
        assert n1 == len(src_base) + len(block(css)), '%s: 注入后长度异常' % name
        # 5) 备份 + 写盘
        bpath = os.path.join(BAK, name)
        if not os.path.exists(bpath):
            shutil.copy2(name, bpath)
        write(name, src)
        total_swaps += len(swaps)
        print('[ok] %-24s %8.1fKB -> %8.1fKB  旧块×%d  %s'
              % (name, n0 / 1024.0, n1 / 1024.0, nrm, ('色收拢: ' + ' '.join(swaps)) if swaps else ''))
    print('[done] 注入 %d 个文件，品牌色替换 %d 组' % (len(TARGETS), total_swaps))


if __name__ == '__main__':
    main()
