# -*- coding: utf-8 -*-
"""CBT 答题板块 + 大撤应急页面补丁（2026-09-18 v2）

对 quiz.html 做幂等改造：
  1) 状态块：答题状态持久化 / 分页游标 / CBT 分组（普通·321）
  2) renderDache() 全量替换：CBT 不再渲染知识卡与内嵌自测，改为「答题板块」——
     进入时选择 全部 / 普通 / 321，点「开始练习」（常规答题引擎 startQuiz）或「模拟考」，
     并列出按章节题量概览（点章节直接开练）
  3) dcSetTab / _dcUpdateProg / dcPick / dcResetQuiz 替换 + 新增 _dcPaint/_dcRestore/dcMoreQuiz
     + CBT 板块函数 cbtIdx/cbtCount/startCbtQuiz/startCbtExam
  4) DC_CAT_META 增加 'CBT练习' 卡面（用于场景方块与标题）
  5) 侧栏 NAV_ITEMS 标签回收为「大撤应急」

用法：python _apply_cbt_scene_20260918.py            # 执行
      python _apply_cbt_scene_20260918.py --check    # 校验（不一致则非零退出）
"""
import io, os, sys, shutil

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
QUIZ = os.path.join(HERE, 'quiz.html')

B = '/* CBT_SCENE_CODE_BEGIN（_apply_cbt_scene_20260918.py 注入；改动请改脚本后重跑） */'
E = '/* CBT_SCENE_CODE_END */'
ANCHOR1 = 'let _dcTab = null;'

NEW_STATE = B + """
/* 大撤场景答题状态 + CBT 答题板块（2026-09-18） */
const _dcQZAll = () => (window.DC_QUIZ || []);
const _dcAns = {};                 // 题号 -> {oi, right}；切场景不丢已答进度
let _dcQuizLimit = 30, _dcCbtGrp = '普通';
const _dcIsDc = c => String(c || '').indexOf('大撤') === 0;
const DC_CBT_CAT = 'CBT练习';
const _dcIsCbtCat = c => String(c || '') === DC_CBT_CAT;
/* —— CBT 练习题库（培训考核的独立特殊分类）：

     题库中 src==='cbt'；chapter = CBT练习·普通题目 / CBT练习·321机型题（培训考核分区两张卡），
     cbtCh = CBT 十类细目（第一章 概述 … 第八章 附录 / 无解析 / 321机型补充） —— */
const CBT321_CH = 'CBT练习·321机型题';
function cbtQuestions(grp){
  const all = (APP.questions || []).filter(q => q.src === 'cbt');
  const g = grp || _dcCbtGrp;
  if(g === '321') return all.filter(q => q.chapter === CBT321_CH);
  if(g === '普通') return all.filter(q => q.chapter !== CBT321_CH);
  return all;
}
function cbtIdx(grp){
  const set = new Set(cbtQuestions(grp));
  return (APP.questions || []).map((q, i) => set.has(q) ? i : -1).filter(i => i >= 0);
}
function cbtCount(grp){ return cbtQuestions(grp).length; }
function cbtChapterRows(grp){
  const m = new Map();
  cbtQuestions(grp).forEach(q => { const k = q.cbtCh || q.chapter; m.set(k, (m.get(k) || 0) + 1); });
  const order = ['第一章 概述','第二章 术语和定义','第三章 安全规则','第四章 机型设备',
    '第五章 标准操作程序','第六章 应急程序','第七章 应急救护','第八章 附录','无解析','321机型补充'];
  return [...m.entries()].sort((a, b) => {
    const ia = order.indexOf(a[0]), ib = order.indexOf(b[0]);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
  });
}
function startCbtQuiz(grp){
  if(grp) _dcCbtGrp = grp;
  const idxs = cbtIdx(_dcCbtGrp);
  if(!idxs.length){ toast('该分组暂无题目', 'warning'); return; }
  startQuiz(idxs);
}
function startCbtExam(grp){
  if(grp) _dcCbtGrp = grp;
  const idxs = cbtIdx(_dcCbtGrp);
  if(!idxs.length){ toast('该分组暂无题目', 'warning'); return; }
  startExam(idxs, 1800);
}
function startCbtChapter(chapter){
  const idxs = (APP.questions || []).map((q, i) => (q.src === 'cbt' && (q.cbtCh || q.chapter) === chapter) ? i : -1).filter(i => i >= 0);
  if(!idxs.length){ toast('该章节暂无题目', 'warning'); return; }
  startQuiz(idxs);
}
function dcSetGrp(g){ _dcCbtGrp = g; _dcQuizLimit = 30; renderDache(); }
function dcMoreQuiz(){ _dcQuizLimit += 60; renderDache(); }""" + E

NEW_RENDER = B + """
function renderDache(){
  const KB = (window.DC_KB || []);
  const cats = [];
  KB.forEach(k => { if(k.cat && cats.indexOf(k.cat) < 0) cats.push(k.cat); });
  if(cats.indexOf(DC_CBT_CAT) < 0) cats.push(DC_CBT_CAT);   // CBT 答题板块（题目在题库中，页面无卡片）
  if(!_dcTab || cats.indexOf(_dcTab) < 0) _dcTab = cats[0] || '';
  const meta = _dcMeta(_dcTab);
  const isDc = _dcIsDc(_dcTab);
  const isCbt = _dcIsCbtCat(_dcTab);
  const cheatsTotal = (DC_CHEATS||[]).reduce((s,g)=>s+(g.items?g.items.length:0),0);
  /* 大撤：知识卡 + 场景内自测题；CBT：仅答题板块 */
  const QZ = isCbt ? [] : _dcQZAll();
  const vis = QZ.map((q,gi)=>({q,gi})).filter(x => x.q.c === _dcTab || (isDc && x.q.c === '大撤专项'));
  const allItems = isCbt ? [] : KB.filter(k => k.cat === _dcTab);
  const shownQ = vis.slice(0, _dcQuizLimit);
  const tiles = cats.map(c => {
    const m = _dcMeta(c);
    const n = _dcIsCbtCat(c) ? cbtCount('全部') : KB.filter(k => k.cat === c).length;
    const unit = _dcIsCbtCat(c) ? '题' : '张知识卡';
    return `<button class="dc-tile${c===_dcTab?' on':''}" style="--dc-c:${m.color}" onclick="dcSetTab('${_dcEsc(c)}')" title="${_dcEsc(m.desc||'')}">
      <span class="dc-tile-ic">${m.icon}</span>
      <span class="dc-tile-t">${_dcEsc(String(c).replace('大撤·',''))}</span>
      <small>${n} ${unit}</small>
    </button>`;
  }).join('');
  const flow = (DC_FLOW||[]).map(s => `
    <div class="dc-flow-step"><i>${s.n}</i><b>${_dcEsc(s.t)}</b><span>${_dcEsc(s.d)}</span></div>`).join('');
  const cards = allItems.map((k,ki) => `
    <div class="dc-card${k.acc?' dc-acc':''}" style="--dc-c:${meta.color}"${k.acc?` onclick="dcToggleAcc(this)" title="点击展开/收起流程"`:''}>
      <div class="dc-card-hd">
        <span class="dc-card-no">${ki+1}</span>
        <span class="dc-hd-ic">${k.icon||meta.icon}</span>
        <span>${_dcEsc(k.q)}</span>
        <span class="dc-src">${_dcEsc(k.src||'')}</span>
      </div>
      <div class="dc-card-bd">${k.a}</div>
    </div>`).join('');
  const chips = (meta.points||[]).map(p => `<span class="dc-chip">${_dcEsc(p)}</span>`).join('');
  const cheats = (DC_CHEATS||[]).map(g => `
    <div class="dc-keys-g">
      <div class="dc-keys-g-t">${g.icon} ${_dcEsc(g.g)}</div>
      <div class="dc-keys-row">${(g.items||[]).map(it=>`<span class="dc-keys-item"><b>${_dcEsc(it.k)}</b>${_dcEsc(it.v)}</span>`).join('')}</div>
    </div>`).join('');
  const quizHtml = shownQ.map(({q,gi},pos) => {
    const opts = (q.o||[]).map((op,oi) => {
      const m = String(op).match(/^([A-E])[.．]\\s*/);
      const letter = m ? m[1] : String(op).trim();
      const label = String(op).replace(/^[A-E][.．]\\s*/,'');
      return `<div class="dc-opt" id="dcq${gi}o${oi}" onclick="dcPick(${gi},${oi})"><b>${_dcEsc(letter)}</b><span>${_dcEsc(label)}</span></div>`;
    }).join('');
    return `<div class="dc-q" id="dcq${gi}" data-a="${_dcEsc(q.a)}">
      <div class="dc-q-t">${pos+1}. ${_dcEsc(q.q)} <span class="dc-q-type">${_dcEsc(q.t||'单选')}</span>${q.x?` <span class="dc-q-type" style="background:#eef5f1;color:#0f6b43">${_dcEsc(q.x)}</span>`:''}</div>
      ${opts}
      <div class="dc-q-ex" id="dcq${gi}ex" style="display:none"></div>
    </div>`;
  }).join('');
  const moreQuiz = vis.length > shownQ.length
    ? `<div style="text-align:center;padding:14px"><button class="btn" onclick="dcMoreQuiz()">显示更多题目（剩 ${vis.length - shownQ.length} 题）</button></div>` : '';
  /* ---- CBT 答题板块面板 ---- */
  const cm = window.CBT_META || {};
  const grpDefs = [['全部','全部题目'],['普通','普通题目'],['321','321 机型题']];
  const cbtPanel = !isCbt ? '' : `
    <div class="dc-scene" id="dcScene" style="background:#fff;border:1px solid #dfe7e2;border-radius:14px;padding:18px;margin-top:18px">
      <div class="dc-sec-hd" style="margin-bottom:12px">🎯 CBT 练习题库 · 选择要练习的分组
        <span class="dc-sec-sub">进入答题前先选分组 · 答题为常规答题板（逐题作答、即时判分、错题自动进错题本）</span></div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px">
        ${grpDefs.map(([k,label]) => {
          const n = cbtCount(k);
          const on = (k === _dcCbtGrp);
          return `<div style="border:2px solid ${on?meta.color:'#dfe7e2'};border-radius:12px;padding:14px;background:${on?'#f2fbf8':'#fff'}">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
              <input type="radio" name="cbtGrp" ${on?'checked':''} onclick="dcSetGrp('${k}')" style="cursor:pointer">
              <b style="font-size:1rem">${label}</b>
              <span style="margin-left:auto;color:${meta.color};font-weight:700">${n} 题</span>
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <button class="btn" style="flex:1;min-width:104px" onclick="dcSetGrp('${k}');startCbtQuiz('${k}')">▶ 开始练习</button>
              <button class="btn" style="flex:1;min-width:104px;background:#fff;color:${meta.color};border:1px solid ${meta.color}" onclick="dcSetGrp('${k}');startCbtExam('${k}')">📝 模拟考 30 分钟</button>
            </div>
          </div>`;
        }).join('')}
      </div>
      <div class="dc-sec-hd" style="margin:18px 0 8px">📚 按章节练习
        <span class="dc-sec-sub">点章节名直接开始该章节练习</span></div>
      <div style="display:flex;flex-wrap:wrap;gap:8px">
        ${cbtChapterRows('全部').map(([ch, n]) => `<button class="dc-chip" style="cursor:pointer;padding:6px 12px;font-size:.83rem" onclick="startCbtChapter('${_dcEsc(ch)}')">${_dcEsc(ch)} <b>${n}</b></button>`).join('')}
      </div>
      <div class="dc-keys" style="margin-top:18px;border-top:1px dashed #dfe7e2;padding-top:12px">
        <div class="muted" style="font-size:.84rem;line-height:1.8">
          <b>本板块核验（逐题对照《客舱乘务员手册》01.10）</b>：
          章节号有效 <b>${(cm.verify&&cm.verify.secRefOk)||785}/${(cm.verify&&cm.verify.total)||785}</b>　·　
          选项与答案内部一致 <b>${(cm.verify&&cm.verify.optConsistent)||785}</b>（0 处错位）　·　
          答案原文/答案值核验通过 <b>${(cm.verify&&cm.verify.answerOk)||422}</b> 题　·　
          依据偏弱 <b>${(cm.verify&&cm.verify.weak)||308}</b> 题 · 未检出 <b>${(cm.verify&&cm.verify.none)||55}</b> 题（解析中已标注「核验」）。
          题目解析均带精确章节号，可在答题后的解析与「题库 · 航班清单」中查看。
        </div>
      </div>
    </div>`;
  const heroDesc = isDc
    ? '依据「动态舱应急撤离流程（大撤）」「CRM机组演练」「机型设备」「设备背诵」四份资料整理归纳，并与《客舱乘务员手册》01.10 应急/设备条目逐项核对——重叠关键数字全部一致。'
    : 'CBT 练习题库（785 题）——进入板块先选分组（普通 / 321），再进入<strong>常规答题板</strong>逐题练习；题目解析逐题对齐《客舱乘务员手册》01.10 章节，并带精确章节号与核验标记。';
  document.getElementById('mainContent').innerHTML = `
  <div class="dc-wrap">
    <div class="dc-hero">
      <span class="dc-hero-kicker">✈️ 春秋航空广州分队 · 客舱小助手</span>
      <h2>🚨 大撤应急 · 场景库</h2>
      <p>${heroDesc}全部考点已<strong>归纳为 ${cats.length} 大场景专题</strong>（含<strong>撤离程序</strong>五张可点击流程卡），每专题附<strong>一句话总结 + 速记要点</strong>，底部另有<strong>关键数字速记卡</strong>。<br>💬 在「你问我答」输入 <b>/大撤 关键词</b> 或点 <b>🚨 大撤专项</b> 库可随时提问。</p>
      <div class="dc-hero-stats">
        <div class="dc-stat"><div class="n">${KB.length}</div><div class="l">知识卡</div></div>
        <div class="dc-stat"><div class="n">${cats.length}</div><div class="l">场景专题</div></div>
        <div class="dc-stat"><div class="n">${cheatsTotal}<span style="font-size:.8rem">项</span></div><div class="l">关键数字速记</div></div>
        <div class="dc-stat"><div class="n">${isCbt ? cbtCount('全部') : QZ.length}</div><div class="l">可练题目</div></div>
      </div>
    </div>

    ${isDc ? `<div class="dc-flow">
      <div class="dc-sec-hd">🛫 大撤八阶段 · 全景流程 <span class="dc-sec-sub">动态舱应急撤离全程主线 · 点击下方场景专题查看对应阶段完整处置</span></div>
      <div class="dc-flow-strip">${flow}</div>
    </div>` : ''}

    <div class="dc-lib">
      <div class="dc-sec-hd">🗂 场景库 · ${cats.length} 大场景专题 <span class="dc-sec-sub">每个专题是一类场景 · 点击方块进入该场景${isDc?'，查看全部知识卡并在下方练习本场景题目':'，选择分组进入答题'}</span></div>
      <div class="dc-lib-grid">${tiles}</div>
    </div>

    ${isCbt ? cbtPanel : `
    <div class="dc-scene" id="dcScene">
      <div class="dc-scene-hd" style="--dc-c:${meta.color}">
        <span class="dc-scene-ic">${meta.icon}</span>
        <div class="dc-scene-tx">
          <div class="dc-scene-name">${_dcEsc(_dcTab)} <span class="dc-scene-tag">${_dcEsc(meta.tag||'')}</span></div>
          <div class="dc-scene-sum">${_dcEsc(meta.summary||meta.desc||'')}</div>
        </div>
        <span class="dc-scene-n">${allItems.length}<small> 张知识卡</small></span>
      </div>
      ${chips ? `<div class="dc-chips">${chips}</div>` : ''}
      ${cards || '<div class="card" style="padding:18px;text-align:center;color:var(--text2)">该场景暂无内容</div>'}
    </div>`}

    ${isDc ? `<div class="dc-keys">
      <div class="dc-sec-hd">⚡ 关键数字速记卡 <span class="dc-sec-sub">考前 30 秒扫一遍 · 全部出自上方知识卡原文</span></div>
      ${cheats}
    </div>` : ''}

    ${isCbt ? '' : `
    <div class="dc-quiz-card">
      <div class="dc-quiz-hd">
        <span class="t">✍️ ${_dcEsc(String(_dcTab).replace('大撤·',''))} · 自测</span>
        <span style="font-size:.75rem;color:var(--text3)">${vis.length} 题 · 点击选项即时批改${vis.length > shownQ.length ? '（已加载 ' + shownQ.length + ' 题）' : ''}</span>
        <span class="dc-prog"><span id="dcProgText">0/${shownQ.length}</span><span class="dc-prog-bar"><i id="dcProgBar"></i></span></span>
      </div>
      <div class="dc-quiz-sub">题目均出自上方知识卡原文，答错请回到对应场景专题复习（切换专题不会丢失已答进度）。</div>
      ${quizHtml}
      ${moreQuiz}
      <div id="dcQuizScore" class="dc-score"></div>
      <button class="btn" style="margin-top:12px" onclick="dcResetQuiz()">↻ 重做本组题</button>
    </div>`}
  </div>`;
  _dcRestore();
}
""" + E

NEW_DC = B + """
function dcSetTab(c){ _dcTab = c; _dcQuizLimit = 30; renderDache();
  const el = document.getElementById('dcScene');
  if(el) setTimeout(()=>el.scrollIntoView({behavior:'smooth', block:'start'}), 60);
}
function _dcPaint(box, q, oi, right){
  const ans = box.dataset.a;
  box.dataset.done = '1';
  if(right) box.dataset.ok = '1';
  box.classList.add('done');
  const opts = box.querySelectorAll('.dc-opt');
  (q.o||[]).forEach((op, idx) => {
    const mm = String(op).match(/^([A-E])[.．]\\s*/);
    const letter = mm ? mm[1] : String(op).trim();
    if(letter === ans) opts[idx].classList.add('right');
    else if(idx === oi && !right) opts[idx].classList.add('wrong');
    opts[idx].classList.add('lock');
  });
  const ex = document.getElementById(box.id + 'ex');
  if(ex){
    ex.textContent = (right ? '✅ 回答正确。' : '❌ 回答错误，正确答案：' + ans + '。') + (q.e || '');
    ex.style.display = 'block';
    ex.classList.toggle('ex-wrong', !right);
  }
}
function _dcRestore(){
  document.querySelectorAll('[id^="dcq"][data-a]').forEach(box => {
    const gi = parseInt(String(box.id).slice(3), 10);
    const st = _dcAns[gi];
    if(!st) return;
    const q = _dcQZAll()[gi];
    if(q) _dcPaint(box, q, st.oi, st.right);
  });
  _dcUpdateProg();
}
function _dcUpdateProg(){
  const all = document.querySelectorAll('[id^="dcq"][data-a]');
  let done = 0, ok = 0;
  all.forEach(b => { if(b.dataset.done === '1'){ done++; if(b.dataset.ok === '1') ok++; } });
  const txt = document.getElementById('dcProgText'), bar = document.getElementById('dcProgBar');
  if(txt) txt.textContent = done + '/' + all.length;
  if(bar) bar.style.width = (all.length ? done / all.length * 100 : 0) + '%';
  const sc = document.getElementById('dcQuizScore');
  if(sc && all.length && done === all.length && sc.style.display !== 'block'){
    const pct = Math.round(ok / all.length * 100);
    const cls = pct === 100 ? 'perfect' : (pct >= 80 ? 'good' : (pct >= 60 ? 'soso' : 'bad'));
    const msg = pct === 100 ? '🎉 全对，稳了！' : (pct >= 80 ? '👍 很扎实，错题回卡复习即可。' : (pct >= 60 ? '💪 及格了，把错题对应的知识卡再看一遍。' : '📖 建议按分类把知识卡通读一遍再重做。'));
    sc.className = 'dc-score ' + cls;
    sc.style.display = 'flex';
    sc.innerHTML = `<span style="font-size:1.25rem">${pct === 100 ? '🏆' : (pct >= 80 ? '✨' : '✍️')}</span><span>${ok} / ${all.length}（${pct}%）</span><span style="font-weight:600;font-size:.84rem;opacity:.92">${msg}</span>`;
  }
}
function dcPick(qi, oi){
  const box = document.getElementById('dcq' + qi);
  if(!box || box.dataset.done === '1') return;
  const q = _dcQZAll()[qi];
  if(!q) return;
  const m = String(q.o[oi]).match(/^([A-E])[.．]\\s*/);
  const picked = m ? m[1] : String(q.o[oi]).trim();
  const right = picked === box.dataset.a;
  _dcAns[qi] = { oi: oi, right: right };
  _dcPaint(box, q, oi, right);
  _dcUpdateProg();
}
function dcResetQuiz(){
  const isDc = _dcIsDc(_dcTab);
  _dcQZAll().map((q,gi)=>({q,gi}))
    .filter(x => (x.q.c === _dcTab || (isDc && x.q.c === '大撤专项')))
    .forEach(x => { delete _dcAns[x.gi]; });
  renderDache();
}
""" + E

CAT_META_ANCHOR = "\n};\nconst _dcMeta = c => DC_CAT_META[c] ||"
CAT_META_NEW = """,
  'CBT练习':      { icon:'🎯', color:'#0d9488', tag:'CBT 题库 · 答题板块', desc:'785 题 · 进入可选 普通 / 321',
    summary:'CBT 练习题库 785 题（普通 719 + 321 机型 66）——进入板块先选分组，再进入常规答题板逐题练习。解析逐题对照《客舱乘务员手册》01.10：章节号 785/785 有效、选项与答案内部一致 785/785（0 处错位），并带精确章节号与核验标记。',
    points:['普通 719 题','321 机型 66 题','章节号全部有效','选项/答案零错位','进入可选分组'] }
};\nconst _dcMeta = c => DC_CAT_META[c] ||"""

NAV_OLD = "{id:'dache',icon:'🎯',label:'场景库'}"
NAV_NEW = "{id:'dache',icon:'🚨',label:'大撤应急'}"

# ---- 培训考核：CBT练习作为独立特殊分类（题库页手册清单 + 章节专项练习分区 + 错题本手册名）----
MANUALS_ANCHOR = ("  {id:'csd',  name:'客舱服务规范', icon:'📗', desc:'CQH-CSD-CSS · "
                  "职业形象/工作要求/特殊旅客/特殊航班/话术/尊享飞/机上销售/乘务长管理'}\n];")
MANUALS_NEW = ("  {id:'csd',  name:'客舱服务规范', icon:'📗', desc:'CQH-CSD-CSS · "
               "职业形象/工作要求/特殊旅客/特殊航班/话术/尊享飞/机上销售/乘务长管理'},\n"
               "  {id:'cbt',  name:'CBT练习', icon:'🎯', desc:'独立特殊分类 · cbt_题库_785题 · "
               "普通 719 / 321 机型 66 · 逐题对齐《客舱乘务员手册》01.10'}\n];")

TAB_ANCHOR = ("      <button class=\"mtab ${filterManual==='csd'?'active':''}\" "
              "onclick=\"setBankManual('csd')\">📗 客舱服务规范</button>\n    </div>")
TAB_NEW = ("      <button class=\"mtab ${filterManual==='csd'?'active':''}\" "
           "onclick=\"setBankManual('csd')\">📗 客舱服务规范</button>\n"
           "      <button class=\"mtab ${filterManual==='cbt'?'active':''}\" "
           "onclick=\"setBankManual('cbt')\">🎯 CBT练习</button>\n    </div>")

CHAPS_ANCHOR = ("  const csdChaps = chapterOrder.filter(c=>APP.questions.some("
                "q=>q.chapter===c && manualOf(q)==='csd'));")
CHAPS_NEW = CHAPS_ANCHOR + ("\n  const cbtChaps = chapterOrder.filter(c=>APP.questions.some("
                            "q=>q.chapter===c && manualOf(q)==='cbt'));")

SEC_ANCHOR = ("      ${csdChaps.length?`<div class=\"manual-sec\">\n"
              "        <div class=\"manual-sec-title\">📗 客舱服务规范 <span class=\"manual-sec-meta\">"
              "${csdChaps.reduce((s,c)=>s+chapterData[c].total,0)}题</span></div>\n"
              "        <div class=\"manual-sec-grid\">${renderChCards(csdChaps,crewChaps.length)}</div>\n"
              "      </div>`:''}")
SEC_NEW = SEC_ANCHOR + ("\n      ${cbtChaps.length?`<div class=\"manual-sec\">\n"
                        "        <div class=\"manual-sec-title\">🎯 CBT练习 "
                        "<span class=\"manual-sec-meta\">独立特殊分类 · "
                        "${cbtChaps.reduce((s,c)=>s+chapterData[c].total,0)}题</span></div>\n"
                        "        <div class=\"manual-sec-grid\">${renderChCards(cbtChaps,"
                        "crewChaps.length+csdChaps.length)}</div>\n"
                        "      </div>`:''}")

MANUALNAME_ANCHOR = "  const manualName = manualOf(q)==='csd' ? '《客舱服务规范》' : '《客舱乘务员手册》';"
MANUALNAME_NEW = ("  const _mo = manualOf(q);\n"
                  "  const manualName = _mo==='csd' ? '《客舱服务规范》' : "
                  "(_mo==='cbt' ? '《客舱乘务员手册》· CBT练习题库' : '《客舱乘务员手册》');")

# 章节排序：让 CBT 分区内「普通题目」排在「321机型题」之前（并统一置后于原题库章节）
SORT_ANCHOR = ("    if(ai>=0 && bi>=0) return ai-bi;\n"
               "    if(ai>=0) return -1;\n"
               "    if(bi>=0) return 1;\n"
               "    return a.localeCompare(b,'zh-CN');\n  });")
SORT_NEW = ("    if(ai>=0 && bi>=0) return ai-bi;\n"
            "    if(ai>=0) return -1;\n"
            "    if(bi>=0) return 1;\n"
            "    const ca = a.indexOf('CBT练习·')===0 ? (a.indexOf('普通')>=0?0:1) : -1;\n"
            "    const cb = b.indexOf('CBT练习·')===0 ? (b.indexOf('普通')>=0?0:1) : -1;\n"
            "    if(ca>=0 && cb>=0) return ca-cb;\n"
            "    if(ca>=0) return 1;\n"
            "    if(cb>=0) return -1;\n"
            "    return a.localeCompare(b,'zh-CN');\n  });")


def span_to(s, start_marker, end_marker, _from=0):
    i = s.find(start_marker, _from)
    if i < 0: return -1, -1
    j = s.find(end_marker, i + len(start_marker))
    return i, j


def apply_block(s, st, en, new_text):
    """把 s[st:en] 换成 new_text；若上方紧邻 BEGIN 标记则并入起点（保证幂等）。"""
    pre = s.rfind(B, 0, st)
    if pre >= 0 and s[pre + len(B):st].strip() == '':
        st = pre
    if s[st:en].strip() == new_text.strip():
        return s, 0
    tail = s[en:]
    sep = '' if tail.startswith('\n') else '\n'
    return s[:st] + new_text + sep + tail, 1


def transform(s):
    n = 0
    # 1) 状态块：紧跟 let _dcTab = null; 之后
    if ANCHOR1 not in s:
        raise SystemExit('!! 未找到 `let _dcTab = null;`')
    p = s.find(ANCHOR1) + len(ANCHOR1)
    i, j = span_to(s, B, E, p)
    if i >= 0 and j > i and s[p:i].strip() == '':
        s, k = apply_block(s, p, j + len(E), NEW_STATE); n += k
    else:
        s = s[:p] + '\n' + NEW_STATE + s[p:]; n += 1

    # 2) renderDache
    st, en = span_to(s, 'function renderDache(){', 'function dcToggleAcc')
    if st >= 0 and en > st:
        s, k = apply_block(s, st, en, NEW_RENDER); n += k

    # 3) dcSetTab .. dcResetQuiz
    st, en = span_to(s, 'function dcSetTab(c){', 'function renderIssues')
    if st >= 0 and en > st:
        s, k = apply_block(s, st, en, NEW_DC); n += k

    # 4) DC_CAT_META
    if "'CBT练习':" not in s:
        if CAT_META_ANCHOR not in s:
            raise SystemExit('!! 未找到 DC_CAT_META 结尾锚点')
        s = s.replace(CAT_META_ANCHOR, CAT_META_NEW, 1); n += 1

    # 5) NAV label 回收为「大撤应急」
    if NAV_OLD in s:
        s = s.replace(NAV_OLD, NAV_NEW, 1); n += 1

    # 6) 手册清单 MANUALS 增加 cbt
    if "name:'CBT练习'" not in s:
        if MANUALS_ANCHOR not in s:
            raise SystemExit('!! 未找到 MANUALS 结尾锚点')
        s = s.replace(MANUALS_ANCHOR, MANUALS_NEW, 1); n += 1

    # 7) 题库页 手册标签 增加 CBT练习
    if "setBankManual('cbt')" not in s:
        if TAB_ANCHOR not in s:
            raise SystemExit('!! 未找到题库页手册标签锚点')
        s = s.replace(TAB_ANCHOR, TAB_NEW, 1); n += 1

    # 8) 章节专项练习：新增 CBT 分区
    if 'const cbtChaps' not in s:
        if CHAPS_ANCHOR not in s:
            raise SystemExit('!! 未找到 csdChaps 锚点')
        s = s.replace(CHAPS_ANCHOR, CHAPS_NEW, 1); n += 1
    if '🎯 CBT练习 <span class="manual-sec-meta">独立特殊分类' not in s:
        if SEC_ANCHOR not in s:
            raise SystemExit('!! 未找到 章节专项练习 客舱服务规范分区锚点')
        s = s.replace(SEC_ANCHOR, SEC_NEW, 1); n += 1

    # 9) 错题本手册名兼容 cbt
    if "_mo==='cbt'" not in s:
        if MANUALNAME_ANCHOR not in s:
            raise SystemExit('!! 未找到错题本 manualName 锚点')
        s = s.replace(MANUALNAME_ANCHOR, MANUALNAME_NEW, 1); n += 1

    # 10) 章节排序：CBT 分区内 普通题目 在 321机型题 之前
    if "const ca = a.indexOf('CBT练习·')" not in s:
        if SORT_ANCHOR not in s:
            raise SystemExit('!! 未找到章节排序锚点')
        s = s.replace(SORT_ANCHOR, SORT_NEW, 1); n += 1

    for need in (B, 'const DC_CBT_CAT', 'startCbtQuiz', "'CBT练习':", 'cbtIdx(', 'const cbtChaps',
                 "setBankManual('cbt')", "const ca = a.indexOf('CBT练习·')"):
        if need not in s:
            raise SystemExit('!! 补丁不完整，缺少：' + need[:40])
    if NAV_NEW not in s:
        raise SystemExit('!! 侧栏标签未回收为「大撤应急」')
    return s, n


def main():
    check = '--check' in sys.argv
    s = io.open(QUIZ, encoding='utf-8', newline='').read()
    out, n = transform(s)
    if check:
        if out == s:
            print('  quiz.html CBT场景代码 -> UP-TO-DATE'); return
        print('!! quiz.html CBT场景代码与脚本目标不一致'); sys.exit(1)
    if out == s:
        print('  quiz.html CBT场景代码 -> UP-TO-DATE（无需改动）'); return
    bak = os.path.join(HERE, 'quiz.bak_cbtscene_20260918.html')
    if not os.path.exists(bak):
        shutil.copy2(QUIZ, bak); print('  备份 ->', os.path.basename(bak))
# __ATOMIC_WRITE_20260921__
    _tmp_w = (QUIZ) + ".tmp_write"
    with io.open(_tmp_w, "w", encoding="utf-8", newline="") as _f_w:
        _f_w.write(out)
    os.replace(_tmp_w, (QUIZ))
    print(f'  quiz.html CBT答题板块 应用 {n} 处补丁（{len(s)} -> {len(out)} chars）')


if __name__ == '__main__':
    main()
