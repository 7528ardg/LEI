/* 你问我答 · 能力增强回归（常驻）
 * 覆盖 C 组四项：
 *   C1 语音输入   麦克风按钮在位；不支持的环境必须"禁用 + 说明原因"，不能静默失败
 *   C2 跨板块数据 拦截真实请求体，断言绩效类问题的 user 消息里带上了本机数据摘要
 *   C3 跨域引导   喂一条"未命中"回复，断言按问题域追加了去对应板块的按钮
 *   C4 场景推荐   推荐卡按时段生成、chip 可点击且真的发出提问
 * 用法：node _verify_qa_capability.js     失败即非零退出（供 _build_all.py 守护）
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

(async () => {
  console.log("=== 你问我答 · 能力增强回归 ===");
  const browser = await launch();
  const ctx = await browser.newContext();
  const page = await ctx.newPage();

  const errs = [];
  page.on("pageerror", (e) => errs.push(String(e && e.message).slice(0, 160)));

  await page.goto(fileUrl("qa.html"));
  await page.waitForTimeout(1600);

  /* ---------------- C1 语音输入 ---------------- */
  console.log("\n[C1] 语音输入");
  const mic = await page.evaluate(() => {
    const m = document.getElementById("qaMic");
    if (!m) return { exists: false };
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    return {
      exists: true,
      supported: !!SR,
      disabled: !!m.disabled,
      hasHandler: typeof m.onclick === "function",
      title: String(m.title || ""),
      size: (function () { const r = m.getBoundingClientRect(); return Math.round(r.width) + "x" + Math.round(r.height); })(),
    };
  });
  ok("麦克风按钮存在", mic.exists);
  ok("已接好交互（可用）或已禁用（不支持）", mic.supported ? mic.hasHandler : mic.disabled,
     JSON.stringify(mic));
  ok("不支持时有明确说明而非静默失败",
     mic.supported ? true : /不支持|HTTPS/.test(mic.title),
     JSON.stringify(mic.title));
  ok("触摸目标 44px 达标", mic.size === "44x44", mic.size);

  /* ---------------- C2 跨板块数据进上下文 ---------------- */
  console.log("\n[C2] 跨板块数据进 AI 上下文");
  const c2 = await page.evaluate(async () => {
    try { localStorage.setItem("qa_perf_data_v1", JSON.stringify({ v: "qa-perf-v1", rows: [{ 月份: "2026-07" }] })); } catch (e) {}
    try { localStorage.setItem("qa_train_records_v1", JSON.stringify([{ chapter: "第3章", score: 88 }])); } catch (e) {}
    window.__reqs = [];
    const of = window.fetch;
    window.fetch = function (u, o) {
      try { window.__reqs.push(o && o.body ? String(o.body) : ""); } catch (e) {}
      return Promise.resolve({
        ok: true,
        json: function () { return Promise.resolve({ choices: [{ message: { content: "\u6a21\u62df" } }] }); }
      });
    };
    try { ask("\u6211\u7684\u7ee9\u6548\u6392\u540d\u600e\u4e48\u6837"); } catch (e) {}
    await new Promise((r) => setTimeout(r, 1400));
    window.fetch = of;
    return window.__reqs;
  });
  // 2026-09-19 本地模式：不再有外部 AI 请求 → 改为「零外发 + 摘要函数仍可用」双断言
  ok("本地模式：不再发起外部 AI 请求（零外发）", c2.length === 0, "reqs=" + c2.length);
  const c2hint = await page.evaluate(() => {
    try { return String(window.QaCap.crossHint("\u6211\u7684\u7ee9\u6548\u6392\u540d\u600e\u4e48\u6837")); }
    catch (e) { return "ERR:" + e.message; }
  });
  ok("跨板块数据摘要仍可用（读出本机绩效库）", /\u7ee9\u6548\u5e93\u5df2\u6536\u5f55/.test(c2hint), c2hint.slice(0, 90));

  /* 注：这里只做单元级断言。「我的错题和练习记录」含「练习」→ 会被 qaIsTrainIntent
     判为培训练习意图走本地组卷流程，压根不调 AI，因此没有请求体可查（测试与意图路由耦合会假失败）。 */
  const c2train = await page.evaluate(() => {
    try { return window.QaCap.crossHint("\u6211\u7684\u9519\u9898\u8bb0\u5f55"); } catch (e) { return "ERR:" + e.message; }
  });
  ok("培训类问题能生成练习记录摘要", /\u7ec3\u4e60|\u8bb0\u5f55/.test(String(c2train)),
     String(c2train).slice(0, 70));

  /* ---------------- C3 跨域智能引导 ---------------- */
  console.log("\n[C3] 跨域智能引导");
  const guideMap = await page.evaluate(() => {
    const f = (t) => { try { const g = window.QaCap.guide(t); return g ? g.mod : ""; } catch (e) { return "ERR"; } };
    return {
      quiz: f("\u6211\u7684\u9519\u9898\u5728\u54ea\u91cc\u770b"),
      perf: f("\u6211\u7684\u7ee9\u6548\u6392\u540d"),
      beauty: f("\u7ed9\u6211\u4e00\u4e2a\u9500\u552e\u8bdd\u672f"),
      none: f("\u9152\u6d4b\u6807\u51c6\u662f\u591a\u5c11"),
    };
  });
  ok("错题 → 培训考核", guideMap.quiz === "quiz", JSON.stringify(guideMap));
  ok("绩效 → 绩效管理", guideMap.perf === "performance", JSON.stringify(guideMap));
  ok("话术 → 美妆话术", guideMap.beauty === "beauty", JSON.stringify(guideMap));
  ok("纯知识问题不误触发引导", guideMap.none === "", JSON.stringify(guideMap.none));

  const guideDom = await page.evaluate(() => {
    try {
      window.addMsg("bot", '<div class="kbox">\u5f53\u524d\u3010\u65e5\u5e38\u5e93\u3011\u8fd8\u6ca1\u6709\u76f4\u63a5\u547d\u4e2d"\u6211\u7684\u9519\u9898\u5728\u54ea\u91cc\u770b"\u3002</div>',
        { q: "\u6211\u7684\u9519\u9898\u5728\u54ea\u91cc\u770b" });
    } catch (e) { return "ERR:" + e.message; }
    const g = document.querySelector(".qa-guide");
    return g ? g.innerText : "";
  });
  // 引导按钮的「指向哪个板块」由当前问题域决定（此处上游已单独断言过 guide() 的映射），
  // 这里只断言「机制生效」：未命中回复里确实追加了一个「去「XX」➔」按钮。
  ok("未命中回复里追加了去板块的按钮", /去「.+」➔/.test(String(guideDom)), JSON.stringify(String(guideDom).slice(0, 70)));

  /* ---------------- C4 场景化推荐（2026-09-19 产品决策：顶部常问条已下线） ---------------- */
  console.log("\n[C4] 场景化推荐问题（已下线，断言翻转）");
  const sug = await page.evaluate(() => {
    try { window.QaCap.renderSuggest(); } catch (e) { return { err: String(e && e.message) }; }
    return { exists: !!document.getElementById("qaSuggest") };
  });
  ok("推荐卡已按用户要求下线（不再渲染）", sug.exists === false, JSON.stringify(sug));
  ok("renderSuggest 可安全调用（早退无异常）", !sug.err, JSON.stringify(sug));

  ok("全程无 pageerror", errs.length === 0, JSON.stringify(errs.slice(0, 2)));

  await browser.close();
  console.log("\n=== 通过 " + pass + " / " + (pass + fail) + " 项 ===");
  if (fail) { console.log("!! " + fail + " 项失败"); process.exit(1); }
  console.log("全部通过 \u2713");
})().catch((e) => { console.error("ERR " + (e && e.stack || e)); process.exit(1); });
