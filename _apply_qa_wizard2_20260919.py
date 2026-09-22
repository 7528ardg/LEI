# -*- coding: utf-8 -*-
"""话术向导增强（2026-09-19）
--------------------------------------------------------------------------------
需求（用户第 3 条）：
  ① 多种触发方式：保留原有 5 步界面选项；**新增直接输入产品名即出稿**
     （例：雅诗兰黛小棕瓶 / 海蓝之谜精粹水 / 小棕瓶 / 神仙水 …）
  ② 生成结果下新增「🔁 换个风格」：对当前稿不满意时一键换另一版风格重生成

实现要点：
  · QA_BRAND / QA_PROD_ALIAS：产品名 → 品牌 / 常见昵称，支持"品牌+品类词"粗粒度命中
    （例「海蓝之谜精粹水」→ 命中本库唯一的海蓝之谜产品，不强行编造不存在的 SKU）
  · qaMatchProducts / qaLeftover：命中打分 + "剩余词"判定，避免抢答知识类问法
    （「小棕瓶的成分是什么」不会被当成出稿请求）
  · buildScript / buildTalkScript 增加 cfg.products 过滤：只针对点名的产品出稿
  · qaRenderScript 统一渲染；SCRIPT_STYLE_CYCLE 四套风格循环（复用现有引擎旋钮，
    不新造引擎）：定向推荐稳妥款 / 广播脱口秀 / 高端定位 / 性价比快速促单

用法：python _apply_qa_wizard2_20260919.py [--check]
"""
import io
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')

def _atomic_write(path, text):
    """先写临时文件再原子替换：任何编码/写入异常都不会破坏源文件。"""
    tmp = path + u'.tmp_write'
    io.open(tmp, 'w', encoding='utf-8', newline='').write(text)
    os.replace(tmp, path)
ROOT = os.path.dirname(os.path.abspath(__file__))
QA = os.path.join(ROOT, u'qa.html')
BAK = os.path.join(ROOT, u'_bak_qa_wizard2_20260919.html')
MARK = u'/*__QA_WIZARD2_v1__*/'


def rd(p):
    return io.open(p, 'r', encoding='utf-8', newline='').read()


def wr(p, s):
    _atomic_write(p, s)


def sub_once(s, old, new, tag):
    n = s.count(old)
    if n != 1:
        raise SystemExit(u'[ERR] %s：期望 1 处，实际 %d 处\n---\n%s' % (tag, n, old[:240]))
    return s.replace(old, new)


# ---------------- W1/W2：引擎支持"只对点名的产品出稿" ----------------
TALK_OLD = u"""function buildTalkScript(cfg){
  const cats = SCRIPT_CATS.filter(function(c){ return (cfg.cats || []).indexOf(c.key) >= 0; });
  if(!cats.length) return '请至少选择一个品类';
  const prods = [];
  cats.forEach(function(c){
    c.items.forEach(function(it){
      prods.push({ _type: c.key, id: it.n, name: it.n, brand: '', category: '', coreBenefits: [it.m], keyIngredients: [{ commonName: it.m, mechanism: it.s }], targetSkinTypes: [] });
    });
  });
  const durMin = parseInt(cfg.dura || '3', 10);
  const s = qaTalkEngine.build(prods, { mode: 'strict', duration: durMin, time: cfg.time || 'auto', holiday: qaFestKeyOf(cfg) });
  if(!s) return '生成失败，请重试';
  return '「' + cats.map(function(c){ return c.label.replace(/^.\\s*/, ''); }).join(' / ') + '」广播·脱口秀稿（约 ' + durMin + ' 分钟）\\n\\n' + s.fullText;
}"""

TALK_NEW = u"""function buildTalkScript(cfg){
  const cats = SCRIPT_CATS.filter(function(c){ return (cfg.cats || []).indexOf(c.key) >= 0; });
  if(!cats.length) return '请至少选择一个品类';
  /* 2026-09-19：支持"指定产品"出稿（产品名直触发 / 换个风格都走这里） */
  const only = (cfg.products && cfg.products.length) ? cfg.products : null;
  const prods = [];
  cats.forEach(function(c){
    c.items.forEach(function(it){
      if(only && only.indexOf(it.n) < 0) return;
      prods.push({ _type: c.key, id: it.n, name: it.n, brand: '', category: '', coreBenefits: [it.m], keyIngredients: [{ commonName: it.m, mechanism: it.s }], targetSkinTypes: [] });
    });
  });
  if(!prods.length) return '没有匹配到产品，请换个名称或改用向导选品类。';
  const durMin = parseInt(cfg.dura || '3', 10);
  const s = qaTalkEngine.build(prods, { mode: 'strict', duration: durMin, time: cfg.time || 'auto', holiday: qaFestKeyOf(cfg) });
  if(!s) return '生成失败，请重试';
  const head = only ? ('「' + only.join(' / ') + '」') : ('「' + cats.map(function(c){ return c.label.replace(/^.\\s*/, ''); }).join(' / ') + '」');
  return head + '广播·脱口秀稿（约 ' + durMin + ' 分钟）\\n\\n' + s.fullText;
}"""

BS_HEAD_OLD = u"""function buildScript(cfg){
  const cats = SCRIPT_CATS.filter(c => (cfg.cats||[]).includes(c.key));
  const items = cats.flatMap(c => c.items);
  const catLabels = cats.map(c => c.label.replace(/^. /,''));"""

BS_HEAD_NEW = u"""function buildScript(cfg){
  const cats = SCRIPT_CATS.filter(c => (cfg.cats||[]).includes(c.key));
  /* 2026-09-19：指定产品时只对这几款出稿（产品名直触发用） */
  const only = (cfg.products && cfg.products.length) ? cfg.products : null;
  const pickItems = (c) => only ? c.items.filter(i => only.includes(i.n)) : c.items;
  const items = cats.flatMap(c => pickItems(c));
  if(!items.length) return '没有匹配到产品，请换个名称或改用向导选品类。';
  const catLabels = only ? only.slice() : cats.map(c => c.label.replace(/^. /,''));"""

BS_S1_OLD = u"""  p('核心卖点与成分', '乘务员：那这几款我给您展开讲讲——\\n' + cats.map(c =>
    `【${c.label.replace(/^. /,'')}】\\n` + combineSameType(c.items)
  ).join('\\n'));"""
BS_S1_NEW = u"""  p('核心卖点与成分', '乘务员：那这几款我给您展开讲讲——\\n' + cats.map(c =>
    `【${c.label.replace(/^. /,'')}】\\n` + combineSameType(pickItems(c))
  ).join('\\n'));"""

BS_S2_OLD = u"""  p('组合搭配建议', '乘务员：单买一样有效果，搭配得当才是1+1>2：\\n' + cats.map(c =>
    `${c.label.replace(/^. /,'')}：${c.items[0].n}打头做${c.items[0].m}，后续${c.items.slice(1).map(x => x.n + '负责' + x.m).join('、')}，一条链路补全需求。`
  ).join('\\n\\n') + '\\n这几样一起带正好覆盖刚才提到的诉求，组合更划算。');"""
BS_S2_NEW = u"""  p('组合搭配建议', '乘务员：单买一样有效果，搭配得当才是1+1>2：\\n' + cats.map(c => {
    const ci = pickItems(c);
    if(!ci.length) return '';
    if(ci.length === 1) return `${c.label.replace(/^. /,'')}：${ci[0].n}主打${ci[0].m}，${ci[0].s}。用法：${ci[0].u}。`;
    return `${c.label.replace(/^. /,'')}：${ci[0].n}打头做${ci[0].m}，后续${ci.slice(1).map(x => x.n + '负责' + x.m).join('、')}，一条链路补全需求。`;
  }).filter(Boolean).join('\\n\\n') + '\\n这几样一起带正好覆盖刚才提到的诉求，组合更划算。');"""

# ---------------- W3：产品名识别 + 统一渲染 + 换个风格 ----------------
WIZ2_BLOCK = u'''/*__QA_WIZARD2_v1__*/
/* ===================== 话术向导增强（2026-09-19） =====================
   ① 直接说产品名就出稿：产品全名 / 品牌 + 品类词 / 常见昵称都能命中
   ② 结果卡上的「🔁 换个风格」：四套风格循环重生成（复用现有引擎旋钮，不另造引擎） */

/* 产品 → 品牌（用于"品牌 + 品类词"这种粗粒度命中，如「海蓝之谜精粹水」） */
const QA_BRAND = {
  'SK-II 神仙水':'sk-ii',
  '雅诗兰黛小棕瓶精华第七代':'雅诗兰黛', '雅诗兰黛紧致眼霜':'雅诗兰黛', '雅诗兰黛DW持妆粉底液':'雅诗兰黛',
  '赫莲娜绿宝瓶精华':'赫莲娜',
  '海蓝之谜经典面霜':'海蓝之谜',
  '纪梵希四宫格散粉':'纪梵希',
  'MAC子弹头口红':'mac',
  '植村秀砍刀眉笔':'植村秀',
  '兰蔻浓密卷翘睫毛膏':'兰蔻',
  '迪奥真我女士香水':'迪奥',
  '香奈儿五号经典香水':'香奈儿',
  '祖·玛珑蓝风铃香水':'祖玛珑',
  '梅森马吉拉慵懒周末香水':'梅森马吉拉',
  '爱马仕尼罗河花园香水':'爱马仕',
  '獭祭纯米大吟酿清酒':'獭祭',
  '奔富BIN389红酒':'奔富',
  '上海女人雪花膏礼盒':'上海女人'
};
/* 常见昵称 → 产品全名（只写"名字里没有的那部分"说法） */
const QA_PROD_ALIAS = {
  '小棕瓶':'雅诗兰黛小棕瓶精华第七代',
  '神仙水':'SK-II 神仙水',
  '绿宝瓶':'赫莲娜绿宝瓶精华',
  '四宫格':'纪梵希四宫格散粉',
  '子弹头':'MAC子弹头口红',
  '砍刀眉笔':'植村秀砍刀眉笔',
  '蓝风铃':'祖·玛珑蓝风铃香水',
  '真我':'迪奥真我女士香水',
  '五号':'香奈儿五号经典香水',
  '尼罗河':'爱马仕尼罗河花园香水',
  '慵懒周末':'梅森马吉拉慵懒周末香水',
  '泡腾片':'维生素C泡腾片',
  '护肝片':'水飞蓟护肝片',
  '褪黑素':'褪黑素软糖',
  '燕窝':'即食燕窝饮品',
  '高丽参':'高丽参补气茶',
  '大飞机模型':'典藏大飞机模型1:100',
  '飞机模型':'典藏大飞机模型1:100',
  '颈枕':'云端好梦·颈枕套装',
  '雪花膏':'上海女人雪花膏礼盒',
  '冰箱贴':'长空万里冰箱贴·云端丝路',
  '毛绒玩具':'春秋航空飞机毛绒玩具',
  '盲盒':'飞行奇遇记毛绒挂件盲盒'
};
/* 问法里可以忽略的填充词（用于判断"他就是在说这个产品"） */
const QA_FILLER = ['帮我','给我','麻烦','来一段','来一份','来','要','写','生成','编','一段','一份','一下','个','的','话术','稿子','台词','文案','推销词','销售词','推荐','介绍','讲讲','说说','怎么讲','怎么说','怎么卖','怎么推','销售','推销','产品','这款','它','请','你'];

function qaNormName(s){
  return String(s == null ? '' : s).toLowerCase().replace(/[\\s·・\\-—_,，。、；;：:！!？?（）()【】\\[\\]"'“”‘’]/g, '');
}
function qaProductIndex(){
  const out = [];
  SCRIPT_CATS.forEach(function(c){
    (c.items || []).forEach(function(p){ out.push({ p:p, cat:c, norm:qaNormName(p.n) }); });
  });
  return out;
}
/* 命中打分：整名 100 > 昵称 80 > 品牌 45（+品类词 25 +角色词 15） */
function qaMatchProducts(text){
  const raw = String(text || '');
  const t = qaNormName(raw);
  if(!t) return [];
  const out = [];
  qaProductIndex().forEach(function(e){
    let score = 0, hit = 0;
    if(t.indexOf(e.norm) >= 0){ score = 100; hit = e.norm.length; }
    else {
      for(const al in QA_PROD_ALIAS){
        if(QA_PROD_ALIAS[al] !== e.p.n) continue;
        if(t.indexOf(qaNormName(al)) >= 0){ score = Math.max(score, 80); hit = Math.max(hit, qaNormName(al).length); }
      }
      const bd = qaNormName(QA_BRAND[e.p.n] || '');
      if(bd && t.indexOf(bd) >= 0){ score = Math.max(score, 45); hit = Math.max(hit, bd.length); }
      const tp = qaNormName(e.p.t);
      if(tp && t.indexOf(tp) >= 0 && score > 0){ score += 25; hit = Math.max(hit, tp.length); }
      const mp = qaNormName(e.p.m);
      if(mp && t.indexOf(mp) >= 0 && score > 0){ score += 15; }
    }
    if(score > 0) out.push({ p:e.p, cat:e.cat, score:score, hit:hit });
  });
  out.sort(function(a, b){ return b.score - a.score || b.hit - a.hit; });
  return out;
}
/* 把产品名/昵称/品类词从问句里剥掉，剩下的字才算"额外诉求" */
function qaLeftover(text, e){
  let t = qaNormName(text);
  const cut = [qaNormName(e.p.n), qaNormName(e.p.t), qaNormName(e.p.m), qaNormName(QA_BRAND[e.p.n] || '')];
  for(const al in QA_PROD_ALIAS){ if(QA_PROD_ALIAS[al] === e.p.n) cut.push(qaNormName(al)); }
  cut.forEach(function(x){ if(x) t = t.split(x).join(''); });
  QA_FILLER.forEach(function(x){ t = t.split(x).join(''); });
  return t;
}
/* 是否属于"给这个产品出话术"（2026-09-19 v2）
   实测 v1 的"剩余词"规则把用户原话「海蓝之谜精粹水」这类「品牌+品类词」挡住了 → 不出稿。
   改为黑名单：出现"求知类字眼"（成分/功效/规定/多少…）就让给知识库，其余一律出稿。 */
const QA_KB_ASK = /(成分|功效|作用|适用|区别|差别|怎么用|用法|多少钱|价格|报价|为什么|为何|是否|能不能|可不可以|有没有|哪一|哪里|哪个|什么时候|几时|多久|多少|规定|标准|条款|依据|出处|手册|条件|要求)/;
function qaIsProductScript(text){
  const raw = String(text || '');
  if (/(写|生成|编|来|要|给|帮我|我要).{0,4}(销售话术|话术|稿子|台词|推销词|销售词)/.test(raw)) return null;  // 没点产品 → 走向导
  if (QA_KB_ASK.test(raw)) return null;                 // 求知类问法优先走知识库，不抢答
  const hits = qaMatchProducts(raw);
  if(!hits.length) return null;
  const e = hits[0];
  if(e.score < 45) return null;
  return e;
}

/* 四套风格：复用现有引擎的 形式(style) / 定位(budget) / 时长(dura) 三个旋钮 */
const SCRIPT_STYLE_CYCLE = [
  { k:'guide-mid',  label:'🗣 定向推荐（一对一 · 稳妥款）', patch:{ style:'guide', budget:'mid',  dura:'5' } },
  { k:'talk',       label:'📢 广播·脱口秀（面向全舱 · 段子金句）', patch:{ style:'talk',  budget:'mid',  dura:'5' } },
  { k:'guide-high', label:'💎 高端定位（主打奢牌质感）', patch:{ style:'guide', budget:'high', dura:'5' } },
  { k:'guide-low',  label:'💰 性价比路线（快速促单）', patch:{ style:'guide', budget:'low',  dura:'3' } }
];
function qaStyleLabel(idx){
  const s = SCRIPT_STYLE_CYCLE[(idx || 0) % SCRIPT_STYLE_CYCLE.length];
  return s ? s.label : '';
}
/* 出稿 HTML（渲染与换风格共用，保证两条路径产出完全一致） */
function qaScriptHtml(cfg){
  let out = '';
  try{ out = (cfg.style === 'talk') ? buildTalkScript(cfg) : buildScript(cfg); }
  catch(e){ out = '生成失败：' + String((e && e.message) || e); }
  const title = (cfg.products && cfg.products.length)
    ? ('「' + esc(cfg.products[0]) + '」话术稿')
    : '话术稿生成结果';
  return '<div class="qa-script-wrap">'
    + '<div class="qa-title"><span class="qi">📄</span><span>' + title + '</span></div>'
    + '<div class="qa-script-style" style="font-size:.74rem;color:var(--text2);margin:-2px 0 6px">当前风格：' + esc(qaStyleLabel(cfg.styleIdx)) + '</div>'
    + '<div class="script-out">' + esc(out) + '</div>'
    + '<div class="act-row">'
    +   '<button class="cp-btn" onclick="copyScript(this)">📋 复制全文</button>'
    +   '<button class="cp-btn" onclick="qaScriptNextStyle(this)" title="对当前稿不满意？换一版风格重新生成">🔁 换个风格</button>'
    +   '<button class="jump-btn" onclick="jumpTo(\\'beauty\\')">💄 去美妆话术生成完整版 ➔</button>'
    + '</div></div>';
}
/* 统一出稿渲染：向导路径 / 产品名直触发 / 换个风格 都走这里 */
function qaRenderScript(cfg, opts){
  addMsg('bot', qaScriptHtml(cfg), { answer:true, q:'' });
  // 记住这条消息在会话里的位置：换风格时改写它的持久化副本（刷新后仍是新版本）
  window.__qaLastScript = { cfg: cfg, idx: chat.msgs.length - 1 };
  renderChat();
}
/* 换个风格：整条消息替换（含 chat.msgs），不刷屏。
   ⚠️ v1 只改 DOM，随后的 renderChat() 会用 chat.msgs 里的旧 HTML 覆盖回去（实测被覆盖）。 */
function qaScriptNextStyle(btn){
  const st = window.__qaLastScript;
  if(!st || !st.cfg){ return; }
  const next = ((st.cfg.styleIdx || 0) + 1) % SCRIPT_STYLE_CYCLE.length;
  const cfg = Object.assign({}, st.cfg, SCRIPT_STYLE_CYCLE[next].patch);
  cfg.styleIdx = next;
  const html = qaScriptHtml(cfg);
  window.__qaLastScript = { cfg: cfg, idx: st.idx };
  try{
    if(chat.msgs[st.idx]){ chat.msgs[st.idx].html = html; chat.msgs[st.idx].raw = html; }
  }catch(e){}
  renderChat();
  if(typeof qaToast === 'function') qaToast('🔁 已换成：' + SCRIPT_STYLE_CYCLE[next].label);
}
/* 产品名直触发入口 */
function qaProductScript(e){
  const cfg = {
    cats:[e.cat.key], dura:'5', budget:'mid', style:'guide', time:'auto', fest:'auto', topic:'',
    products:[e.p.n], styleIdx:0
  };
  addMsg('bot', '<div class="kbox">🧴 已识别产品：<b>' + esc(e.p.n) + '</b>（' + esc(e.cat.label) + '）'
    + (e.p.m ? ' · 主打' + esc(e.p.m) : '') + '。下面按当前风格给您出一版话术，不满意点「🔁 换个风格」。</div>');
  qaRenderScript(cfg, { product:true });
}
'''

# ---------------- W4：路由（process 里接管产品名问法） ----------------
ROUTE_OLD = u"""  if (intent === 'script'){ startWizard(); return; }"""
ROUTE_NEW = u"""  if (intent === 'script'){ startWizard(); return; }
  // 话术向导增强（2026-09-19）：直接报产品名 / 产品名+要话术 → 不用走向导，直接出稿
  const pq = qaIsProductScript(text);
  if (pq){ qaProductScript(pq); return; }"""

# ---------------- W5：入口提示 + 快捷问法 ----------------
PH_OLD = u'placeholder="问点什么？比如：病假怎么请 / 帮我写一段销售话术…"'
PH_NEW = u'placeholder="问点什么？比如：病假怎么请 / 雅诗兰黛小棕瓶 / 帮我写一段销售话术…"'
CHIP_OLD = u"""  { ic:'📝', tl:'写销售话术', st:'选品类+时长出稿', q:'帮我写一段销售话术稿子' },"""
CHIP_NEW = u"""  { ic:'📝', tl:'写销售话术', st:'选品类+时长出稿', q:'帮我写一段销售话术稿子' },
  { ic:'🧴', tl:'按产品名出话术', st:'说名字就给稿', q:'雅诗兰黛小棕瓶' },"""



# ---------------- W6：向导出稿统一走 qaRenderScript（带「换个风格」） ----------------
DOGEN_OLD = u'''async function doGenerate(){
  if(!wizard.cats.length){ return; }
  const out = (wizard.style === 'talk') ? buildTalkScript(wizard) : buildScript(wizard);
  wizard.active = false;
  addMsg('bot', `<div style="word-break:break-word"><div class="qa-title"><span class="qi">📄</span><span>话术稿生成结果（可复制到剪贴板）</span></div>
    <div class="script-out">${esc(out)}</div>
    <div class="act-row">
      <button class="cp-btn" onclick="copyScript(this)">📋 复制全文</button>
      <button class="jump-btn" onclick="jumpTo('beauty')">💄 去美妆话术生成完整版 ➔</button>
    </div></div>`);
  renderChat();
}'''

DOGEN_NEW = u'''async function doGenerate(){
  if(!wizard.cats.length){ return; }
  /* 2026-09-19：向导出稿统一走 qaRenderScript —— 与"产品名直触发"同一条渲染路径，
     于是向导出稿同样带「🔁 换个风格」按钮，且换版会改写会话里的这条消息。 */
  const cfg = {
    cats: wizard.cats.slice(), dura: wizard.dura, budget: wizard.budget, style: wizard.style,
    time: wizard.time || 'auto', fest: wizard.fest || 'auto', topic: wizard.topic || '',
    products: (wizard.products && wizard.products.length) ? wizard.products.slice() : null,
    styleIdx: (wizard.style === 'talk') ? 1 : 0        // 手选广播稿 → 当前风格即第 2 套，换风格从下一套起
  };
  wizard.active = false; wizard.products = null;
  qaRenderScript(cfg, { fromWizard:true });
}'''

def main():
    if not os.path.exists(QA):
        print(u'[ERR] 找不到 qa.html')
        return 1
    s = rd(QA)
    print(u'[in] qa.html %d 字符  marker=%s' % (len(s), MARK in s))
    if MARK in s:
        print(u'[skip] 已注入过（幂等）')
        return 0
    if not os.path.exists(BAK):
        shutil.copy2(QA, BAK)
        print(u'[bak] -> %s' % os.path.basename(BAK))

    s = sub_once(s, TALK_OLD, TALK_NEW, u'buildTalkScript 产品过滤')
    s = sub_once(s, BS_HEAD_OLD, BS_HEAD_NEW, u'buildScript 产品过滤')
    s = sub_once(s, BS_S1_OLD, BS_S1_NEW, u'buildScript 卖点段')
    s = sub_once(s, BS_S2_OLD, BS_S2_NEW, u'buildScript 搭配段')

    # W3：新代码块插到 copyScript 之前（同一作用域，函数声明会提升）
    anchor = u'function copyScript(btn){'
    if s.count(anchor) != 1:
        raise SystemExit(u'[ERR] copyScript 锚点异常')
    s = s.replace(anchor, WIZ2_BLOCK + anchor, 1)

    s = sub_once(s, DOGEN_OLD, DOGEN_NEW, u'doGenerate 统一渲染')

    # W4：路由接管
    s = sub_once(s, ROUTE_OLD, ROUTE_NEW, u'process 路由')
    # W5：入口提示 + 快捷问法
    s = sub_once(s, PH_OLD, PH_NEW, u'输入框 placeholder')
    s = sub_once(s, CHIP_OLD, CHIP_NEW, u'CHIPS 产品名示例')

    # 变量提升守卫：doGenerate 已存在；新增函数必须都在同一 <script> 内
    checks = {
        u'新块 1 份': s.count(MARK) == 1,
        u'产品匹配函数': u'function qaMatchProducts(' in s,
        u'换个风格入口': u'function qaScriptNextStyle(' in s and u'qaScriptNextStyle(this)' in s,
        u'风格表 4 套': s.count(u"k:'guide-mid'") == 1 and s.count(u"k:'talk',") >= 1 and s.count(u"k:'guide-high'") == 1 and s.count(u"k:'guide-low'") == 1,
        u'引擎产品过滤': u'const only = (cfg.products && cfg.products.length) ? cfg.products : null;' in s,
        u'路由接管': u'const pq = qaIsProductScript(text);' in s,
        u'向导出稿走统一渲染': u'qaRenderScript(cfg, { fromWizard:true });' in s,
        u'placeholder 示例': u'雅诗兰黛小棕瓶 / 帮我写一段销售话术' in s,
        u'script 标签平衡': s.count(u'<script') == s.count(u'</script>'),
        u'html 闭合 1 份': s.count(u'</html>') == 1,
    }
    fails = [k for k, v in checks.items() if not v]
    for k, v in checks.items():
        print(u'  [%s] %s' % (u'OK' if v else u'NG', k))
    if fails:
        print(u'!! 自检失败 %d 项，未写盘' % len(fails))
        return 1
    wr(QA, s)
    print(u'[ok] qa.html %d -> %d 字符' % (len(rd(BAK)), len(s)))
    return 0


if __name__ == '__main__':
    if '--check' in sys.argv:
        s = rd(QA)
        ok = MARK in s and u'function qaScriptNextStyle(' in s and u'const pq = qaIsProductScript(text);' in s
        print(u'[check] 话术向导增强：%s' % (u'OK' if ok else u'FAIL'))
        raise SystemExit(0 if ok else 1)
    raise SystemExit(main())
