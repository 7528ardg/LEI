# -*- coding: utf-8 -*-
"""销售板块 · 脱口秀话术 v2 注入（2026-09-18）

做两件事（均幂等）：
  1) 用单一来源 `_talkshow_engine_v2.js` 整块替换 beauty.html 的 talkShowEngine
     —— 破千篇一律（结构模板轮转 + 素材池扩容）、破“每款都讲历史故事”（故事配额）、
        去冒犯（禁语安全带）。
  2) 数据层精确替换：产品 tale / 话术库（vocab.lifeScenarios / scriptLibraryData /
     SKIN_SUB_TRANSITIONS / categorySpecificIntros）里的冒犯旅客与焦虑营销表述。

用法：python _apply_talkshow_v2_20260918.py            # 执行
      python _apply_talkshow_v2_20260918.py --check    # 校验（不一致则非零退出）
      python _apply_talkshow_v2_20260918.py --audit    # 仅扫描残留冒犯性表述（只读）
"""
import io, os, re, sys, shutil

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
BEAUTY = os.path.join(HERE, 'beauty.html')
SRC = os.path.join(HERE, '_talkshow_engine_v2.js')

BEGIN = '/* TALKSHOW_ENGINE_BEGIN（单一来源 _talkshow_engine_v2.js；改动请改该文件后重跑注入脚本） */'
END = '/* TALKSHOW_ENGINE_END */'
ENGINE_START = 'const talkShowEngine = (function(){'
ENGINE_END = 'window.talkShowEngine = talkShowEngine;'

# ---------- 数据层替换表（子串级；新文本一律不含 ASCII 引号，避免破坏 JS 字面量）----------
FIXES = [
    # —— D2（2026-09-18）：工作台 话术风格/生成模式 按钮行窄屏可换行，降低密度（min-width 保证按钮不被挤压）——
    ('<div class="flex gap-2">\n<button onclick="setScriptStyle(\'scene\')" class="flex-1 px-3 py-2 rounded-lg',
     '<div class="flex flex-wrap gap-2">\n<button onclick="setScriptStyle(\'scene\')" class="flex-1 min-w-[140px] px-3 py-2 rounded-lg'),
    ('<div class="flex gap-2">\n<button onclick="setComplianceMode(\'strict\')" class="flex-1 px-3 py-2 rounded-lg',
     '<div class="flex flex-wrap gap-2">\n<button onclick="setComplianceMode(\'strict\')" class="flex-1 min-w-[130px] px-3 py-2 rounded-lg'),
    # —— D1（2026-09-18）：重选「话术生成」页签时收起已生成结果卡，回到工作台（不再需要手动点"返回配置"）——
    ('            const scrollLeft = navScroll ? navScroll.scrollLeft : 0;\n            state.activeTab = id;',
     '            const scrollLeft = navScroll ? navScroll.scrollLeft : 0;\n            // D1(2026-09-18)重选「话术生成」页签时收起已生成结果卡，回到工作台\n            if (id === \'script\' && state.generatedScript && state.activeTab === \'script\') state.generatedScript = null;\n            state.activeTab = id;'),
    # —— 重复典故去重（estee-004 红石榴精华水 与 skin1-005 红石榴面霜共用同一句故事 → 面霜改写为本套装的收尾思路）——
    ('红石榴被挑中，是因为它的抗氧化力在水果里排得上前列——一颗果子憋着一整个夏天的太阳，用来对付暗沉正对口。这套把洁面、水、日霜晚霜凑齐，是想让你一天从清到养。',
     '这系列把洁面、水、日霜晚霜凑齐，为的是让一天从清洁到滋养都顺下来——晚霜放在睡前收尾，锁住前面几步，隔天起来脸上是润的。'),
    # —— 焦虑营销 / 评判旅客 ——
    ('很多旅客跟我说，出差最大的烦恼不是工作，是皮肤变差。在酒店照镜子看到自己暗沉的脸，心情都不好了。',
     '很多旅客跟我说，出差最影响状态的其实是作息：觉睡不好、水喝得少，皮肤也跟着闹情绪。所以在路上把基础护理做稳，比什么都实在。'),
    ('您说现在的人，哪个不是手机不离手、电脑不离眼？时间长了，蓝光伤害加上辐射，皮肤能好才怪。',
     '您说现在的人，哪个不是手机不离手、电脑不离眼？一天下来眼睛干、肩颈紧，皮肤也容易跟着发暗。所以日常的补水修护，也就更值得认真做。'),
    ('您有没有发现，同龄的人看起来年龄差很多？除了基因，就是护肤习惯的差别。坚持护肤的人，时间会给她回报。',
     '您有没有发现，同一个年纪的人，状态差别有时候挺明显？除了天生条件，日常习惯占的分量不小。肯在日常上花点心思的人，时间久了是看得出来的。'),
    ('现在这社会，第一印象太重要了。皮肤好的人，不化妆都显得精神。皮肤差的，化再浓的妆也遮不住。',
     '妆效好不好，跟妆前的底子关系很大：底子润，妆就服帖、气色也透；底子干，妆容易卡，怎么补都不太顺。所以打底这一步，值得认真挑。'),
    ('说真的，女人到了一定年龄，拼的不是谁有钱，是谁看起来更年轻。而看起来年轻的关键，就是皮肤状态。',
     '说真的，到了某个阶段，大家比的往往不是别的，而是谁的状态更稳。状态稳了，精神气自然就出来了——这也是日常护理最实际的价值。'),
    ('我跟您说个数据，25岁以后皮肤胶原蛋白每年流失1%，到了35岁就流失了10%。所以抗老真的要趁早。',
     '跟您说个常识：皮肤里的胶原蛋白会随年龄增长慢慢减少。所以基础护理和防护，早一点稳定下来，后面就省心一点。'),
    ('很多旅客跟我说，她们在飞机上最容易冲动消费。但我跟您说，买护肤品不是冲动，是给自己的皮肤投资，只要选对了就不亏。',
     '有些旅客跟我说，在飞机上买东西容易一时兴起。所以我一般建议：先看看是不是自己正需要的，选对了再带——用得上才叫划算。'),
    ('您有没有觉得，过了25岁，以前随便涂涂就能好的皮肤，现在怎么护理都不够用了？这就是皮肤在提醒您，该升级护肤方案了。',
     '您有没有觉得，前些年怎么涂都行的皮肤，现在好像要更用心一点了？这其实很正常——护理方案跟着状态调整，是件挺自然的事。'),
    ('您看啊，这几样搭配起来，就是一套完整的抗初老方案。25岁以后就可以开始用了，预防永远比修复容易。',
     '您看啊，这几样搭配起来，就是一套完整的基础护理方案。什么时候开始都不晚——提前把底子稳住，总比事后补救轻松。'),
    ('最后我想跟各位旅客说，春秋航空的纪念品，不是什么冲动消费的陷阱，是真正经过筛选的好产品。您买回去觉得好，才是我们的目标。',
     '最后我想跟各位旅客说，春秋航空的纪念品都经过认真筛选，不是什么随手买的东西。您带回去觉得好、用得着，才是我们的目标。'),
    ('最后我想跟各位旅客说，春秋航空的机上好物，不是什么冲动消费的陷阱，是真正经过筛选的好产品。您买回去用着好，才是我们的目标。',
     '最后我想跟各位旅客说，春秋航空的机上好物都经过认真筛选，不是什么随手买的东西。您带回去用着好，才是我们的目标。'),
    ('您有没有想过，为什么有些经常出差的旅客看起来还是比同龄人精神？很大程度上是因为她们懂得在旅途中也好好保养。这款产品就是帮您做这种',
     '您有没有想过，为什么有些经常出差的旅客，落地时状态还挺稳？很大程度上是因为她们懂得在旅途中也照顾着自己。这款产品就是帮您做这种'),
    ('现在很多出差的女旅客，二十出头就开始注意抗老了。不是吓唬您，出差熬夜、机舱干燥、水土不服，都让皮肤老得快。这款产品就是帮您',
     '现在不少常出差的旅客，很年轻就开始做抗老功课了。说实话，出差熬夜、机舱干燥、水土不服，确实容易让皮肤状态往下走。这款产品就是帮您'),
    ('的，趁早保养，以后比同龄人年轻好几岁。', '的——提前把底子稳住，后面省心。'),
    ('您说现在的人，哪个不是手机不离手、电脑不离眼？出差路上就更别提了，整个旅途都在刷屏。时间长了，眼睛酸、脖子疼、皮肤差。',
     '您说现在的人，哪个不是手机不离手、电脑不离眼？出差路上就更别提了，整个旅途都在刷屏。时间长了，眼睛酸、脖子疼，皮肤也容易跟着没精神。'),
    # —— 外貌/年龄评判 ——
    ('全脸的精华用过了，眼周这块容易显老的地方，正好用眼霜补上。',
     '全脸的精华用过了，眼周这块皮肤最薄、最需要单独照顾，正好用眼霜补上。'),
    ('眼周是最容易显老的地方，这款眼霜是很多旅客回购最多的。',
     '眼周皮肤最薄，护理得单独来，这款眼霜是很多旅客回购最多的。'),
    ('常洗手的人指尖最容易显老', '常洗手的人指尖最容易干得起皮'),
    ('想让暗沉的脸透出点粉亮的气色', '想让肤色透出点粉亮的气色'),
    ('熬夜暗沉的脸用着合适。您肤色容易发黄还是偏干？', '熬夜后肤色发暗时用着合适。您平时更在意提亮还是保湿？'),
    ('您问的这款是蒂佳婷绿丸面膜。是蒂佳婷绿丸弹润面膜，积雪草加多肽，偏紧致弹润，熬夜脸垮时敷一片提提气。 您平时更在意初老松弛肌还是熬夜暗沉肌？',
     '您问的这款是蒂佳婷绿丸弹润面膜，积雪草加多肽，偏紧致弹润，熬夜后脸没精神时敷一片提提气。您平时更在意紧致还是提亮？'),
    # —— 年龄指代 ——
    ('叔叔阿姨，年纪大了皮肤容易干燥，这款滋润度特别好，用完皮肤滑滑的。',
     '叔叔阿姨，手和脸的皮肤本来就容易干，这款滋润度特别好，用完摸着滑滑的。'),
    ('这款护手霜便宜又好用，年纪大了手容易干裂，随身带一支随时涂。',
     '这款护手霜便宜又好用，手常年干、容易裂的话，随身带一支随时涂。'),
    # —— 暗示旅客看不懂 ——
    ('如果您担心看不懂包装上的说明', '如果包装上的外文看着不方便'),
    # —— 门面 / 掉价 ——
    ('超级面膜是他家的门面', '超级面膜是他家的招牌'),
    ('超级面膜是伊菲丹的门面', '超级面膜是伊菲丹的招牌'),
    ('送人自用都不掉价', '送人自用都不失礼'),
    # —— 同伴比较 / 贬低他人商品 ——
    ('很多旅客跟我说，她们最怕的就是同学聚会，怕自己看起来比别人老。其实只要坚持护肤，同龄人之间的差距可以很大。',
     '常听旅客说，最开心的事是被夸一句“你气色真好”。其实只要日常把基础护理坚持下来，时间长了是看得出来的。'),
    ('我跟您说，这款纪念品拿在手里有分量，不是那种轻飘飘的廉价感。合金材质就是不一样。',
     '我跟您说，这款纪念品拿在手里有分量，做工扎实。合金材质就是不一样。'),
    ('您有没有觉得，春秋航空的纪念品有一种特别的质感？拿在手里有分量、有质感，不是那种轻飘飘的廉价品。',
     '您有没有觉得，春秋航空的纪念品有一种特别的质感？拿在手里有分量、做工扎实，一眼能看出来。'),
]

# ---------- 残留扫描（--audit）：强冒犯模式 ----------
AUDIT_PAT = re.compile(
    '把脸当门面|(?<!全)脸面|门面|面子工程|看得比天大|虚荣|攀比|'
    '年纪大了|上了年纪|显老|老得快|比别人老|比同龄人年轻|比同龄人精神|黄脸婆|'
    '皮肤差|皮肤不好|脸垮|皮肤变差|暗沉的脸|不修边幅|赘肉|发福|身材走样|'
    '看不懂包装|不识字|没文化|(?<!泥)土气|没品位|'
    '怕老|吓唬|买不起|舍不得|小气|斤斤计较|掉价|廉价|'
    '冲动消费|老五岁|女人到了一定年龄|拼的不是谁有钱|第一印象太重要|皮肤能好才怪|皮肤在提醒您|过了25岁')


def read(path):
    return io.open(path, encoding='utf-8', newline='').read()


def load_src():
    """单一来源 = 头部说明 + 标记块，整份作为替换体（保证重跑时区间完全一致）"""
    src = read(SRC).rstrip('\n')
    if src.find(BEGIN) < 0:
        raise SystemExit('!! 单一来源文件缺少 TALKSHOW_ENGINE_BEGIN 标记')
    return src


# 一次性清理：v1 遗留的说明注释（描述已过时，保留会误导）
V1_HEAD_RE = re.compile(r'/\* =+\n \* 【增强】广播·脱口秀话术引擎（2026-09）[\s\S]*?\* =+ \*/\n')


def transform(s, blk):
    n = 0
    # 0) 清理 v1 遗留头部注释
    s, k = V1_HEAD_RE.subn('', s, count=1)
    n += k

    # 1) 引擎整块替换（幂等：把紧邻的 BEGIN/END 标记与源文件头部说明一起纳入替换区间）
    st = s.find(ENGINE_START)
    en = s.find(ENGINE_END, st if st >= 0 else 0)
    if st < 0 or en < 0:
        raise SystemExit('!! 未找到 talkShowEngine 块')
    en += len(ENGINE_END)
    pre = s.rfind(BEGIN, 0, st)
    if pre >= 0 and s[pre + len(BEGIN):st].strip() == '':
        st = pre
    # 替换体含头部说明 —— 若其紧邻排在 BEGIN 之前，一并纳入，避免重复注入
    hi = blk.find(BEGIN)
    head = blk[:hi]
    if head:
        hp = s.rfind(head, 0, st)
        if hp >= 0 and s[hp + len(head):st].strip() == '':
            st = hp
    post = s.find(END, en)
    if post >= 0 and s[en:post].strip() == '':
        en = post + len(END)
    if s[st:en] != blk:
        s = s[:st] + blk + s[en:]
        n += 1

    # 2) 数据层替换（幂等：已换过则跳过）
    for old, new in FIXES:
        if old in s:
            s = s.replace(old, new)
            n += 1
        elif new not in s:
            raise SystemExit('!! 目标字符串未找到（可能已被改动）：' + old[:40])
    return s, n


def strip_engine(s):
    """去掉引擎块（禁语表本身含这些词，扫描时必须排除，否则全是假阳性）"""
    st = s.find(BEGIN)
    if st < 0:
        st = s.find(ENGINE_START)
    if st < 0:
        return s, s
    en = s.find(END, st)
    if en < 0:
        en = s.find(ENGINE_END, st)
        en = (en + len(ENGINE_END)) if en >= 0 else len(s)
    else:
        en += len(END)
    return s[:st] + s[en:], s[st:en]


def main():
    check = '--check' in sys.argv
    audit = '--audit' in sys.argv
    s = read(BEAUTY)
    if audit:
        body, _ = strip_engine(s)
        hits = {}
        for m in AUDIT_PAT.finditer(body):
            hits[m.group(0)] = hits.get(m.group(0), 0) + 1
        print('  残留强冒犯模式（已排除引擎禁语表）：', hits if hits else '无')
        sys.exit(0 if not hits else 1)
    if check:
        if not os.path.exists(SRC):
            raise SystemExit('!! 缺少单一来源文件 _talkshow_engine_v2.js')
        blk = load_src()
        out, n = transform(s, blk)
        if out == s:
            print('  beauty.html 脱口秀 v2 -> UP-TO-DATE')
            return
        print('!! beauty.html 脱口秀与脚本目标不一致'); sys.exit(1)
    if not os.path.exists(SRC):
        raise SystemExit('!! 缺少单一来源文件 _talkshow_engine_v2.js')
    blk = load_src()
    out, n = transform(s, blk)
    if out == s:
        print('  beauty.html 脱口秀 v2 -> UP-TO-DATE（无需改动）'); return
    bak = os.path.join(HERE, 'beauty.bak_talkshowv2_20260918.html')
    if not os.path.exists(bak):
        shutil.copy2(BEAUTY, bak); print('  备份 ->', os.path.basename(bak))
    io.open(BEAUTY, 'w', encoding='utf-8', newline='').write(out)
    body, _ = strip_engine(out)
    hits = {}
    for m in AUDIT_PAT.finditer(body):
        hits[m.group(0)] = hits.get(m.group(0), 0) + 1
    print(f'  beauty.html 脱口秀 v2 应用 {n} 处补丁（{len(s)} -> {len(out)} chars）')
    print('  残留强冒犯模式（已排除引擎禁语表）：', hits if hits else '无')


if __name__ == '__main__':
    main()
