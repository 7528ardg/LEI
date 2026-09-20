/* =============================================================
 * 日期匹配引擎（文本 / 日期 → 节假日 / 日期区间）—— 单一来源
 * 生成/维护：直接改本文件，再跑 python _sync_date_match.py 同步进各页面
 * 注入目标：index.html / qa.html / beauty.html
 * 依赖：window.SeasonEngine（农历节日表 LUNAR、24 节气表 TERMS）
 *
 * 统一输出结构（所有入口共用，字段齐全，不再各页面各写一套）：
 *   raw        原始匹配词（含修饰语，如「教师节快到了」）
 *   type       solar(公历节日) / lunar(农历节日) / weekday(第N个星期几)
 *              / shopping(通用购物节点) / term(节气) / relative(相对时间)
 *   key        节日标识（与 SeasonEngine 的 FEST_NAMES / OPEN_FESTS 对齐）
 *   name       节日中文名
 *   start      起始日期 YYYY-MM-DD
 *   end        结束日期 YYYY-MM-DD（多日假期为区间，单日为同一天）
 *   label      人类可读区间（如「2026-09-25 ~ 2026-09-27（3 天）」）
 *   confidence 置信度 0~1
 *   offset     before / same / after / around / soon / none（修饰语类别）
 *   note       解析说明（含跨年顺延、农历估算等提示）
 *
 * 三个对外主入口：
 *   parse(text)        文本 → 全部命中（数组，已做重叠消解）
 *   parseBest(text)    文本 → 置信度最高的一个
 *   todayMatch(dt)     日期 → 当天所处节日/节气（替代各页面自写的当日判断）
 *   resolveScript(t)   文本 → 直接可用的「开场话术挂载点」（含降级策略）
 *
 * ── 跨年处理策略 ───────────────────────────────────────────────
 * 1) 默认「就近向未来」：先算今年的日期；若整个假期已早于今天且超出宽限期
 *    （GRACE_DAYS=3 天），顺延到明年，note 标注「自动顺延到 YYYY 年」。
 *    宽限期的意义：9/12 说「教师节」时，教师节（9/10）才过两天，仍按今年算，
 *    避免跳到明年，符合「刚过不久」的日常语感。
 * 2) 「快到了 / 临近 / 节前」这类修饰语表意是「还没到」，因此附加
 *    preferFuture：只要节日当天已早于今天，一律顺延到明年 —— 否则会出现
 *    「教师节快到了」却解析出 3 天前区间的自相矛盾结果。
 * 3) 文本里出现「明年 / 来年 / 下一年」→ 强制 +1 年；「去年 / 上年」→ 强制 -1 年，
 *    优先级最高，不再走就近顺延。
 *
 * ── 农历节日日期不固定的处理策略 ──────────────────────────────
 * 农历节日（春节、中秋、端午、七夕、重阳、腊八、小年、除夕、元宵）每年对应的
 * 公历日期都不同，因此不做日期硬编码，分三档处理：
 *   a. 表内年份（SeasonEngine.LUNAR，2026-2040 天文算法生成）→ 精确日期，
 *      estimated=false，置信度 0.9；
 *   b. 表外年份 → 用该节日在公历中的「常见出现区间」(FESTS[].est) 取中点估算，
 *      estimated=true，置信度降到 0.55，note 明确标注「估算，实际日期以官方日历为准」；
 *   c. 节气（清明、冬至等）同理：TERMS 表内精确，表外按 TERM_EST 区间估算并降级。
 * 下游消费方应把 estimated=true 的结果当作「参考区间」，不要用于精确倒计时。
 * ============================================================= */
window.DateMatch = (function () {
  // 懒获取：SeasonEngine 可能在 DateMatch 之后注入，加载期一次性捕获会永久为 null。
  // （旧实现 var SE = window.SeasonEngine 曾导致农历/节气静默降级为 estimated=true、
  //   置信度 0.55 且不报错 —— 改为调用时现读，注入顺序不再敏感。）
  function SE() {
    return (typeof window !== 'undefined') ? window.SeasonEngine : null;
  }

  /* ---------------- 日期小工具 ---------------- */
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function ymd(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function day0(d) { return new Date(d.getFullYear(), d.getMonth(), d.getDate()); }
  function addDays(d, n) { return new Date(day0(d).getTime() + n * 86400000); }
  function md2date(s, y) {
    if (!s) return null;
    var p = String(s).split('-');
    if (p.length < 2) return null;
    var m = parseInt(p[0], 10), d = parseInt(p[1], 10);
    if (isNaN(m) || isNaN(d)) return null;
    return new Date(y, m - 1, d);
  }
  function daysBetween(a, b) { return Math.round((day0(b) - day0(a)) / 86400000); }

  var CN_NUM = { '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10 };
  function cn2num(s) {
    if (s == null) return NaN;
    s = String(s).trim();
    if (/^\d+$/.test(s)) return parseInt(s, 10);
    if (s === '十') return 10;
    if (s.length === 1) return CN_NUM[s] != null ? CN_NUM[s] : NaN;
    if (/^十[一二三四五六七八九]$/.test(s)) return 10 + CN_NUM[s.charAt(1)];
    if (/^[二三四五六七八九]十$/.test(s)) return CN_NUM[s.charAt(0)] * 10;
    if (/^[二三四五六七八九]十[一二三四五六七八九]$/.test(s)) return CN_NUM[s.charAt(0)] * 10 + CN_NUM[s.charAt(2)];
    return NaN;
  }

  /* ---------------- 节日词典 ----------------
   * date：公历固定 MM-DD（solar / shopping）
   * span：假期天数（含当天），around 修饰时展开为区间
   * rule：weekday 类型用 [月份, 第几个, 星期几(0=周日)]
   * lunarKey：农历节日在 SeasonEngine.LUNAR 表中的键
   * est：该农历节日在公历中的可能区间（表外年份估算 + 跨年判断用）
   */
  var FESTS = [
    // ---------- 公历固定节日 ----------
    { key: 'newyear', name: '元旦', type: 'solar', date: '01-01', span: 3, alias: ['元旦', '元旦节', '新年', '跨年', '阳历年', '1月1号', '1月1日'] },
    { key: 'valentine', name: '情人节', type: 'solar', date: '02-14', span: 1, alias: ['情人节', '2月14号', '2月14日'] },
    { key: 'women', name: '妇女节', type: 'solar', date: '03-08', span: 1, alias: ['妇女节', '三八节', '女神节', '女王节', '女生节', '3月8号', '3月8日'] },
    { key: 'qingming', name: '清明节', type: 'solar', date: '04-05', span: 3, alias: ['清明', '清明节', '踏青', '扫墓'] },
    { key: 'labor', name: '劳动节', type: 'solar', date: '05-01', span: 5, alias: ['劳动节', '五一', '五一节', '5月1号', '5月1日', '小长假'] },
    { key: 'children', name: '儿童节', type: 'solar', date: '06-01', span: 1, alias: ['儿童节', '六一', '六一节', '6月1号', '6月1日'] },
    { key: 'teachers', name: '教师节', type: 'solar', date: '09-10', span: 1, alias: ['教师节', '老师节', '9月10号', '9月10日'] },
    { key: 'national', name: '国庆节', type: 'solar', date: '10-01', span: 7, alias: ['国庆', '国庆节', '十一', '10月1号', '10月1日', '黄金周'] },
    { key: 'halloween', name: '万圣节', type: 'solar', date: '10-31', span: 1, alias: ['万圣节', '万圣夜', '10月31号'] },
    { key: 'thanksgiving', name: '感恩节', type: 'solar', date: '11-26', span: 1, alias: ['感恩节'] },
    { key: 'christmas', name: '圣诞节', type: 'solar', date: '12-25', span: 1, alias: ['圣诞', '圣诞节', '平安夜', '12月25号'] },
    // ---------- 第 N 个星期几 ----------
    { key: 'mothers', name: '母亲节', type: 'weekday', rule: [5, 2, 0], span: 1, alias: ['母亲节', '妈妈节'] },
    { key: 'fathers', name: '父亲节', type: 'weekday', rule: [6, 3, 0], span: 1, alias: ['父亲节', '爸爸节'] },
    // ---------- 通用购物节点 ----------
    { key: 'shopping618', name: '618年中大促', type: 'shopping', date: '06-18', span: 1, alias: ['618', '6.18', '6月18', '年中大促', '618大促'] },
    { key: 'shuang11', name: '双十一', type: 'shopping', date: '11-11', span: 1, alias: ['双十一', '双11', '双十一购物节', '光棍节', '11.11', '11月11号'] },
    { key: 'shuang12', name: '双十二', type: 'shopping', date: '12-12', span: 1, alias: ['双十二', '双12', '12.12', '12月12号'] },
    { key: 'nianhuo', name: '年货节', type: 'shopping', date: '01-10', span: 10, alias: ['年货节', '年货', '办年货'] },
    // ---------- 农历节日（每年公历日期不同，查 SeasonEngine.LUNAR 表） ----------
    { key: 'laba', name: '腊八节', type: 'lunar', lunarKey: 'laba', span: 1, est: ['01-01', '01-31'], alias: ['腊八', '腊八节', '腊月初八'] },
    { key: 'xiaonian', name: '小年', type: 'lunar', lunarKey: 'xiaonian', span: 1, est: ['01-15', '02-15'], alias: ['小年', '小年夜', '祭灶'] },
    { key: 'chuxi', name: '除夕', type: 'lunar', lunarKey: 'chuxi', span: 1, est: ['01-20', '02-20'], alias: ['除夕', '大年夜', '年三十', '大年三十'] },
    { key: 'spring', name: '春节', type: 'lunar', lunarKey: 'spring', span: 7, est: ['01-21', '02-21'], alias: ['春节', '过年', '新春', '农历新年', '大年初一', '初一'] },
    { key: 'yuanxiao', name: '元宵节', type: 'lunar', lunarKey: 'yuanxiao', span: 1, est: ['02-04', '03-06'], alias: ['元宵', '元宵节', '正月十五', '灯节'] },
    { key: 'duanwu', name: '端午节', type: 'lunar', lunarKey: 'duanwu', span: 3, est: ['05-27', '06-27'], alias: ['端午', '端午节', '粽子节', '五月初五'] },
    { key: 'qixi', name: '七夕节', type: 'lunar', lunarKey: 'qixi', span: 1, est: ['07-31', '08-31'], alias: ['七夕', '七夕节', '乞巧节', '七月初七'] },
    { key: 'midautumn', name: '中秋节', type: 'lunar', lunarKey: 'midautumn', span: 3, est: ['09-07', '10-07'], alias: ['中秋', '中秋节', '八月十五', '月饼节', '团圆节'] },
    { key: 'chongyang', name: '重阳节', type: 'lunar', lunarKey: 'chongyang', span: 1, est: ['09-30', '10-31'], alias: ['重阳', '重阳节', '敬老节', '九月初九'] }
  ];

  // 24 节气（type=term，日期查 SeasonEngine.TERMS 表）
  var TERMS = (SE() && SE().TERM_ORDER) ? SE().TERM_ORDER : [
    '小寒', '大寒', '立春', '雨水', '惊蛰', '春分', '清明', '谷雨', '立夏', '小满',
    '芒种', '夏至', '小暑', '大暑', '立秋', '处暑', '白露', '秋分', '寒露', '霜降',
    '立冬', '小雪', '大雪', '冬至'
  ];
  // 节气在公历中的常见区间（表外年份估算用）
  var TERM_EST = {
    '小寒': ['01-05', '01-07'], '大寒': ['01-19', '01-21'], '立春': ['02-03', '02-05'], '雨水': ['02-18', '02-20'],
    '惊蛰': ['03-05', '03-07'], '春分': ['03-20', '03-22'], '清明': ['04-04', '04-06'], '谷雨': ['04-19', '04-21'],
    '立夏': ['05-05', '05-07'], '小满': ['05-20', '05-22'], '芒种': ['06-05', '06-07'], '夏至': ['06-20', '06-22'],
    '小暑': ['07-06', '07-08'], '大暑': ['07-22', '07-24'], '立秋': ['08-07', '08-09'], '处暑': ['08-22', '08-24'],
    '白露': ['09-07', '09-09'], '秋分': ['09-22', '09-24'], '寒露': ['10-07', '10-09'], '霜降': ['10-22', '10-24'],
    '立冬': ['11-06', '11-08'], '小雪': ['11-21', '11-23'], '大雪': ['12-06', '12-08'], '冬至': ['12-21', '12-23']
  };

  /* ---------------- 修饰语：把节日当天变成区间 ---------------- */
  var SOON_DAYS = 7;    // 「快到了 / 临近」默认按节前 7 天算
  var NEAR_DAYS = 3;    // 「节前 / 之前」未带数字时，默认取节前 3 天
  // 数量词（含中文数字），供 before / after 计算跨度
  var NUM = '([一二三四五六七八九十两1-9]|十[一二三四五六七八九]|\\d+)';
  var UNIT = '(个月|月|周|个星期|星期|礼拜|天|日)';
  var MODS = [
    // 顺序即优先级：先看「临近」，再看「节前/节后」，最后才是泛化的「前后/期间」
    { re: /(快到了|就快到了|快要到了|就要到了|马上到了|即将到来|即将来临|临近了?|快到了|快到|接近了?|倒计时|要到了|快过节|要过节)/, off: 'soon', label: '临近（节前 ' + SOON_DAYS + ' 天起）' },
    { re: /(节前|之前|以前)/, off: 'before', n: NEAR_DAYS, label: '节前（默认节前 ' + NEAR_DAYS + ' 天）' },
    { re: /(节后|之后|过后|以后)/, off: 'after', n: NEAR_DAYS, label: '节后（默认节后 ' + NEAR_DAYS + ' 天）' },
    { re: /(前一天|头一天|提前一天|提前1天)/, off: 'before', n: 1, unit: '天', label: '节前 1 天' },
    { re: /(后一天|次日|第二天|隔天)/, off: 'after', n: 1, unit: '天', label: '节后 1 天' },
    // 注意：动词用非捕获组，保证 m[1]=数量、m[2]=单位 的索引在所有规则里一致
    { re: /(?:提前|提早)\s*([一二三四五六七八九十两1-9]|十[一二三四五六七八九]|\d+)\s*(个月|月|周|个星期|星期|天|日)/, off: 'before', label: '提前 N 个单位' },
    { re: new RegExp('前\\s*' + NUM + '\\s*' + UNIT), off: 'before', label: '节前 N 个单位' },
    { re: new RegExp('后\\s*' + NUM + '\\s*' + UNIT), off: 'after', label: '节后 N 个单位' },
    { re: /(当天|正日子|当日|那天|节日当天|这一天)/, off: 'same', label: '节日当天' },
    { re: /(前后|期间|那几天|这几天|假期里|假期|过节期间|过节|节日里|左右)/, off: 'around', label: '节日前后' }
  ];
  // 单位 → 天数（「月」走日历加月，这里只在无法加月时兜底）
  function unitDays(u) {
    if (!u) return 1;
    if (u.indexOf('月') >= 0) return 30;
    if (u.indexOf('周') >= 0 || u.indexOf('星期') >= 0 || u.indexOf('礼拜') >= 0) return 7;
    return 1;
  }
  // 按单位平移日期（月按日历自然月，避免 30 天累计误差）
  function shiftByUnit(d, n, u) {
    if (u && u.indexOf('月') >= 0) return new Date(d.getFullYear(), d.getMonth() + n, d.getDate());
    return addDays(d, n * unitDays(u));
  }

  /* ---------------- 相对时间 ---------------- */
  function weekStart(d) { var x = day0(d), w = x.getDay(); return addDays(x, w === 0 ? -6 : 1 - w); } // 周一为首
  function monthStart(d) { return new Date(d.getFullYear(), d.getMonth(), 1); }
  function monthEnd(d) { return new Date(d.getFullYear(), d.getMonth() + 1, 0); }
  function addMonths(d, n) { return new Date(d.getFullYear(), d.getMonth() + n, 1); }

  /* 相对时间词表
   * 顺序原则：特异表达在前（「这周末」优先于「这周」），重叠命中由 dedupe 按
   * raw 长度与置信度消解 —— 例如「下周末」同时命中「下周末」与「下周」时保留前者。
   */
  var RELS = [
    // —— 天级 ——
    { re: /今天|今日|现在/, name: '今天', calc: function (t) { return { s: t, e: t }; } },
    { re: /大后天/, name: '大后天', calc: function (t) { return { s: addDays(t, 3), e: addDays(t, 3) }; } },
    { re: /明天|明日|明儿/, name: '明天', calc: function (t) { return { s: addDays(t, 1), e: addDays(t, 1) }; } },
    { re: /后天/, name: '后天', calc: function (t) { return { s: addDays(t, 2), e: addDays(t, 2) }; } },
    { re: /昨天|昨日/, name: '昨天', calc: function (t) { return { s: addDays(t, -1), e: addDays(t, -1) }; } },
    { re: /前天/, name: '前天', calc: function (t) { return { s: addDays(t, -2), e: addDays(t, -2) }; } },
    { re: new RegExp(NUM + '\\s*(天|日)后'), name: 'N天后', calc: function (t, m) { var n = cn2num(m[1]) || 1; return { s: addDays(t, n), e: addDays(t, n) }; } },
    { re: new RegExp('前\\s*' + NUM + '\\s*(天|日)'), name: '前N天', calc: function (t, m) { var n = cn2num(m[1]) || 3; return { s: addDays(t, -n), e: addDays(t, -1) }; } },
    { re: /这几天|近几天|这两天/, name: '这几天', calc: function (t) { return { s: addDays(t, -2), e: t }; } },
    { re: /前几天|前些天/, name: '前几天', calc: function (t) { return { s: addDays(t, -3), e: addDays(t, -1) }; } },
    // —— 周级：周末类必须排在泛化周之前 ——
    { re: /这(个)?周末|本周末|这(个)?礼拜天?/, name: '这周末', calc: function (t) { var w = weekStart(t); return { s: addDays(w, 5), e: addDays(w, 6) }; } },
    { re: /下(个)?周末|下(个)?礼拜天?/, name: '下周末', calc: function (t) { var w = weekStart(t); return { s: addDays(w, 12), e: addDays(w, 13) }; } },
    { re: /上(个)?周末|上(个)?礼拜天?/, name: '上周末', calc: function (t) { var w = weekStart(t); return { s: addDays(w, -2), e: addDays(w, -1) }; } },
    { re: /周末|礼拜天|周日/, name: '周末', calc: function (t) { var w = weekStart(t); return { s: addDays(w, 5), e: addDays(w, 6) }; } },
    { re: new RegExp(NUM + '\\s*(周|个星期|星期|礼拜)后'), name: 'N周后', calc: function (t, m) { var n = cn2num(m[1]) || 1; return { s: addDays(t, n * 7), e: addDays(t, n * 7) }; } },
    { re: /下(个)?(周|星期|礼拜)/, name: '下周', calc: function (t) { var w = weekStart(t); return { s: addDays(w, 7), e: addDays(w, 13) }; } },
    { re: /这(个)?(周|星期|礼拜)|本(周|星期)/, name: '这周', calc: function (t) { var w = weekStart(t); return { s: w, e: addDays(w, 6) }; } },
    { re: /上上?(个)?(周|星期|礼拜)/, name: '上周', calc: function (t) { var w = weekStart(t); return { s: addDays(w, -7), e: addDays(w, -1) }; } },
    // —— 月 / 季 / 年 ——
    { re: new RegExp(NUM + '\\s*(个月|月)后'), name: 'N个月后', calc: function (t, m) { var n = cn2num(m[1]) || 1, d = addMonths(t, n); return { s: d, e: new Date(d.getFullYear(), d.getMonth() + 1, 0) }; } },
    { re: /下个月|下月|下个?月/, name: '下个月', calc: function (t) { var m = addMonths(t, 1); return { s: m, e: new Date(m.getFullYear(), m.getMonth() + 1, 0) }; } },
    { re: /这个月|本月|这月/, name: '这个月', calc: function (t) { return { s: monthStart(t), e: monthEnd(t) }; } },
    { re: /上个月|上月/, name: '上个月', calc: function (t) { var m = addMonths(t, -1); return { s: m, e: new Date(m.getFullYear(), m.getMonth() + 1, 0) }; } },
    { re: /年底|年末|年底前/, name: '年底', calc: function (t) { return { s: new Date(t.getFullYear(), 11, 1), e: new Date(t.getFullYear(), 11, 31) }; } },
    { re: /年初|开年/, name: '年初', calc: function (t) { var y = t.getFullYear() + (t.getMonth() > 0 ? 1 : 0); return { s: new Date(y, 0, 1), e: new Date(y, 0, 31), rolled: t.getMonth() > 0 }; } },
    { re: /半年内|近半年/, name: '近半年', calc: function (t) { return { s: addDays(t, -180), e: t }; } }
  ];

  /* ---------------- 节日 → 具体日期 ---------------- */
  // 取某年该节日的 {s, e, estimated}
  function datesOf(fest, year) {
    if (fest.type === 'solar' || fest.type === 'shopping') {
      var d = md2date(fest.date, year);
      return { s: d, e: addDays(d, (fest.span || 1) - 1), estimated: false };
    }
    if (fest.type === 'weekday') {
      var r = fest.rule, first = new Date(year, r[0] - 1, 1).getDay();
      var day = ((r[2] - first + 7) % 7) + 1 + (r[1] - 1) * 7;
      var wd = new Date(year, r[0] - 1, day);
      return { s: wd, e: addDays(wd, (fest.span || 1) - 1), estimated: false };
    }
    if (fest.type === 'lunar') {
      var tbl = SE() && SE().LUNAR && SE().LUNAR[String(year)];
      if (tbl && tbl[fest.lunarKey]) {
        var ld = md2date(tbl[fest.lunarKey], year);
        return { s: ld, e: addDays(ld, (fest.span || 1) - 1), estimated: false };
      }
      // 表外年份：用公历可能区间的中点估算，置信度降级，同时把真实可能区间一并带出
      var a = md2date(fest.est[0], year), b = md2date(fest.est[1], year);
      var mid = day0(new Date((a.getTime() + b.getTime()) / 2));
      return { s: mid, e: addDays(mid, (fest.span || 1) - 1), estimated: true, estRange: [ymd(a), ymd(b)] };
    }
    if (fest.type === 'term') {
      var tt = SE() && SE().TERMS && SE().TERMS[String(year)];
      if (tt && tt[fest.key]) {
        var td = md2date(tt[fest.key], year);
        return { s: td, e: addDays(td, 2), estimated: false };
      }
      var er = TERM_EST[fest.key] || ['01-01', '12-31'];
      var ea = md2date(er[0], year), eb = md2date(er[1], year);
      var tm = day0(new Date((ea.getTime() + eb.getTime()) / 2));
      return { s: tm, e: addDays(tm, 2), estimated: true, estRange: [ymd(ea), ymd(eb)] };
    }
    return null;
  }

  /* 跨年策略：
   * 1. 先取「今年」的日期；若整个假期已早于今天，且超出宽限期（默认 3 天），顺延到明年（rolled=true）
   *    —— 宽限期的意义：刚过去两三天的节（9/12 说「教师节」）仍按今年算，避免跳到明年
   * 2. 文本里出现「明年 / 明年中秋」→ 强制 +1 年；「去年 / 去年春节」→ 强制 -1 年
   * 3. 农历节日日期每年不同：表内年份（2026-2040）用天文算法生成的精确表；
   *    表外年份用「该节日在公历中的可能区间」取中点估算，并置 estimated=true、置信度降至 0.6
   */
  var GRACE_DAYS = 3;
  /* preferFuture：语义上必然指向「还没到的那个节」（临近 / 节前 / 提前准备）时置 true ——
   * 此时只要节日当天已早于今天，一律顺延到明年，避免「教师节快到了」解析出已过去的区间 */
  function resolveFest(fest, today, forceYear, grace, preferFuture) {
    grace = (grace == null) ? GRACE_DAYS : grace;
    var y = today.getFullYear();
    if (forceYear === 'next') y += 1;
    if (forceYear === 'prev') y -= 1;
    var r = datesOf(fest, y);
    if (!r) return null;
    var rolled = false, justPassed = 0;
    if (!forceYear) {
      var gap = daysBetween(r.e, day0(today)); // >0 表示假期已结束多少天
      if (preferFuture && gap > 0) {
        y += 1;
        r = datesOf(fest, y);
        rolled = true;
      } else if (gap > grace) {
        y += 1;
        r = datesOf(fest, y);
        rolled = true;
      } else if (gap > 0) {
        justPassed = gap;
      }
    }
    return { year: y, s: r.s, e: r.e, estimated: r.estimated, estRange: r.estRange, rolled: rolled, justPassed: justPassed };
  }

  /* ---------------- 扫描：节日词 ---------------- */
  // 构造（词 → 节日）索引，长词优先
  var WORDS = [];
  var FEST_ALIAS = {};
  FESTS.forEach(function (f) {
    f.alias.forEach(function (a) {
      FEST_ALIAS[a] = 1;
      WORDS.push({ w: a, f: f });
    });
  });
  // 节气词：已被节日别名占用的（如「清明」）不再单独建词，避免同位置重复命中
  TERMS.forEach(function (t) {
    if (FEST_ALIAS[t]) return;
    WORDS.push({ w: t, f: { key: t, name: t, type: 'term', span: 3, alias: [t] } });
  });
  WORDS.sort(function (a, b) { return b.w.length - a.w.length; });

  // 上下文保护：排除「三十一号」里的「十一」、「十一月」里的「十一」这类数字片段误命中
  var NUMCHARS = '0-9一二三四五六七八九十百千万两';
  function badCtx(text, i, w) {
    var prev = i > 0 ? text.charAt(i - 1) : '';
    var next = text.charAt(i + w.length) || '';
    var isNum = function (ch) { return !!ch && NUMCHARS.indexOf(ch) >= 0; };
    // 前面紧跟数字/数词 → 是更大数字的一部分（三十一、一百一）
    if (isNum(prev) && isNum(w.charAt(0))) return true;
    // 「双十一 / 双十二」里的数字片段由整词命中，这里排除重复扫描
    if (prev === '双' && w.charAt(0) === '十') return true;
    // 后接「月」→ 是月份（十一月、五月、六月），不是节日
    if (next === '月' && (w === '十一' || w === '五一' || w === '六一' || w === '初一' || w === '十一五')) return true;
    // 后接量词/单位 → 是数量或时间点（十一点、十一号、三十一号、十一万）
    if ((w === '十一' || w === '五一' || w === '六一') && /[点号日时个万人元岁分秒]/.test(next)) return true;
    // 五一路、五一路口这类地名
    if (w === '五一' && next === '路') return true;
    if (w === '过年' && isNum(prev)) return true;
    return false;
  }

  function scanFestivals(text, today) {
    var out = [];
    WORDS.forEach(function (item) {
      var from = 0, i;
      while ((i = text.indexOf(item.w, from)) >= 0) {
        var end = i + item.w.length;
        if (badCtx(text, i, item.w)) { from = end; continue; }
        // 年份修饰：明年 / 去年 / 后年
        var pre = text.slice(Math.max(0, i - 4), i);
        var force = null;
        if (/明年|来年|下一年/.test(pre)) force = 'next';
        else if (/去年|上年|上一年|前年/.test(pre)) force = 'prev';
        // 修饰语：先看词后 8 字，再看词前 3 字（「临近中秋」「节前 3 天」两种语序）
        var post = text.slice(end, end + 8);
        var mod = null, modAt = end, modLen = 0;
        for (var k = 0; k < MODS.length; k++) {
          var m = post.match(MODS[k].re);
          if (m) { mod = { def: MODS[k], m: m }; modAt = end + m.index; modLen = m[0].length; break; }
          var preTxt = text.slice(Math.max(0, i - 3), i);
          var m2 = preTxt.match(MODS[k].re);
          if (m2) { mod = { def: MODS[k], m: m2 }; modAt = i - m2[0].length; modLen = m2[0].length; break; }
        }
        // 临近 / 节前语义 → 一律指向「还没到的那个节」
        var _pf = !!(mod && (mod.def.off === 'soon' || mod.def.off === 'before' || mod.def.off === 'pre'));
        var resolved = resolveFest(item.f, today, force, null, _pf);
        if (!resolved) { from = end; continue; }
        var s = resolved.s, e = resolved.e, off = 'none', note = '';
        var conf = item.f.type === 'lunar' ? 0.9 : (item.f.type === 'term' ? 0.85 : (item.f.type === 'shopping' ? 0.86 : 0.92));
        if (resolved.estimated) {
          conf = 0.55;
          var _rg = resolved.estRange ? ('，实际落在 ' + resolved.estRange[0] + ' ~ ' + resolved.estRange[1] + ' 之间') : '';
          note = '该年无精确' + (item.f.type === 'term' ? '节气' : '农历') + '表，按公历常见区间取中估算' + _rg + '，以官方日历为准';
        }
        if (mod) {
          off = mod.def.off;
          var n = (mod.def.n != null) ? mod.def.n : cn2num(mod.m[1]);
          if (!n || isNaN(n)) n = 1;
          var uu = mod.def.unit || (mod.m && mod.m[2]) || '天';
          if (off === 'before' || off === 'pre') {
            s = shiftByUnit(resolved.s, -n, uu); e = addDays(resolved.s, -1);
          } else if (off === 'after') {
            s = addDays(resolved.e, 1); e = shiftByUnit(resolved.e, n, uu);
          } else if (off === 'soon') {
            s = addDays(resolved.s, -SOON_DAYS); e = resolved.s;
          } else if (off === 'same') {
            s = resolved.s; e = resolved.s;
          } else if (off === 'around') {
            s = addDays(resolved.s, -1); e = resolved.e;
          }
          conf -= 0.04;
          note = (note ? note + '；' : '') + mod.def.label;
        }
        if (resolved.rolled) { conf -= 0.03; note = (note ? note + '；' : '') + '今年该节日已过，自动顺延到 ' + resolved.year + ' 年'; }
        else if (resolved.justPassed) { conf -= 0.02; note = (note ? note + '；' : '') + '该节日 ' + resolved.justPassed + ' 天前刚过（' + GRACE_DAYS + ' 天宽限内，仍按今年）'; }
        conf = Math.max(0.35, Math.min(0.99, conf));
        // 原文跨度：节日词 + 修饰语（前/后）+ 年份词（明年/去年）
        var rawFrom = Math.min(i, modAt, force ? i - 2 : i);
        var rawTo = Math.max(end, modAt + modLen);
        var _s0 = ymd(s), _e0 = ymd(e), _days = daysBetween(s, e) + 1;
        out.push({
          raw: text.slice(Math.max(0, rawFrom), rawTo),
          type: item.f.type, key: item.f.key, name: item.f.name,
          start: _s0, end: _e0,
          label: _s0 + (_s0 === _e0 ? '' : ' ~ ' + _e0) + '（' + _days + ' 天）',
          confidence: Math.round(conf * 100) / 100,
          offset: off, index: Math.max(0, rawFrom), note: note || '未带修饰语，按节日当天（含假期 ' + (item.f.span || 1) + ' 天）',
          year: resolved.year, estimated: resolved.estimated, rolled: resolved.rolled, span: item.f.span || 1
        });
        from = end;
      }
    });
    return out;
  }

  /* ---------------- 扫描：相对时间 ---------------- */
  function scanRelative(text, today) {
    var out = [];
    RELS.forEach(function (r) {
      var m = text.match(r.re);
      if (!m) return;
      var c = r.calc(today, m);
      if (!c) return;
      var _rs = ymd(c.s), _re = ymd(c.e), _rd = daysBetween(c.s, c.e) + 1;
      out.push({
        raw: m[0], type: 'relative', key: r.name, name: r.name,
        start: _rs, end: _re,
        label: _rs + (_rs === _re ? '' : ' ~ ' + _re) + '（' + _rd + ' 天）',
        confidence: (c.s.getTime() === c.e.getTime() ? 0.9 : 0.8), offset: 'none',
        index: text.indexOf(m[0]),
        note: '按当前系统日期 ' + ymd(today) + ' 归一化' + (c.rolled ? '（已过，顺延到下一年）' : ''),
        year: c.s.getFullYear(), estimated: false, rolled: !!c.rolled, span: _rd
      });
    });
    return out;
  }

  /* ---------------- 主入口 ---------------- */
  // 重叠消解：长匹配优先，其次置信度高优先
  function dedupe(list) {
    list.sort(function (a, b) {
      var la = a.raw.length, lb = b.raw.length;
      if (lb !== la) return lb - la;
      return b.confidence - a.confidence;
    });
    var taken = [], out = [];
    list.forEach(function (m) {
      var s = m.index, e = s + m.raw.length;
      for (var i = 0; i < taken.length; i++) {
        if (s < taken[i].e && e > taken[i].s) return; // 与已选重叠
      }
      taken.push({ s: s, e: e });
      out.push(m);
    });
    out.sort(function (a, b) { return a.index - b.index; });
    return out;
  }

  function parse(text, opts) {
    opts = opts || {};
    if (text == null) return [];
    text = String(text);
    var today = opts.today ? day0(opts.today) : day0(new Date());
    var all = scanFestivals(text, today).concat(scanRelative(text, today));
    return dedupe(all);
  }

  function parseBest(text, opts) {
    var list = parse(text, opts);
    if (!list.length) return null;
    var best = list[0];
    list.forEach(function (m) { if (m.confidence > best.confidence) best = m; });
    return best;
  }

  /* ---------------- 当日匹配：统一「今天是什么节」 ----------------
   * 与 SeasonEngine.match 的差异（也是各页面此前各写一套的根源）：
   *   1. 认「假期区间」——春节第 3 天、国庆第 5 天都算在节里（SeasonEngine 只认当天）
   *   2. 覆盖万圣节 / 感恩节等 SeasonEngine 词表里没有的节日
   *   3. 输出结构与 parse() 完全一致，消费方不必写两套字段
   * 优先级：公历节日 > 第 N 个星期几 > 农历节日 > 购物节点 > 节气
   */
  var TODAY_ORDER = { solar: 0, weekday: 1, lunar: 2, shopping: 3, term: 4 };
  function todayMatch(dt) {
    var today = day0(dt || new Date());
    var hits = [];
    FESTS.forEach(function (f) {
      var r = datesOf(f, today.getFullYear());
      if (!r || !r.s) return;
      var rs = day0(r.s), re = day0(r.e);
      if (today >= rs && today <= re) {
        var a = ymd(rs), b = ymd(re), sp = daysBetween(rs, re) + 1;
        hits.push({
          raw: f.name, type: f.type, key: f.key, name: f.name,
          start: a, end: b,
          label: a + (a === b ? '' : ' ~ ' + b) + '（' + sp + ' 天）',
          confidence: r.estimated ? 0.55 : (f.type === 'lunar' ? 0.9 : 0.92),
          offset: 'same', index: -1,
          note: '今天是' + f.name + (daysBetween(rs, today) > 0 ? '（假期第 ' + (daysBetween(rs, today) + 1) + ' 天）' : ''),
          year: today.getFullYear(), estimated: !!r.estimated, rolled: false, span: sp
        });
      }
    });
    // 节气：复用 SeasonEngine 的精确表，DateMatch 不再维护第二份节气日期
    try {
      var tn = (SE() && SE().solarTermOf) ? SE().solarTermOf(today) : '';
      if (tn) {
        var row = (SE() && SE().TERMS) ? SE().TERMS[String(today.getFullYear())] : null;
        var td = row ? md2date(row[tn], today.getFullYear()) : null;
        var ok = !!(td && !isNaN(td.getTime()));
        var ts = ok ? day0(td) : today, te = addDays(ts, 2);
        hits.push({
          raw: tn, type: 'term', key: tn, name: tn,
          start: ymd(ts), end: ymd(te),
          label: ymd(ts) + (ymd(ts) === ymd(te) ? '' : ' ~ ' + ymd(te)) + '（' + (daysBetween(ts, te) + 1) + ' 天）',
          confidence: ok ? 0.85 : 0.6, offset: 'same', index: -1,
          note: '今天是节气「' + tn + '」' + (ok ? '' : '（按常见区间估算）'),
          year: today.getFullYear(), estimated: !ok, rolled: false, span: 3
        });
      }
    } catch (e) {}
    if (!hits.length) return null;
    hits.sort(function (a, b) {
      var oa = TODAY_ORDER[a.type] == null ? 9 : TODAY_ORDER[a.type];
      var ob = TODAY_ORDER[b.type] == null ? 9 : TODAY_ORDER[b.type];
      if (oa !== ob) return oa - ob;
      return b.span - a.span;
    });
    return hits[0];
  }

  /* ---------------- 解析结果 → 开场话术挂载点 ----------------
   * 只有话术库里真有对应话术池的才返回 key（fest→OPEN_FESTS / term→OPEN_TERMS），
   * 其余返回 null，由调用方走通用开场 —— 关键是「识别」与「有话说」解耦，
   * 不再因为话术池缺 key 就把识别结果整条丢掉。
   */
  var TERM_AS_FEST = { qingming: '清明' };
  function scriptKeyOf(m) {
    if (!m) return null;
    if (m.type === 'term') return { kind: 'term', key: m.key };
    if (m.type === 'relative') return null;
    if (TERM_AS_FEST[m.key]) return { kind: 'term', key: TERM_AS_FEST[m.key] };
    if (SE() && SE().OPEN_FESTS && SE().OPEN_FESTS[m.key]) return { kind: 'fest', key: m.key };
    return null;
  }
  function hasOpenPool(k) {
    if (!k || !SE) return false;
    var pool = (k.kind === 'term') ? (SE().OPEN_TERMS && SE().OPEN_TERMS[k.key]) : (SE().OPEN_FESTS && SE().OPEN_FESTS[k.key]);
    return !!(pool && pool.length);
  }

  /* ---------------- 一站式：文本 → 可直接驱动话术的结果 ----------------
   * 优先级：话术主题里识别到的节日 > 今日匹配
   * 返回：source(topic|today|none) / match / script(有现成话术时) / label / confidence / inlineHint
   */
  function resolveScript(text, opts) {
    opts = opts || {};
    var today = opts.today ? day0(opts.today) : day0(new Date());
    var t = (text == null) ? '' : String(text).trim();
    var m = t ? parseBest(t, { today: today }) : null;
    var source = 'topic';
    if (!m) { m = todayMatch(today); source = m ? 'today' : 'none'; }
    var key = scriptKeyOf(m);
    var usable = hasOpenPool(key);
    return {
      source: source,
      match: m,
      script: usable ? key : null,
      kind: (key && usable) ? key.kind : '',
      key: (key && usable) ? key.key : '',
      name: m ? m.name : '',
      start: m ? m.start : '',
      end: m ? m.end : '',
      label: m ? m.label : '',
      confidence: m ? m.confidence : 0,
      note: m ? m.note : '',
      estimated: m ? !!m.estimated : false,
      // 只有「节日 / 节气」才值得补一句应景提示；相对时间（下个月、这周）不植入
      inlineHint: (m && !usable && m.type !== 'relative') ? ('正好赶上' + m.name + '，算是应景。') : ''
    };
  }

  // 一句话说明（UI 展示用）
  function describe(m) {
    if (!m) return '';
    var range = m.label || (m.start === m.end ? m.start : (m.start + ' ~ ' + m.end));
    return m.name + '（' + range + '，置信度 ' + Math.round(m.confidence * 100) + '%' + (m.note ? '，' + m.note : '') + '）';
  }

  var TYPE_NAMES = { solar: '公历节日', lunar: '农历节日', weekday: '公历节日', shopping: '通用节点', term: '节气', relative: '相对时间' };
  function typeName(t) { return TYPE_NAMES[t] || t; }

  /* ---------------- 自检样例 ---------------- */
  var SAMPLES = [
    // —— 话术里最常见的节日称呼（务必先识别节日词，再解析日期）——
    '教师节快到了，想给老师挑份礼物',
    '中秋想送点礼给爸妈',
    '国庆出去玩，路上带点什么好',
    '春节前一天飞',
    '端午后一天回程',
    '中秋当天想订一盒',
    '临近中秋的航班',
    '国庆节前的班次',
    '教师节后三天到货',
    '中秋前一周开始备货',
    '明年中秋想提前一个月准备',
    // —— 通用购物节点 ——
    '双十一准备囤货',
    '618有什么值得买的',
    '双十二要不要上点货',
    // —— 节气 ——
    '冬至快到了',
    '立冬那天开始用',
    // —— 相对时间 ——
    '前三天刚买了这个',
    '这周有促销吗',
    '下周末回来',
    '下个月要出差',
    // —— 负例（不应命中的数字片段）——
    '11月去日本'
  ];
  function selfTest(today) {
    return SAMPLES.map(function (s) { return { text: s, match: parseBest(s, { today: today }) }; });
  }

  return {
    FESTS: FESTS, TERMS: TERMS, MODS: MODS, RELS: RELS, SAMPLES: SAMPLES,
    parse: parse, parseBest: parseBest, describe: describe, typeName: typeName,
    todayMatch: todayMatch, scriptKeyOf: scriptKeyOf, hasOpenPool: hasOpenPool,
    resolveScript: resolveScript,
    resolveFest: resolveFest, datesOf: datesOf, selfTest: selfTest,
    ymd: ymd, addDays: addDays, shiftByUnit: shiftByUnit, SOON_DAYS: SOON_DAYS
  };
})();
