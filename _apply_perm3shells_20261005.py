# -*- coding: utf-8 -*-
"""
权限门禁移植到 spring-assistant.html + nc/index.html（2026-10-05）
==================================================================
【需求】除管理员账号外，其他账号均不可见 绩效管理(performance) 与 风险预警(risk) 板块。
【现状】index.html 已有完整门禁（_apply_permfix_20261004.py，守护 28 项全 PASS），
        但 spring-assistant.html 与 nc/index.html 完全没有权限块（grep 0 命中），
        两壳均有 performance 入口（spring 另有 risk 入口），普通账号登录后全部可见。
【移植】与 index.html 同款五件套：
  1) CSS：.is-user 隐藏 performance/risk 全部入口形态（mod-tab/m-sheet-item/m-tab/data-mod/onclick）
  2) JS 权限块：sessionRole / shellIsAdmin / ADMIN_ONLY_MODS / shellCanMod / applyPermUI（包装 switchModule）
  3) finishAuth：saveSession 补 role 字段（与 index.html 对齐）+ 调用 applyPermUI()
  4) shellLogout：登出补 applyPermUI()（复位为普通用户视图）
  5) init IIFE：applyPermUI() 无条件提前调用（游客=普通用户）
【约束】幂等（MARK 判定）；原子写 + newline=''；长度守卫；同文件多处替换逐一校验。
"""
import io, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
MARK = '__PERM3SHELLS_20261005__'

CSS_BLOCK = (
    u'<style id="permGateCSS">' + MARK +
    u'/* 管理员专属板块：普通账号/游客不可见（与 index.html 权限门禁同源） */\n'
    u'.is-user .mod-tab[data-mod="risk"],.is-user .m-sheet-item[data-mod="risk"],'
    u'.is-user [data-mod="risk"],.is-user [onclick*="switchModule(\'risk\')"],'
    u'.is-user [onclick*="mGoMod(\'risk\')"],.is-user [onclick*="mGo(\'risk\')"],'
    u'.is-user .mod-tab[data-mod="performance"],.is-user .m-tab[data-mod="performance"],'
    u'.is-user .m-sheet-item[data-mod="performance"],.is-user [data-mod="performance"],'
    u'.is-user [onclick*="switchModule(\'performance\')"],'
    u'.is-user [onclick*="mGoMod(\'performance\')"],.is-user [onclick*="mGo(\'performance\')"]'
    u'{display:none!important}</style>\n</head>'
)

JS_BLOCK = (
    u"""/* ---------- 板块权限：绩效管理/风险预警仅管理员可见可用（""" + MARK + u"""，与 index.html 同源） ---------- */
function sessionRole(){
  var s = readSession();
  if(!s) return '';
  return (s.role === 'admin' || s.工号 === ADMIN.工号) ? 'admin' : 'user';
}
window.shellIsAdmin = function(){ return sessionRole() === 'admin'; };
/* 管理员专属板块：普通账号既看不到入口（CSS .is-user 隐藏），也进不去（此处门禁拦截） */
var ADMIN_ONLY_MODS = ['risk', 'performance'];
window.shellCanMod = function(id){
  return !(ADMIN_ONLY_MODS.indexOf(String(id)) >= 0 && !window.shellIsAdmin());
};
function applyPermUI(){
  window.__permInit = true;
  var isAdmin = window.shellIsAdmin();
  try{ document.body.classList.toggle('is-user', !isAdmin); }catch(e){}
  if(!window.__permWrapped && typeof window.switchModule === 'function'){
    window.__permWrapped = true;
    var _origMod = window.switchModule;
    window.switchModule = function(id){
      if(window.shellCanMod && !window.shellCanMod(id)){
        var _mn = {risk:'风险预警', performance:'绩效管理'}[String(id)] || '该板块';
        try{ if(typeof toast === 'function') toast('⚠️ ' + _mn + '仅管理员可用'); }catch(e){}
        console.warn('[权限] 非管理员访问受限板块被拦截:', id);
        return;
      }
      return _origMod.apply(window, arguments);
    };
  }
}

function finishAuth(user){"""
)

FINISH_OLD = u"""function finishAuth(user){
  saveSession({ 工号: user.工号, 姓名: user.姓名, 手机号: user.手机号 || '' });
  if(authOverlay){ authOverlay.style.display = 'none'; }
  updateChip();"""

FINISH_NEW = u"""function finishAuth(user){
  saveSession({ 工号: user.工号, 姓名: user.姓名, 手机号: user.手机号 || '', role: (user.工号 === ADMIN.工号 ? 'admin' : 'user') });
  if(authOverlay){ authOverlay.style.display = 'none'; }
  updateChip();
  /* """ + MARK + u"""：登录成功立即应用权限 UI（管理员可见绩效/风险，普通账号隐藏） */
  applyPermUI();"""

LOGOUT_OLD = u"""window.shellLogout = function(){
  saveSession(null);
  var pm = el('profileModal');
  if(pm) pm.classList.remove('show');
  showAuth();"""

LOGOUT_NEW = u"""window.shellLogout = function(){
  saveSession(null);
  var pm = el('profileModal');
  if(pm) pm.classList.remove('show');
  /* """ + MARK + u"""：登出后必须复位权限 UI，否则残留管理员视图（入口不隐藏、门禁不拦截） */
  applyPermUI();
  showAuth();"""

INIT_OLD = u"""  lsSet('spring_onb_done', '1');
  if(readSession()){
    updateChip();
    maybeStartTour();
  } else {
    showAuth();
  }"""

INIT_NEW = u"""  lsSet('spring_onb_done', '1');
  /* """ + MARK + u"""：权限 UI 必须【无条件】先应用一次——未登录（游客）同样按普通用户处理，
     否则 body 拿不到 .is-user 类、switchModule 也不会被包装，管理员专属板块会暴露。 */
  applyPermUI();
  if(readSession()){
    updateChip();
    maybeStartTour();
  } else {
    showAuth();
  }"""


def read_text(p):
    with io.open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def write_text_atomic(p, s):
    tmp = p + '.tmp_write'
    with io.open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(s)
    os.replace(tmp, p)


def patch(fname):
    path = os.path.join(BASE, fname)
    s = read_text(path)
    orig_len = len(s)
    if MARK in s:
        print(u'[跳过] %s 已应用过 %s' % (fname, MARK))
        return True

    # 1) CSS 注入（</head> 前）
    if u'</head>' not in s:
        print(u'[失败] %s 找不到 </head>' % fname)
        return False
    s = s.replace(u'</head>', CSS_BLOCK, 1)

    # 2) JS 权限块 + finishAuth 前插入（JS_BLOCK 尾部自带 "function finishAuth(user){" 开头，
    #    用 FINISH_OLD 的首行做锚点：把 "function finishAuth(user){\n  saveSession(...role 旧串)" 整体替换
    if FINISH_OLD not in s:
        print(u'[失败] %s 未匹配 finishAuth 片段' % fname)
        return False
    s = s.replace(FINISH_OLD, JS_BLOCK + u'\n  saveSession_PLACEHOLDER__', 1)
    # 上面把 FINISH_OLD 的前半替换成了 JS_BLOCK + 占位，需要把 FINISH_OLD 的剩余部分接回去：
    # 更简单直接：改为两步——先插 JS 块（锚点 finishAuth 首行前），再改 finishAuth 内部。
    return True


def patch_v2(fname):
    """清晰版：每处替换独立、逐一校验。"""
    path = os.path.join(BASE, fname)
    s = read_text(path)
    orig_len = len(s)
    if MARK in s:
        print(u'[跳过] %s 已应用过 %s' % (fname, MARK))
        return True
    changed = []

    # 1) CSS（</head> 前）
    head_count = s.count(u'</head>')
    if head_count < 1:
        print(u'[失败] %s 无 </head>' % fname)
        return False
    css = CSS_BLOCK.replace(u'</head>', u'')  # 不含收口
    s = s.replace(u'</head>', css + u'</head>', 1)
    changed.append(u'CSS .is-user 隐藏规则')

    # 2) JS 权限块：插在 "function finishAuth(user){" 之前
    anchor = u'function finishAuth(user){'
    if anchor not in s:
        print(u'[失败] %s 无 finishAuth 锚点' % fname)
        return False
    js_only = JS_BLOCK[:JS_BLOCK.rfind(u'function finishAuth(user){')]
    s = s.replace(anchor, js_only + anchor, 1)
    changed.append(u'JS 权限块(sessionRole/ADMIN_ONLY_MODS/applyPermUI)')

    # 3) finishAuth：补 role + applyPermUI
    if FINISH_OLD not in s:
        print(u'[失败] %s 未匹配 finishAuth 片段' % fname)
        return False
    s = s.replace(FINISH_OLD, FINISH_NEW, 1)
    changed.append(u'finishAuth 补 role 字段 + applyPermUI')

    # 4) shellLogout：补 applyPermUI
    if LOGOUT_OLD not in s:
        print(u'[失败] %s 未匹配 shellLogout 片段' % fname)
        return False
    s = s.replace(LOGOUT_OLD, LOGOUT_NEW, 1)
    changed.append(u'shellLogout 补 applyPermUI')

    # 5) init IIFE：无条件 applyPermUI
    if INIT_OLD not in s:
        print(u'[失败] %s 未匹配 init IIFE 片段' % fname)
        return False
    s = s.replace(INIT_OLD, INIT_NEW, 1)
    changed.append(u'init 无条件 applyPermUI')

    delta = len(s) - orig_len
    if delta <= 0 or delta > 20000:
        print(u'[失败] %s 长度变化异常 delta=%d，终止写入' % (fname, delta))
        return False

    write_text_atomic(path, s)
    print(u'[完成] %s（delta=+%d 字符）' % (fname, delta))
    for c in changed:
        print(u'   ✓', c)
    return True


def main():
    ok = True
    for f in (u'spring-assistant.html', os.path.join(u'nc', u'index.html')):
        if not patch_v2(f):
            ok = False
    if not ok:
        print(u'[总结] 存在失败项，请人工核对')
        return 1
    print(u'[总结] 两壳权限门禁移植完成')
    return 0


if __name__ == '__main__':
    sys.exit(main())
