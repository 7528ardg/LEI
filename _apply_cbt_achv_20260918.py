# -*- coding: utf-8 -*-
"""成就系统扩展（CBT 练习题库专项，2026-09-18 v2）

对应培训考核的**独立特殊分类「CBT练习」**（cbt_题库_785题.csv 的 785 题：普通 719 / 321 机型 66）。
题库条目字段约定（见 _apply_cbt_bank_20260918.py）：
  src='cbt'、manual='cbt'、chapter='CBT练习·普通题目'|'CBT练习·321机型题'、cbtCh=CBT 十类细目
本脚本只依赖 src / cbtCh / section，不与 chapter 显示名耦合。

新增：分类 tab「CBT题库」+ 15 枚成就 + 7 个进度类型 + 6 个统计 helper。

幂等：四个补丁块各自带 BEGIN/END 标记，重跑时**先整体剥离再按锚点重插**，
      因此改动本脚本内容后直接重跑即可生效（无需手工清理旧块）。

用法：python _apply_cbt_achv_20260918.py            # 执行
      python _apply_cbt_achv_20260918.py --check    # 校验（不一致则非零退出）
"""
import io, os, re, sys, shutil

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
QUIZ = os.path.join(HERE, 'quiz.html')

AE = '/* CBT_ACHV_END */'
AB_BADGES = '/* CBT_ACHV_BADGES_BEGIN（_apply_cbt_achv_20260918.py 注入；改动请改脚本后重跑） */'
AB_HELPER = '/* CBT_ACHV_HELPER_BEGIN（_apply_cbt_achv_20260918.py 注入；改动请改脚本后重跑） */'
AB_PROG = '/* CBT_ACHV_PROG_BEGIN（_apply_cbt_achv_20260918.py 注入；改动请改脚本后重跑） */'
AB_UNLOCK = '/* CBT_ACHV_UNLOCK_BEGIN（_apply_cbt_achv_20260918.py 注入；改动请改脚本后重跑） */'
ACHV_RE = re.compile(r'/\* CBT_ACHV_[A-Z_]*BEGIN[^\n]*\*/\n[\s\S]*?/\* CBT_ACHV_END \*/')

CAT_ANCHOR = "{id:'coverage',label:'章节覆盖',icon:'🌐'},"
CAT_NEW = CAT_ANCHOR + "\n  {id:'cbt',label:'CBT题库',icon:'🎯'},"

HELPER_ANCHOR = '/* ===== 按题干关键词统计累计答对的题数 ===== */'
HELPER_BODY = """
/* ===== CBT 练习题库成就统计（2026-09-18）
   培训考核 · 独立特殊分类「CBT练习」= cbt_题库_785题：src==='cbt'；
   chapter 为 CBT练习·普通题目 / CBT练习·321机型题；cbtCh 为 CBT 十类细目
   （第一章 概述 … 第八章 附录 / 无解析 / 321机型补充）。 ===== */
const isCbtQ = q => !!(q && q.src === 'cbt');
const cbtChOf = q => String((q && (q.cbtCh || q.chapter)) || '');
function _countCorrect(pred){
  if(!APP.history || !APP.history.length) return 0;
  const seen = new Set();
  APP.history.forEach(h=>{
    if(!h.questions || !h.answers) return;
    h.questions.forEach((idx, i)=>{
      if(seen.has(idx)) return;
      const ans = h.answers[i];
      if(ans === undefined || ans === null) return;
      const q = APP.questions[idx];
      if(!q || !pred(q)) return;
      if(checkAnswer(q, ans)) seen.add(idx);
    });
  });
  return seen.size;
}
function getCbtCorrect(grp){
  if(grp === '321')  return _countCorrect(q => isCbtQ(q) && cbtChOf(q) === '321机型补充');
  if(grp === '普通') return _countCorrect(q => isCbtQ(q) && cbtChOf(q) !== '321机型补充');
  return _countCorrect(isCbtQ);
}
/* 答对某个 CBT 细目（第一章 概述 … 无解析 / 321机型补充）的题数 */
function getCbtChCorrect(ch){
  return _countCorrect(q => isCbtQ(q) && cbtChOf(q) === ch);
}
/* 答对「带精确手册章节号」的题数（解析可回溯到手册 1.1.1 形式章节，仅统计 CBT 练习题库） */
function getCorrectWithSection(){
  return _countCorrect(q => isCbtQ(q) && !!q.section && /^\\d+\\.\\d+/.test(String(q.section)));
}
/* 练到过的 CBT 细目数（含 无解析 / 321机型补充，共 10 类） */
function getCbtChaptersPracticed(){
  const s = new Set();
  (APP.history||[]).forEach(h=>{
    (h.questions||[]).forEach(idx=>{
      const q = APP.questions[idx];
      if(isCbtQ(q) && cbtChOf(q)) s.add(cbtChOf(q));
    });
  });
  return s.size;
}
/* 完成过 CBT 题库题目的模拟考次数 */
function getCbtExamCount(){
  return (APP.history||[]).filter(h =>
    h.mode === 'exam' && (h.questions||[]).some(idx => isCbtQ(APP.questions[idx]))
  ).length;
}
"""

PROG_ANCHOR_HEAD = "    return Math.min(today/badge.target*100, 100);\n  }\n"
PROG_ANCHOR_TAIL = "  return 0;\n}"
PROG_BODY = """
  if(t==='cbt_correct') return Math.min(getCbtCorrect('全部')/badge.target*100, 100);
  if(t==='cbt_normal_correct') return Math.min(getCbtCorrect('普通')/badge.target*100, 100);
  if(t==='cbt321_correct') return Math.min(getCbtCorrect('321')/badge.target*100, 100);
  if(t==='sec_correct') return Math.min(getCorrectWithSection()/badge.target*100, 100);
  if(t==='noana_correct') return Math.min(getCbtChCorrect('无解析')/badge.target*100, 100);
  if(t==='cbt_chapters') return Math.min(getCbtChaptersPracticed()/badge.target*100, 100);
  if(t==='cbt_exam') return Math.min(getCbtExamCount()/badge.target*100, 100);
"""

UNLOCK_ANCHOR = "  // ===== 终极 ====="
UNLOCK_BODY = """
  // ===== CBT 练习题库专项（2026-09-18，对应培训考核「CBT练习」独立分类） =====
  const cbtAll = getCbtCorrect('全部');
  const cbtN   = getCbtCorrect('普通');
  const cbt321 = getCbtCorrect('321');
  const cbtSec = getCorrectWithSection();
  if(cbtAll >= 5)    tryUnlock('cbt_first');
  if(cbtAll >= 100)  tryUnlock('cbt_100');
  if(cbtAll >= 500)  tryUnlock('cbt_500');
  if(cbtN   >= 300)  tryUnlock('cbt_normal300');
  if(cbt321 >= 5)    tryUnlock('cbt_321_first');
  if(cbt321 >= 30)   tryUnlock('cbt_321_30');
  if(cbt321 >= 66)   tryUnlock('cbt_321_all');
  if(cbtSec >= 50)   tryUnlock('cbt_sec50');
  if(cbtSec >= 200)  tryUnlock('cbt_sec200');
  if(getCbtChCorrect('无解析') >= 10) tryUnlock('cbt_noana10');
  if(getCbtChaptersPracticed() >= 5)  tryUnlock('cbt_chap5');
  if(getCbtChaptersPracticed() >= 10) tryUnlock('cbt_chap_all');
  if(getCbtExamCount() >= 1) tryUnlock('cbt_exam1');
  if(getCbtExamCount() >= 3) tryUnlock('cbt_exam3');
  // 一次 CBT 练习（≥10 题）全对
  const _cq = APP.quiz;
  if(_cq && seriousSession && correct === total && total >= 10 && (()=>{
        const idxs = _cq.indices || [];
        return idxs.length > 0 && idxs.every(i => isCbtQ(APP.questions[i]));
      })()) tryUnlock('cbt_perfect');
"""

BADGES_BODY = """  /* ===== CBT 练习题库专项（2026-09-18；培训考核「CBT练习」独立分类 = cbt_题库_785题） ===== */
  {id:'cbt_first',cat:'cbt',rarity:'common',points:8,name:'CBT 启航',desc:'答对 5 道 CBT 练习题库题',icon:'🎯',target:5,type:'cbt_correct',unlocked:false},
  {id:'cbt_100',cat:'cbt',rarity:'uncommon',points:14,name:'CBT 百题',desc:'答对 100 道 CBT 练习题库题',icon:'📗',target:100,type:'cbt_correct',unlocked:false},
  {id:'cbt_500',cat:'cbt',rarity:'rare',points:28,name:'CBT 题海',desc:'答对 500 道 CBT 练习题库题',icon:'📚',target:500,type:'cbt_correct',unlocked:false},
  {id:'cbt_normal300',cat:'cbt',rarity:'rare',points:24,name:'普通题通关',desc:'答对 300 道 CBT 普通题（非 321 机型）',icon:'🧭',target:300,type:'cbt_normal_correct',unlocked:false},
  {id:'cbt_321_first',cat:'cbt',rarity:'uncommon',points:14,name:'321 起步',desc:'答对 5 道 321 机型题',icon:'🛩',target:5,type:'cbt321_correct',unlocked:false},
  {id:'cbt_321_30',cat:'cbt',rarity:'rare',points:26,name:'321 专精',desc:'答对 30 道 321 机型题',icon:'✈️',target:30,type:'cbt321_correct',unlocked:false},
  {id:'cbt_321_all',cat:'cbt',rarity:'epic',points:60,name:'321 机型通',desc:'答对全部 66 道 321 机型题',icon:'🏅',target:66,type:'cbt321_correct',unlocked:false},
  {id:'cbt_sec50',cat:'cbt',rarity:'uncommon',points:16,name:'手册可追溯',desc:'答对 50 道带精确手册章节号的 CBT 题',icon:'🔖',target:50,type:'sec_correct',unlocked:false},
  {id:'cbt_sec200',cat:'cbt',rarity:'rare',points:30,name:'章节号如数家珍',desc:'答对 200 道带精确手册章节号的 CBT 题',icon:'🗂',target:200,type:'sec_correct',unlocked:false},
  {id:'cbt_noana10',cat:'cbt',rarity:'uncommon',points:18,name:'疑难克星',desc:'答对 10 道「无解析」题（手册无对应正文）',icon:'❓',target:10,type:'noana_correct',unlocked:false},
  {id:'cbt_chap5',cat:'cbt',rarity:'uncommon',points:16,name:'五章贯通',desc:'在 CBT 练习题库中练过 5 个章节',icon:'🧩',target:5,type:'cbt_chapters',unlocked:false},
  {id:'cbt_chap_all',cat:'cbt',rarity:'rare',points:32,name:'十门全通',desc:'在 CBT 练习题库中练过全部 10 个章节',icon:'🌐',target:10,type:'cbt_chapters',unlocked:false},
  {id:'cbt_exam1',cat:'cbt',rarity:'common',points:10,name:'CBT 首考',desc:'完成 1 次 CBT 练习题库模拟考',icon:'📝',target:1,type:'cbt_exam',unlocked:false},
  {id:'cbt_exam3',cat:'cbt',rarity:'uncommon',points:18,name:'CBT 三连考',desc:'完成 3 次 CBT 练习题库模拟考',icon:'🗒',target:3,type:'cbt_exam',unlocked:false},
  {id:'cbt_perfect',cat:'cbt',rarity:'rare',points:26,name:'CBT 满堂红',desc:'单次 CBT 练习（≥10 题）全部答对',icon:'💯',target:10,type:'cbt_correct',unlocked:false},
"""


def find_array_end(s, start):
    depth = 0; i = start; in_str = None
    while i < len(s):
        c = s[i]
        if in_str:
            if c == '\\': i += 2; continue
            if c == in_str: in_str = None
            i += 1; continue
        if c in '"\'`': in_str = c; i += 1; continue
        if c == '[': depth += 1
        elif c == ']':
            depth -= 1
            if depth == 0: return i
        i += 1
    return -1


def block(marker, body):
    return marker + '\n' + body.rstrip('\n') + '\n' + AE


def existing_blocks(s):
    """返回 [(start, end, site)]；site ∈ badges/helper/prog/unlock，按块后紧跟的内容判定。"""
    out = []
    for m in ACHV_RE.finditer(s):
        after = s[m.end():m.end() + 220].lstrip()
        if after.startswith(HELPER_ANCHOR[:26]):
            site = 'helper'
        elif after.startswith('// ===== 终极'):
            site = 'unlock'
        elif after.startswith('return 0;'):
            site = 'prog'
        else:
            site = 'badges'
        out.append((m.start(), m.end(), site))
    return out


def transform(s):
    n = 0
    # 1) 分类 tab
    if "{id:'cbt'" not in s:
        if CAT_ANCHOR not in s:
            raise SystemExit('!! 未找到 BADGE_CATEGORIES 锚点')
        s = s.replace(CAT_ANCHOR, CAT_NEW, 1); n += 1

    want = {'badges': block(AB_BADGES, BADGES_BODY),
            'helper': block(AB_HELPER, HELPER_BODY),
            'prog': block(AB_PROG, PROG_BODY),
            'unlock': block(AB_UNLOCK, UNLOCK_BODY)}

    # 2) 已存在的块：按块原位替换（不增删周边空白 → 幂等）
    found = set()
    for st, en, site in reversed(existing_blocks(s)):
        found.add(site)
        if s[st:en] != want[site]:
            s = s[:st] + want[site] + s[en:]; n += 1

    # 3) 缺失的块：按锚点插入
    if 'badges' not in found:
        st = s.find('const BADGES = [')
        if st < 0:
            raise SystemExit('!! 未找到 BADGES 数组')
        en = find_array_end(s, s.find('[', st))
        if en < 0:
            raise SystemExit('!! BADGES 数组未闭合')
        if not s[:en].rstrip().endswith(','):
            s = s[:en] + ',' + s[en:]; en += 1
        s = s[:en] + '\n' + want['badges'] + '\n' + s[en:]; n += 1

    if 'helper' not in found:
        if HELPER_ANCHOR not in s:
            raise SystemExit('!! 未找到 helper 锚点')
        s = s.replace(HELPER_ANCHOR, want['helper'] + '\n' + HELPER_ANCHOR, 1); n += 1

    if 'prog' not in found:
        i = s.find(PROG_ANCHOR_HEAD)
        j = s.find(PROG_ANCHOR_TAIL, i + len(PROG_ANCHOR_HEAD)) if i >= 0 else -1
        if i < 0 or j < 0:
            raise SystemExit('!! 未找到 getBadgeProgress 锚点')
        s = s[:i + len(PROG_ANCHOR_HEAD)] + want['prog'] + '\n' + s[j:]; n += 1

    if 'unlock' not in found:
        if UNLOCK_ANCHOR not in s:
            raise SystemExit('!! 未找到解锁规则锚点')
        s = s.replace(UNLOCK_ANCHOR, want['unlock'] + '\n' + UNLOCK_ANCHOR, 1); n += 1

    for need in ("'cbt_first'", "{id:'cbt'", 'function getCbtCorrect', "t==='cbt_correct'",
                 'cbtAll >= 5', 'getCbtChCorrect', AB_BADGES, AB_HELPER, AB_PROG, AB_UNLOCK):
        if need not in s:
            raise SystemExit('!! 补丁不完整，缺少：' + need[:44])
    if len(existing_blocks(s)) != 4:
        raise SystemExit('!! CBT 成就块数量异常（应为 4）')
    return s, n


def main():
    check = '--check' in sys.argv
    s = io.open(QUIZ, encoding='utf-8', newline='').read()
    out, n = transform(s)
    if check:
        if out == s:
            print('  quiz.html CBT成就 -> UP-TO-DATE'); return
        print('!! quiz.html CBT成就与脚本目标不一致'); sys.exit(1)
    if out == s:
        print('  quiz.html CBT成就 -> UP-TO-DATE（无需改动）'); return
    bak = os.path.join(HERE, 'quiz.bak_cbtachv_v2_20260918.html')
    if not os.path.exists(bak):
        shutil.copy2(QUIZ, bak); print('  备份 ->', os.path.basename(bak))
# __ATOMIC_WRITE_20260921__
    _tmp_w = (QUIZ) + ".tmp_write"
    with io.open(_tmp_w, "w", encoding="utf-8", newline="") as _f_w:
        _f_w.write(out)
    os.replace(_tmp_w, (QUIZ))
    print(f'  quiz.html CBT成就 应用 {n} 处补丁（{len(s)} -> {len(out)} chars）')


if __name__ == '__main__':
    main()
