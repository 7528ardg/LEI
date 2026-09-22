/* 你问我答 · 跳转落地（A4 接收侧）回归（常驻）
 * 验的是**闭环**，不是单边：
 *   1) URL 通道  manual.html?from=qa&q=… → 落地条显示 + 文本正确 + 可关闭
 *   2) 填入搜索框  点按钮后有明确反馈（已填入 / 没找到搜索框），不静默失败
 *   3) 闭环       qa 侧 jumpTo 写出上下文 → 目标板块真的接住 → 且消费即清
 *   4) 边界       超过 TTL 不显示；无上下文不显示
 * 用法：node _verify_qa_landing.js     失败即非零退出（供 _build_all.py 守护）
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
    } catch (e) { /* 下一个 */ }
  }
  throw new Error("无法启动浏览器");
}

const Q = "\u8fdf\u5230\u600e\u4e48\u6263\u5206";   // 迟到怎么扣分

(async () => {
  console.log("=== 你问我答 · 跳转落地回归 ===");
  const browser = await launch();
  const ctx = await browser.newContext();

  /* ---------------- 1) URL 通道 ---------------- */
  console.log("\n[1] URL 通道 ?from=qa&q=");
  const p1 = await ctx.newPage();
  await p1.goto(fileUrl("manual.html") + "?from=qa&q=" + encodeURIComponent(Q));
  await p1.waitForTimeout(1400);

  const urlShown = await p1.evaluate(() => {
    const b = document.getElementById("qaLanding");
    if (!b || b.hidden) return { shown: false };
    const q = document.getElementById("qaLandingQ");
    return { shown: true, text: q ? q.textContent : "", bar: b.innerText.slice(0, 60) };
  });
  ok("落地条显示", urlShown.shown, JSON.stringify(urlShown));
  ok("带回原问题文本", /迟到|扣分/.test(String(urlShown.text)), String(urlShown.text));
  ok("文案标明来源「你问我答」", /你问我答/.test(String(urlShown.bar)), String(urlShown.bar));

  /* ---------------- 2) 填入搜索框 ---------------- */
  console.log("\n[2] 填入搜索框");
  const fill = await p1.evaluate(() => {
    const b = document.getElementById("qaLandingFill");
    if (!b) return { err: "no-btn" };
    b.click();
    const box = window.QaLanding.find();
    return {
      label: b.textContent,
      found: !!box,
      value: box ? String(box.value) : "",
    };
  });
  ok("点按钮后有明确反馈", /已填入|没找到/.test(String(fill.label)), JSON.stringify(fill));
  if (fill.found) {
    ok("找到输入框时确实填入了问题", /迟到/.test(fill.value), JSON.stringify(fill.value));
  } else {
    ok("找不到搜索框时给出提示而非静默失败", /没找到/.test(String(fill.label)), JSON.stringify(fill.label));
  }

  /* ---------------- 3) 闭环：qa 写出 → 目标页接住 ---------------- */
  console.log("\n[3] 闭环（qa jumpTo → 目标板块）");
  /* 先关掉 p1：它也是 manual.html，同模块会同样认领上下文（真实行为如此），
     留着会抢走"目标页是否接住"的判定 */
  await p1.close();

  const pq = await ctx.newPage();
  await pq.goto(fileUrl("qa.html"));
  await pq.waitForTimeout(1600);

  const wrote = await pq.evaluate(() => {
    try { localStorage.removeItem("spring_jump_ctx"); } catch (e) {}
    try { window.open = function () { return null; }; } catch (e) {}
    try { window.ask("迟到怎么扣分"); } catch (e) {}
    try { window.jumpTo("manual"); } catch (e) {}
    return localStorage.getItem("spring_jump_ctx") || "";
  });
  ok("qa 跳转时写出 localStorage 上下文", /迟到/.test(wrote), String(wrote).slice(0, 80));

  const land = await ctx.newPage();
  await land.goto(fileUrl("manual.html"));
  await land.waitForTimeout(1400);
  const got = await land.evaluate(() => {
    const b = document.getElementById("qaLanding");
    return {
      shown: !!(b && !b.hidden),
      text: document.getElementById("qaLandingQ") ? document.getElementById("qaLandingQ").textContent : "",
    };
  });
  ok("目标板块接住了带入的问题", got.shown && /迟到/.test(String(got.text)), JSON.stringify(got));

  const consumed = await land.evaluate(() => localStorage.getItem("spring_jump_ctx"));
  ok("消费即清（下次手动打开不再误弹）", consumed === null, String(consumed));

  /* ---------------- 4) 边界 ---------------- */
  console.log("\n[4] 边界");
  await land.evaluate(() => {
    localStorage.setItem("spring_jump_ctx", JSON.stringify({ from: "qa", q: "\u8fc7\u671f\u6d4b\u8bd5", t: Date.now() - 10 * 60 * 1000 }));
  });
  const p2 = await ctx.newPage();
  await p2.goto(fileUrl("manual.html"));
  await p2.waitForTimeout(1100);
  const expired = await p2.evaluate(() => {
    const b = document.getElementById("qaLanding");
    return !!(b && !b.hidden);
  });
  ok("超过 5 分钟 TTL 不再显示", !expired, "shown=" + expired);

  await p2.evaluate(() => localStorage.removeItem("spring_jump_ctx"));
  const p3 = await ctx.newPage();
  await p3.goto(fileUrl("manual.html"));
  await p3.waitForTimeout(1100);
  const clean = await p3.evaluate(() => {
    const b = document.getElementById("qaLanding");
    return !!(b && !b.hidden);
  });
  ok("无上下文时不打扰（不显示）", !clean, "shown=" + clean);

  const badFrom = await p3.evaluate(() => {
    localStorage.setItem("spring_jump_ctx", JSON.stringify({ from: "other", q: "\u4e0d\u8be5\u663e\u793a", t: Date.now() }));
    const b = document.getElementById("qaLanding");
    window.QaLanding.boot();
    return !!(b && !b.hidden);
  });
  ok("来源不是 qa 的上下文不接管", !badFrom, "shown=" + badFrom);

  const otherTo = await p3.evaluate(() => {
    localStorage.setItem("spring_jump_ctx", JSON.stringify({ from: "qa", q: "\u70b9\u540d\u7ed9\u522b\u7684\u6a21\u5757", to: "quiz", t: Date.now() }));
    const b = document.getElementById("qaLanding");
    b.hidden = true;
    window.QaLanding.boot();
    return !!(b && !b.hidden);
  });
  ok("点名给别的模块时不认领（manual ≠ quiz）", !otherTo, "shown=" + otherTo);

  await browser.close();
  console.log("\n=== 通过 " + pass + " / " + (pass + fail) + " 项 ===");
  if (fail) { console.log("!! " + fail + " 项失败"); process.exit(1); }
  console.log("全部通过 \u2713");
})().catch((e) => { console.error("ERR " + (e && e.stack || e)); process.exit(1); });
