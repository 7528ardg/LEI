/* APK 内容 + 虚拟域环境实测（不依赖模拟器）
 * ---------------------------------------------------------------------------
 * 用途：把 https://cabin.local/** 用路由拦截直接映射到 APK 解包后的
 *       assets/www/** —— 验的是**真正打进 APK 的那份文件**，以及虚拟域/https 环境。
 * 与 _e2e_apk_cdp_test.js 的分工：
 *   模拟器版 = 真 WebView（最真实，但本机软件渲染会段错误，不稳定）
 *   本脚本   = 真 APK 内容 + 真协议（快、稳，可常驻回归）
 * 用法：node _e2e_apk_www_test.js
 */
"use strict";
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright-core");

const WWW = path.join(__dirname, "APK封装", "CabinAssistant", "assets", "www");
const SHOTS = path.join(__dirname, "_apk_field_shots");
if (!fs.existsSync(SHOTS)) fs.mkdirSync(SHOTS, { recursive: true });

const MIME = {
  ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
  ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
  ".svg": "image/svg+xml", ".glb": "model/gltf-binary", ".gz": "application/gzip",
  ".mp3": "audio/mpeg", ".woff2": "font/woff2", ".ico": "image/x-icon", ".bin": "application/octet-stream",
};

let pass = 0, fail = 0;
const notes = [];
const ok = (n, c, e) => {
  if (c) { pass++; console.log("  \u2713 " + n); }
  else { fail++; console.log("  \u2717 " + n + (e ? "  :: " + String(e).slice(0, 200) : "")); }
};
const note = (s) => { notes.push(s); console.log("    \u00b7 " + s); };

(async () => {
  console.log("=== APK 内容 + 虚拟域实测（assets/www）===");
  if (!fs.existsSync(path.join(WWW, "index.html"))) {
    console.log("!! 找不到 APK assets/www/index.html");
    process.exit(1);
  }
  const apkStat = fs.statSync(path.join(WWW, "index.html"));
  note("被测入口：APK封装/CabinAssistant/assets/www/index.html（" + Math.round(apkStat.size / 1024) + " KB）");

  const browser = await chromium.launch({ channel: "msedge", headless: true })
    .catch(() => chromium.launch({ headless: true }));

  /* Android WebView 形态 */
  const ctx = await browser.newContext({
    viewport: { width: 393, height: 851 },
    isMobile: true, hasTouch: true, deviceScaleFactor: 2.75,
    userAgent: "Mozilla/5.0 (Linux; Android 14; sdk_gphone64_x86_64 Build/UE1A.230829.036; wv) "
      + "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/124.0.6367.82 Mobile Safari/537.36",
  });
  const page = await ctx.newPage();

  /* 虚拟域 → assets/www 映射（等价于 MainActivity.shouldInterceptRequest） */
  await page.route("https://cabin.local/**", (route) => {
    let p;
    try { p = decodeURIComponent(new URL(route.request().url()).pathname); } catch (e) { p = "/"; }
    if (p === "/") p = "/index.html";
    const file = path.join(WWW, p.replace(/^\/+/, ""));
    if (!file.startsWith(WWW)) return route.fulfill({ status: 403, body: "forbidden" });
    try {
      const buf = fs.readFileSync(file);
      route.fulfill({ status: 200, contentType: MIME[path.extname(file).toLowerCase()] || "application/octet-stream", body: buf });
    } catch (e) {
      route.fulfill({ status: 404, body: "not found" });
    }
  });

  const pageErrors = [];
  page.on("pageerror", (e) => pageErrors.push(String(e && e.message).slice(0, 180)));

  await page.goto("https://cabin.local/index.html", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(4000);

  /* ---------- ① 虚拟域环境 ---------- */
  console.log("\n[1] 虚拟域环境");
  const env = await page.evaluate(() => ({
    protocol: location.protocol, host: location.host,
    tabs: document.querySelectorAll(".mod-tab").length,
    ua: navigator.userAgent.indexOf("wv") > 0 ? "Android WebView" : "other",
  }));
  ok("走虚拟域 https://cabin.local", env.protocol === "https:" && env.host === "cabin.local", JSON.stringify(env));
  ok("UA 为 Android WebView 形态", env.ua === "Android WebView", env.ua);
  ok("壳层模块页签 >= 12", env.tabs >= 12, "tabs=" + env.tabs);
  await page.screenshot({ path: path.join(SHOTS, "B1_APK内容_启动首屏.png") });

  /* ---------- ② APK 专属补丁（这份 index.html 就是打进包的那份） ---------- */
  console.log("\n[2] APK 专属补丁（读 APK 内文件）");
  const html = fs.readFileSync(path.join(WWW, "index.html"), "utf8");
  const marks = {
    "APK_FIX3": html.indexOf("APK_FIX3") >= 0,
    "apkSplash": html.indexOf("apkSplash") >= 0,
    // 2026-09-22：预热收敛已由壳层「预取门控」(_pwEnv) 接管 —— 手机/省流/弱网完全不预取，
    // 收敛力度强于旧补丁 APK_PREWARM_V2，故两种形态均视为通过。
    "预热收敛": html.indexOf("APK_PREWARM_V2") >= 0 || html.indexOf("function _pwEnv") >= 0,
    "APK_LRU_CORE": html.indexOf("APK_LRU_CORE") >= 0,
    "APK_LRU_FINAL": html.indexOf("APK_LRU_FINAL") >= 0,
    "MAX_LOADED": /MAX_LOADED\s*=\s*5/.test(html),
  };
  Object.keys(marks).forEach((k) => ok("补丁标记 " + k, marks[k]));
  const runtime = await page.evaluate(() => ({
    lru: typeof window.__apkLRU !== "undefined", state: !!window.__apkState,
    free: typeof window.__apkFreeMemory === "function",
  }));
  ok("LRU 运行时对象已装载", runtime.lru && runtime.state && runtime.free, JSON.stringify(runtime));

  /* ---------- ③ qa 板块（APK 内的那份 qa.html） ---------- */
  console.log("\n[3] 你问我答（APK 内 qa.html）");
  const qaHtml = fs.readFileSync(path.join(WWW, "qa.html"), "utf8");
  ok("qa.html 内含跨板块桥接", qaHtml.indexOf("__QA_BRIDGE_BEGIN__") >= 0);
  ok("qa.html 内含会话记忆", qaHtml.indexOf("__QA_MEM_BEGIN__") >= 0);
  ok("qa.html 内含能力增强", qaHtml.indexOf("__QA_CAP_BEGIN__") >= 0);
  const manHtml = fs.readFileSync(path.join(WWW, "manual.html"), "utf8");
  ok("manual.html 内含跳转落地条", manHtml.indexOf("QALANDING_BEGIN") >= 0);
  ok("落地条带目标模块认领", manHtml.indexOf("function mine(o)") >= 0);

  await page.evaluate(() => { try { switchModule("qa"); } catch (e) {} });
  await page.waitForTimeout(3800);
  const qaFrame = page.frames().find((f) => /qa\.html/.test(f.url()));
  ok("qa iframe 已加载", !!qaFrame, qaFrame ? "ok" : "none");

  if (qaFrame) {
    /* ---------- 3a) 清洁态隔离（2026-09-21 修）----------
       原断言「msgs===0」在真实使用过的设备上必然失败：qa 会从 localStorage(qa_history_v1)
       恢复上次会话（这正是 [5] 会话恢复要验证的能力）。要验证的是「首屏不自动弹欢迎卡」，
       故先清掉会话记忆并重载 qa，再做清洁态判定。 */
    await qaFrame.evaluate(() => { try { localStorage.removeItem("qa_history_v1"); } catch (e) {} });
    await qaFrame.evaluate(() => { try { location.reload(); } catch (e) {} });
    await page.waitForTimeout(2600);
    const qaClean = page.frames().find((f) => /qa\.html/.test(f.url()));
    const fresh = qaClean ? await qaClean.evaluate(() => ({
      msgs: (function () { try { return chat.msgs.length; } catch (e) { return -1; } })(),
      welcome: !!document.querySelector(".welcome"),
      suggest: !!document.getElementById("qaSuggest"),
      capSuggest: typeof (window.QaCap && window.QaCap.suggest) === "function",
      flag: (function () { try { return QA_SHOW_WELCOME; } catch (e) { return null; } })(),
    })) : null;

    const qa = await (qaClean || qaFrame).evaluate(() => ({
      bridge: typeof window.QaBridge, mem: typeof window.QaMemory, cap: typeof window.QaCap,
      msgs: (function () { try { return chat.msgs.length; } catch (e) { return -1; } })(),
      mic: (function () { const m = document.getElementById("qaMic"); return m ? { exists: true, disabled: !!m.disabled, title: m.title } : { exists: false }; })(),
      suggest: !!document.getElementById("qaSuggest"),
      models: typeof window.CC3D_MODELS,
      ready: (function () { try { return (window.CC3D_READY || []).length; } catch (e) { return -1; } })(),
    }));
    ok("四个能力模块在位", qa.bridge === "object" && qa.mem === "object" && qa.cap === "object", JSON.stringify(qa));
    /* 2026-09-19 断言反转：用户 2026-09-14 已要求「取消初始弹出的 CC·你问我答 卡片」，
       该回归曾在 QA_SHOW_WELCOME 被改回 true 时复发（用户投诉"我说我要考题目，弹出毫不相关的东西"）。
       正确行为 = 首屏不自动弹欢迎卡：清洁态下 msgs 为 0 且不存在 .welcome 卡片节点。 */
    ok("qa 首屏不自动弹欢迎卡", !!(fresh && fresh.msgs === 0 && !fresh.welcome),
       JSON.stringify(fresh));
    ok("语音按钮在 https 下可用", qa.mic.exists && !qa.mic.disabled, JSON.stringify(qa.mic));
    /* 2026-09-21 断言反转：顶部常问条已按用户要求下线（qa.html renderSuggest 内 __QA_SUGGEST_OFF_20260919__），
       故不再断言 #qaSuggest 存在，改为「不自动显示」+「推荐能力本体仍在」。 */
    ok("顶部常问条已按下线决策不再自动显示", !!(fresh && !fresh.suggest),
       fresh ? "qaSuggest=" + fresh.suggest : "no-fresh-frame");
    ok("场景推荐能力仍在（QaCap.suggest 可用）", !!(fresh && fresh.capSuggest),
       fresh ? "capSuggest=" + fresh.capSuggest : "no-fresh-frame");
    ok("3D 就绪清单 = 24", qa.ready === 24, "ready=" + qa.ready);
    ok("https 下不走 base64 回退（CC3D_MODELS 未定义）", qa.models === "undefined", "CC3D_MODELS=" + qa.models);
    note("语音按钮状态：" + (qa.mic.disabled ? "禁用（" + qa.mic.title + "）" : "可用"));
    note("清洁态 QA_SHOW_WELCOME=" + (fresh ? fresh.flag : "?") + " / msgs=" + (fresh ? fresh.msgs : "?"));
  }
  await page.screenshot({ path: path.join(SHOTS, "B2_APK内容_你问我答.png") });

  /* ---------- ④ 跨板块带入闭环 ---------- */
  console.log("\n[4] 跨板块带入闭环");
  if (qaFrame) {
    const fired = await qaFrame.evaluate(() => {
      try { localStorage.removeItem("spring_jump_ctx"); } catch (e) {}
      try { ask("迟到怎么扣分"); jumpTo("manual"); return "fired"; } catch (e) { return "ERR:" + e.message; }
    });
    ok("触发跳转", fired === "fired", String(fired));
    await page.waitForTimeout(3600);
    const act = await page.evaluate(() => { const a = document.querySelector(".mod-tab.active"); return a ? a.getAttribute("data-mod") : ""; });
    ok("壳层切到 manual", act === "manual", "active=" + act);
    const manFrame = page.frames().find((f) => /manual\.html/.test(f.url()));
    const landed = manFrame ? await manFrame.evaluate(() => {
      const b = document.getElementById("qaLanding");
      return { shown: !!(b && !b.hidden), text: (document.getElementById("qaLandingQ") || {}).textContent || "" };
    }) : { err: "no-frame" };
    ok("manual 接住带入问题", landed.shown && /迟到/.test(String(landed.text)), JSON.stringify(landed));
    const consumed = await page.evaluate(() => localStorage.getItem("spring_jump_ctx"));
    ok("上下文消费即清", consumed === null, String(consumed));
  }
  await page.screenshot({ path: path.join(SHOTS, "B3_APK内容_manual接住问题.png") });

  /* ---------- ⑤ 会话恢复 ---------- */
  console.log("\n[5] 会话恢复");
  await page.evaluate(() => { try { switchModule("qa"); } catch (e) {} });
  await page.waitForTimeout(3000);
  await page.reload();
  await page.waitForTimeout(4200);
  await page.evaluate(() => { try { switchModule("qa"); } catch (e) {} });
  await page.waitForTimeout(3400);
  const f2 = page.frames().find((f) => /qa\.html/.test(f.url()));
  const len = f2 ? await f2.evaluate(() => (function () { try { return chat.msgs.length; } catch (e) { return -1; } })()) : -1;
  ok("reload 后会话恢复", len > 1, "msgs=" + len);

  /* ---------- ⑥ 12 模块 ---------- */
  console.log("\n[6] 12 模块遍历");
  const mods = ["qa", "home", "quiz", "performance", "beauty", "risk", "medical", "daily", "manual", "report", "kbadmin", "issues"];
  const bad = [];
  for (const m of mods) {
    const r = await page.evaluate((mm) => { try { switchModule(mm); return "ok"; } catch (e) { return "ERR:" + e.message; } }, m);
    if (r !== "ok") bad.push(m);
    await page.waitForTimeout(700);
  }
  ok("12 模块全部切换成功", bad.length === 0, JSON.stringify(bad));

  const realErrs = pageErrors.filter((e) => !/favicon|Failed to fetch|NetworkError|net::/i.test(e));
  ok("无页面级 JS 报错", realErrs.length === 0, JSON.stringify(realErrs.slice(0, 3)));

  await browser.close();
  console.log("\n=== 通过 " + pass + " / " + (pass + fail) + " 项 ===");
  if (fail) { console.log("!! " + fail + " 项失败"); process.exit(1); }
  console.log("APK 内容实测全部通过 \u2713");
})().catch((e) => { console.error("ERR " + (e && e.stack || e)); process.exit(1); });
