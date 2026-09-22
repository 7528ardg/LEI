/* 库管理总台 · 真实浏览器端到端（2026-09-21）
 * -----------------------------------------------------------------------------
 * 覆盖用户在界面上真实走的路径：
 *   打开即是库管理 → 八源 chips → 分页列表 → 编辑保存 → 删除 → 往返自检
 *   → 导出完整数据包（真实下载到磁盘）→ 重新导入 → 还原一致性复核报告
 *   → 撤销改动回到基线
 * 用法：node _verify_kb_console_e2e.js     失败即非零退出（供 _build_all.py 守护）
 */
"use strict";
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright-core");

const ROOT = __dirname;
const fileUrl = (p) => "file:///" + path.resolve(ROOT, p).replace(/\\/g, "/");
const TMP_PACK = path.resolve(ROOT, "_kb_console_roundtrip_tmp.json");

let pass = 0, fail = 0;
const fails = [];
const ok = (name, cond, extra) => {
  if (cond) { pass++; console.log("  ✓ " + name); }
  else { fail++; fails.push(name + (extra ? " :: " + extra : "")); console.log("  ✗ " + name + (extra ? " :: " + extra : "")); }
};

async function launch() {
  const args = ["--allow-file-access-from-files", "--disable-web-security"];
  for (const ch of ["msedge", "chrome", null]) {
    try { return await chromium.launch(ch ? { channel: ch, headless: true, args } : { headless: true, args }); }
    catch (e) { /* 换下一个 */ }
  }
  throw new Error("无法启动浏览器（msedge / chrome / 内置均失败）");
}

async function modalText(page) {
  return await page.evaluate(() => {
    const t = document.getElementById("modalTitle");
    const b = document.getElementById("modalBody");
    return { title: t ? t.textContent : "", body: b ? b.innerHTML : "" };
  });
}
async function clickAct(page, label) {
  await page.click('#modalActs button:has-text("' + label + '")');
  await page.waitForTimeout(150);
}
function hasText(html, s) { return String(html).indexOf(s) >= 0; }

(async () => {
  const browser = await launch();
  const ctx = await browser.newContext({ acceptDownloads: true, viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", (e) => errs.push(String(e && e.message)));
  await page.goto(fileUrl("kb-admin.html"), { waitUntil: "load", timeout: 120000 });
  await page.waitForSelector("#dsChips .cs-chip", { timeout: 60000 });

  console.log("== 1. 首屏：库管理为默认页，八源齐备 ==");
  const activeTab = await page.evaluate(() => {
    const a = document.querySelector(".kb-tab.active");
    return a ? a.textContent : "";
  });
  ok("默认落在「库管理」标签", hasText(activeTab, "库管理"), activeTab);
  const chips = await page.evaluate(() => Array.from(document.querySelectorAll("#dsChips .cs-chip")).map(e => e.textContent.replace(/\s+/g, " ").trim()));
  ok("数据源 chips 共 8 个", chips.length === 8, String(chips.length));
  ok("含六库 + 话术库 + 产品库",
    ["日常库", "乘务员手册", "管理手册", "服务规范", "大撤专项", "CBT 题库", "销售话术库", "产品库"].every(n => chips.join("|").indexOf(n) >= 0),
    chips.join(" | "));
  const stat0 = await page.textContent("#csStat");
  ok("统计条显示总数且未改动", /全库共/.test(stat0) && hasText(stat0, "未改动"), stat0);
  const rows0 = await page.evaluate(() => document.querySelectorAll("#csTbl tr").length - 1);
  ok("首屏分页渲染 50 行", rows0 === 50, String(rows0));

  console.log("\n== 2. 切换数据源 + 搜索 ==");
  await page.click('#dsChips .cs-chip:has-text("CBT")');
  await page.waitForTimeout(300);
  const cbtPager = await page.textContent("#csPager");
  ok("CBT 题库分页显示 2654 条", /2654/.test(cbtPager), cbtPager);
  await page.click('#dsChips .cs-chip:has-text("销售话术库")');
  await page.waitForTimeout(300);
  const scrPager = await page.textContent("#csPager");
  ok("销售话术库分页显示 1045 条", /1045/.test(scrPager), scrPager);
  await page.fill("#csSearch", "起飞");
  await page.waitForTimeout(400);
  const afterSearch = await page.textContent("#csPager");
  ok("搜索过滤生效（条数变化）", !/1045/.test(afterSearch), afterSearch);
  await page.fill("#csSearch", "");
  await page.waitForTimeout(400);

  console.log("\n== 3. 编辑并保存 ==");
  await page.click('#dsChips .cs-chip:has-text("乘务员手册")');
  await page.waitForTimeout(300);
  await page.click('#csTbl tr:nth-child(2) button:has-text("编辑")');
  await page.waitForSelector("#modal.show .cs-form", { timeout: 10000 });
  const qid = await page.evaluate(() => {
    const flds = Array.from(document.querySelectorAll(".cs-form .fld"));
    const f = flds.find(d => (d.querySelector("label") || {}).textContent === "q");
    const el = f && f.querySelector("textarea,input,select");
    return el ? el.id : null;
  });
  ok("编辑表单按字段动态生成（含 q 字段）", !!qid, String(qid));
  await page.fill("#" + qid, "（端到端已编辑）这是人工改过的问题");
  await clickAct(page, "保存");
  await page.waitForTimeout(300);
  const chipCcm = await page.evaluate(() => {
    const c = Array.from(document.querySelectorAll("#dsChips .cs-chip")).find(e => e.textContent.indexOf("乘务员手册") >= 0);
    return c ? c.textContent.replace(/\s+/g, " ") : "";
  });
  ok("改动落到编辑层并标记（改 1）", hasText(chipCcm, "改 1"), chipCcm);
  const persisted = await page.evaluate(() => {
    const raw = localStorage.getItem("kb_console_edit_v1");
    if (!raw) return null;
    const o = JSON.parse(raw);
    return { magic: o.magic, mod: Object.keys((o.bySource.ccm || {}).mod || {}).length };
  });
  ok("编辑层已持久化到本机（magic 正确）", persisted && persisted.magic === "cabin-console-edit-v1" && persisted.mod === 1,
    JSON.stringify(persisted));

  console.log("\n== 4. 删除 ==");
  await page.click('#csTbl tr:nth-child(3) button:has-text("删除")');
  await page.waitForSelector("#modal.show", { timeout: 10000 });
  await clickAct(page, "确认删除");
  await page.waitForTimeout(300);
  const stat1 = await page.textContent("#csStat");
  ok("删除记录进编辑层（统计出现 删 1）", hasText(stat1, "删 1"), stat1);

  console.log("\n== 5. 往返自检（导出→校验→还原→逐条比对） ==");
  await page.click('button:has-text("往返自检")');
  await page.waitForSelector("#modal.show", { timeout: 60000 });
  const rt = await modalText(page);
  ok("往返自检报告通过", hasText(rt.title, "通过"), rt.title);
  ok("报告覆盖 8 个数据源且逐条一致", (rt.body.match(/逐条一致/g) || []).length >= 8,
    String((rt.body.match(/逐条一致/g) || []).length));
  await clickAct(page, "知道了");

  console.log("\n== 6. 导出完整数据包（真实下载） ==");
  let downloaded = false;
  try {
    const [dl] = await Promise.all([
      page.waitForEvent("download", { timeout: 60000 }),
      page.click("button:has-text(\"导出完整数据包\")")
    ]);
    await dl.saveAs(TMP_PACK);
    downloaded = fs.existsSync(TMP_PACK);
  } catch (e) {
    ok("导出下载", false, String(e && e.message));
  }
  if (downloaded) {
    ok("导出文件已落到磁盘", true);
    const pack = JSON.parse(fs.readFileSync(TMP_PACK, "utf8"));
    ok("下载包 magic 正确", pack.magic === "cabin-fullpack-v1", String(pack.magic));
    ok("下载包含 8 个数据源", Array.isArray(pack.sources) && pack.sources.length === 8, String(pack.sources && pack.sources.length));
    ok("下载包含全部条目（>4900）", pack.summary && pack.summary.items > 4900, String(pack.summary && pack.summary.items));
  }
  await page.waitForSelector('#modal.show button:has-text("知道了")', { timeout: 30000 });
  const ex = await modalText(page);
  ok("导出后即刻自检通过（弹窗报告）", hasText(ex.title, "导出完成"), ex.title);
  await clickAct(page, "知道了");

  console.log("\n== 7. 重新导入并验证完整还原 ==");
  await page.setInputFiles("#csFile", TMP_PACK);
  await page.waitForSelector("#modal.show", { timeout: 60000 });
  const pv = await modalText(page);
  ok("导入前识别校验通过", hasText(pv.title, "校验通过"), pv.title);
  ok("预览报告列出 8 个数据源", (pv.body.match(/<tr><td>/g) || []).length >= 8, String((pv.body.match(/<tr><td>/g) || []).length));
  await clickAct(page, "整包还原");
  await page.waitForSelector("#modal.show", { timeout: 60000 });
  const rp = await modalText(page);
  ok("导入完成且还原校验全部通过", hasText(rp.title, "还原校验全部通过"), rp.title);
  ok("逐条复核均为「完全一致」", (rp.body.match(/完全一致/g) || []).length === 8, String((rp.body.match(/完全一致/g) || []).length));
  ok("无任何「不符」记录", !hasText(rp.body, "不符"), rp.body.slice(0, 200));
  await clickAct(page, "知道了");

  const restored = await page.evaluate(() => {
    const raw = localStorage.getItem("kb_console_edit_v1");
    const o = JSON.parse(raw);
    const c = o.bySource.ccm || {};
    return { mod: Object.keys(c.mod || {}).length, del: (c.del || []).length, add: (c.add || []).length };
  });
  ok("还原后编辑层精确保留 改1/删1", restored.mod === 1 && restored.del === 1 && restored.add === 0, JSON.stringify(restored));
  const firstQ = await page.evaluate(() => {
    const t = document.querySelector("#csTbl tr:nth-child(2) .cs-main .t1");
    return t ? t.textContent : "";
  });
  ok("列表显示的是人工改过的内容", hasText(firstQ, "端到端已编辑"), firstQ);

  console.log("\n== 8. 往返自检（导入后再跑一次） ==");
  await page.click('button:has-text("往返自检")');
  await page.waitForSelector("#modal.show", { timeout: 60000 });
  const rt2 = await modalText(page);
  ok("导入后再次往返自检仍通过", hasText(rt2.title, "通过"), rt2.title);
  await clickAct(page, "知道了");

  console.log("\n== 9. 撤销改动回到基线 ==");
  await page.click('button:has-text("撤销本源改动")');
  await page.waitForSelector("#modal.show", { timeout: 10000 });
  await clickAct(page, "确认撤销");
  await page.waitForTimeout(300);
  const stat2 = await page.textContent("#csStat");
  ok("本源改动已撤销（不再显示 改/删）", !hasText(stat2, "改 ") && !hasText(stat2, "删 "), stat2);

  console.log("\n== 10. 无脚本错误 ==");
  ok("页面运行期无 JS 异常", errs.length === 0, errs.slice(0, 3).join(" | "));

  await browser.close();
  console.log("\n===== 汇总 =====");
  console.log("通过 " + pass + " / " + (pass + fail));
  if (fail) {
    console.log("失败项：");
    fails.forEach(f => console.log("  - " + f));
    process.exit(1);
  }
  console.log("库管理总台端到端全绿：查看/编辑/删除/导出/导入/还原校验/撤销 全部可用。");
})().catch(e => {
  console.error("运行异常：", e);
  process.exit(1);
});
