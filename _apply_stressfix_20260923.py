# -*- coding: utf-8 -*-
"""压力测试缺陷修复（2026-09-23）
==============================================================================
一次修复五组「已用真实浏览器实测确认」的缺陷。全部幂等（重复运行结果一致），
支持 --check 只校验不写入。

FIX-A  index.html                 switchModule 加载成功判据
  实测：模块 HTML 首次加载失败时，Chromium 仍会触发 iframe 的 load 事件（加载的是错误页），
        旧实现仅凭 onload 就置 _loaded[id]=true → 15s 超时与「自动切换镜像线路」被永久绕过，
        loader 文案停在「正在进入 …」，45s 无任何提示；恢复网络后切出再切回也不重试
        （实测 qa.html 仅被请求 1 次），用户只能重启应用。
  改法：成功判据改为「iframe 内容就绪」；失败路径绝不置 _loaded，并保留镜像切换与点击重试。

FIX-B  qa.html                    aiRetryable 重试白名单
  实测：注入 8s 超时后请求序列仅 [glm-4-flash] 一次即失败 —— 超时/网络类错误不在白名单，
        三级降级链完全没有机会生效。
  改法：chatLLMOnce 保留 HTTP 状态码；白名单补齐超时/AbortError/Failed to fetch/ERR_*/5xx。

FIX-C  qa.html                    熔断器并发保护 + 链尾冷却检查
  实测：10 路并发下，已限流的模型仍被尝试 10 次、请求总数 20 次（放大 2×）——
        熔断标记要等第一个 429 回来才写入，竞态窗口内所有请求都已发出，且无在途去重。
        另外熔断累积 60s、链尾不参与冷却检查 → 降级链退化为单模型。
  改法：单模型并发上限（AI_MAX_INFLIGHT=2）+ 空位等待；链尾同样参与冷却检查；
        全部模型处于冷却时快速失败并给出明确文案。

FIX-D  risk/api/api-client.js     risk 会话自动补建
  实测：quiz / kbadmin 模块稳定报 [weather] 刷新失败「未登录或会话已过期」——
        主登录流程只写 cabin_session_v1，risk 专属会话键（cabin_risk_session_v1）从不写入，
        而 mock 服务的 requireAuth 直接读该键。
  改法：请求前若 risk 会话缺失而主会话存在，用 mock 的 user_id 备用登录路径自动补建会话。
        失败即静默跳过（不阻断原请求），行为与之前一致。

FIX-E  PWA封装/_build_pwa.py      Service Worker 缓存策略
  实测：CACHE_NAME 固定 'cabin-pwa-v1'、activate 不清理旧缓存、cache-first 无重新验证
        → 版本更新后用户可能长期被锁在旧内容；CORE_URLS 不预缓存任何模块页，
        离线点开未访问过的模块只会得到 503 纯文本。
  改法：缓存名带版本号 + activate 清除旧版本缓存 + stale-while-revalidate +
        预缓存首屏高频模块页。

用法：
  python _apply_stressfix_20260923.py           # 应用（幂等）
  python _apply_stressfix_20260923.py --check   # 只校验，缺失即退出码 1
==============================================================================
"""
from __future__ import annotations

import io
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
CHECK = '--check' in sys.argv

MARK = '__STRESSFIX_20260923__'


def read(p):
    with io.open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def write(p, s):
    tmp = p + '.tmp_write'
    with io.open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(s)
    os.replace(tmp, p)


# ============================================================ FIX-A index.html
A_OLD_START = "  if(!_loaded[id]){\n    const loader = document.getElementById('loader-'+id);"
A_OLD_END = "    doLoad();\n  } else {\n    restoreModuleScroll(id);\n  }\n}"

A_NEW = """  if(!_loaded[id]){
    const loader = document.getElementById('loader-'+id);
    const frame = document.getElementById('frame-'+id);
    /* __STRESSFIX_20260923__ 导航失败时 Chromium 同样会触发 iframe 的 load 事件（加载错误页），
       旧实现仅凭 onload 就置 _loaded[id]=true → 15s 超时与镜像切换被永久绕过，
       该模块也再不会重试（实测 45s 无提示、qa.html 仅被请求 1 次），只能重启应用。
       现改为「内容就绪」判据：失败一律不置位，保留镜像切换与点击重试。 */
    if(loader && loader.__origText == null){
      const _t0 = loader.querySelector('.sl-text');
      loader.__origText = _t0 ? _t0.textContent : '';
    }
    const frameReadyFlag = function(){
      try{
        const d = frame.contentDocument;
        if(!d || !d.body) return false;                       // 空文档 = 导航失败
        return d.body.innerText.trim().length > 20
          || !!d.querySelector('main,header,nav,.appbar,.main-scroll-container');
      }catch(e){ return true; }                               // 跨域读不到就不阻断，放行更安全
    };
    if(loader) loader.classList.remove('hidden');
    // 加载保护：超时自动切换镜像线路，避免弱网下"一直等待"；双线路都失败则给出可点击重试
    let triedMirror = false;
    const doLoad = function(){
      if(frame._lt) clearTimeout(frame._lt);
      if(loader && loader.__origText != null){
        const t = loader.querySelector('.sl-text');
        if(t) t.textContent = loader.__origText;
      }
      frame.onload = function(){
        if(frame._lt) clearTimeout(frame._lt);
        if(!frameReadyFlag()){ onLoadFail(); return; }         // 误触发的 load（导航失败）走失败分支
        _loaded[id] = true;
        if(loader){ loader.classList.add('hidden'); loader.onclick = null; loader.style.cursor = ''; }
        injectEmbedCss(id, frame);
        restoreModuleScroll(id);
      };
      frame.onerror = function(){ onLoadFail(); };
      frame.src = modUrl(id);
      frame._lt = setTimeout(onLoadFail, 15000); // 15s 无响应视为卡住
    };
    const onLoadFail = function(){
      if(frame._lt) clearTimeout(frame._lt);
      _loaded[id] = false;                 // 关键：失败绝不置为已加载，切走再切回仍会重试
      if(triedMirror){
        if(loader){
          const t = loader.querySelector('.sl-text');
          if(t) t.textContent = '加载失败，点击此处重试';
          loader.classList.remove('hidden');
          loader.style.cursor = 'pointer';
          loader.onclick = function(){ triedMirror = false; doLoad(); };
        }
        return;
      }
      triedMirror = true;
      // 当前已是镜像则回主源，否则切镜像：双线路间自动切换，避免"一直等待"且可自愈
      const cur = getModBase();
      setModBase(cur === APP_MIRROR_BASE ? '' : APP_MIRROR_BASE);
      toast('检测到加载缓慢，已切换加载线路');
      doLoad();
    };
    doLoad();
  } else {
    restoreModuleScroll(id);
  }
}"""


def fix_index(s):
    if MARK in s:
        return s, 'skip'
    i = s.find(A_OLD_START)
    if i < 0:
        raise SystemExit('FIX-A 锚点未命中（index.html）：%r' % A_OLD_START[:48])
    j = s.find(A_OLD_END, i)
    if j < 0:
        raise SystemExit('FIX-A 结束锚点未命中（index.html）')
    j += len(A_OLD_END)
    old = s[i:j]
    if len(old) < 1200 or len(old) > 3000:
        raise SystemExit('FIX-A 命中长度异常：%d（期望 1200~3000），拒绝写入' % len(old))
    return s[:i] + A_NEW + s[j:], 'apply'


# ======================================================== FIX-B qa.html 白名单
B_OLD = """  function aiRetryable(e){
    var s = String((e && e.message) || e || '');
    /* BAD_RESPONSE（2026-09-22）：网关返回 HTML 错误页 / 非 JSON 正文时也应换模型重试 */
    return /1305|429|访问量过大|速率限制|限流|频率|too many|rate.?limit|系统繁忙|繁忙|EMPTY_CONTENT|BAD_RESPONSE/i.test(s);
  }"""

B_NEW = """  function aiRetryable(e){
    var s = String((e && e.message) || e || '');
    /* __STRESSFIX_20260923__ 时延/连接类错误此前不在白名单 → 一次超时即整链失败、
       两个备用模型完全没机会顶上（实测：注入 8s 超时后请求序列只有 1 个模型）。 */
    var _st = (e && e.status) || 0;
    if (_st >= 500 || _st === 408 || _st === 429) return true;
    /* BAD_RESPONSE（2026-09-22）：网关返回 HTML 错误页 / 非 JSON 正文时也应换模型重试 */
    return /1305|429|访问量过大|速率限制|限流|频率|too many|rate.?limit|系统繁忙|繁忙|EMPTY_CONTENT|BAD_RESPONSE|超时|timeout|timed ?out|AbortError|aborted|abort|Failed to fetch|NetworkError|network error|ERR_NETWORK|ERR_INTERNET|ERR_CONNECTION|ERR_TIMED_OUT|网络异常|网络错误|网络不稳|断网|Gateway Timeout|Bad Gateway|Service Unavailable|502|503|504/i.test(s);
  }"""

B2_OLD = """      if(!res.ok){
        let msg = 'HTTP ' + res.status;
        try{ const d = await res.json(); msg = (d.error && (d.error.message || d.error.code)) || msg; }catch(e){}
        throw new Error(msg);
      }"""

B2_NEW = """      if(!res.ok){
        let msg = 'HTTP ' + res.status;
        try{ const d = await res.json(); msg = (d.error && (d.error.message || d.error.code)) || msg; }catch(e){}
        /* __STRESSFIX_20260923__ 保留 HTTP 状态码，供 aiRetryable 判定 5xx 可重试 */
        const _httpErr = new Error(msg); _httpErr.status = res.status; throw _httpErr;
      }"""


# ================================================= FIX-C qa.html 熔断并发保护
C_OLD_START = "  var AI_RETRY_BACKOFF = [800, 1500];"
C_OLD_END = """    throw lastErr;
  }"""

C_NEW = """  var AI_RETRY_BACKOFF = [800, 1500];
  var AI_FALLBACK_MODELS = ['glm-4-flash-250414', 'glm-4-flash'];
  var AI_RATE_UNTIL = {};
  var AI_RATE_COOLDOWN = 60000;
  /* __STRESSFIX_20260923__ 并发保护：同一模型同时最多 AI_MAX_INFLIGHT 个请求在飞。
     旧实现无在途去重，10 路并发会在熔断标记写入前同时轰击链首
     （实测：已限流的模型被尝试 10 次、请求总数 20 次，熔断形同虚设）。 */
  var AI_INFLIGHT = {};
  var AI_SLOT_WAIT = {};
  var AI_MAX_INFLIGHT = 2;
  function aiSlotTry(m){
    var n = AI_INFLIGHT[m] || 0;
    if (n >= AI_MAX_INFLIGHT) return false;
    AI_INFLIGHT[m] = n + 1; return true;
  }
  function aiSlotRelease(m){
    var n = (AI_INFLIGHT[m] || 1) - 1;
    AI_INFLIGHT[m] = n < 0 ? 0 : n;
    var ws = AI_SLOT_WAIT[m] || [];
    AI_SLOT_WAIT[m] = [];
    for (var i = 0; i < ws.length; i++){ try{ ws[i](); }catch(e){} }
  }
  function aiSlotWait(m){
    return new Promise(function(res){ (AI_SLOT_WAIT[m] = AI_SLOT_WAIT[m] || []).push(res); });
  }
  /* 取名额：返回 'ok' | 'cooldown' | 'busy'。
     非链尾等待 budget 短（快速换下一个模型），链尾给足预算（保底模型仍要能服务）。 */
  async function aiSlotAcquire(m, budgetMs){
    var t0 = Date.now();
    while (true){
      if (aiInCooldown(m)) return 'cooldown';
      if (aiSlotTry(m)) return 'ok';
      if (Date.now() - t0 > budgetMs) return 'busy';
      await aiSlotWait(m);
    }
  }
  function aiRetryable(e){(FIX_B_PLACEHOLDER)}
  function aiRateLimited(e){
    var s = String((e && e.message) || e || '');
    return /1305|429|访问量过大|速率限制|限流|频率|too many|rate.?limit|系统繁忙|繁忙/i.test(s);
  }
  function aiModelOf(o){ return (o && o._model) || resolve(getCfg()).model; }
  function aiInCooldown(m){
    var until = m ? AI_RATE_UNTIL[m] : 0;
    if (!until) return false;
    if (Date.now() >= until) { delete AI_RATE_UNTIL[m]; return false; }
    return true;
  }
  async function chatLLM(messages, opts){
    opts = opts || {};
    var lastErr = null;
    var onZhipu = String(resolve(getCfg()).base || '').indexOf('bigmodel.cn') >= 0;
    // 链首 = 用户配置的主模型（默认 glm-4-flash-250414），其后为两个稳定的免费 Flash 备用模型
    var chain = onZhipu ? [null].concat(AI_FALLBACK_MODELS) : [null, null, null];
    for (var _i = 0; _i < chain.length; _i++){
      var o = chain[_i] ? Object.assign({}, opts, { _model: chain[_i] }) : opts;
      var _m = aiModelOf(o);
      var _tail = (_i === chain.length - 1);
      /* __STRESSFIX_20260923__ 链尾同样参与冷却检查：旧实现只跳过链首，
         导致链首被熔断后流量单点压向链尾；链尾再被打爆则整链不可用。
         全部模型都在冷却时快速失败并给出明确文案，而不是空等 25s 超时。 */
      var _acq = await aiSlotAcquire(_m, _tail ? 20000 : 1200);
      if (_acq !== 'ok'){
        lastErr = lastErr || new Error(_acq === 'cooldown'
          ? 'ALL_MODELS_COOLDOWN 全部模型处于限流冷却中，请稍后再试'
          : 'ALL_MODELS_BUSY 模型并发已满，请稍后再试');
        continue;
      }
      var _retry = true;
      try {
        var out = await chatLLMOnce(messages, o);
        // 空正文（推理模型把内容放在 reasoning_content / 被 max_tokens 截断）→ 换下一个模型，
        // 而不是静默返回空串，让业务侧误判成「联网没搜到价格」
        if(!String(out || '').trim()) lastErr = new Error('EMPTY_CONTENT 模型未返回正文');
        else return out;
      } catch(e){
        lastErr = e;
        _retry = aiRetryable(e);
        if(aiRateLimited(e)) AI_RATE_UNTIL[_m] = Date.now() + AI_RATE_COOLDOWN;
      } finally {
        aiSlotRelease(_m);
      }
      if(!_retry || _tail) break;
      await new Promise(function(r){ setTimeout(r, AI_RETRY_BACKOFF[_i] || 1500); });
    }
    throw lastErr;
  }"""


def fix_qa(s):
    if MARK in s:
        return s, 'skip'
    # C：整体替换 熔断/降级链 区段（用 B 的旧文本作为区段内锚点之一）
    i = s.find(C_OLD_START)
    if i < 0:
        raise SystemExit('FIX-C 起始锚点未命中（qa.html）')
    j = s.find(C_OLD_END, i)
    if j < 0:
        raise SystemExit('FIX-C 结束锚点未命中（qa.html）')
    j += len(C_OLD_END)
    old = s[i:j]
    if len(old) < 1500 or len(old) > 4500:
        raise SystemExit('FIX-C 命中长度异常：%d（期望 1500~4500），拒绝写入' % len(old))
    if B_OLD not in old:
        raise SystemExit('FIX-C 区段内未包含 aiRetryable 旧实现，拒绝写入')
    if B2_OLD not in s:
        raise SystemExit('FIX-B2 锚点未命中（chatLLMOnce 的 !res.ok 分支）')
    # 把 B 的新 aiRetryable 内联进 C 的新区段，保证只留一份定义
    body = B_NEW.split('function aiRetryable(e){', 1)[1]
    body = body[:body.rfind('}')]
    new = C_NEW.replace('function aiRetryable(e){(FIX_B_PLACEHOLDER)}', 'function aiRetryable(e){' + body + '}')
    s = s[:i] + new + s[j:]
    # B2：chatLLMOnce 保留状态码（在 C 区段之后，单独替换）
    s = s.replace(B2_OLD, B2_NEW, 1)
    return s, 'apply'


# ================================================== FIX-D risk/api/api-client.js
D_OLD = """  function getToken() {
    try {
      const s = JSON.parse(localStorage.getItem('cabin_risk_session_v1') || 'null');
      return s?.token || null;
    } catch { return null; }
  }"""

D_NEW = """  /* __STRESSFIX_20260923__ risk 会话自动补建。
     主登录流程只写 cabin_session_v1，risk 专属会话键（cabin_risk_session_v1）从不写入，
     而 mock 服务的 requireAuth 直接读该键 → quiz / kbadmin 模块恒报
     「未登录或会话已过期」，天气与风险因子能力静默失效。
     这里在主会话存在而 risk 会话缺失时，用 mock 的 user_id 备用登录路径补建会话。
     补建失败不影响原请求（与修复前行为一致，只是不再必然 401）。 */
  var _riskProvisioning = null;
  function readRiskSession() {
    try {
      const s = JSON.parse(localStorage.getItem('cabin_risk_session_v1') || 'null');
      return (s && s.token) ? s : null;
    } catch { return null; }
  }
  function readMainSession() {
    try {
      const m = JSON.parse(localStorage.getItem('cabin_session_v1') || 'null');
      return (m && typeof m === 'object') ? m : null;
    } catch { return null; }
  }
  async function ensureRiskSession() {
    if (readRiskSession()) return true;
    const m = readMainSession();
    if (!m) return false;
    const uid = m['工号'] || m.user_id || m.user || m.account || '';
    if (!uid || !global.CabinMockServer) return false;
    if (_riskProvisioning) return _riskProvisioning;
    _riskProvisioning = (async () => {
      try {
        const res = await global.CabinMockServer.handle('POST', '/api/v1/auth/login', {
          query: {},
          body: {
            user_id: String(uid),
            user_name: m['姓名'] || m.user_name || '管理员',
            base_id: m.base_id || 'Z1'
          }
        });
        return !!(res && res.ok && readRiskSession());
      } catch (e) { return false; }
      finally { _riskProvisioning = null; }
    })();
    return _riskProvisioning;
  }
  function getToken() {
    try {
      const s = readRiskSession();
      return s?.token || null;
    } catch { return null; }
  }"""

D_ANCHOR = """      // 调用 Mock 服务端
      const token = getToken();"""

D_ANCHOR_NEW = """      // 调用 Mock 服务端
      await ensureRiskSession();
      const token = getToken();"""


def fix_risk(s):
    if MARK in s:
        return s, 'skip'
    if D_OLD not in s:
        raise SystemExit('FIX-D 锚点未命中（risk/api/api-client.js getToken）')
    if D_ANCHOR not in s:
        raise SystemExit('FIX-D 锚点未命中（request() 内调用点）')
    s = s.replace(D_OLD, D_NEW, 1)
    s = s.replace(D_ANCHOR, D_ANCHOR_NEW, 1)
    return s, 'apply'


# ==================================================== FIX-E _build_pwa.py 的 SW
E_OLD_NAME = "const CACHE_NAME = 'cabin-pwa-v1';"
E_NEW_NAME = """/* __STRESSFIX_20260923__ 缓存版本化：原实现 CACHE_NAME 固定为 cabin-pwa-v1 且 activate
   不清理旧缓存、cache-first 无重新验证 → 版本更新后用户可能长期被锁在旧内容里。
   改名升级即触发重新预缓存，并在 activate 中清掉历史版本。 */
const CACHE_VERSION = 'v2';
const CACHE_NAME = 'cabin-pwa-' + CACHE_VERSION;"""

E_OLD_CORE = """  './icons/maskable-512.png'
];"""
E_NEW_CORE = """  './icons/maskable-512.png',
  // __STRESSFIX_20260923__ 预缓存首屏高频模块：原实现只缓存壳与图标，
  // 离线点开未访问过的模块只会拿到 503 纯文本
  './qa.html',
  './cc-home.html',
  './daily.html',
  './beauty.html',
  './quiz.html'
];"""

E_OLD_ACT = """self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});"""
E_NEW_ACT = """self.addEventListener('activate', (event) => {
  // __STRESSFIX_20260923__ 清除历史版本缓存，避免升级后旧内容长期驻留
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.map((k) => (k !== CACHE_NAME ? caches.delete(k) : null)));
    await self.clients.claim();
  })());
});"""

E_OLD_FETCH = """      const cached = await cache.match(event.request);
      if (cached) return cached;
      try {
        const response = await fetch(event.request);
        if (response && response.status === 200) {
          cache.put(event.request, response.clone());
        }
        return response;
      } catch (err) {"""
E_NEW_FETCH = """      const cached = await cache.match(event.request);
      if (cached) {
        // __STRESSFIX_20260923__ stale-while-revalidate：先给可用内容，同时在后台静默更新，
        // 避免 cache-first 让用户长期停在旧版本
        event.waitUntil((async () => {
          try {
            const fresh = await fetch(event.request);
            if (fresh && fresh.status === 200) cache.put(event.request, fresh.clone());
          } catch (e) {}
        })());
        return cached;
      }
      try {
        const response = await fetch(event.request);
        if (response && response.status === 200) {
          cache.put(event.request, response.clone());
        }
        return response;
      } catch (err) {"""


def fix_sw(s):
    if MARK in s:
        return s, 'skip'
    for name, old in (('CACHE_NAME', E_OLD_NAME), ('CORE_URLS', E_OLD_CORE),
                      ('activate', E_OLD_ACT), ('fetch', E_OLD_FETCH)):
        if old not in s:
            raise SystemExit('FIX-E 锚点未命中（_build_pwa.py 的 %s）' % name)
    s = s.replace(E_OLD_NAME, E_NEW_NAME, 1)
    s = s.replace(E_OLD_CORE, E_NEW_CORE, 1)
    s = s.replace(E_OLD_ACT, E_NEW_ACT, 1)
    s = s.replace(E_OLD_FETCH, E_NEW_FETCH, 1)
    return s, 'apply'


TARGETS = [
    ('index.html', fix_index, ['$STRESSFIX', 'frameReadyFlag', '_loaded[id] = false']),
    ('qa.html', fix_qa, ['$STRESSFIX', 'aiSlotAcquire', 'AI_MAX_INFLIGHT', '_httpErr.status']),
    ('risk/api/api-client.js', fix_risk, ['$STRESSFIX', 'ensureRiskSession', 'readRiskSession']),
    ('PWA封装/_build_pwa.py', fix_sw, ['$STRESSFIX', 'CACHE_VERSION', 'stale-while-revalidate']),
]


def main():
    print('===== 压力测试缺陷修复（%s）=====' % ('--check 只校验' if CHECK else '应用'))
    fails = []
    for rel, fn, needles in TARGETS:
        p = os.path.join(BASE, rel)
        if not os.path.exists(p):
            print('  [MISS] %-28s 目标文件不存在' % rel)
            fails.append(rel)
            continue
        s = read(p)
        if CHECK:
            miss = [n for n in needles if n.replace('$STRESSFIX', MARK) not in s]
            if miss:
                print('  [FAIL] %-28s 缺少：%s' % (rel, ', '.join(miss)))
                fails.append(rel)
            else:
                print('  [ OK ] %-28s 修复标记齐全' % rel)
            continue
        try:
            out, act = fn(s)
        except SystemExit as e:
            print('  [FAIL] %-28s %s' % (rel, e))
            fails.append(rel)
            continue
        if act == 'skip':
            print('  [skip] %-28s 已修复（幂等跳过）' % rel)
            continue
        write(p, out)
        print('  [done] %-28s %d → %d 字符' % (rel, len(s), len(out)))

    if CHECK:
        print('\n--check 结论：%s' % ('全部就位' if not fails else '缺失 %d 项' % len(fails)))
        return 1 if fails else 0
    print('\n结论：%s' % ('全部应用成功' if not fails else '失败 %d 项：%s' % (len(fails), fails)))
    print('复查命令：python _apply_stressfix_20260923.py --check')
    return 1 if fails else 0


if __name__ == '__main__':
    raise SystemExit(main())
