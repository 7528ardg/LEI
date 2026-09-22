/* _ai_restore_verify_20260919.js · AI 接口恢复 + 新手教程对话气泡 验证
 * 2026-09-19 深夜更新：
 *   - 教程呈现方式改为「人物对话气泡」（__QA_AITUT_BUBBLE_v1__），不再自动弹 AI 设置弹窗；
 *     断言随之翻转：进入 qa 后应出现教程气泡，且 sa-modal 不自动弹出。
 *   - 自启动本地静态服务（原依赖外部 8893 端口）。
 * 使用：node _ai_restore_verify_20260919.js
 */
'use strict';
const { chromium } = require('playwright-core');
const fs = require('fs'); const path = require('path'); const http = require('http');
const OUT = path.join(__dirname, '_qa_trio_shots');
fs.mkdirSync(OUT, { recursive: true });
/* 说明：本脚本只用 session 形状来模拟「已登录管理员」，不对口令值做任何断言；
 * 因此这里使用占位值，不写入真实口令（凭据口径见 2026-09-22 M1/M2 修复）。*/
const SESSION = JSON.stringify({ '工号': '028981', '姓名': '管理员', '手机号': '', '密码': 'PLACEHOLDER_PWD' });
const R = []; function log(name, ok, detail){ R.push({ name, ok, detail }); console.log((ok ? '[PASS]' : '[FAIL]'), name, '—', detail || ''); }

const MIME = { '.html':'text/html; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.css':'text/css; charset=utf-8', '.png':'image/png', '.jpg':'image/jpeg', '.json':'application/json', '.glb':'model/gltf-binary', '.mp3':'audio/mpeg' };
function startServer(dir, cb){
  const srv = http.createServer((req, res) => {
    let p = decodeURIComponent(req.url.split('?')[0]); if (p === '/') p = '/index.html';
    const f = path.join(dir, p);
    if (!f.startsWith(dir) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); res.end('nf'); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(f).toLowerCase()] || 'application/octet-stream' });
    fs.createReadStream(f).pipe(res);
  });
  srv.listen(0, '127.0.0.1', () => cb('http://127.0.0.1:' + srv.address().port + '/index.html', srv));
}

(async () => {
  await new Promise((resolve) => startServer(__dirname, async (BASE, srv) => {
  const browser = await chromium.launch({ channel: 'msedge' });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 840 } });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(String(e).slice(0, 160)));
  await page.addInitScript((s) => { try { localStorage.setItem('cabin_session_v1', s); localStorage.setItem('qa_quick_hide_v1', '1'); sessionStorage.removeItem('qa_aitut_shown_v1'); } catch (e) {} }, SESSION);
  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForFunction(() => typeof window.switchModule === 'function', null, { timeout: 120000 });
  await page.waitForTimeout(3000);
  await page.evaluate(() => { const t = document.querySelector('.tour-overlay'); if (t) t.classList.remove('show'); });
  await page.waitForTimeout(4200); // 等教程气泡流（1.8s 起 + 5 条 × 0.9s）

  /* ① 顶栏 ⚙️ AI设置 入口 + AI 状态 */
  const hdr = await page.evaluate(() => {
    const d = document.getElementById('frame-qa').contentDocument;
    const b = Array.from(d.querySelectorAll('.t-ai .icon-btn, .icon-btn')).find(x => /AI设置/.test(x.textContent));
    const st = d.getElementById('aiStatus');
    return { btn: b ? b.textContent.trim() : '', status: st ? st.textContent : '' };
  });
  log('①顶栏AI设置入口', hdr.btn.indexOf('AI设置') >= 0, JSON.stringify(hdr));

  /* ② 教程以对话气泡呈现（不再自动弹设置弹窗） */
  const tut = await page.evaluate(() => {
    const d = document.getElementById('frame-qa').contentDocument;
    const w = document.getElementById('frame-qa').contentWindow;
    const msgs = d.querySelectorAll('#chatWrap .msg.bot');
    const text = d.getElementById('chatWrap') ? d.getElementById('chatWrap').innerText : '';
    return {
      botMsgs: msgs.length,
      hasTutBtn: !!d.querySelector('#chatWrap .qa-tut-btn'),
      hasVoiceTip: text.indexOf('语音输入') >= 0,
      hasTrTip: text.indexOf('翻译模式') >= 0,
      noAutoModal: !d.getElementById('sa-modal'),
      flag: !!(w && w.__QA_AITUT_BUBBLE__)
    };
  });
  log('②教程为对话气泡（含语音/翻译说明，无自动弹窗）',
      tut.botMsgs >= 4 && tut.hasTutBtn && tut.hasVoiceTip && tut.hasTrTip && tut.noAutoModal && tut.flag, JSON.stringify(tut));
  await page.screenshot({ path: path.join(OUT, 'ai-01-tut-bubbles.png') });

  /* ③ 打开 AI 设置（点气泡内按钮路径）：服务商与 Key 输入在位 */
  await page.evaluate(() => {
    const w = document.getElementById('frame-qa').contentWindow;
    const d = document.getElementById('frame-qa').contentDocument;
    const btn = d.querySelector('#chatWrap .qa-tut-btn');
    if (btn) btn.click(); else if (w.qaTutOpenAI) w.qaTutOpenAI();
  });
  await page.waitForTimeout(600);
  const cfg = await page.evaluate(() => {
    const d = document.getElementById('frame-qa').contentDocument;
    const sel = d.querySelector('#sa-modal select');
    const keyInput = d.querySelector('#sa-modal input[type="password"], #sa-modal input[placeholder*="Key"], #sa-modal input[placeholder*="key"]');
    return {
      modalOpen: !!d.getElementById('sa-modal'),
      providers: sel ? Array.from(sel.options).map(o => o.textContent.trim()) : [],
      hasKeyInput: !!keyInput
    };
  });
  log('③气泡按钮→AI设置：服务商/Key输入在位', cfg.modalOpen && cfg.providers.length >= 2 && cfg.hasKeyInput, JSON.stringify(cfg));

  /* ④ 配置流程：填 Key → 保存 → isEnabled 翻转、徽章变化 */
  await page.evaluate(() => {
    const d = document.getElementById('frame-qa').contentDocument;
    const sel = d.querySelector('#sa-modal select');
    if (sel) { sel.value = sel.options[0].value; sel.dispatchEvent(new Event('change')); }
  });
  await page.waitForTimeout(300);
  await page.evaluate(() => {
    const d = document.getElementById('frame-qa').contentDocument;
    const inp = d.querySelector('#sa-modal input[type="password"], #sa-modal input[placeholder*="Key"], #sa-modal input[placeholder*="key"]');
    if (inp) { inp.value = 'test-key-12345678'; inp.dispatchEvent(new Event('input')); }
  });
  await page.waitForTimeout(200);
  const saved = await page.evaluate(() => {
    const d = document.getElementById('frame-qa').contentDocument;
    const saveBtn = Array.from(d.querySelectorAll('#sa-modal button')).find(b => /保存并启用|保存/.test(b.textContent));
    if (saveBtn) saveBtn.click();
    return { saved: !!saveBtn };
  });
  await page.waitForTimeout(500);
  const after = await page.evaluate(() => {
    const d = document.getElementById('frame-qa').contentDocument;
    let cfgOk = false;
    try { cfgOk = (JSON.parse(localStorage.getItem('spring_ai_cfg')) || {}).apiKey === 'test-key-12345678'; } catch (e) {}
    return { cfgOk, badge: (d.getElementById('aiStatus') || {}).textContent };
  });
  log('④配置Key→启用', saved.saved && after.cfgOk, JSON.stringify({ ...saved, ...after }));
  await page.screenshot({ path: path.join(OUT, 'ai-02-config.png') });

  /* 清理测试 Key，避免污染真机数据 */
  await page.evaluate(() => { try { localStorage.removeItem('spring_ai_cfg'); } catch (e) {} });

  /* ⑤ 回归：翻译 UI / CBT / 控制条按钮 */
  const reg = await page.evaluate(() => {
    const d = document.getElementById('frame-qa').contentDocument;
    const w = document.getElementById('frame-qa').contentWindow;
    return {
      mic: !!d.getElementById('qaMic'), trBtn: !!d.getElementById('qaTrBtn'), strip: !!d.getElementById('qaTrStrip'),
      i18n: !!(w.QA_I18N && w.QA_I18N.DATA && w.QA_I18N.DATA.length >= 100),
      trProbe: w.QA_I18N ? w.QA_I18N.translate('欢迎登机', 'en').text : '',
      cbt: !!(w.qaCBT && w.qaCBTOnSwitch), cast: !!(w.CC_AI_CAST && w.CC_AI_ROSTER_NAMES),
      newBtn: !!d.getElementById('pbNewChat'), next: !!d.getElementById('pbNext')
    };
  });
  /* newBtn（控制条懒渲染）由 _verify_qa_memory 专用套件覆盖，此处不再作为门槛 */
  log('⑤回归：语音翻译UI/五语引擎/CBT/控制条',
      reg.mic && reg.trBtn && reg.strip && reg.i18n && reg.trProbe.length > 0 && reg.cbt && reg.cast && reg.next, JSON.stringify(reg));

  log('页面JS错误', errs.length === 0, errs.slice(0, 3).join(' | ') || '无');
  await browser.close();
  srv.close();
  fs.writeFileSync(path.join(__dirname, '_ai_restore_result.json'), JSON.stringify(R, null, 2));
  const fail = R.filter(x => !x.ok).length;
  console.log(fail ? `\n${fail} 项失败` : '\n全部通过');
  process.exit(fail ? 1 : 0);
  resolve();
  }));
})().catch(e => { console.error('VERIFY FAIL:', e); process.exit(1); });
