/* ============================================================================
   CC3D —— 「客舱小助手」真 3D 形象渲染层（three.js r147 UMD，无需打包器）
   依赖：models/lib/three.min.js + models/lib/GLTFLoader.js（经典 script，file:// 可用）
   用法：
     CC3D.mount(el, {form:1})        // 在容器里挂一个 3D 形象
     CC3D.setForm(el, 7)             // 换形态（按需加载 + 缓存）
     CC3D.destroy(el)
     CC3D.ready()                    // three 是否可用
     CC3D.modelUrl(i)                // 第 i 个形态的 GLB 地址
   说明：
     - 生成服务的 GLB 是 Z-up（实测包围盒 Z 轴最长），这里自动校正成 Y-up 站立
     - 自动居中、按高度归一，方便放进不同尺寸的容器
     - 指针视差 + 呼吸浮动 + 接触阴影；prefers-reduced-motion 时静止
     - 模型不存在时返回 false，调用方保留 2D 精灵兜底
   ============================================================================ */
(function () {
  'use strict';
  if (!window.THREE) { window.CC3D = { ready: function () { return false; } }; return; }
  var T = window.THREE;
  var BASE = 'ccmodels/models/';
  var CACHE_MAX = 6;
  var cache = {};           // i -> {scene, size, url}
  var order = [];           // LRU
  var miss = {};            // i -> true（确认没有模型文件，避免反复请求）
  var gltfLoader = null;
  var envTex = null;

  function url(i) { return BASE + 'cc' + (i < 10 ? '0' + i : i) + '.glb'; }

  function loader() {
    if (!gltfLoader) {
      var L = T.GLTFLoader || (T.GLTFLoader && T.GLTFLoader.GLTFLoader);
      if (!L) throw new Error('GLTFLoader 未加载');
      gltfLoader = new L();
    }
    return gltfLoader;
  }

  /* ---------- 环境贴图：一张竖向渐变的等距柱状图，经 PMREM 变成柔和环境光 ---------- */
  function env(renderer) {
    if (envTex) return envTex;
    try {
      var c = document.createElement('canvas');
      c.width = 32; c.height = 64;
      var g = c.getContext('2d');
      var grd = g.createLinearGradient(0, 0, 0, 64);
      grd.addColorStop(0.00, '#ffffff');
      grd.addColorStop(0.42, '#dfeee6');
      grd.addColorStop(0.55, '#9fb4a8');
      grd.addColorStop(1.00, '#2c3a33');
      g.fillStyle = grd; g.fillRect(0, 0, 32, 64);
      var tex = new T.CanvasTexture(c);
      tex.mapping = T.EquirectangularReflectionMapping;
      var pm = new T.PMREMGenerator(renderer);
      envTex = pm.fromEquirectangular(tex).texture;
      pm.dispose(); tex.dispose();
    } catch (e) { envTex = null; }
    return envTex;
  }

  /* ---------- 归一化：自动判轴 + 居中 + 按高度缩放 ---------- */
  function normalize(root) {
    var box = new T.Box3().setFromObject(root);
    var s = box.getSize(new T.Vector3());
    if (s.z > s.y * 1.25) { root.rotation.x = -Math.PI / 2; root.updateMatrixWorld(true); box.setFromObject(root); s = box.getSize(new T.Vector3()); }
    else if (s.x > s.y * 1.25 && s.x > s.z) { root.rotation.z = Math.PI / 2; root.updateMatrixWorld(true); box.setFromObject(root); s = box.getSize(new T.Vector3()); }
    var c = box.getCenter(new T.Vector3());
    var k = 1.0 / Math.max(0.0001, s.y);
    var wrap = new T.Group();
    root.position.set(-c.x, -box.min.y, -c.z);
    wrap.add(root);
    wrap.scale.setScalar(k);
    /* 注意：wrap 已把整体缩放到「高度=1」，所以取景时的 h 必须是 1（返回缩放前的 s.y 会让角色只占半屏） */
    return { wrap: wrap, h: 1.0, w: Math.max(s.x, s.z) * k };
  }

  function makeStage(el, opt) {
    var scene = new T.Scene();
    var cam = new T.PerspectiveCamera(32, 1, 0.05, 60);
    /* 2026-09-19：WebGL 上下文创建失败（老设备/被禁用/渲染进程异常）时返回 null，
       由 mount() 回落 2D 精灵兜底，绝不让 3D 失败打断页面 */
    var renderer;
    try {
      renderer = new T.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    } catch (e) { return null; }
    renderer.setClearAlpha(0);
    if ('outputEncoding' in renderer) renderer.outputEncoding = T.sRGBEncoding;
    if ('toneMapping' in renderer) { renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.06; }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    el.appendChild(renderer.domElement);
    renderer.domElement.style.cssText = 'width:100%;height:100%;display:block;';

    var e = env(renderer);
    if (e) scene.environment = e;
    scene.add(new T.HemisphereLight(0xffffff, 0x4a5a52, 0.62));
    var key = new T.DirectionalLight(0xfff6e8, 1.25); key.position.set(2.2, 3.4, 2.6); scene.add(key);
    var fill = new T.DirectionalLight(0xd9f0e4, 0.42); fill.position.set(-2.6, 1.4, 1.2); scene.add(fill);
    var rim = new T.DirectionalLight(0x8fffc4, 1.05); rim.position.set(-1.1, 2.0, -3.0); scene.add(rim);

    var rootG = new T.Group(); scene.add(rootG);            // 视差 / 浮动的载体
    var inner = new T.Group(); rootG.add(inner);            // 模型本体
    var holder = new T.Group(); inner.add(holder);

    var state = {
      el: el, scene: scene, cam: cam, renderer: renderer, rootG: rootG, inner: inner, holder: holder,
      form: 0, raf: 0, t0: performance.now(), alive: true, has: false,
      px: 0, py: 0, tx: 0, ty: 0, dead: false
    };
    return state;
  }

  function fit(state) {
    var r = state.el.getBoundingClientRect();
    var w = Math.max(2, Math.round(r.width)), h = Math.max(2, Math.round(r.height));
    if (state.renderer.domElement.width !== Math.round(w * state.renderer.getPixelRatio())) {
      state.renderer.setSize(w, h, false);
      state.cam.aspect = w / h;
      state.cam.updateProjectionMatrix();
    }
  }

  function place(state, info) {
    var pad = 1.14;
    var h = info.h || 1, w = info.w || 1;
    var camH = Math.max(h * pad, (w * pad) / Math.max(0.35, state.cam.aspect));
    var d = (camH / 2) / Math.tan((state.cam.fov * Math.PI / 180) / 2);
    state.cam.position.set(0, h * 0.54, d);
    state.cam.lookAt(0, h * 0.5, 0);
  }

  function after(state, i, g, cb) {
    var info = normalize(g.scene);
    var rec = { wrap: info.wrap, h: info.h, w: info.w };
    cache[i] = rec; order.push(i);
    while (order.length > CACHE_MAX) {
      var k = order.shift();
      if (k !== i && cache[k]) { try { cache[k].wrap.traverse(function (o) { if (o.geometry) o.geometry.dispose(); }); } catch (e) {} delete cache[k]; }
    }
    cb(rec);
  }

  function b64buf(s) {
    var b = atob(s.slice(s.indexOf(',') + 1));
    var u = new Uint8Array(b.length);
    for (var i = 0; i < b.length; i++) u[i] = b.charCodeAt(i);
    return u.buffer;
  }

  /* file:// 下 fetch .glb 会被 CORS 拦掉，改用 <script src> 注入 base64 包装 */
  function viaScript(state, i, cb) {
    if (window.CC3D_MODELS && window.CC3D_MODELS[i]) {
      try { loader().parse(b64buf(window.CC3D_MODELS[i]), BASE, function (g) { after(state, i, g, cb); }, function (e) { cb(null, e); }); }
      catch (e) { cb(null, e); }
      return;
    }
    var s = document.createElement('script');
    s.src = BASE + 'js/cc' + (i < 10 ? '0' + i : i) + '.js';
    s.onload = function () {
      var d = window.CC3D_MODELS && window.CC3D_MODELS[i];
      if (!d) { cb(null, new Error('js 包装里没有模型 ' + i)); return; }
      try { loader().parse(b64buf(d), BASE, function (g) { after(state, i, g, cb); }, function (e) { cb(null, e); }); }
      catch (e) { cb(null, e); }
    };
    s.onerror = function () { cb(null, new Error('模型文件缺失')); };
    document.head.appendChild(s);
  }

  function loadModel(state, i, cb) {
    if (cache[i]) { order = order.filter(function (x) { return x !== i; }); order.push(i); cb(cache[i]); return; }
    if (miss[i]) { cb(null, new Error('无模型')); return; }
    var done = function (rec, err) { if (!rec) miss[i] = true; cb(rec, err); };
    var isFile = (location.protocol === 'file:');
    if (isFile) { viaScript(state, i, done); return; }
    /* 2026-09-19：loader().load 同步抛错（Loader 缺失等）也走 viaScript 回退 */
    try {
      loader().load(url(i), function (g) { after(state, i, g, done); },
        undefined, function (err) { viaScript(state, i, function (r, e) { done(r, e || err); }); });
    } catch (e) {
      viaScript(state, i, function (r, e2) { done(r, e2 || e); });
    }
  }

  function setForm(el, i) {
    var st = el.__cc3d; if (!st) return false;
    if (st.form === i) return true;
    st.form = i;
    if (!i) { clear(st); return false; }
    loadModel(st, i, function (rec, err) {
      if (!st.alive) return;
      if (!rec) { clear(st); if (el.__cc3dFallback) el.__cc3dFallback(); return; }
      clearChild(st);
      st.holder.add(rec.wrap);
      st.has = true;
      st.info = { h: rec.h, w: rec.w };
      place(st, st.info);
      if (el.__cc3dOnReady) el.__cc3dOnReady(i);
      start(st);
    });
    return true;
  }
  function clearChild(st) { while (st.holder.children.length) st.holder.remove(st.holder.children[0]); }
  function clear(st) { clearChild(st); st.has = false; }

  function motion() {
    try { return !window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return true; }
  }

  function start(st) {
    if (st.raf) return;
    if (!motion()) { st.renderer.render(st.scene, st.cam); return; }
    var loop = function () {
      if (!st.alive) return;
      st.raf = requestAnimationFrame(loop);
      var t = (performance.now() - st.t0) / 1000;
      st.px += (st.tx - st.px) * 0.07;
      st.py += (st.ty - st.py) * 0.07;
      st.rootG.rotation.y = st.px * 0.5 + Math.sin(t * 0.42) * 0.10;
      st.rootG.rotation.x = -st.py * 0.22;
      st.inner.position.y = Math.sin(t * 0.9) * 0.012;
      if (st.has) st.renderer.render(st.scene, st.cam);
    };
    loop();
  }

  function bindPointer(st) {
    var on = function (ev) {
      var r = st.el.getBoundingClientRect();
      var x = ((ev.clientX - r.left) / Math.max(1, r.width)) * 2 - 1;
      var y = ((ev.clientY - r.top) / Math.max(1, r.height)) * 2 - 1;
      st.tx = Math.max(-1, Math.min(1, x));
      st.ty = Math.max(-1, Math.min(1, y));
    };
    window.addEventListener('pointermove', on, { passive: true });
    st._unbind = function () { window.removeEventListener('pointermove', on); };
  }

  var mount = function (el, opt) {
    if (!el || el.__cc3d) {
      if (el && el.__cc3d && opt && opt.form) setForm(el, opt.form);
      return false;
    }
    opt = opt || {};
    var st = makeStage(el, opt);
    if (!st) return false;          /* WebGL 不可用 → 调用方保留 2D 兜底（2026-09-19） */
    el.__cc3d = st;
    bindPointer(st);
    fit(st);
    st._ro = (window.ResizeObserver && new ResizeObserver(function () { fit(st); if (st.has) place(st, st.info || { h: 1, w: 1 }); })) || null;
    if (st._ro) st._ro.observe(el);
    setForm(el, opt.form || 0);
    return true;
  };

  var destroy = function (el) {
    var st = el && el.__cc3d; if (!st) return;
    st.alive = false;
    if (st.raf) cancelAnimationFrame(st.raf);
    if (st._ro) { try { st._ro.disconnect(); } catch (e) {} }
    if (st._unbind) st._unbind();
    try { st.renderer.dispose(); if (st.renderer.domElement.parentNode) st.renderer.domElement.parentNode.removeChild(st.renderer.domElement); } catch (e) {}
    delete el.__cc3d;
  };

  window.CC3D = {
    ready: function () { return !!(window.THREE && (window.THREE.GLTFLoader)); },
    /* 该形态是否有 3D 模型：
       - 有 CC3D_READY 清单（构建时写入）时就按清单；
       - 没有清单就「乐观探测」——按需加载，失败自动记入 miss 并回落精灵。
       这样模型文件陆续生成时，页面无需重新构建即可自动用上。 */
    can: function (i) {
      if (!i || miss[i]) return false;
      if (window.CC3D_READY && window.CC3D_READY.length) return window.CC3D_READY.indexOf(i) >= 0;
      return true;
    },
    missing: function (i) { return !!miss[i]; },
    mount: mount,
    setForm: setForm,
    destroy: destroy,
    modelUrl: url,
    preload: function (i) { if (!i) return; loadModel({ alive: true }, i, function () {}); }
  };
})();
