# -*- coding: utf-8 -*-
"""你问我答 · 3D 可用性甄别（2026-09-19，修平板「无模型」体验层）
--------------------------------------------------------------------------------
背景：用户平板 APK 上点 🧊3D 一直提示「3D 模型还没生成好（已完成 n/24）」——
      实际 24/24 模型早已入库，真实根因是 **3D 组件脚本/资源没加载成功**
      （中文资产路径 形象IP/ 在部分机型 WebView 虚拟域拦截链路上不可靠，APK 侧
      已由 _apply_apk_fix 的 ascii_3d_assets 步骤切换为全 ASCII 的 ccmodels/）。
      但 r3dAvail 把「组件没加载」「WebGL 不支持」「模型缺失」三种失败混成一个文案，
      误导排障方向。

本补丁做三件事（全部幂等，命中即跳过）：
  1. 新增 webglOK()：canvas 探测 WebGL 可用性；
  2. pet3dSync()：CC3D.mount / setForm 全程 try/catch，任何抛错回落 2D 立绘，
     绝不因 3D 初始化失败影响问答主功能；
  3. 🧊3D 键点击的失败文案三分：组件未加载 / 不支持 WebGL / 模型真缺失。

用法：python _apply_qa_3dfix_20260919.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

def _atomic_write(path, text):
    tmp = path + u'.tmp_write'
    io.open(tmp, 'w', encoding='utf-8', newline='').write(text)
    os.replace(tmp, path)

ROOT = os.path.dirname(os.path.abspath(__file__))
QA = os.path.join(ROOT, u'qa.html')

# ---- 三组精确替换（old 在当前 qa.html 必须恰好 1 份；new 含即视为已打过） ----
R1_OLD = u"""  function pet3dSync(i){
    var el = $('petFig3d'), b3 = $('pb3d');
    if (!el || !stage) return;"""
R1_NEW = u"""  /* __QA_3DFIX_v1__ ：WebGL 能力探测（2026-09-19 平板「无模型」甄别） */
  function webglOK(){
    try{
      if(!window.WebGLRenderingContext) return false;
      var c = document.createElement('canvas');
      return !!(c.getContext('webgl') || c.getContext('experimental-webgl'));
    }catch(e){ return false; }
  }
  function pet3dSync(i){
    var el = $('petFig3d'), b3 = $('pb3d');
    if (!el || !stage) return;"""

R2_OLD = u"""    if (!el.__cc3d){
      el.__cc3dOnReady = function(){ stage.classList.add('is3d'); };
      el.__cc3dFallback = function(){ stage.classList.remove('is3d'); };
      CC3D.mount(el, { form: i });
    } else {
      CC3D.setForm(el, i);
      if (el.__cc3d.has) stage.classList.add('is3d');
    }"""
R2_NEW = u"""    /* __QA_3DFIX_v1__ ：3D 挂载全程兜底，失败回落 2D，不影响问答主功能 */
    try{
      if (!el.__cc3d){
        el.__cc3dOnReady = function(){ stage.classList.add('is3d'); };
        el.__cc3dFallback = function(){ stage.classList.remove('is3d'); };
        if (!CC3D.mount(el, { form: i })){ stage.classList.remove('is3d'); }
      } else {
        CC3D.setForm(el, i);
        if (el.__cc3d.has) stage.classList.add('is3d');
      }
    }catch(e){ try{ stage.classList.remove('is3d'); }catch(_e){} }"""

R3_OLD = u"""      if (!r3dAvail(ci)){
        var n = 0;
        try{ if (window.CC3D && CC3D.ready() && CC3D.can){
          for (var k = 0; k < ROSTER.length; k++){ if (CC3D.can(ROSTER[k].i)) n++; } } }catch(e){}
        say('「' + ROSTER[cur].n + '」的 3D 模型还没生成好（已完成 ' + n + '/24，生成完会自动亮起）', true);
        return;
      }"""
R3_NEW = u"""      if (!r3dAvail(ci)){
        /* __QA_3DFIX_v1__ ：失败三分文案（组件没加载 / WebGL 不支持 / 模型真缺失） */
        if (!window.CC3D || !CC3D.ready()){
          say('这台设备的 WebView 加载不了 3D 组件，先用 2D 形象（其他功能不受影响）', true);
        } else if (!webglOK()){
          say('这台设备不支持 WebGL 3D 渲染，先用 2D 形象', true);
        } else {
          var n = 0;
          try{ if (window.CC3D && CC3D.ready() && CC3D.can){
            for (var k = 0; k < ROSTER.length; k++){ if (CC3D.can(ROSTER[k].i)) n++; } } }catch(e){}
          say('「' + ROSTER[cur].n + '」的 3D 模型还没生成好（已完成 ' + n + '/24，生成完会自动亮起）', true);
        }
        return;
      }"""

REPLACES = [
    (u'webglOK 探测函数', R1_OLD, R1_NEW, u'function webglOK()'),
    (u'挂载 try/catch 兜底', R2_OLD, R2_NEW, u'3D 挂载全程兜底'),
    (u'3D 键三分文案', R3_OLD, R3_NEW, u'加载不了 3D 组件'),
]


def main():
    if not os.path.exists(QA):
        print(u'[ERR] 找不到 qa.html')
        return 1
    s = io.open(QA, 'r', encoding='utf-8', newline='').read()
    if s.count(u'__QA_3DFIX_v1__') >= 3:
        print(u'[skip] 3D 甄别补丁已在位（幂等）')
        return 0

    changed = 0
    for name, old, new, probe in REPLACES:
        if probe in s:
            print(u'  [skip] %s（已打过）' % name)
            continue
        c = s.count(old)
        if c != 1:
            print(u'[ERR] %s：old 串出现 %d 次（应为 1），不动盘' % (name, c))
            return 1
        s = s.replace(old, new, 1)
        changed += 1
        print(u'  [ok] %s' % name)

    checks = {
        u'三处标记齐全': s.count(u'__QA_3DFIX_v1__') == 3,
        u'webglOK 定义': u'function webglOK()' in s,
        u'mount 布尔守卫': u'if (!CC3D.mount(el, { form: i }))' in s,
        u'组件失败文案': u'加载不了 3D 组件' in s,
        u'WebGL 失败文案': u'不支持 WebGL 3D 渲染' in s,
        u'模型缺失文案保留': u'的 3D 模型还没生成好' in s,
        u'script 标签平衡': s.count(u'<script') == s.count(u'</script>'),
    }
    fails = [k for k, v in checks.items() if not v]
    for k, v in checks.items():
        print(u'  [%s] %s' % (u'OK' if v else u'NG', k))
    if fails:
        print(u'!! 自检失败，未写盘')
        return 1
    _atomic_write(QA, s)
    print(u'[ok] 3D 甄别补丁完成（本次改 %d 处）' % changed)
    return 0


if __name__ == '__main__':
    if '--check' in sys.argv:
        s = io.open(QA, 'r', encoding='utf-8', newline='').read()
        ok = s.count(u'__QA_3DFIX_v1__') == 3 and u'function webglOK()' in s
        print(u'[check] 3D 甄别补丁：%s' % (u'OK' if ok else u'FAIL'))
        raise SystemExit(0 if ok else 1)
    raise SystemExit(main())
