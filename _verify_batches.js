/* 批次数据校验器：按 _prod_batches/SPEC.md 检查所有 batch*.json
 * 用法：node _verify_batches.js
 */
'use strict';
const fs = require('fs');
const path = require('path');

const DIR = path.join(__dirname, '_prod_batches');
const FILES = fs.readdirSync(DIR).filter(f => /^batch\d+.*\.json$/.test(f) && !/tales/.test(f)).sort();

const CATS = new Set(['洁面','卸妆','化妆水','精华水','精华','眼霜','眼膜','面霜','乳液','防晒','面膜','护手霜','身体护理','唇部护理',
  '洗发水','护发素','护发精油','发膜','染发','粉底液','口红','隔离','彩妆','香水','保健品','酒','清酒','红酒','梅子酒','烧酒','纪念品']);
const PREQ = ['id','name','brand','category','tale','volume','origin','stock','description','coreBenefits','targetSkinTypes','keyIngredients','unsuitable','tags','reviewCount'];
const CREQ = ['id','name','brand','category','prices','ingredients','advantages','disadvantages','complianceNote','updateTime'];
const SCATS = new Set(['informationInquiry','priceObjection','priceNegotiation','effectivenessDoubt','hesitationHandling','trustBuilding',
  'authenticityGuarantee','stockUncertainty','returnShipping','chineseLabel','noReviewsOnPlane','problemSolving','emotionalSupport',
  'souvenirValue','souvenirQuality','souvenirGift']);

const BAN = ['治疗','治愈','100%','永久','根治','秒杀','碾压','全网最低','最低价','最便宜','手慢无','错过就没有','比专柜','比代购','比免税',
  '药到病除','无副作用','绝对','唯一','宣称','承诺','顶级','立竿见影','最具标志性','医美','水光针','热玛吉','干细胞','排毒','消炎','杀菌','注射','填充','医疗'];
// 软性绝对化：用正则避免「第一步/第一次/第一代/第一层」这类正常用法误报
const SOFT_RE = [
  [/第(?!.{0,2}(步|次|代|层|重|件|时间|款|个|位|支|瓶|罐|盒|条|颗|片|门|印象|反应|感觉|要素|件事|天|夜|周|月|年|回|遍|句|口|眼|下|招|课|章|节|页|桶|道|序|念|序曲|瓶装))一/, '第一'],
  [/最好/, '最好'], [/最佳/, '最佳'], [/独家/, '独家'], [/国家级/, '国家级'],
  [/功效显著/, '功效显著'], [/彻底解决/, '彻底解决'], [/销量冠军/, '销量冠军'], [/行业领先/, '行业领先'],
];

const problems = [];
const warns = [];
const allIds = new Map();
const allCats = new Map();
let nP = 0, nC = 0, nS = 0;

function scanText(where, t) {
  BAN.forEach(w => { if (t.indexOf(w) >= 0) problems.push(where + ' 命中违禁词「' + w + '」'); });
  SOFT_RE.forEach(([re, label]) => { if (re.test(t)) warns.push(where + ' 含软性绝对化「' + label + '」: ' + (t.match(re) ? '' : '')); });
}

FILES.forEach(f => {
  const j = JSON.parse(fs.readFileSync(path.join(DIR, f), 'utf8'));
  const tag = f;
  (j.products || []).forEach(p => {
    nP++;
    const miss = PREQ.filter(k => p[k] === undefined || p[k] === null || (Array.isArray(p[k]) && k !== 'unsuitable' && !p[k].length));
    if (miss.length) problems.push(tag + ' ' + p.id + ' 缺字段: ' + miss.join('/'));
    if (p.category && !CATS.has(p.category)) problems.push(tag + ' ' + p.id + ' 品类不在白名单: ' + p.category);
    if (p.reviewCount !== undefined && !(p.reviewCount > 0)) problems.push(tag + ' ' + p.id + ' reviewCount 非法');
    (p.keyIngredients || []).forEach((k, i) => { if (!k.commonName || !k.mechanism) problems.push(tag + ' ' + p.id + ' keyIngredients[' + i + '] 缺项'); });
    (p.unsuitable || []).forEach((u, i) => { if (!u.type || !u.reason) problems.push(tag + ' ' + p.id + ' unsuitable[' + i + '] 缺项'); });
    const t = p.tale || '';
    if (t.length < 15) problems.push(tag + ' ' + p.id + ' tale 过短(' + t.length + ')');
    if (t.length > 160) warns.push(tag + ' ' + p.id + ' tale 偏长(' + t.length + ')');
    scanText(tag + ' ' + p.id + ' tale', t);
    scanText(tag + ' ' + p.id + ' desc', p.description || '');
    scanText(tag + ' ' + p.id + ' benefits', (p.coreBenefits || []).join(' '));
    scanText(tag + ' ' + p.id + ' targets', (p.targetSkinTypes || []).join(' '));
    if (allIds.has(p.id)) problems.push('重复 id: ' + p.id + '（' + allIds.get(p.id) + ' 与 ' + tag + '）');
    allIds.set(p.id, tag);
    if (p.category) allCats.set(p.category, (allCats.get(p.category) || 0) + 1);
  });
  (j.competitors || []).forEach(c => {
    nC++;
    const miss = CREQ.filter(k => c[k] === undefined || c[k] === null || (Array.isArray(c[k]) && !c[k].length));
    if (miss.length) problems.push(tag + ' ' + c.id + ' 缺字段: ' + miss.join('/'));
    if (c.category && !CATS.has(c.category)) problems.push(tag + ' ' + c.id + ' 品类不在白名单: ' + c.category);
    if (!/[(（].+[)）]/.test(c.brand || '')) warns.push(tag + ' ' + c.id + ' 竞品 brand 未带英文名: ' + c.brand);
    (c.prices || []).forEach((pr, i) => {
      if (!pr.platform || !pr.size || typeof pr.price !== 'number' || pr.price <= 0 || !pr.updateTime) {
        problems.push(tag + ' ' + c.id + ' prices[' + i + '] 字段/数值非法');
      }
      if (pr.note && pr.note.indexOf('2026-09 联网价') < 0) warns.push(tag + ' ' + c.id + ' prices[' + i + '] note 未标注联网口径');
    });
    scanText(tag + ' ' + c.id + ' comp', (c.advantages || []).join(' ') + ' ' + (c.disadvantages || []).join(' '));
    if (allIds.has(c.id)) problems.push('重复 id: ' + c.id);
    allIds.set(c.id, tag);
  });
  (j.scriptEntries || []).forEach((s, i) => {
    nS++;
    if (!SCATS.has(s.category)) problems.push(tag + ' scriptEntries[' + i + '] 分类非法: ' + s.category);
    if (!s.content || s.content.length < 20) problems.push(tag + ' scriptEntries[' + i + '] content 过短');
    if (!s.tags || !s.tags.length) problems.push(tag + ' scriptEntries[' + i + '] 缺 tags');
    scanText(tag + ' script[' + s.category + ']', s.content || '');
  });
  console.log(f, '→ P:' + (j.products || []).length, 'C:' + (j.competitors || []).length, 'S:' + (j.scriptEntries || []).length);
});

console.log('\n合计 商品 ' + nP + ' / 竞品 ' + nC + ' / 话术 ' + nS + ' / 唯一 id ' + allIds.size);
console.log('品类覆盖: ' + JSON.stringify([...allCats.entries()].sort((a, b) => b[1] - a[1])));
if (warns.length) { console.log('\n--- 提醒（' + warns.length + '）---'); warns.slice(0, 40).forEach(w => console.log('  ! ' + w)); if (warns.length > 40) console.log('  ... 其余 ' + (warns.length - 40) + ' 条'); }
if (problems.length) { console.log('\n--- 硬伤（' + problems.length + '）---'); problems.slice(0, 60).forEach(p => console.log('  X ' + p)); process.exit(1); }
console.log('\n批次校验通过。');
