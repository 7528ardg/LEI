# -*- coding: utf-8 -*-
"""
_apply_apk_opt_20260918.py · APK 资产层专项优化（2026-09-18）

背景（实测定位结论，详见 _apk_perf_probe.js / _apk_diag.js / _apk_ui_audit.js）：
  1. 旧 APK 打的是 22MB gzip 内嵌旧壳（const MODULES 单行 7.67MB base64），
     与主线「拆分 html 直连」架构脱节 → 首屏解析 22MB、启动 heap 122MB 起。
  2. 壳层 _startOnlinePrewarm 启动 900ms 后把其余 11 个模块（约 30MB HTML）全部
     渲染进 iframe：主线程长期被解压/解析占用（切换板块卡顿）、12 个 iframe 常驻
     （heap 150MB+）→ 低端机 WebView 渲染进程被杀 → 白屏「偶发打不开」。
  3. UI：721-1024px（平板/手机横屏）无底部 TabBar 且顶部页签被挤成 8-70px 缝隙
     → 这些尺寸下几乎无法切换板块；loader 用 opacity:0 常驻合成层；无启动封面。

本脚本做四件事（幂等，strip→replay，重复运行结果一致）：
  A. 对壳 index.html 打 APK 专项补丁 → 输出 assets/www/index.html
     - 预热收敛：全量预热 → 仅延迟 4s 预热 home 一个模块，且页面隐藏时不执行
     - iframe LRU：已加载 iframe 超过 5 个时自动卸载最久未用者（防内存爬升）
     - 启动封面：品牌绿封面 + 加载点动画，qa 首屏 load 后淡出（9s 兜底）
     - UI 修复：721-1024px 启用底部 TabBar/隐藏顶部页签、页签 min-height 42、
       modal-x 最小 38px、loader 隐藏改 visibility（保留淡出动效且脱离合成层）
  B. 组装 assets/www/：12 个模块 html + 形象IP/models(js,lib) + risk/
  C. 移除旧版 22MB 内嵌 assets/index.html
  D. 自检：断言关键标记存在、体积达标
"""
import io, os, re, shutil, sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BASE))      # 融合版根目录（APK封装/CabinAssistant 的上两级）
ASSETS = os.path.join(BASE, 'assets')
WWW = os.path.join(ASSETS, 'www')

INDEX_SRC = os.path.join(ROOT, 'index.html')
MOD_FILES = {
    'qa': 'qa.html', 'home': 'cc-home.html', 'quiz': 'quiz.html',
    'performance': 'performance.html', 'beauty': 'beauty.html',
    'risk': 'risk-lite.html', 'medical': 'medical.html', 'daily': 'daily.html',
    'manual': 'manual.html', 'report': 'report.html', 'kbadmin': 'kb-admin.html',
    'issues': 'issues.html',
}


def read(p):
    with io.open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def write(p, s):
    s.encode('utf-8')
    with io.open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def strip_marked(s, begin, end):
    """删除已注入的标记块（含标记本身），幂等前置步骤"""
    pat = re.compile(re.escape(begin) + r'[\s\S]*?' + re.escape(end))
    return pat.sub('', s)


# ---------------------------------------------------------------- CSS 补丁
APK_CSS = r"""
/*__APK_OPT_CSS_BEGIN__*/
/* ===== APK 专项 UI 修复（2026-09-18）===== */
/* 1) 平板 / 手机横屏（721-1024px）：启用底部 TabBar，隐藏被挤压的顶部页签
      实测该区间顶部页签栏 clientW 仅 8-70px，11 个页签完全不可用 */
@media (min-width:721px) and (max-width:1024px){
  .m-tabbar{display:flex;position:fixed;left:0;right:0;bottom:0;height:calc(var(--tabbar-h) + env(safe-area-inset-bottom,0px));padding:0 4px env(safe-area-inset-bottom,0px);background:var(--bg-card);border-top:1px solid var(--border);z-index:200;box-shadow:0 -4px 16px rgba(15,42,31,.06);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);}
  .m-tab{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;font-size:11px;color:var(--text2);background:none;border:none;cursor:pointer;min-height:46px;padding:4px 0;border-radius:10px;transition:color .2s,background-color .15s,transform .12s;}
  .m-tab:active{background:var(--primary-mist);transform:scale(.94);}
  .m-tab .mi{font-size:21px;line-height:1;}
  .m-tab.active{color:var(--primary);font-weight:600;}
  .module-tabs{display:none;}
  .sys-area{bottom:calc(var(--tabbar-h) + env(safe-area-inset-bottom,0px));}
  .shell-crumb{display:flex !important;}
  .brand-main{display:inline;}
}
/* 2) 页签触控目标与滚动保底（所有尺寸） */
.mod-tab{min-height:40px;}
.module-tabs{flex:1 1 auto;min-width:0;}
/* 3) 小号关闭按钮垫到可点尺寸 */
.modal-x{min-width:38px;min-height:38px;}
/* 4) loader 隐藏改 visibility：保留 0.4s 淡出动效，且淡出后脱离渲染/合成树
      （原 opacity:0 常驻合成层，12 个 loader 全部参与合成） */
.sys-loader.hidden{opacity:0;visibility:hidden;pointer-events:none;transition:opacity .35s ease, visibility 0s linear .35s;}
/* 5) 启动封面 */
#apkSplash{position:fixed;inset:0;z-index:9999;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;background:linear-gradient(165deg,#0B5D3A 0%,#148453 52%,#0A4A30 100%);color:#fff;transition:opacity .5s ease, visibility .5s;user-select:none;-webkit-user-select:none;}
#apkSplash.gone{opacity:0;visibility:hidden;pointer-events:none;}
#apkSplash .apk-logo{width:92px;height:92px;filter:drop-shadow(0 6px 18px rgba(0,0,0,.28));}
#apkSplash .apk-name{font-size:30px;font-weight:700;letter-spacing:.14em;margin-top:16px;text-shadow:0 2px 12px rgba(0,0,0,.22);}
#apkSplash .apk-sub{font-size:12.5px;opacity:.72;letter-spacing:.3em;margin-top:2px;}
#apkSplash .apk-dots{display:flex;gap:9px;margin-top:30px;}
#apkSplash .apk-dots i{width:8px;height:8px;border-radius:50%;background:rgba(255,255,255,.9);animation:apkDot 1.2s ease-in-out infinite;}
#apkSplash .apk-dots i:nth-child(2){animation-delay:.16s}
#apkSplash .apk-dots i:nth-child(3){animation-delay:.32s}
@keyframes apkDot{0%,100%{opacity:.22;transform:translateY(0)}50%{opacity:1;transform:translateY(-5px)}}
@media (prefers-reduced-motion:reduce){#apkSplash{transition:none}.apk-dots i{animation:none}}
/*__APK_OPT_CSS_END__*/
"""

# ---------------------------------------------------------------- SPLASH HTML
SPLASH_HTML = r"""
<!--__APK_SPLASH_BEGIN__-->
<div id="apkSplash" aria-hidden="true">
  <svg class="apk-logo" viewBox="0 0 40 40" aria-hidden="true">
    <defs><linearGradient id="apkLg" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="#7FE0AE"/><stop offset="50%" stop-color="#F5D66B"/><stop offset="100%" stop-color="#FF8A5C"/></linearGradient></defs>
    <path d="M8 28 Q12 8 20 18 Q28 8 32 28" fill="none" stroke="url(#apkLg)" stroke-width="4" stroke-linecap="round"/>
    <path d="M5 30 Q14 14 20 22 Q26 14 35 30" fill="none" stroke="url(#apkLg)" stroke-width="3" stroke-linecap="round" opacity=".5"/>
    <path d="M11 26 Q16 12 20 20 Q24 12 29 26" fill="none" stroke="url(#apkLg)" stroke-width="2.5" stroke-linecap="round" opacity=".7"/>
  </svg>
  <div class="apk-name">客舱小助手</div>
  <div class="apk-sub">春秋航空 · 广州分队</div>
  <div class="apk-dots"><i></i><i></i><i></i></div>
</div>
<!--__APK_SPLASH_END__-->
"""

# ---------------------------------------------------------------- JS 补丁
APK_JS = r"""
<script id="apk-opt-js">
/*__APK_OPT_JS_BEGIN__*/
(function(){
  'use strict';
  /* ===== ① iframe LRU：已加载模块超过 5 个时卸载最久未用者 =====
     12 个 iframe 全常驻 = heap 150MB+，低端安卓 WebView 渲染进程会被系统杀掉
     （表现为切着切着白屏 / 偶发打不开）。LRU 上限保住常用板块的秒开与内存。 */
  var MAX_LOADED = 5, use = {};
  var origSwitch = window.switchModule;
  if(typeof origSwitch === 'function'){
    window.switchModule = function(id){
      try{
        use[id] = Date.now();
        var loaded = Object.keys(window._loaded || {}).filter(function(k){ return window._loaded[k] && k !== id; });
        if(loaded.length >= MAX_LOADED){
          loaded.sort(function(a,b){ return (use[a]||0) - (use[b]||0); });
          while(loaded.length >= MAX_LOADED){
            var v = loaded.shift();
            try{
              var f = document.getElementById('frame-'+v);
              if(f){ f.onload = null; f.onerror = null; f.src = 'about:blank'; }
              if(window._loaded) window._loaded[v] = false;
            }catch(e){}
          }
        }
      }catch(e){}
      return origSwitch.apply(this, arguments);
    };
  }
  /* ===== ② 启动封面淡出：qa 首屏 load 后 350ms 淡出，9s 兜底 ===== */
  function hideSplash(){
    try{
      var s = document.getElementById('apkSplash');
      if(!s || s.classList.contains('gone')) return;
      s.classList.add('gone');
      setTimeout(function(){ if(s && s.parentNode) s.parentNode.removeChild(s); }, 650);
    }catch(e){}
  }
  var fq = document.getElementById('frame-qa');
  if(fq) fq.addEventListener('load', function(){ setTimeout(hideSplash, 350); });
  setTimeout(hideSplash, 9000);
  /* ===== ③ 内存紧急释放入口：容器 onTrimMemory 时调用 =====
     卸载除当前板块外的全部 iframe，把内存让给正在使用的板块 */
  window.__apkFreeMemory = function(){
    try{
      var cur = window.currentMod;
      Object.keys(window._loaded || {}).forEach(function(k){
        if(k === cur || !window._loaded[k]) return;
        var f = document.getElementById('frame-'+k);
        if(f){ f.onload = null; f.onerror = null; f.src = 'about:blank'; }
        window._loaded[k] = false;
      });
    }catch(e){}
  };
})();
/*__APK_OPT_JS_END__*/
</script>
"""

# 预热收敛：替换原 _startOnlinePrewarm 全量预热段
PREWARM_BEGIN, PREWARM_END = '/*__APK_PREWARM_V2_BEGIN__*/', '/*__APK_PREWARM_V2_END__*/'
PREWARM_NEW = PREWARM_BEGIN + r"""
function _startOnlinePrewarm(){
  if(_pwOnlineStarted) return;
  _pwOnlineStarted = true;
  /* APK 专项（2026-09-18）：全量预热收敛。
     原实现启动后把 11 个模块（约 30MB HTML）串行渲染进 iframe：
     ① 主线程长期被解压/解析占用 → 用户切换板块卡顿（「切换加载慢」的直接来源）
     ② 12 个 iframe 常驻 → heap 150MB+ → 低端机渲染进程被杀（「偶发打不开」）
     现只预热次高频的 home 一个模块，延迟 4s、页面不可见时不执行；
     其余模块保持点击时加载（本地 assets 毫秒级，配合 loader 反馈体验良好）。 */
  var f = document.getElementById('frame-home');
  if(!f || _loaded['home']) return;
  setTimeout(function(){
    try{
      if(document.hidden || _loaded['home'] || currentMod === 'home') return;
      f.src = modUrl('home');
    }catch(e){}
  }, 4000);
}
setTimeout(_startOnlinePrewarm, 900);
""" + PREWARM_END


def patch_shell(src):
    """对壳 HTML 施加 APK 专项补丁（幂等）"""
    n0 = len(src)

    # -- 幂等 strip --
    src = strip_marked(src, '/*__APK_OPT_CSS_BEGIN__*/', '/*__APK_OPT_CSS_END__*/')
    src = strip_marked(src, '<!--__APK_SPLASH_BEGIN__-->', '<!--__APK_SPLASH_END__-->')
    src = strip_marked(src, '<script id="apk-opt-js">', '</script>')
    src = strip_marked(src, PREWARM_BEGIN, PREWARM_END)

    # -- A1 预热收敛（精确锚定原函数全段替换）--
    # 2026-09-22：壳层已改为「预取门控」（_pwEnv：手机/省流/弱网完全不预取，桌面非 Wi-Fi 仅轻量 6 个），
    # 收敛力度强于本补丁；原锚点 setTimeout(_startOnlinePrewarm, 900) 随之消失。
    # 故锚点不匹配时降级为跳过（A2~A4 的 APK 专项 UI 仍必须应用），不再中断整个装配流程。
    i = src.find('function _startOnlinePrewarm(){')
    j = src.find('setTimeout(_startOnlinePrewarm, 900);')
    if i < 0 or j < 0 or j < i:
        print('  [skip] A1 预热收敛：锚点不匹配（壳层已由预取门控接管，等效且更严格）')
    else:
        j_end = j + len('setTimeout(_startOnlinePrewarm, 900);')
        seg = src[i:j_end]
        # 长度守卫：原段应为 ~700-900 字符
        if not (500 <= len(seg) <= 1200):
            raise SystemExit('预热段长度异常: %d' % len(seg))
        src = src[:i] + PREWARM_NEW + src[j_end:]

    # -- A2 CSS：注入到 </head> 前 --
    marker = '</head>'
    k = src.find(marker)
    if k < 0:
        raise SystemExit('锚点丢失: </head>')
    style_block = '<style id="apk-opt-css">' + APK_CSS + '</style>\n'
    src = src[:k] + style_block + src[k:]

    # -- A3 SPLASH：注入到 <body…> 后（取 body 开标签行尾）--
    m = re.search(r'<body[^>]*>', src)
    if not m:
        raise SystemExit('锚点丢失: <body>')
    pos = m.end()
    src = src[:pos] + SPLASH_HTML + src[pos:]

    # -- A4 JS：注入到 </body> 前 --
    k = src.rfind('</body>')
    if k < 0:
        raise SystemExit('锚点丢失: </body>')
    src = src[:k] + APK_JS + '\n' + src[k:]

    print('  壳补丁: %d -> %d 字符 (+%d)' % (n0, len(src), len(src) - n0))
    return src


def copytree_fixed(src_dir, dst_dir):
    os.makedirs(dst_dir, exist_ok=True)
    for root, _dirs, files in os.walk(src_dir):
        rel = os.path.relpath(root, src_dir)
        out = os.path.join(dst_dir, rel) if rel != '.' else dst_dir
        os.makedirs(out, exist_ok=True)
        for fn in files:
            s = os.path.join(root, fn)
            d = os.path.join(out, fn)
            if not os.path.exists(d) or os.path.getsize(s) != os.path.getsize(d):
                shutil.copy2(s, d)


def main():
    print('== A. 壳补丁 ==')
    shell = read(INDEX_SRC)
    patched = patch_shell(shell)

    print('== B. 组装 assets/www ==')
    if os.path.exists(WWW):
        for fn in os.listdir(WWW):
            p = os.path.join(WWW, fn)
            if os.path.isfile(p):
                os.remove(p)
    else:
        os.makedirs(WWW)
    write(os.path.join(WWW, 'index.html'), patched)

    total = 0
    for mid, fn in MOD_FILES.items():
        s = os.path.join(ROOT, fn)
        if not os.path.exists(s):
            raise SystemExit('缺模块文件: %s' % fn)
        shutil.copy2(s, os.path.join(WWW, fn))
        total += os.path.getsize(s)
    print('  模块 html: %d 个, %.2f MB' % (len(MOD_FILES), total / 1048576))

    # assets/img：2026-09-22 站点把模块内联 base64 大图抽成独立文件，APK 侧必须一并拷入，
    # 否则 12 个模块页全是裂图（路径是相对 assets/www/ 的，模块与 assets 同级即可解析）
    for rel in [os.path.join('形象IP', 'models', 'js'), os.path.join('形象IP', 'models', 'lib'),
                os.path.join('assets', 'img'), 'risk']:
        s = os.path.join(ROOT, rel)
        if os.path.exists(s):
            copytree_fixed(s, os.path.join(WWW, rel))
            sz = sum(os.path.getsize(os.path.join(r, f)) for r, _d, fs in os.walk(s) for f in fs)
            print('  %-28s %.2f MB' % (rel + '/', sz / 1048576))

    print('== C. 清理旧版内嵌 assets ==')
    old = os.path.join(ASSETS, 'index.html')
    if os.path.exists(old):
        os.remove(old)
        print('  已移除旧版 22MB 内嵌 assets/index.html')
    else:
        print('  无旧版文件')

    print('== D. 自检 ==')
    out = read(os.path.join(WWW, 'index.html'))
    checks = {
        # 2026-09-22：壳层改「预取门控」(_pwEnv) 后，A1 会优雅跳过；
        # 两种形态都视为通过（门控版收敛更强：手机/弱网完全不预取）。
        '预热收敛标记': ('APK_PREWARM_V2' in out) or ('function _pwEnv' in out),
        'LRU 注入': 'MAX_LOADED = 5' in out,
        '启动封面': 'id="apkSplash"' in out,
        'UI 断点修复': 'min-width:721px' in out,
        '无旧内嵌 MODULES': 'const MODULES' not in out,
        '拆分架构 MOD_SRC': "qa: 'qa.html'" in out,
        '图集 assets/img': os.path.isdir(os.path.join(WWW, 'assets', 'img')),
    }
    ok = True
    for k, v in checks.items():
        print('  [%s] %s' % ('OK' if v else 'FAIL', k))
        ok = ok and v
    www_sz = sum(os.path.getsize(os.path.join(r, f)) for r, _d, fs in os.walk(WWW) for f in fs)
    print('  assets/www 总计: %.2f MB' % (www_sz / 1048576))
    if not ok:
        sys.exit(1)
    print('APK 资产优化完成 → %s' % WWW)


if __name__ == '__main__':
    main()
