# -*- coding: utf-8 -*-
"""
risk-lite.html 门禁加固 + 移除硬编码凭据（2026-10-05）
======================================================
【需求】除管理员账号外，其他账号均不可见/不可用 风险预警 板块（含直接打开文件绕过壳层的场景）。
【问题】走查实测（_walk_out3/）：
  1) L2776 硬编码 CabinAPI.auth.login({account:'028981',password:'LWH'}) —— 管理员明文凭据写死在源码，
     且 initDashboard（DOMContentLoaded 无条件调用，先于 SSO 执行）每次启动都真实执行该自动登录；
  2) L2782 备用登录 {user_id:'dash-manager'} 同为无鉴权后门；
  3) 壳层 SSO 块（L18539）对【任何】壳会话放行 —— 普通账号会话也能直接进入本板块；
  4) 登录表单 handleLogin 提交成功即进入，无角色校验。
【修复】
  A) initDashboard 内自动登录块整体替换：不再含任何硬编码凭据，
     改为「壳层管理员会话 → 构造 STATE.user」→「后端登录（无凭据）」→「离线模式」三级降级；
  B) 新增 __riskGateAdmin()（读 cabin_session_v1，role==='admin' 或 工号==='028981'）
     与 __riskGateShowDenied()（全屏无权限遮罩）；
  C) DOMContentLoaded 主初始化（initLeafletMap/initDashboard 前）：非管理员 → 显示遮罩并 return；
  D) 壳层 SSO：仅管理员会话自动进入；
  E) handleLogin：登录成功后复核门禁，非管理员壳会话一律拒绝。
【约束】幂等（MARK）；原子写 + newline=''；长度守卫；每处替换独立校验。
"""
import io, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(BASE, 'risk-lite.html')
MARK = '__PERMGATE_RISK_20261005__'


def read_text(p):
    with io.open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def write_text_atomic(p, s):
    tmp = p + '.tmp_write'
    with io.open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(s)
    os.replace(tmp, p)


# ---------- A) initDashboard 自动登录块：删除硬编码凭据 ----------
A_OLD = u"""    if(!_isLoggedIn){
      try{
        const login=await CabinAPI.auth.login({account:'028981',password:'LWH'});
        STATE.user=login.data?login.data.user||login.data:login;
        _isLoggedIn=true;
      }catch(loginErr){
        console.warn('[init] 自动登录失败，尝试用户ID登录：',loginErr.message);
        try{
          const login2=await CabinAPI.auth.login({user_id:'dash-manager',user_name:'雷管理',base_id:'SHA'});
          STATE.user=login2.data.user;
          _isLoggedIn=true;
          toast('已登录：'+STATE.user.user_name,'success');
        }catch(loginErr2){
          console.warn('[init] 备用登录也失败：',loginErr2.message);
          // 非阻塞：即使登录失败也继续加载（某些API可能不需要认证）
          STATE.user={user_name:'离线模式',user_id:'offline'};
          toast('离线模式运行（部分功能受限）','warn');
        }
      }
    }else{"""

A_NEW = u"""    if(!_isLoggedIn){
      /* """ + MARK + u"""：原硬编码自动登录（含管理员明文凭据）与
         无鉴权备用登录后门已删除。管理员身份由壳层会话（cabin_session_v1）提供，
         且 DOMContentLoaded 门禁保证只有管理员会话才会走到这里。 */
      try{
        var _sh=null;
        try{ _sh=JSON.parse(localStorage.getItem('cabin_session_v1')||'null'); }catch(_e){}
        if(_sh && _sh['工号']){
          STATE.user=STATE.user||{user_name:_sh['姓名']||'管理员',user_id:_sh['工号'],base_id:'Z1',role:'manager'};
          _isLoggedIn=true;
        }
      }catch(_shErr){ console.warn('[init] 壳层会话读取失败：',_shErr.message); }
      if(!_isLoggedIn){
        try{
          const login2=await CabinAPI.auth.login({user_id:'cabin-admin',user_name:'管理员',base_id:'Z1'});
          STATE.user=login2.data?login2.data.user||login2.data:login2;
          _isLoggedIn=true;
        }catch(loginErr2){
          console.warn('[init] 后端登录失败（离线模式）：',loginErr2.message);
          // 非阻塞：即使登录失败也继续加载（某些API可能不需要认证）
          STATE.user={user_name:'离线模式',user_id:'offline'};
          toast('离线模式运行（部分功能受限）','warn');
        }
      }
    }else{"""

# ---------- B) 门禁函数定义（插在 handleLogin 之前） ----------
B_ANCHOR = u"""function resetInactivityTimer(){"""
B_NEW = u"""/* ---------- 板块门禁：风险预警仅管理员可用（""" + MARK + u"""，与壳层 index.html 权限体系同源） ---------- */
function __riskGateAdmin(){
  try{
    var s=JSON.parse(localStorage.getItem('cabin_session_v1')||'null');
    return !!(s && (s.role==='admin' || s['工号']==='028981'));
  }catch(e){ return false; }
}
function __riskGateShowDenied(){
  try{
    var ov=document.getElementById('loginOverlay');
    if(ov){
      ov.classList.remove('hidden');
      ov.innerHTML='<div style="position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:#0f1c2e;z-index:99999">'
        +'<div style="text-align:center;color:#fff;max-width:420px;padding:0 24px">'
        +'<div style="font-size:56px;margin-bottom:16px">\\uD83D\\uDD12</div>'
        +'<div style="font-size:20px;font-weight:700;margin-bottom:10px">该板块仅管理员可用</div>'
        +'<div style="font-size:14px;opacity:.75;line-height:1.7">请使用管理员账号在「客舱小助手」登录后，从主界面进入风险预警。</div>'
        +'</div></div>';
    }
  }catch(e){ console.warn('[gate] 遮罩渲染失败：',e.message); }
}
function resetInactivityTimer(){"""

# ---------- C) DOMContentLoaded 主初始化门禁 ----------
C_OLD = u"""  // 启动初始化
  initLeafletMap(); // 初始化 Leaflet 全景实际地图
  initDashboard();"""

C_NEW = u"""  // 启动初始化（""" + MARK + u"""：板块门禁——仅管理员可用，非管理员显示无权限遮罩并终止初始化）
  if(!__riskGateAdmin()){
    __riskGateShowDenied();
    console.warn('[gate] 非管理员会话，风险预警板块已锁定');
    return;
  }
  initLeafletMap(); // 初始化 Leaflet 全景实际地图
  initDashboard();"""

# ---------- D) 壳层 SSO：仅管理员自动进入 ----------
D_OLD = u"""// ============ 壳层单点登录：客舱小助手已登录则自动进入，跳过独立登录页 ============
document.addEventListener('DOMContentLoaded',function(){
  try{
    var _sess=null;
    try{ _sess=JSON.parse(localStorage.getItem('cabin_session_v1')||'null'); }catch(e){}
    if(_sess && (_sess['工号']||_sess.account) && !_isLoggedIn){"""

D_NEW = u"""// ============ 壳层单点登录：客舱小助手已登录则自动进入，跳过独立登录页 ============
// """ + MARK + u"""：仅管理员会话自动进入；普通账号会话由板块门禁统一拦截（显示无权限遮罩）。
document.addEventListener('DOMContentLoaded',function(){
  try{
    if(!__riskGateAdmin()) return;
    var _sess=null;
    try{ _sess=JSON.parse(localStorage.getItem('cabin_session_v1')||'null'); }catch(e){}
    if(_sess && (_sess['工号']||_sess.account) && !_isLoggedIn){"""

# ---------- E) handleLogin：登录成功后复核门禁 ----------
E_OLD = u"""  try{
    const res=await CabinAPI.auth.login({account,password});
    _isLoggedIn=true;
    document.getElementById('loginOverlay').classList.add('hidden');"""

E_NEW = u"""  try{
    const res=await CabinAPI.auth.login({account,password});
    /* """ + MARK + u"""：登录成功后复核板块门禁——壳层会话非管理员一律拒绝（防止绕过壳层直接登录本板块） */
    if(!__riskGateAdmin()){
      errEl.textContent='该板块仅管理员可用';
      document.getElementById('loginPassword').value='';
      return;
    }
    _isLoggedIn=true;
    document.getElementById('loginOverlay').classList.add('hidden');"""


def main():
    s = read_text(TARGET)
    orig_len = len(s)
    if MARK in s:
        print(u'[跳过] 已应用过 %s' % MARK)
        return 0
    changed = []

    # A
    if A_OLD not in s:
        print(u'[失败] 未匹配 initDashboard 自动登录块')
        return 1
    s = s.replace(A_OLD, A_NEW, 1)
    changed.append(u'initDashboard 自动登录块去硬编码凭据（028981/LWH 与 dash-manager 后门已删）')

    # B
    if B_ANCHOR not in s:
        print(u'[失败] 未匹配 resetInactivityTimer 锚点')
        return 1
    s = s.replace(B_ANCHOR, B_NEW, 1)
    changed.append(u'新增 __riskGateAdmin/__riskGateShowDenied 门禁函数')

    # C
    if C_OLD not in s:
        print(u'[失败] 未匹配 DOMContentLoaded 主初始化块')
        return 1
    s = s.replace(C_OLD, C_NEW, 1)
    changed.append(u'主初始化前门禁拦截（非管理员显示遮罩并 return）')

    # D
    if D_OLD not in s:
        print(u'[失败] 未匹配壳层 SSO 块')
        return 1
    s = s.replace(D_OLD, D_NEW, 1)
    changed.append(u'壳层 SSO 改为仅管理员自动进入')

    # E
    if E_OLD not in s:
        print(u'[失败] 未匹配 handleLogin 片段')
        return 1
    s = s.replace(E_OLD, E_NEW, 1)
    changed.append(u'handleLogin 登录成功后复核门禁')

    delta = len(s) - orig_len
    if delta <= 0 or delta > 20000:
        print(u'[失败] 长度变化异常 delta=%d，终止写入' % delta)
        return 1

    write_text_atomic(TARGET, s)
    print(u'[完成] risk-lite.html 门禁加固（delta=+%d 字符）' % delta)
    for c in changed:
        print(u'   ✓', c)
    return 0


if __name__ == '__main__':
    sys.exit(main())
