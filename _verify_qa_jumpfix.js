/* 你问我答 · 跳转目标回归（常驻）
 * 背景：原 jumpBtn 第一分支是 `if(isManualPool)`，而 isManualPool = qaSource !== 'daily'，
 *       导致 CBT / 大撤 / 手册 等**所有非日常库**的按钮恒为「去日常库再问」——
 *       用户在 CBT 题库里想练题，却没有去题库的入口（2026-09-19 用户反馈）。
 * 本回归按「当前库」逐库实测按钮文案与跳转目标，防止再次回退。
 * 用法：node _verify_qa_jumpfix.js     失败即非零退出
 */
"use strict";
const path = require("path");
const { chromium } = require("playwright-core");

const ROOT = __dirname;
const fileUrl = (p) => "file:///" + path.resolve(ROOT, p).replace(/\\/g, "/");

let pass = 0, fail = 0;
const ok = (n, c, e) => {
  if (c) { pass++; console.log("  \u2713 " + n); }
  else { fail++; console.log("  \u2717 " + n + (e ? "  :: " + String(e).slice(0, 200) : "")); }
};

function launch() {
  return chromium.launch({ channel: "msedge", headless: true })
    .catch(() => chromium.launch({ chrome: true }).catch(() => chromium.launch({ headless: true })));
}

(async () => {
  console.log("=== 你问我答 · 跳转目标回归 ===");
  const browser = await chromium.launch({ channel: "msedge", headless: true })
    .catch(() => chromium.launch({ headless: true }));
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await await page.addInitScript(() => { try { sessionStorage.setItem('qa_aitut_shown_v1','1'); } catch(e){} });
  page.goto(fileUrl("qa.html"));
  await page.waitForTimeout(1600);

  /* 在页面里注入一个"捕获跳转"的桩：把 jumpTo / window.open 的结果记下来 */
  await page.evaluate(() => {
    window.__jumps = [];
    const origOpen = window.open;
    window.open = function (u) { window.__jumps.push(String(u)); return null; };
    const origJump = window.jumpTo;
    window.jumpTo = function (mod, opts) {
      window.__jumps.push("jumpTo:" + mod);
      try { return origJump.apply(this, arguments); } catch (e) { return null; }
    };
    window.__probe = function (src, q) {
      window.__jumps = [];
      try { setQaSourceSilent(src); } catch (e) { return { err: String(e && e.message) }; }
      const wrap = document.getElementById("chatWrap");
      if (wrap) wrap.innerHTML = "";
      try { ask(q); } catch (e) { return { err: String(e && e.message) }; }
      return { ok: true };
    };
    /* 只看**最后一条消息**：chatWrap 里是全部历史，读整个 wrap 会拿到早先用例的按钮，
       造成「文案与跳转对不上」的假失败（2026-09-19 实测踩到，且 chat.msgs 累积后
       清空 wrap 也没用 —— 下次 renderChat 会把历史全部写回）。 */
    window.__readBack = function () {
      const wrap = document.getElementById("chatWrap");
      const last = wrap ? wrap.lastElementChild : null;
      return {
        html: last ? last.innerHTML : "",
        btns: last ? Array.from(last.querySelectorAll(".jump-btn")).map((b) => b.textContent.trim()) : [],
      };
    };
    window.__clickFirstJump = function () {
      const wrap = document.getElementById("chatWrap");
      const last = wrap ? wrap.lastElementChild : null;
      const b = last ? last.querySelector(".jump-btn") : null;
      if (!b) return "no-btn";
      const t = b.textContent.trim();
      b.click();
      return { label: t, jumps: window.__jumps.slice() };
    };
    return true;
  });

  const CASES = [
    { src: "cbt", q: "\u65cb\u8f6c\u5ea7\u6905\u53d6\u51fa\u9700\u65cb\u8f6c\u591a\u5c11\u5ea6", want: "\u53bb\u57f9\u8bad\u8003\u6838", mod: "quiz", ban: "\u53bb\u65e5\u5e38\u5e93\u518d\u95ee" },
    { src: "dc", q: "\u5927\u64a4\u6574\u4f53\u6d41\u7a0b", want: "\u53bb\u5927\u64a4\u7b54\u9898", mod: "quiz", ban: "\u53bb\u65e5\u5e38\u5e93\u518d\u95ee" },
    { src: "ccm", q: "\u64a4\u79bb\u53e3\u4ee4\u662f\u4ec0\u4e48", want: "\u624b\u518c\u5956\u60e9\u8be6\u60c5", mod: "manual", ban: "\u53bb\u65e5\u5e38\u5e93\u518d\u95ee" },
    { src: "mgm", q: "\u9152\u6d4b\u8d85\u6807\u6807\u51c6\u662f\u591a\u5c11", want: "\u624b\u518c\u5956\u60e9\u8be6\u60c5", mod: "manual", ban: "\u53bb\u65e5\u5e38\u5e93\u518d\u95ee" },
  ];


  /* 条件等待：轮询读回按钮/HTML，替代固定 900ms（负载下会抖动） */
  async function waitBtn(want, ms) {
    ms = ms || 6000;
    const t0 = Date.now();
    let back = await page.evaluate(() => window.__readBack());
    while (Date.now() - t0 < ms) {
      if (back.btns.some((t) => t.indexOf(want) >= 0)) return back;
      await page.waitForTimeout(150);
      back = await page.evaluate(() => window.__readBack());
    }
    return back;
  }
  async function waitHtml(sub, ms) {
    ms = ms || 6000;
    const t0 = Date.now();
    let html = (await page.evaluate(() => window.__readBack())).html;
    while (Date.now() - t0 < ms) {
      if (html.indexOf(sub) >= 0) return html;
      await page.waitForTimeout(150);
      html = (await page.evaluate(() => window.__readBack())).html;
    }
    return html;
  }

  for (const c of CASES) {
    console.log("\n[" + c.src + "] " + c.q);
    const r = await page.evaluate(({ src, q }) => window.__probe(src, q), { src: c.src, q: c.q });
    ok("可提问", !r.err, JSON.stringify(r));
    const back = await waitBtn(c.want);
    const labelHit = back.btns.some((t) => t.indexOf(c.want) >= 0);
    ok("按钮文案含「" + c.want + "」", labelHit, JSON.stringify(back.btns));
    if (c.ban) {
      ok("不再误显示「" + c.ban + "」", !back.btns.some((t) => t.indexOf(c.ban) >= 0), JSON.stringify(back.btns));
    }

    const clicked = await page.evaluate(() => window.__clickFirstJump());
    const hitMod = clicked && Array.isArray(clicked.jumps)
      && clicked.jumps.some((j) => String(j).indexOf(c.mod) >= 0 || String(j).indexOf("jumpTo:" + c.mod) >= 0);
    ok("点击后确实去 " + c.mod, hitMod, JSON.stringify(clicked));
  }

  /* CBT 专属：回答顶部应有「去培训考核」练题入口 */
  console.log("\n[CBT 练题入口]");
  await page.evaluate(() => window.__probe("cbt", "\u65cb\u8f6c\u5ea7\u6905\u53d6\u51fa\u9700\u65cb\u8f6c\u591a\u5c11\u5ea6"));
  const cbtHtml = await waitHtml("\u8fd9\u9898\u6765\u81ea CBT \u9898\u5e93");
  ok("回答顶部有练题提示条", cbtHtml.indexOf("\u8fd9\u9898\u6765\u81ea CBT \u9898\u5e93") >= 0);
  ok("提示条带「去培训考核」按钮", /jumpTo\(&#39;quiz&#39;\)|jumpTo\('quiz'\)/.test(cbtHtml), "");

  /* 大撤库也应有入口 */
  await page.evaluate(() => window.__probe("dc", "\u5927\u64a4\u6574\u4f53\u6d41\u7a0b"));
  const dcHtml = await waitHtml("\u5927\u64a4\u4e13\u9879");
  ok("大撤回答顶部有答题入口", dcHtml.indexOf("\u5927\u64a4\u4e13\u9879") >= 0);

  /* 日常库不应被误加提示条，且兜底仍是手册奖惩 */
  await page.evaluate(() => window.__probe("daily", "\u8fdf\u5230\u600e\u4e48\u6263\u5206"));
  await page.waitForTimeout(1600);
  const dailyHtml = await page.evaluate(() => window.__readBack().html);
  ok("日常库不显示题库提示条", dailyHtml.indexOf("\u8fd9\u9898\u6765\u81ea CBT \u9898\u5e93") < 0);

  await browser.close();
  console.log("\n=== 通过 " + pass + " / " + (pass + fail) + " 项 ===");
  if (fail) { console.log("!! " + fail + " 项失败"); process.exit(1); }
  console.log("全部通过 \u2713");
})().catch((e) => { console.error("ERR " + (e && e.stack || e)); process.exit(1); });
