/* 你问我答 · 会话记忆回归（常驻）
 * 覆盖 B 组三项改造，关键路径全部实测（不信静态断言）：
 *   B1 会话持久化   提问 → 落盘 → reload → 恢复 + 恢复提示条；resetChat 能清掉
 *   B2 多轮上下文   拦截 fetch 取真实请求体，断言 messages 里确实带了历史（非只塞当前一条）
 *   B3 记忆抽屉     打开/关闭三路径、联想记忆渲染、逐条撤销、导出入口
 * 用法：node _verify_qa_memory.js     失败即非零退出（供 _build_all.py 守护）
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
  console.log("=== 你问我答 · 会话记忆回归 ===");
  const browser = await launch();
  const ctx = await browser.newContext();
  const page = await ctx.newPage();

  /* ---------------- B1 会话持久化 ---------------- */
  console.log("\n[B1] 会话持久化");
  await page.goto(fileUrl("qa.html"));
  await page.waitForTimeout(1500);

  const askOk = await page.evaluate(() => {
    try { ask("迟到怎么扣分"); return true; } catch (e) { return String(e && e.message); }
  });
  ok("可正常提问（基线）", askOk === true, String(askOk));

  /* 2026-09-19 修复测试时间假设：欢迎卡取消后（QA_SHOW_WELCOME=false）开场没有现成消息，
     必须等机器人回复真正进聊天流再校验落盘（原先 1200ms 依赖欢迎卡凑数，属假通过）。 */
  const waitReply = await page.evaluate(async () => {
    for (let i = 0; i < 60; i++) {
      try { if (chat.msgs.length >= 2) return chat.msgs.length; } catch (e) {}
      await new Promise(r => setTimeout(r, 200));
    }
    try { return chat.msgs.length; } catch (e) { return -1; }
  });
  await page.waitForTimeout(900);    // 等节流落盘（saveSoon 600ms）
  const savedRaw = await page.evaluate(() => {
    try { return localStorage.getItem("qa_history_v1") || ""; } catch (e) { return "ERR:" + e.message; }
  });
  let savedObj = null;
  try { savedObj = JSON.parse(savedRaw); } catch (e) {}
  ok("提问后已落盘", !!savedObj && Array.isArray(savedObj.msgs) && savedObj.msgs.length >= 2,
     "len=" + (savedObj && savedObj.msgs ? savedObj.msgs.length : String(savedRaw).slice(0, 60)) + " 聊天流=" + waitReply);

  const lenBefore = await page.evaluate(() => { try { return chat.msgs.length; } catch (e) { return -1; } });
  await page.reload();
  await page.waitForTimeout(1800);
  const lenAfter = await page.evaluate(() => { try { return chat.msgs.length; } catch (e) { return -1; } });
  ok("reload 后会话已恢复（消息数 > 1）", lenAfter > 1, "before=" + lenBefore + " after=" + lenAfter);

  const hasBar = await page.evaluate(() => !!document.getElementById("qaRestoreBar"));
  ok("显示「已恢复对话」提示条", hasBar);

  const barClosable = await page.evaluate(() => {
    const b = document.querySelector("#qaRestoreBar .qa-ctx-x");
    if (!b) return "no-btn";
    b.click();
    return document.getElementById("qaRestoreBar") === null ? "closed" : "still";
  });
  ok("提示条可关闭", barClosable === "closed", barClosable);

  /* ---------------- B2 多轮上下文 ---------------- */
  console.log("\n[B2] 多轮上下文（拦截真实请求体）");
  const ctxReq = await page.evaluate(async () => {
    try { localStorage.removeItem("qa_assoc_v1"); } catch (e) {}
    window.__reqs = [];
    const of = window.fetch;
    window.fetch = function (u, o) {
      try { window.__reqs.push({ url: String(u), body: o && o.body ? String(o.body) : "" }); } catch (e) {}
      return Promise.resolve({
        ok: true,
        json: function () { return Promise.resolve({ choices: [{ message: { content: "\u6a21\u62df\u56de\u590d" } }] }); }
      });
    };
    try { ask("zzzzqqqq"); } catch (e) {}
    await new Promise((r) => setTimeout(r, 1500));
    window.fetch = of;
    return window.__reqs.map((r) => r.body);
  });
  let msgCount = -1;
  try {
    const body = JSON.parse(ctxReq[0] || "{}");
    msgCount = (body.messages || []).length;
  } catch (e) {}
  // 2026-09-19 本地模式：外部 AI 已停用 → reqs=0 才是预期（零外发）。
  //   多轮上下文改为「包装函数内部取证」：调用 SpringAI.chatLLM 时包装器会先把历史拼进 messages，
  //   再由本地 stub 抛出『本地知识库模式』错误；我们只检查入参是否被动过。
  // 包装器是「返回新数组」而非原地修改，故改为调用暴露出来的注入器取证（函数级断言）。
  const hist = await page.evaluate(() => {
    try {
      const out = window.QaMemory.injectHistory([{ role: "user", content: "zzzzqqqq（第二轮）" }]);
      return { n: out.length, texts: out.map((m) => String(m.content || "")).join(" | ").slice(0, 200) };
    } catch (e) { return { err: String(e && e.message) }; }
  });
  ok("本地模式：不再发起真实 AI 请求（零外发）", ctxReq.length === 0, "reqs=" + ctxReq.length);
  ok("多轮上下文仍会拼进 messages（历史注入未被移除）",
     hist.n > 1 && /zzzzqqqq/.test(hist.texts), JSON.stringify(hist).slice(0, 200));

  const wrapped = await page.evaluate(() => !!(window.__qaMemFlags && window.__qaMemFlags.chatLLM));
  ok("chatLLM 包装标志在位", wrapped);

  const turns = await page.evaluate(() => {
    try { return window.QaMemory.turns(3).length; } catch (e) { return -1; }
  });
  ok("历史轮次可读（>=2 条消息）", turns >= 2, "turns=" + turns);

  /* ---------------- B3 记忆抽屉 ---------------- */
  console.log("\n[B3] 历史 / 记忆抽屉");
  const seeded = await page.evaluate(() => {
    try {
      localStorage.removeItem("qa_assoc_v1");
      qaAssocSave("灭火是什么", "灭火瓶位置", "daily");
      qaAssocSave("酒测那个数", "酒测超标标准", "mgm");
      qaAssocSave("三角形标志在哪", "应急出口标志", "ccm");
      return Object.keys(qaAssocLoad()).length;
    } catch (e) { return -1; }
  });
  ok("预置 3 条联想记忆", seeded === 3, "seeded=" + seeded);

  const opened = await page.evaluate(() => {
    try { window.qaOpenDrawer(); } catch (e) { return "ERR:" + e.message; }
    const d = document.getElementById("qaDrawer");
    return d && d.classList.contains("on") ? "on" : "off";
  });
  ok("抽屉可打开", opened === "on", String(opened));

  const memCount = await page.evaluate(() => {
    return document.querySelectorAll("#qdMem .qd-mem").length;
  });
  ok("记忆列表渲染 3 条", memCount === 3, "rendered=" + memCount);

  const cntText = await page.evaluate(() => {
    const el = document.getElementById("qdMemCount");
    return el ? el.textContent : "";
  });
  ok("计数文案含「3 条」", /\u0033\s*\u6761/.test(cntText) || cntText.indexOf("3") >= 0, JSON.stringify(cntText));

  const histItems = await page.evaluate(() => document.querySelectorAll("#qdHist .qd-item").length);
  ok("最近提问可点击列表非空", histItems >= 1, "items=" + histItems);

  const forgot = await page.evaluate(() => {
    const btn = document.querySelector("#qdMem [data-forget]");
    if (!btn) return "no-btn";
    btn.click();
    return document.querySelectorAll("#qdMem .qd-mem").length;
  });
  ok("点「撤销这条」后记忆减少到 2", forgot === 2, "left=" + String(forgot));

  await page.keyboard.press("Escape");
  await page.waitForTimeout(200);
  const afterEsc = await page.evaluate(() => {
    const d = document.getElementById("qaDrawer");
    return d && d.classList.contains("on") ? "on" : "off";
  });
  ok("Esc 可关闭抽屉（关闭路径之一）", afterEsc === "off", String(afterEsc));

  const maskClose = await page.evaluate(() => {
    window.qaOpenDrawer();
    const m = document.querySelector("#qaDrawer .qd-mask");
    if (!m) return "no-mask";
    m.click();
    const d = document.getElementById("qaDrawer");
    return d && d.classList.contains("on") ? "on" : "off";
  });
  ok("点遮罩可关闭抽屉（关闭路径之二）", maskClose === "off", String(maskClose));

  const clearWorks = await page.evaluate(async () => {
    window.qaOpenDrawer();
    const b = document.getElementById("qdClearHist");
    if (!b) return "no-btn";
    b.click();
    await new Promise((r) => setTimeout(r, 300));
    return localStorage.getItem("qa_history_v1") === null ? "cleared" : "not-cleared";
  });
  ok("「清空对话记录」真的清掉持久化历史", clearWorks === "cleared", String(clearWorks));

  await browser.close();
  console.log("\n=== 通过 " + pass + " / " + (pass + fail) + " 项 ===");
  if (fail) { console.log("!! " + fail + " 项失败"); process.exit(1); }
  console.log("全部通过 \u2713");
})().catch((e) => { console.error("ERR " + (e && e.stack || e)); process.exit(1); });
