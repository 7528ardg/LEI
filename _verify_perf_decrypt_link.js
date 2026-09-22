/* 绩效数据跨板块链路回归：performance.html 真实加密落库 → qa 读取还原（常驻）
 *
 * 为什么需要这个脚本：
 *   原有 _verify_perf_linkage.js / _verify_perf_real.js 都在测试侧用内存 mock 往 IndexedDB
 *   灌**明文**结构，绕过了 performance.html 的 Storage.saveMonth()（AES-GCM 加密）真实路径，
 *   属自证式测试。结果是「映射层正确」但「真实存储形态不可消费」的断裂长期不暴露
 *   （2026-09-21 审查发现：密文被当"无数据"静默丢弃）。
 *   本脚本改为**复刻 performance 的加密算法与密钥存储**后落库，再让 qa 侧真实读取。
 *
 * 断言：
 *   [静态] 两侧密钥常量一致（qa QA_PERF_ENC_KEY_STORAGE ≡ performance ENC_KEY_STORAGE）
 *   [动态] 密文落库 → qa 读到 1 条且字段精确（含销售额、完成率、来源标注）
 *   [兼容] 明文对象落库 → qa 同样读到（旧数据不回归）
 *   [降级] 密钥缺失 + 密文 → 返回 0 条且不抛异常（不编造）
 *   [自检] 复刻的加密算法与 performance 源码逐项一致
 *
 * 用法：node _verify_perf_decrypt_link.js     失败即非零退出
 */
'use strict';
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const ROOT = __dirname;
const fileUrl = (p) => 'file:///' + path.resolve(ROOT, p).replace(/\\/g, '/');

let pass = 0, fail = 0;
const ok = (n, c, extra) => {
  if (c) { pass++; console.log('  \u2713 ' + n); }
  else { fail++; console.log('  \u2717 ' + n + (extra ? '  :: ' + extra : '')); }
};

const MONTH = (() => { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0'); })();

async function launch() {
  for (const ch of ['msedge', 'chrome', null]) {
    try { return await chromium.launch(ch ? { channel: ch, headless: true } : { headless: true }); } catch (e) {}
  }
  throw new Error('无法启动浏览器');
}

/* 在页面上下文里复刻 performance.html 的落库方式 */
const PAGE_HELPERS = `
window.__idbPut = function(key, val){
  return new Promise(function(res, rej){
    var r = indexedDB.open('keyval-store');
    r.onupgradeneeded = function(){ try { r.result.createObjectStore('keyval'); } catch(e){} };
    r.onerror = function(){ rej(r.error); };
    r.onsuccess = function(){
      var db = r.result;
      try{
        var tx = db.transaction('keyval', 'readwrite');
        tx.objectStore('keyval').put(val, key);
        tx.oncomplete = function(){ try{ db.close(); }catch(e){} res(true); };
        tx.onerror = function(){ try{ db.close(); }catch(e){} rej(tx.error); };
      }catch(e){ try{ db.close(); }catch(e2){} rej(e); }
    };
  });
};
window.__idbClear = function(){
  return new Promise(function(res){
    try{
      var r = indexedDB.open('keyval-store');
      r.onupgradeneeded = function(){ try { r.result.createObjectStore('keyval'); } catch(e){} };
      r.onerror = function(){ res(false); };
      r.onsuccess = function(){
        var db = r.result;
        try{
          var tx = db.transaction('keyval', 'readwrite');
          tx.objectStore('keyval').clear();
          tx.oncomplete = function(){ try{ db.close(); }catch(e){} res(true); };
          tx.onerror = function(){ try{ db.close(); }catch(e){} res(false); };
        }catch(e){ try{ db.close(); }catch(e2){} res(false); }
      };
    }catch(e){ res(false); }
  });
};
window.__ENC_KEY_STORAGE = 'gz_perf_enc_key_v2';
window.__encryptLikePerf = async function(plainData, opts){
  opts = opts || {};
  if (opts.dropKey) { try{ localStorage.removeItem(window.__ENC_KEY_STORAGE); }catch(e){} }
  if (!crypto.subtle || typeof crypto.subtle.importKey !== 'function') return plainData;
  var stored = localStorage.getItem(window.__ENC_KEY_STORAGE);
  var rawKey = null;
  if (stored) { try{ rawKey = Uint8Array.from(atob(stored), function(c){ return c.charCodeAt(0); }); }catch(e){ rawKey = null; } }
  if (!rawKey || rawKey.length !== 32) {
    rawKey = crypto.getRandomValues(new Uint8Array(32));
    localStorage.setItem(window.__ENC_KEY_STORAGE, btoa(String.fromCharCode.apply(null, rawKey)));
  }
  var key = await crypto.subtle.importKey('raw', rawKey, { name:'AES-GCM' }, false, ['encrypt']);
  var iv = crypto.getRandomValues(new Uint8Array(12));
  var ct = await crypto.subtle.encrypt({ name:'AES-GCM', iv: iv }, key, new TextEncoder().encode(JSON.stringify(plainData)));
  var combined = new Uint8Array(iv.length + new Uint8Array(ct).length);
  combined.set(iv);
  combined.set(new Uint8Array(ct), iv.length);
  return 'ENC:' + btoa(String.fromCharCode.apply(null, combined));
};
`;

const DATA = {
  summary: [{ name: '雷炜豪', team: '广州张露班组', position: '乘务员', safeScore: 95, operationScore: 93, businessScore: 92, comprehensiveScore: 94, workScore: 90, salesScore: 80, flightHours: 88, performance: 91.5 }],
  sales: { detailRows: [{ name: '雷炜豪', personalSale: 8383.5, personalTarget: 9000, completionRate: 93 }] }
};

(async () => {
  console.log('=== 绩效跨板块解码链路回归（真实加密路径）===');

  /* ---------- 静态契约 ---------- */
  console.log('\n[静态] 两侧密钥常量一致性');
  const qaSrc = fs.readFileSync(path.join(ROOT, 'qa.html'), 'utf8');
  const perfSrc = fs.readFileSync(path.join(ROOT, 'performance.html'), 'utf8');
  const qaKey = (qaSrc.match(/QA_PERF_ENC_KEY_STORAGE\s*=\s*'([^']+)'/) || [])[1];
  const perfKey = (perfSrc.match(/ENC_KEY_STORAGE:\s*'([^']+)'/) || [])[1];
  ok('qa 侧声明了密钥存储常量', !!qaKey, String(qaKey));
  ok('performance 侧声明了密钥存储常量', !!perfKey, String(perfKey));
  ok('两侧密钥存储键完全一致', !!qaKey && qaKey === perfKey, qaKey + ' vs ' + perfKey);
  ok('qa 侧识别 ENC: 密文前缀', /QA_PERF_ENC_PREFIX\s*=\s*'ENC:'/.test(qaSrc));
  ok('qa 侧已接入解密（qaPerfDecrypt 定义 + 调用）',
    /async function qaPerfDecrypt/.test(qaSrc) && /await qaPerfDecrypt\(md\)/.test(qaSrc));
  ok('performance 侧仍产出 ENC: 前缀', /return 'ENC:' \+/.test(perfSrc));
  ok('performance 侧 iv 长度与 qa 解析一致（12 字节）',
    /new Uint8Array\(12\)/.test(perfSrc) && /raw\.slice\(0,\s*12\)/.test(qaSrc));
  ok('performance 侧密钥长度校验与 qa 一致（32 字节）',
    /rawKey\.length !== 32/.test(perfSrc) && /raw\.length !== 32/.test(qaSrc));

  const browser = await launch();
  const ctx = await browser.newContext();

  /* ---------- 场景 1：密文落库 → qa 读回 ---------- */
  console.log('\n[动态] 密文（performance 真实形态）→ qa 读取');
  const writer = await ctx.newPage();
  await writer.goto(fileUrl('performance.html'));
  await writer.waitForTimeout(1500);
  await writer.evaluate(PAGE_HELPERS);
  const wrote = await writer.evaluate(async ([month, data]) => {
    await window.__idbClear();
    const enc = await window.__encryptLikePerf(data);
    await window.__idbPut('crew_gz_' + month, enc);
    await window.__idbPut('crew_gz_month_index', [month]);
    return { startsWithENC: String(enc).startsWith('ENC:'), len: String(enc).length };
  }, [MONTH, DATA]);
  ok('落库值确为 ENC: 密文（构造有效）', wrote.startsWithENC, JSON.stringify(wrote));

  const reader = await ctx.newPage();
  const errs = [];
  reader.on('pageerror', e => errs.push(String(e).slice(0, 160)));
  await reader.goto(fileUrl('qa.html'));
  await reader.waitForTimeout(2500);
  const read1 = await reader.evaluate(async (month) => {
    if (typeof window.qaLoadRealPerf !== 'function') return { err: 'qaLoadRealPerf 不可访问' };
    const rows = await window.qaLoadRealPerf();
    const r = rows.find(x => x && x.姓名 === '雷炜豪') || rows[0] || null;
    return { n: rows.length, row: r };
  }, MONTH);
  ok('qa 读到绩效行（不再是 0 条）', (read1.n || 0) > 0, JSON.stringify(read1).slice(0, 200));
  ok('姓名正确', read1.row && read1.row.姓名 === '雷炜豪', read1.row && read1.row.姓名);
  ok('绩效总分精确（91.5）', read1.row && read1.row.绩效总分 === 91.5, read1.row && String(read1.row.绩效总分));
  ok('个人销售额精确（8383.5）', read1.row && read1.row.个人销售额 === 8383.5, read1.row && String(read1.row.个人销售额));
  ok('完成率精确（93）', read1.row && read1.row.完成率 === 93, read1.row && String(read1.row.完成率));
  ok('月份标注正确', read1.row && read1.row.月份 === MONTH, read1.row && read1.row.月份);
  ok('来源标注为绩效后台', read1.row && read1.row._来源 === '绩效后台', read1.row && read1.row._来源);
  ok('解密读取过程无 JS 异常', errs.length === 0, errs[0]);

  /* ---------- 场景 2：明文落库 → qa 兼容读取 ---------- */
  console.log('\n[兼容] 明文对象（历史数据）→ qa 读取');
  await writer.evaluate(async ([month, data]) => {
    await window.__idbClear();
    await window.__idbPut('crew_gz_' + month, data);
    await window.__idbPut('crew_gz_month_index', [month]);
  }, [MONTH, DATA]);
  const read2 = await reader.evaluate(async () => {
    const rows = await window.qaLoadRealPerf();
    return { n: rows.length, name: rows[0] && rows[0].姓名, score: rows[0] && rows[0].绩效总分 };
  });
  ok('明文数据仍可读（无前缀直接返回）', read2.n > 0 && read2.name === '雷炜豪', JSON.stringify(read2));

  /* ---------- 场景 3：密钥缺失 → 降级不编造 ---------- */
  console.log('\n[降级] 密钥缺失 + 密文 → 空结果且不抛错');
  await writer.evaluate(async ([month, data]) => {
    await window.__idbClear();
    const enc = await window.__encryptLikePerf(data, { dropKey: true });
    await window.__idbPut('crew_gz_' + month, enc);
    await window.__idbPut('crew_gz_month_index', [month]);
  }, [MONTH, DATA]);
  const read3 = await reader.evaluate(async () => {
    try {
      const rows = await window.qaLoadRealPerf();
      return { n: rows.length, threw: false };
    } catch (e) { return { n: -1, threw: true, msg: String(e).slice(0, 120) }; }
  });
  ok('密钥不可用时返回 0 条（不编造）', read3.n === 0, JSON.stringify(read3));
  ok('密钥不可用时未抛异常', read3.threw === false, JSON.stringify(read3));

  /* ---------- 清理 ---------- */
  await writer.evaluate(async () => {
    try { await window.__idbClear(); } catch (e) {}
    try { localStorage.removeItem(window.__ENC_KEY_STORAGE); } catch (e) {}
  });

  console.log('\n=== 通过 ' + pass + ' / 失败 ' + fail + ' ===');
  await browser.close();
  process.exit(fail ? 1 : 0);
})().catch(e => { console.log('FATAL ' + e.message); process.exit(2); });
