/* 你问我答 · AI 赋魂回归（批 α · 常驻）
 * 用途：验证 __QA_AI_BRAIN_20260921__ 块的四件事，并守护接缝不被后续补丁踩坏——
 *   A4 指代消解：承接式追问（「还有呢」「多久内」）还原成完整问句；完整新问题与 /命令 不误判；
 *   A3 问法改写：AI 可用时改写→再检索→强命中即返回；AI 不可用 / 防抖窗口内返回 null（原链路不受影响）；
 *   A6 强制溯源：库内能找到依据 → ok 栏零标记；查不到依据 → warn 栏 + 波浪线标记；无上下文 → miss 栏；
 *   A5 未明示需求：从库内上下文给出可点推荐芯片，且不与回答内容重复。
 * 另外守护三处 in-place 接缝：原 process / kbStrong / kbReply 定义未被改写，
 * 情绪共情那条 addMsg 未被误伤，且源码未引入内置密钥字面量。
 *
 * 用法：node _verify_qa_ai_brain.js      失败即非零退出（供 _build_all.py 守护）
 * 说明：脚本从 qa.html 实时抽取 mdToHtml + AI 赋魂块运行，其余依赖用桩替换。
 */
"use strict";
const fs = require("fs");

const src = fs.readFileSync("qa.html", "utf8");

let pass = 0, fail = 0;
const ok = (name, cond, extra) => {
  if (cond) { pass++; console.log("  \u2713 " + name); }
  else { fail++; console.log("  \u2717 " + name + (extra ? "  :: " + extra : "")); }
};

// ---------- 1) 抽取：mdToHtml（按大括号配对） ----------
function extractFn(name) {
  const i = src.indexOf("function " + name + "(");
  if (i < 0) throw new Error("缺少 function " + name);
  let depth = 0, started = false;
  for (let k = i; k < src.length; k++) {
    const ch = src[k];
    if (ch === "{") { depth++; started = true; }
    else if (ch === "}") { depth--; if (started && depth === 0) return src.slice(i, k + 1); }
  }
  throw new Error(name + " 大括号未闭合");
}
const mdJs = extractFn("mdToHtml");

// ---------- 2) 抽取：AI 赋魂块 ----------
const B = "/*__QA_AI_BRAIN_20260921_BEGIN__*/";
const E = "/*__QA_AI_BRAIN_20260921_END__*/";
const iB = src.indexOf(B), iE = src.indexOf(E);
if (iB < 0 || iE < 0 || iE < iB) throw new Error("AI 赋魂块缺失（qa.html）");
const brainJs = src.slice(iB + B.length, iE);

// ---------- 3) 构造沙箱 ----------
function build(aiEnabled) {
  const domCss = { id: "", textContent: "" };
  const documentStub = {
    _css: domCss,
    head: { appendChild: (n) => { domCss.id = n.id; domCss.textContent = n.textContent; } },
    documentElement: { appendChild: () => {} },
    getElementById: () => null,
    createElement: () => ({ id: "", textContent: "" }),
    addEventListener: () => {},
    readyState: "complete",
  };
  const store = new Map();
  const localStorageStub = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
  };
  const msgCalls = [];
  const chatCalls = [];
  const windowStub = {};
  const SpringAIStub = {
    isEnabled: () => aiEnabled,
    _reply: "机上无冷藏设施时餐食可保存 4 小时\n餐食保存时限",
    chatLLM: async (messages, opts) => { chatCalls.push({ messages, opts }); return SpringAIStub._reply; },
  };
  const kbSearchStub = (q, n, pool) => {
    if (/餐食保存时限|机上无冷藏设施时餐食/.test(q)) {
      return [{ k: { q: "机上餐食保存多久？", a: "无冷藏设施时餐食可保存 4 小时（6.7.9.1）。", src: "手册 6.7.9.1", icon: "🍱" }, s: 12 }];
    }
    return [{ k: { q: "泛泛条目", a: "无所谓", src: "x" }, s: 1 }];
  };
  const kbStrongStub = (hits) => !!(hits && hits.length && hits[0].s >= 8);
  const toastCalls = [];
  const factory = new Function(
    "window", "localStorage", "document", "kbSearch", "kbStrong", "currentKbPool", "currentPoolLabel",
    "SpringAI", "QAAT", "ask", "typing", "clearTyping", "addMsg", "esc",
    mdJs + "\n" + brainJs + "\n return { QABRAIN: window.QABRAIN, css: document.__cssOut };"
  );
  const out = factory(
    windowStub, localStorageStub, documentStub, kbSearchStub, kbStrongStub,
    () => [{ k: { q: "机上餐食保存多久？", a: "无冷藏设施时餐食可保存 4 小时（6.7.9.1）。", src: "手册 6.7.9.1" }, s: 12 }],
    () => "乘务员手册", SpringAIStub,
    { toast: (t) => toastCalls.push(t) }, () => {}, async () => {}, () => {},
    (role, html) => msgCalls.push({ role, html }),
    (s) => String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  );
  return { Q: out.QABRAIN, documentStub, msgCalls, chatCalls, toastCalls, store };
}

// ================= A4 · 指代消解 =================
console.log("\n[A4] 指代消解");
{
  const { Q, toastCalls } = build(false);
  const Q1 = "机上有旅客突发癫痫怎么处置";
  ok("长问题原样返回且不弹承接提示", Q.resolveFollowUp(Q1) === Q1 && toastCalls.length === 0);
  const Q2 = Q.resolveFollowUp("还有呢");
  ok("「还有呢」承接上文", Q2.indexOf("癫痫") >= 0 && Q2.indexOf("还有呢") >= 0, Q2);
  ok("承接时给出可见提示", toastCalls.length === 1, JSON.stringify(toastCalls));
  const Q3 = Q.resolveFollowUp("多久内");
  ok("裸疑问词「多久内」承接（持续挂在同一主题上）", Q3.indexOf("癫痫") >= 0 && Q3.indexOf("多久内") >= 0, Q3);
  const NEW = "这是什么设备";
  ok("「这是什么设备」不误判为承接", Q.resolveFollowUp(NEW) === NEW, Q.resolveFollowUp(NEW));
  const CMD = "/风格 正式";
  ok("/ 命令不参与承接", Q.resolveFollowUp(CMD) === CMD);
  const LONG2 = "客舱服务规范里关于女乘丝袜配色的要求是什么";
  ok("新主题长问题重置上下文", Q.resolveFollowUp(LONG2) === LONG2);
  ok("重置后「为什么」可承接新主题", Q.resolveFollowUp("为什么").indexOf("丝袜") >= 0);
}

// ================= A6 · 强制溯源 =================
console.log("\n[A6] 强制溯源");
const CTX = [{ k: { q: "机上餐食保存多久？", a: "无冷藏设施时餐食可保存 4 小时，依据手册 6.7.9.1。", src: "手册 6.7.9.1" }, s: 12 }];
{
  const { Q } = build(false);
  const good = Q.auditAnswer("按手册 6.7.9.1，机上无冷藏设施时餐食可保存 4 小时。", CTX);
  ok("有依据 → ok 栏", good.indexOf("qa-gr-ok") >= 0, good.slice(0, 120));
  ok("有依据 → 零波浪线标记", good.indexOf("qa-gr-unv") < 0);
  ok("标注了参考条目数", /参考了库内 1 条资料/.test(good), good.slice(0, 160));

  const bad = Q.auditAnswer("按手册 8.8.8，餐食可保存 99 小时。", CTX);
  ok("无依据 → warn 栏", bad.indexOf("qa-gr-warn") >= 0, bad.slice(0, 120));
  ok("无依据 → 波浪线标记（章节号 + 数值）", (bad.match(/qa-gr-unv/g) || []).length === 2, String((bad.match(/qa-gr-unv/g) || []).length));
  ok("warn 文案给出处数", /2 处数值 \/ 章节号未能/.test(bad), bad.slice(0, 200));

  const none = Q.auditAnswer("这个问题库里没有，我凭通用知识说说。", []);
  ok("零上下文 → miss 栏", none.indexOf("qa-gr-miss") >= 0, none.slice(0, 120));
  ok("miss 文案点明无库内依据", /没有库内条目作为依据/.test(none));

  // HTML 属性不应被改写
  const withAttr = Q.auditAnswer('<a href="https://x.cn/4.htm">看这里 4 小时</a> 与 99 小时', CTX);
  ok("不动 HTML 属性（href 未被标记）", withAttr.indexOf("qa-gr-unv\">https") < 0 && withAttr.indexOf("/4.htm") >= 0, withAttr.slice(0, 200));
}

// ================= A5 · 未明示需求 =================
console.log("\n[A5] 未明示需求（库内推荐芯片）");
{
  const { Q } = build(false);
  const ctx2 = CTX.concat([{ k: { q: "冷链食品温度测试要求？", a: "每隔 4 小时测温。", src: "手册 5.4" }, s: 6 }]);
  const h = Q.auditAnswer("机上无冷藏设施时餐食可保存 4 小时。", ctx2);
  ok("出现推荐区", h.indexOf("qa-gr-chips") >= 0);
  ok("芯片使用既有 .w-chip 样式", h.indexOf('class="w-chip"') >= 0);
  ok("芯片取自库内条目", h.indexOf("冷链食品温度测试要求") >= 0);
  ok("回答里已提过的条目不重复推荐", h.indexOf("机上餐食保存多久") < 0, "应为不出现");
  const h2 = Q.auditAnswer("机上无冷藏设施时餐食可保存 4 小时。", CTX);
  ok("无可推荐条目不渲染空推荐区", h2.indexOf("qa-gr-chips") < 0);
}

// ================= A3 · 问法改写 =================
console.log("\n[A3] 问法改写（弱命中时用 AI 改写再检索）");
(async () => {
  {
    const { Q, chatCalls } = build(false);
    const r = await Q.rewriteAndSearch("饭能放多久");
    ok("AI 未启用 → 返回 null（原链路不受影响）", r === null);
    ok("AI 未启用 → 不发起调用", chatCalls.length === 0);
  }
  {
    const { Q, chatCalls } = build(true);
    const r = await Q.rewriteAndSearch("饭能放多久");
    ok("AI 启用 → 发起改写调用", chatCalls.length === 1);
    const c0 = chatCalls[0] || {};
    ok("改写调用带 noHistory / noCrossData（不污染历史）", !!(c0.opts && c0.opts.noHistory && c0.opts.noCrossData));
    ok("改写后命中即返回 hits", !!(r && r.hits && r.hits.length && r.hits[0].s >= 8), JSON.stringify(r && r.q));
    ok("返回命中的检索式", !!(r && r.q && r.q.indexOf("餐食") >= 0), r && r.q);
    const again = await Q.rewriteAndSearch("饭能放多久");
    ok("防抖窗口内第二次返回 null", again === null);
  }

  // ================= 接缝守护 =================
  console.log("\n[接缝] in-place 改动未伤及原实现");
  ok("原 process 定义在位", src.indexOf("async function process(text){") >= 0);
  ok("原 kbStrong 定义在位", src.indexOf("function kbStrong(hits){") >= 0);
  ok("原 kbReply 定义在位", src.indexOf("function kbReply(hits, rawText){") >= 0);
  ok("原 mdToHtml 定义在位", src.indexOf("function mdToHtml(") >= 0);
  ok("AI 兜底已接溯源", src.indexOf("QABRAIN.auditAnswer(resp, kbCtx)") >= 0);
  ok("情绪共情那条 addMsg 未被误伤", src.indexOf("addMsg('bot', mdToHtml(resp), { answer:true, q:text });") >= 0);
  ok("A3 接在候选追问之前", src.indexOf("QABRAIN.rewriteAndSearch(text)") < src.indexOf("【候选追问（2026-09-15）】"));
  ok("A4 接在待补要素承接之前", src.indexOf("QABRAIN.resolveFollowUp(text)") < src.indexOf("【增强】待补要素承接"));
  ok("块恰好 1 份", src.split(B).length === 2 && src.split(E).length === 2);
  ok("源码无内置密钥字面量", src.indexOf("4986b927") < 0 && src.indexOf("BUILTIN_AI_KEY") < 0);
  ok("仅预留注入位", src.indexOf("__QA_BUILTIN_AI__") >= 0);
  ok("script 标签平衡", src.split("<script").length === src.split("</script>").length);

  // ================= UI 规范（review 后加固） =================
  console.log("\n[UI 规范] 触屏可达性与长文本处理");
  {
    const { Q } = build(false);
    const bad = Q.auditAnswer("按手册 8.8.8，餐食可保存 99 小时。", CTX);
    ok("不再用 title 承载说明（触屏看不到）", bad.indexOf('title="') < 0);
    ok("未核实项直接写进文案（可读、可复制）", bad.indexOf("8.8.8") >= 0 && bad.indexOf("99 小时") >= 0);
    ok("波浪线标记带 translate=no（防自动翻译改写章节号）", bad.indexOf('translate="no"') >= 0);
    ok("状态栏 role=status", (bad.match(/role="status"/g) || []).length === 1);
    ok("状态图标 aria-hidden", bad.indexOf('class="qa-gr-ico" aria-hidden="true"') >= 0);
    ok("正文收进单一文本容器（防 flex 多栏切分）", (bad.match(/class="qa-gr-c"/g) || []).length === 1);
    const good = Q.auditAnswer("按手册 6.7.9.1，机上无冷藏设施时餐食可保存 4 小时。", CTX);
    ok("ok 栏同样带 role=status", good.indexOf('role="status"') >= 0);
    const many = Q.auditAnswer("依次是 1.1、2.2、3.3、4.4、5.5、6.6、7.7、8.8 共 8 处", CTX);
    ok("未核实项超过 6 处时以「等」收尾（不撑破气泡）", / 等，已用波浪线标出/.test(many), many.slice(0, 300));
    const chips = Q.auditAnswer("机上无冷藏设施时餐食可保存 4 小时。", CTX.concat([{ k: { q: "冷链食品温度测试要求？", a: "每隔 4 小时测温。", src: "手册 5.4" }, s: 6 }]));
    ok("推荐区标题图标 aria-hidden", chips.indexOf('aria-hidden="true">🔗') >= 0);
  }
  {
    const css = fs.readFileSync("qa.html", "utf8");
    ok("长问法芯片允许换行（overflow-wrap:anywhere）", css.indexOf(".qa-gr-chips .w-chip{max-width:100%;overflow-wrap:anywhere") >= 0);
    ok("状态栏不用 flex（否则正文被切成多栏）", css.indexOf(".qa-gr-bar{display:block;") >= 0 && css.indexOf(".qa-gr-bar{display:flex") < 0);
    ok("答案卡工具键粗指针补齐 44px", /@media \(pointer:coarse\)\{\.qa-at-b\{min-height:44px/.test(css));
    ok("波浪线颜色走 CSS 变量而非裸硬编码", css.indexOf("text-decoration-color:var(--gold,#D98324)") >= 0);
    ok("浅/深双主题均覆盖（5 条 dark 变体）", (css.match(/html\[data-theme="dark"\] \.qa-gr-/g) || []).length === 5);
  }

  console.log("\n=== AI 赋魂回归：通过 " + pass + " / 失败 " + fail + " ===");
  process.exit(fail ? 1 : 0);
})();
