/* 你问我答 · 跨板块桥接回归（常驻）
 * 覆盖 A 组四项改造，全部在真实浏览器里跑，不信静态断言：
 *   A2 URL 深链  ?q=&src=&from=  → 预置问题 + 静默切库 + 上下文条含来源名
 *   A1 cc:nav-jump 深跳          → 同窗口与「宿主 iframe」两条送达路径都验
 *   A3 cc:crumb 上报             → 宿主页真实收到，且切库后 crumb 跟着变
 *   A4 jumpTo 带上下文           → 包装生效 + sessionStorage 落盘 + 新标签拼 URL
 * 用法：node _verify_qa_bridge.js     失败即非零退出（供 _build_all.py 守护）
 * 依赖：playwright（仅 core，故指定 channel）
 */
"use strict";
const path = require("path");
const { chromium } = require("playwright-core");

const ROOT = __dirname;
const fileUrl = (p) => "file:///" + path.resolve(ROOT, p).replace(/\\/g, "/");

let pass = 0, fail = 0;
const ok = (name, cond, extra) => {
  if (cond) { pass++; console.log("  \u2713 " + name); }
  else { fail++; console.log("  \u2717 " + name + (extra ? "  :: " + extra : "")); }
};

async function launch() {
  for (const ch of ["msedge", "chrome", null]) {
    try {
      return await chromium.launch(ch ? { channel: ch, headless: true } : { headless: true });
    } catch (e) { /* 换下一个 */ }
  }
  throw new Error("无法启动浏览器（msedge / chrome / 内置均失败）");
}

(async () => {
  console.log("=== 你问我答 · 跨板块桥接回归 ===");
  const browser = await launch();
  const ctx = await browser.newContext();

  /* ================= 场景 1：URL 深链（A2） ================= */
  console.log("\n[A2] URL 深链 ?q=&src=&from=");
  const p1 = await ctx.newPage();
  const q1 = encodeURIComponent("值勤限制是多少");
  await p1.goto(fileUrl("qa.html") + "?q=" + q1 + "&src=ccm&from=performance");
  await p1.waitForTimeout(1600);

  const in1 = await p1.$eval("#qaInput", (el) => el.value).catch(() => "");
  ok("预置问题进输入框", in1 === "值勤限制是多少", JSON.stringify(in1));

  const barText = await p1.$eval("#qaCtxBar", (el) => el.innerText).catch(() => "");
  ok("上下文条出现", barText.length > 0, JSON.stringify(barText));
  ok("上下文条含来源名「绩效管理」", barText.indexOf("绩效管理") >= 0, JSON.stringify(barText));

  const src1 = await p1.$eval(".src-tab.active", (el) => el.dataset.src).catch(() => "");
  ok("静默切库到 ccm", src1 === "ccm", JSON.stringify(src1));

  const closable = await p1.evaluate(() => {
    const x = document.querySelector("#qaCtxBar .qa-ctx-x");
    if (!x) return "no-close-btn";
    x.click();
    return document.getElementById("qaCtxBar") === null ? "closed" : "still-there";
  });
  ok("上下文条可关闭", closable === "closed", closable);

  const hasUrl = await p1.evaluate(() => typeof URLSearchParams === "function" && !!window.QaBridge);
  ok("QaBridge 对外暴露", hasUrl);

  /* ================= 场景 2：同窗口 cc:nav-jump（A1） ================= */
  console.log("\n[A1] cc:nav-jump（同窗口送达路径）");
  await p1.evaluate(() => { document.getElementById("qaInput").value = ""; });
  await p1.evaluate(() => {
    window.postMessage({ type: "cc:nav-jump", mod: "qa", q: "病假要交什么材料", src: "mgm", from: "manual" }, "*");
  });
  await p1.waitForTimeout(500);
  const in2 = await p1.$eval("#qaInput", (el) => el.value).catch(() => "");
  ok("带入问题", in2 === "病假要交什么材料", JSON.stringify(in2));
  const src2 = await p1.$eval(".src-tab.active", (el) => el.dataset.src).catch(() => "");
  ok("按 src 切库到 mgm", src2 === "mgm", JSON.stringify(src2));
  const bar2 = await p1.$eval("#qaCtxBar", (el) => el.innerText).catch(() => "");
  ok("提示条含来源名「手册奖惩」", bar2.indexOf("手册奖惩") >= 0, JSON.stringify(bar2));

  const wrongMod = await p1.evaluate(() => {
    document.getElementById("qaInput").value = "不应被覆盖";
    window.postMessage({ type: "cc:nav-jump", mod: "quiz", q: "不该进来" }, "*");
    return document.getElementById("qaInput").value;
  });
  ok("忽略非 qa 模块的深跳", wrongMod === "不应被覆盖", JSON.stringify(wrongMod));

  /* ================= 场景 3：jumpTo 带上下文（A4） ================= */
  console.log("\n[A4] jumpTo 带上下文（发出侧）");
  const wrapped = await p1.evaluate(() => {
    const f = window.__qaBridgeFlags || {};
    window.__qaLastQ = "";
    let err = "";
    try { window.ask("迟到怎么扣分"); } catch (e) { err = String(e && e.message); }
    return { jump: !!f.jumpTo, ask: !!f.ask, lastQ: window.__qaLastQ || "", err };
  });
  ok("ask 包装链生效（__qaLastQ 已写入）", /迟到/.test(wrapped.lastQ),
     JSON.stringify(wrapped.lastQ) + " err=" + wrapped.err);
  ok("jumpTo 包装标志", wrapped.jump);
  ok("ask 包装标志", wrapped.ask);

  const saved = await p1.evaluate(() => {
    try { localStorage.removeItem("spring_jump_ctx"); } catch (e) {}
    try { window.open = function () { return null; }; } catch (e) {}
    window.ask("迟到怎么扣分");
    window.jumpTo("manual");
    return localStorage.getItem("spring_jump_ctx") || "";
  });
  let ctxObj = null;
  try { ctxObj = JSON.parse(saved); } catch (e) {}
  ok("原问题写入 localStorage（跨板块通道）", !!ctxObj && /迟到/.test(ctxObj.q || ""), saved);
  ok("上下文标记来源为 qa", !!ctxObj && ctxObj.from === "qa", saved);

  const popUrl = await p1.evaluate(() => {
    let captured = "";
    try { window.open = function (u) { captured = String(u || ""); return null; }; } catch (e) {}
    window.ask("酒测标准是多少");
    window.jumpTo("manual");
    return captured;
  });
  ok("独立打开时把问题拼进 URL", /manual\.html\?from=qa&q=/.test(popUrl), popUrl);
  ok("URL 里的问题已编码", /%E9%85%92%E6%B5%8B/.test(popUrl), popUrl);

  /* ================= 场景 4：真实宿主 iframe（A1 + A3） ================= */
  console.log("\n[A3] cc:crumb / [A1] 宿主 iframe 送达路径");
  const host = await ctx.newPage();
  await host.goto(fileUrl("_qa_bridge_host_test.html"));
  await host.waitForTimeout(2600);

  const m0 = await host.evaluate(() => window.__msgs);
  const crumb0 = m0.filter((m) => m.type === "cc:crumb");
  ok("开场即上报 cc:crumb", crumb0.length >= 1, JSON.stringify(m0));
  ok("crumb 文本含「你问我答」", crumb0.some((m) => /你问我答/.test(m.text)),
     JSON.stringify(crumb0.map((m) => m.text)));

  const sendRes = await host.evaluate(() =>
    window.__send({ type: "cc:nav-jump", mod: "qa", q: "大撤整体流程", src: "dc", from: "quiz" }));
  ok("宿主可向 iframe 发深跳", sendRes === "sent", String(sendRes));
  await host.waitForTimeout(900);

  const m1 = await host.evaluate(() => window.__msgs);
  const crumb1 = m1.filter((m) => m.type === "cc:crumb");
  ok("深跳后 crumb 跟着切库（含「大撤」）", crumb1.some((m) => /大撤/.test(m.text)),
     JSON.stringify(crumb1.map((m) => m.text).slice(-3)));
  ok("crumb 数量增长（确实重发）", crumb1.length > crumb0.length,
     crumb0.length + " -> " + crumb1.length);

  await browser.close();
  console.log("\n=== 通过 " + pass + " / " + (pass + fail) + " 项 ===");
  if (fail) { console.log("!! " + fail + " 项失败"); process.exit(1); }
  console.log("全部通过 \u2713");
})().catch((e) => { console.error("ERR " + (e && e.stack || e)); process.exit(1); });
