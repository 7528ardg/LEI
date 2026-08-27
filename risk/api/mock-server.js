/**
 * 客舱核心风险差异化预警系统 · Mock API 服务层
 * 实现设计手册 §7.9 API 契约
 * 浏览器端运行（基于 localStorage 持久化），无需后端依赖
 *
 * 端点清单（与 §7.9 对齐）：
 *   GET  /api/v1/risk-scores                  风险评分查询（含分页/过滤/缓存）
 *   GET  /api/v1/risk-scores/:risk_id         风险详情
 *   GET  /api/v1/risk-scores/:risk_id/factors 因子溯源
 *   GET  /api/v1/factors/:factor_id/weather   天气因子详情
 *   GET  /api/v1/factors/:factor_id/events    事件因子详情
 *   POST /api/v1/measures/:measure_id/status  管理措施状态更新
 *   GET  /api/v1/briefing/today               今日晨间简报
 *   POST /api/v1/briefing/push                推送简报到飞书
 *   POST /api/v1/reports/export               报告导出（异步任务）
 *   GET  /api/v1/reports/:task_id             查询导出任务状态
 *   GET  /api/v1/health                       健康检查
 *   POST /api/v1/auth/login                   飞书 OAuth 模拟登录
 */
(function (global) {
  'use strict';

  const STORAGE_KEY = 'cabin_risk_db_v5_gz'; // 【精简版】独立存储键，与完整版数据隔离
  const LEGACY_KEYS = []; // 【精简版】不迁移完整版旧数据
  const WEATHER_CACHE_KEY = 'cabin_risk_weather_cache_v1';
  const WEATHER_CACHE_TTL = 3 * 60 * 60 * 1000; // 3 小时缓存（毫秒）
  const TYPHOON_CACHE_KEY = 'cabin_risk_typhoon_cache_v5';
  const TYPHOON_CACHE_TTL = 6 * 60 * 60 * 1000; // 6 小时缓存（台风数据更新频率低，且CORS代理不稳定时减少对外部依赖）
  const SESSION_KEY = 'cabin_risk_session_v1';
  const AUDIT_KEY = 'cabin_risk_audit_v1';
  const LOGIN_ATTEMPTS_KEY = 'cabin_risk_login_attempts_v1';

  // ============ 工具函数 ============
  const utils = {
    now: () => new Date().toISOString(),
    today: () => new Date().toISOString().slice(0, 10),
    delay: (ms) => new Promise(r => setTimeout(r, ms)),
    uuid: () => 'xxxxxxxxxxxx4xxxyxxxxxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0;
      return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    }),
    clone: (obj) => JSON.parse(JSON.stringify(obj)),
    pick: (obj, keys) => keys.reduce((acc, k) => (obj[k] !== undefined ? (acc[k] = obj[k]) : null, acc), {})
  };

  // ============ 种子数据 ============
  // 【广州分队定制版】绩效文件导入的正式人员名单（84人，BASE→base_id='Z1-CAN'，division→班组名）
  const GZ_CREW_SEED = [
    { id:'017199', name:'黄子健', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'00753',  name:'李凯',   base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'016064', name:'李幸宗', base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'006485', name:'张桃',   base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'007576', name:'薛军',   base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'016337', name:'许裕扬', base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'011538', name:'刘献波', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'005969', name:'张陆宇', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'024395', name:'庞然',   base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'019916', name:'张奎宇', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'011623', name:'卢鑫',   base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'030695', name:'程琦淮', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'027957', name:'褚春娜', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'031207', name:'黄恩豪', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'028199', name:'范力丹', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'028980', name:'曹晨',   base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'028030', name:'方旋',   base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'027959', name:'陈雨晴', base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'028150', name:'古欣冉', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'027030', name:'熊沁垚', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'028215', name:'管李阳', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'020733', name:'黄艺蕾', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'028015', name:'冯涵书', base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'030995', name:'黎晓亮', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'027031', name:'李思颖', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'027039', name:'葛晓楠', base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'028981', name:'雷炜豪', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'027813', name:'黎鑫汝', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'028989', name:'侯鑫淼', base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'027968', name:'李梦瑶1', base_id:'Z1-CAN', division_id:'广州张露班组',  key_personnel:false },
    { id:'028982', name:'李贝贝', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'027947', name:'黄越',   base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'028971', name:'梁馨怡', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'028218', name:'江欣',   base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'027035', name:'李宇晴', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'027952', name:'梁园',   base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'027043', name:'孔近如', base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'028020', name:'卢艺方', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'027958', name:'李静雯1', base_id:'Z1-CAN', division_id:'广州李凯班组',  key_personnel:false },
    { id:'027967', name:'骆诚',   base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'018804', name:'吕梦琪', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'027099', name:'李泽彬', base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'027964', name:'田佳鑫', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'027950', name:'齐元捷', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'027049', name:'王鲁明', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'006700', name:'雷沁璇', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'028966', name:'汪世强', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'027949', name:'柳祥龙', base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'027953', name:'杨玉玲', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'017678', name:'邓书娟', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'028973', name:'卢佳妮', base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'028026', name:'张俊强', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'028045', name:'罗俊',   base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'026631', name:'张萌1', base_id:'Z1-CAN', division_id:'广州张露班组',    key_personnel:false },
    { id:'026620', name:'王荣',   base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'026628', name:'王俊',   base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'024747', name:'张硕1', base_id:'Z1-CAN', division_id:'广州张露班组',    key_personnel:false },
    { id:'031060', name:'许文祺', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'028975', name:'王晓璇', base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'027965', name:'张天乐', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'023831', name:'闫思源', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'024318', name:'王雪',   base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'028212', name:'张轩霖', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'028979', name:'余浩峰', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'028214', name:'王晶晶', base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'026624', name:'张扬',   base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'026623', name:'苑弘毅', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'027966', name:'张洋1', base_id:'Z1-CAN', division_id:'广州张露班组',    key_personnel:false },
    { id:'024022', name:'赵怡雨', base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'027951', name:'赵雅琳', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'024176', name:'郑庆妮娜', base_id:'Z1-CAN', division_id:'广州李凯班组', key_personnel:false },
    { id:'030714', name:'钟梅芝', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'029891', name:'赵怡斐', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'026632', name:'朱希苑', base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'028035', name:'周文婷', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'027956', name:'周新茹', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'027945', name:'李雅雯', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'028016', name:'周妍蓉', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false },
    { id:'013178', name:'赫美汇', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'017197', name:'于宝康', base_id:'Z1-CAN', division_id:'广州张露班组',   key_personnel:false },
    { id:'023623', name:'李佳乐', base_id:'Z1-CAN', division_id:'广州李凯班组',   key_personnel:false },
    { id:'015159', name:'覃文质', base_id:'Z1-CAN', division_id:'广州黄子健班组', key_personnel:false }
  ];

  function seedData() {
    // ==================== 结构元数据：保留（系统识别基地/维度/分队/航线必需）====================
    // 一级基地 + 分队
    // 【精简版】仅保留 综一基地 + 广州 两级结构
    const bases = [
      { id:'Z1',     name:'综一基地',  base_type:'secondary', iata:'SHA', lat:31.1979, lon:121.3360, parent_id:null },
      { id:'Z1-CAN', name:'广州',      base_type:'outstation',iata:'CAN', lat:23.3924, lon:113.2988, parent_id:'Z1' }
    ];

    // 7 大风险维度（二级分类）—— 结构元数据，保留
    const RISK_DIMENSIONS = [
      { id:'RD01', name:'空中伤人', icon:'💨', color:'var(--color-risk-high)',    is_core:true,  chapter:'客舱安全' },
      { id:'RD02', name:'疲劳管理', icon:'😴', color:'var(--color-risk-medium)',  is_core:true,  chapter:'第三章 疲劳管理' },
      { id:'RD03', name:'证照管控', icon:'📋', color:'var(--color-risk-medium)',  is_core:true,  chapter:'资质证照' },
      { id:'RD04', name:'起火冒烟', icon:'🔥', color:'var(--color-risk-high)',    is_core:true,  chapter:'客舱安全' },
      { id:'RD05', name:'舱门管控', icon:'🚪', color:'var(--color-risk-high)',    is_core:true,  chapter:'客舱安全' },
      { id:'RD06', name:'偏离程序', icon:'⚠️', color:'var(--color-risk-medium)',  is_core:false, chapter:'标准作业程序' },
      { id:'RD07', name:'紧急情况', icon:'🚨', color:'var(--color-risk-high)',    is_core:true,  chapter:'应急处置' }
    ];

    // 分队 → 【精简版】仅保留广州分队
    const divisions = [
      { id:'Z1-CAN-D1', name:'广州分队', base_id:'Z1-CAN' }
    ];

    // 班组（与分队 1:1 对应）
    const teams = divisions.map((d, i) => ({
      id: 'T-' + d.id, name: d.name + '班组', division_id: d.id, base_id: d.base_id,
      leader: '', members: []
    }));

    // 【广州分队定制版】航线数据：默认不内置示例航线（空），由用户在航线管理中手动添加多段航路
    const routes = [];

    // ==================== 业务数据：事件等为空池（用户通过Excel手动导入）；人员资料内置广州分队正式名单 ====================
    const crew_profiles = utils.clone(GZ_CREW_SEED); // 【广州分队定制版】绩效文件导入的84人名单
    const scores = [];             // 风险评分
    const events = [];             // 历史事件
    const weathers = [];           // 天气缓存
    const reportTasks = {};        // 报告任务
    return {
      meta: { version: '2.1.0', seeded_at: utils.now(), manual_version: 'v1.3', data_mode: 'import_only' },
      bases, divisions, teams, routes, risk_dimensions: RISK_DIMENSIONS,
      scores, events, weathers,
      measures: [],
      crew_profiles,
      report_tasks: reportTasks,
      briefing_log: [],
      op_history: []
    };
  }

  function buildFactors(route, turb, fatig, hasViolation, db) {
    const factors = [];
    if (turb >= 0.6) {
      factors.push({
        factor_id: `F-TURB-WX-${route.id}`,
        factor: '航路天气预报中度以上颠簸',
        weight: Number((turb * 0.4).toFixed(3)),
        source: 'weather_current',
        source_tier: 'GENERAL',
        detail: '实时气象API预报雷暴+大风，预计航路有中度颠簸'
      });
    }
    // 从真实事件数据库统计历史颠簸事件（替代硬编码随机数）
    const allEvents = db.events || [];
    const histTurbCount = allEvents.filter(e =>
      e.flight_no === route.id &&
      (e.dimension_id === 'RD01' || (e.description || '').includes('颠簸'))
    ).length;
    if (histTurbCount > 0) {
      factors.push({
        factor_id: `F-HIST-${route.id}`,
        factor: `该航线历史颠簸事件 ${histTurbCount} 起`,
        weight: Number((Math.min(histTurbCount / 10, 0.5)).toFixed(3)),
        source: 'historical_turbulence_event',
        source_tier: 'INTERNAL',
        detail: '内部事件数据库聚合统计'
      });
    }
    // 从基地画像数据获取风险特征（替代硬编码 LHW 检查）
    const baseProfile = (db.bases || []).find(b => b.id === route.base_id);
    if (baseProfile && baseProfile.risk_profile) {
      factors.push({
        factor_id: `F-PROF-${route.base_id}`,
        factor: baseProfile.risk_profile,
        weight: 0.18,
        source: 'base_profile',
        source_tier: 'INTERNAL',
        detail: '差异化画像聚类分析结果'
      });
    }
    if (hasViolation) {
      factors.push({
        factor_id: `F-FATIG-VIOLATION-${route.id}`,
        factor: '疲劳违规·零容忍（连续值勤 5 日 / FDP 超限）',
        weight: 1.0,
        source: 'fatigue_record',
        source_tier: 'INTERNAL',
        detail: 'CCMS 排班数据触发零容忍规则，疲劳分直接置 1.0'
      });
    } else if (fatig >= 0.4) {
      factors.push({
        factor_id: `F-FATIG-LOAD-${route.id}`,
        factor: '机组累积负荷接近上限',
        weight: Number((fatig * 0.25).toFixed(3)),
        source: 'fatigue_record',
        source_tier: 'INTERNAL',
        detail: '7 日累积 FDP 接近规章上限 80%'
      });
    }
    return factors.sort((a, b) => b.weight - a.weight);
  }

  function buildMeasures(level, route, hasViolation) {
    if (level === 'low') return [];
    const measures = [];
    const baseId = `M-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    if (hasViolation) {
      measures.push({
        measure_id: `${baseId}-1`,
        risk_id: `${utils.today()}_ROUTE_${route.id}_${route.base_id}`,
        measure_text: '立即调整排班，确保涉事机组满足规章休息期；对相关分队进行疲劳管理专项约谈',
        factor_refs: ['F-FATIG-VIOLATION'],
        status: 'generated',
        created_at: utils.now()
      });
    }
    if (level === 'high' || level === 'critical') {
      measures.push({
        measure_id: `${baseId}-2`,
        risk_id: `${utils.today()}_ROUTE_${route.id}_${route.base_id}`,
        measure_text: `针对 ${route.id} 航线加强客舱颠簸防范提示，乘务长在航前简报中重点宣导安全带检查与餐具固定流程`,
        factor_refs: ['F-TURB-WX', 'F-HIST'],
        status: 'generated',
        created_at: utils.now()
      });
    }
    if (level === 'critical') {
      measures.push({
        measure_id: `${baseId}-3`,
        risk_id: `${utils.today()}_ROUTE_${route.id}_${route.base_id}`,
        measure_text: '考虑调整服务程序，平飞阶段暂停热饮服务；提前与驾驶舱建立颠簸联络暗号',
        factor_refs: ['F-TURB-WX'],
        status: 'generated',
        created_at: utils.now()
      });
    }
    return measures;
  }

  // ============ 持久化 ============
  function loadDB() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const db = JSON.parse(raw);
        const seed = seedData();
        // 数据迁移：强制刷新关键结构（保证seed最新），避免旧版本缓存导致缺失或不全
        // 【P0 修复】原来只在 divisions 为空时才补，但如果是旧缓存的"不完整divisions"（仅12条SHA/PVG），也必须强制刷新
        // 策略：基地、风险维度、分队、班组统一用seed最新，这些是结构型元数据，不存用户数据
        db.bases = seed.bases;
        db.risk_dimensions = seed.risk_dimensions;
        db.divisions = seed.divisions;
        db.teams = seed.teams;
        if (!Array.isArray(db.routes)) db.routes = seed.routes;
        // 【任务2 兼容补丁】对已有db.routes，给缺失 category 的航线统一补上中文默认值（国内/国际判定）
        if (Array.isArray(db.routes) && db.routes.length > 0) {
          const INTL_ARR = new Set(['NRT','HND','KIX','ICN','GMP','CJU','BKK','DMK','SIN','KUL','HKG','MFM','TPE','KHH','LAX','JFK','SFO','ORD','LHR','CDG','FRA','SYD','MEL','YYZ','YVR','DXB','DOH']);
          db.routes.forEach(r => {
            if (!r.category) {
              const arr = (r.arr||'').toUpperCase();
              const dep = (r.dep||'').toUpperCase();
              r.category = (INTL_ARR.has(arr) || INTL_ARR.has(dep)) ? '国际' : '国内';
            } else if (typeof r.category === 'string') {
              // 将英文 category 统一转中文（后端保障也做一次，与前端 normalizeRouteCat 对应）
              const cl = r.category.toLowerCase();
              if (cl === 'domestic') r.category = '国内';
              else if (cl === 'international') r.category = '国际';
              else if (cl === 'regional') r.category = '区域/支线';
            }
          });
        }
        // 以下数据为用户/业务数据，缺失时才补
        if (!Array.isArray(db.events)) db.events = [];
        if (!Array.isArray(db.weathers)) db.weathers = [];
        if (!Array.isArray(db.scores)) db.scores = [];
        if (!Array.isArray(db.measures)) db.measures = [];
        if (!db.report_tasks) db.report_tasks = {};
        if (!Array.isArray(db.briefing_log)) db.briefing_log = [];
        if (!Array.isArray(db.op_history)) db.op_history = [];
        // 【广州分队定制版】空档案自动填充绩效文件导入的广州分队正式名单（84人）
        if (!Array.isArray(db.crew_profiles) || db.crew_profiles.length === 0) {
          db.crew_profiles = utils.clone(GZ_CREW_SEED);
        }
        // ===== 第6项（人工复核池）新增结构 =====
        if (!Array.isArray(db.reject_pool))    db.reject_pool = [];    // 待复核导入数据池
        if (!Array.isArray(db.audit_logs))     db.audit_logs = [];     // 操作审计日志（放行/删除/复核动作）
        // =======================================
        // 航线数据（广州分队定制版）：seed 不内置示例航线（空），由用户手动添加
        //  - 旧缓存（含示例航线）首次升级时一次性清空（gz_route_cleared 标记）
        //  - 之后不再强制刷新，避免清掉用户在航线管理中手动添加的航线
        if (!db.meta) db.meta = {};
        if (seed.routes.length === 0 && Array.isArray(db.routes) && db.routes.length > 0 && !db.meta.gz_route_cleared) {
          db.routes = [];
          db.meta.gz_route_cleared = true;
        }
        const seedRoutesNonEmpty = Array.isArray(seed.routes) && seed.routes.length > 0;
        const needsRouteRefresh = seedRoutesNonEmpty && (
          !Array.isArray(db.routes)
          || db.routes.length !== seed.routes.length
          || db.routes.some(r => /^9C-GZ-/.test(r.id) || (r.dep === r.arr))
          || !db.routes.every(r => seed.routes.some(s => s.id === r.id && s.dep === r.dep && s.arr === r.arr))
        );
        if (needsRouteRefresh) {
          db.routes = seed.routes;
        }
        if (!db.meta || db.meta.version !== '2.1.0') {
          db.meta = { ...db.meta, version: '2.1.0', migrated_at: utils.now(), manual_version: 'v1.3' };
          saveDB(db);
        }
        return db;
      }
      // 清理旧版本 key
      LEGACY_KEYS.forEach(k => { try { localStorage.removeItem(k); } catch (e) {} });
    } catch (e) { /* fallthrough */ }
    const seeded = seedData();
    // 第6项：初始化空池结构
    seeded.reject_pool = [];
    seeded.audit_logs = [];
    saveDB(seeded);
    return seeded;
  }

  // 展开父级基地 ID 为包含所有子基地的列表
  // 【修复问题3.1】增加 HQ_BASE_CHILDREN 兜底映射，防止 bases 表 parent_id 缺失时展开失败导致不过滤（综一出现浦东事件根因）
  // 【精简版】仅保留综一基地 → 广州 的展开映射
  const HQ_BASE_CHILDREN = {
    'Z1': ['Z1-CAN']
  };
  function expandBaseId(db, baseId) {
    if (!baseId) return null; // null 表示不过滤
    // 1) 先在 bases 表查找
    const base = (db.bases || []).find(b => b.id === baseId);
    if (base) {
      const childIds = (db.bases || [])
        .filter(b => b.parent_id === baseId)
        .map(b => b.id);
      // 合并 HQ_BASE_CHILDREN 兜底映射（去重）
      const fallback = HQ_BASE_CHILDREN[baseId] || [];
      const merged = Array.from(new Set([baseId, ...childIds, ...fallback]));
      return merged;
    }
    // 2) 在 divisions（分队）表查找：分队 → 归属基地 ID
    //    分队查询时需映射到其 base_id，使事件（base 字段存基地ID）能匹配
    const div = (db.divisions || []).find(d => d.id === baseId);
    if (div) {
      // 返回分队的 base_id（事件 base 字段存储的是基地 ID）
      // 同时包含分队自身 ID，兼容直接用分队 ID 标记的事件
      return [div.base_id, baseId];
    }
    // 3) 在 teams（小组）表查找
    const team = (db.teams || []).find(t => t.id === baseId);
    if (team) {
      const parentDiv = (db.divisions || []).find(d => d.id === team.division_id);
      if (parentDiv) return [parentDiv.base_id, baseId, parentDiv.id];
    }
    // 4) HQ_BASE_CHILDREN 兜底：如果是一级基地但 bases 表中无对应记录
    if (HQ_BASE_CHILDREN[baseId]) {
      return [baseId, ...HQ_BASE_CHILDREN[baseId]];
    }
    // 5) 兜底：返回自身
    return [baseId];
  }
  function saveDB(db) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
  }
  function resetDB() {
    const seeded = seedData();
    saveDB(seeded);
    return seeded;
  }

  // ============ 数据备份 / 导出 / 导入 ============
  // 【低风险修复】Mock 数据存于浏览器 localStorage（键 cabin_risk_db_v5），容量有限且随清缓存丢失。
  // 切换真实后端前提供导出(.json 下载)与导入(文件恢复/合并)能力，确保本地数据可安全备份与迁移。
  function dbEventCount(db) {
    const d = db || loadDB();
    return Array.isArray(d.events) ? d.events.length : 0;
  }

  // 打包为带元数据的备份 JSON 字符串
  function exportDBData() {
    const db = loadDB();
    const payload = {
      app: 'cabin-risk-warning',
      schema: 'cabin_risk_db_v5',
      version: '2.1.0',
      exported_at: utils.now(),
      event_count: dbEventCount(db),
      data: db
    };
    return JSON.stringify(payload, null, 2);
  }

  // 触发浏览器下载 .json 备份文件
  function downloadBackup() {
    const json = exportDBData();
    const blob = new Blob([json], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const ts = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = '客舱风险预警系统-数据备份-' + ts + '.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1500);
    return dbEventCount();
  }

  // 校验备份 JSON 并写入 localStorage（mode：'replace' 覆盖 / 'merge' 合并事件）
  function importDBData(jsonStr, mode) {
    mode = mode || 'replace';
    if (typeof jsonStr !== 'string' || !jsonStr.trim()) {
      const e = new Error('备份内容为空');
      e.code = 'INVALID_JSON'; throw e;
    }
    let payload;
    try { payload = JSON.parse(jsonStr); } catch (e) {
      const err = new Error('备份文件不是合法 JSON：' + e.message);
      err.code = 'INVALID_JSON'; throw err;
    }
    // 兼容两种格式：直接是 db 对象，或 { app, data: db } 包装
    let db = (payload && typeof payload === 'object' && payload.data && typeof payload.data === 'object') ? payload.data : payload;
    if (!db || typeof db !== 'object' || Array.isArray(db)) {
      const err = new Error('备份内容格式错误（缺少数据对象）');
      err.code = 'INVALID_PAYLOAD'; throw err;
    }
    // 逐字段兜底，避免不完整备份破坏运行时结构
    ['events', 'weathers', 'scores', 'measures', 'routes', 'divisions', 'bases', 'teams', 'risk_dimensions',
     'briefing_log', 'op_history', 'crew_profiles', 'reject_pool', 'audit_logs']
      .forEach(function (k) { if (!Array.isArray(db[k])) db[k] = []; });
    if (!db.report_tasks || typeof db.report_tasks !== 'object') db.report_tasks = {};
    if (!db.meta || typeof db.meta !== 'object') db.meta = {};
    // 位置数据若不完整，用 seed 兜底结构元数据
    try {
      const seed = seedData();
      if (!Array.isArray(db.bases) || db.bases.length === 0) db.bases = seed.bases;
      if (!Array.isArray(db.risk_dimensions) || db.risk_dimensions.length === 0) db.risk_dimensions = seed.risk_dimensions;
      if (!Array.isArray(db.divisions) || db.divisions.length === 0) db.divisions = seed.divisions;
      if (!Array.isArray(db.teams) || db.teams.length === 0) db.teams = seed.teams;
      if (!Array.isArray(db.routes) || db.routes.length === 0) db.routes = seed.routes;
    } catch (e) { /* ignore */ }

    // merge 模式：保留当前已有事件，追加备份中不重复的新事件
    if (mode === 'merge') {
      try {
        const before = loadDB();
        if (Array.isArray(before.events)) {
          const seen = new Set(before.events.map(function (x) { return x.id || x.event_id || JSON.stringify(x); }));
          const fresh = (db.events || []).filter(function (x) { return !seen.has(x.id || x.event_id || JSON.stringify(x)); });
          db.events = before.events.concat(fresh);
        }
      } catch (e) { /* ignore */ }
    }

    db.meta.version = '2.1.0';
    db.meta.imported_at = utils.now();
    saveDB(db);
    // 记录导入审计
    try {
      if (typeof audit === 'function') {
        audit('import_backup', { events: dbEventCount(db), mode: mode });
      }
    } catch (e) { /* ignore */ }
    return db;
  }

  // 只读返回当前数据概要（供 UI 展示）
  function dbSummary() {
    const db = loadDB();
    return {
      events: Array.isArray(db.events) ? db.events.length : 0,
      routes: Array.isArray(db.routes) ? db.routes.length : 0,
      measures: Array.isArray(db.measures) ? db.measures.length : 0,
      updated_at: (db.meta && (db.meta.imported_at || db.meta.upgraded_at)) || null
    };
  }

  // ============ 鉴权 ============
  function getSession() {
    try {
      return JSON.parse(localStorage.getItem(SESSION_KEY) || 'null');
    } catch { return null; }
  }
  function setSession(s) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(s));
  }
  function clearSession() {
    localStorage.removeItem(SESSION_KEY);
  }
  function requireAuth() {
    const s = getSession();
    if (!s || !s.token || new Date(s.expires_at) < new Date()) {
      const err = new Error('未认证');
      err.status = 401;
      err.code = 'UNAUTHORIZED';
      throw err;
    }
    // 检查 session 是否过期（30分钟）
    if (s.session_expires_at && Date.now() > s.session_expires_at) {
      clearSession();
      const err = new Error('会话已过期，请重新登录');
      err.status = 401;
      err.code = 'SESSION_EXPIRED';
      throw err;
    }
    return s;
  }

  // ============ 登录尝试限流 ============
  function getLoginAttempts() {
    try {
      return JSON.parse(localStorage.getItem(LOGIN_ATTEMPTS_KEY) || '{"attempts":0,"lockUntil":0}');
    } catch { return { attempts: 0, lockUntil: 0 }; }
  }
  function setLoginAttempts(state) {
    localStorage.setItem(LOGIN_ATTEMPTS_KEY, JSON.stringify(state));
  }
  function resetLoginAttempts() {
    setLoginAttempts({ attempts: 0, lockUntil: 0 });
  }

  // ============ 限流 ============
  // 阈值 300 次/分钟（默认 60 太低，测试套件单次运行 100+ 请求会触发误判）
  // 支持通过 CabinMockServer.configureRateLimit({ limit, window }) 自定义
  const rateLimitState = { count: 0, windowStart: Date.now(), limit: 300, window: 60000 };
  function checkRateLimit() {
    const now = Date.now();
    if (now - rateLimitState.windowStart > rateLimitState.window) {
      rateLimitState.count = 0;
      rateLimitState.windowStart = now;
    }
    rateLimitState.count++;
    if (rateLimitState.count > rateLimitState.limit) {
      const err = new Error('请求过于频繁');
      err.status = 429;
      err.code = 'RATE_LIMITED';
      err.retryAfter = Math.ceil((rateLimitState.window - (now - rateLimitState.windowStart)) / 1000);
      throw err;
    }
  }
  function configureRateLimit(opts) {
    if (opts?.limit) rateLimitState.limit = opts.limit;
    if (opts?.window) rateLimitState.window = opts.window;
    rateLimitState.count = 0;
    rateLimitState.windowStart = Date.now();
  }

  // ============ 审计日志 ============
  function audit(action, detail) {
    const log = JSON.parse(localStorage.getItem(AUDIT_KEY) || '[]');
    log.push({
      audit_id: utils.uuid(),
      action,
      detail,
      user: getSession()?.user_id || 'anonymous',
      timestamp: utils.now()
    });
    // 保留最近 500 条
    if (log.length > 500) log.splice(0, log.length - 500);
    localStorage.setItem(AUDIT_KEY, JSON.stringify(log));
  }

  // ============ 路由匹配 ============
  function matchRoute(method, path) {
    // 已注册路由
    const routes = [
      { m: 'GET',    p: '/api/v1/health',                                  fn: healthCheck },
      { m: 'POST',   p: '/api/v1/auth/login',                              fn: authLogin },
      { m: 'POST',   p: '/api/v1/auth/logout',                             fn: authLogout },
      { m: 'GET',    p: '/api/v1/auth/me',                                 fn: authMe },
      { m: 'GET',    p: '/api/v1/risk-scores',                             fn: listRiskScores },
      { m: 'GET',    p: '/api/v1/risk-scores/:risk_id',                    fn: getRiskScore },
      { m: 'GET',    p: '/api/v1/risk-scores/:risk_id/factors',            fn: getRiskFactors },
      { m: 'GET',    p: '/api/v1/factors/:factor_id/weather',              fn: getFactorWeather },
      { m: 'GET',    p: '/api/v1/factors/:factor_id/events',               fn: getFactorEvents },
      { m: 'POST',   p: '/api/v1/measures/:measure_id/status',             fn: updateMeasureStatus },
      { m: 'GET',    p: '/api/v1/briefing/today',                          fn: getBriefingToday },
      { m: 'POST',   p: '/api/v1/briefing/push',                           fn: pushBriefing },
      { m: 'POST',   p: '/api/v1/reports/export',                          fn: exportReport },
      { m: 'GET',    p: '/api/v1/reports/:task_id',                        fn: getReportTask },
      { m: 'GET',    p: '/api/v1/bases',                                   fn: listBases },
      { m: 'GET',    p: '/api/v1/audit',                                   fn: listAudit },
      { m: 'GET',    p: '/api/v1/routes',                                  fn: listRoutes },
      { m: 'POST',   p: '/api/v1/routes',                                  fn: createRoute },
      { m: 'PUT',    p: '/api/v1/routes/:route_id',                        fn: updateRoute },
      { m: 'DELETE', p: '/api/v1/routes/:route_id',                        fn: deleteRoute },
      // 风险维度与事件统计
      { m: 'GET',    p: '/api/v1/risk-dimensions',                         fn: listRiskDimensions },
      { m: 'GET',    p: '/api/v1/risk-dimensions/overview',                fn: getRiskDimensionsOverview },
      { m: 'POST',   p: '/api/v1/risk-dimensions/stats/batch',              fn: getRiskDimensionStatsBatch }, // 批处理接口：一次返回所有维度的统计（替代逐维度调用，减少并发请求）
      { m: 'GET',    p: '/api/v1/risk-dimensions/:dimension_id/stats',     fn: getRiskDimensionStats },
      { m: 'GET',    p: '/api/v1/risk-dimensions/:dimension_id/events',    fn: listDimensionEvents },
      // 行业对标
      { m: 'GET',    p: '/api/v1/industry-benchmark',                      fn: getIndustryBenchmark },
      { m: 'GET',    p: '/api/v1/events/template',                         fn: downloadEventTemplate },
      { m: 'GET',    p: '/api/v1/events/export',                           fn: exportEvents },
      { m: 'GET',    p: '/api/v1/events',                                  fn: listEvents },
      { m: 'GET',    p: '/api/v1/events/:event_id',                        fn: getEventDetail },
      { m: 'POST',   p: '/api/v1/events',                                  fn: createEvent },
      { m: 'POST',   p: '/api/v1/events/import',                           fn: importEvents },
      { m: 'PUT',    p: '/api/v1/events/:event_id',                        fn: updateEvent },
      { m: 'DELETE', p: '/api/v1/events/:event_id',                        fn: deleteEvent },
      { m: 'DELETE', p: '/api/v1/events/purge/all',                       fn: purgeAllEvents },
      // 第6项：人工复核池（被拒导入事件）
      { m: 'GET',    p: '/api/v1/reject-pool',                             fn: listRejectPool },
      { m: 'GET',    p: '/api/v1/reject-pool/count',                       fn: getRejectCount },
      { m: 'POST',   p: '/api/v1/reject-pool/:reject_id/approve',          fn: approveReject },
      { m: 'POST',   p: '/api/v1/reject-pool/:reject_id/delete',           fn: deleteReject },
      { m: 'POST',   p: '/api/v1/reject-pool/batch',                       fn: batchRejectAction },
      // 天气按时间段查询
      { m: 'GET',    p: '/api/v1/weather/timeline',                        fn: getWeatherTimeline },
      // 天气缓存状态
      { m: 'GET',    p: '/api/v1/weather/cache-status',                    fn: getWeatherCacheStatusInfo },
      // 手动刷新天气数据（3小时缓存，支持手动触发更新）
      { m: 'POST',   p: '/api/v1/weather/refresh',                         fn: manualRefreshWeather },
      // 单一航线逐小时颠簸数据
      { m: 'GET',    p: '/api/v1/weather/route/:route_id/hourly',          fn: getRouteHourlyWeather },
      { m: 'GET',    p: '/api/v1/weather/typhoons',                        fn: getActiveTyphoons },
      // 基地坐标（用于地图定位与就近基地选择）
      { m: 'GET',    p: '/api/v1/bases/coords',                            fn: listBaseCoords },
      // 航线专项风险提醒（基于历史事件联动风险维度）
      { m: 'GET',    p: '/api/v1/route-risk-alerts',                       fn: getRouteRiskAlerts },
      // 操作历史时间线（供导入操作记录使用）
      { m: 'GET',    p: '/api/v1/dev/op-history',                          fn: listOpHistory },
      // 简报审核（发送前预览与编辑）
      { m: 'POST',   p: '/api/v1/briefing/preview',                        fn: previewBriefing },
      { m: 'POST',   p: '/api/v1/briefing/send',                           fn: sendBriefing },
      // 乘务员档案
      { m: 'GET',    p: '/api/v1/crew',                                    fn: listCrew },
      { m: 'GET',    p: '/api/v1/crew/:crew_id',                           fn: getCrewDetail },
      { m: 'PUT',    p: '/api/v1/crew/:crew_id',                           fn: updateCrew },
      // 重点人员管控
      { m: 'POST',   p: '/api/v1/key-personnel/add',                       fn: addKeyPersonnel },
      { m: 'POST',   p: '/api/v1/key-personnel/remove',                    fn: removeKeyPersonnel },
      { m: 'GET',    p: '/api/v1/key-personnel',                           fn: listKeyPersonnel },
      
      // 新版今日简报（六大模块，基于真实数据）
      { m: 'GET',    p: '/api/v2/briefing/today',                          fn: getBriefingTodayV2 },
      // 简报数据下钻（按维度/基地/时段）
      { m: 'GET',    p: '/api/v2/briefing/drilldown',                      fn: getBriefingDrilldown }
    ];

    for (const r of routes) {
      if (r.m !== method) continue;
      const params = matchPath(r.p, path);
      if (params) return { handler: r.fn, params };
    }
    return null;
  }
  function matchPath(pattern, path) {
    const pp = pattern.split('/');
    const pa = path.split('/');
    if (pp.length !== pa.length) return null;
    const params = {};
    for (let i = 0; i < pp.length; i++) {
      if (pp[i].startsWith(':')) {
        params[pp[i].slice(1)] = decodeURIComponent(pa[i]);
      } else if (pp[i] !== pa[i]) {
        return null;
      }
    }
    return params;
  }

  // ============ 路由处理器 ============

  // GET /api/v1/health
  function healthCheck(_params, _query, _body) {
    return {
      status: 'ok',
      service: 'cabin-risk-mock-api',
      version: '1.1.0',
      manual_version: 'v1.3',
      time: utils.now(),
      db_records: countDB()
    };
  }

  // POST /api/v1/auth/login
  function authLogin(_params, _query, body) {
    const account = body?.account || '';
    const password = body?.password || '';
    const userIdLogin = body?.user_id || '';

    // 支持 user_id 直接登录（备用路径，用于自动登录回退）
    if (userIdLogin && !account && !password) {
      const userName = body?.user_name || '管理员';
      const baseId = body?.base_id || 'Z1'; // 【精简版】默认归属综一基地
      const session = {
        token: 'mock-' + utils.uuid(),
        user_id: userIdLogin,
        user_name: userName,
        base_id: baseId,
        role: 'manager',
        expires_at: new Date(Date.now() + 8 * 3600 * 1000).toISOString(),
        session_expires_at: Date.now() + 30 * 60 * 1000
      };
      setSession(session);
      audit('auth.login', { user_id: userIdLogin });
      return { token: session.token, expires_at: session.expires_at, user: utils.pick(session, ['user_id', 'user_name', 'base_id', 'role']) };
    }

    // 登录尝试限流检查
    const attempts = getLoginAttempts();
    if (Date.now() < attempts.lockUntil) {
      const err = new Error('登录尝试次数过多，请30秒后再试');
      err.status = 429;
      err.code = 'LOGIN_LOCKED';
      throw err;
    }

    // 验证凭据（支持多账号 - 完整白名单）
    const VALID_ACCOUNTS = {
      '028981': { password: 'LWH', name: '测试管理员', role: 'manager' },
      '031316': { password: 'XY999999', name: '管理员', role: 'admin' },
      'admin': { password: 'admin123', name: '系统管理员', role: 'admin' },
      'cabin01': { password: 'cabin2026', name: '客舱调度员', role: 'manager' },
      'cabin02': { password: 'cabin2026', name: '客舱安全员', role: 'manager' },
      'test': { password: 'test123', name: '测试用户', role: 'manager' }
    };
    const userRecord = VALID_ACCOUNTS[account];
    if (!userRecord || password !== userRecord.password) {
      attempts.attempts += 1;
      if (attempts.attempts >= 3) {
        attempts.lockUntil = Date.now() + 30000;
        setLoginAttempts(attempts);
        const err = new Error('登录尝试次数过多，请30秒后再试');
        err.status = 429;
        err.code = 'LOGIN_LOCKED';
        throw err;
      }
      setLoginAttempts(attempts);
      const err = new Error('账号或密码错误');
      err.status = 401;
      err.code = 'INVALID_CREDENTIALS';
      throw err;
    }

    // 登录成功，重置尝试次数
    resetLoginAttempts();

    const userId = body?.account || '028981';
    const userName = userRecord.name;
    const baseId = body?.base_id || 'Z1'; // 【精简版】默认归属综一基地
    const session = {
      token: 'mock-' + utils.uuid(),
      user_id: userId,
      user_name: userName,
      base_id: baseId,
      role: userRecord.role,
      expires_at: new Date(Date.now() + 8 * 3600 * 1000).toISOString(),
      session_expires_at: Date.now() + 30 * 60 * 1000 // 30分钟无操作超时
    };
    setSession(session);
    audit('auth.login', { user_id: userId });
    return { token: session.token, expires_at: session.expires_at, user: utils.pick(session, ['user_id', 'user_name', 'base_id', 'role']) };
  }

  // POST /api/v1/auth/logout
  function authLogout() {
    const s = getSession();
    clearSession();
    if (s) audit('auth.logout', { user_id: s.user_id });
    return { success: true };
  }

  // GET /api/v1/auth/me
  function authMe() {
    const s = requireAuth();
    return utils.pick(s, ['user_id', 'user_name', 'base_id', 'role', 'expires_at']);
  }

  // GET /api/v1/risk-scores
  function listRiskScores(_params, query) {
    const db = loadDB();
    const today = query.date || utils.today();
    let items = db.scores.filter(s => s.date === today);

    // 当 db.scores 中无当天数据时，从 events 动态计算风险评分
    // 确保生成模拟事件后风险卡片能联动显示
    if (items.length === 0 && db.events.length > 0) {
      items = computeScoresFromEvents(db, today);
    }

    if (query.base) {
      const baseIds = expandBaseId(db, query.base);
      items = items.filter(s => baseIds.includes(s.base_id));
    }
    if (query.level) items = items.filter(s => s.total_level === query.level);
    if (query.scope_type) items = items.filter(s => s.scope_type === query.scope_type);

    // 默认仅返回航线级评分
    if (!query.scope_type) items = items.filter(s => s.scope_type === 'ROUTE');

    // 排序：高风险优先，再按更新时间倒序
    const levelOrder = { critical: 0, high: 1, medium: 2, low: 3 };
    items.sort((a, b) => (levelOrder[a.total_level] - levelOrder[b.total_level]) || (new Date(b.updated_at) - new Date(a.updated_at)));

    const page = parseInt(query.page || '1', 10);
    const pageSize = Math.min(parseInt(query.page_size || '20', 10), 100);
    const total = items.length;
    const paged = items.slice((page - 1) * pageSize, page * pageSize);

    return {
      data: paged,
      pagination: { page, page_size: pageSize, total }
    };
  }

  // 从事件数据动态计算风险评分（当 scores 表为空时使用）
  // 按航线分组，根据事件数量/严重程度/维度分布计算风险分数
  function computeScoresFromEvents(db, today) {
    const events = db.events || [];
    if (events.length === 0) return [];
    const routes = db.routes || [];
    const dims = db.risk_dimensions || [];
    // 【修正15项】ICAO Doc 9859 SMS 风险矩阵：Risk = L(可能性 1-5) × S(严重性 1-5)
    //   严重性 S（对应 CCAR-121 / ICAO 事件严重度分类）：
    //     重 = 较大事故征候 = 4 （CCAR 严重度第2档）
    //     中 = 一般事故征候 = 2 （CCAR 严重度第3档，中等偏低）
    //     轻 = 轻微偏差 = 1     （CCAR 严重度第4档，仅训练级纠正）
    //   可能性 L（基于样本期内事件数量 N，符合 ICAO SMS 5 档发生率区间）：
    //     L=5 频繁    N≥10  （统计周期内该航线/基地每周≥2起）
    //     L=4 经常    3≤N≤9 （每月 1-3 起）
    //     L=3 偶尔    N=2    （每季度 1 起）
    //     L=2 稀少    N=1    （每半年 1 起）
    //     L=1 极罕见  N=0    （≤每年 1 起）
    //   阈值：L×S / 25 归一到 [0,1]，level：1 低 / 2 中 / 3 高 / 4 极高
    const sevWeight = { '重': 4, '中': 2, '轻': 1 };
    const levelMap = { 4: 'critical', 3: 'high', 2: 'medium', 1: 'low', 0: 'low' };

    // 按航线+基地分组事件
    const routeGroups = {};
    events.forEach(e => {
      const routeId = e.flight_no || '';
      const baseId = e.base || '';
      // 优先按航线分组；无航线的事件按基地分组
      const groupKey = routeId ? routeId : `BASE_${baseId}`;
      if (!routeGroups[groupKey]) {
        routeGroups[groupKey] = { route_id: routeId, base_id: baseId, events: [] };
      }
      routeGroups[groupKey].events.push(e);
    });

    const scores = [];
    Object.values(routeGroups).forEach(group => {
      const evts = group.events;
      if (evts.length === 0) return;
      // ===== ICAO L×S 矩阵 =====
      // S：组内最严重的严重性（SMS 推荐用"最严重事件"而不是均值，避免均值掩盖事故征候）
      const sevOrder = { '重': 3, '中': 2, '轻': 1 };
      let maxSev = '轻';
      evts.forEach(e => { if ((sevOrder[e.severity]||0) > (sevOrder[maxSev]||0)) maxSev = e.severity; });
      const S = sevWeight[maxSev] || 1;
      // L：基于事件数量的 5 档发生率（SMS 频次分级）
      const N = evts.length;
      const L = N >= 10 ? 5 : N >= 3 ? 4 : N === 2 ? 3 : N === 1 ? 2 : 1;
      // 核心风险值 = L × S（1~25）→ 归一到 [0,1]
      const riskLS = L * S;
      const score = Number((riskLS / 25).toFixed(2)); // ∈[0.04, 1.00]
      // L×S 矩阵等级：CCAR 风险矩阵 4 档
      //   critical: ≥20  (极高，不可接受)
      //   high:     12-19 (高，需立即控制措施)
      //   medium:   6-11  (中，需制定缓解措施)
      //   low:      ≤5   (低，常规监控)
      const levelNum = riskLS >= 20 ? 4 : riskLS >= 12 ? 3 : riskLS >= 6 ? 2 : 1;
      const level = levelMap[levelNum];

      // 维度分布统计
      const dimCounts = {};
      evts.forEach(e => { dimCounts[e.dimension_id] = (dimCounts[e.dimension_id] || 0) + 1; });

      // 生成 top_factors（增加 ICAO 因子溯源标签）
      const route = routes.find(r => r.id === group.route_id);
      const topFactors = Object.entries(dimCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([dimId, count]) => {
          const dim = dims.find(d => d.id === dimId);
          return {
            factor_id: `F-EVT-${dimId}-${group.route_id || group.base_id}`,
            factor: `${dim ? dim.name : dimId} ${count} 起`,
            weight: Number((count / evts.length).toFixed(3)),
            source: 'historical_event',
            source_tier: 'INTERNAL',
            detail: `ICAO SMS L×S=${L}×${S}=${riskLS}/25：${dim ? dim.name : dimId} 维度 ${count} 条，最严重="${maxSev}"`,
            icao_meta: { L, S, maxSev, N }
          };
        });

      const routeObj = route || { id: group.route_id, base_id: group.base_id };
      const riskId = `${today}_ROUTE_${routeObj.id || group.base_id}_${routeObj.base_id || group.base_id}`;
      scores.push({
        risk_id: riskId,
        date: today,
        route_id: routeObj.id || '',
        // 【修复】base_id 以事件实际所属基地为准（group.base_id 来自事件 e.base），
        // 不应用种子航线的配置基地覆盖，避免分队事件被错误归到其他基地
        base_id: group.base_id || routeObj.base_id,
        scope_type: 'ROUTE',
        scope_code: routeObj.route_path || '',
        total_score: score,
        total_level: level,
        confidence: evts.length >= 5 ? 'high' : evts.length >= 2 ? 'medium' : 'low',
        dimension_scores: dimCounts,
        top_factors: topFactors,
        suggested_measures: buildMeasures(level, routeObj, false),
        icao_risk_meta: { model: 'L×S Matrix (ICAO Doc 9859)', L, S, riskLS, normalized: score, N, maxSev },
        updated_at: evts[0].created_at || utils.now()
      });
    });
    return scores;
  }

  // GET /api/v1/risk-scores/:risk_id
  function getRiskScore(params) {
    const db = loadDB();
    let score = db.scores.find(s => s.risk_id === params.risk_id);
    // 当 scores 表无数据时，从 events 动态计算并查找
    if (!score && db.events.length > 0) {
      const computed = computeScoresFromEvents(db, utils.today());
      score = computed.find(s => s.risk_id === params.risk_id);
    }
    if (!score) {
      const err = new Error('风险评分不存在');
      err.status = 404; err.code = 'NOT_FOUND';
      throw err;
    }
    // 补充完整 top_factors 与 suggested_measures 详情
    return {
      ...score,
      top_factors: score.top_factors,
      suggested_measures: score.suggested_measures,
      related_events: db.events.filter(e => e.flight_no === score.route_id).slice(0, 5),
      related_weather: db.weathers.find(w => w.station_or_area === score.base_id)
    };
  }

  // GET /api/v1/risk-scores/:risk_id/factors
  function getRiskFactors(params) {
    const db = loadDB();
    let score = db.scores.find(s => s.risk_id === params.risk_id);
    // 当 scores 表无数据时，从 events 动态计算并查找
    if (!score && db.events.length > 0) {
      const computed = computeScoresFromEvents(db, utils.today());
      score = computed.find(s => s.risk_id === params.risk_id);
    }
    if (!score) {
      const err = new Error('风险评分不存在'); err.status = 404; err.code = 'NOT_FOUND'; throw err;
    }
    return {
      risk_id: score.risk_id,
      total_score: score.total_score,
      total_level: score.total_level,
      dimension_scores: score.dimension_scores,
      factors: score.top_factors.map(f => ({
        ...f,
        trace_available: f.source === 'weather_current' || f.source === 'historical_turbulence_event'
      }))
    };
  }

  // GET /api/v1/factors/:factor_id/weather
  function getFactorWeather(params) {
    const db = loadDB();
    // 解析 factor_id → 关联航线
    const factor = db.scores.flatMap(s => s.top_factors).find(f => f.factor_id === params.factor_id);
    if (!factor) {
      const err = new Error('因子不存在'); err.status = 404; err.code = 'NOT_FOUND'; throw err;
    }
    if (factor.source !== 'weather_current') {
      const err = new Error('该因子非天气来源'); err.status = 400; err.code = 'INVALID_FACTOR_TYPE'; throw err;
    }
    // 返回关联航线两端机场天气
    const route = db.routes.find(r => r.id === factor.factor_id.split('-').pop());
    const weathers = route
      ? db.weathers.filter(w => w.station_or_area === route.dep || w.station_or_area === route.arr)
      : [];
    return {
      factor_id: factor.factor_id,
      factor_text: factor.factor,
      weight: factor.weight,
      source_tier: factor.source_tier,
      weather_records: weathers,
      explanation: factor.detail,
      // 中文解读
      interpretation: interpretWeather(weathers, factor)
    };
  }

  // ============ 天气报文中文化 ============
  function interpretWeather(weathers, factor) {
    if (!weathers || weathers.length === 0) return { summary: '暂无天气数据' };
    const parts = [];
    weathers.forEach(w => {
      const station = w.station_or_area || '未知站点';
      const phen = w.weather_phenomena || '未知';
      const wind = w.wind_speed != null ? `${w.wind_direction || ''}${w.wind_speed}m/s` : '风速未知';
      const vis = w.visibility != null ? `${w.visibility}km` : '能见度未知';
      const temp = w.temperature != null ? `${w.temperature}°C` : '';
      const alert = w.weather_alert ? `【${w.weather_alert.headline}】` : '';
      const flightImpact = w.interpretation?.flight_impact || '';
      const recommendation = w.interpretation?.recommendation || '';

      parts.push({
        station,
        raw_summary: `${alert}${station}：${phen}，${wind}，能见度${vis}${temp ? '，温度' + temp : ''}`,
        detail: w.interpretation?.summary || `${station}当前${phen}，风速${w.wind_speed}m/s，能见度${w.visibility}km`,
        flight_impact: flightImpact,
        recommendation: recommendation
      });
    });

    // SIGMET 中文解读
    const sigmetInterp = {
      'SIGMET': '重要气象情报（SIGMET）——可能影响飞行安全的重要天气现象',
      'MODERATE TURB': '中度颠簸——飞机可能出现明显的高度或姿态变化，客舱需暂停服务并固定餐车',
      'SEVERE TURB': '严重颠簸——飞机将出现剧烈颠簸，乘务员需立即就座并系好安全带',
      'EXTREME TURB': '极端颠簸——飞机可能短暂失控，所有人员必须立即固定',
      'TS': '雷暴（Thunderstorm）——伴有强对流、颠簸、积冰及风切变，客舱需暂停所有服务',
      'MT OBSC': '山地 obscuration——山脉被云层遮蔽，影响目视参考',
      'VA': '火山灰（Volcanic Ash）——严重危害发动机及飞机系统，需绕飞',
      'FL250': '飞行高度层250（约7620米）',
      'FL330': '飞行高度层330（约10058米）',
      'ZSSS': '上海虹桥机场',
      'ZSPD': '上海浦东机场',
      'VTBS': '曼谷素万那普机场',
      'ZGSZ': '深圳宝安机场',
      'ZGGG': '广州白云机场',
      'CAN': '广州白云机场',
      'FIR': '飞行情报区（Flight Information Region）'
    };

    return {
      stations: parts,
      sigmet_glossary: sigmetInterp,
      overall_summary: parts.map(p => p.raw_summary).join('；'),
      factor_explanation: factor?.detail || ''
    };
  }

  // GET /api/v1/factors/:factor_id/events
  function getFactorEvents(params) {
    const db = loadDB();
    const factor = db.scores.flatMap(s => s.top_factors).find(f => f.factor_id === params.factor_id);
    if (!factor) {
      const err = new Error('因子不存在'); err.status = 404; err.code = 'NOT_FOUND'; throw err;
    }
    // 关联历史事件（按航线匹配）
    const routeId = factor.factor_id.split('-').pop();
    const events = db.events.filter(e => e.flight_no === routeId).slice(0, 10);
    return {
      factor_id: factor.factor_id,
      factor_text: factor.factor,
      weight: factor.weight,
      source: factor.source,
      events,
      stats: {
        total: events.length,
        by_severity: events.reduce((acc, e) => (acc[e.severity] = (acc[e.severity] || 0) + 1, acc), {}),
        by_phase: events.reduce((acc, e) => (acc[e.flight_phase] = (acc[e.flight_phase] || 0) + 1, acc), {})
      }
    };
  }

  // POST /api/v1/measures/:measure_id/status
  function updateMeasureStatus(params, _query, body) {
    requireAuth();
    const db = loadDB();
    const { status, note } = body || {};
    const validStatus = ['adopted', 'rejected', 'not_applicable', 'executed', 'verified'];
    if (!validStatus.includes(status)) {
      const err = new Error('非法状态值'); err.status = 400; err.code = 'INVALID_STATUS'; throw err;
    }

    // 在 scores 中找到包含该 measure 的记录
    let targetMeasure = null;
    let targetScore = null;
    for (const s of db.scores) {
      const m = s.suggested_measures.find(x => x.measure_id === params.measure_id);
      if (m) { targetMeasure = m; targetScore = s; break; }
    }
    if (!targetMeasure) {
      const err = new Error('措施不存在'); err.status = 404; err.code = 'NOT_FOUND'; throw err;
    }

    const prevStatus = targetMeasure.status;
    targetMeasure.status = status;
    if (note) targetMeasure.note = note;
    if (status === 'executed') targetMeasure.executed_at = utils.now();

    // 记录到措施跟踪
    db.measures.push({
      measure_id: targetMeasure.measure_id,
      risk_id: targetScore.risk_id,
      prev_status: prevStatus,
      new_status: status,
      note,
      operator: getSession().user_id,
      operated_at: utils.now()
    });

    saveDB(db);
    audit('measure.update', { measure_id: params.measure_id, prev: prevStatus, new: status });
    return { measure_id: params.measure_id, status, prev_status: prevStatus, updated_at: utils.now() };
  }

  // GET /api/v1/briefing/today
  function getBriefingToday(_params, query) {
    const db = loadDB();
    const today = utils.today();
    const baseId = query.base;
    let scores = db.scores.filter(s => s.date === today && s.scope_type === 'ROUTE');
    // 当 scores 为空时从 events 动态计算（确保模拟数据生成后简报也有数据）
    if (scores.length === 0 && db.events.length > 0) {
      scores = computeScoresFromEvents(db, today).filter(s => s.scope_type === 'ROUTE');
    }
    if (baseId) {
      const baseIds = expandBaseId(db, baseId);
      scores = scores.filter(s => baseIds.includes(s.base_id));
    }

    const levelOrder = { critical: 0, high: 1, medium: 2, low: 3 };
    scores.sort((a, b) => levelOrder[a.total_level] - levelOrder[b.total_level]);

    const top3 = scores.slice(0, 3);
    const highCount = scores.filter(s => s.total_level === 'high' || s.total_level === 'critical').length;

    return {
      date: today,
      generated_at: `${today}T07:00:00Z`,
      summary: `今日共监控 ${scores.length} 条航线评分，其中高风险 ${highCount} 条`,
      top_risks: top3.map(s => ({
        risk_id: s.risk_id,
        route_id: s.route_id,
        base_id: s.base_id,
        level: s.total_level,
        score: s.total_score,
        key_factors: s.top_factors.slice(0, 2).map(f => f.factor),
        suggested_actions: s.suggested_measures.map(m => ({ measure_id: m.measure_id, text: m.measure_text }))
      })),
      weather_alerts: db.weathers.filter(w => w.weather_alert).map(w => ({
        station: w.station_or_area,
        alert: w.weather_alert
      })),
      cert_expiry_alerts: (function() {
        const crew = db.crew_profiles || [];
        const alerts = [];
        crew.forEach(c => {
          if (baseId && c.base_id !== baseId) {
            const baseCrew = db.bases.find(b => b.id === c.base_id);
            if (!baseCrew || baseCrew.parent_id !== baseId) return;
          }
          (c.certs || []).forEach(cert => {
            if (cert.status === 'expiring' || cert.status === 'expired') {
              alerts.push({
                crew_id: c.id,
                crew_name: c.name,
                division_id: c.division_id,
                base_id: c.base_id,
                cert_name: cert.name,
                cert_status: cert.status,
                cert_exp: cert.exp,
                urgency: cert.status === 'expired' ? 'critical' : 'warning'
              });
            }
          });
        });
        return alerts;
      })(),
      key_personnel_flights: (function() {
        const todayScores = scores.filter(s => s.date === today && s.scope_type === 'ROUTE');
        const keyCrew = (db.crew_profiles || []).filter(c => c.key_personnel === true);
        const flights = [];
        todayScores.forEach(s => {
          keyCrew.forEach(c => {
            const events = (c.events || []).filter(e => {
              const route = db.routes.find(r => r.id === s.route_id);
              return route && (e.dimension_id && s.dimension_scores && s.dimension_scores[e.dimension_id] !== undefined);
            });
            if (events.length > 0 || c.base_id === s.base_id) {
              const route = db.routes.find(r => r.id === s.route_id);
              const reminder = c.key_control_items && c.key_control_items.length > 0
                ? `【${c.name}】重点管控：${c.key_control_items.join('、')}。航前请重点关注${c.key_control_items[0]}，加强监管。`
                : `【${c.name}】${c.key_reason || '重点人员'}，请加强航前沟通与安全宣导。`;
              flights.push({
                crew_id: c.id,
                crew_name: c.name,
                division_id: c.division_id,
                flight_no: s.route_id,
                route_path: route ? (route.route_path || `${route.dep}→${route.arr}`) : s.route_id,
                key_control_items: c.key_control_items || [],
                key_reason: c.key_reason || '',
                reminder
              });
            }
          });
        });
        // 去重
        const seen = new Set();
        return flights.filter(f => {
          const key = `${f.crew_id}:${f.flight_no}`;
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });
      })(),
      data_freshness: {
        weather: { status: 'fresh', last_updated: utils.now(), source: 'WeatherAPI.com（主源）/ Open-Meteo（备用源）', source_tier: 'GENERAL' },
        fatigue: { status: 'fresh', last_updated: utils.now(), source: 'CCMS' }
      },
      risk_items: (function() {
        const now = new Date();
        const curYear = now.getFullYear();
        const curMonth = now.getMonth() + 1;
        const dims = (db.risk_dimensions || []).filter(d => !d.is_total);
        const allEvents = db.events || [];
        const monthEvents = allEvents.filter(e => e.event_year === curYear && e.event_month === curMonth);
        return dims.map(d => {
          const dimEvents = allEvents.filter(e => e.dimension_id === d.id && e.event_year === curYear && e.event_month === curMonth);
          const allDimEvents = allEvents.filter(e => e.dimension_id === d.id);
          // 取最近 3-5 条事件
          const recentEvents = allDimEvents.slice(-5).map(e => ({
            event_id: e.event_id,
            event_date: e.event_date,
            description: e.description || e.label_secondary,
            severity: e.severity,
            base: e.base,
            flight_no: e.flight_no
          }));
          // 收集涉及的基础
          const bases = [...new Set(allDimEvents.map(e => e.base))].slice(0, 5);
          return {
            dimension_id: d.id,
            dimension_name: d.name,
            icon: d.icon,
            color: d.color,
            current_month_count: dimEvents.length,
            bases: bases,
            events: recentEvents,
            expandable: recentEvents.length > 3
          };
        });
      })()
    };
  }

  // POST /api/v1/briefing/push
  function pushBriefing(_params, _query, body) {
    requireAuth();
    const db = loadDB();
    const channel = body?.channel || 'feishu';
    const baseId = body?.base_id;
    const targetUserId = body?.target_user_id || '828cd2ef'; // 默认推送给飞书ID 828cd2ef
    const briefing = getBriefingToday({}, { base: baseId });

    const logEntry = {
      log_id: utils.uuid(),
      channel,
      base_id: baseId,
      target_user_id: targetUserId,
      briefing_date: briefing.date,
      pushed_at: utils.now(),
      pushed_by: getSession().user_id,
      top_risk_count: briefing.top_risks.length,
      status: 'sent',
      message: `【客舱风险预警】已向飞书用户 ${targetUserId} 推送晨间简报，包含 ${briefing.top_risks.length} 条高风险项`
    };
    db.briefing_log.push(logEntry);
    saveDB(db);
    audit('briefing.push', { channel, base_id: baseId, target_user_id: targetUserId });
    return { success: true, log_id: logEntry.log_id, pushed_at: logEntry.pushed_at, target_user_id: targetUserId, message: logEntry.message };
  }

  // POST /api/v1/reports/export
  function exportReport(_params, _query, body) {
    requireAuth();
    const db = loadDB();
    const validTypes = ['daily', 'weekly', 'topic'];
    const type = body?.type || 'daily';
    if (!validTypes.includes(type)) {
      const err = new Error('非法报告类型'); err.status = 400; err.code = 'INVALID_TYPE'; throw err;
    }

    const taskId = 'RPT-' + utils.uuid();
    const task = {
      task_id: taskId,
      type,
      format: body?.format || 'pdf',
      date_range: body?.date_range || { start: utils.today(), end: utils.today() },
      base_id: body?.base_id,
      status: 'pending',
      created_at: utils.now(),
      created_by: getSession().user_id,
      download_url: null,
      completed_at: null
    };
    db.report_tasks[taskId] = task;
    saveDB(db);
    audit('report.export', { task_id: taskId, type });

    // 模拟异步完成（3 秒后）
    setTimeout(() => {
      const fresh = loadDB();
      const t = fresh.report_tasks[taskId];
      if (t) {
        t.status = 'completed';
        t.download_url = `#/reports/${taskId}.pdf`;
        t.completed_at = utils.now();
        t.file_size = 512000; // 固定大小 500KB
        saveDB(fresh);
      }
    }, 3000);

    return { task_id: taskId, status: 'pending', created_at: task.created_at };
  }

  // GET /api/v1/reports/:task_id
  function getReportTask(params) {
    const db = loadDB();
    const task = db.report_tasks[params.task_id];
    if (!task) {
      const err = new Error('任务不存在'); err.status = 404; err.code = 'NOT_FOUND'; throw err;
    }
    return task;
  }

  // GET /api/v1/bases
  function listBases() {
    const db = loadDB();
    const sorted = db.bases.sort((a, b) => a.order - b.order);
    // 构建层级树
    const roots = sorted.filter(b => !b.parent_id);
    const tree = roots.map(r => {
      const children = sorted.filter(c => c.parent_id === r.id);
      return children.length > 0 ? { ...r, children } : { ...r };
    });
    return {
      data: sorted,
      tree: tree,
      divisions: db.divisions,
      teams: db.teams
    };
  }

  // ============ 航线管理 ============
  // GET /api/v1/routes
  function listRoutes(_params, query) {
    const db = loadDB();
    let items = utils.clone(db.routes);
    if (query.base_id) {
      const baseIds = expandBaseId(db, query.base_id);
      items = items.filter(r => baseIds.includes(r.base_id));
    }
    if (query.overnight === 'true') items = items.filter(r => r.overnight);
    return { data: items, total: items.length };
  }

  // POST /api/v1/routes
  function createRoute(_params, _query, body) {
    requireAuth();
    const db = loadDB();
    const route = {
      id: body.id || ('9C-' + utils.uuid().slice(0, 6).toUpperCase()),
      dep: body.dep || '',
      arr: body.arr || '',
      base_id: body.base_id || 'Z1', // 【精简版】默认归属综一基地
      category: body.category || '国内',
      dep_time: body.dep_time || '00:00',
      arr_time: body.arr_time || '00:00',
      overnight: !!body.overnight,
      route_path: body.route_path || null,
      // 【广州分队定制版】多段航路：途经点数组 [{code,lat,lon,name}]
      waypoints: Array.isArray(body.waypoints) ? body.waypoints : (body.waypoints_text ? body.waypoints_text : null),
      arr_time_next_day: !!body.arr_time_next_day,
      created_at: utils.now()
    };
    db.routes.push(route);
    saveDB(db);
    audit('route.create', { route_id: route.id, base_id: route.base_id });
    return route;
  }

  // PUT /api/v1/routes/:route_id
  function updateRoute(params, _query, body) {
    requireAuth();
    const db = loadDB();
    const route = db.routes.find(r => r.id === params.route_id);
    if (!route) {
      const err = new Error('航线不存在'); err.status = 404; err.code = 'NOT_FOUND'; throw err;
    }
    const allowed = ['dep', 'arr', 'base_id', 'category', 'dep_time', 'arr_time', 'overnight', 'route_path', 'arr_time_next_day', 'waypoints'];
    allowed.forEach(k => { if (body[k] !== undefined) route[k] = body[k]; });
    saveDB(db);
    audit('route.update', { route_id: route.id });
    return route;
  }

  // DELETE /api/v1/routes/:route_id
  function deleteRoute(params) {
    requireAuth();
    const db = loadDB();
    const idx = db.routes.findIndex(r => r.id === params.route_id);
    if (idx < 0) {
      const err = new Error('航线不存在'); err.status = 404; err.code = 'NOT_FOUND'; throw err;
    }
    const removed = db.routes.splice(idx, 1)[0];
    saveDB(db);
    audit('route.delete', { route_id: removed.id });
    return { success: true, deleted: removed.id };
  }

  // GET /api/v1/audit
  function listAudit(_params, query) {
    requireAuth();
    const log = JSON.parse(localStorage.getItem(AUDIT_KEY) || '[]');
    const limit = Math.min(parseInt(query.limit || '50', 10), 500);
    return {
      data: log.slice(-limit).reverse(),
      total: log.length
    };
  }

  // ============ 风险维度与事件统计 ============
  // GET /api/v1/risk-dimensions
  function listRiskDimensions() {
    const db = loadDB();
    const dims = utils.clone(db.risk_dimensions || []);
    // 增加第 8 板块：总计（虚拟维度，点击后展示 7 大维度汇总对比）
    dims.push({
      id: 'RD00',
      name: '总计',
      icon: '📊',
      color: 'var(--color-brand)',
      sub_categories: [],
      is_total: true
    });
    return { data: dims };
  }

  // ========== 全局共享：分队/基地映射缓存（Squad→Division 引擎） ==========
  // 【修复说明】原_initSquadMaps声明在getRiskDimensionsOverview函数内部，导致每次调用overview时重置缓存
  // 此外，getRiskDimensionStats/eventBelongsToDivision等函数需共享相同映射表，因此提升为模块级变量
  let _sharedSquadMaps = null;
  function getSquadMaps() {
    if (_sharedSquadMaps) return _sharedSquadMaps;
    const CN_NUMS = ['一','二','三','四','五','六'];
    const SQUAD_TO_DIVISION = {};
    for (let i = 0; i < 6; i++) { SQUAD_TO_DIVISION['虹'+(i+1)] = '虹桥'+CN_NUMS[i]+'分队'; SQUAD_TO_DIVISION['虹'+CN_NUMS[i]] = '虹桥'+CN_NUMS[i]+'分队'; }
    for (let i = 0; i < 6; i++) { SQUAD_TO_DIVISION['浦'+(i+1)] = '浦东'+CN_NUMS[i]+'分队'; SQUAD_TO_DIVISION['浦'+CN_NUMS[i]] = '浦东'+CN_NUMS[i]+'分队'; }
    // 【tailtest发现bug修复】移除 HB-1/HB-2 条目：它们和合法基地ID VALID_BASE_IDS 重名。保留石一/石家庄X 等其他映射
    for (let i = 0; i < 2; i++) { SQUAD_TO_DIVISION['石'+(i+1)] = '石'+CN_NUMS[i]+'分队'; SQUAD_TO_DIVISION['石'+CN_NUMS[i]] = '石'+CN_NUMS[i]+'分队'; SQUAD_TO_DIVISION['石家庄'+CN_NUMS[i]] = '石'+CN_NUMS[i]+'分队'; }
    for (let i = 1; i <= 2; i++) { SQUAD_TO_DIVISION['兰州'+i] = '兰州'+i+'分队'; SQUAD_TO_DIVISION['兰'+i] = '兰州'+i+'分队'; }
    const Z1_CITY = {宁波:'Z1-NBG',扬州:'Z1-YZH',南昌:'Z1-KHN',揭阳:'Z1-SWA',广州:'Z1-CAN',深圳:'Z1-SZX'};
    const Z2_CITY = {沈阳:'Z2-SHE',西安:'Z2-XIY',大连:'Z2-DLC',成都:'Z2-CTU'};
    for (const city in Z1_CITY) SQUAD_TO_DIVISION[city] = city+'分队';
    for (const city in Z2_CITY) SQUAD_TO_DIVISION[city] = city+'分队';
    SQUAD_TO_DIVISION['双照'] = '双照分队';
    const DIVISION_TO_BASE = {};
    for (let i = 0; i < 6; i++) { DIVISION_TO_BASE['虹桥'+CN_NUMS[i]+'分队'] = 'SHA'; DIVISION_TO_BASE['浦东'+CN_NUMS[i]+'分队'] = 'PVG'; }
    DIVISION_TO_BASE['石一分队'] = 'HB-1'; DIVISION_TO_BASE['石二分队'] = 'HB-2';
    DIVISION_TO_BASE['兰州1分队'] = 'LHW-1'; DIVISION_TO_BASE['兰州2分队'] = 'LHW-2';
    for (const city in Z1_CITY) DIVISION_TO_BASE[city+'分队'] = Z1_CITY[city];
    for (const city in Z2_CITY) DIVISION_TO_BASE[city+'分队'] = Z2_CITY[city];
    DIVISION_TO_BASE['双照分队'] = 'DUO';
    const SQUAD_TO_DIV_ID = {};
    for (let i = 0; i < 6; i++) { SQUAD_TO_DIV_ID['虹'+(i+1)] = 'SHA-D'+(i+1); SQUAD_TO_DIV_ID['虹'+CN_NUMS[i]] = 'SHA-D'+(i+1); }
    for (let i = 0; i < 6; i++) { SQUAD_TO_DIV_ID['浦'+(i+1)] = 'PVG-D'+(i+1); SQUAD_TO_DIV_ID['浦'+CN_NUMS[i]] = 'PVG-D'+(i+1); }
    // 【tailtest发现bug修复】移除 HB-1/HB-2 条目：它们和合法基地ID VALID_BASE_IDS 重名。保留石一/石二/石家庄X 等其他映射
    for (let i = 0; i < 2; i++) { SQUAD_TO_DIV_ID['石'+(i+1)] = 'HB-'+(i+1)+'-D1'; SQUAD_TO_DIV_ID['石'+CN_NUMS[i]] = 'HB-'+(i+1)+'-D1'; SQUAD_TO_DIV_ID['石家庄'+CN_NUMS[i]] = 'HB-'+(i+1)+'-D1'; }
    for (let i = 1; i <= 2; i++) { SQUAD_TO_DIV_ID['兰州'+i] = 'LHW-'+i+'-D1'; SQUAD_TO_DIV_ID['兰'+i] = 'LHW-'+i+'-D1'; }
    for (const city in Z1_CITY) SQUAD_TO_DIV_ID[city] = Z1_CITY[city]+'-D1';
    for (const city in Z2_CITY) SQUAD_TO_DIV_ID[city] = Z2_CITY[city]+'-D1';
    SQUAD_TO_DIV_ID['双照'] = 'DUO-D1';
    const VALID_BASE_IDS = new Set(['SHA','PVG','Z1','Z1-NBG','Z1-YZH','Z1-KHN','Z1-SWA','Z1-CAN','Z1-SZX','Z2','Z2-SHE','Z2-XIY','Z2-DLC','Z2-CTU','LHW','LHW-1','LHW-2','HB','HB-1','HB-2','DUO']);
    // 【tailtest发现bug修复】补充 分队中文名→自身 的映射，确保 e.division_name="虹桥二分队" 这类形式能正确匹配
    // 在 SQUAD_TO_DIVISION 中已建立键=短名，现在加键=全名 的条目
    Object.values(DIVISION_TO_BASE).forEach(()=>{}); // no-op，仅为了与上方DIVISION_TO_BASE保持依赖关系
    for (let i = 0; i < 6; i++) {
      SQUAD_TO_DIVISION['虹桥'+CN_NUMS[i]+'分队'] = '虹桥'+CN_NUMS[i]+'分队';
      SQUAD_TO_DIVISION['浦东'+CN_NUMS[i]+'分队'] = '浦东'+CN_NUMS[i]+'分队';
      SQUAD_TO_DIV_ID['虹桥'+CN_NUMS[i]+'分队'] = 'SHA-D'+(i+1);
      SQUAD_TO_DIV_ID['浦东'+CN_NUMS[i]+'分队'] = 'PVG-D'+(i+1);
    }
    ['石一分队','石二分队'].forEach((k,i)=>{ SQUAD_TO_DIVISION[k]=k; SQUAD_TO_DIV_ID[k] = 'HB-'+(i+1)+'-D1'; });
    ['兰州1分队','兰州2分队'].forEach((k,i)=>{ SQUAD_TO_DIVISION[k]=k; SQUAD_TO_DIV_ID[k] = 'LHW-'+(i+1)+'-D1'; });
    ['宁波分队','扬州分队','南昌分队','揭阳分队','广州分队','深圳分队'].forEach(k=>{
      SQUAD_TO_DIVISION[k]=k;
      // 反查 base_id→div_id
      for (const city in Z1_CITY) if (k === city+'分队') SQUAD_TO_DIV_ID[k] = Z1_CITY[city]+'-D1';
    });
    ['沈阳分队','西安分队','大连分队','成都分队'].forEach(k=>{
      SQUAD_TO_DIVISION[k]=k;
      for (const city in Z2_CITY) if (k === city+'分队') SQUAD_TO_DIV_ID[k] = Z2_CITY[city]+'-D1';
    });
    SQUAD_TO_DIVISION['双照分队'] = '双照分队';
    SQUAD_TO_DIV_ID['双照分队'] = 'DUO-D1';
    _sharedSquadMaps = { SQUAD_TO_DIVISION, DIVISION_TO_BASE, SQUAD_TO_DIV_ID, VALID_BASE_IDS, Z1_CITY, Z2_CITY, CN_NUMS };
    return _sharedSquadMaps;
  }
  // 对外统一版本：resolveSquad 分队解析（所有接口调用复用，消除重复定义）
  function resolveSquad(raw) {
    if (!raw) return {divName:null,divId:null,baseId:null,valid:false};
    const s = String(raw).replace(/\s/g,'').trim();
    if (!s) return {divName:null,divId:null,baseId:null,valid:false};
    const { SQUAD_TO_DIVISION, DIVISION_TO_BASE, SQUAD_TO_DIV_ID, VALID_BASE_IDS, CN_NUMS } = getSquadMaps();
    const dn = SQUAD_TO_DIVISION[s]; const di = SQUAD_TO_DIV_ID[s];
    if (dn && DIVISION_TO_BASE[dn]) return {divName:dn, divId:di||'', baseId:DIVISION_TO_BASE[dn], valid:true};
    if (VALID_BASE_IDS.has(s)) return {divName:null, divId:null, baseId:s, valid:true};
    // ===== 中文基地名称映射 =====
    const CN_BASE_MAP = {
      '虹桥基地':'SHA', '虹桥':'SHA',
      '浦东基地':'PVG', '浦东':'PVG',
      '综一基地':'Z1', '综一':'Z1',
      '综二基地':'Z2', '综二':'Z2',
      '兰州基地':'LHW', '兰州':'LHW',
      '河北基地':'HB', '河北':'HB', '石家庄':'HB',
      '双照':'DUO',
      '宁波':'Z1-NBG', '扬州':'Z1-YZH', '南昌':'Z1-KHN',
      '揭阳':'Z1-SWA', '广州':'Z1-CAN', '深圳':'Z1-SZX',
      '沈阳':'Z2-SHE', '西安':'Z2-XIY', '大连':'Z2-DLC', '成都':'Z2-CTU'
    };
    // 扩展：城市名+分队 形式（如"宁波分队"→Z1-NBG）
    const CN_SQUAD_FULL_MAP = {
      '宁波分队':'Z1-NBG','扬州分队':'Z1-YZH','南昌分队':'Z1-KHN',
      '揭阳分队':'Z1-SWA','广州分队':'Z1-CAN','深圳分队':'Z1-SZX',
      '沈阳分队':'Z2-SHE','西安分队':'Z2-XIY','大连分队':'Z2-DLC','成都分队':'Z2-CTU',
      '兰州分队':'LHW','河北分队':'HB','石家庄分队':'HB','双照分队':'DUO',
      '虹桥分队':'SHA','浦东分队':'PVG','综一分队':'Z1','综二分队':'Z2'
    };
    // 扩展：城市名+数字+队/分队 形式（如"宁波1队"→Z1-NBG-D1）
    const CN_SQUAD_NUM_MAP = (() => {
      const map = {};
      const cities = [
        { prefix:'宁波', base:'Z1-NBG', div:'Z1-NBG-D1', name:'宁波分队' },
        { prefix:'扬州', base:'Z1-YZH', div:'Z1-YZH-D1', name:'扬州分队' },
        { prefix:'南昌', base:'Z1-KHN', div:'Z1-KHN-D1', name:'南昌分队' },
        { prefix:'揭阳', base:'Z1-SWA', div:'Z1-SWA-D1', name:'揭阳分队' },
        { prefix:'广州', base:'Z1-CAN', div:'Z1-CAN-D1', name:'广州分队' },
        { prefix:'深圳', base:'Z1-SZX', div:'Z1-SZX-D1', name:'深圳分队' },
        { prefix:'沈阳', base:'Z2-SHE', div:'Z2-SHE-D1', name:'沈阳分队' },
        { prefix:'西安', base:'Z2-XIY', div:'Z2-XIY-D1', name:'西安分队' },
        { prefix:'大连', base:'Z2-DLC', div:'Z2-DLC-D1', name:'大连分队' },
        { prefix:'成都', base:'Z2-CTU', div:'Z2-CTU-D1', name:'成都分队' },
        { prefix:'兰州', base:'LHW', div:'LHW-1-D1', name:'兰州分队' },
        { prefix:'河北', base:'HB', div:'HB-1-D1', name:'河北分队' },
        { prefix:'石家庄', base:'HB', div:'HB-1-D1', name:'石家庄分队' }
      ];
      const NUMS = ['一','二','三','四','五','六'];
      cities.forEach(c => {
        // 城市1队, 城市1分队, 城市一队, 城市一分队
        for (let i = 1; i <= 6; i++) {
          map[c.prefix + i + '队'] = { baseId: c.base, divId: c.div, divName: c.name };
          map[c.prefix + i + '分队'] = { baseId: c.base, divId: c.div, divName: c.name };
          map[c.prefix + NUMS[i-1] + '队'] = { baseId: c.base, divId: c.div, divName: c.name };
          map[c.prefix + NUMS[i-1] + '分队'] = { baseId: c.base, divId: c.div, divName: c.name };
        }
      });
      return map;
    })();
    if (CN_BASE_MAP[s]) return {divName:null, divId:null, baseId:CN_BASE_MAP[s], valid:true};
    if (CN_SQUAD_FULL_MAP[s]) return {divName:null, divId:null, baseId:CN_SQUAD_FULL_MAP[s], valid:true};
    const numMatch = CN_SQUAD_NUM_MAP[s];
    if (numMatch) return {divName: numMatch.divName, divId: numMatch.divId, baseId: numMatch.baseId, valid: true};
    // ===== 中文分队名映射：虹桥一分队/虹桥一队/虹桥1队 → SHA-D1 =====
    const CN_SQUAD_MAP = {
      '虹桥一分队':'SHA-D1', '虹桥一队':'SHA-D1', '虹桥1队':'SHA-D1', '虹桥1分队':'SHA-D1',
      '虹桥二队':'SHA-D2', '虹桥2分队':'SHA-D2', '虹桥2队':'SHA-D2', '虹桥二分队':'SHA-D2',
      '虹桥三队':'SHA-D3', '虹桥3分队':'SHA-D3', '虹桥3队':'SHA-D3', '虹桥三分队':'SHA-D3',
      '虹桥四队':'SHA-D4', '虹桥4分队':'SHA-D4', '虹桥4队':'SHA-D4', '虹桥四分队':'SHA-D4',
      '虹桥五队':'SHA-D5', '虹桥5分队':'SHA-D5', '虹桥5队':'SHA-D5', '虹桥五分队':'SHA-D5',
      '虹桥六队':'SHA-D6', '虹桥6分队':'SHA-D6', '虹桥6队':'SHA-D6', '虹桥六分队':'SHA-D6',
      '浦东一分队':'PVG-D1', '浦东一队':'PVG-D1', '浦东1队':'PVG-D1', '浦东1分队':'PVG-D1',
      '浦东二队':'PVG-D2', '浦东2分队':'PVG-D2', '浦东2队':'PVG-D2', '浦东二分队':'PVG-D2',
      '浦东三队':'PVG-D3', '浦东3分队':'PVG-D3', '浦东3队':'PVG-D3', '浦东三分队':'PVG-D3',
      '浦东四队':'PVG-D4', '浦东4分队':'PVG-D4', '浦东4队':'PVG-D4', '浦东四分队':'PVG-D4',
      '浦东五队':'PVG-D5', '浦东5分队':'PVG-D5', '浦东5队':'PVG-D5', '浦东五分队':'PVG-D5',
      '浦东六队':'PVG-D6', '浦东6分队':'PVG-D6', '浦东6队':'PVG-D6', '浦东六分队':'PVG-D6',
    };
    const CN_SQUAD_BASE_MAP = {
      '虹桥':'SHA', '浦东':'PVG', '综一':'Z1', '综二':'Z2', '兰州':'LHW', '河北':'HB', '石家庄':'HB', '双照':'DUO'
    };
    // 精确匹配中文分队名
    if (CN_SQUAD_MAP[s]) {
      const divId = CN_SQUAD_MAP[s];
      const baseId = divId.split('-')[0];
      // 推断分队名
      const CN_NUMS_FULL = ['零','一','二','三','四','五','六','七','八','九','十'];
      const numMatch = s.match(/([一二三四五六])\s*(队|分队)/);
      let divName = '';
      if (numMatch) {
        const baseCn = Object.keys(CN_SQUAD_BASE_MAP).find(k => s.startsWith(k)) || '';
        if (baseCn) divName = baseCn + numMatch[1] + '分队';
      }
      return { divName: divName || '', divId, baseId, valid: true };
    }
    // 模糊匹配：以"虹桥""浦东"等开头，包含数字/中文数字的分队名
    const cnSquadMatch = s.match(/^(虹桥|浦东|综一|综二|兰州|河北|石|双照)\s*([队分]?\s*([一二三四五六]|\d)\s*队?)?$/);
    if (cnSquadMatch) {
      const baseCn = cnSquadMatch[1];
      const baseId = CN_SQUAD_BASE_MAP[baseCn === '石' ? '河北' : baseCn] || '';
      if (baseId) return {divName:null, divId:null, baseId, valid:true};
    }
    // ===== 新增兜底：解析「基地ID-分队号」格式，如 SHA-5 / PVG-2 / HB-1 / LHW-2 =====
    const hyb = s.match(/^(SHA|PVG|HB|LHW|DUO|Z1|Z2|Z1-NBG|Z1-YZH|Z1-KHN|Z1-SWA|Z1-CAN|Z1-SZX|Z2-SHE|Z2-XIY|Z2-DLC|Z2-CTU)-([1-6一二三四五六D一二三四五六]?\d*)$/);
    if (hyb) {
      const bId = hyb[1]; let sqNo = hyb[2];
      // 提取纯数字分队号
      let no = 0;
      if (/^\d+$/.test(sqNo)) no = parseInt(sqNo,10);
      else if (/^[一二三四五六]$/.test(sqNo)) no = CN_NUMS.indexOf(sqNo)+1;
      else if (/^D\d+$/.test(sqNo)) no = parseInt(sqNo.slice(1),10);
      let divName = null, divId = null;
      if (no >= 1 && no <= 6 && (bId === 'SHA' || bId === 'PVG')) {
        const prefix = bId === 'SHA' ? '虹桥' : '浦东';
        divName = prefix + CN_NUMS[no-1] + '分队';
        divId = bId + '-D' + no;
      } else if (bId === 'HB' && no >= 1 && no <= 2) {
        divName = '石' + CN_NUMS[no-1] + '分队';
        divId = bId + '-' + no + '-D1';
      } else if (bId === 'LHW' && no >= 1 && no <= 2) {
        divName = '兰州' + no + '分队';
        divId = bId + '-' + no + '-D1';
      } else if ((bId.startsWith('Z1-') || bId.startsWith('Z2-')) && no > 0) {
        const cityMap = Object.assign({}, getSquadMaps().Z1_CITY, getSquadMaps().Z2_CITY);
        let city = null;
        for (const k in cityMap) if (cityMap[k] === bId) { city = k; break; }
        if (city) { divName = city + '分队'; divId = bId + '-D1'; }
      }
      // 只要 baseId 合法，就算没有分队名也视为通过（至少能归属到基地下）
      if (VALID_BASE_IDS.has(bId)) {
        return { divName: divName || '', divId: divId || '', baseId: bId, valid: true };
      }
    }
    return {divName:null, divId:null, baseId:null, valid:false};
  }
  // 事件→分队匹配：给定事件对象和目标division_id，判断事件是否归属于该分队
  // 优先级：1.division_id严格相等 2.squad字段映射后相等 3.division_name映射后相等 4.base_id归属单分队base 5.division字段映射
  function eventBelongsToDivision(event, divisionId, divisionBaseId) {
    if (!event || !divisionId) return false;
    // 事件是否已带明确的分队归属信息（division_id / squad / 中文分队名 / 旧division字段）
    // 若带明细分队，则只归到其明确分队，不再走哈希兜底，避免同一事件被重复计入多个分队
    const hasExplicitDiv = !!(event.division_id || event.squad || event.division_name || event.division);
    const { SQUAD_TO_DIV_ID } = getSquadMaps();
    if (event.division_id === divisionId) return true;
    if (event.squad && SQUAD_TO_DIV_ID[String(event.squad).replace(/\s/g,'').trim()] === divisionId) return true;
    if (event.division_name) {
      const org = resolveSquad(event.division_name);
      if (org.valid && org.divId === divisionId) return true;
    }
    // 兼容旧数据：division字段 = squad短名 / 分队中文名
    if (event.division) {
      // 尝试 squad → div_id 映射
      if (SQUAD_TO_DIV_ID[String(event.division).replace(/\s/g,'').trim()] === divisionId) return true;
      // 尝试 resolveSquad
      const org2 = resolveSquad(event.division);
      if (org2.valid && org2.divId === divisionId) return true;
    }
    // 无明确分队信息的事件，才用哈希均匀分配到该基地所有分队（避免与上面明确匹配重复计数）
    if (hasExplicitDiv) return false;
    // 【修复】无特定分队的base事件：用事件ID哈希均匀分配到该基地所有分队
    if (event.base === divisionBaseId) {
      const allDivs = (loadDB().divisions || []).filter(d => d.base_id === divisionBaseId);
      if (allDivs.length > 0) {
        // 对事件ID做简单哈希，分配到该基地的某个分队
        const idStr = event.event_id || event.event_date || String(Math.random());
        let hash = 0;
        for (let i = 0; i < idStr.length; i++) { hash = ((hash << 5) - hash) + idStr.charCodeAt(i); hash |= 0; }
        const idx = ((hash % allDivs.length) + allDivs.length) % allDivs.length;
        if (allDivs[idx].id === divisionId) return true;
      }
    }
    // 【修复】事件base为父级基地（如Z1）时，分配到子级基地的分队
    if (event.base && divisionBaseId) {
      // 检查 event.base 是否是 divisionBaseId 的父级（如 Z1 是 Z1-NBG 的父级）
      const db = loadDB();
      const parentBase = (db.bases || []).find(b => b.id === event.base);
      if (parentBase) {
        const childIds = (db.bases || []).filter(b => b.parent_id === event.base).map(b => b.id);
        const fallback = HQ_BASE_CHILDREN[event.base] || [];
        const allChildren = new Set([...childIds, ...fallback]);
        if (allChildren.has(divisionBaseId)) {
          const childDivs = (db.divisions || []).filter(d => d.base_id === divisionBaseId);
          if (childDivs.length > 0) {
            const idStr = event.event_id || event.event_date || String(Math.random());
            let hash = 0;
            for (let i = 0; i < idStr.length; i++) { hash = ((hash << 5) - hash) + idStr.charCodeAt(i); hash |= 0; }
            const idx = ((hash % childDivs.length) + childDivs.length) % childDivs.length;
            if (childDivs[idx].id === divisionId) return true;
          }
        }
      }
    }
    return false;
  }

  // GET /api/v1/risk-dimensions/:dimension_id/stats?base_id=&year=&month=
  // ============ 总部全景：7 大风险维度总览（按月/季/年统计 + 各基地对比） ============
  // GET /api/v1/risk-dimensions/overview
  // 返回：
  //   - dimensions: 7 大维度本年每月（1-12）具体数量+占比
  //   - monthly_comparison: 各月 7 大维度数量矩阵
  //   - quarterly_comparison: 4 个季度对比
  //   - yearly_comparison: 近 3 年对比
  //   - base_breakdown: 各一级基地在每个维度下的本月案例数与占比
  function getRiskDimensionsOverview(params, query) {
    const db = loadDB();
    const dims = (db.risk_dimensions || []).filter(d => !d.is_total);
    const allEvents = db.events.slice();
    // 【修复】处理 time_range 参数：从 time_range 推断 year/month
    const now = new Date();
    let defYear = now.getFullYear(), defMonth = now.getMonth() + 1;
    const validEvents = allEvents.filter(e => e && !isNaN(e.event_year) && !isNaN(e.event_month) && e.event_year > 2000 && e.event_month >= 1 && e.event_month <= 12);
    if (validEvents.length > 0) {
      const latestEvent = validEvents.reduce((a,b)=>{
        const at = (a.event_year*12)+(a.event_month||0);
        const bt = (b.event_year*12)+(b.event_month||0);
        return at >= bt ? a : b;
      });
      if (latestEvent && latestEvent.event_year) { defYear = latestEvent.event_year; defMonth = latestEvent.event_month || 1; }
    }
    // 根据 time_range 覆盖 year/month
    // 【修复】前端发送的 time_range 值（如 this_month_vs_prev）与后端期望值（如 this_month）做映射
    if (query.time_range) {
      const TR_MAP = {
        'this_month_vs_prev': 'this_month',
        'this_month_vs_yoy': 'this_month',
        'this_quarter_vs_prev': 'this_quarter',
        'this_quarter_vs_yoy': 'this_quarter',
        'this_year_vs_prev': 'this_year',
        'last30_vs_prev30': 'this_month'
      };
      let tr = query.time_range;
      if (TR_MAP[tr]) tr = TR_MAP[tr];
      const y = now.getFullYear(), m = now.getMonth() + 1;
      // 找到指定年份中有数据的最近月份
      const findLatestMonth = (yr) => {
        const yrEvents = validEvents.filter(e => e.event_year === yr);
        if (yrEvents.length === 0) return 1;
        return yrEvents.reduce((mx, e) => Math.max(mx, e.event_month || 1), 1);
      };
      if (tr === 'this_month') { defYear = y; defMonth = m; }
      else if (tr === 'last_month') { defYear = m === 1 ? y - 1 : y; defMonth = m === 1 ? 12 : m - 1; }
      else if (tr === 'this_quarter') {
        defYear = y; defMonth = m;
      } else if (tr === 'last_quarter') {
        const q = Math.floor((m - 1) / 3) - 1;
        if (q < 0) { defYear = y - 1; defMonth = 12 + (q + 1) * 3; }
        else { defYear = y; defMonth = (q * 3) + 3; }
      } else if (tr === 'this_year') { defYear = y; defMonth = findLatestMonth(y); }
      else if (tr === 'last_year') { defYear = y - 1; defMonth = findLatestMonth(y - 1); }
      else if (tr === 'custom' && query.from && query.to) {
        const fromParts = query.from.split('-');
        const toParts = query.to.split('-');
        if (fromParts.length >= 2) { defYear = parseInt(fromParts[0],10); defMonth = parseInt(fromParts[1],10); }
        if (toParts.length >= 2) { /* 自定义范围暂只取起始月 */ }
      }
    }
    const year = query.year ? parseInt(query.year, 10) : defYear;
    const month = query.month ? parseInt(query.month, 10) : defMonth;
    const thisYearEvents = allEvents.filter(e => e.event_year === year);
    const lastYearEvents = allEvents.filter(e => e.event_year === (year - 1));
    const yearBeforeLastEvents = allEvents.filter(e => e.event_year === (year - 2));

    // 1) 每个维度每月具体数量与占比
    const dimensions = dims.map(d => {
      const monthCounts = [];
      for (let m = 1; m <= 12; m++) {
        const c = allEvents.filter(e => e.dimension_id === d.id && e.event_year === year && e.event_month === m).length;
        monthCounts.push({ month: m, count: c });
      }
      const yearTotal = monthCounts.reduce((s, x) => s + x.count, 0);
      return {
        dimension_id: d.id,
        dimension_name: d.name,
        icon: d.icon,
        color: d.color,
        year_total: yearTotal,
        monthly: monthCounts.map(mc => ({
          month: mc.month,
          count: mc.count,
          percent: yearTotal > 0 ? Number((mc.count / yearTotal * 100).toFixed(1)) : 0
        }))
      };
    });

    // 2) 月度对比矩阵：行=月份，列=各维度数量
    const monthly_comparison = [];
    for (let m = 1; m <= 12; m++) {
      const row = { month: m, dimensions: {} };
      dims.forEach(d => {
        row.dimensions[d.id] = allEvents.filter(e => e.dimension_id === d.id && e.event_year === year && e.event_month === m).length;
      });
      row.total = Object.values(row.dimensions).reduce((s, x) => s + x, 0);
      monthly_comparison.push(row);
    }

    // 3) 季度对比
    const quarterly_comparison = [
      { quarter: 'Q1', months: [1, 2, 3] },
      { quarter: 'Q2', months: [4, 5, 6] },
      { quarter: 'Q3', months: [7, 8, 9] },
      { quarter: 'Q4', months: [10, 11, 12] }
    ].map(q => {
      const row = { quarter: q.quarter, dimensions: {} };
      dims.forEach(d => {
        row.dimensions[d.id] = allEvents.filter(e => e.dimension_id === d.id && e.event_year === year && q.months.includes(e.event_month)).length;
      });
      row.total = Object.values(row.dimensions).reduce((s, x) => s + x, 0);
      return row;
    });

    // 4) 年度对比（近 3 年）
    const yearly_comparison = [
      { year: year - 2, events: yearBeforeLastEvents },
      { year: year - 1, events: lastYearEvents },
      { year: year, events: thisYearEvents }
    ].map(y => {
      const row = { year: y.year, dimensions: {} };
      dims.forEach(d => {
        row.dimensions[d.id] = y.events.filter(e => e.dimension_id === d.id).length;
      });
      row.total = Object.values(row.dimensions).reduce((s, x) => s + x, 0);
      return row;
    });

    // 5) 各基地对比明细：包含一级基地和子级基地，每个基地在每个维度下的本月案例数 + 占比
    const allBases = db.bases || [];
    const base_breakdown = allBases.map(b => {
      // 对于一级基地（有子基地），统计自身 + 子基地；对于子级基地，仅统计自身
      const baseIds = expandBaseId(db, b.id) || [b.id];
      const baseEvents = allEvents.filter(e => {
        if (e.event_year !== year || e.event_month !== month) return false;
        if (baseIds.includes(e.base)) return true;
        if (e.division_id && baseIds.includes(e.division_id)) return true;
        if (e.division && baseIds.includes(e.division)) return true;
        return false;
      });
      const dims_ = {};
      dims.forEach(d => {
        dims_[d.id] = baseEvents.filter(e => e.dimension_id === d.id).length;
      });
      const parent = b.parent_id ? (allBases.find(x => x.id === b.parent_id) || null) : null;
      return {
        base_id: b.id,
        base_name: b.name,
        is_level1: !b.parent_id,
        parent_name: parent ? parent.name : null,
        month_total: baseEvents.length,
        dimensions: dims_
      };
    });

  // 6) 分队对比明细：按分队统计各维度数据 + 每个维度最新 5 条事件预览（供前端「各分队需关注风险项目」展开展示用）
    const allDivisions = db.divisions || [];
    const matchedEventIds = new Set();
    const division_breakdown = allDivisions.map(div => {
      const divEvents = allEvents.filter(e => {
        if (e.event_year !== year || e.event_month !== month) return false;
        if (eventBelongsToDivision(e, div.id, div.base_id)) {
          matchedEventIds.add(e.event_id || e);
          return true;
        }
        return false;
      });
      const dimsDiv = {};
      const dimEventsDiv = {};
      dims.forEach(d => {
        const eInDim = divEvents.filter(e => e.dimension_id === d.id);
        dimsDiv[d.id] = eInDim.length;
        // 每个维度取最新 5 条事件预览（按 event_date DESC + created_at DESC），前端可直接渲染
        dimEventsDiv[d.id] = eInDim
          .slice()
          .sort((a, b) => {
            const da = (a.event_date || '') + '|' + (a.created_at || '');
            const db_ = (b.event_date || '') + '|' + (b.created_at || '');
            return db_.localeCompare(da);
          })
          .slice(0, 5)
          .map(e => ({
            event_id: e.event_id,
            event_date: e.event_date,
            flight_no: e.flight_no || '',
            severity: e.severity || '轻',
            label_secondary: e.label_secondary || '',
            description: e.description || ''
          }));
      });
      // 所有维度合并的最新 10 条事件（供整体面板查看全部模态）
      const recentEvents = divEvents
        .slice()
        .sort((a, b) => {
          const da = (a.event_date || '') + '|' + (a.created_at || '');
          const db_ = (b.event_date || '') + '|' + (b.created_at || '');
          return db_.localeCompare(da);
        })
        .slice(0, 10)
        .map(e => ({
          event_id: e.event_id,
          event_date: e.event_date,
          dimension_id: e.dimension_id,
          severity: e.severity || '轻',
          flight_no: e.flight_no || '',
          label_secondary: e.label_secondary || '',
          description: e.description || ''
        }));
      return {
        division_id: div.id,
        division_name: div.name,
        base_id: div.base_id,
        order: div.order,
        month_total: divEvents.length,
        dimensions: dimsDiv,
        dim_events_preview: dimEventsDiv,  // 【新增第7项】 {RD01:[evts×5], RD02:[evts×5], ...}
        recent_events: recentEvents        // 【新增第7项】 整体分队 10 条最新
      };
    });

    // base_division_fallback: 对于没有归属到任何分队的事件，按 event.base 归属到对应分队
    // 【修复·问题1】原用 .find(d=>d.base_id===e.base) 只会返回该基地第一个分队（如SHA永远匹配到SHA-D1虹一分队），
    // 导致所有无法精确定位分队的事件全部堆积到第一个分队（表现为：空中伤人全部归虹桥一分队）。
    // 修复：与 eventBelongsToDivision() 保持一致，用 event_id/event_date 哈希均匀分配到该基地所有分队。
    allEvents.forEach(e => {
      if (e.event_year !== year || e.event_month !== month) return;
      if (matchedEventIds.has(e.event_id || e)) return;
      if (!e.base) return;
      // 先按精确 base_id 查找该基地下所有分队
      let candidates = allDivisions.filter(d => d.base_id === e.base);
      // 若 event.base 是父级基地（Z1/Z2 等），用 HQ_BASE_CHILDREN 展开到子基地对应分队
      if (candidates.length === 0 && HQ_BASE_CHILDREN[e.base]) {
        const childSet = new Set(HQ_BASE_CHILDREN[e.base]);
        candidates = allDivisions.filter(d => childSet.has(d.base_id));
      }
      if (candidates.length > 0) {
        // 哈希选分队：与 eventBelongsToDivision 保持同算法
        const idStr = e.event_id || e.event_date || String(Math.random());
        let hash = 0;
        for (let i = 0; i < idStr.length; i++) { hash = ((hash << 5) - hash) + idStr.charCodeAt(i); hash |= 0; }
        const idx = ((hash % candidates.length) + candidates.length) % candidates.length;
        const targetDiv = candidates[idx];
        const entry = division_breakdown.find(d => d.division_id === targetDiv.id);
        if (entry) {
          matchedEventIds.add(e.event_id || e);
          entry.month_total += 1;
          if (e.dimension_id && entry.dimensions[e.dimension_id] !== undefined) {
            entry.dimensions[e.dimension_id] += 1;
          }
          // 同步写入 dim_events_preview，保证分队预览也能看到这些兜底分配的事件
          if (e.dimension_id && entry.dim_events_preview[e.dimension_id] && entry.dim_events_preview[e.dimension_id].length < 5) {
            entry.dim_events_preview[e.dimension_id].push({
              event_id: e.event_id,
              event_date: e.event_date,
              flight_no: e.flight_no || '',
              severity: e.severity || '轻',
              label_secondary: e.label_secondary || '',
              description: e.description || ''
            });
          }
        }
      }
    });

    // 行业对标数据（动态计算）
    const BASE_POPULATION = 3200;
    const totalEvents = thisYearEvents.length;
    const per_mille_rate = Number((totalEvents / BASE_POPULATION * 1000).toFixed(2));
    const criticalCount = thisYearEvents.filter(e => e.severity === '重').length;
    const critical_pct = totalEvents > 0 ? Number((criticalCount / totalEvents * 100).toFixed(1)) : 0;
    const closure_rate = totalEvents > 0
      ? Number(((thisYearEvents.filter(e => e.result && e.result !== '未处理').length / totalEvents) * 100).toFixed(1))
      : 100;

    // ==================== 【第10项】新增 7 种时间维度趋势对比 trend_comparison ====================
    // 工具函数：计算两个区间的 {total,dimensions}
    function _calcBucket(evtsBucket) {
      const totals = { total: evtsBucket.length, dimensions: {} };
      dims.forEach(d => { totals.dimensions[d.id] = 0; });
      evtsBucket.forEach(e => {
        if (e && e.dimension_id && totals.dimensions[e.dimension_id] !== undefined) {
          totals.dimensions[e.dimension_id]++;
        }
      });
      return totals;
    }
    function _buildComparison(currentBucket, referenceBucket, label, label_ref, timeKey) {
      // ===== 安全百分比工具：NaN/Infinity/±999% 钳制 =====
      function _safePct(absDelta, refCount) {
        if (!refCount || refCount === 0) return null;
        const raw = (absDelta / refCount) * 100;
        if (!isFinite(raw) || isNaN(raw)) return null;
        const clamped = Math.max(-999, Math.min(999, raw));
        return Number(clamped.toFixed(1));
      }
      const cur = _calcBucket(currentBucket);
      const ref = _calcBucket(referenceBucket);
      const d_abs = cur.total - ref.total;
      const d_pct = _safePct(d_abs, ref.total);
      // 整体方向：对于风险事件，越少越好。↑ 表示恶化（变多），↓ 表示改善（变少），→ 表示持平。
      const dir = (Math.abs(d_abs) === 0 || (d_pct !== null && Math.abs(d_pct) < 1.0)) ? '→'
        : (d_abs > 0 ? '↑' : '↓');
      const dimsArr = dims.map(d => {
        const c = cur.dimensions[d.id] || 0;
        const r = ref.dimensions[d.id] || 0;
        const da = c - r;
        const dp = _safePct(da, r);
        const ddir = (Math.abs(da) === 0 || (dp !== null && Math.abs(dp) < 1.0)) ? '→'
          : (da > 0 ? '↑' : '↓');
        return {
          dimension_id: d.id,
          dimension_name: d.name,
          icon: d.icon,
          color: d.color,
          current: c,
          reference: r,
          delta_abs: da,
          delta_pct: dp,
          direction: ddir
        };
      });
      return {
        key: timeKey,
        label,
        label_reference: label_ref,
        current_total: cur.total,
        reference_total: ref.total,
        delta_abs: d_abs,
        delta_pct: d_pct,
        direction: dir,
        // 结论解读：给前端直接使用
        interpretation: dir === '↓' ? '整体改善（事件数下降）' : dir === '↑' ? '整体恶化（事件数上升）' : '整体持平',
        dimensions: dimsArr
      };
    }
    function _monthEvents(y, m) { return allEvents.filter(e => e.event_year === y && e.event_month === m); }
    function _quarterEvents(y, q) {
      const mRange = q === 1 ? [1, 2, 3] : q === 2 ? [4, 5, 6] : q === 3 ? [7, 8, 9] : [10, 11, 12];
      return allEvents.filter(e => e.event_year === y && mRange.includes(e.event_month));
    }
    const curQ = Math.floor((month - 1) / 3) + 1;
    const prevQ_Month = month <= 3 ? 12 : month - 3;
    const prevQ_Year = month <= 3 ? year - 1 : year;
    const quarterOf = (m) => Math.floor((m - 1) / 3) + 1;
    // 近30天 / 上30天（用 event_date 字符串过滤）
    function _parseDate(s) {
      if (!s || typeof s !== 'string') return null;
      const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
      if (!m) return null;
      return new Date(+m[1], +m[2] - 1, +m[3]);
    }
    // 取最新事件日期作为"今天"，避免空数据库（new Date() 可能比数据超前）
    let latestDate = null;
    validEvents.forEach(e => {
      const d = _parseDate(e.event_date);
      if (d && (!latestDate || d > latestDate)) latestDate = d;
    });
    if (!latestDate) latestDate = new Date(year, month - 1, 1);
    function _lastNEvents(nDays, endDate) {
      const end = new Date(endDate); end.setHours(0, 0, 0, 0);
      const start = new Date(end); start.setDate(start.getDate() - nDays + 1);
      return allEvents.filter(e => {
        const d = _parseDate(e.event_date);
        if (!d) return false;
        return d >= start && d <= end;
      });
    }
    const last30End = new Date(latestDate);
    const prev30End = new Date(last30End); prev30End.setDate(prev30End.getDate() - 30);
    const last30 = _lastNEvents(30, last30End);
    const prev30 = _lastNEvents(30, prev30End);
    // 自定义区间（query.from / query.to）
    function _parseDateStr2(s) { if (!s) return null; const m = String(s).match(/^(\d{4})-(\d{1,2})-(\d{1,2})/); return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null; }
    let customComp = null;
    const cf = _parseDateStr2(query.from || query.date_from), ct = _parseDateStr2(query.to || query.date_to);
    if (cf && ct && ct >= cf) {
      const curC = allEvents.filter(e => {
        const d = _parseDate(e.event_date);
        if (!d) return false;
        return d >= cf && d <= ct;
      });
      // 参照期 = 等长前一个区间
      const lenDays = Math.round((ct - cf) / 86400000) + 1;
      const refEnd = new Date(cf); refEnd.setDate(refEnd.getDate() - 1);
      const refStart = new Date(refEnd); refStart.setDate(refStart.getDate() - lenDays + 1);
      const refC = allEvents.filter(e => {
        const d = _parseDate(e.event_date);
        if (!d) return false;
        return d >= refStart && d <= refEnd;
      });
      customComp = _buildComparison(curC, refC, '自定义区间', '参照（前一等长区间）', 'custom');
      customComp.custom_current = {
        from: `${cf.getFullYear()}-${String(cf.getMonth()+1).padStart(2,'0')}-${String(cf.getDate()).padStart(2,'0')}`,
        to:   `${ct.getFullYear()}-${String(ct.getMonth()+1).padStart(2,'0')}-${String(ct.getDate()).padStart(2,'0')}`
      };
      customComp.custom_reference = {
        from: `${refStart.getFullYear()}-${String(refStart.getMonth()+1).padStart(2,'0')}-${String(refStart.getDate()).padStart(2,'0')}`,
        to:   `${refEnd.getFullYear()}-${String(refEnd.getMonth()+1).padStart(2,'0')}-${String(refEnd.getDate()).padStart(2,'0')}`
      };
    }
    const trend_comparison = {
      selected: (query.time_range || query.trend || 'this_month_vs_prev'),
      custom_available: !!customComp,
      // 1) 本月 vs 上月
      this_month_vs_prev: _buildComparison(
        _monthEvents(year, month),
        month === 1 ? _monthEvents(year - 1, 12) : _monthEvents(year, month - 1),
        `本月（${year}-${String(month).padStart(2,'0')}）`,
        month === 1 ? `上月（${year-1}-12）` : `上月（${year}-${String(month-1).padStart(2,'0')}）`,
        'this_month_vs_prev'
      ),
      // 2) 本月 vs 去年同月（同比）
      this_month_vs_yoy: _buildComparison(
        _monthEvents(year, month),
        _monthEvents(year - 1, month),
        `本月（${year}-${String(month).padStart(2,'0')}）`,
        `去年同月（${year-1}-${String(month).padStart(2,'0')}）`,
        'this_month_vs_yoy'
      ),
      // 3) 本季度 vs 上季度
      this_quarter_vs_prev: _buildComparison(
        _quarterEvents(year, curQ),
        (curQ === 1 ? _quarterEvents(year - 1, 4) : _quarterEvents(year, curQ - 1)),
        `本季度（${year} Q${curQ}）`,
        curQ === 1 ? `上季度（${year-1} Q4）` : `上季度（${year} Q${curQ-1}）`,
        'this_quarter_vs_prev'
      ),
      // 4) 本季度 vs 去年同季度
      this_quarter_vs_yoy: _buildComparison(
        _quarterEvents(year, curQ),
        _quarterEvents(year - 1, curQ),
        `本季度（${year} Q${curQ}）`,
        `去年同季度（${year-1} Q${curQ}）`,
        'this_quarter_vs_yoy'
      ),
      // 5) 本年 vs 去年
      this_year_vs_prev: _buildComparison(
        thisYearEvents,
        lastYearEvents,
        `本年（${year}年）`,
        `去年（${year-1}年）`,
        'this_year_vs_prev'
      ),
      // 6) 近30天 vs 上30天
      last30_vs_prev30: _buildComparison(
        last30,
        prev30,
        '近30天（以最新事件日截止）',
        '此前30天',
        'last30_vs_prev30'
      ),
      // 7) 自定义（如有）
      custom: customComp
    };
    // 如果用户指定了 time_range，在 trend_comparison.selected 上再加一个 current 快捷字段，供前端直接读取
    const sel = trend_comparison.selected;
    if (sel && trend_comparison[sel]) {
      trend_comparison.current = trend_comparison[sel];
    } else if (trend_comparison.custom) {
      trend_comparison.current = trend_comparison.custom;
    } else {
      trend_comparison.current = trend_comparison.this_month_vs_prev;
    }

    return {
      year,
      current_month: month,
      available_years: [2024, 2025, 2026],
      dimensions,
      monthly_comparison,
      quarterly_comparison,
      yearly_comparison,
      base_breakdown,
      division_breakdown,
      trend_comparison,   // 【第10项】新增 7 种时间维度对比
      summary: {
        this_year_total: totalEvents,
        last_year_total: lastYearEvents.length,
        yoy_change: totalEvents - lastYearEvents.length,
        yoy_percent: lastYearEvents.length > 0 ? Number(((totalEvents - lastYearEvents.length) / lastYearEvents.length * 100).toFixed(1)) : null,
        per_mille_rate: per_mille_rate,
        critical_pct: critical_pct,
        closure_rate: closure_rate,
        industry_benchmark: {
          per_mille_rate: Number((totalEvents / BASE_POPULATION * 1000).toFixed(2)),
          critical_pct: critical_pct,
          closure_rate: closure_rate
        }
      }
    };
  }

  // GET /api/v1/industry-benchmark
  function getIndustryBenchmark(_params, query) {
    const db = loadDB();
    const now = new Date();
    const year = query.year ? parseInt(query.year, 10) : now.getFullYear();
    const BASE_POPULATION = 3200;
    const allEvents = db.events || [];
    const yearEvents = allEvents.filter(e => e.event_year === year);
    const totalEvents = yearEvents.length;
    const per_mille_rate = Number((totalEvents / BASE_POPULATION * 1000).toFixed(2));
    const criticalCount = yearEvents.filter(e => e.severity === '重').length;
    const critical_pct = totalEvents > 0 ? Number((criticalCount / totalEvents * 100).toFixed(1)) : 0;
    const closure_rate = totalEvents > 0
      ? Number(((yearEvents.filter(e => e.result && e.result !== '未处理').length / totalEvents) * 100).toFixed(1))
      : 100;

    // 按维度统计行业平均值
    const dims = (db.risk_dimensions || []).filter(d => !d.is_total);
    const industry_averages = dims.map(d => {
      const dimEvents = yearEvents.filter(e => e.dimension_id === d.id);
      const dimTotal = dimEvents.length;
      const dimCritical = dimEvents.filter(e => e.severity === '重').length;
      return {
        dimension_id: d.id,
        dimension_name: d.name,
        icon: d.icon,
        color: d.color,
        event_count: dimTotal,
        critical_count: dimCritical,
        critical_pct: dimTotal > 0 ? Number((dimCritical / dimTotal * 100).toFixed(1)) : 0,
        per_mille_rate: Number((dimTotal / BASE_POPULATION * 1000).toFixed(2))
      };
    });

    return {
      year,
      base_population: BASE_POPULATION,
      per_mille_rate: per_mille_rate,
      critical_pct: critical_pct,
      closure_rate: closure_rate,
      industry_averages: industry_averages,
      comparison: {
        per_mille_rate: {
          current: per_mille_rate,
          industry_avg: Number((totalEvents / BASE_POPULATION * 1000 * 0.85).toFixed(2)),
          status: per_mille_rate > (totalEvents / BASE_POPULATION * 1000 * 0.85) ? 'above' : 'below'
        },
        critical_pct: {
          current: critical_pct,
          industry_avg: 12.5,
          status: critical_pct > 12.5 ? 'above' : 'below'
        },
        closure_rate: {
          current: closure_rate,
          industry_avg: 92.0,
          status: closure_rate >= 92.0 ? 'above' : 'below'
        }
      }
    };
  }

  function getRiskDimensionStats(params, query) {
    const db = loadDB();
    const isTotal = params.dimension_id === 'RD00';
    const dim = isTotal
      ? { id: 'RD00', name: '总计', icon: '📊', color: 'var(--color-brand)', is_total: true }
      : (db.risk_dimensions || []).find(d => d.id === params.dimension_id);
    if (!dim) {
      const err = new Error('风险维度不存在'); err.status = 404; err.code = 'NOT_FOUND'; throw err;
    }
    let events = isTotal ? db.events.slice() : db.events.filter(e => e.dimension_id === dim.id);
    // 按基地/分队过滤
    if (query.base_id) {
      // 检查是否为分队 ID：分队查询时匹配 e.division_id 字段（兼容旧的 division 字段）
      const div = (db.divisions || []).find(d => d.id === query.base_id);
      if (div) {
        events = events.filter(e => {
          if (e.division_id === query.base_id || e.division === query.base_id) return true;
          if (e.division_name) {
            const orgq = resolveSquad(e.division_name);
            if (orgq.valid && orgq.divId === query.base_id) return true;
          }
          return false;
        });
      } else {
        const baseIds = expandBaseId(db, query.base_id);
        // 对于非分队（基地级别）过滤：
        // - 事件 base 字段匹配（基地 ID）
        // - OR 事件 division_id/base 属于 expandBaseId 返回的扩展列表中的任何一个
        events = events.filter(e => {
          if (baseIds.includes(e.base)) return true;
          if (e.division_id && baseIds.includes(e.division_id)) return true;
          if (e.division && baseIds.includes(e.division)) return true;
          return false;
        });
      }
    }
    // 当前年月（与 overview 保持一致：未传时默认取数据库最新事件的年月，避免全空）
    // 【修复】取最新事件时必须过滤NaN/非法year/month，避免NaN比较污染结果，最终回退到8月
    const now = new Date();
    let defYear = now.getFullYear(), defMonth = now.getMonth() + 1;
    const validDimEvents = (db.events || []).filter(e => e && !isNaN(e.event_year) && !isNaN(e.event_month) && e.event_year > 2000 && e.event_month >= 1 && e.event_month <= 12);
    const latestDimEvent = validDimEvents.length > 0 ? validDimEvents.reduce((a,b)=>{
      const at = (a.event_year*12)+(a.event_month||0);
      const bt = (b.event_year*12)+(b.event_month||0);
      return at >= bt ? a : b;
    }) : null;
    if (latestDimEvent && latestDimEvent.event_year) { defYear = latestDimEvent.event_year; defMonth = latestDimEvent.event_month || 1; }
    const year = query.year ? parseInt(query.year, 10) : defYear;
    const month = query.month ? parseInt(query.month, 10) : defMonth;

    const currentMonthCount = events.filter(e => e.event_year === year && e.event_month === month).length;
    const lastMonthDate = new Date(year, month - 2, 1);
    const lastMonthCount = events.filter(e => e.event_year === lastMonthDate.getFullYear() && e.event_month === (lastMonthDate.getMonth() + 1)).length;
    // 近 3 年同期对比
    const yearlyComparison = [];
    for (let y = year - 3; y <= year; y++) {
      yearlyComparison.push({
        year: y,
        count: events.filter(e => e.event_year === y && e.event_month === month).length
      });
    }
    // 子分类统计
    const subCategoryStats = {};
    events.forEach(e => {
      const k = e.label_secondary || '未分类';
      subCategoryStats[k] = (subCategoryStats[k] || 0) + 1;
    });
    // 当月占比（仅基于当前基地/分队范围内的事件，避免混入其他分队）
    const totalCurrentMonth = events.filter(e => e.event_year === year && e.event_month === month).length;
    const monthPercent = totalCurrentMonth > 0 ? Number((currentMonthCount / totalCurrentMonth * 100).toFixed(1)) : 0;
    // 当月排名（仅基于当前基地/分队范围内的事件，避免显示其他分队的排名）
    const dimCounts = {};
    events.filter(e => e.event_year === year && e.event_month === month).forEach(e => {
      dimCounts[e.dimension_id] = (dimCounts[e.dimension_id] || 0) + 1;
    });
    const ranking = Object.entries(dimCounts).sort((a, b) => b[1] - a[1]).map(([k, v], i) => ({ dimension_id: k, count: v, rank: i + 1 }));
    const myRank = ranking.find(r => r.dimension_id === dim.id);

    // ============ 总计板块（RD00）专属：7 大维度月/年对比 + 同比环比 ============
    let totalComparison = undefined;
    if (isTotal) {
      // 各维度本月/上月/去年同月对比
      const dimBreakdown = (db.risk_dimensions || []).map(d => {
        const dEvents = events.filter(e => e.dimension_id === d.id);
        const cur = dEvents.filter(e => e.event_year === year && e.event_month === month).length;
        const last = dEvents.filter(e => e.event_year === lastMonthDate.getFullYear() && e.event_month === (lastMonthDate.getMonth() + 1)).length;
        const lastYear = dEvents.filter(e => e.event_year === (year - 1) && e.event_month === month).length;
        return {
          dimension_id: d.id,
          dimension_name: d.name,
          icon: d.icon,
          color: d.color,
          current_month: cur,
          last_month: last,
          last_year_same_month: lastYear,
          mom_change: cur - last,                                          // 环比变化
          mom_trend: cur > last ? 'up' : cur < last ? 'down' : 'flat',    // 环比趋势
          yoy_change: cur - lastYear,                                       // 同比变化
          yoy_trend: cur > lastYear ? 'up' : cur < lastYear ? 'down' : 'flat'  // 同比趋势
        };
      });
      // 全年总数量与去年全年总数量对比
      const thisYearTotal = events.filter(e => e.event_year === year).length;
      const lastYearTotal = events.filter(e => e.event_year === (year - 1)).length;
      totalComparison = {
        dimension_breakdown: dimBreakdown,
        this_year_total: thisYearTotal,
        last_year_total: lastYearTotal,
        yoy_total_change: thisYearTotal - lastYearTotal,
        yoy_total_trend: thisYearTotal > lastYearTotal ? 'up' : thisYearTotal < lastYearTotal ? 'down' : 'flat',
        yoy_total_percent: lastYearTotal > 0 ? Number(((thisYearTotal - lastYearTotal) / lastYearTotal * 100).toFixed(1)) : null,
        current_month_total: currentMonthCount,
        last_month_total: lastMonthCount,
        mom_total_change: currentMonthCount - lastMonthCount,
        mom_total_trend: currentMonthCount > lastMonthCount ? 'up' : currentMonthCount < lastMonthCount ? 'down' : 'flat'
      };
    }

    return {
      dimension: dim,
      base_id: query.base_id || null,
      current_month: { year, month, count: currentMonthCount, percent: monthPercent, rank: myRank ? myRank.rank : null },
      last_month: { year: lastMonthDate.getFullYear(), month: lastMonthDate.getMonth() + 1, count: lastMonthCount, change: currentMonthCount - lastMonthCount, change_percent: lastMonthCount > 0 ? Number(((currentMonthCount - lastMonthCount) / lastMonthCount * 100).toFixed(1)) : null },
      yearly_comparison: yearlyComparison,
      sub_category_stats: subCategoryStats,
      total_events: events.length,
      ranking: ranking,
      total_comparison: totalComparison
    };
  }

  // POST /api/v1/risk-dimensions/stats/batch  （性能优化新增接口）
  // 批处理接口：一次请求返回所有维度的统计数据（含RD00总计），将N个维度的并发请求合并为1次请求
  // 请求Body：{ dimension_ids?: string[] | undefined, base_id?: string, year?: number, month?: number }
  // 响应：{ [dimension_id]: { stats } —— 与逐个调用 stats/:dim_id/stats 的返回数据结构一致
  function getRiskDimensionStatsBatch(_p, _q, body) {
    requireAuth();
    const req = body || {};
    const params_template = {};
    const query = {
      base_id: req.base_id || '',
      year: req.year || undefined,
      month: req.month || undefined
    };
    const db = loadDB();
    // 维度列表：如果请求中指定了dimension_ids则按指定，否则返回所有风险维度（含总计RD00）
    let dimIds = Array.isArray(req.dimension_ids) && req.dimension_ids.length > 0 ? req.dimension_ids.slice() : null;
    if (!dimIds) {
      dimIds = (db.risk_dimensions || []).map(d => d.id);
      dimIds.push('RD00');
    }
    const result = {};
    for (let i = 0; i < dimIds.length; i++) {
      const dimId = dimIds[i];
      try {
        params_template.dimension_id = dimId;
        result[dimId] = getRiskDimensionStats(params_template, query);
      } catch (e) {
        // 单个维度失败不影响其他维度
        result[dimId] = { error: e.message || 'error', dimension: { id: dimId, name: dimId } };
      }
    }
    return {
      batch_size: dimIds.length,
      requested_at: utils.now(),
      stats_by_dimension: result
    };
  }

  // GET /api/v1/risk-dimensions/:dimension_id/events?base_id=
  function listDimensionEvents(params, query) {
    const db = loadDB();
    const isTotal = params.dimension_id === 'RD00';
    const dim = isTotal
      ? { id: 'RD00', name: '总计', icon: '📊', color: 'var(--color-brand)', is_total: true }
      : (db.risk_dimensions || []).find(d => d.id === params.dimension_id);
    if (!dim) {
      const err = new Error('风险维度不存在'); err.status = 404; err.code = 'NOT_FOUND'; throw err;
    }
    let events = isTotal ? db.events.slice() : db.events.filter(e => e.dimension_id === dim.id);
    if (query.base_id) {
      // 检查是否为分队 ID：分队查询时匹配 e.division_id 字段（兼容旧的 division 字段）
      const div = (db.divisions || []).find(d => d.id === query.base_id);
      if (div) {
        events = events.filter(e => {
          if (e.division_id === query.base_id || e.division === query.base_id) return true;
          if (e.division_name) {
            const orgq = resolveSquad(e.division_name);
            if (orgq.valid && orgq.divId === query.base_id) return true;
          }
          return false;
        });
      } else {
        const baseIds = expandBaseId(db, query.base_id);
        events = events.filter(e => {
          if (baseIds.includes(e.base)) return true;
          if (e.division_id && baseIds.includes(e.division_id)) return true;
          if (e.division && baseIds.includes(e.division)) return true;
          return false;
        });
      }
    }
    // 按日期倒序
    events = events.sort((a, b) => b.event_date.localeCompare(a.event_date));
    return { data: events, total: events.length, dimension: dim };
  }

  // GET /api/v1/events?base_id=&dimension_id=&year=&month=&page_size=
  function listEvents(_params, query) {
    const db = loadDB();
    let events = utils.clone(db.events);
    if (query.base_id) {
      // 检查是否为分队 ID：分队查询时匹配 e.division_id 字段（兼容旧的 division 字段）
      const div = (db.divisions || []).find(d => d.id === query.base_id);
      if (div) {
        // 分队查询：匹配 division_id / 旧division字段 / 中文分队名(division_name)，兼容导入时 division_id 为空的旧数据
        events = events.filter(e => {
          if (e.division_id === query.base_id || e.division === query.base_id) return true;
          if (e.division_name) {
            const orgq = resolveSquad(e.division_name);
            if (orgq.valid && orgq.divId === query.base_id) return true;
          }
          return false;
        });
      } else {
        const baseIds = expandBaseId(db, query.base_id);
        events = events.filter(e => {
          if (baseIds.includes(e.base)) return true;
          if (e.division_id && baseIds.includes(e.division_id)) return true;
          if (e.division && baseIds.includes(e.division)) return true;
          return false;
        });
      }
    }
    if (query.dimension_id) events = events.filter(e => e.dimension_id === query.dimension_id);
    if (query.year) events = events.filter(e => e.event_year === parseInt(query.year, 10));
    if (query.month) events = events.filter(e => e.event_month === parseInt(query.month, 10));
    events = events.sort((a, b) => b.event_date.localeCompare(a.event_date));
    const pageSize = parseInt(query.page_size || '100', 10);
    const paged = events.slice(0, Math.min(pageSize, 1000));
    return { data: paged, total: events.length };
  }

  // GET /api/v1/events/:event_id
  function getEventDetail(params) {
    const db = loadDB();
    const evt = db.events.find(e => e.event_id === params.event_id);
    if (!evt) {
      const err = new Error('事件不存在'); err.status = 404; err.code = 'NOT_FOUND'; throw err;
    }
    // 计算该事件在当月该维度的占比与排名
    const dim = (db.risk_dimensions || []).find(d => d.id === evt.dimension_id);
    const sameMonthDimEvents = db.events.filter(e => e.dimension_id === evt.dimension_id && e.event_year === evt.event_year && e.event_month === evt.event_month);
    const sameMonthAllEvents = db.events.filter(e => e.event_year === evt.event_year && e.event_month === evt.event_month);
    const percent = sameMonthAllEvents.length > 0 ? Number((sameMonthDimEvents.length / sameMonthAllEvents.length * 100).toFixed(1)) : 0;
    // 近 3 年同期对比
    const yearlyComparison = [];
    for (let y = evt.event_year - 3; y <= evt.event_year; y++) {
      yearlyComparison.push({
        year: y,
        count: db.events.filter(e => e.dimension_id === evt.dimension_id && e.event_year === y && e.event_month === evt.event_month).length
      });
    }
    // 上月对比
    const lastMonthDate = new Date(evt.event_year, evt.event_month - 2, 1);
    const lastMonthCount = db.events.filter(e => e.dimension_id === evt.dimension_id && e.event_year === lastMonthDate.getFullYear() && e.event_month === (lastMonthDate.getMonth() + 1)).length;
    return {
      ...utils.clone(evt),
      dimension: dim,
      month_stats: {
        count_in_dim: sameMonthDimEvents.length,
        count_total: sameMonthAllEvents.length,
        percent,
        rank: (() => {
          const dimCounts = {};
          sameMonthAllEvents.forEach(e => { dimCounts[e.dimension_id] = (dimCounts[e.dimension_id] || 0) + 1; });
          return Object.entries(dimCounts).sort((a, b) => b[1] - a[1]).map(([k], i) => ({ dimension_id: k, rank: i + 1 })).find(r => r.dimension_id === evt.dimension_id)?.rank;
        })()
      },
      yearly_comparison: yearlyComparison,
      last_month_comparison: { year: lastMonthDate.getFullYear(), month: lastMonthDate.getMonth() + 1, count: lastMonthCount, change: sameMonthDimEvents.length - lastMonthCount }
    };
  }

  // POST /api/v1/events
  function createEvent(_params, _query, body) {
    requireAuth();
    const db = loadDB();
    const evt = {
      event_id: body.event_id || ('EVT-' + utils.uuid().slice(0, 8).toUpperCase()),
      event_date: body.event_date || utils.today(),
      event_year: body.event_date ? parseInt(body.event_date.slice(0, 4), 10) : new Date().getFullYear(),
      event_month: body.event_date ? parseInt(body.event_date.slice(5, 7), 10) : (new Date().getMonth() + 1),
      flight_no: body.flight_no || '',
      // 航段列已删除：route_pair 不再使用
      flight_phase: body.flight_phase || '平飞',
      severity: body.severity || '轻',
      injury_count: body.injury_count || 0,
      base: body.base || 'Z1', // 【精简版】默认综一
      division_id: body.division_id || '',
      dimension_id: body.dimension_id || 'RD01',
      label_primary: body.label_primary || '',
      label_secondary: body.label_secondary || '',
      description: body.description || '',
      cause_analysis: body.cause_analysis || '',
      result: body.result || '',
      source_doc_ref: body.source_doc_ref || '手动录入',
      source_type: body.source_type || '',
      created_at: utils.now()
    };
    // 自动填充 label_primary
    const dim = (db.risk_dimensions || []).find(d => d.id === evt.dimension_id);
    if (dim && !evt.label_primary) evt.label_primary = dim.name;
    db.events.push(evt);
    saveDB(db);
    audit('event.create', { event_id: evt.event_id, dimension_id: evt.dimension_id });
    return evt;
  }

  // PUT /api/v1/events/:event_id
  function updateEvent(params, _query, body) {
    requireAuth();
    const db = loadDB();
    const evt = db.events.find(e => e.event_id === params.event_id);
    if (!evt) {
      const err = new Error('事件不存在'); err.status = 404; err.code = 'NOT_FOUND'; throw err;
    }
    // 航段列已删除：allowed 中不再包含 route_pair
    const allowed = ['event_date', 'flight_no', 'flight_phase', 'severity', 'injury_count', 'base', 'division_id', 'dimension_id', 'label_primary', 'label_secondary', 'description', 'cause_analysis', 'result', 'source_doc_ref', 'source_type'];
    allowed.forEach(k => { if (body[k] !== undefined) evt[k] = body[k]; });
    if (body.event_date) {
      evt.event_year = parseInt(body.event_date.slice(0, 4), 10);
      evt.event_month = parseInt(body.event_date.slice(5, 7), 10);
    }
    if (body.dimension_id) {
      const dim = (db.risk_dimensions || []).find(d => d.id === body.dimension_id);
      if (dim) evt.label_primary = dim.name;
    }
    saveDB(db);
    audit('event.update', { event_id: evt.event_id });
    return evt;
  }

  // DELETE /api/v1/events/:event_id
  function deleteEvent(params) {
    requireAuth();
    const db = loadDB();
    const idx = db.events.findIndex(e => e.event_id === params.event_id);
    if (idx < 0) {
      const err = new Error('事件不存在'); err.status = 404; err.code = 'NOT_FOUND'; throw err;
    }
    const removed = db.events.splice(idx, 1)[0];
    saveDB(db);
    audit('event.delete', { event_id: removed.event_id });
    return { success: true, deleted: removed.event_id };
  }

  // DELETE /api/v1/events/purge/all  清空所有事件
  function purgeAllEvents() {
    requireAuth();
    const db = loadDB();
    const count = db.events.length;
    db.events = [];
    db.op_history = (db.op_history || []).concat({
      type: 'purge_all',
      label: '清空所有事件 ' + count + ' 条',
      detail: { deleted_count: count },
      timestamp: utils.now()
    });
    saveDB(db);
    audit('event.purge_all', { deleted_count: count });
    return { success: true, deleted_count: count };
  }

  // GET /api/v1/events/template  下载 CSV 模板（与数据-控制清单文件格式完全一致）
  // 【修复】使用英文列名（DB字段名），importEvents 的 HEADER_ALIAS 同时支持中英文，中文Excel导入仍兼容
  // 同时保证事件CSV模板包含 event_date/dimension_id/base 三个必填字段（符合集成测试断言）
  function downloadEventTemplate() {
    const headers = ['event_id', 'event_date', 'dimension_id', 'label_secondary', 'base', 'division_id', 'squad', 'responsible_person', 'severity', 'flight_no', 'description'];
    const sample = ['EVT-SAMPLE-001', '2026-05-15', 'RD06', 'SOP执行', 'SHA', 'SHA-D5', '虹5', '张三', '一般', '9C8888', '事件描述：XX航班在执行……过程中发现……'];
    const csv = '\uFEFF' + headers.join(',') + '\n' + sample.join(',');
    return { content: csv, filename: '数据-控制清单_导入模板.csv', mime_type: 'text/csv;charset=utf-8' };
  }

  // ============================================================
  // 第6项：人工复核池（被拒/失败导入事件 → 待复核 → 人工放行 / 删除）
  //   · reject_pool 字段：
  //       reject_id, row_no (1-based CSV行号), original_row (原始KV), reject_reasons:[...],
  //       normalized (import后归一化的字段), severity, can_approve, status=PENDING|APPROVED|DELETED,
  //       created_at, updated_at, processed_at, approver, processed_note
  //   · 白名单规则（can_approve=true 时可人工放行）：
  //       - 严重度 severity 为空         → 自动补 '轻'
  //       - 维度 dimension_id 不在字典     → 保留原 value + 打 UNKNOWN 标签（放行后写 description 前缀 "⚠️未知维度:"）
  //       - event_date 含中文年月日/M月D日/Y/M/D → 宽松正则转 YYYY-MM-DD
  //       - flight_no / route 全空        → 可放行（纯地面事件）
  //     ❌ 禁放行：
  //       - resolveSquad(squad/base) 完全失败且 squad/base 都非空 → 拒绝
  //       - 最终 parse 后 event_date 仍非法 YYYY-MM-DD
  // ============================================================
  const REJECT_STATUS = { PENDING:'PENDING', APPROVED:'APPROVED', DELETED:'DELETED' };

  // 写入 db.audit_logs（复核动作审计）—— 第6项专用（跟全局 audit 独立，保证可追溯）
  function _auditDb(db, action, detail) {
    if (!Array.isArray(db.audit_logs)) db.audit_logs = [];
    db.audit_logs.push({
      audit_id: 'AUD-' + utils.uuid().slice(0,8).toUpperCase(),
      action,
      detail: detail || {},
      user: getSession()?.user_id || 'anonymous',
      timestamp: utils.now()
    });
    if (db.audit_logs.length > 1000) db.audit_logs.splice(0, db.audit_logs.length - 1000);
  }

  // 计算 can_approve：一条被拒数据能否走人工放行白名单
  function _canApproveReject(item /* original normalized + reject_reasons */) {
    // 若被拒原因里包含 组织层级非法 的致命原因 → 禁放行
    const fatalOrg = (item.reject_reasons || []).some(r => (r||'').includes('无法识别为合法组织层级'));
    if (fatalOrg && (item.base || item.division || item.squad)) return { ok:false, reason:'组织层级完全无法识别，且填写了base/分队，需用户手动修改原CSV' };
    // 若最终日期仍非法（宽松转换后仍不是YYYY-MM-DD）→ 禁放行
    if (!item.event_date || !/^\d{4}-\d{2}-\d{2}$/.test(item.event_date)) return { ok:false, reason:'日期字段无法解析为 YYYY-MM-DD，需用户手动修正' };
    return { ok:true };
  }

  // 推入一条 reject_pool 记录（importEvents 中被拒或失败的行）
  function _pushRejectPool(db, { row_no, original_row, normalized, reject_reasons, import_type }) {
    if (!Array.isArray(db.reject_pool)) db.reject_pool = [];
    // 规范化用的 item（用于后续 can_approve 判定 + 放行时的数据）
    const item = Object.assign({}, normalized || original_row || {}, { reject_reasons: reject_reasons || [] });
    const ca = _canApproveReject(item);
    db.reject_pool.push({
      reject_id: 'REJ-' + utils.uuid().slice(0,10).toUpperCase(),
      row_no: row_no || 0,
      original_row: original_row || {},
      normalized: normalized || {},
      reject_reasons: reject_reasons || [],
      import_type: import_type || 'event_import',
      can_approve: ca.ok,
      cannot_approve_reason: ca.ok ? '' : (ca.reason || ''),
      status: REJECT_STATUS.PENDING,
      created_at: utils.now(),
      updated_at: utils.now(),
      processed_at: null,
      approver: null,
      processed_note: ''
    });
  }

  // 人工放行：通过 reject_id 放行 → 写入 events 表 + 白名单自动补默认值
  function _approveOne(db, rj, remark) {
    if (rj.status !== REJECT_STATUS.PENDING) throw new Error('当前记录不是待复核状态: ' + rj.status);
    if (!rj.can_approve) throw new Error('该记录被标记为禁放行，请先修改原CSV重新导入: ' + (rj.cannot_approve_reason || ''));
    const baseItem = Object.assign({}, rj.normalized || {}, rj.original_row || {});
    // ========== 白名单自动补默认值 ==========
    const fixedReasons = [];
    // (a) severity 空 → 补 '轻'
    if (!baseItem.severity || !String(baseItem.severity).trim()) { baseItem.severity = '轻'; fixedReasons.push('严重度为空→补默认"轻"'); }
    // (b) dimension_id 不在字典 → 保留原值并在 description 前加前缀 "⚠️未知维度:<原值> "
    const rdims = db.risk_dimensions || [];
    const hasDim = rdims.some(d => d.id === baseItem.dimension_id);
    if (!baseItem.dimension_id || !hasDim) {
      const origDim = baseItem.dimension_id;
      baseItem.dimension_id = 'RD06';   // 未知维度兜底放 RD06(偏离程序)
      baseItem.label_primary = rdims.find(d=>d.id==='RD06')?.name || '偏离程序';
      const prefix = origDim ? `⚠️未知维度标签:${origDim} · ` : '⚠️维度缺失·';
      baseItem.description = prefix + (baseItem.description || '');
      fixedReasons.push(origDim ? `未知维度${origDim}→归到RD06` : '维度缺失→归到RD06');
    } else {
      baseItem.label_primary = (rdims.find(d=>d.id===baseItem.dimension_id)?.name) || baseItem.label_primary || '';
    }
    // (c) 日期 → 再次宽松转 YYYY-MM-DD（can_approve 保证最终有效）
    if (baseItem.event_date && !/^\d{4}-\d{2}-\d{2}$/.test(baseItem.event_date)) {
      const orig = baseItem.event_date + '';
      let v = orig;
      if (/^\d{4}年\d{1,2}月/.test(v)) { const m=v.match(/^(\d{4})年(\d{1,2})月(\d{1,2})?/); v = m ? `${m[1]}-${String(m[2]).padStart(2,'0')}-${String(m[3]||1).padStart(2,'0')}` : v; }
      baseItem.event_date = /^\d{4}-\d{2}-\d{2}$/.test(v) ? v : baseItem.event_date;
      fixedReasons.push(`日期格式转换:${orig}→${baseItem.event_date}`);
    }
    // (d) 组织层级 → 用 resolveSquad 兜底重算一次（用户可能补了base，或之前误判）
    const sq = baseItem.base || baseItem.division || baseItem.squad;
    const org = resolveSquad(sq);
    let baseVal = ''; let divIdVal = baseItem.division_id || ''; let divNameVal = baseItem.division_name || '';
    if (org.valid) {
      baseVal = org.baseId; divIdVal = org.divId || divIdVal; divNameVal = org.divName || divNameVal;
    } else if (sq) {
      // 仍不行 → 放 UNKNOWN_BASE 但仍允许放行（不堵死）
      baseVal = 'UNKNOWN_BASE'; fixedReasons.push('base仍识别失败→写入UNKNOWN_BASE，需后续人工改');
    }
    const _ey = parseInt(baseItem.event_date.slice(0,4),10);
    const _em = parseInt(baseItem.event_date.slice(5,7),10);
    // (e) event_id 若重复 → 生成新的
    const evtId = (baseItem.event_id && !(db.events||[]).some(e=>e.event_id===baseItem.event_id))
      ? baseItem.event_id : ('EVT-APR-' + utils.uuid().slice(0,6).toUpperCase());
    // ========== 组装 event ==========
    const evt = {
      event_id: evtId,
      event_date: baseItem.event_date,
      event_year: _ey,
      event_month: _em,
      flight_no: baseItem.flight_no || '',
      flight_phase: baseItem.flight_phase || '平飞',
      severity: baseItem.severity || '轻',
      injury_count: parseInt(baseItem.injury_count,10) || 0,
      base: baseVal,
      division_id: divIdVal,
      division_name: divNameVal,
      dimension_id: baseItem.dimension_id,
      label_primary: baseItem.label_primary || (rdims.find(d=>d.id===baseItem.dimension_id)?.name) || '',
      label_secondary: baseItem.label_secondary || '',
      description: baseItem.description || '',
      cause_analysis: baseItem.cause_analysis || '',
      result: baseItem.result || '',
      responsible_person: baseItem.responsible_person || '',
      source_doc_ref: '人工复核放行' + (remark ? ' · ' + remark : '') + ' · 白名单处理:' + fixedReasons.join('; '),
      source_type: 'case_data_approved',
      created_at: utils.now()
    };
    (db.events = db.events || []).push(evt);
    rj.status = REJECT_STATUS.APPROVED;
    rj.processed_at = utils.now();
    rj.updated_at = rj.processed_at;
    rj.approver = getSession()?.user_id || 'anonymous';
    rj.processed_note = (remark || '') + (fixedReasons.length ? ' [白名单自动处理:] ' + fixedReasons.join('; ') : '');
    _auditDb(db, 'reject.approve', { reject_id: rj.reject_id, event_id: evt.event_id, fixed: fixedReasons, remark });
    return evt;
  }

  function _deleteOne(db, rj, remark) {
    if (rj.status !== REJECT_STATUS.PENDING) throw new Error('当前记录不是待复核状态: ' + rj.status);
    rj.status = REJECT_STATUS.DELETED;
    rj.processed_at = utils.now();
    rj.updated_at = rj.processed_at;
    rj.approver = getSession()?.user_id || 'anonymous';
    rj.processed_note = remark || '';
    _auditDb(db, 'reject.delete', { reject_id: rj.reject_id, remark });
  }

  // ===== 新路由 handlers =====
  function listRejectPool(_params, query) {
    requireAuth();
    const db = loadDB();
    const pool = Array.isArray(db.reject_pool) ? db.reject_pool.slice() : [];
    // 筛选：status / import_type / page
    let arr = pool;
    if (query.status && query.status !== 'ALL') arr = arr.filter(r => r.status === query.status);
    if (query.import_type) arr = arr.filter(r => r.import_type === query.import_type);
    arr.sort((a,b)=> (b.created_at||'').localeCompare(a.created_at||''));
    const page = parseInt(query.page,10) || 1;
    const size = Math.min(parseInt(query.size,10) || 50, 500);
    const total = arr.length;
    const data = arr.slice((page-1)*size, page*size);
    return { total, page, size, status_filter: query.status || 'ALL', pending_count: pool.filter(r=>r.status===REJECT_STATUS.PENDING).length, data };
  }
  function getRejectCount() {
    requireAuth();
    const db = loadDB();
    const pool = Array.isArray(db.reject_pool) ? db.reject_pool : [];
    return {
      pending: pool.filter(r=>r.status===REJECT_STATUS.PENDING).length,
      approved: pool.filter(r=>r.status===REJECT_STATUS.APPROVED).length,
      deleted: pool.filter(r=>r.status===REJECT_STATUS.DELETED).length,
      total: pool.length,
      can_approve_pending: pool.filter(r=>r.status===REJECT_STATUS.PENDING && r.can_approve).length,
      blocked_pending: pool.filter(r=>r.status===REJECT_STATUS.PENDING && !r.can_approve).length
    };
  }
  function approveReject(params, _query, body) {
    requireAuth();
    const db = loadDB();
    const rj = (db.reject_pool||[]).find(r=>r.reject_id===params.reject_id);
    if (!rj) { const e = new Error('记录不存在'); e.status=404; e.code='NOT_FOUND'; throw e; }
    const evt = _approveOne(db, rj, (body||{}).remark || '');
    saveDB(db);
    return { success:true, reject_id:rj.reject_id, event_id:evt.event_id, status:rj.status, note:rj.processed_note };
  }
  function deleteReject(params, _query, body) {
    requireAuth();
    const db = loadDB();
    const rj = (db.reject_pool||[]).find(r=>r.reject_id===params.reject_id);
    if (!rj) { const e = new Error('记录不存在'); e.status=404; e.code='NOT_FOUND'; throw e; }
    _deleteOne(db, rj, (body||{}).remark || '');
    saveDB(db);
    return { success:true, reject_id:rj.reject_id, status:rj.status };
  }
  function batchRejectAction(_params, _query, body) {
    requireAuth();
    const db = loadDB();
    const { action, reject_ids, remark } = body || {};
    if (!Array.isArray(reject_ids)) throw new Error('reject_ids 必须是数组');
    if (!['approve','delete'].includes(action)) throw new Error('非法action');
    let ok=0,fail=0,results=[];
    reject_ids.forEach(id => {
      try {
        const rj = (db.reject_pool||[]).find(r=>r.reject_id===id);
        if (!rj) throw new Error('NOT_FOUND');
        if (action==='approve') { const ev = _approveOne(db,rj,remark||''); results.push({id,ok:true,event_id:ev.event_id}); }
        else { _deleteOne(db,rj,remark||''); results.push({id,ok:true}); }
        ok++;
      } catch (e) {
        fail++; results.push({id,ok:false,error:e.message});
      }
    });
    saveDB(db);
    return { action, ok, fail, results };
  }

  // POST /api/v1/events/import  批量导入事件（记录到操作历史，支持撤回）
  // 升级：1) 组织层级映射引擎；2) 非组织层级数据自动拒绝 → **进入人工复核池（第6项优化）**；3) 航段列已删除
  function importEvents(_params, _query, body) {
    requireAuth();
    const db = loadDB();
    const items = Array.isArray(body.events) ? body.events : (body.csv_text ? parseCsv(body.csv_text) : []);
    let inserted = 0, failed = 0, rejected = 0;
    const errors = [];
    const addedIds = [];
    const rejectedDetails = [];
    const validationWarnings = []; // 【问题5】日期解析警告列表
    // 第6项：本次导入推入 reject_pool 的数量（用于前端展示）
    let intoRejectPool = 0;

    // ==================== 中文表头归一化（兼容数据-控制清单格式） ====================
    // 将中文列名映射为系统标准字段名，并处理日期/维度格式
    const HEADER_ALIAS = {
      '时间':'event_date', '日期':'event_date', 'event_date':'event_date', 'date':'event_date', '发生日期':'event_date', '事件日期':'event_date',
      '一级风险主标签':'dimension_id', '问题类型':'dimension_id', '风险维度':'dimension_id', '维度':'dimension_id', 'dimension_id':'dimension_id',
      '二级分类':'label_secondary', '子分类':'label_secondary', 'label_secondary':'label_secondary', 'sub_category':'label_secondary',
      '责任人':'responsible_person', '负责人':'responsible_person', '当事人':'responsible_person', 'responsible_person':'responsible_person',
      '分队':'base', '基地':'base', '所属基地':'base', 'base':'base',
      '问题描述':'description', '事件描述':'description', '描述':'description', 'description':'description',
      '问题等级':'severity', '严重程度':'severity', '程度':'severity', '等级':'severity', 'severity':'severity',
      '原因分析':'cause_analysis', '原因':'cause_analysis', 'cause_analysis':'cause_analysis',
      '处理结果':'result', '结果':'result', 'result':'result',
      '航班号':'flight_no', '航班':'flight_no', 'flight_no':'flight_no',
    };
    const DIM_NAME_MAP = {'空中伤人':'RD01','疲劳管理':'RD02','证照管控':'RD03','起火冒烟':'RD04','舱门管控':'RD05','偏离程序':'RD06','紧急情况':'RD07'};
    const SUB_CAT_TO_DIM = {'颠簸防范':'RD01','客舱监控':'RD01','健康管理':'RD02','酒精管理':'RD02','无关事宜（含作风）':'RD02','无关事宜(含作风)':'RD02','证照管控':'RD03','锂电池管控':'RD04','舱门管控':'RD05','出口评估':'RD05','安保检查':'RD06','安全检查':'RD06','设备检查':'RD06','规章标准':'RD06','分队日常管理':'RD06','客舱机组准备会':'RD06','客舱SOP执行':'RD06','业务知识':'RD06','驻外管理':'RD06','装具携带':'RD06','误放氧气面罩':'RD07'};
    // ===== RD06偏离程序·10个标准系统定义子类 + 归一化引擎 =====
    const RD06_STD_SUBCATS = ['安保检查','安全检查','设备检查','规章标准','分队日常管理','客舱机组准备会','客舱SOP执行','业务知识','驻外管理','装具携带'];
    const RD06_ALIAS_MAP = {
      '安保':              '安保检查', '安保核查':         '安保检查', '客舱安保':         '安保检查', '航空安保':         '安保检查',
      '安检':              '安全检查', '安全核查':         '安全检查', '清舱检查':         '安全检查', '安全管理':         '安全检查',
      '设备':              '设备检查', '设备维护':         '设备检查', '设备故障':         '设备检查', '应急设备':         '设备检查', '客舱设备':         '设备检查',
      '规章':              '规章标准', '标准':             '规章标准', '制度':             '规章标准', '手册':             '规章标准', '规章程序':         '规章标准', '合规':             '规章标准',
      '分队管理':          '分队日常管理', '日常管理':       '分队日常管理', '分队建设':         '分队日常管理', '班组管理':         '分队日常管理', '日常工作':         '分队日常管理',
      '准备会':            '客舱机组准备会', '机组准备会':     '客舱机组准备会', '航前准备会':       '客舱机组准备会', '乘务准备会':       '客舱机组准备会', 'briefing':         '客舱机组准备会',
      'SOP':               '客舱SOP执行', 'sop':             '客舱SOP执行', '标准作业程序':     '客舱SOP执行', '服务程序':         '客舱SOP执行', '服务规范':         '客舱SOP执行', '程序执行':         '客舱SOP执行', 'SOP执行':          '客舱SOP执行',
      '业务':              '业务知识', '业务能力':         '业务知识', '培训':             '业务知识', '考核':             '业务知识', '理论知识':         '业务知识',
      '驻外':              '驻外管理', '驻外期间':         '驻外管理', '国际驻外':         '驻外管理', '过夜管理':         '驻外管理',
      '装具':              '装具携带', '携带物品':         '装具携带', '行李':             '装具携带', '个人装具':         '装具携带', '装备':             '装具携带'
    };
    function normalizeRD06SubCat(raw) {
      if (!raw) return '';
      const s = String(raw).trim().replace(/\s+/g,'');
      if (!s) return '';
      // 1) 精确匹配
      if (RD06_STD_SUBCATS.includes(s)) return s;
      // 2) 别名精确匹配
      if (RD06_ALIAS_MAP[s]) return RD06_ALIAS_MAP[s];
      // 3) 包含匹配（标准子类名出现在输入中）
      for (const std of RD06_STD_SUBCATS) { if (s.includes(std)) return std; }
      // 4) 别名包含匹配（如输入含"安保"→安保检查）
      const keys = Object.keys(RD06_ALIAS_MAP);
      for (const k of keys) { if (s.includes(k)) return RD06_ALIAS_MAP[k]; }
      // 5) 文本关键字扫描回退：输入/描述文本扫到的第一个子类关键字
      return '';
    }
    const originalRows = items.slice(); // 【第6项】保存原始KV行以便 reject_pool 回溯
    const normalizedItems = items.map((item, idx) => {
      const normalized = {};
      for (const key in item) {
        const lk = String(key).toLowerCase();
        const sysKey = HEADER_ALIAS[key] || HEADER_ALIAS[lk] || key;
        if (sysKey) normalized[sysKey] = item[key];
      }
      // 【修复问题5】日期格式处理：Excel序列号 / "2024年11月" / "2024.5" / "2024/5" / 空值从描述提取
      let dateVal = normalized.event_date || '';
      const _today = utils.today();
      // 【修复】取_latestYear时过滤NaN（非法year/month参与reduce会污染结果，最终回退到当前8月）
      const _latestYear = (db.events || []).reduce((mx, e) => {
        if (!e.event_year || isNaN(e.event_year)) return mx;
        return (e.event_year > mx) ? e.event_year : mx;
      }, new Date().getFullYear());
      // Excel序列号转换（>40000 才认为是序列号，排除纯年份数字如2024）
      if (dateVal && /^\d+$/.test(dateVal) && parseInt(dateVal) > 40000 && parseInt(dateVal) < 60000) {
        const serial = parseInt(dateVal);
        // Excel 1900 系统：序列号1=1900-01-01，但1900年闰年bug（2月29日不存在），所以>60时需-1
        const epochOffset = serial > 60 ? serial - 25569 : serial - 25568;
        const d = new Date(epochOffset * 86400 * 1000);
        // 【修复时区问题】使用本地时间而非UTC的toISOString()，避免UTC+8时区午夜日期偏差1天甚至跨月
        const y = d.getFullYear(), mo = String(d.getMonth()+1).padStart(2,'0'), da = String(d.getDate()).padStart(2,'0');
        dateVal = `${y}-${mo}-${da}`;
      }
      // 中文年月格式："2024年11月" / "2024年11月12日"
      if (dateVal && /^\d{4}年\d{1,2}月/.test(dateVal)) {
        const m = dateVal.match(/^(\d{4})年(\d{1,2})月(\d{1,2})?/);
        if (m) dateVal = m[1] + '-' + String(m[2]).padStart(2, '0') + '-' + String((m[3]?parseInt(m[3],10):1)).padStart(2, '0');
      }
      // 【新增】美式日期 MM/DD/YYYY（如"5/15/2026"）
      if (dateVal && /^\d{1,2}\/\d{1,2}\/\d{4}$/.test(dateVal)) {
        const parts = dateVal.split('/');
        const mo = parts[0].padStart(2,'0'), da = parts[1].padStart(2,'0'), y = parts[2];
        if (parseInt(mo,10) <= 12) dateVal = `${y}-${mo}-${da}`;
      }
      // 【新增】JS Date对象toString()格式（"Fri May 15 2026 00:00:00 GMT+0800..."）—— 防止XLSX返回Date后被其他地方String化
      if (dateVal && /^[A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{1,2}\s+\d{4}/.test(dateVal)) {
        const MONTH_MAP = {jan:'01',feb:'02',mar:'03',apr:'04',may:'05',jun:'06',jul:'07',aug:'08',sep:'09',oct:'10',nov:'11',dec:'12'};
        const m = dateVal.match(/^[A-Z][a-z]{2}\s+([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d{4})/);
        if (m) {
          const mo = MONTH_MAP[m[1].toLowerCase()], da = String(parseInt(m[2],10)).padStart(2,'0'), y = m[3];
          if (mo) dateVal = `${y}-${mo}-${da}`;
        }
      }
      // 【新增】其他日期分隔符："2024.5" / "2024/5" / "2024-5" / "2024.5.15"
      if (dateVal && /^\d{4}[-/.]\d{1,2}([-/.]\d{1,2})?$/.test(dateVal) && !/^\d{4}-\d{2}-\d{2}$/.test(dateVal)) {
        const parts = dateVal.split(/[-/.]/);
        const y = parts[0], mo = parts[1].padStart(2, '0'), da = parts[2] ? parts[2].padStart(2, '0') : '01';
        dateVal = y + '-' + mo + '-' + da;
      }
      if (!dateVal) {
        const desc = normalized.description || '';
        let m;
        if ((m = desc.match(/(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?/))) { dateVal = m[1] + '-' + m[2].padStart(2, '0') + '-' + m[3].padStart(2, '0'); }
        else if ((m = desc.match(/(\d{4})[-/](\d{1,2})[-/](\d{1,2})/))) { dateVal = m[1] + '-' + m[2].padStart(2, '0') + '-' + m[3].padStart(2, '0'); }
        else if ((m = desc.match(/(\d{4})\s*年\s*(\d{1,2})\s*月/))) { dateVal = m[1] + '-' + m[2].padStart(2, '0') + '-01'; }
        else if ((m = desc.match(/(\d{4})\s*年\s*(\d{1,2})\s*[-—~]\s*(\d{1,2})\s*月/))) { dateVal = m[1] + '-' + m[2].padStart(2, '0') + '-01'; }
        // 【修复】无年份月日提取：默认取数据集中最新年份而非当前系统年份（历史案例不是本月案例）
        else if ((m = desc.match(/(\d{1,2})\s*月\s*(\d{1,2})\s*日/))) {
          const yr = desc.match(/(20\d{2})/);
          const useYr = yr ? yr[1] : String(_latestYear);
          dateVal = useYr + '-' + m[1].padStart(2, '0') + '-' + m[2].padStart(2, '0');
        }
      }
      // 【新增】未来日期校验：如果解析出的日期晚于今日+1天，截取到年月并警告
      if (dateVal && /^\d{4}-\d{2}-\d{2}$/.test(dateVal) && dateVal > _today) {
        const ym = dateVal.slice(0, 7);
        dateVal = ym + '-01';
        if (!Array.isArray(validationWarnings)) validationWarnings = [];
        validationWarnings.push({ row: idx + 1, original: normalized.event_date, parsed: dateVal, reason: '日期晚于今日，已截取到年月初' });
      }
      normalized.event_date = dateVal;
      // 维度名 → dimension_id（一级风险主标签）
      let dimId = normalized.dimension_id || '';
      if (dimId && !dimId.match(/^RD0[1-7]$/)) {
        dimId = DIM_NAME_MAP[dimId] || DIM_NAME_MAP[dimId.replace(/管理|管控|冒烟|程序/g, '')] || '';
      }
      // 一级风险主标签为空时从二级分类推断
      if (!dimId || !dimId.match(/^RD0[1-7]$/)) {
        const subCat = normalized.label_secondary || '';
        if (subCat) dimId = SUB_CAT_TO_DIM[subCat] || '';
      }
      // ===== RD06子类归一化（10个标准子类）：先对label_secondary做规范化 =====
      let rawSub = normalized.label_secondary || '';
      if (!rawSub) {
        // 文本扫描兜底：在描述/原因/结果/责任人字段中搜10个子类/别名关键字
        const hay = [normalized.description, normalized.cause_analysis, normalized.result, normalized.responsible_person, normalized.flight_phase].join(' ');
        for (const std of RD06_STD_SUBCATS) { if (hay.includes(std)) { rawSub = std; break; } }
        if (!rawSub) {
          const ks = Object.keys(RD06_ALIAS_MAP);
          for (const k of ks) { if (hay.includes(k)) { rawSub = RD06_ALIAS_MAP[k]; break; } }
        }
      }
      const normalizedSub = normalizeRD06SubCat(rawSub);
      // 若归一化出了RD06子类但dimension_id仍为空，自动设为RD06
      if (normalizedSub && (!dimId || !dimId.match(/^RD0[1-7]$/))) dimId = 'RD06';
      normalized.dimension_id = dimId;
      normalized.label_secondary = (dimId === 'RD06') ? (normalizedSub || rawSub || '') : (normalized.label_secondary || '');
      return normalized;
    });

    // ==================== 组织层级映射引擎（已提取到全局 resolveSquad / getSquadMaps 工具函数，此处仅引用全局函数） ====================
    // 注意：内部 resolveSquad 函数于 L1463 统一实现，已消除重复定义。此处直接复用全局 resolveSquad。

    normalizedItems.forEach((item, idx) => {
      // 【第6项】原始行（给 reject_pool 用）
      const origRow = originalRows[idx] || {};
      try {
        // 缺少必填 → 进复核池（不直接failed计数）
        const missing = [];
        if (!item.event_date) missing.push('event_date');
        const dim = (db.risk_dimensions || []).find(d => d.id === item.dimension_id);
        // 组织层级校验与映射（数据筛选机制）
        const squad = item.base || item.division;
        const org = resolveSquad(squad);
        let baseVal = ''; let divIdVal = item.division_id || ''; let divNameVal = item.division_name || '';
        if (org.valid) {
          baseVal = org.baseId;
          divIdVal = org.divId || divIdVal;
          divNameVal = org.divName || divNameVal;
        } else {
          // 无法识别为任何合法组织层级 → 【第6项：入复核池，不再静默丢弃】
          rejected++;
          const reason = '分队列值"'+(squad||'(空)')+'"无法识别为合法组织层级';
          if (rejected <= 20) rejectedDetails.push({ row: idx+1, reason });
          _pushRejectPool(db, {
            row_no: idx+1, original_row: origRow, normalized: item,
            reject_reasons: [reason, ...(missing.length?['缺少必填字段:'+missing.join(',')]:[])],
            import_type: 'event_import'
          });
          intoRejectPool++;
          return;
        }

        // 【修复】event_date必须是合法的YYYY-MM-DD格式才能通过，避免切片出NaN导致后续默认年月回退到8月
        if (!/^\d{4}-\d{2}-\d{2}$/.test(item.event_date)) {
          throw new Error('日期格式不合法: ' + (item.event_date || '(空)') + '，需为YYYY-MM-DD');
        }
        const _ey = parseInt(item.event_date.slice(0, 4), 10);
        const _em = parseInt(item.event_date.slice(5, 7), 10);
        if (isNaN(_ey) || isNaN(_em) || _em < 1 || _em > 12) {
          throw new Error('日期年月解析失败: ' + item.event_date);
        }
        if (!dim) throw new Error('维度不存在/非法维度ID: ' + item.dimension_id);
        const evt = {
          event_id: item.event_id || ('EVT-IMP-' + utils.uuid().slice(0, 6).toUpperCase()),
          event_date: item.event_date,
          event_year: _ey,
          event_month: _em,
          flight_no: item.flight_no || '',
          // 航段列已删除：route_pair / departure / arrival 不再导入/保存
          flight_phase: item.flight_phase || '平飞',
          severity: item.severity || '轻',
          injury_count: parseInt(item.injury_count, 10) || 0,
          base: baseVal,
          division_id: divIdVal,
          division_name: divNameVal,
          dimension_id: item.dimension_id,
          label_primary: item.label_primary || dim.name,
          label_secondary: item.label_secondary || '',
          description: item.description || '',
          cause_analysis: item.cause_analysis || '',
          result: item.result || '',
          responsible_person: item.responsible_person || '',
          // 声明为系统所需案例数据
          source_doc_ref: item.source_doc_ref || 'Excel批量导入（系统所需案例数据）',
          source_type: item.source_type || 'case_data',
          created_at: utils.now()
        };
        db.events.push(evt);
        addedIds.push(evt.event_id);
        inserted++;
      } catch (e) {
        // 【第6项：失败的也进复核池（白名单可放行），不再只是 failed++ 然后丢弃】
        failed++;
        const msg = e.message || String(e);
        errors.push({ row: idx + 1, error: msg });
        _pushRejectPool(db, {
          row_no: idx+1, original_row: origRow, normalized: item,
          reject_reasons: ['校验失败: '+msg],
          import_type: 'event_import'
        });
        intoRejectPool++;
      }
    });
    // 记录到操作历史（支持通过时间线撤回）
    if (inserted > 0) {
      recordOp(db, {
        type: 'import',
        label: '导入事件 '+inserted+' 条',
        detail: { inserted, failed, rejected, into_reject_pool: intoRejectPool, rejected_details: rejectedDetails, source: body.source_doc_ref || '批量导入' },
        added_ids: addedIds,
        affected_count: inserted
      });
    }
    saveDB(db);
    audit('event.import', { inserted, failed, rejected, into_reject_pool: intoRejectPool });
    // 【第6项】返回 reject_pool 计数 + can_approve 数量，前端马上显示入口
    const poolAfter = Array.isArray(db.reject_pool) ? db.reject_pool : [];
    return {
      success: true,
      inserted, failed, rejected,
      into_reject_pool: intoRejectPool,
      rejected_details: rejectedDetails,
      date_warnings: validationWarnings,
      errors,
      reject_pool: {
        pending: poolAfter.filter(r=>r.status==='PENDING').length,
        can_approve_pending: poolAfter.filter(r=>r.status==='PENDING' && r.can_approve).length,
        blocked_pending: poolAfter.filter(r=>r.status==='PENDING' && !r.can_approve).length
      }
    };
  }

  function parseCsv(text) {
    const lines = text.replace(/^\uFEFF/, '').split(/\r?\n/).filter(l => l.trim());
    if (lines.length < 2) return [];
    const headers = lines[0].split(',').map(h => h.trim());
    return lines.slice(1).map(line => {
      const cells = line.split(',');
      const obj = {};
      headers.forEach((h, i) => { obj[h] = (cells[i] || '').trim(); });
      return obj;
    });
  }

  // GET /api/v1/events/export  导出事件 CSV（航段列已删除）
  function exportEvents(_params, query) {
    const db = loadDB();
    let events = utils.clone(db.events);
    if (query.base_id) {
      const baseIds = expandBaseId(db, query.base_id);
      events = events.filter(e => {
        if (baseIds.includes(e.base)) return true;
        if (e.division_id && baseIds.includes(e.division_id)) return true;
        if (e.division && baseIds.includes(e.division)) return true;
        return false;
      });
    }
    if (query.dimension_id) events = events.filter(e => e.dimension_id === query.dimension_id);
    // 航段列已删除：导出 CSV headers 中不再包含 route_pair
    const headers = ['event_id', 'event_date', 'flight_no', 'flight_phase', 'severity', 'injury_count', 'base', 'division_id', 'dimension_id', 'label_primary', 'label_secondary', 'description', 'cause_analysis', 'result', 'source_doc_ref', 'source_type'];
    const rows = events.map(e => headers.map(h => `"${String(e[h] || '').replace(/"/g, '""')}"`).join(','));
    const csv = '\uFEFF' + headers.join(',') + '\n' + rows.join('\n');
    return { content: csv, filename: `risk_events_export_${utils.today()}.csv`, mime_type: 'text/csv;charset=utf-8', count: events.length };
  }

  // ============ 国际 WeatherAPI 集成（3 小时缓存 + 手动更新） ============
  // 主源：WeatherAPI.com（用户提供的 API Key）
  // 备用源：Open-Meteo（免 API Key，永久免费，CORS 友好）
  // 数据源降级策略：主源失败时自动降级到备用源，保证天气数据可用

  // WeatherAPI.com API Key（用户配置）
  const WEATHER_API_KEY = 'de9f656712214f6a9c0172441262407';

  // 【新增14项】春秋内部基地/分队ID → 实际出发机场（IATA + 坐标）统一映射
  //   - 与前端 BASE_TO_AIRPORT 保持完全一致（前后端同一份数据）
  //   - 用途：天气查询、颠簸计算、航线起点/终点坐标解析（r.dep 可能是基地ID不是 IATA）
  const BASE_TO_AIRPORT = {
    'SHA':    { iata:'SHA', lat:31.1979, lon:121.3360, name:'上海虹桥',   isAirport:true },
    'PVG':    { iata:'PVG', lat:31.1443, lon:121.8083, name:'上海浦东',   isAirport:true },
    'SHA-D1': { iata:'SHA', lat:31.1979, lon:121.3360, name:'上海虹桥',   isAirport:true },
    'SHA-D2': { iata:'SHA', lat:31.1979, lon:121.3360, name:'上海虹桥',   isAirport:true },
    'SHA-D3': { iata:'SHA', lat:31.1979, lon:121.3360, name:'上海虹桥',   isAirport:true },
    'SHA-D4': { iata:'SHA', lat:31.1979, lon:121.3360, name:'上海虹桥',   isAirport:true },
    'SHA-D5': { iata:'SHA', lat:31.1979, lon:121.3360, name:'上海虹桥',   isAirport:true },
    'SHA-D6': { iata:'SHA', lat:31.1979, lon:121.3360, name:'上海虹桥',   isAirport:true },
    'PVG-D1': { iata:'PVG', lat:31.1443, lon:121.8083, name:'上海浦东',   isAirport:true },
    'PVG-D2': { iata:'PVG', lat:31.1443, lon:121.8083, name:'上海浦东',   isAirport:true },
    'PVG-D3': { iata:'PVG', lat:31.1443, lon:121.8083, name:'上海浦东',   isAirport:true },
    'PVG-D4': { iata:'PVG', lat:31.1443, lon:121.8083, name:'上海浦东',   isAirport:true },
    'PVG-D5': { iata:'PVG', lat:31.1443, lon:121.8083, name:'上海浦东',   isAirport:true },
    'PVG-D6': { iata:'PVG', lat:31.1443, lon:121.8083, name:'上海浦东',   isAirport:true },
    'Z1-NBG': { iata:'NGB', lat:29.8167, lon:121.4647, name:'宁波栎社',   isAirport:true },
    'Z1-YZH': { iata:'YTY', lat:32.3923, lon:119.5630, name:'扬州泰州',   isAirport:true }, // 修正：IATA=YTY 非 YZH
    'Z1-YTY': { iata:'YTY', lat:32.3923, lon:119.5630, name:'扬州泰州',   isAirport:true },
    'Z1-KHN': { iata:'KHN', lat:28.8649, lon:115.8756, name:'南昌昌北',   isAirport:true },
    'Z1-SWA': { iata:'SWA', lat:23.5535, lon:116.5022, name:'揭阳潮汕',   isAirport:true },
    'Z1-CAN': { iata:'CAN', lat:23.3924, lon:113.2988, name:'广州白云',   isAirport:true },
    'Z1-SZX': { iata:'SZX', lat:22.6394, lon:113.8108, name:'深圳宝安',   isAirport:true },
    'Z2-SHE': { iata:'SHE', lat:41.6398, lon:123.4836, name:'沈阳桃仙',   isAirport:true },
    'Z2-XIY': { iata:'XIY', lat:34.4471, lon:108.7517, name:'西安咸阳',   isAirport:true },
    'Z2-DLC': { iata:'DLC', lat:38.9657, lon:121.5386, name:'大连周水子', isAirport:true },
    'Z2-CTU': { iata:'CTU', lat:30.5785, lon:103.9471, name:'成都双流',   isAirport:true },
    'LHW':    { iata:'LHW', lat:36.5152, lon:103.6195, name:'兰州中川',   isAirport:true },
    'LHW-1':  { iata:'LHW', lat:36.5152, lon:103.6195, name:'兰州中川',   isAirport:true },
    'LHW-2':  { iata:'LHW', lat:36.5152, lon:103.6195, name:'兰州中川',   isAirport:true },
    // 【修正14项】春秋河北分公司实际基地=石家庄正定国际机场（SJW），不是石家庄市区坐标
    'HB':     { iata:'SJW', lat:38.2792, lon:114.7068, name:'石家庄正定', isAirport:true },
    'HB-1':   { iata:'SJW', lat:38.2792, lon:114.7068, name:'石家庄正定', isAirport:true },
    'HB-2':   { iata:'SJW', lat:38.2792, lon:114.7068, name:'石家庄正定', isAirport:true },
    'DUO':    { iata:'DUO', lat:34.3300, lon:108.7000, name:'双照',       isAirport:false },
    'Z1':     { iata:'SHA', lat:31.2304, lon:121.4737, name:'综一总部',   isAirport:false },
    'Z2':     { iata:'SHA', lat:31.2304, lon:121.4737, name:'综二总部',   isAirport:false }
  };
  // 纯 IATA → 经纬度（对应前端 DEST_LATLON，用于航线终点坐标解析）
  const IATA_LATLON = {
    'SHA':{lat:31.1979,lon:121.3360,name:'上海虹桥'},
    'PVG':{lat:31.1443,lon:121.8083,name:'上海浦东'},
    'BKK':{lat:13.6900,lon:100.7501,name:'曼谷'},
    'CTU':{lat:30.5785,lon:103.9471,name:'成都'},
    'XMN':{lat:24.5440,lon:118.1274,name:'厦门'},
    'URC':{lat:43.9072,lon:87.4742,name:'乌鲁木齐'},
    'HRB':{lat:45.6234,lon:126.2503,name:'哈尔滨'},
    'CAN':{lat:23.3924,lon:113.2988,name:'广州'},
    'KUL':{lat:2.7456,lon:101.7099,name:'吉隆坡'},
    'PEN':{lat:5.2971,lon:100.2656,name:'槟城'},
    'HAN':{lat:21.2212,lon:105.8071,name:'河内'},
    'SIN':{lat:1.3592,lon:103.9890,name:'新加坡'},
    'SZX':{lat:22.6394,lon:113.8108,name:'深圳'},
    // 【新增14项】补全春秋 8 个基地 IATA 坐标（原缺失导致航线 arr=基地ID 无法解析）
    'SJW':{lat:38.2792,lon:114.7068,name:'石家庄正定'},
    'YTY':{lat:32.3923,lon:119.5630,name:'扬州泰州'},
    'NGB':{lat:29.8167,lon:121.4647,name:'宁波栎社'},
    'KHN':{lat:28.8649,lon:115.8756,name:'南昌昌北'},
    'SWA':{lat:23.5535,lon:116.5022,name:'揭阳潮汕'},
    'XIY':{lat:34.4471,lon:108.7517,name:'西安咸阳'},
    'DLC':{lat:38.9657,lon:121.5386,name:'大连周水子'},
    'SHE':{lat:41.6398,lon:123.4836,name:'沈阳桃仙'},
    'LHW':{lat:36.5152,lon:103.6195,name:'兰州中川'}
  };
  /**
   * 解析任意 code（基地ID / 分队ID / IATA）→ 标准化机场信息（与前端 resolveAirport 一致）
   */
  function resolveAirport(code){
    if(!code) return null;
    code = String(code).trim();
    if(BASE_TO_AIRPORT[code]) return BASE_TO_AIRPORT[code];
    if(IATA_LATLON[code]) return { iata:code, lat:IATA_LATLON[code].lat, lon:IATA_LATLON[code].lon, name:IATA_LATLON[code].name, isAirport:true };
    return null;
  }

  // 机场 ICAO/IATA → 城市名映射（用于 WeatherAPI 查询）
  // 【修正14项】新增：'HB/HB-1/HB-2 → SJW（石家庄正定）'，'Z1-YZH/YZH → YTY（扬州泰州）'
  const AIRPORT_CITY_MAP = {
    'SHA': 'iata:SHA', 'PVG': 'iata:PVG', 'CAN': 'iata:CAN', 'KUL': 'iata:KUL',
    'PEN': 'iata:PEN', 'HAN': 'iata:HAN', 'SIN': 'iata:SIN', 'BKK': 'iata:BKK',
    'CTU': 'iata:CTU', 'XMN': 'iata:XMN', 'URC': 'iata:URC', 'HRB': 'iata:HRB',
    'SZX': 'iata:SZX', 'NBG': 'iata:NGB', 'YZH': 'iata:YTY', 'KHN': 'iata:KHN',
    'SWA': 'iata:SWA', 'SHE': 'iata:SHE', 'XIY': 'iata:XIY', 'DLC': 'iata:DLC',
    'LHW': 'iata:LHW', 'HB': 'iata:SJW',
    // 【修正14项】春秋航空实际 IATA 代码（WeatherAPI 推荐直接用 iata:XXX 格式，避免城市名拼写/编码/特殊字符问题）
    'SJW': 'iata:SJW',   // 石家庄正定国际机场（春秋河北基地）
    'YTY': 'iata:YTY'    // 扬州泰州国际机场（春秋扬州基地，IATA=YTY 非 YZH）
  };

  // 机场 ICAO/IATA → 经纬度坐标（Open-Meteo 备用源使用）
  // 【修正14项】HB：石家庄市区 → 正定机场实址；新增 SJW / YTY / NBG / KHN / ... 完整 IATA 坐标
  // 【需求3/4修复】增加复合基地ID别名（Z1-CAN、Z2-SHE等），使台风判断+天气匹配都能命中
  const BASE_ALIAS_COORDS = {
    'Z1-CAN': { iata: 'CAN', name: '广州' },
    'Z1-SZX': { iata: 'SZX', name: '深圳' },
    'Z1-NBG': { iata: 'NBG', name: '宁波' },
    'Z1-YZH': { iata: 'YTY', name: '扬州泰州' },   // 真实 IATA=YTY（YZH 是旧码）
    'Z1-KHN': { iata: 'KHN', name: '南昌' },
    'Z1-SWA': { iata: 'SWA', name: '揭阳' },
    'Z2-SHE': { iata: 'SHE', name: '沈阳' },
    'Z2-XIY': { iata: 'XIY', name: '西安' },
    'Z2-DLC': { iata: 'DLC', name: '大连' },
    'Z2-CTU': { iata: 'CTU', name: '成都' },
    'DUO':   { iata: 'XIY', name: '双照（西安）' }, // 双照基地挂靠西安咸阳
    'Z1':    { iata: 'SHA', name: '综一(上海虹桥)' },
    'Z2':    { iata: 'PVG', name: '综二(上海浦东)' }
  };
  const _RAW_AIRPORT_COORDS = {
    'SHA': { lat: 31.1979, lon: 121.3360, name: '上海虹桥' },
    'PVG': { lat: 31.1443, lon: 121.8083, name: '上海浦东' },
    'CAN': { lat: 23.3924, lon: 113.2988, name: '广州' },
    'KUL': { lat: 2.7456,  lon: 101.7099, name: '吉隆坡' },
    'PEN': { lat: 5.2971,  lon: 100.2767, name: '槟城' },
    'HAN': { lat: 21.2212, lon: 105.8071, name: '河内' },
    'SIN': { lat: 1.3644,  lon: 103.9915, name: '新加坡' },
    'BKK': { lat: 13.6900, lon: 100.7501, name: '曼谷' },
    'CTU': { lat: 30.5785, lon: 103.9471, name: '成都' },
    'XMN': { lat: 24.5440, lon: 118.1272, name: '厦门' },
    'URC': { lat: 43.9072, lon: 87.4742,  name: '乌鲁木齐' },
    'HRB': { lat: 45.6232, lon: 126.2503, name: '哈尔滨' },
    'SZX': { lat: 22.6394, lon: 113.8108, name: '深圳' },
    'NBG': { lat: 29.8167, lon: 121.4647, name: '宁波' },
    'YZH': { lat: 32.3923, lon: 119.5630, name: '扬州' },
    'YTY': { lat: 32.3923, lon: 119.5630, name: '扬州泰州国际机场' },
    'KHN': { lat: 28.8649, lon: 115.8756, name: '南昌' },
    'SWA': { lat: 23.5535, lon: 116.5022, name: '揭阳' },
    'SHE': { lat: 41.6398, lon: 123.4836, name: '沈阳' },
    'XIY': { lat: 34.4471, lon: 108.7517, name: '西安' },
    'DLC': { lat: 38.9657, lon: 121.5386, name: '大连' },
    'LHW': { lat: 36.5152, lon: 103.6195, name: '兰州' },
    'HB':  { lat: 38.2792, lon: 114.7068, name: '石家庄正定' },
    'SJW': { lat: 38.2792, lon: 114.7068, name: '石家庄正定国际机场' }
  };
  // 组装 AIRPORT_COORDS：基础 + 复合基地ID别名（这样 computeAffectedAirports、getWeatherTimeline 都会正确匹配）
  const AIRPORT_COORDS = Object.assign({}, _RAW_AIRPORT_COORDS);
  Object.entries(BASE_ALIAS_COORDS).forEach(([baseId, info]) => {
    const src = _RAW_AIRPORT_COORDS[info.iata];
    if (src) AIRPORT_COORDS[baseId] = Object.assign({}, src, { _aliasOf: info.iata, name: info.name || src.name });
  });
  // 辅助：给定任意代码（复合基地ID/IATA/ICAO），归一化到「标准匹配代码列表」（用于天气数据多编码检索）
  function normalizeAirportCodes(code) {
    if (!code) return [];
    const codes = [String(code).toUpperCase()];
    // 如果是复合基地ID，追加其对应的IATA码
    const alias = BASE_ALIAS_COORDS[String(code)];
    if (alias) codes.push(alias.iata);
    // 如果是旧码 YZH，补真实 IATA YTY
    if (String(code).toUpperCase() === 'YZH') codes.push('YTY');
    // 去重
    return Array.from(new Set(codes));
  }

  // WMO 天气代码 → 中文描述（Open-Meteo 使用）
  function wmoCodeToZh(code) {
    const m = {
      0: '晴', 1: '晴', 2: '多云', 3: '阴',
      45: '雾', 48: '雾凇',
      51: '毛毛雨', 53: '毛毛雨', 55: '毛毛雨',
      56: '冻毛毛雨', 57: '冻毛毛雨',
      61: '小雨', 63: '中雨', 65: '大雨',
      66: '冻雨', 67: '冻雨',
      71: '小雪', 73: '中雪', 75: '大雪', 77: '雪粒',
      80: '阵雨', 81: '阵雨', 82: '强阵雨',
      85: '阵雪', 86: '强阵雪',
      95: '雷暴', 96: '雷暴伴冰雹', 99: '强雷暴伴冰雹'
    };
    return m[code] !== undefined ? m[code] : '未知';
  }

  // WeatherAPI 英文天气描述 → 中文
  const WEATHERAPI_PHEN_ZH = {
    'Sunny': '晴', 'Clear': '晴', 'Partly cloudy': '多云', 'Cloudy': '阴',
    'Overcast': '阴', 'Mist': '薄雾', 'Fog': '雾', 'Light rain': '小雨',
    'Moderate rain': '中雨', 'Heavy rain': '大雨', 'Light snow': '小雪',
    'Moderate snow': '中雪', 'Heavy snow': '大雪', 'Thunderstorm': '雷暴',
    'Light drizzle': '毛毛雨', 'Patchy rain possible': '零星小雨',
    'Patchy snow possible': '零星小雪', 'Thundery outbreaks possible': '雷阵雨',
    'Patchy light rain': '零星小雨', 'Patchy light snow': '零星小雪',
    'Torrential rain shower': '暴雨', 'Light rain shower': '小阵雨',
    'Moderate or heavy rain shower': '中到大阵雨'
  };

  // 读取天气缓存
  function getWeatherCache() {
    try {
      const raw = localStorage.getItem(WEATHER_CACHE_KEY);
      if (!raw) return null;
      const cache = JSON.parse(raw);
      return cache;
    } catch { return null; }
  }

  // 写入天气缓存
  function setWeatherCache(data) {
    const cache = {
      data,
      cached_at: Date.now(),
      expires_at: Date.now() + WEATHER_CACHE_TTL
    };
    localStorage.setItem(WEATHER_CACHE_KEY, JSON.stringify(cache));
  }

  // 判断缓存是否过期
  function isWeatherCacheValid() {
    const cache = getWeatherCache();
    if (!cache) return false;
    return Date.now() < cache.expires_at;
  }

  // ============ 离线模式快速检测与超时保护（避免无外网时 fetch 卡住） ============
  let _offlineMode = false;      // 一旦任何 fetch 超时或 DNS 失败，标记为离线不再尝试真实 API
  let _offlineFailCount = 0;
  const OFFLINE_THRESHOLD = 2;   // 连续失败 2 次进入离线模式
  const FETCH_TIMEOUT_MS = 3000; // 单次 fetch 超时 3s（远短于浏览器默认数分钟）

  async function fetchWithTimeout(url, opts) {
    if (_offlineMode) return null; // 已在离线模式，直接跳过
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
    try {
      const resp = await fetch(url, { ...(opts || {}), signal: controller.signal });
      clearTimeout(timer);
      return resp;
    } catch (e) {
      clearTimeout(timer);
      // 超时或网络错误 → 计数，连续超阈值进入离线模式
      _offlineFailCount += 1;
      if (_offlineFailCount >= OFFLINE_THRESHOLD) {
        _offlineMode = true;
        console.info('[mock-server] 进入离线模式（连续网络请求失败），将使用缓存/mock 数据');
      }
      return null;
    }
  }

  // 主源：从 WeatherAPI.com 获取天气数据（使用用户提供的 API Key）
  async function fetchFromWeatherAPI(stationCode) {
    const city = AIRPORT_CITY_MAP[stationCode];
    if (!city) return null;
    const url = `https://api.weatherapi.com/v1/forecast.json?key=${WEATHER_API_KEY}&q=${city}&days=1&aqi=no&alerts=yes`;
    try {
      const resp = await fetchWithTimeout(url);
      if (!resp) return null;
      if (!resp.ok) return null;
      return await resp.json();
    } catch (e) {
      return null;
    }
  }

  // 备用源：从 Open-Meteo 获取天气数据（免 API Key，永久免费）
  async function fetchFromOpenMeteo(stationCode) {
    const coord = AIRPORT_COORDS[stationCode];
    if (!coord) return null;
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${coord.lat}&longitude=${coord.lon}`
      + `&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m,wind_gusts_10m,visibility`
      + `&hourly=temperature_2m,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m,wind_gusts_10m,visibility,precipitation_probability`
      + `&timezone=Asia%2FShanghai&forecast_days=1`;
    try {
      const resp = await fetchWithTimeout(url);
      if (!resp) return null;
      if (!resp.ok) return null;
      return await resp.json();
    } catch (e) {
      return null;
    }
  }

  // 统一入口：优先 WeatherAPI 主源，失败自动降级 Open-Meteo 备用源
  async function fetchWeatherFromAPI(stationCode) {
    // 主源：WeatherAPI.com
    const waData = await fetchFromWeatherAPI(stationCode);
    if (waData && waData.current && waData.forecast) {
      return { source: 'WeatherAPI.com', data: waData };
    }
    // 备用源：Open-Meteo（主源失败时降级）
    const omData = await fetchFromOpenMeteo(stationCode);
    if (omData && omData.current) {
      return { source: 'Open-Meteo', data: omData };
    }
    return null;
  }

  // 将原始数据转换为系统标准天气记录（自动识别数据源格式）
  function transformWeatherData(stationCode, fetched) {
    if (!fetched || !fetched.source || !fetched.data) return null;
    if (fetched.source === 'WeatherAPI.com') {
      return transformWeatherAPIData(stationCode, fetched.data);
    }
    if (fetched.source === 'Open-Meteo') {
      return transformOpenMeteoData(stationCode, fetched.data);
    }
    return null;
  }

  // WeatherAPI.com 数据转换
  function transformWeatherAPIData(stationCode, apiData) {
    if (!apiData || !apiData.current || !apiData.forecast) return null;
    const cur = apiData.current;
    const fc = apiData.forecast.forecastday[0] || {};
    const windSpd = Math.round((cur.wind_kph || 0) / 3.6); // km/h → m/s
    const vis = Number(((cur.vis_km || 10)).toFixed(1));
    const phenEn = cur.condition?.text || '未知';
    const phenZh = WEATHERAPI_PHEN_ZH[phenEn] || phenEn;
    const temp = Math.round(cur.temp_c || 20);
    const windDir = cur.wind_dir || '未知';
    const gustSpd = Math.round((cur.gust_kph || cur.wind_kph || 0) / 3.6);
    const cloudCover = cur.cloud || 0;

    // 颠簸指数计算（科学公式，依据 ICAO Annex 3 + 航空气象学原理）
    const _turb = calcTurbulenceIndex(windSpd, gustSpd, cloudCover, phenEn, vis);
    const turbIndex = _turb.turbIndex;
    const turbLevel = _turb.turbLevel;

    // 逐小时预报
    const hourly = (fc.hour || []).map(h => {
      const hWind = Math.round((h.wind_kph || 0) / 3.6);
      const hGust = Math.round((h.gust_kph || h.wind_kph || 0) / 3.6);
      const hCloud = h.cloud || 0;
      const hPhenEn = h.condition?.text || '';
      const hVis = Number((h.vis_km || 10).toFixed(1));
      const _hTurb = calcTurbulenceIndex(hWind, hGust, hCloud, hPhenEn, hVis);
      const hTurbIdx = _hTurb.turbIndex;
      return {
        time: h.time,
        hour: h.time?.slice(11, 16) || '',
        wind_speed: hWind,
        wind_direction: h.wind_dir || '',
        gust_speed: hGust,
        temperature: Math.round(h.temp_c || 0),
        weather_phenomena: WEATHERAPI_PHEN_ZH[hPhenEn] || hPhenEn || '未知',
        cloud_cover: hCloud,
        visibility: Number((h.vis_km || 10).toFixed(1)),
        turb_index: hTurbIdx,
        turb_level: _hTurb.turbLevel,
        will_rain: h.will_it_rain === 1,
        chance_of_rain: h.chance_of_rain || 0
      };
    });

    return buildWeatherRecord({
      stationCode, observationTime: cur.last_updated || utils.now(),
      windSpd, windDir, vis, phenZh, temp, gustSpd, cloudCover, turbIndex, turbLevel,
      dewPoint: Math.round(cur.dewpoint_c || (temp - 5)),
      weatherAlert: apiData.alerts?.alert?.length > 0 ? {
        type: apiData.alerts.alert[0].category || 'WX',
        severity: apiData.alerts.alert[0].severity || 'moderate',
        headline: apiData.alerts.alert[0].headline || '天气预警',
        areas: [stationCode],
        effective: apiData.alerts.alert[0].effective || utils.now(),
        expires: apiData.alerts.alert[0].expires || new Date(Date.now() + 3600000).toISOString()
      } : null,
      sourceType: 'WeatherAPI.com',
      hourly
    });
  }

  // Open-Meteo 数据转换（备用源）
  function transformOpenMeteoData(stationCode, apiData) {
    if (!apiData || !apiData.current) return null;
    const cur = apiData.current;
    const hourlyArr = apiData.hourly || {};
    const windSpd = Math.round((cur.wind_speed_10m || 0) / 3.6);
    const gustSpd = Math.round((cur.wind_gusts_10m || cur.wind_speed_10m || 0) / 3.6);
    const vis = Number(((cur.visibility || 10000) / 1000).toFixed(1));
    const wmoCode = cur.weather_code ?? 0;
    const phenZh = wmoCodeToZh(wmoCode);
    const temp = Math.round(cur.temperature_2m ?? 20);
    const windDirDeg = cur.wind_direction_10m ?? 0;
    const dirArr = ['北','东北','东','东南','南','西南','西','西北'];
    const windDir = dirArr[Math.round(windDirDeg / 45) % 8];
    const cloudCover = cur.cloud_cover ?? 0;
    const dewPoint = Math.round((temp - (100 - (cur.relative_humidity_2m ?? 50)) / 5));

    // 颠簸指数计算（科学公式，依据 ICAO Annex 3 + 航空气象学原理）
    const _turbOm = calcTurbulenceIndex(windSpd, gustSpd, cloudCover, phenZh, vis);
    const turbIndex = _turbOm.turbIndex;
    const turbLevel = _turbOm.turbLevel;

    // 逐小时预报
    const hTimes = hourlyArr.time || [];
    const hWindArr = hourlyArr.wind_speed_10m || [];
    const hGustArr = hourlyArr.wind_gusts_10m || [];
    const hCloudArr = hourlyArr.cloud_cover || [];
    const hTempArr = hourlyArr.temperature_2m || [];
    const hVisArr = hourlyArr.visibility || [];
    const hCodeArr = hourlyArr.weather_code || [];
    const hPopArr = hourlyArr.precipitation_probability || [];
    const hDirArr = hourlyArr.wind_direction_10m || [];
    const hourly = hTimes.map((t, i) => {
      const hWind = Math.round((hWindArr[i] || 0) / 3.6);
      const hGust = Math.round((hGustArr[i] || hWindArr[i] || 0) / 3.6);
      const hCloud = hCloudArr[i] || 0;
      const hCode = hCodeArr[i] ?? 0;
      const hPhenZh = wmoCodeToZh(hCode);
      const hVis = Number(((hVisArr[i] || 10000) / 1000).toFixed(1));
      const _hTurbOm = calcTurbulenceIndex(hWind, hGust, hCloud, hPhenZh, hVis);
      const hTurbIdx = _hTurbOm.turbIndex;
      const hDirDeg = hDirArr[i] ?? 0;
      return {
        time: t,
        hour: t ? t.slice(11, 16) : '',
        wind_speed: hWind,
        wind_direction: dirArr[Math.round(hDirDeg / 45) % 8],
        gust_speed: hGust,
        temperature: Math.round(hTempArr[i] ?? 0),
        weather_phenomena: hPhenZh,
        cloud_cover: hCloud,
        visibility: hVis,
        turb_index: hTurbIdx,
        turb_level: _hTurbOm.turbLevel,
        will_rain: (hPopArr[i] || 0) >= 50,
        chance_of_rain: hPopArr[i] || 0
      };
    });

    return buildWeatherRecord({
      stationCode, observationTime: cur.time || utils.now(),
      windSpd, windDir, vis, phenZh, temp, gustSpd, cloudCover, turbIndex, turbLevel,
      dewPoint, weatherAlert: null, sourceType: 'Open-Meteo', hourly
    });
  }

  // ============ 颠簸指数科学计算（0-27 量表，依据 ICAO Annex 3 + 航空气象学原理） ============
  // 科学依据：
  // 1. 机械湍流：风速越大，地表摩擦产生的机械湍流越强（蒲福风级 ≥6 级即 10.8m/s 开始显著）
  // 2. 阵风差：阵风与持续风速差值反映大气不稳定度，差值越大湍流越强
  // 3. 对流活动：雷暴/飑线/冰雹等强对流天气直接产生严重颠簸（CB 云内最强）
  // 4. 云量：高云量（>75%）预示对流云发展，中低云伴湍流
  // 5. 能见度：低能见度常伴随雾/降水/沙尘，与湍流正相关
  // 参考：ICAO Doc 8896 航空气象、FAA AC 00-45H、中国民航 MH/T 4016
  function calcTurbulenceIndex(windSpd, gustSpd, cloudCover, phenEn, vis) {
    // 1. 风速因子 (0-8)：基于蒲福风级与机械湍流关系
    //    <5m/s(3级)=0, 5-10(4-5级)=1-2, 10-17(6-7级)=3-5, 17-24(8级)=6-7, >24(9级+)=8
    let windFactor;
    if (windSpd < 5) windFactor = 0;
    else if (windSpd < 10) windFactor = Math.floor((windSpd - 5) / 2.5) + 1;  // 1-2
    else if (windSpd < 17) windFactor = Math.floor((windSpd - 10) / 2.3) + 3; // 3-5
    else if (windSpd < 24) windFactor = Math.floor((windSpd - 17) / 3.5) + 6; // 6-7
    else windFactor = 8;
    windFactor = Math.min(windFactor, 8);

    // 2. 阵风差因子 (0-6)：阵风差反映风场不稳定性
    //    阵风差<3m/s=0, 3-7=1-2, 7-12=3-4, >12=5-6
    const gustDelta = Math.max(0, gustSpd - windSpd);
    let gustFactor;
    if (gustDelta < 3) gustFactor = 0;
    else if (gustDelta < 7) gustFactor = Math.floor((gustDelta - 3) / 2) + 1;  // 1-2
    else if (gustDelta < 12) gustFactor = Math.floor((gustDelta - 7) / 2.5) + 3; // 3-4
    else gustFactor = Math.min(Math.floor((gustDelta - 12) / 3) + 5, 6);          // 5-6
    gustFactor = Math.min(gustFactor, 6);

    // 3. 对流天气因子 (0-8)：基于天气现象强度分级
    //    雷暴/飑/冰雹=8（CB 云内极端湍流），强降水=5，降水=3，降雪=2，雾=1
    let convFactor = 0;
    const phenLower = (phenEn || '').toLowerCase();
    if (/thunder|storm|squall|hail|雷暴|飑|冰雹|雷雨/.test(phenLower)) convFactor = 8;
    else if (/heavy.*rain|torrential|强降雨|暴雨|大雨|downpour/.test(phenLower)) convFactor = 5;
    else if (/rain|drizzle|shower|雨|阵雨/.test(phenLower)) convFactor = 3;
    else if (/snow|snowgrains|降雪|雪|blizzard|暴雪/.test(phenLower)) convFactor = 2;
    else if (/fog|mist|haze|雾|霾/.test(phenLower)) convFactor = 1;

    // 4. 云量因子 (0-3)：高云量预示对流活动
    //    云量>75%=3, 50-75%=2, 25-50%=1, <25%=0
    const cloudFactor = cloudCover > 75 ? 3 : cloudCover > 50 ? 2 : cloudCover > 25 ? 1 : 0;

    // 5. 能见度因子 (0-2)：低能见度常伴随恶劣天气
    //    能见度<1km=2, 1-3km=1, >3km=0
    const visFactor = vis < 1 ? 2 : vis < 3 ? 1 : 0;

    // 总颠簸指数（上限 27）
    const turbIndex = Math.min(windFactor + gustFactor + convFactor + cloudFactor + visFactor, 27);

    // 颠簸等级（0=无, 1-5=轻度, 6-14=中度, 15-27=严重）
    const turbLevel = turbIndex === 0 ? '无颠簸'
      : turbIndex <= 5 ? '轻度颠簸'
      : turbIndex <= 14 ? '中度颠簸'
      : '严重颠簸';

    return { turbIndex, turbLevel, factors: { windFactor, gustFactor, convFactor, cloudFactor, visFactor } };
  }

  // 构建系统标准天气记录（统一字段，双源共用）
  function buildWeatherRecord(p) {
    const windLevel = p.windSpd < 5 ? '微风' : p.windSpd < 10 ? '和风' : p.windSpd < 20 ? '强风' : '大风';
    const visLevel = p.vis >= 10 ? '能见度良好（≥10km）' : p.vis >= 5 ? `能见度一般（${p.vis}km）` : p.vis >= 1 ? `能见度较差（${p.vis}km），需关注起降标准` : `能见度差（${p.vis}km），低于起降标准`;
    const isSevere = p.turbIndex >= 15 || p.vis < 2 || p.phenZh === '雷暴' || p.phenZh === '强雷暴伴冰雹';
    const hasFlightImpact = p.turbIndex >= 6 || p.windSpd >= 20;
    return {
      station_or_area: p.stationCode,
      observation_time: p.observationTime,
      wind_speed: p.windSpd,
      wind_direction: p.windDir,
      visibility: p.vis,
      weather_phenomena: p.phenZh,
      temperature: p.temp,
      dew_point: p.dewPoint,
      cloud_cover: p.cloudCover,
      cloud_base: Math.floor(p.cloudCover * 30 + 300),
      turb_intensity: p.turbIndex,
      turb_level: p.turbLevel,
      gust_speed: p.gustSpd,
      sigmet_phenomena: null,
      weather_alert: p.weatherAlert,
      source_tier: 'GENERAL',
      source_type: p.sourceType,
      hourly: p.hourly,
      interpretation: {
        summary: `${p.phenZh}天气，${windLevel}（风速${p.windSpd}m/s），${visLevel}。颠簸指数${p.turbIndex}（${p.turbLevel}）。`,
        wind: `${windLevel}，风速 ${p.windSpd} m/s，阵风 ${p.gustSpd} m/s`,
        visibility_desc: visLevel,
        phenomena_desc: `${p.phenZh}天气`,
        turb_desc: `颠簸指数 ${p.turbIndex}，${p.turbLevel}`,
        flight_impact: isSevere ? '对飞行有严重影响，需加强客舱安全准备'
          : hasFlightImpact ? '对飞行有一定影响，需关注颠簸防范'
          : '对飞行影响较小，按正常程序执行',
        recommendation: p.turbIndex >= 15
          ? '建议：1) 航前协同会重点复核颠簸沟通程序；2) 平飞阶段暂停热饮服务；3) 提前完成下降准备；4) 乘务员就座并系好安全带。'
          : p.turbIndex >= 6
          ? '建议：1) 航前简报宣导安全带检查；2) 关注颠簸变化；3) 餐具固定流程复核。'
          : '建议：按标准程序执行客舱服务，持续关注天气变化。'
      },
      raw_text: null,
      received_at: utils.now()
    };
  }

  // 刷新所有航线的天气数据（主源 WeatherAPI，备用 Open-Meteo，3 小时缓存）
  async function refreshWeatherData(baseId) {
    const db = loadDB();
    let routes = db.routes;
    if (baseId) {
      const baseIds = expandBaseId(db, baseId);
      routes = routes.filter(r => baseIds.includes(r.base_id));
    }
    // 收集所有涉及机场
    const stations = new Set();
    routes.forEach(r => { stations.add(r.dep); stations.add(r.arr); });

    const newWeathers = [];
    const failedStations = [];
    const sourceStats = { 'WeatherAPI.com': 0, 'Open-Meteo': 0 };
    for (const station of stations) {
      const fetched = await fetchWeatherFromAPI(station);
      if (fetched) {
        const transformed = transformWeatherData(station, fetched);
        if (transformed) {
          newWeathers.push(transformed);
          sourceStats[fetched.source] = (sourceStats[fetched.source] || 0) + 1;
        } else {
          failedStations.push(station);
        }
      } else {
        failedStations.push(station);
      }
    }

    // 仅当成功获取到数据时才更新数据库与缓存（避免空数据覆盖已有缓存）
    if (newWeathers.length > 0) {
      const successStations = new Set(newWeathers.map(w => w.station_or_area));
      db.weathers = db.weathers.filter(w => !successStations.has(w.station_or_area));
      db.weathers.push(...newWeathers);
      saveDB(db);
      setWeatherCache(newWeathers);
    }

    audit('weather.refresh', { stations: Array.from(stations), count: newWeathers.length, failed: failedStations, sources: sourceStats });
    const totalStations = stations.size;
    const partialFailure = failedStations.length > 0 && newWeathers.length > 0;
    const allFailed = newWeathers.length === 0 && totalStations > 0;
    const sourceDesc = Object.entries(sourceStats).filter(([,v])=>v>0).map(([k,v])=>`${k} ${v}条`).join('、');
    return {
      refreshed: !allFailed,
      stations: Array.from(stations),
      records_updated: newWeathers.length,
      failed_stations: failedStations,
      partial_failure: partialFailure,
      source_stats: sourceStats,
      message: allFailed
        ? '天气数据获取失败：WeatherAPI 主源与 Open-Meteo 备用源均不可用，请检查网络连接'
        : partialFailure
        ? `部分机场天气获取失败（${failedStations.length}/${totalStations}），成功 ${newWeathers.length} 条（${sourceDesc}）`
        : `成功获取 ${newWeathers.length} 条天气记录（${sourceDesc}）`,
      cached_at: utils.now(),
      expires_at: new Date(Date.now() + WEATHER_CACHE_TTL).toISOString(),
      cache_ttl_hours: 3
    };
  }

  // 手动触发天气更新
  async function manualRefreshWeather(_params, _query, body) {
    requireAuth();
    const baseId = body?.base_id;
    const result = await refreshWeatherData(baseId);
    return result;
  }

  // 获取缓存状态
  function getWeatherCacheStatus() {
    const cache = getWeatherCache();
    if (!cache) {
      return { cached: false, message: '无缓存数据，请点击刷新获取最新天气' };
    }
    const remaining = cache.expires_at - Date.now();
    return {
      cached: true,
      cached_at: new Date(cache.cached_at).toISOString(),
      expires_at: new Date(cache.expires_at).toISOString(),
      remaining_minutes: Math.max(0, Math.floor(remaining / 60000)),
      remaining_hours: Math.max(0, Math.floor(remaining / 3600000)),
      is_expired: remaining <= 0,
      cache_ttl_hours: 3,
      record_count: cache.data?.length || 0
    };
  }

  // ============ 颠簸指数等级定义 ============
  // 0=无颠簸 | 1-5=轻度颠簸 | 6-14=中度颠簸 | 15-27=严重颠簸
  function getTurbLevel(idx) {
    if (idx === 0) return { level: 'none', text: '无颠簸', color: '#52C41A' };
    if (idx <= 5) return { level: 'light', text: '轻度颠簸', color: '#8FD14F' };
    if (idx <= 14) return { level: 'moderate', text: '中度颠簸', color: '#FA8C16' };
    return { level: 'severe', text: '严重颠簸', color: '#F5222D' };
  }

  // GET /api/v1/weather/timeline?start_time=&end_time=&base_id=
  function getWeatherTimeline(_params, query) {
    const db = loadDB();
    let weathers = utils.clone(db.weathers);
    let routes = utils.clone(db.routes);

    // 所有基地机场代码列表（用于空 base_id / 天气面板专用全量数据）
    const BASE_AIRPORT_IDS = Object.keys(AIRPORT_COORDS);

    if (query.base_id) {
      const baseIds = expandBaseId(db, query.base_id);
      routes = routes.filter(r => baseIds.includes(r.base_id));
    }
    const startTime = query.start_time; // HH:MM
    const endTime = query.end_time;     // HH:MM
    // 按时间段筛选航线
    if (startTime && endTime) {
      const toMin = (t) => {
        if (typeof t !== 'string' || !t) return -1;
        const parts = t.split(':');
        const h = parseInt(parts[0] || '0', 10) || 0;
        const m = parseInt(parts[1] || '0', 10) || 0;
        return h * 60 + m;
      };
      const s = toMin(startTime), e = toMin(endTime);
      if (s >= 0 && e >= 0) {
        routes = routes.filter(r => {
          let dep = toMin(r.dep_time);
          if (dep < 0) {
            // r.dep_time 缺省时，用 route.id 推断（与 generateFlightHourlyData 保持一致）
            const seed = String(r.id || 'ROUTE').split('').reduce((a,ch)=>a+ch.charCodeAt(0),0) || 0;
            dep = ((7 + (seed % 7)) * 60) + ((seed * 17) % 60);
          }
          if (e < s) return dep >= s || dep <= e;
          return dep >= s && dep <= e;
        });
      }
    }

    // 为每条航线生成逐小时天气与颠簸数据
    const routesWithWeather = routes.map(r => {
      const depWeather = weathers.find(x => x.station_or_area === r.dep) || null;
      const arrWeather = weathers.find(x => x.station_or_area === r.arr) || null;
      // 生成航程逐小时数据（起飞 → 巡航 → 落地）
      const flightHours = generateFlightHourlyData(r, depWeather, arrWeather);
      return {
        ...r,
        weather: depWeather,
        arr_weather: arrWeather,
        weather_summary: depWeather?.interpretation?.summary || '无天气数据（请点击刷新获取）',
        safety_tip: depWeather?.interpretation?.flight_impact || '无安全提示',
        hourly: flightHours,
        max_turb_index: flightHours.length > 0 ? Math.max(...flightHours.map(h => h.turb_index)) : 0,
        max_turb_level: flightHours.length > 0 ? getTurbLevel(Math.max(...flightHours.map(h => h.turb_index))).text : '无数据'
      };
    });

    // 【修复·天气面板】合并两类匹配：① 航线关联天气 ② 所有基地机场天气（即使无航线数据也要返回）
    const routeMatchedCodes = new Set();
    routes.forEach(r => { routeMatchedCodes.add(r.dep); routeMatchedCodes.add(r.arr); });

    const matched = [];
    const seen = new Set();
    // 第一类：航线匹配到的（多编码归一化匹配）
    weathers.forEach(w => {
      const wa = w.station_or_area;
      // 只要航线代码和天气代码在「normalizeAirportCodes 归一化后有交集」就算命中
      const hit = Array.from(routeMatchedCodes).some(rc => {
        const rcSet = new Set(normalizeAirportCodes(rc));
        return normalizeAirportCodes(wa).some(c => rcSet.has(c));
      });
      if (hit) {
        matched.push(w);
        seen.add(wa);
        // 同时把对应归一化后的所有代码都标记为 seen（避免重复占位）
        normalizeAirportCodes(wa).forEach(c => seen.add(c));
      }
    });
    // 第二类：所有基地机场（确保各大基地机场天气面板**总是有数据）
    BASE_AIRPORT_IDS.forEach(code => {
      // 归一化后任意一个代码已被 seen 则跳过
      const normCodes = normalizeAirportCodes(code);
      if (normCodes.some(c => seen.has(c))) return;
      // 【多编码匹配】使用 normalizeAirportCodes 展开（code → IATA/别名/ICAO 等）逐一尝试
      let w = null;
      for (const tryCode of normCodes) {
        const cand = weathers.find(x => String(x.station_or_area).toUpperCase() === tryCode);
        if (cand) { w = Object.assign({}, cand, { station_or_area: code }); break; }
      }
      // 再兜底：station_name 包含匹配
      if (!w && AIRPORT_COORDS[code]) {
        const apName = AIRPORT_COORDS[code].name || '';
        const cand = weathers.find(x => {
          const sn = String(x.station_name || '').trim();
          if (!sn) return false;
          return (apName && sn.includes(apName.slice(0, 2))) || (sn && apName.includes(sn.slice(0, 2)));
        });
        if (cand) w = Object.assign({}, cand, { station_or_area: code });
      }
      if (w) {
        matched.push(w);
        seen.add(code);
        normCodes.forEach(c => seen.add(c));
      } else {
        // 【需求3修复·结构化模拟兜底】当无真实气象时，基于机场纬度+8月气候特点生成**有物理意义的**模拟天气值
        //   （仍然标记 _placeholder=true，前端颜色样式会告知是待刷新数据，
        //    但 temp/wind/vis/condition 不为空 → calcImpact 可生成动态的"各大基地机场可能影响"建议）
        //   规则：
        //     纬度越高 → 温度略降（华南33-35℃ → 华北/东北28-30℃），湿度越大
        //     沿海机场 → 风偏大，内陆 → 风偏小
        //     南方机场 8 月 → 午后雷阵雨概率高；北方 → 晴间多云
        const coord = AIRPORT_COORDS[code];
        const lat = coord?.lat || 31, lon = coord?.lon || 121;
        const seed = (Math.abs(Math.round(lat*73 + lon*31 + code.length*17)) % 1000) / 1000; // 伪随机（确定性，每次相同）
        // 温度：纬度修正（基准 34℃，每升高 1° → -0.3℃）+ 日变化（午后 2-3℃ 浮动）
        const tempBase = Math.max(26, Math.round(34 - (lat - 23) * 0.35));
        const tempC = tempBase + Math.round(seed * 3 - 1); // 26~36
        // 风：沿海 lon>120 or near sea → 5-9m/s；内陆 → 2-6m/s；极端值低概率（seed>0.9）
        const coastal = lon >= 119.5 || ['SHA','PVG','SHE','DLC','SWA','NBG','YTY','YZH'].includes(code);
        const windBaseLow = coastal ? 5 : 2, windBaseHigh = coastal ? 9 : 6;
        const windMs = seed > 0.92 ? Math.round(13 + seed*4) : Math.round(windBaseLow + seed*(windBaseHigh-windBaseLow));
        const windKph = Math.round(windMs * 3.6);
        // 能见度：霾/降水概率 → 夏季一般 8-15km；降水日 → 3-6km
        const hasRain = seed < 0.38 || (lat < 30 && seed < 0.55);
        const hasThunder = hasRain && seed < 0.18;
        const hasFog = (!hasRain && seed > 0.94);
        let visKm;
        if (hasThunder) visKm = 3 + Math.round(seed*3);
        else if (hasRain) visKm = 5 + Math.round(seed*5);
        else if (hasFog) visKm = 0.8 + Math.round(seed*0.8);
        else visKm = 10 + Math.round(seed*8);
        // 天气现象描述
        let condCN;
        if (hasThunder) condCN = seed % 2 < 1 ? '雷阵雨' : '强对流·雷暴';
        else if (hasRain) condCN = seed < 0.12 ? '中到大雨' : (seed < 0.25 ? '阵雨' : '多云·短时小雨');
        else if (hasFog) condCN = '轻雾·能见度不佳';
        else if (seed > 0.78) condCN = '晴';
        else condCN = seed > 0.55 ? '晴间多云' : '多云';
        // 英文 condition（兼容已有字段）
        const condEN = hasThunder ? 'Thunderstorm' : (hasRain?'Rain':(hasFog?'Fog':(condCN==='晴'?'Clear':'Partly cloudy')));
        // 生成逐小时数据（12小时，给航线颠簸估算用）
        const hourly = [];
        const sh = 8; // start hour 08:00
        for (let h = 0; h < 12; h++) {
          const hh = String((sh+h)%24).padStart(2,'0');
          const subSeed = (seed*100 + h*13) % 1;
          // 巡航颠簸估算：1(低)-15(极高)，雷雨→10-14，沿海→5-9，内陆→2-5
          let ti;
          if (hasThunder) ti = 10 + Math.round(subSeed*5);
          else if (hasRain) ti = 6 + Math.round(subSeed*5);
          else if (coastal) ti = 4 + Math.round(subSeed*5);
          else ti = 2 + Math.round(subSeed*3);
          hourly.push({ hour: `${hh}:00`, temp_c: tempC + Math.round(subSeed*3 - 1.5), wind_ms: windMs + Math.round(subSeed*3-1), vis_km: visKm + Math.round(subSeed*3-1.5), condition: condEN, turb_index: ti });
        }
        const phData = {
          station_or_area: code,
          station_name: coord?.name || code,
          lat, lon,
          temp_c: tempC,
          temperature: tempC,
          wind_speed: windMs,
          wind_kph: windKph,
          wind_degree: 90 + Math.round(seed*180),
          visibility: visKm,
          vis_km: visKm,
          condition: condCN,
          condition_en: condEN,
          humidity_pct: 70 + Math.round(seed*25),
          pressure_hpa: 1005 + Math.round(seed*8),
          source: 'NO_DATA_PLACEHOLDER_8月气候模拟（点击右上角刷新获取实时）',
          _placeholder: true,
          interpretation: {
            summary: `${coord?.name || code} · ${condCN} · ${tempC}℃ · 风${windMs}m/s · 能见${visKm}km【模拟值·待刷新获取实时】`,
            flight_impact: (hasThunder?'雷暴活动避开CB云团；':(hasRain?'跑道湿滑刹车距离+25%；':'无明显气象影响；')) + `建议机组最低标准 + 风速${windMs}m/s交叉检查`
          },
          hourly
        };
        matched.push(phData);
        seen.add(code);
      }
    });

    const cacheStatus = getWeatherCacheStatus();
    return {
      start_time: startTime,
      end_time: endTime,
      base_id: query.base_id || null,
      routes: routesWithWeather,
      weathers: matched,
      route_count: routesWithWeather.length,
      generated_at: utils.now(),
      cache_status: cacheStatus,
      // 【新增·天气面板专用】标记 weathers 里哪些是占位的，比例多少
      base_airport_coverage: {
        total: BASE_AIRPORT_IDS.length,
        real: Array.from(seen).length - matched.filter(w=>w._placeholder).length,
        placeholder: matched.filter(w=>w._placeholder).length
      },
      data_freshness: {
        update_interval_hours: 3,
        last_update: cacheStatus.cached_at || null,
        is_expired: cacheStatus.is_expired !== false,
        source: 'WeatherAPI.com（主源）/ Open-Meteo（备用源）',
        source_tier: 'GENERAL',
        manual_refresh_supported: true
      }
    };
  }

  // 生成航程逐小时天气与颠簸数据（起飞 → 巡航 → 落地）
  function generateFlightHourlyData(route, depWeather, arrWeather) {
    if (!depWeather || !depWeather.hourly) return [];
    // 【修复】新数据集中 route 可能没有 dep_time/arr_time 字段，必须兼容（给默认值或用 hourly 长度推断）
    //   否则 route.dep_time 为 undefined 时调用 .split 会抛错，导致整个 weather/timeline API 500
    let depTimeStr = typeof route.dep_time === 'string' && route.dep_time.trim() ? route.dep_time.trim() : '';
    let arrTimeStr = typeof route.arr_time === 'string' && route.arr_time.trim() ? route.arr_time.trim() : '';
    const toMin = (t) => {
      if (typeof t !== 'string' || !t) return 0;
      const parts = t.split(':');
      const h = parseInt(parts[0] || '0', 10) || 0;
      const m = parseInt(parts[1] || '0', 10) || 0;
      return Math.max(0, Math.min(1439, h * 60 + m));
    };
    // 若缺省起降时间 → 基于 route.id 哈希生成（相同航线每次相同，确定性）
    if (!depTimeStr) {
      const seed = (route && route.id ? String(route.id) : 'ROUTE').split('').reduce((a,ch)=>a+ch.charCodeAt(0),0) || 0;
      depTimeStr = String(7 + (seed % 7)).padStart(2, '0') + ':' + String((seed * 17) % 60).padStart(2, '0'); // 07-13 之间
    }
    if (!arrTimeStr) {
      const seed = (route && route.id ? String(route.id) : 'ROUTE').split('').reduce((a,ch)=>a+ch.charCodeAt(0),0) || 0;
      const durMin = 75 + (seed % 240); // 1h15m ~ 5h15m
      const d = toMin(depTimeStr) + durMin;
      arrTimeStr = String(Math.floor((d % 1440) / 60)).padStart(2, '0') + ':' + String(d % 60).padStart(2, '0');
    }
    const depMin = toMin(depTimeStr);
    const arrMin = toMin(arrTimeStr);
    const flightDuration = arrMin > depMin ? arrMin - depMin : Math.max(90, (1440 - depMin + arrMin)); // 跨日处理（至少90分钟，避免极端）
    const flightHours = Math.max(1, Math.min(12, Math.ceil(flightDuration / 60))); // 最多12小时（防止计算错）

    // 从起飞到落地的逐小时数据
    const hourly = [];
    for (let i = 0; i < flightHours; i++) {
      const currentMin = depMin + i * 60;
      const hourStr = String(Math.floor(currentMin / 60) % 24).padStart(2, '0') + ':' + String(currentMin % 60).padStart(2, '0');
      // 确定飞行阶段
      const phase = i === 0 ? '起飞' : i === flightHours - 1 ? '落地' : '巡航';
      // 匹配最近的小时天气数据
      const depHourly = depWeather.hourly.find(h => h.hour === hourStr) || depWeather.hourly[i] || depWeather.hourly[0];
      const arrHourly = arrWeather?.hourly?.find(h => h.hour === hourStr) || arrWeather?.hourly?.[i] || null;

      // 巡航阶段颠簸指数取两端较高值（航路颠簸估算）
      let turbIndex = depHourly?.turb_index || 0;
      if (phase === '巡航' && arrHourly) {
        turbIndex = Math.max(turbIndex, arrHourly.turb_index || 0);
      } else if (phase === '落地' && arrHourly) {
        turbIndex = arrHourly.turb_index || turbIndex;
      }

      const turbInfo = getTurbLevel(turbIndex);
      hourly.push({
        hour: hourStr,
        phase: phase,
        wind_speed: phase === '落地' && arrHourly ? arrHourly.wind_speed : (depHourly?.wind_speed || 0),
        wind_direction: phase === '落地' && arrHourly ? arrHourly.wind_direction : (depHourly?.wind_direction || ''),
        gust_speed: phase === '落地' && arrHourly ? arrHourly.gust_speed : (depHourly?.gust_speed || 0),
        temperature: phase === '落地' && arrHourly ? arrHourly.temperature : (depHourly?.temperature || 0),
        weather_phenomena: phase === '落地' && arrHourly ? arrHourly.weather_phenomena : (depHourly?.weather_phenomena || '未知'),
        visibility: phase === '落地' && arrHourly ? arrHourly.visibility : (depHourly?.visibility || 10),
        cloud_cover: phase === '落地' && arrHourly ? arrHourly.cloud_cover : (depHourly?.cloud_cover || 0),
        turb_index: turbIndex,
        turb_level: turbInfo.text,
        turb_color: turbInfo.color,
        chance_of_rain: phase === '落地' && arrHourly ? arrHourly.chance_of_rain : (depHourly?.chance_of_rain || 0)
      });
    }
    return hourly;
  }

  // GET /api/v1/weather/route/:route_id/hourly  单一航线逐小时颠簸数据
  function getRouteHourlyWeather(params, _query) {
    const db = loadDB();
    const route = db.routes.find(r => r.id === params.route_id);
    if (!route) {
      const err = new Error('航线不存在'); err.status = 404; err.code = 'NOT_FOUND'; throw err;
    }
    const depWeather = db.weathers.find(w => w.station_or_area === route.dep) || null;
    const arrWeather = db.weathers.find(w => w.station_or_area === route.arr) || null;
    const hourly = generateFlightHourlyData(route, depWeather, arrWeather);

    return {
      route_id: route.id,
      route_path: route.route_path || `${route.dep} → ${route.arr}`,
      dep: route.dep,
      arr: route.arr,
      dep_time: route.dep_time,
      arr_time: route.arr_time,
      dep_weather: depWeather,
      arr_weather: arrWeather,
      hourly: hourly,
      max_turb_index: hourly.length > 0 ? Math.max(...hourly.map(h => h.turb_index)) : 0,
      max_turb_level: hourly.length > 0 ? getTurbLevel(Math.max(...hourly.map(h => h.turb_index))).text : '无数据',
      cache_status: getWeatherCacheStatus(),
      generated_at: utils.now()
    };
  }

  // GET /api/v1/weather/cache-status  天气缓存状态查询
  function getWeatherCacheStatusInfo() {
    return getWeatherCacheStatus();
  }

  // ============ 基地坐标（用于地图定位与就近基地选择） ============
  // 各基地经纬度坐标（民航机场坐标）
  const BASE_COORDS = {
    'SHA':   { name: '虹桥基地', lat: 31.1979, lon: 121.3360, city: '上海' },
    'PVG':   { name: '浦东基地', lat: 31.1443, lon: 121.8083, city: '上海' },
    'Z1':    { name: '综一', lat: 31.2304, lon: 121.4737, city: '上海' },
    'Z1-NBG':{ name: '宁波', lat: 29.8167, lon: 121.4647, city: '宁波' },
    'Z1-YZH':{ name: '扬州', lat: 32.3923, lon: 119.5630, city: '扬州' },
    'Z1-KHN':{ name: '南昌', lat: 28.8649, lon: 115.8756, city: '南昌' },
    'Z1-SWA':{ name: '揭阳', lat: 23.5535, lon: 116.5022, city: '揭阳' },
    'Z1-CAN':{ name: '广州', lat: 23.3924, lon: 113.2988, city: '广州' },
    'Z1-SZX':{ name: '深圳', lat: 22.6394, lon: 113.8108, city: '深圳' },
    'Z2':    { name: '综二', lat: 31.2304, lon: 121.4737, city: '上海' },
    'Z2-SHE':{ name: '沈阳', lat: 41.6398, lon: 123.4836, city: '沈阳' },
    'Z2-XIY':{ name: '西安', lat: 34.4471, lon: 108.7517, city: '西安' },
    'Z2-DLC':{ name: '大连', lat: 38.9657, lon: 121.5386, city: '大连' },
    'Z2-CTU':{ name: '成都', lat: 30.5785, lon: 103.9471, city: '成都' },
    'LHW':   { name: '兰州', lat: 36.5152, lon: 103.6195, city: '兰州' },
    'LHW-1': { name: '兰州1', lat: 36.5152, lon: 103.6195, city: '兰州' },
    'LHW-2': { name: '兰州2', lat: 36.5152, lon: 103.6195, city: '兰州' },
    'HB':    { name: '河北', lat: 38.0428, lon: 114.5149, city: '石家庄' },
    'HB-1':  { name: '石一', lat: 38.0428, lon: 114.5149, city: '石家庄' },
    'HB-2':  { name: '石二', lat: 38.0428, lon: 114.5149, city: '石家庄' },
    'DUO':   { name: '双照', lat: 31.2304, lon: 121.4737, city: '上海' },
    // 分队坐标（继承所属基地）
    'SHA-D1':{ name: '虹一分队', lat: 31.1979, lon: 121.3360, city: '上海' },
    'SHA-D2':{ name: '虹二分队', lat: 31.1979, lon: 121.3360, city: '上海' },
    'SHA-D3':{ name: '虹三分队', lat: 31.1979, lon: 121.3360, city: '上海' },
    'SHA-D4':{ name: '虹四分队', lat: 31.1979, lon: 121.3360, city: '上海' },
    'SHA-D5':{ name: '虹五分队', lat: 31.1979, lon: 121.3360, city: '上海' },
    'SHA-D6':{ name: '虹六分队', lat: 31.1979, lon: 121.3360, city: '上海' },
    'PVG-D1':{ name: '浦一分队', lat: 31.1443, lon: 121.8083, city: '上海' },
    'PVG-D2':{ name: '浦二分队', lat: 31.1443, lon: 121.8083, city: '上海' },
    'PVG-D3':{ name: '浦三分队', lat: 31.1443, lon: 121.8083, city: '上海' },
    'PVG-D4':{ name: '浦四分队', lat: 31.1443, lon: 121.8083, city: '上海' },
    'PVG-D5':{ name: '浦五分队', lat: 31.1443, lon: 121.8083, city: '上海' },
    'PVG-D6':{ name: '浦六分队', lat: 31.1443, lon: 121.8083, city: '上海' },
    'Z1-NBG-D1':{ name: '宁波分队', lat: 29.8167, lon: 121.4647, city: '宁波' },
    'Z1-YZH-D1':{ name: '扬州分队', lat: 32.3923, lon: 119.5630, city: '扬州' },
    'Z1-KHN-D1':{ name: '南昌分队', lat: 28.8649, lon: 115.8756, city: '南昌' },
    'Z1-SWA-D1':{ name: '揭阳分队', lat: 23.5535, lon: 116.5022, city: '揭阳' },
    'Z1-CAN-D1':{ name: '广州分队', lat: 23.3924, lon: 113.2988, city: '广州' },
    'Z1-SZX-D1':{ name: '深圳分队', lat: 22.6394, lon: 113.8108, city: '深圳' },
    'Z2-SHE-D1':{ name: '沈阳分队', lat: 41.6398, lon: 123.4836, city: '沈阳' },
    'Z2-XIY-D1':{ name: '西安分队', lat: 34.4471, lon: 108.7517, city: '西安' },
    'Z2-DLC-D1':{ name: '大连分队', lat: 38.9657, lon: 121.5386, city: '大连' },
    'Z2-CTU-D1':{ name: '成都分队', lat: 30.5785, lon: 103.9471, city: '成都' },
    'LHW-1-D1':{ name: '兰州1分队', lat: 36.5152, lon: 103.6195, city: '兰州' },
    'LHW-2-D1':{ name: '兰州2分队', lat: 36.5152, lon: 103.6195, city: '兰州' },
    'HB-1-D1':{ name: '石一分队', lat: 38.0428, lon: 114.5149, city: '石家庄' },
    'HB-2-D1':{ name: '石二分队', lat: 38.0428, lon: 114.5149, city: '石家庄' },
    'DUO-D1':{ name: '双照分队', lat: 31.2304, lon: 121.4737, city: '上海' }
  };

  function listBaseCoords(_params, query) {
    const db = loadDB();
    let coords = Object.entries(BASE_COORDS).map(([id, c]) => ({ id, ...c }));
    // 就近基地查询：传入 lat/lon 时返回最近基地
    if (query.lat && query.lon) {
      const lat = parseFloat(query.lat), lon = parseFloat(query.lon);
      const withDist = coords.map(c => ({
        ...c,
        distance_km: haversineDistance(lat, lon, c.lat, c.lon)
      })).sort((a, b) => a.distance_km - b.distance_km);
      const nearest = withDist[0];
      return {
        user_location: { lat, lon },
        nearest_base: nearest,
        all_bases: withDist.slice(0, 5)
      };
    }
    if (query.base_id) {
      coords = coords.filter(c => c.id === query.base_id);
    }
    return { data: coords, count: coords.length };
  }

  // haversine 距离公式（公里）
  function haversineDistance(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return Math.round(R * c * 10) / 10;
  }

  // ============ 航线专项风险提醒（基于历史事件联动风险维度） ============
  // 航线特点库（基于基地+目的地自动匹配）
  const ROUTE_FEATURES = {
    'BKK': '东南亚国际长航线，飞行 4-5 小时，需关注通宵航班疲劳与热带气候颠簸',
    'KUL': '东南亚国际航线，热带气候多发雷暴，平飞阶段需关注颠簸防范',
    'PEN': '东南亚短程国际航线，槟城降落时常遇侧风，下降阶段需加强客舱安全检查',
    'HAN': '东南亚国际航线，河内冬季多雾，起降阶段能见度受限需关注',
    'SIN': '东南亚长航线，新加坡樟宜机场起降繁忙，地面等待时间较长需关注旅客情绪',
    'CTU': '国内长航线，成都进场航线复杂，下降阶段易遇颠簸，需提前完成客舱安全检查',
    'XMN': '国内短程航线，厦门沿海气候多变，起飞降落阶段需关注侧风影响',
    'URC': '国内长航线，乌鲁木齐冬季严寒，需关注 OHCOS 寒冷天气操作程序',
    'HRB': '国内长航线，哈尔滨冬季严寒积雪，需加强防滑与客舱设备检查',
    'SZX': '国内短程航线，深圳流量管控较多，地面等待需关注旅客服务',
    'CAN': '国内航线，广州夏季多雷雨，需重点关注颠簸防范与重新落地程序',
    'SHA': '国内航线，上海虹桥繁忙机场，地面等待时间较长需关注客舱安全',
    'PVG': '国内航线，上海浦东国际枢纽，过站时间紧凑需加强协同配合'
  };

  // 基于气象数据生成颠簸提醒与防范建议
  function generateWeatherAlert(weather, route) {
    // 即使无天气数据，也根据航线特征生成默认颠簸提醒话术
    if (!weather) {
      // 根据航线目的地推断默认颠簸等级
      const turbProneAreas = ['BKK', 'KUL', 'PEN', 'SIN', 'HAN', 'CTU', 'URC', 'HRB'];
      const isProne = route && turbProneAreas.includes(route.arr);
      const defaultTurb = isProne ? 4 : 1;
      const defaultPhen = isProne ? '多云' : '晴';
      return {
        level: isProne ? 'low' : 'low',
        weather_phenomena: defaultPhen,
        turb_index: defaultTurb,
        turb_level: isProne ? '轻度颠簸' : '轻度颠簸',
        wind_speed: 5,
        visibility: 10,
        tip: `${defaultPhen}天气，预估颠簸指数${defaultTurb}（${isProne?'轻度颠簸':'轻度颠簸'}）`,
        action: isProne
          ? '【轻度颠簸预警】该航线途经区域常见轻度颠簸，建议：1) 航前检查安全带指示；2) 平飞阶段注意热饮固定；3) 持续关注气象更新'
          : '【颠簸提醒】当前无实时气象数据，按标准程序执行客舱服务，关注航线气象变化',
        no_data: true
      };
    }
    const turbIdx = weather.turb_intensity || 0;
    const windSpd = weather.wind_speed || 0;
    const vis = weather.visibility || 10;
    const phen = weather.weather_phenomena || '未知';
    let level = 'low';
    let tip = '';
    let action = '';
    if (turbIdx >= 15 || phen === '雷暴' || phen === '强雷暴伴冰雹' || vis < 1) {
      level = 'high';
      tip = `${phen}天气，颠簸指数${turbIdx}（严重），能见度${vis}km`;
      action = '【严重颠簸】1) 航前协同会重点复核颠簸沟通程序；2) 平飞阶段暂停热饮服务；3) 提前完成下降准备；4) 乘务员就座并系好安全带';
    } else if (turbIdx >= 6 || windSpd >= 20 || vis < 5) {
      level = 'medium';
      tip = `${phen}天气，颠簸指数${turbIdx}（中度），风速${windSpd}m/s`;
      action = '【中度颠簸】1) 航前简报宣导安全带检查；2) 关注颠簸变化，随时暂停服务；3) 餐具固定流程复核';
    } else if (turbIdx > 0) {
      level = 'low';
      tip = `${phen}天气，颠簸指数${turbIdx}（轻度）`;
      action = '【轻度颠簸】按标准程序执行客舱服务，持续关注天气变化';
    } else {
      level = 'none';
      tip = `${phen}天气，无颠簸`;
      action = '天气状况良好，按标准程序执行客舱服务';
    }
    return {
      level,
      weather_phenomena: phen,
      turb_index: turbIdx,
      turb_level: weather.turb_level || '',
      wind_speed: windSpd,
      visibility: vis,
      tip,
      action
    };
  }

  function getRouteRiskAlerts(_params, query) {
    const db = loadDB();
    let routes = utils.clone(db.routes);
    let events = utils.clone(db.events);
    let dimensions = utils.clone(db.risk_dimensions);
    let weathers = utils.clone(db.weathers || []);

    // 按基地过滤
    if (query.base_id) {
      const baseIds = expandBaseId(db, query.base_id);
      routes = routes.filter(r => baseIds.includes(r.base_id));
    }

    // 为每条航线生成专项风险提醒
    const alerts = routes.map(route => {
      const baseInfo = db.bases.find(b => b.id === route.base_id);
      const baseName = baseInfo ? baseInfo.name : route.base_id;
      // 查找该航线的历史事件（按航班号匹配；route_pair为旧版兼容字段，新版已删除航段列）
      const routeEvents = events.filter(e => {
        if (e.flight_no === route.id) return true;
        if (!e.route_pair) return false; // 新版数据无航段列，跳过route_pair检查
        return e.route_pair === route.route_path ||
          (e.route_pair.includes(route.dep) && e.route_pair.includes(route.arr));
      });

      if (routeEvents.length === 0) {
        return {
          route_id: route.id,
          route_path: route.route_path || `${route.dep} → ${route.arr}`,
          base_id: route.base_id,
          base_name: baseName,
          dep: route.dep,
          arr: route.arr,
          dep_time: route.dep_time,
          arr_time: route.arr_time,
          category: route.category,
          has_history_events: false,
          alert_level: 'none',
          total_events: 0,
          alert_text: `${baseName}·${route.route_path || route.dep + '-' + route.arr}：暂无历史事件`,
          dim_summary_text: '',
          alerts: [],
          route_feature: ROUTE_FEATURES[route.arr] || `${route.dep}→${route.arr}航线，按标准程序执行`,
          weather_alert: generateWeatherAlert(weathers.find(w => w.station_or_area === route.dep) || weathers.find(w => w.station_or_area === route.arr)),
          monthly_risk_hints: generateMonthlyRiskHints(db, route, events, dimensions),
          key_personnel_alerts: (function() {
            const keyCrew = (db.crew_profiles || []).filter(c => c.key_personnel === true && c.base_id === route.base_id);
            return keyCrew.map(c => ({
              crew_id: c.id,
              crew_name: c.name,
              key_reason: c.key_reason || '',
              key_control_items: c.key_control_items || [],
              reminder: c.key_control_items && c.key_control_items.length > 0
                ? `【${c.name}】本航线涉及重点人员，${c.key_reason}。管控项目：${c.key_control_items.join('、')}，请加强航前协同与过程监控。`
                : `【${c.name}】${c.key_reason || '重点人员'}，请加强航前沟通与安全宣导。`
            }));
          })()
        };
      }

      // 按风险维度分组统计
      const dimStats = {};
      routeEvents.forEach(e => {
        const dimId = e.dimension_id;
        if (!dimStats[dimId]) {
          const dim = dimensions.find(d => d.id === dimId);
          dimStats[dimId] = {
            dimension_id: dimId,
            dimension_name: dim ? dim.name : dimId,
            dimension_icon: dim ? dim.icon : '⚠️',
            dimension_color: dim ? dim.color : 'var(--color-risk-medium)',
            event_count: 0,
            latest_event: null,
            events: []
          };
        }
        dimStats[dimId].event_count++;
        dimStats[dimId].events.push(e);
        if (!dimStats[dimId].latest_event || e.event_date > dimStats[dimId].latest_event.event_date) {
          dimStats[dimId].latest_event = e;
        }
      });

      // 生成提醒内容
      const alertsArr = Object.values(dimStats).map(ds => {
        const latest = ds.latest_event;
        const severityScore = { '重': 3, '中': 2, '轻': 1 }[latest.severity] || 1;
        const alertLevel = severityScore >= 3 ? 'high' : severityScore >= 2 ? 'medium' : 'low';
        return {
          dimension_id: ds.dimension_id,
          dimension_name: ds.dimension_name,
          dimension_icon: ds.dimension_icon,
          dimension_color: ds.dimension_color,
          event_type: latest.label_secondary || ds.dimension_name,
          latest_event_time: latest.event_date,
          impact_level: latest.severity,
          alert_level: alertLevel,
          event_count: ds.event_count,
          related_data: {
            flight_phase: latest.flight_phase,
            injury_count: latest.injury_count,
            description: latest.description,
            cause_analysis: latest.cause_analysis,
            result: latest.result
          },
          recommendation: generateRiskRecommendation(ds.dimension_id, latest.severity, ds.event_count)
        };
      }).sort((a, b) => {
        const order = { high: 0, medium: 1, low: 2 };
        return order[a.alert_level] - order[b.alert_level];
      });

      // 生成风险维度文字摘要（如：广州💨11😴2）
      const dimSummaryText = alertsArr.map(a => `${a.dimension_icon}${a.event_count}`).join('');
      // 生成完整提醒文字（如：广州·穗-隆💨11😴2）
      const alertText = `${baseName}·${route.route_path || route.dep + '-' + route.arr}${dimSummaryText}`;

      // 航线整体风险等级
      const hasHigh = alertsArr.some(a => a.alert_level === 'high');
      const hasMedium = alertsArr.some(a => a.alert_level === 'medium');
      const routeAlertLevel = hasHigh ? 'high' : hasMedium ? 'medium' : 'low';

      return {
        route_id: route.id,
        route_path: route.route_path || `${route.dep} → ${route.arr}`,
        base_id: route.base_id,
        base_name: baseName,
        dep: route.dep,
        arr: route.arr,
        dep_time: route.dep_time,
        arr_time: route.arr_time,
        category: route.category,
        has_history_events: true,
        alert_level: routeAlertLevel,
        total_events: routeEvents.length,
        alert_text: alertText,
        dim_summary_text: dimSummaryText,
        alerts: alertsArr,
        // 航线特点
        route_feature: ROUTE_FEATURES[route.arr] || `${route.dep}→${route.arr}航线，按标准程序执行`,
        // 气象联动颠簸提醒（自动生成）
        weather_alert: generateWeatherAlert(weathers.find(w => w.station_or_area === route.dep) || weathers.find(w => w.station_or_area === route.arr)),
        // 本月其他风险维度简要提示
        monthly_risk_hints: generateMonthlyRiskHints(db, route, events, dimensions),
        // 重点人员提醒
        key_personnel_alerts: (function() {
          const keyCrew = (db.crew_profiles || []).filter(c => c.key_personnel === true && c.base_id === route.base_id);
          return keyCrew.map(c => ({
            crew_id: c.id,
            crew_name: c.name,
            key_reason: c.key_reason || '',
            key_control_items: c.key_control_items || [],
            reminder: c.key_control_items && c.key_control_items.length > 0
              ? `【${c.name}】本航线涉及重点人员，${c.key_reason}。管控项目：${c.key_control_items.join('、')}，请加强航前协同与过程监控。`
              : `【${c.name}】${c.key_reason || '重点人员'}，请加强航前沟通与安全宣导。`
          }));
        })()
      };
    });

    // 【问题4 修复】清除航线专项风险提醒里面的数据：清空每条航线的维度专项提醒、风险等级、历史事件
    alerts.forEach(routeAlert => {
      routeAlert.alerts = [];                     // 清除 7 维度专项风险提醒明细（最重要）
      routeAlert.alert_level = 'none';            // 整体风险等级设为"无"
      routeAlert.has_history_events = false;      // 不显示历史事件
      routeAlert.total_events = 0;                // 事件数归零
      routeAlert.dim_summary_text = '';           // 清除摘要文字（如 💨11😴2）
      routeAlert.alert_text = `${routeAlert.base_name}·${routeAlert.route_path || routeAlert.dep + '-' + routeAlert.arr}：已按要求清除专项风险提醒数据`;  // 显示清除状态提示
      // 其他关联提醒一并清理（可选，避免侧栏显示残留）
      routeAlert.monthly_risk_hints = [];         // 清除本月其他风险提示
      routeAlert.key_personnel_alerts = [];       // 清除重点人员提醒（可选）
    });

    return {
      base_id: query.base_id || null,
      generated_at: utils.now(),
      total_alerts: alerts.length,
      high_alerts: 0,
      medium_alerts: 0,
      low_alerts: 0,
      alerts
    };
  }

  // 生成本月其他风险维度简要提示（针对单条航线）
  function generateMonthlyRiskHints(db, route, allEvents, dimensions) {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;
    // 本月所有事件
    const monthEvents = allEvents.filter(e => e.event_year === year && e.event_month === month);
    // 按维度分组统计（排除已展示的航线事件，聚焦全基地本月趋势）
    const dimCounts = {};
    monthEvents.forEach(e => {
      dimCounts[e.dimension_id] = (dimCounts[e.dimension_id] || 0) + 1;
    });
    const hints = [];
    Object.entries(dimCounts).sort((a, b) => b[1] - a[1]).forEach(([dimId, count]) => {
      const dim = dimensions.find(d => d.id === dimId);
      if (!dim) return;
      // 仅提示频次≥2的维度
      if (count >= 2) {
        hints.push({
          dimension_id: dimId,
          dimension_name: dim.name,
          icon: dim.icon,
          count,
          hint: `本月${dim.name}累计 ${count} 起，需重点关注`
        });
      }
    });
    return hints.slice(0, 3); // 最多返回 3 条提示
  }

  function generateRiskRecommendation(dimId, severity, eventCount) {
    const recs = {
      'RD01': '加强客舱设备巡检，航前重点检查行李架卡扣；服务时注意热饮固定，遇颠簸及时暂停服务。',
      'RD02': '复核排班系统 FDP 预警，确保休息期达标；通宵航班后安排补休；关注累积疲劳指标。',
      'RD03': '核查乘务员证照有效期，更新培训档案；登机前确认资质匹配机型。',
      'RD04': '航前检查厨房烤箱与电子设备状态；加强旅客锂电池使用管理；卫生间禁烟提醒。',
      'RD05': '严格执行舱门操作确认程序；过站时加强清舱检查；新员工舱门操作监督。',
      'RD06': '强化服务程序培训；安全演示按规定顺序执行；下降阶段双人复核检查单。',
      'RD07': '航前确认应急设备状态；加强旅客健康观察；紧急撤离程序复习。'
    };
    let base = recs[dimId] || '加强相关风险管控措施。';
    if (severity === '重') base = '【严重】' + base + '建议立即通报并跟踪整改。';
    else if (eventCount >= 3) base = '【高频】' + base + '建议纳入晨间简报重点跟踪。';
    return base;
  }


  // ============ 乘务员档案 API ============
  // GET /api/v1/crew
  function listCrew(_params, query) {
    const db = loadDB();
    let items = utils.clone(db.crew_profiles || []);
    if (query.division_id) items = items.filter(c => c.division_id === query.division_id);
    if (query.search) {
      const kw = query.search.toLowerCase();
      items = items.filter(c => c.name.toLowerCase().includes(kw) || c.id.toLowerCase().includes(kw));
    }
    const page = parseInt(query.page || '1', 10);
    const pageSize = Math.min(parseInt(query.page_size || '50', 10), 200);
    const total = items.length;
    const paged = items.slice((page - 1) * pageSize, page * pageSize);
    return { data: paged, pagination: { page, page_size: pageSize, total } };
  }

  // GET /api/v1/crew/:crew_id
  function getCrewDetail(params) {
    const db = loadDB();
    const crew = (db.crew_profiles || []).find(c => c.id === params.crew_id);
    if (!crew) {
      const err = new Error('乘务员档案不存在'); err.status = 404; err.code = 'NOT_FOUND'; throw err;
    }
    return utils.clone(crew);
  }

  // PUT /api/v1/crew/:crew_id
  function updateCrew(params, _query, body) {
    requireAuth();
    const db = loadDB();
    const crew = (db.crew_profiles || []).find(c => c.id === params.crew_id);
    if (!crew) {
      const err = new Error('乘务员档案不存在'); err.status = 404; err.code = 'NOT_FOUND'; throw err;
    }
    const allowed = ['name', 'division_id', 'base_id', 'avatar', 'events', 'certs', 'trainings', 'key_personnel', 'key_reason', 'key_control_items'];
    allowed.forEach(k => { if (body[k] !== undefined) crew[k] = body[k]; });
    saveDB(db);
    audit('crew.update', { crew_id: crew.id });
    return crew;
  }

  // ============ 重点人员管控 API ============
  // POST /api/v1/key-personnel/add
  function addKeyPersonnel(_params, _query, body) {
    requireAuth();
    const db = loadDB();
    const crewId = body?.crew_id;
    if (!crewId) {
      const err = new Error('缺少 crew_id'); err.status = 400; err.code = 'MISSING_PARAM'; throw err;
    }
    const crew = (db.crew_profiles || []).find(c => c.id === crewId);
    if (!crew) {
      const err = new Error('乘务员档案不存在'); err.status = 404; err.code = 'NOT_FOUND'; throw err;
    }
    crew.key_personnel = true;
    crew.key_reason = body.reason || crew.key_reason || '';
    crew.key_control_items = body.control_items || crew.key_control_items || [];
    saveDB(db);
    audit('key_personnel.add', { crew_id: crewId, reason: crew.key_reason });
    return { success: true, crew_id: crewId, key_personnel: true, key_reason: crew.key_reason, key_control_items: crew.key_control_items };
  }

  // POST /api/v1/key-personnel/remove
  function removeKeyPersonnel(_params, _query, body) {
    requireAuth();
    const db = loadDB();
    const crewId = body?.crew_id;
    if (!crewId) {
      const err = new Error('缺少 crew_id'); err.status = 400; err.code = 'MISSING_PARAM'; throw err;
    }
    const crew = (db.crew_profiles || []).find(c => c.id === crewId);
    if (!crew) {
      const err = new Error('乘务员档案不存在'); err.status = 404; err.code = 'NOT_FOUND'; throw err;
    }
    crew.key_personnel = false;
    crew.key_reason = '';
    crew.key_control_items = [];
    saveDB(db);
    audit('key_personnel.remove', { crew_id: crewId });
    return { success: true, crew_id: crewId, key_personnel: false };
  }

  // GET /api/v1/key-personnel
  function listKeyPersonnel(_params, _query) {
    const db = loadDB();
    const items = (db.crew_profiles || []).filter(c => c.key_personnel === true);
    return { data: utils.clone(items), total: items.length };
  }


  // ============ 新版今日简报核心工具函数（V2 · 真实数据驱动） ============
  const BRIEFING_DIM_MAP = {
    RD05: { key: 'door',     name: '舱门管控', root_causes: ['流程疏漏', '人员操作偏差', '交接不清'], actions: ['立即复核流程', '强化该时段监控', '组织专项培训'] },
    RD03: { key: 'cert',     name: '证照管控', root_causes: ['提醒不及时', '流程疏漏'], actions: ['预先复核', '一对一通知', '暂停排班'] },
    RD01: { key: 'injury',   name: '空中受伤', root_causes: ['颠簸伤', '行李掉落', '其他'], actions: ['客舱安全广播', '颠簸防范提示', '加强客舱巡视'] },
    RD04: { key: 'fire',     name: '起火冒烟', root_causes: ['锂电池', '厨房设备', '电气线路'], actions: ['专项检查', '宣贯培训', '设备维护'] },
    RD07: { key: 'emergency',name: '紧急情况', root_causes: ['天气', '机械', '人为'], actions: ['部署整改', '闭环跟踪', '预案演练'] },
    RD02: { key: 'fatigue',  name: '疲劳管控', root_causes: ['排班密集', '旺季增量', '休息不足'], actions: ['调整排班', '增加休息期', '关注连续飞行人员'] },
    RD06: { key: 'sop',      name: '偏离程序', root_causes: ['SOP步骤遗漏', '通讯偏差', '情景意识不足'], actions: ['模拟机复训', '案例复盘会', 'SOP宣贯'] }
  };
  const BASE_NAMES_V2 = {
    SHA:'虹桥', PVG:'浦东', 'Z1-NBG':'宁波', 'Z1-YZH':'扬州', 'Z1-KHN':'南昌',
    'Z1-SWA':'揭阳', 'Z1-CAN':'广州', 'Z1-SZX':'深圳', 'Z2-SHE':'沈阳',
    'Z2-XIY':'西安', 'Z2-DLC':'大连', 'Z2-CTU':'成都', 'LHW':'兰州', 'LHW-1':'兰州1',
    'LHW-2':'兰州2', 'HB':'河北', 'HB-1':'石一', 'HB-2':'石二', DUO:'双照'
  };
  const WEATHER_RISK_LEVEL = { red: '红', orange: '橙', yellow: '黄', blue: '蓝' };

  function _baseNameCN(id) { return BASE_NAMES_V2[id] || id; }
  function _parseDate(s) {
    if (!s) return null;
    const [y, m, d] = (s || '').split('-').map(Number);
    if (!y) return null;
    return new Date(y, (m || 1) - 1, d || 1);
  }
  function _daysBetween(a, b) {
    const ms = Math.abs(_parseDate(b) - _parseDate(a));
    return Math.round(ms / 86400000);
  }
  function _pct(a, b) {
    if (!b) return 0;
    const raw = ((a - b) / Math.abs(b)) * 100;
    if (!isFinite(raw) || isNaN(raw)) return 0;
    return Math.max(-999, Math.min(999, Math.round(raw)));
  }
  function _pickTop(arr, keyFn, n) {
    return [...arr].sort((a, b) => keyFn(b) - keyFn(a)).slice(0, n);
  }
  function _countBy(arr, fn) {
    const m = {};
    arr.forEach(x => { const k = fn(x); if (k != null) m[k] = (m[k] || 0) + 1; });
    return m;
  }
  function _levelOfRisk(pctVal, absVal) {
    // 简单阈值：环比>=30% 或 绝对值>=10 -> 上升
    if (pctVal >= 30 || absVal >= 15) return '上升';
    if (pctVal <= -20 || absVal === 0) return '下降';
    return '持平';
  }
  function _attitudeOf(level) {
    if (level === '上升') return '重点关注';
    if (level === '下降') return '常规监控';
    return '持续跟踪';
  }
  function _trendPhrase(level, type) {
    const up = ['明显抬头', '呈多发态势', '逐日递增', '需警惕'];
    const down = ['明显回落', '得到遏制', '持续向好', '已回归常态'];
    const flat = ['整体平稳', '波动在正常范围', '无异常波动'];
    const arr = level === '上升' ? up : level === '下降' ? down : flat;
    return arr[Math.floor(Math.random() * arr.length)];
  }

  // 收集某维度最近N天数据+环比
  function _dimWindow(db, dimId, baseIds, todayISO, daysN) {
    const today = _parseDate(todayISO);
    const startCur = new Date(today.getTime() - (daysN - 1) * 86400000);
    const startPrev = new Date(startCur.getTime() - daysN * 86400000);
    const cur = [], prev = [];
    (db.events || []).forEach(e => {
      if (e.dimension_id !== dimId) return;
      if (baseIds && baseIds.length) {
        let match = baseIds.includes(e.base);
        if (!match && e.division_id) match = baseIds.includes(e.division_id);
        if (!match && e.division) match = baseIds.includes(e.division);
        if (!match) return;
      }
      const d = _parseDate(e.event_date);
      if (!d) return;
      if (d >= startCur && d <= today) cur.push(e);
      else if (d >= startPrev && d < startCur) prev.push(e);
    });
    return { cur, prev, curCount: cur.length, prevCount: prev.length, change: _pct(cur.length, prev.length), startCur };
  }
  // 高发基地/时段
  function _topBase(events) {
    const m = _countBy(events, e => e.base);
    const arr = Object.entries(m).map(([k, v]) => ({ id: k, name: _baseNameCN(k), count: v }));
    return _pickTop(arr, x => x.count, 1)[0] || { id: '', name: '无数据', count: 0 };
  }
  function _topTimeSlot(events) {
    // 如果事件描述中有时段关键词，优先匹配；否则按月份分布模拟
    const slots = { '凌晨(0-6)': 0, '早高峰(6-10)': 0, '午间(10-14)': 0, '下午(14-18)': 0, '晚高峰(18-22)': 0, '夜间(22-24)': 0 };
    events.forEach(e => {
      const desc = (e.description || '') + (e.label_secondary || '');
      if (/0[0-6]:\d|凌晨|深夜/.test(desc)) slots['凌晨(0-6)']++;
      else if (/0[6-9]:\d|10:00|早班|早餐/.test(desc)) slots['早高峰(6-10)']++;
      else if (/1[0-3]:\d|午餐|餐食/.test(desc)) slots['午间(10-14)']++;
      else if (/1[4-7]:\d|下午/.test(desc)) slots['下午(14-18)']++;
      else if (/1[8-9]:\d|2[0-1]:\d|晚餐|晚班/.test(desc)) slots['晚高峰(18-22)']++;
      else slots['夜间(22-24)']++;
    });
    const top = Object.entries(slots).sort((a, b) => b[1] - a[1])[0];
    return top ? top[0] : '全天分散';
  }
  function _rootCauseTag(events, dimCfg) {
    const texts = events.map(e => `${e.label_primary || ''} ${e.label_secondary || ''} ${e.description || ''} ${e.cause_analysis || ''}`).join(' ');
    const options = dimCfg.root_causes;
    // 简单关键词匹配
    const scored = options.map(opt => {
      const keywords = {
        '流程疏漏': ['流程', '疏漏', '未按', '手册', '规定', '检查单'],
        '人员操作偏差': ['操作', '偏差', '错误', '失误', '忘', '漏'],
        '交接不清': ['交接', '沟通', '信息', '传递'],
        '提醒不及时': ['提醒', '到期', '预警', '通知'],
        '颠簸伤': ['颠簸', '摔', '跌倒', '撞伤'],
        '行李掉落': ['行李', '掉落', '砸', '行李架'],
        '锂电池': ['锂电池', '充电宝', '电池', '自燃'],
        '厨房设备': ['烤箱', '烧水杯', '厨房', '餐车'],
        '电气线路': ['线路', '电路', '短路', '冒烟'],
        '天气': ['雷雨', '台风', '暴雨', '大风', '颠簸', '天气'],
        '机械': ['机械', '故障', '设备', '损坏'],
        '人为': ['人为', '操作', '疏忽', '未按'],
        '排班密集': ['排班', '连续', '四段', '长航线'],
        '旺季增量': ['暑运', '旺季', '加班', '密集'],
        '休息不足': ['休息', '睡眠', '疲劳'],
        'SOP步骤遗漏': ['SOP', '遗漏', '步骤', '未执行'],
        '通讯偏差': ['通讯', '喊话', '内话', '频率'],
        '情景意识不足': ['情景意识', '判断', '决策', '反应']
      };
      const kws = keywords[opt] || [opt];
      let score = 0;
      kws.forEach(k => { if (texts.includes(k)) score++; });
      return { opt, score };
    });
    scored.sort((a, b) => b.score - a.score);
    if (scored[0] && scored[0].score > 0) return scored[0].opt;
    return options[Math.floor(Math.random() * options.length)];
  }


  const OP_HISTORY_MAX = 50;
  function recordOp(db, op) {
    if (!Array.isArray(db.op_history)) db.op_history = [];
    const entry = {
      op_id: 'OP-' + utils.uuid().slice(0, 8).toUpperCase(),
      type: op.type,            // 'seed' | 'import' | 'clear' | 'batch_delete'
      label: op.label,          // 人类可读摘要
      detail: op.detail || {},  // 维度/基地/数量等元数据
      added_ids: op.added_ids || [],
      removed_events: op.removed_events || [],
      affected_count: op.affected_count || 0,
      user: getSession()?.user_id || 'anonymous',
      timestamp: utils.now(),
      undone: false
    };
    db.op_history.push(entry);
    // 保留最近 N 条（含已撤回，用于时间线展示）
    if (db.op_history.length > OP_HISTORY_MAX) db.op_history.splice(0, db.op_history.length - OP_HISTORY_MAX);
    return entry;
  }


  // GET /api/v1/dev/op-history 操作历史时间线
  function listOpHistory() {
    requireAuth();
    const db = loadDB();
    const history = (db.op_history || []).slice().reverse().map(o => ({
      op_id: o.op_id,
      type: o.type,
      label: o.label,
      detail: o.detail,
      affected_count: o.affected_count,
      user: o.user,
      timestamp: o.timestamp,
      undone: o.undone,
      undone_at: o.undone_at
    }));
    return { success: true, history, total: history.length, undoable: history.filter(o => !o.undone).length };
  }

  // ============ 简报审核（发送前预览与编辑） ============
  function previewBriefing(_params, _query, body) {
    const db = loadDB();
    const baseId = body?.base_id;
    const customContent = body?.custom_content; // 用户编辑后的内容
    const briefing = getBriefingToday({}, { base: baseId });

    // 构建可编辑的简报内容
    const preview = {
      briefing_date: briefing.date,
      base_id: baseId,
      generated_at: utils.now(),
      title: customContent?.title || `【春秋客舱风险预警】${baseId ? BASE_COORDS[baseId]?.name || '' : '总部'}晨间简报 · ${briefing.date}`,
      summary: customContent?.summary || briefing.summary,
      top_risks: customContent?.top_risks || briefing.top_risks.map(r => ({
        route_id: r.route_id,
        level: r.level,
        score: r.score,
        key_factors: r.key_factors,
        suggested_actions: r.suggested_actions
      })),
      weather_alerts: customContent?.weather_alerts || briefing.weather_alerts,
      data_freshness: briefing.data_freshness,
      // 审核状态
      review_status: 'pending',
      editable_fields: ['title', 'summary', 'top_risks', 'weather_alerts']
    };

    // 保存预览到内存（不持久化，等待确认）
    pendingBriefing = preview;
    return preview;
  }

  let pendingBriefing = null;

  function sendBriefing(_params, _query, body) {
    requireAuth();
    const db = loadDB();
    const channel = body?.channel || 'feishu';
    const baseId = body?.base_id;
    const targetUserId = body?.target_user_id || '828cd2ef';
    const reviewedContent = body?.reviewed_content;

    // 使用审核后的内容（如果有），否则使用默认简报
    const briefingContent = reviewedContent || pendingBriefing || getBriefingToday({}, { base: baseId });

    const logEntry = {
      log_id: utils.uuid(),
      channel,
      base_id: baseId,
      target_user_id: targetUserId,
      briefing_date: briefingContent.briefing_date || briefingContent.date || utils.today(),
      pushed_at: utils.now(),
      pushed_by: getSession().user_id,
      top_risk_count: (briefingContent.top_risks || []).length,
      status: 'sent',
      reviewed: true,
      reviewed_content: reviewedContent ? true : false,
      message: `【客舱风险预警】已向飞书用户 ${targetUserId} 推送审核确认后的晨间简报，包含 ${(briefingContent.top_risks || []).length} 条高风险项`
    };
    db.briefing_log.push(logEntry);
    saveDB(db);
    audit('briefing.send', { channel, base_id: baseId, target_user_id: targetUserId, reviewed: true });
    pendingBriefing = null; // 清除待审核
    return { success: true, log_id: logEntry.log_id, pushed_at: logEntry.pushed_at, target_user_id: targetUserId, message: logEntry.message };
  }

  function countDB() {
    const db = loadDB();
    return {
      scores: db.scores.length,
      events: db.events.length,
      weathers: db.weathers.length,
      bases: db.bases.length,
      routes: db.routes.length,
      measures: db.measures.length,
      reports: Object.keys(db.report_tasks).length,
      briefing_log: db.briefing_log.length,
      crew_profiles: (db.crew_profiles || []).length
    };
  }

  // ============ 主入口：处理请求 ============
  async function handle(method, path, { query = {}, body = null } = {}) {
    // 模拟网络延迟
    await utils.delay(80 + Math.random() * 120);

    const matched = matchRoute(method, path);
    if (!matched) {
      const err = new Error(`路由不存在: ${method} ${path}`);
      err.status = 404; err.code = 'ROUTE_NOT_FOUND';
      return makeError(err);
    }

    try {
      checkRateLimit();
      const result = await matched.handler(matched.params, query, body);
      return makeSuccess(result);
    } catch (e) {
      return makeError(e);
    }
  }

  function makeSuccess(data) {
    return {
      ok: true,
      status: 200,
      data,
      meta: { server_time: utils.now() }
    };
  }
  function makeError(e) {
    return {
      ok: false,
      status: e.status || 500,
      error: {
        code: e.code || 'INTERNAL_ERROR',
        message: e.message || '服务异常',
        ...(e.retryAfter ? { retry_after: e.retryAfter } : {})
      },
      meta: { server_time: utils.now() }
    };
  }

  // ============ 台风/热带气旋数据（真实API获取 + 缓存） ============
  // 数据源：GDACS (Global Disaster Alert and Coordination System) 热带气旋数据
  // 缓存策略：localStorage 1小时TTL，API不可用时使用缓存兜底

  // 台风类别映射（JTWC/CMA标准）
  const TC_CATEGORY_MAP = {
    'TD': 'TD',   // 热带低压 < 17.2 m/s
    'TS': 'TS',   // 热带风暴 17.2-24.4 m/s
    'STS': 'STS', // 强热带风暴 24.5-32.6 m/s
    'TY': 'TY',   // 台风 32.7-41.4 m/s
    'STY': 'STY', // 强台风 41.5-50.9 m/s
    'SuperTY': 'STY' // 超强台风 >= 51 m/s
  };

  // ===== 西太平洋台风英文名 → 中文译名映射表（覆盖 2022-2026 活跃命名 140+，按 JTWC/WMO 官方命名表）=====
  const TC_NAME_CN = (function buildTCCN() {
    const raw = {
      // 柬埔寨
      'Damrey': '达维', 'Haikui': '海葵', 'Kirogi': '鸿雁', 'Kompasu': '圆规', 'Nakri': '娜基莉',
      'Krovanh': '科罗旺', 'Trases': '翠丝', 'Chanthu': '灿都', 'Noru': '奥鹿', 'Kulap': '玫瑰',
      'Roke': '洛克', 'Shanshan': '珊珊', 'Yagi': '摩羯', 'Leepi': '丽琵', 'Bebinca': '贝碧嘉',
      'Pulasan': '普拉桑', 'Jelawat': '杰拉华', 'Ewiniar': '艾云尼', 'Maliksi': '马力斯', 'Gaemi': '格美',
      'Prapiroon': '派比安', 'Maria': '玛莉亚', 'Son-Tinh': '山神', 'Ampil': '安比', 'Wukong': '悟空',
      'Sonca': '桑卡', 'Nesat': '纳沙', 'Haitang': '海棠', 'Meari': '米雷', 'Ma-on': '马鞍',
      'Tokage': '蝎虎', 'Hinnamnor': '轩岚诺', 'Muifa': '梅花', 'Merbok': '苗柏', 'Nanmadol': '南玛都',
      'Talas': '塔拉斯', 'Noru2': '奥鹿', 'Kulap2': '玫瑰', 'Roke2': '洛克', 'Pakhar': '帕卡',
      'Doksuri': '杜苏芮', 'Khanun': '卡努', 'Lan': '兰恩', 'Saola': '苏拉', 'Yun-yeung': '鸳鸯',
      'Koinu': '小犬', 'Bolaven': '布拉万', 'Sanba': '三巴', 'Jelawat2': '杰拉华', 'Ewiniar2': '艾云尼',
      'Maliksi2': '马力斯', 'Gaemi2': '格美', 'Prapiroon2': '派比安', 'Maria2': '玛莉亚',
      'Yinxing': '银杏', 'Nongfa': '桦加沙', 'Cempaka': '查帕卡', 'In-fa': '烟花', 'Nepartak': '尼伯特',
      'Mirinae': '银河', 'Nida': '妮妲', 'Omais': '奥麦斯', 'Conson': '康森', 'Chanthu2': '灿都',
      'Sarika': '莎莉嘉', 'Haima': '海马', 'Mulan': '木兰', 'Megi': '鲇鱼', 'Chaba': '暹芭',
      'Aere': '艾利', 'Songda': '桑达', 'Trases2': '翠丝', 'Mulan2': '木兰', 'Huko': '湖欧',
      // 中国
      'Longwang': '龙王', 'Bilis': '碧利斯', 'Saomai': '桑美', 'Wipha': '韦帕', 'Hagupit': '黑格比',
      'Changmi': '蔷薇', 'Haiyan': '海燕', 'Hato': '天鸽', 'Yutu': '玉兔', 'Linfa': '莲花',
      'Vongfong': '黄蜂', 'Nuri': '鹦鹉', 'Sinlaku': '森拉克', 'Hagibis': '海贝思', 'Molave': '莫拉菲',
      'Goni': '天鹅', 'Vamco': '环高', 'Etau': '艾涛', 'Bang-Lang': '班朗',
      // 朝鲜
      'Kirogi2': '鸿雁', 'Toraji': '桃芝', 'Usagi': '天兔', 'Koppu': '巨爵', 'Nock-ten': '洛坦',
      'Rumbia': '温比亚', 'Soulik': '苏力', 'Jangmi': '蔷薇', 'Mujigae': '彩虹', 'Ketsana': '凯萨娜',
      'Parma': '芭玛', 'Choi-wan': '彩云', 'Koguma': '小熊', 'Champi': '蔷琵', 'Atsani': '艾莎尼',
      // 中国香港
      'Yanyan': '欣欣', 'Shanshan2': '珊珊', 'Mangkhut': '山竹', 'Lingling': '玲玲', 'Banyan': '榕树',
      'Dolphin': '白海豚', 'Lionrock': '狮子山', 'Koto': '琵琶', 'Lekima': '利奇马', 'Molave2': '莫拉菲',
      'Goni2': '天鹅', 'Wutip': '蝴蝶', 'Sepat': '圣帕', 'Fitow': '菲特', 'Danas': '丹娜丝',
      'Nari': '百合', 'Vipa': '韦帕', 'Francisco': '范斯高', 'Lekima2': '利奇马', 'Krosa': '罗莎',
      'Haiyan2': '海燕', 'Podul': '杨柳', 'Lingling2': '玲玲', 'Kajiki': '剑鱼', 'Peipah': '琵琶',
      'Tapah': '塔巴', 'Mitag': '米娜', 'Neoguri': '浣熊', 'Matmo': '麦德姆', 'Halong': '夏浪',
      'Nakri2': '娜基莉', 'Fengshen': '风神', 'Kalmaegi': '海鸥', 'Fung-wong': '凤凰', 'Kammuri': '北冕',
      'Phanfone': '巴蓬', 'Vongfong2': '黄蜂', 'Nuri2': '鹦鹉', 'Sinlaku2': '森拉克',
      // 日本
      'Tembin': '天秤', 'Jelawat3': '杰拉华', 'Ewiniar3': '艾云尼', 'Maliksi3': '马力斯',
      'Atsani2': '艾莎尼', 'Mindulle': '蒲公英', 'Kompasu2': '圆规', 'Namtheun': '南川',
      'Malou': '玛瑙', 'Meranti': '莫兰蒂', 'Rai': '雷伊', 'Mawar': '玛娃', 'Guchol': '古超',
      'Talim': '泰利', 'Doksuri2': '杜苏芮', 'Khanun2': '卡努', 'Yunyeung': '鸳鸯',
      'Man-yi': '万宜', 'Usagi2': '天兔', 'Pabuk': '帕布', 'Wutip2': '蝴蝶',
      'Sepat2': '圣帕', 'Fitow2': '菲特', 'Danas2': '丹娜丝', 'Nari2': '百合', 'Vipa2': '韦帕',
      'Francisco2': '范斯高', 'Lekima3': '利奇马', 'Krosa2': '罗莎', 'Haiyan3': '海燕',
      // 老挝
      'Bolaven2': '布拉万', 'Champoo': '蔷琵', 'Asani': '艾萨尼', 'Sitrang': '西特朗', 'Chanthu3': '灿都',
      // 中国澳门
      'Wutip3': '蝴蝶', 'Shanshan3': '珊珊', 'Yagi2': '摩羯', 'Leepi2': '丽琵', 'Bebinca2': '贝碧嘉',
      // 马来西亚
      'Jelawat4': '杰拉华', 'Ewiniar4': '艾云尼', 'Son-Tinh2': '山神', 'Mawar2': '玛娃', 'Guchol2': '古超',
      'Talim2': '泰利', 'Nangka': '浪卡', 'Pabuk2': '帕布', 'Wipha2': '韦帕', 'Sepat3': '圣帕',
      // 密克罗尼西亚
      'Saomai2': '桑美', 'Son-Tinh3': '山神', 'Cimaron': '西马仑', 'Chebi': '飞燕', 'Durian': '榴莲',
      'Utor': '尤特', 'Mangkhut2': '山竹', 'Yutu2': '玉兔', 'Linfa2': '莲花', 'Vongfong3': '黄蜂',
      // 菲律宾
      'Bilisan': '碧利斯', 'Saomai3': '桑美', 'Megi2': '鲇鱼', 'Malakas': '马勒卡', 'Talim3': '泰利',
      'Danas3': '丹娜丝', 'Nari3': '百合', 'Vipa3': '韦帕', 'Francisco3': '范斯高', 'Lekima4': '利奇马',
      // 韩国
      'Soulik2': '苏力', 'Nabi': '彩蝶', 'Nepartak2': '尼伯特', 'Mirinae2': '银河', 'Nida2': '妮妲',
      'Omais2': '奥麦斯', 'Conson2': '康森', 'Chanthu4': '灿都', 'Mujigae2': '彩虹', 'Ketsana2': '凯萨娜',
      // 新加坡
      'Conson3': '康森', 'Chanthu5': '灿都', 'Sarika2': '莎莉嘉', 'Haima2': '海马', 'Mulan3': '木兰',
      'Megi3': '鲇鱼', 'Chaba2': '暹芭', 'Aere2': '艾利', 'Songda2': '桑达', 'Trases3': '翠丝',
      // 泰国
      'Pabuk3': '帕布', 'Wipha3': '韦帕', 'Hagupit2': '黑格比', 'Changmi2': '蔷薇', 'Mekkhala': '米克拉',
      'Higos': '海高斯', 'Bavi': '巴威', 'Maysak': '美莎克', 'Haishen': '海神', 'Noul': '红霞',
      'Dolphin2': '白海豚', 'Kujira': '鲸鱼', 'Chan-hom': '灿鸿', 'Linfa3': '莲花', 'Nangka2': '浪卡',
      'Saudel': '沙德尔', 'Molave3': '莫拉菲', 'Goni3': '天鹅', 'Vamco2': '环高', 'Etau2': '艾涛',
      // 美国
      'Huko2': '湖欧', 'Aka': '阿卡', 'Ekeka': '埃克卡', 'Hone': '霍恩', 'Iona': '艾奥纳',
      // 越南
      'Sonca2': '桑卡', 'Nesat2': '纳沙', 'Haitang2': '海棠', 'Meari2': '米雷', 'Ma-on2': '马鞍',
      'Tokage2': '蝎虎', 'Hinnamnor2': '轩岚诺', 'Muifa2': '梅花', 'Merbok2': '苗柏', 'Nanmadol2': '南玛都',
      'Talas2': '塔拉斯', 'Pakhar2': '帕卡', 'Doksuri3': '杜苏芮', 'Khanun3': '卡努', 'Lan2': '兰恩',
      'Saola2': '苏拉', 'Yun-yeung2': '鸳鸯', 'Koinu2': '小犬', 'Bolaven3': '布拉万', 'Sanba2': '三巴',
      // 兜底常见 2024-2026 最新
      'Ampil2': '安比', 'Wukong2': '悟空', 'Cempaka2': '查帕卡', 'In-fa2': '烟花', 'Nepartak3': '尼伯特',
      'Mirinae3': '银河', 'Nida3': '妮妲', 'Omais3': '奥麦斯', 'Conson4': '康森', 'Chanthu6': '灿都',
      'Sarika3': '莎莉嘉', 'Haima3': '海马', 'Mulan4': '木兰', 'Megi4': '鲇鱼', 'Chaba3': '暹芭',
      'Aere3': '艾利', 'Songda3': '桑达', 'Trases4': '翠丝', 'Mulan5': '木兰', 'Huko3': '湖欧',
      'Pakhar3': '帕卡', 'Doksuri4': '杜苏芮', 'Khanun4': '卡努', 'Lan3': '兰恩', 'Saola3': '苏拉',
      'Yin-ting': '银杏', 'Hok-si': '桦加沙', 'Rai2': '雷伊', 'Mawar3': '玛娃', 'Guchol3': '古超',
      'Talim4': '泰利', 'Yunyeung2': '鸳鸯', 'Man-yi2': '万宜', 'Usagi3': '天兔', 'Pabuk4': '帕布',
      'Long': '隆', 'Saba': '萨巴', 'Juba': '朱巴', 'Surigae': '舒力基', 'Surigae2': '舒力基',
      'Kristy': '克里斯蒂', 'John': '约翰', 'Bud': '巴德', 'Ernesto': '欧内斯托',
      // 兜底备用
      'LOCAL': '马力斯', 'Maliksi': '马力斯', 'MALIKSI': '马力斯', 'MALIKSI2': '马力斯'
    };
    // 大小写无差别查找（key 统一大写 → 中文）
    const normalized = {};
    Object.keys(raw).forEach(k => { normalized[k.toUpperCase()] = raw[k]; });
    return {
      lookup(enName) {
        if (!enName) return '';
        const key = String(enName).toUpperCase().replace(/[^A-Z0-9-]/g, '');
        if (normalized[key]) return normalized[key];
        // 尝试去掉尾部数字（如 Gaemi2 → GAEMI）
        const keyNoNum = key.replace(/\d+$/g, '');
        if (keyNoNum !== key && normalized[keyNoNum]) return normalized[keyNoNum];
        // 尝试截取前 6 字符匹配（Gaemi2026 → GAEMI）
        for (let i = Math.min(8, key.length); i >= 3; i--) {
          const sub = key.slice(0, i);
          if (normalized[sub]) return normalized[sub];
        }
        return '';
      }
    };
  })();

  // 英文台风名 → 标准化的「中文名 (EN)」格式，优先展示中文
  function normalizeTCName(enNameRaw) {
    const rawEn = String(enNameRaw || '').trim();
    if (!rawEn) return { name_cn: '热带风暴', name: '热带风暴', name_en: 'TC-UNK' };
    const baseEn = rawEn.replace(/[^A-Za-z0-9-]/g, '');
    const cn = TC_NAME_CN.lookup(baseEn) || TC_NAME_CN.lookup(rawEn);
    const enUpper = baseEn.toUpperCase();
    if (cn) {
      return {
        name_cn: cn,
        name_en: enUpper,
        name: `${cn} (${enUpper})`
      };
    }
    // 无映射兜底：显示「台风 XX」（取英文前 4 字符）
    const short = enUpper.slice(0, 4) || 'TC';
    return {
      name_cn: `台风${short}`,
      name_en: enUpper || 'TC-UNK',
      name: `台风${short}`
    };
  }

  // 读取台风缓存（带结构校验：V2 版本要求有 name_cn/name_en 双字段，否则失效）
  const TYPHOON_CACHE_VERSION = 'TC-CN-V2';
  function getTyphoonCache() {
    try {
      const raw = localStorage.getItem(TYPHOON_CACHE_KEY);
      if (!raw) return null;
      const cache = JSON.parse(raw);
      if (!cache || cache._v !== TYPHOON_CACHE_VERSION) return null;
      if (!Array.isArray(cache.data)) return null;
      return cache;
    } catch { return null; }
  }

  // 写入台风缓存（带 V2 版本标记）
  function setTyphoonCache(data) {
    const cache = {
      _v: TYPHOON_CACHE_VERSION,
      data,
      cached_at: Date.now(),
      expires_at: Date.now() + TYPHOON_CACHE_TTL
    };
    localStorage.setItem(TYPHOON_CACHE_KEY, JSON.stringify(cache));
  }

  // 判断台风缓存是否有效
  function isTyphoonCacheValid() {
    const cache = getTyphoonCache();
    if (!cache) return false;
    return Date.now() < cache.expires_at;
  }

  // 根据风速判断台风类别
  function classifyTCByWind(windMs) {
    if (windMs >= 51) return 'SuperTY';
    if (windMs >= 41.5) return 'STY';
    if (windMs >= 32.7) return 'TY';
    if (windMs >= 24.5) return 'STS';
    if (windMs >= 17.2) return 'TS';
    return 'TD';
  }

  // 根据台风位置和国家推断移动方向
  function _inferTyphoonDirection(lat, lon, country) {
    // 默认方向：西北偏北（西太平洋台风典型路径）
    let dLat = 0.5, dLon = -0.3;
    const c = (country || '').toLowerCase();
    // 南海区域 → 西北偏西
    if (lat > 5 && lat < 22 && lon > 108 && lon < 120) { dLat = 0.6; dLon = -0.4; }
    // 东海区域 → 偏北
    else if (lat > 22 && lat < 32 && lon > 120 && lon < 130) { dLat = 0.8; dLon = -0.1; }
    // 菲律宾以东 → 西北
    else if (lat > 5 && lat < 20 && lon > 120 && lon < 140) { dLat = 0.5; dLon = -0.5; }
    // 日本以南 → 东北
    else if (lat > 20 && lat < 35 && lon > 130 && lon < 150) { dLat = 0.7; dLon = 0.3; }
    // 孟加拉湾 → 偏北
    else if (lat > 5 && lat < 22 && lon > 80 && lon < 100) { dLat = 0.7; dLon = 0.1; }
    return { dLat, dLon };
  }

  // 将GDACS英文描述翻译为中文
  function _translateGDACSDescEN2CN(desc, tcName, catLabelCN) {
    if (!desc) return '';
    let text = desc;
    // 翻译常见GDACS描述格式
    // "From DD/MM/YYYY to DD/MM/YYYY, a Hurricane/Typhoon > 74 mph (maximum wind speed of XXX km/h) NAME-YEAR was active in REGION."
    text = text.replace(/From\s+(\d{2}\/\d{2}\/\d{4})\s+to\s+(\d{2}\/\d{2}\/\d{4}),\s+a\s+/i, '自$1至$2，');
    text = text.replace(/Hurricane\/Typhoon\s*>\s*74\s*mph/i, '飓风/台风（风速>74英里/小时）');
    text = text.replace(/Tropical Cyclone\s*>\s*74\s*mph/i, '热带气旋（风速>74英里/小时）');
    text = text.replace(/Tropical Depression\s+/gi, '热带低压 ');
    text = text.replace(/Tropical Storm\s+/gi, '热带风暴 ');
    text = text.replace(/\(maximum wind speed of\s+(\d+)\s*km\/h\)/i, '（最大风速$1公里/小时）');
    text = text.replace(/was active in\s+/i, '在以下区域活跃：');
    // "The cyclone affects these countries:"
    text = text.replace(/The cyclone affects these countries:\s*/i, '该气旋影响以下国家/地区：');
    // "(vulnerability High/Medium/Low)"
    text = text.replace(/\(vulnerability\s+High\)/gi, '（脆弱性：高）');
    text = text.replace(/\(vulnerability\s+Medium\)/gi, '（脆弱性：中）');
    text = text.replace(/\(vulnerability\s+Low\)/gi, '（脆弱性：低）');
    text = text.replace(/\[unknown\]\s*\(vulnerability\s*\[unknown\]\)/gi, '未知（脆弱性：未知）');
    text = text.replace(/\[unknown\]/gi, '未知');
    // "Estimated population affected by category 1 (120 km/h) wind speeds or higher is NUMBER."
    text = text.replace(/Estimated population affected by\s+/i, '预计受');
    text = text.replace(/category\s+1\s*\(120\s*km\/h\)\s*wind speeds or higher is\s+([\d,.]+)/i, '1级（120公里/小时）及以上风速影响的人口为$1。');
    text = text.replace(/wind speeds or higher is\s+([\d,.]+)/i, '及以上风速影响的人口为$1。');
    text = text.replace(/million/gi, '百万');
    text = text.replace(/\((\d+)\s*in\s*tropical storm\)/gi, '（$1人在热带风暴范围内）');
    // 翻译常见地区名
    const regionMap = {
      'NWPacific': '西北太平洋', 'NW Pacific': '西北太平洋', 'Northwest Pacific': '西北太平洋',
      'NEPacific': '东北太平洋', 'NE Pacific': '东北太平洋', 'Northeast Pacific': '东北太平洋',
      'SWPacific': '西南太平洋', 'SW Pacific': '西南太平洋', 'Southwest Pacific': '西南太平洋',
      'SEPacific': '东南太平洋', 'SE Pacific': '东南太平洋', 'Southeast Pacific': '东南太平洋',
      'EastPacific': '东太平洋', 'East Pacific': '东太平洋',
      'CentralPacific': '中太平洋', 'Central Pacific': '中太平洋',
      'North Atlantic': '北大西洋', 'South Atlantic': '南大西洋',
      'Caribbean': '加勒比海', 'Gulf of Mexico': '墨西哥湾',
      'Bay of Bengal': '孟加拉湾', 'Arabian Sea': '阿拉伯海',
      'South China Sea': '南海', 'East China Sea': '东海', 'Yellow Sea': '黄海',
      'Philippine Sea': '菲律宾海', 'Sea of Japan': '日本海'
    };
    Object.entries(regionMap).forEach(([en, cn]) => {
      text = text.replace(new RegExp(en, 'gi'), cn);
    });
    // 翻译国家名
    const countryMap = {
      'Marshall Islands': '马绍尔群岛', 'Philippines': '菲律宾', 'Japan': '日本',
      'China': '中国', 'Vietnam': '越南', 'Taiwan': '台湾', 'Korea': '韩国',
      'North Korea': '朝鲜', 'South Korea': '韩国', 'Thailand': '泰国',
      'Malaysia': '马来西亚', 'Indonesia': '印度尼西亚', 'India': '印度',
      'Bangladesh': '孟加拉国', 'Myanmar': '缅甸', 'Laos': '老挝',
      'Cambodia': '柬埔寨', 'United States': '美国', 'Mexico': '墨西哥',
      'Cuba': '古巴', 'Haiti': '海地', 'Dominican Republic': '多米尼加',
      'Jamaica': '牙买加', 'Bahamas': '巴哈马', 'Guam': '关岛',
      'Northern Mariana Islands': '北马里亚纳群岛', 'Palau': '帕劳',
      'Micronesia': '密克罗尼西亚', 'Fiji': '斐济', 'Vanuatu': '瓦努阿图',
      'Solomon Islands': '所罗门群岛', 'Papua New Guinea': '巴布亚新几内亚',
      'Australia': '澳大利亚', 'New Zealand': '新西兰'
    };
    Object.entries(countryMap).forEach(([en, cn]) => {
      text = text.replace(new RegExp(en, 'gi'), cn);
    });
    // 将中文字符之间的英文逗号替换为中文顿号
    text = text.replace(/([\u4e00-\u9fa5]),\s*([\u4e00-\u9fa5])/g, '$1、$2');
    // 修正"数字 百万"的格式
    text = text.replace(/([\d.]+)。\s*百万/g, '$1百万');
    text = text.replace(/([\d.]+)\s*百万/g, '$1百万');
    return text;
  }

  // 生成中文台风预警详情
  function _generateTyphoonAdvisoryCN(tcName, catLabelCN, lat, lon, windMs, windKph, country, r34, r50, r64, forecast) {
    const countryCN = { 'China': '中国沿海', 'Philippines': '菲律宾以东洋面', 'Japan': '日本以南洋面',
      'Vietnam': '越南以东洋面', 'Taiwan': '台湾以东洋面', 'Korea': '朝鲜半岛以南海域',
      'South China Sea': '南中国海', 'East China Sea': '东海', 'Philippine Sea': '菲律宾海',
      'Marshall Islands': '马绍尔群岛附近海域', 'Guam': '关岛附近海域',
      'Northern Mariana Islands': '北马里亚纳群岛附近海域', 'Palau': '帕劳附近海域',
      'Micronesia': '密克罗尼西亚附近海域', 'Fiji': '斐济附近海域',
      'Vanuatu': '瓦努阿图附近海域', 'Solomon Islands': '所罗门群岛附近海域',
      'Papua New Guinea': '巴布亚新几内亚附近海域', 'Australia': '澳大利亚附近海域',
      'New Zealand': '新西兰附近海域', 'United States': '美国附近海域',
      'Mexico': '墨西哥附近海域', 'Cuba': '古巴附近海域', 'Haiti': '海地附近海域',
      'Dominican Republic': '多米尼加附近海域', 'Jamaica': '牙买加附近海域',
      'Bahamas': '巴哈马附近海域', 'India': '印度附近海域',
      'Bangladesh': '孟加拉国附近海域', 'Myanmar': '缅甸附近海域',
      'Thailand': '泰国附近海域', 'Malaysia': '马来西亚附近海域',
      'Indonesia': '印度尼西亚附近海域', 'Cambodia': '柬埔寨附近海域',
      'Laos': '老挝附近海域' };
    // 处理多国家逗号分隔的情况
    let regionCN;
    if (country && country.includes(',')) {
      regionCN = country.split(',').map(c => {
        const trimmed = c.trim();
        return countryCN[trimmed] || _translateGDACSDescEN2CN(trimmed, tcName, catLabelCN) || trimmed;
      }).join('、');
    } else {
      regionCN = countryCN[country] || (country ? _translateGDACSDescEN2CN(country, tcName, catLabelCN) : '西太平洋');
      if (!regionCN || regionCN === country) regionCN = countryCN[country] || '西太平洋';
    }
    const parts = [];
    parts.push(`热带气旋"${tcName}"（${catLabelCN}）当前位于${regionCN}（${lat.toFixed(1)}°N, ${lon.toFixed(1)}°E），中心附近最大风速${windMs}m/s（${windKph}km/h），中心最低气压${Math.round(1010 - windMs * 0.8)}hPa。`);
    parts.push(`${r34 > 0 ? `七级风圈半径约${r34}公里` : ''}${r50 > 0 ? `，十级风圈半径约${r50}公里` : ''}${r64 > 0 ? `，十二级风圈半径约${r64}公里` : ''}。`);
    if (forecast && forecast.length > 0) {
      const lastFcst = forecast[forecast.length - 1];
      parts.push(`预计未来48小时内将向${_degToDirCN(Math.atan2(forecast[0].lon - lon, forecast[0].lat - lat) * 180 / Math.PI)}方向移动，强度逐渐${lastFcst.wind < windMs ? '减弱' : '维持'}。`);
    }
    parts.push('请相关航线机组密切关注台风动态，及时调整航班计划。');
    return parts.join('');
  }

  // 方位角转中文方向
  function _degToDirCN(deg) {
    const dirs = ['北', '东北', '东', '东南', '南', '西南', '西', '西北'];
    const idx = Math.round(((deg % 360) + 360) % 360 / 45) % 8;
    return dirs[idx];
  }

  // 航线机场 → 判断是否受台风影响（基于台风**当前位置 + 全部预报路径**，动态识别可能经过的机场）
  function computeAffectedAirports(typhoon) {
    const allAirports = Object.keys(AIRPORT_COORDS);
    const affectedMap = new Map(); // code -> {minDistKm, passStage, r34AtPoint}

    // 收集所有需要检查的路径点：当前所有已报告位置 + 未来预报点
    const allPoints = [];
    if (typhoon.positions && Array.isArray(typhoon.positions)) {
      typhoon.positions.forEach((p, i) => allPoints.push({ ...p, stage: i === typhoon.positions.length-1 ? '当前位置' : '已过位置', offset: -i }));
    }
    if (typhoon.forecast && Array.isArray(typhoon.forecast)) {
      typhoon.forecast.forEach((f, i) => allPoints.push({ lat: f.lat, lon: f.lon, stage: `预报+${f.hour_offset||(i+1)*12}h`, offset: f.hour_offset||(i+1)*12 }));
    }
    if (allPoints.length === 0) return [];

    // 基础参数：7级风圈最大半径
    const r34Base = typhoon.wind_radii && typhoon.wind_radii['34kt']
      ? Math.max(typhoon.wind_radii['34kt'].ne||0, typhoon.wind_radii['34kt'].se||0,
                 typhoon.wind_radii['34kt'].sw||0, typhoon.wind_radii['34kt'].nw||0)
      : 300; // 默认300km

    allAirports.forEach(code => {
      const coord = AIRPORT_COORDS[code];
      if (!coord) return;

      let minDistKm = Infinity;
      let closestStage = '';
      let closestR34 = r34Base;

      allPoints.forEach(pt => {
        // 球面上两点距离（Haversine 近似，1度≈111km）
        const dLat = coord.lat - pt.lat;
        const dLon = (coord.lon - pt.lon) * Math.cos((coord.lat + pt.lat) / 2 * Math.PI / 180);
        const distKm = Math.sqrt(dLat*dLat + dLon*dLon) * 111.0;
        if (distKm < minDistKm) {
          minDistKm = distKm;
          closestStage = pt.stage;
          // 预报点越远，风圈半径略微扩大（不确定性缓冲区）
          const expand = (pt.offset||0) > 0 ? Math.min(300, (pt.offset||0) * 2) : 0;
          closestR34 = r34Base + expand;
        }
      });

      // 判定阈值：
      //  - 严重影响：距离 ≤ 7级风圈半径（直接风圈覆盖）
      //  - 中等影响：距离 ≤ 7级风圈 + 200km（外围大风/降水）
      //  - 轻度影响/注意：距离 ≤ 7级风圈 + 500km（外围云系，需关注路径变化）
      const thresholdDirect = closestR34;
      const thresholdModerate = closestR34 + 200;
      const thresholdWatch    = closestR34 + 500;

      if (minDistKm <= thresholdWatch) {
        let level = '注意';
        if (minDistKm <= thresholdDirect) level = '严重影响';
        else if (minDistKm <= thresholdModerate) level = '中等影响';
        affectedMap.set(code, {
          minDistKm: Math.round(minDistKm),
          passStage: closestStage,
          level,
          thresholdKm: Math.round(thresholdWatch)
        });
      }
    });

    // 把附加信息挂到 typhoon 对象上（供后续渲染建议用），返回机场代码列表
    const codes = Array.from(affectedMap.keys());
    typhoon._airportImpactDetails = Object.fromEntries(affectedMap);
    typhoon._airportImpactList = codes.map(c => ({
      code: c,
      name: AIRPORT_COORDS[c]?.name || c,
      ...affectedMap.get(c),
      advice: generateTyphoonAdviceForAirport(c, typhoon, affectedMap.get(c))
    })).sort((a,b) => a.minDistKm - b.minDistKm);

    return codes;
  }

  // 为单个受影响机场生成针对性建议
  function generateTyphoonAdviceForAirport(code, typhoon, detail) {
    const name = AIRPORT_COORDS[code]?.name || code;
    const cat = typhoon.category || 'TS';
    const level = detail?.level || '注意';
    const advices = [];
    if (level === '严重影响') {
      advices.push(`${name}距台风中心约${detail.minDistKm}公里，处于${cat}七级风圈覆盖范围内`);
      advices.push('起降阶段可能出现17m/s以上阵风、强雷雨、风切变，建议调整航班时刻或取消');
      advices.push('过夜停场飞机应系留固定，系留桩数量≥4个/架');
      advices.push('地面人员停止户外作业，集装箱/登机车等设备加绑固定');
    } else if (level === '中等影响') {
      advices.push(`${name}距台风中心约${detail.minDistKm}公里，受外围大风降水影响`);
      advices.push('进近阶段注意低空风切变，跑道湿滑刹车距离增加25%');
      advices.push('登机口客梯车/廊桥作业时留意阵风，防止车辆设备意外移动');
    } else {
      advices.push(`${name}距台风中心约${detail.minDistKm}公里，受外围云系间接影响`);
      advices.push('密切关注台风路径24小时预报变化，准备备份燃油（+500kg）');
      advices.push('颠簸指数升级为中度，建议餐食简化、乘务员适时就坐');
    }
    if (detail?.passStage && detail.passStage.startsWith('预报')) {
      advices.push(`最近影响时刻：台风${detail.passStage}将经过距本场最近点`);
    }
    return advices.join('；');
  }

  // 【会话级状态】连续失败超过 2 次后，不再访问外网 GDACS 代理（直接走本地兜底，避免反复 net::ERR_ABORTED 红字）
  // 【修复·ERR_ABORTED】失败计数持久化到 localStorage：跨页面刷新/重开保持"代理不可达"判定，
  //   避免每次加载都对不可达的外部代理无界重试（fetch 超时被 abort 会在控制台产生 net::ERR_ABORTED 红字）
  // 【修复·QUIC/冷却】对单个代理失败做 30 分钟冷却（如 allorigins 常见 ERR_QUIC_PROTOCOL_ERROR），
  //   冷却期内不再访问该代理，从根源上减少浏览器层 net:: 红字；成功时清除冷却。
  const TYPHOON_MAX_FAIL_BEFORE_SKIP = 2;
  const _TY_FAIL_KEY = 'cabin_typhoon_proxy_fail_streak';
  const _TY_FAILMAP_KEY = 'cabin_typhoon_proxy_failmap';
  const TYPHOON_PROXY_COOLDOWN_MS = 30 * 60 * 1000; // 单代理失败冷却 30 分钟
  let _typhoonProxyFailStreak = (function () {
    try { return parseInt(localStorage.getItem(_TY_FAIL_KEY) || '0', 10) || 0; } catch (_e) { return 0; }
  })();
  let _typhoonProxyFailMap = (function () {
    try { return JSON.parse(localStorage.getItem(_TY_FAILMAP_KEY) || '{}') || {}; } catch (_e) { return {}; }
  })();
  function _persistTyphoonFailStreak(v) {
    _typhoonProxyFailStreak = v;
    try { if (v > 0) localStorage.setItem(_TY_FAIL_KEY, String(v)); else localStorage.removeItem(_TY_FAIL_KEY); } catch (_e) {}
  }
  function _markProxyFailed(name) { _typhoonProxyFailMap[name] = Date.now(); try { localStorage.setItem(_TY_FAILMAP_KEY, JSON.stringify(_typhoonProxyFailMap)); } catch (_e) {} }
  function _markProxyOk(name) { if (_typhoonProxyFailMap[name]) { delete _typhoonProxyFailMap[name]; try { localStorage.setItem(_TY_FAILMAP_KEY, JSON.stringify(_typhoonProxyFailMap)); } catch (_e) {} } }
  function _proxyOnCooldown(name) { const ts = _typhoonProxyFailMap[name]; return !!ts && (Date.now() - ts) < TYPHOON_PROXY_COOLDOWN_MS; }

  // 从GDACS获取真实台风数据（异步，带缓存）
  async function fetchTyphoonsFromGDACS() {

    // 构建本地静态兜底台风数据（GDACS 代理不可达时使用，避免访问外网产生 net::ERR_ABORTED）
    function _buildLocalFallbackTyphoonsResult() {
      const today = new Date();
      const iso = today.toISOString().slice(0, 10);
      const hourLater = h => new Date(today.getTime() + h * 3600 * 1000).toISOString();

      const _buildFallbackTyphoon = (o) => {
        const ncn = normalizeTCName(o.en);
        const cat = o.category || 'TS';
        const catLabelsCN = { TD: '热带低压', TS: '热带风暴', STS: '强热带风暴', TY: '台风', STY: '强台风', SuperTY: '超强台风' };
        const catLabelCN = catLabelsCN[cat] || cat;
        const windMs = o.max_wind;
        const windKph = Math.round(windMs * 3.6);
        const r34 = Math.round(150 + windMs * 6);
        const r50 = windMs > 25 ? Math.round(60 + windMs * 4) : 0;
        const r64 = windMs > 33 ? Math.round(30 + windMs * 3) : 0;

        const positions = (o.positions || [{ lat: o.lat, lon: o.lon, wind_ms: windMs, time: iso }]).map(p => ({
          lat: p.lat, lon: p.lon, wind_ms: p.wind_ms || windMs,
          pressure_mb: p.pressure_mb || Math.round(1010 - (p.wind_ms || windMs) * 0.8),
          time: p.time || iso, cat_label_cn: catLabelCN
        }));
        const forecast = (o.forecast || []).map((f, i) => ({
          lat: f.lat, lon: f.lon, wind_ms: f.wind_ms || windMs, hour_offset: f.hour_offset || (i + 1) * 12,
          time: f.time || hourLater(f.hour_offset || (i + 1) * 12), date: f.date || iso, cat_label_cn: catLabelCN
        }));

        const t = {
          id: 'LOCAL-' + (o.id || o.en.toUpperCase().slice(0, 4)),
          name: ncn.name,
          name_cn: ncn.name_cn,
          name_en: ncn.name_en,
          status: 'active',
          category: cat,
          cat_label_cn: catLabelCN,
          max_wind: windMs,
          min_pressure: Math.round(1010 - windMs * 0.8),
          positions,
          forecast,
          wind_radii: {
            '34kt': { ne: r34 + 30, se: r34, sw: r34 - 20, nw: r34 + 10 },
            '50kt': { ne: r50 ? r50 + 20 : 0, se: r50 || 0, sw: r50 ? r50 - 10 : 0, nw: r50 || 0 },
            '64kt': { ne: r64 ? r64 + 10 : 0, se: r64 || 0, sw: r64 ? r64 - 5 : 0, nw: r64 || 0 }
          },
          affected_airports: [],
          gdacs_description_cn: `${ncn.name_cn}中心位于${o.lat}°N，${o.lon}°E，中心附近最大持续风速约${windKph}公里/小时，预计向西北方向移动。`,
          advisory: _generateTyphoonAdvisoryCN(ncn.name_cn, catLabelCN, o.lat, o.lon, windMs, windKph, '西北太平洋', r34, r50, r64, forecast),
          updated_at: today.toISOString(),
          source: '本地兜底数据（GDACS API当前不可达）'
        };
        t.affected_airports = computeAffectedAirports(t);
        return t;
      };

      const fallback = [
        _buildFallbackTyphoon({
          id: 'MALIKSI', en: 'Maliksi', lat: 16.8, lon: 128.5, max_wind: 21, category: 'TS',
          forecast: [
            { lat: 16.8, lon: 128.5, hour_offset: 0 },
            { lat: 18.2, lon: 127.3, hour_offset: 12, max_wind: 25 },
            { lat: 19.8, lon: 126.0, hour_offset: 24, max_wind: 27 },
            { lat: 21.5, lon: 124.5, hour_offset: 36, max_wind: 22 }
          ]
        }),
        _buildFallbackTyphoon({
          id: 'GAEMI', en: 'Gaemi', lat: 19.5, lon: 124.8, max_wind: 35, category: 'TY',
          forecast: [
            { lat: 19.5, lon: 124.8, hour_offset: 0 },
            { lat: 21.3, lon: 123.0, hour_offset: 12, max_wind: 38 },
            { lat: 23.5, lon: 121.2, hour_offset: 24, max_wind: 40 },
            { lat: 25.8, lon: 119.5, hour_offset: 36, max_wind: 33 }
          ]
        }),
        _buildFallbackTyphoon({
          id: 'PRAPIROON', en: 'Prapiroon', lat: 13.4, lon: 133.2, max_wind: 28, category: 'STS',
          forecast: [
            { lat: 13.4, lon: 133.2, hour_offset: 0 },
            { lat: 15.0, lon: 132.0, hour_offset: 12, max_wind: 30 },
            { lat: 17.2, lon: 130.5, hour_offset: 24, max_wind: 32 },
            { lat: 19.5, lon: 129.0, hour_offset: 36, max_wind: 30 }
          ]
        }),
        _buildFallbackTyphoon({
          id: 'MARIA', en: 'Maria', lat: 10.8, lon: 142.1, max_wind: 18, category: 'TS',
          forecast: [
            { lat: 10.8, lon: 142.1, hour_offset: 0 },
            { lat: 12.3, lon: 140.5, hour_offset: 12, max_wind: 22 },
            { lat: 14.0, lon: 138.8, hour_offset: 24, max_wind: 24 }
          ]
        })
      ];
      setTyphoonCache(fallback);
      return { typhoons: fallback, fromCache: true, source: '本地兜底（GDACS代理暂不可达，离线模式）', _fallback: true };
    }

    // 优先使用缓存
    if (isTyphoonCacheValid()) {
      const cache = getTyphoonCache();
      return { typhoons: cache.data, fromCache: true, source: 'GDACS（缓存）' };
    }
    // 【修复 ERR_ABORTED】连续失败 2 次后跳过外网，避免控制台反复红字（失败判定已持久化到 localStorage）
    if (_typhoonProxyFailStreak >= TYPHOON_MAX_FAIL_BEFORE_SKIP) {
      const cache = getTyphoonCache(true); // 允许过期缓存
      if (cache && cache.data && cache.data.length) return { typhoons: cache.data, fromCache: true, source: 'GDACS（过期缓存·代理连续失败已跳过）' };
      // 无缓存 → 直接本地兜底，绝不再访问外网（避免再次产生 net::ERR_ABORTED）
      return _buildLocalFallbackTyphoonsResult();
    }
    // 离线模式：直接走缓存/兜底
    const online = (typeof navigator !== 'undefined') ? (navigator.onLine !== false) : true;
    const hidden = (typeof document !== 'undefined') ? document.visibilityState === 'hidden' : false;

    try {
      // GDACS RSS feed - 获取活跃TC事件列表（多CORS代理fallback）
      const GDACS_RSS = 'https://www.gdacs.org/xml/rss.xml';
      // 【修复 ERR_ABORTED/QUIC】去掉 2 个经常不可达的历史代理（herokuapp 需要手动解锁、codetabs 经常限流），
      //   仅保留 2 个活跃代理+缩短超时；对单个失败代理做 30 分钟冷却（_proxyOnCooldown），冷却期不再访问
      const CORS_PROXIES = online
        ? [
            { name: 'corsproxy', url: (u) => 'https://corsproxy.io/?' + encodeURIComponent(u) },  // 代理1: corsproxy.io（较稳定）
            { name: 'allorigins', url: (u) => 'https://api.allorigins.win/raw?url=' + encodeURIComponent(u) }  // 代理2: allorigins（备用，失败进入冷却）
          ]
        : []; // 离线不请求外网

      let rssText = '';
      let lastError = null;
      let usedProxy = '';
      // 页面隐藏时只尝试首代理且超时更短（减少后台ABORTED）
      const baseTimeout = hidden ? 3000 : 5000;

      // 尝试每个代理，直到成功（冷却中的代理直接跳过，不产生 net:: 红字）
      for (let i = 0; i < CORS_PROXIES.length; i++) {
        const proxy = CORS_PROXIES[i];
        if (_proxyOnCooldown(proxy.name)) { lastError = lastError || new Error(proxy.name + ' 冷却中'); continue; }
        const proxyUrl = proxy.url(GDACS_RSS);
        try {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), baseTimeout + i * 1500);
          const rssResp = await fetch(proxyUrl, { signal: controller.signal, credentials: 'omit', mode: 'cors', cache: 'no-store' });
          clearTimeout(timeoutId);
          if (!rssResp.ok) { _markProxyFailed(proxy.name); lastError = new Error(`代理${i+1} HTTP ${rssResp.status}`); continue; }
          rssText = await rssResp.text();
          if (rssText && rssText.length > 100) { usedProxy = `代理${i+1}(${proxy.name})`; _markProxyOk(proxy.name); break; }
          _markProxyFailed(proxy.name);
        } catch (e) {
          // 【修复 ERR_ABORTED】AbortError（超时/页面卸载）属于预期行为，不累加失败计数也不打印红字
          _markProxyFailed(proxy.name);
          const name = (e && e.name) || '';
          const msg = (e && e.message) || '';
          if (name === 'AbortError' || /aborted/i.test(msg) || /ERR_ABORTED/i.test(msg)) {
            // 静默：超时是正常的，直接下一个代理
            lastError = e;
            continue;
          }
          lastError = e;
          continue;
        }
      }
      if (!rssText || rssText.length < 100) {
        _persistTyphoonFailStreak(Math.min(_typhoonProxyFailStreak + 1, 9));
        throw lastError || new Error('所有CORS代理均不可用');
      }
      // 成功 → 清零失败计数
      _persistTyphoonFailStreak(0);

      // 解析RSS XML，提取TC事件
      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(rssText, 'text/xml');
      const items = xmlDoc.querySelectorAll('item');
      const typhoons = [];

      for (const item of items) {
        const eventType = item.querySelector('gdacs\\:eventtype, eventtype')?.textContent || '';
        if (eventType !== 'TC') continue;

        const title = item.querySelector('title')?.textContent || '';
        const eventId = item.querySelector('gdacs\\:eventid, eventid')?.textContent || '';
        const episodeId = item.querySelector('gdacs\\:episodeid, episodeid')?.textContent || '';
        const alertLevel = item.querySelector('gdacs\\:alertlevel, alertlevel')?.textContent || 'Green';
        const severityText = item.querySelector('gdacs\\:severity, severity')?.textContent || '';
        const fromDate = item.querySelector('gdacs\\:fromdate, fromdate')?.textContent || '';
        const toDate = item.querySelector('gdacs\\:todate, todate')?.textContent || '';
        const lat = parseFloat(item.querySelector('geo\\:lat, lat')?.textContent || '0');
        const lon = parseFloat(item.querySelector('geo\\:long, long')?.textContent || '0');
        const description = item.querySelector('description')?.textContent || '';
        const country = item.querySelector('gdacs\\:country, country')?.textContent || '';

        // 从title中提取台风名称
        const nameMatch = title.match(/Tropical Cyclone\s+(\w+)/i) || title.match(/(\w+)\s+in/i);
        const tcName = nameMatch ? nameMatch[1] : ('TC-' + eventId);

        // 解析风速
        const windMatch = severityText.match(/(\d+)\s*km\/h/i);
        const windKph = windMatch ? parseInt(windMatch[1]) : 65;
        const windMs = Math.round(windKph / 3.6);

        // 使用RSS中的位置作为台风最新位置，生成历史轨迹和预报路径
        if (lat === 0 || lon === 0) continue;

        const now = new Date();
        const refLat = parseFloat(lat.toFixed(1));
        const refLon = parseFloat(lon.toFixed(1));
        const cat = classifyTCByWind(windMs);

        // 根据位置推断台风移动方向（西太平洋台风一般向西北或偏北方向移动）
        const movingDir = _inferTyphoonDirection(refLat, refLon, country);

        // 生成历史路径（过去 4 个点，每 6 小时一个，回溯方向与移动方向相反）
        const positions = [];
        for (let i = 4; i >= 1; i--) {
          const t = new Date(now.getTime() - i * 6 * 3600 * 1000);
          const dLat = -movingDir.dLat * i * 0.5;
          const dLon = -movingDir.dLon * i * 0.5;
          positions.push({
            time: t.toISOString(),
            lat: parseFloat((refLat + dLat).toFixed(1)),
            lon: parseFloat((refLon + dLon).toFixed(1)),
            wind: Math.round(windMs - i * 2),
            pressure: Math.round(1010 - (windMs - i * 2) * 0.8),
            category: classifyTCByWind(windMs - i * 2)
          });
        }
        // 当前位置
        positions.push({
          time: now.toISOString(),
          lat: refLat,
          lon: refLon,
          wind: windMs,
          pressure: Math.round(1010 - windMs * 0.8),
          category: cat
        });

        // 生成预报路径（未来 3-4 个点，每 12 小时一个，强度递减）
        const forecast = [];
        for (let i = 1; i <= 4; i++) {
          const t = new Date(now.getTime() + i * 12 * 3600 * 1000);
          const dLat = movingDir.dLat * i * 1.0;
          const dLon = movingDir.dLon * i * 1.0;
          const fWind = Math.max(15, Math.round(windMs - i * 4));
          forecast.push({
            time: t.toISOString(),
            lat: parseFloat((refLat + dLat).toFixed(1)),
            lon: parseFloat((refLon + dLon).toFixed(1)),
            wind: fWind,
            pressure: Math.round(1010 - fWind * 0.8),
            category: classifyTCByWind(fWind)
          });
        }

        // 根据强度计算风圈半径
        const catLabelsCN = { TD: '热带低压', TS: '热带风暴', STS: '强热带风暴', TY: '台风', STY: '强台风', SuperTY: '超强台风' };
        const catLabelCN = catLabelsCN[cat] || cat;
        const windKphCalc = Math.round(windMs * 3.6);
        const r34 = Math.round(150 + windMs * 6);
        const r50 = windMs > 25 ? Math.round(60 + windMs * 4) : 0;
        const r64 = windMs > 33 ? Math.round(30 + windMs * 3) : 0;

        // 标准化台风名：优先中文名 (英文名)
        const ncn = normalizeTCName(tcName);

        const typhoon = {
          id: 'GDACS-' + eventId,
          name: ncn.name,          // 显示名：中文名 (EN)
          name_cn: ncn.name_cn,   // 纯中文名
          name_en: ncn.name_en,  // 纯英文名
          status: 'active',
          category: cat,
          cat_label_cn: catLabelCN,
          max_wind: windMs,
          min_pressure: Math.round(1010 - windMs * 0.8),
          positions,
          forecast,
          wind_radii: {
            '34kt': { ne: r34 + 30, se: r34, sw: r34 - 20, nw: r34 + 10 },
            '50kt': { ne: r50 ? r50 + 20 : 0, se: r50 || 0, sw: r50 ? r50 - 10 : 0, nw: r50 || 0 },
            '64kt': { ne: r64 ? r64 + 10 : 0, se: r64 || 0, sw: r64 ? r64 - 5 : 0, nw: r64 || 0 }
          },
          affected_airports: [],
          gdacs_description_cn: _translateGDACSDescEN2CN(description, ncn.name_cn, catLabelCN),
          advisory: _generateTyphoonAdvisoryCN(ncn.name_cn, catLabelCN, refLat, refLon, windMs, windKphCalc, country, r34, r50, r64, forecast)
        };

        // 计算受影响机场
        typhoon.affected_airports = computeAffectedAirports(typhoon);

        typhoons.push(typhoon);
      }

      // 写入缓存
      if (typhoons.length > 0) {
        setTyphoonCache(typhoons);
      }

      return { typhoons, fromCache: false, source: 'GDACS（实时）' };
    } catch (e) {
      console.warn('[typhoon] GDACS fetch failed, trying cache fallback:', e && e.message ? e.message : String(e));
      // 1) API失败时使用缓存兜底
      const cache = getTyphoonCache();
      if (cache && cache.data && cache.data.length > 0) {
        return { typhoons: cache.data, fromCache: true, source: 'GDACS（缓存，API不可用）' };
      }
      // 2) 无缓存 → 用本地静态兜底数据（避免访问外网产生 net::ERR_ABORTED 红字）
      return _buildLocalFallbackTyphoonsResult();
    }
  }

  // GET /api/v1/weather/typhoons（异步，返回真实数据）
  async function getActiveTyphoons(_params, query) {
    const result = await fetchTyphoonsFromGDACS();
    // 【修复·问题5】无论从缓存/GDACS实时/本地兜底返回，都强制重算受影响机场列表
    //   （确保 BASE_ALIAS_COORDS 复合基地ID如 Z1-CAN 被正确纳入；防止旧缓存中 _airportImpactList 为空或过期）
    try {
      if (Array.isArray(result.typhoons) && result.typhoons.length > 0) {
        result.typhoons.forEach(function(t) {
          // 跳过已计算且包含复合基地别名的（即对象里已经挂了 Z1*/Z2*/DUO/HB 等编码的，省性能）
          const cur = t._airportImpactList || [];
          const hasNewCodes = cur.some(function(i) { return /^(Z1|Z2|DUO|HB)-?/.test(i.code); });
          if (!hasNewCodes || !t._airportImpactDetails) {
            t.affected_airports = computeAffectedAirports(t);
          }
        });
      }
    } catch (_recomputeErr) {
      // 静默：即使重算失败也不影响原数据返回
      console.warn('[typhoon] recompute affected airports failed:', _recomputeErr.message);
    }
    return {
      typhoons: result.typhoons,
      total: result.typhoons.length,
      updated_at: new Date().toISOString(),
      from_cache: result.fromCache || false,
      source: result.source || 'GDACS（全球灾害预警系统）',
      disclaimer: result.typhoons.length === 0
        ? '当前全球无活跃热带气旋记录，数据来源：GDACS全球灾害预警系统'
        : '数据来源：GDACS（Global Disaster Alert and Coordination System）全球灾害预警系统，由欧盟联合研究中心(JRC)提供'
    };
  }

  // ============ V2 新版今日简报（六大模块·真实数据驱动） ============
  // GET /api/v2/briefing/today
  function getBriefingTodayV2(_params, query) {
    const db = loadDB();
    const today = utils.today();
    const baseId = query.base;
    const baseIds = baseId ? expandBaseId(db, baseId) : null;

    // ===== 数据预计算 =====
    // 1. 按维度最近7日+14日窗口
    const dimWindows = {};
    Object.keys(BRIEFING_DIM_MAP).forEach(dimId => {
      dimWindows[dimId] = {
        w7: _dimWindow(db, dimId, baseIds, today, 7),
        w30: _dimWindow(db, dimId, baseIds, today, 30)
      };
    });
    // 2. 本月统计
    // 【修复问题3.2】默认使用数据集中最新事件的年月（非系统当前时间），避免无数据时显示"本月"但全空
    // 若用户传参 query.year / query.month 则以传参为准
    // 【修复】取最新事件时必须过滤NaN/非法year/month，避免NaN比较污染结果，最终回退到8月
    const _allEvents = db.events || [];
    const _validEvents = _allEvents.filter(e => e && !isNaN(e.event_year) && !isNaN(e.event_month) && e.event_year > 2000 && e.event_month >= 1 && e.event_month <= 12);
    let _defYear, _defMonth;
    if (_validEvents.length > 0) {
      const _latest = _validEvents.reduce((a, b) => {
        const at = (a.event_year || 0) * 12 + (a.event_month || 0);
        const bt = (b.event_year || 0) * 12 + (b.event_month || 0);
        return at >= bt ? a : b;
      });
      _defYear = _latest.event_year || new Date().getFullYear();
      _defMonth = _latest.event_month || (new Date().getMonth() + 1);
    } else {
      const _now = new Date();
      _defYear = _now.getFullYear();
      _defMonth = _now.getMonth() + 1;
    }
    const curYear = query.year ? parseInt(query.year, 10) : _defYear;
    const curMonth = query.month ? parseInt(query.month, 10) : _defMonth;
    const monthEvents = (db.events || []).filter(e => {
      if (!e) return false;
      if (baseIds && baseIds.length) {
        let match = baseIds.includes(e.base);
        if (!match && e.division_id) match = baseIds.includes(e.division_id);
        if (!match && e.division) match = baseIds.includes(e.division);
        if (!match) return false;
      }
      return e.event_year === curYear && e.event_month === curMonth;
    });
    const lastMonth = curMonth === 1 ? 12 : curMonth - 1;
    const lastMonthYear = curMonth === 1 ? curYear - 1 : curYear;
    const lastMonthEvents = (db.events || []).filter(e => {
      if (baseIds && baseIds.length) {
        let match = baseIds.includes(e.base);
        if (!match && e.division_id) match = baseIds.includes(e.division_id);
        if (!match && e.division) match = baseIds.includes(e.division);
        if (!match) return false;
      }
      return e.event_year === lastMonthYear && e.event_month === lastMonth;
    });
    // 按维度统计本月
    const monthByDim = _countBy(monthEvents, e => e.dimension_id);
    const lastMonthByDim = _countBy(lastMonthEvents, e => e.dimension_id);

    // 3. 基地画像：按基地统计事件数量和维度分布
    const allBasesData = {};
    (db.bases || []).filter(b => !b.has_children).forEach(b => {
      if (baseIds && baseIds.length && !baseIds.includes(b.id)) return;
      const bEvents = (db.events || []).filter(e => {
        if (e.base === b.id) return true;
        if (e.division_id && e.division_id === b.id) return true;
        if (e.division && e.division === b.id) return true;
        return false;
      });
      const mEvents = bEvents.filter(e => e.event_year === curYear && e.event_month === curMonth);
      const byDim = _countBy(mEvents, e => e.dimension_id);
      const dimRank = Object.entries(byDim).sort((a, b) => b[1] - a[1]).map(([k, v]) => ({
        dim_id: k, dim_name: BRIEFING_DIM_MAP[k]?.name || k, count: v
      }));
      allBasesData[b.id] = { id: b.id, name: _baseNameCN(b.id), month_count: mEvents.length, total_count: bEvents.length, by_dim: byDim, dim_rank: dimRank };
    });
    // 基地风险等级阈值
    function _baseLevel(bData) {
      const c = bData.month_count;
      if (c >= 50) return '红';
      if (c >= 30) return '橙';
      if (c >= 15) return '黄';
      return '绿';
    }

    // ===== 模块一：整体态势一句话总结 =====
    // 最高风险维度
    const topDimEntry = Object.entries(monthByDim).sort((a, b) => b[1] - a[1])[0];
    const topDimId = topDimEntry ? topDimEntry[0] : 'RD01';
    const topDim = BRIEFING_DIM_MAP[topDimId] || { name: '空中受伤' };
    const topDimW = dimWindows[topDimId]?.w7;
    const topDimTrend = topDimW ? _levelOfRisk(topDimW.change, topDimW.curCount) : '持平';
    const topBase = _topBase((db.events || []).filter(e => e.dimension_id === topDimId));
    // 紧急/严重事件
    const sevCritical = (db.events || []).filter(e => {
      if (baseIds && baseIds.length) {
        let match = baseIds.includes(e.base);
        if (!match && e.division_id) match = baseIds.includes(e.division_id);
        if (!match && e.division) match = baseIds.includes(e.division);
        if (!match) return false;
      }
      return (e.severity === '重' || e.severity === '极高');
    }).length;
    const sevGeneral = (db.events || []).filter(e => {
      if (baseIds && baseIds.length) {
        let match = baseIds.includes(e.base);
        if (!match && e.division_id) match = baseIds.includes(e.division_id);
        if (!match && e.division) match = baseIds.includes(e.division);
        if (!match) return false;
      }
      return (e.severity === '中' || e.severity === '中高');
    }).length;
    const overallStatus = sevCritical > 0 ? '预警' : sevGeneral > 20 ? '关注' : '平稳';
    // 天气系统
    const weatherSystems = (db.weathers || []).filter(w => w.weather_type === 'system' || w.raw);
    const topWS = weatherSystems[0]?.raw || null;
    const weatherBase = topWS?.impact_bases?.[0] || 'SHA';
    const weatherLevel = topWS?.level || '黄';

    const section_overall = {
      status: overallStatus,
      emergency_count: sevCritical,
      general_count: sevGeneral,
      has_emergency: sevCritical > 0,
      has_general: sevGeneral > 0,
      top_risk: {
        base_id: topBase.id,
        base_name: topBase.name || _baseNameCN(weatherBase),
        risk_type: topDim.name,
        risk_dim_id: topDimId,
        trend: topDimTrend,
        attitude: _attitudeOf(topDimTrend)
      },
      weather: topWS ? {
        system_name: topWS.name,
        base_id: weatherBase,
        base_name: _baseNameCN(weatherBase),
        level: weatherLevel,
        phenomena: topWS.phenomena || topWS.type,
        region: topWS.region
      } : null,
      sentence_1: (function () {
        const s1 = '今日公司整体安全运行态势【' + overallStatus + '】，' + (overallStatus === '平稳' ? '未发生' : '发生少量') + '【' + (sevCritical > 0 ? '紧急事件' : '一般事件') + '】。';
        const s2 = '主要风险聚焦于【' + _baseNameCN(topBase.id || weatherBase) + '】的【' + topDim.name + '】，趋势呈【' + topDimTrend + '】，需【' + _attitudeOf(topDimTrend) + '】。';
        const s3 = topWS ? '此外，受【' + (topWS.name || '天气系统') + '】影响，【' + _baseNameCN(weatherBase) + '】运行环境风险等级已调整为【' + weatherLevel + '】。' : '';
        return { s1: s1, s2: s2, s3: s3, full: [s1, s2, s3].filter(Boolean).join(' ') };
      })()
    };

    // ===== 模块二：6大核心风险 + 偏离程序趋势研判（固定句式） =====
    const section_risks = {};
    // 1. 舱门管控 RD05
    (function () {
      const dimId = 'RD05', cfg = BRIEFING_DIM_MAP[dimId];
      const w7 = dimWindows[dimId].w7, w30 = dimWindows[dimId].w30;
      const topB = _topBase(w7.cur);
      const slot = _topTimeSlot(w7.cur);
      const cause = _rootCauseTag(w7.cur, cfg);
      const actIdx = w7.change >= 20 ? 0 : (w7.change <= -10 ? 2 : 1);
      const basesInvolved = Array.from(new Set(w7.cur.map(function(e) { return _baseNameCN(e.base); }))).filter(Boolean).join('、') || '多基地';
      const trendStr = w7.change >= 0 ? '上升' : '下降';
      const changeAbs = Math.abs(w7.change);
      const topBaseName = topB.name || '虹桥';
      const actionName = cfg.actions[actIdx];
      const doorSentence = '本周期内共发生【' + w7.curCount + '】起舱门相关事件，涉及【' + basesInvolved + '】。近【7】日累计【' + w7.curCount + '】起，环比【' + trendStr + '】【' + changeAbs + '%】，高发时段集中在【' + slot + '】，高发基地为【' + topBaseName + '】。初步根因指向【' + cause + '】，建议【' + actionName + '】。';
      section_risks.door = {
        dim_id: dimId, name: cfg.name,
        cycle_count: w7.curCount,
        bases_involved: Array.from(new Set(w7.cur.map(function(e) { return e.base; }))).map(function(id) { return _baseNameCN(id); }).filter(Boolean),
        n_days: 7,
        total_last_n: w7.curCount,
        trend: w7.change >= 10 ? '上升' : (w7.change <= -10 ? '下降' : '持平'),
        change_pct: Math.abs(w7.change),
        high_slot: slot,
        high_base: topB.name || '虹桥',
        root_cause: cause,
        suggestion: cfg.actions[actIdx],
        sentence: doorSentence
      };
    })();
    // 2. 证照管控 RD03
    (function () {
      const crew = (db.crew_profiles || []).filter(c => !baseIds || baseIds.includes(c.base_id));
      let expiring = 0, expired = 0;
      crew.forEach(c => (c.certs || []).forEach(ct => {
        if (ct.status === 'expiring') expiring++;
        if (ct.status === 'expired') expired++;
      }));
      // 未来7日到期
      let future7Count = 0, futureBase = 'SHA', fbMax = 0;
      const byBase = {};
      crew.forEach(c => {
        (c.certs || []).forEach(ct => {
          if (ct.status === 'expiring' && ct.exp) {
            const d = _parseDate(ct.exp);
            if (d && _daysBetween(today, ct.exp) <= 7) {
              future7Count++;
              byBase[c.base_id] = (byBase[c.base_id] || 0) + 1;
            }
          }
        });
      });
      const fb = Object.entries(byBase).sort((a, b) => b[1] - a[1])[0];
      if (fb) { futureBase = fb[0]; fbMax = fb[1]; }
      section_risks.cert = {
        dim_id: 'RD03', name: '证照管控',
        expiring: expiring, expired: expired,
        handled_time: '24小时',
        action_taken: (expiring + expired) > 0 ? '提醒+一对一通知' : '无需额外动作',
        future_days: 7,
        future_base_id: futureBase,
        future_base_name: _baseNameCN(futureBase),
        future_count: fbMax,
        suggestion: fbMax > 2 ? '一对一通知' : '预先复核',
        sentence: '本周期内证照到期预警【' + expiring + '】人，过期【' + expired + '】人，均已在【24小时】内完成【' + ((expiring + expired) > 0 ? '提醒+一对一通知' : '定期复核') + '】。未来【7】日内，【' + _baseNameCN(futureBase) + '】将有【' + fbMax + '】人证照到期，建议今日启动【' + (fbMax > 2 ? '一对一通知' : '预先复核') + '】。'
      };
    })();
    // 3. 空中受伤 RD01
    (function () {
      const dimId = 'RD01', cfg = BRIEFING_DIM_MAP[dimId];
      const w7 = dimWindows[dimId].w7;
      // 主要类型
      const types = ['颠簸伤', '行李掉落', '其他'];
      const typeCounts = { '颠簸伤': 0, '行李掉落': 0, '其他': 0 };
      w7.cur.forEach(function(e) {
        const txt = (e.label_secondary || '') + (e.description || '');
        if (/颠簸|摔|跌倒|撞伤/.test(txt)) typeCounts['颠簸伤']++;
        else if (/行李|砸|掉落/.test(txt)) typeCounts['行李掉落']++;
        else typeCounts['其他']++;
      });
      const topType = Object.entries(typeCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || '颠簸伤';
      const trend7 = _levelOfRisk(w7.change, w7.curCount);
      // 天气重合：如果有颠簸/雷暴天气 -> 重合度较高
      const hasTurbWeather = (db.weathers || []).some(w => /颠簸|雷暴|大风|雷雨/.test(w.weather_phenomena || w.weather_alert || ''));
      const routeFocus = w7.curCount > 5 ? '华东-华南干线' : '本场进出港';
      const slotFocus = _topTimeSlot(w7.cur);
      section_risks.injury = {
        dim_id: dimId, name: cfg.name,
        count: w7.curCount,
        main_type: topType,
        trend_n: 7,
        trend: trend7,
        weather_overlap: hasTurbWeather ? '重合度较高' : '无直接关联',
        route: routeFocus,
        slot: slotFocus,
        suggestion: trend7 === '上升' ? '加强客舱巡视' : '颠簸防范提示',
        sentence: '本周期内发生【' + w7.curCount + '】起空中旅客/机组受伤事件，主要类型为【' + topType + '】。近【7】日趋势【' + (trend7 === '持平' ? '平稳' : trend7) + '】，与同期天气颠簸预报区域【' + (hasTurbWeather ? '重合度较高' : '无直接关联') + '】。建议在【' + routeFocus + '】【' + slotFocus + '】加强【客舱安全广播+颠簸防范提示】。'
      };
    })();
    // 4. 起火冒烟 RD04
    (function () {
      const dimId = 'RD04', cfg = BRIEFING_DIM_MAP[dimId];
      const w30 = dimWindows[dimId].w30;
      const hasAny = w30.curCount > 0;
      // 连续零发生天数：从今天往前扫，直到遇到一起该维度事件
      let zeroDays = 0;
      const dates = new Set((db.events || []).filter(e => e.dimension_id === dimId).map(e => e.event_date));
      for (let i = 0; i < 365; i++) {
        const d = new Date(now.getTime() - i * 86400000).toISOString().slice(0, 10);
        if (dates.has(d)) break;
        zeroDays++;
      }
      const focus = ['锂电池', '厨房设备', '电气线路'];
      const wxFocus = hasAny ? _rootCauseTag(w30.cur, cfg) : '锂电池';
      const baseName = _baseNameCN(_topBase((db.events || []).slice(-50).filter(function (e) { return e.dimension_id === dimId; })).id) || '虹桥/浦东';
      section_risks.fire = {
        dim_id: dimId, name: cfg.name,
        has_event: hasAny,
        zero_days: zeroDays,
        status: hasAny ? '保持平稳' : '零发生',
        current_focus: wxFocus,
        action_base: baseName,
        action: hasAny ? '宣贯培训' : '专项检查',
        sentence: '本周期内【' + (hasAny ? '发生' : '未发生') + '】起火冒烟事件，连续【' + zeroDays + '】天【' + (hasAny ? '保持平稳' : '零发生') + '】。当前风险焦点为【' + wxFocus + '】，已在【' + baseName + '】开展【' + (hasAny ? '宣贯培训' : '专项检查') + '】，后续将持续跟踪。'
      };
    })();
    // 5. 紧急情况 RD07
    (function () {
      const dimId = 'RD07', cfg = BRIEFING_DIM_MAP[dimId];
      const w30 = dimWindows[dimId].w30;
      const mCount = monthByDim[dimId] || 0;
      const lmCount = lastMonthByDim[dimId] || 0;
      const monthChange = _pct(mCount, lmCount);
      const cause = _rootCauseTag(w30.cur, cfg);
      const types = Array.from(new Set(w30.cur.map(e => e.label_secondary || '应急响应'))).slice(0, 2);
      section_risks.emergency = {
        dim_id: dimId, name: cfg.name,
        count: w30.curCount,
        emergency_types: types.length ? types : ['应急响应'],
        handled: w30.curCount > 0 ? '已妥善处置' : '无需处置',
        month_count: mCount,
        month_change: monthChange >= 0 ? '增加' : '减少',
        month_change_pct: Math.abs(monthChange),
        main_cause: cause,
        rectification: monthChange > 0 ? '落实中' : '部署',
        sentence: '本周期内共启动【' + w30.curCount + '】次紧急响应，涉及【' + (types.length ? types.join('、') : '应急响应') + '】，均【' + (w30.curCount > 0 ? '已妥善处置' : '无需处置') + '】。本月累计【' + mCount + '】起，与上月同期相比【' + (monthChange >= 0 ? '增加' : '减少') + '】【' + Math.abs(monthChange) + '%】，主要诱因为【' + cause + '】，整改措施已【' + (monthChange > 0 ? '落实中' : '部署') + '】。'
      };
    })();
    // 6. 疲劳管控 RD02
    (function () {
      const dimId = 'RD02', cfg = BRIEFING_DIM_MAP[dimId];
      const w7 = dimWindows[dimId].w7;
      const baseAvgHours = 6.8 + (w7.curCount * 0.05); // 假设备勤时间与疲劳事件数相关
      const pctChange = Math.max(-15, Math.min(25, w7.change));
      const nearLimitCrew = w7.cur.length > 0 ? w7.cur[0].responsible_person || '某机组' : '某机组';
      const topBaseF = _topBase(w7.cur);
      const seasonTrend = Math.random() > 0.4 ? '增加' : '减少';
      section_risks.fatigue = {
        dim_id: dimId, name: cfg.name,
        base_id: topBaseF.id,
        base_name: topBaseF.name || '虹桥',
        avg_hours: baseAvgHours.toFixed(1),
        n_days: 7,
        trend: pctChange >= 5 ? '上升' : (pctChange <= -5 ? '下降' : '持平'),
        change_pct: Math.abs(pctChange),
        near_limit_crew: nearLimitCrew,
        limit_type: w7.curCount > 3 ? '警戒值' : '上限',
        action: w7.curCount > 3 ? '调整排班' : '增加休息期',
        season_trend: seasonTrend,
        suggestion: '连续多日飞行',
        sentence: '本周期内【' + (topBaseF.name || '虹桥') + '】机组平均执勤时间为【' + baseAvgHours.toFixed(1) + '】小时，近【7】日环比【' + (pctChange >= 0 ? '上升' : '下降') + '】【' + Math.abs(pctChange) + '%】。其中【' + nearLimitCrew + '】执勤时间接近【' + (w7.curCount > 3 ? '警戒值' : '上限') + '】，已进行【' + (w7.curCount > 3 ? '调整排班' : '增加休息期') + '】处理。暑运/旺季以来，该基地月均飞行小时【' + seasonTrend + '】，建议关注【连续多日飞行】人员名单。'
      };
    })();
    // 7. 偏离程序 RD06
    (function () {
      const dimId = 'RD06', cfg = BRIEFING_DIM_MAP[dimId];
      const w7 = dimWindows[dimId].w7;
      const types = ['起飞', '进近', '复飞', '其他'];
      const typeMap = { '起飞': 0, '进近': 0, '复飞': 0, '其他': 0 };
      w7.cur.forEach(e => {
        const t = (e.label_secondary || '') + (e.description || '');
        if (/起飞|离场/.test(t)) typeMap['起飞']++;
        else if (/进近|落地|五边/.test(t)) typeMap['进近']++;
        else if (/复飞|go around/.test(t)) typeMap['复飞']++;
        else typeMap['其他']++;
      });
      const topT = Object.entries(typeMap).sort((a, b) => b[1] - a[1])[0][0];
      const baseTop = _topBase(w7.cur);
      const cause = _rootCauseTag(w7.cur, cfg);
      const suggestionAction = w7.change > 20 ? '模拟机复训' : (w7.change < -10 ? 'SOP宣贯' : '案例复盘会');
      section_risks.sop = {
        dim_id: dimId, name: cfg.name,
        count: w7.curCount,
        types: topT,
        n_days: 7,
        trend: w7.change >= 10 ? '上升' : (w7.change <= -10 ? '下降' : '持平'),
        top_base_id: baseTop.id,
        top_base_name: baseTop.name || '虹桥',
        root_cause: cause,
        suggestion: suggestionAction,
        sentence: '本周期内发生【' + w7.curCount + '】起程序偏离事件，类型集中在【' + topT + '】。近【7】日偏离率【' + (w7.change >= 10 ? '上升' : (w7.change <= -10 ? '下降' : '持平')) + '】，【' + (baseTop.name || '虹桥') + '】占比最高，主要涉及【' + cause + '】。建议在【' + (baseTop.name || '虹桥') + '】安排【' + suggestionAction + '】。'
      };
    })();

    // ===== 模块三：各基地风险画像 =====
    const section_bases = Object.values(allBasesData)
      .filter(b => b.month_count > 0 || b.total_count > 0)
      .sort((a, b) => b.month_count - a.month_count)
      .slice(0, 10)
      .map(b => {
        const lv = _baseLevel(b);
        const topDim0 = b.dim_rank[0] || { dim_name: '无', count: 0 };
        const topDim1 = b.dim_rank[1];
        const wTop = topDim0.dim_id ? _dimWindow(db, topDim0.dim_id, [b.id], today, 7) : null;
        const avgBase = Object.values(allBasesData).reduce((s, x) => s + x.month_count, 0) / Math.max(1, Object.values(allBasesData).length);
        const vsAvg = b.month_count > avgBase ? '高于' : '低于';
        const risk2 = [topDim0?.dim_name, topDim1?.dim_name].filter(Boolean);
        return {
          base_id: b.id,
          base_name: b.name,
          level: lv,
          top_risks: risk2,
          trend_dim_id: topDim0?.dim_id,
          trend_dim_name: topDim0?.dim_name,
          trend: wTop ? _levelOfRisk(wTop.change, wTop.curCount) : '持平',
          n_days: 7,
          count_7d: wTop?.curCount || 0,
          vs_avg: vsAvg,
          weakness: wTop?.curCount ? (topDim0?.dim_name + '流程复核') : '夜间SOP执行',
          suggestion: lv === '绿' ? '常规巡查' : (lv === '黄' ? '加强抽查' : (lv === '橙' ? '专项整顿' : '现场督办')),
          sentence: (function () {
            const tr = wTop ? _levelOfRisk(wTop.change, wTop.curCount) : '持平';
            const cc7 = wTop?.curCount || 0;
            const weakPt = (topDim0?.dim_name ? topDim0.dim_name + '流程执行' : '夜间SOP执行');
            const sg = lv === '绿' ? '常规巡查' : '专项抽查+案例复盘';
            return '【' + b.name + '】综合风险等级【' + lv + '】，本周期突出风险为【' + (risk2.join('、') || '常规运行') + '】。其中【' + (topDim0?.dim_name || '无') + '】趋势【' + tr + '】，近【7】日共【' + cc7 + '】起，' + vsAvg + '全公司平均水平。需重点关注的薄弱环节为【' + weakPt + '】，建议【' + sg + '】。';
          })()
        };
      });

    // ===== 模块四：天气与运行风险联动 =====
    const section_weather = (function () {
      const ws = (db.weathers || []).filter(w => w.raw && w.weather_type === 'system').map(w => w.raw);
      const primary = ws[0] || {
        name: '华东区域对流云系', type: '雷暴', duration: '4小时', region: '上海、杭州、南京',
        impact_bases: ['Z1-CAN'], level: '黄', phenomena: '短时强降水+雷暴'
      };
      const impacted = (primary.impact_bases || []).map(id => _baseNameCN(id)).filter(Boolean);
      const phaseRisk = /颠簸|大风|雷雨/.test(primary.phenomena || primary.type || '') ? '进近' : '起飞';
      const riskLevel = primary.level === '红' ? '高' : (primary.level === '橙' ? '中' : '中低');
      const consequence = primary.level === '红' ? '备降' : (primary.level === '橙' ? '复飞' : '不稳定进近');
      return {
        primary: {
          name: primary.name,
          type: primary.type,
          phenomena: primary.phenomena,
          region: primary.region,
          duration: primary.duration,
          level: primary.level,
          impact_bases: primary.impact_bases || [],
          impact_base_names: impacted,
          phase: phaseRisk,
          phase_risk: riskLevel,
          consequence: consequence,
          sample_routes: ['SHA-CTU', 'PVG-CAN'],
          suggestion: ['气象监控', '燃油政策', '备降场预案'],
          suggest_mechanism: primary.level === '红' || primary.level === '橙' ? '运行副总师会商机制' : '基地签派会商'
        },
        sentence: (function () {
          const pName = primary.name || '对流云团';
          const pPhen = primary.phenomena || primary.type || '';
          const pRegion = primary.region || '华东区域';
          const pDur = primary.duration || '4小时';
          const pImp = impacted.join('、') || '虹桥浦东';
          const pBases = (primary.impact_bases || []).join('/') || '华东干线';
          const pMech = primary.level === '红' || primary.level === '橙' ? '运行副总师会商机制' : '基地签派会商';
          return '当前影响运行的主要天气系统为【' + pName + '】（' + pPhen + '），覆盖【' + pRegion + '】，预计持续【' + pDur + '】。该天气对【' + pImp + '】的【' + phaseRisk + '】阶段构成【' + riskLevel + '】风险，可能引发【' + consequence + '】增加。建议对涉及【' + pBases + '】的航班加强【气象监控+燃油政策+备降场预案】，并视情启动【' + pMech + '】。';
        })()
      };
    })();

    // ===== 模块五：重点工作提醒（行动项） =====
    const section_actions = (function () {
      const dimsSorted = Object.entries(monthByDim).sort((a, b) => b[1] - a[1]);
      const top1 = dimsSorted[0] ? { dim: BRIEFING_DIM_MAP[dimsSorted[0][0]]?.name || '偏离程序', id: dimsSorted[0][0], count: dimsSorted[0][1] } : null;
      const top2 = dimsSorted[1] ? { dim: BRIEFING_DIM_MAP[dimsSorted[1][0]]?.name || '舱门管控', id: dimsSorted[1][0], count: dimsSorted[1][1] } : null;
      const topBase1 = _topBase((db.events || []).filter(e => top1 && e.dimension_id === top1.id));
      const topBase2 = _topBase((db.events || []).filter(e => top2 && e.dimension_id === top2.id));
      return {
        focus_today: [
          top1 ? {
            content: '【' + top1.dim + '专项复核】（' + (topBase1.name || '虹桥/浦东') + '基地/相关' + top1.count + '名责任人员），要求今日内18:00前完成SOP再确认',
            base: topBase1.name || '虹桥/浦东',
            deadline: '今日 18:00',
            detail: top1.count + '起事件复盘+责任到人'
          } : null,
          top2 ? {
            content: '【' + top2.dim + '宣贯培训】（' + (topBase2.name || '综合一') + '基地乘务组），要求明日前完成全员覆盖',
            base: topBase2.name || '综合一',
            deadline: '明日 12:00',
            detail: top2.count + '起典型案例学习+现场考核'
          } : null,
          section_weather.primary ? {
            content: '【' + section_weather.primary.name + '天气联动】（受影响' + section_weather.primary.impact_base_names.join('/') + '基地），相关航班机组提前签收天气简报',
            base: section_weather.primary.impact_base_names.join('/'),
            deadline: '航班前 2小时',
            detail: section_weather.primary.phenomena + ' 风险提示+备降场预选'
          } : null
        ].filter(Boolean),
        rectification: {
          planned: 12,
          done: 9,
          pending: 3,
          pending_list: ['证照到期复核（广州）', '锂电池专项检查（广州）', '复飞案例复盘（广州分队）'],
          follow_up: ['广州/证照到期复核', '广州/锂电池专项', '广州分队/复飞案例复盘']
        },
        tomorrow_forecast: {
          base_id: 'Z1-CAN',
          base_name: '广州',
          risk_type: top1?.dim || 'SOP偏离',
          measure: '航前SOP书面抽查+现场督导'
        }
      };
    })();

    // ===== 模块六：专业衔接用语（词汇表+推荐句式） =====
    const section_lexicon = {
      trend: {
        up: ['明显抬头', '呈多发态势', '逐日递增', '需警惕'],
        down: ['明显回落', '得到遏制', '持续向好', '已回归常态'],
        flat: ['整体平稳', '波动在正常范围', '无异常波动']
      },
      root_cause: [
        '初步判断为操作疏漏所致',
        '数据指向流程衔接环节存在薄弱',
        '与人员疲劳因素高度相关，需进一步核实',
        '与天气颠簸区域高度重合'
      ],
      suggestion: {
        strong: ['必须', '立即', '今日内完成'],
        medium: ['建议', '应', '尽快'],
        weak: ['可考虑', '视情', '酌情']
      }
    };

    // 最终返回
    return {
      version: 'v2.0.0 专业简报升级版',
      date: today,
      generated_at: new Date().toISOString(),
      base_scope: baseId ? { id: baseId, name: _baseNameCN(baseId) } : { id: 'HQ', name: '总部全景' },
      stats_overview: {
        total_events: (db.events || []).length,
        total_crew: (db.crew_profiles || []).length,
        month_events: monthEvents.length,
        month_change_pct: _pct(monthEvents.length, lastMonthEvents.length),
        bases_covered: Object.keys(allBasesData).length
      },
      // 六大模块
      section_overall,
      section_risks,
      section_bases,
      section_weather,
      section_actions,
      section_lexicon,
      // 下钻所需原始数据（轻量）
      drilldown: {
        dim_windows_available: true,
        top_dim_id: topDimId,
        base_ids_scope: baseIds
      }
    };
  }
  // GET /api/v2/briefing/drilldown
  function getBriefingDrilldown(_p, query) {
    const db = loadDB();
    const dimId = query.dim_id || 'RD06';
    const baseId = query.base;
    const baseIds = baseId ? expandBaseId(db, baseId) : null;
    const daysN = parseInt(query.days || '30', 10);
    const today = utils.today();
    const w = _dimWindow(db, dimId, baseIds, today, daysN);
    const byBase = {};
    w.cur.forEach(e => { byBase[e.base] = (byBase[e.base] || 0) + 1; });
    const bySlot = {};
    w.cur.forEach(e => {
      const d = _parseDate(e.event_date);
      const s = d ? (d.getHours() >= 6 && d.getHours() < 12 ? '上午' : (d.getHours() < 18 ? '下午' : '夜间')) : '未知';
      bySlot[s] = (bySlot[s] || 0) + 1;
    });
    return {
      dim_id: dimId,
      dim_name: BRIEFING_DIM_MAP[dimId]?.name || dimId,
      days: daysN,
      count: w.curCount,
      prev_count: w.prevCount,
      change_pct: w.change,
      by_base: Object.entries(byBase).map(([k, v]) => ({ id: k, name: _baseNameCN(k), count: v })),
      by_slot: Object.entries(bySlot).map(([k, v]) => ({ slot: k, count: v })),
      sample_events: w.cur.slice(0, 10).map(e => ({
        event_id: e.event_id, date: e.event_date, severity: e.severity,
        base: _baseNameCN(e.base), desc: e.description || e.label_secondary
      }))
    };
  }

  // ============ 暴露 API ============
  global.CabinMockServer = {
    handle,
    reset: resetDB,
    getDB: loadDB,
    getSession,
    audit,
    utils,
    configureRateLimit,
    getRateLimitState: () => ({ ...rateLimitState }),
    // 数据备份/导出/导入能力（低风险修复）
    exportBackup: exportDBData,
    downloadBackup,
    importBackup: importDBData,
    dbSummary,
    eventCount: dbEventCount,
    // 新增V2工具供前端调用
    briefingHelpers: {
      baseNameCN: _baseNameCN,
      dimMap: BRIEFING_DIM_MAP,
      trendPhrase: _trendPhrase
    }
  };

  // 自动初始化（如果 localStorage 为空）
  try { loadDB(); } catch (e) { /* 无 localStorage 环境时忽略 */ }

  // 如果是 Node.js 环境，启动一个 HTTP 服务器提供静态服务
  if (typeof module !== 'undefined' && module.exports && typeof require !== 'undefined') {
    try {
      // 在 Node 环境中模拟 localStorage（使用 JSON 文件持久化，或使用内存存储）
      (function () {
        const memoryStore = {};
        const path = require('path');
        const fs = require('fs');
        // 持久化路径优先级：
        //   1) 环境变量 CABIN_PERSIST_FILE（显式指定完整文件路径）
        //   2) IISNODE 环境：站点根下 App_Data/mock-server-storage.json（IIS 默认写权限安全目录）
        //   3) 默认：项目根下 .mock-server-storage.json（开发模式）
        let storageFile = process.env.CABIN_PERSIST_FILE
          ? path.resolve(process.env.CABIN_PERSIST_FILE)
          : (process.env.IISNODE_VERSION
              ? path.resolve(__dirname, '..', 'App_Data', 'mock-server-storage.json')
              : path.resolve(__dirname, '..', '.mock-server-storage.json'));
        // 自动确保持久化目录存在（App_Data / 自定义目录）
        try {
          const persistDir = path.dirname(storageFile);
          if (!fs.existsSync(persistDir)) fs.mkdirSync(persistDir, { recursive: true });
        } catch (e) { /* 目录创建失败，退化到内存 */ }
        // 尝试从文件读取持久化数据
        try {
          if (fs.existsSync(storageFile)) {
            const raw = fs.readFileSync(storageFile, 'utf-8');
            if (raw) {
              const parsed = JSON.parse(raw);
              for (const k in parsed) if (parsed.hasOwnProperty(k)) memoryStore[k] = parsed[k];
            }
          }
        } catch (e) { /* ignore */ }
        function flushToDisk() {
          try { fs.writeFileSync(storageFile, JSON.stringify(memoryStore, null, 2), 'utf-8'); } catch (e) {}
        }
        if (typeof global !== 'undefined' && !global.localStorage) {
          global.localStorage = {
            getItem: function (k) { return memoryStore.hasOwnProperty(k) ? memoryStore[k] : null; },
            setItem: function (k, v) { memoryStore[k] = String(v); flushToDisk(); },
            removeItem: function (k) { delete memoryStore[k]; flushToDisk(); },
            clear: function () { for (const k in memoryStore) delete memoryStore[k]; flushToDisk(); },
            key: function (i) { return Object.keys(memoryStore)[i] || null; },
            get length() { return Object.keys(memoryStore).length; }
          };
        }
      })();
      const fs = require('fs');
      const path = require('path');
      const http = require('http');
      const url = require('url');
      const PORT = Number(process.env.PORT) || 5173;

      const MIME = {
        '.html': 'text/html; charset=utf-8',
        '.js': 'application/javascript; charset=utf-8',
        '.json': 'application/json; charset=utf-8',
        '.css': 'text/css; charset=utf-8',
        '.svg': 'image/svg+xml',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.ico': 'image/x-icon'
      };

      const server = http.createServer(function (req, res) {
        try {
          const parsed = url.parse(req.url, true);
          let pathname = decodeURIComponent(parsed.pathname || '/');
          if (pathname === '/' || pathname === '') pathname = '/dashboard-prototype.html';
          const rootDir = path.resolve(__dirname, '..');
          let filePath = path.join(rootDir, pathname);
          if (!filePath.startsWith(rootDir)) {
            res.writeHead(403); res.end('Forbidden'); return;
          }
          // 处理 /api/ 路由（但排除 /api/ 路径下的静态文件，如 /api/api-client.js）
          // 修复：/api/api-client.js 被当作 API 请求返回 404，导致前端加载到旧缓存
          const STATIC_EXTS = ['.html', '.js', '.css', '.json', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.map'];
          const reqExt = path.extname(parsed.pathname).toLowerCase();
          const isStaticFileReq = STATIC_EXTS.includes(reqExt);
          if (parsed.pathname.startsWith('/api/') && !isStaticFileReq) {
            let body = '';
            req.on('data', function (chunk) { body += chunk.toString(); });
            req.on('end', async function () {
              try {
                const bodyData = body ? (function () {
                  try { return JSON.parse(body); } catch (e) { return null; }
                })() : null;
                // 调用 mock-server 的 handle 函数
                const result = await global.CabinMockServer.handle(
                  req.method,
                  parsed.pathname,
                  { query: parsed.query || {}, body: bodyData }
                );
                const statusCode = result?.status || 200;
                res.writeHead(statusCode, {
                  'Content-Type': MIME['.json'],
                  'Access-Control-Allow-Origin': '*',
                  'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
                  'Access-Control-Allow-Headers': 'Content-Type,Authorization'
                });
                res.end(JSON.stringify(result));
              } catch (apiErr) {
                console.error('[api error]', parsed.pathname, apiErr);
                res.writeHead(500, { 'Content-Type': MIME['.json'] });
                res.end(JSON.stringify({
                  ok: false, status: 500,
                  error: { code: 'SERVER_ERROR', message: apiErr.message || 'Internal Server Error' },
                  meta: { server_time: new Date().toISOString() }
                }));
              }
            });
            return;
          }
          // CORS 预检测
          if (req.method === 'OPTIONS') {
            res.writeHead(204, {
              'Access-Control-Allow-Origin': '*',
              'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
              'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            });
            res.end();
            return;
          }
          // 静态文件服务
          fs.stat(filePath, function (err, stat) {
            if (err || !stat.isFile()) {
              const altPath = path.join(rootDir, 'deploy', pathname === '/dashboard-prototype.html' ? 'index.html' : pathname.slice(1));
              fs.stat(altPath, function (e2, st2) {
                if (e2 || !st2.isFile()) {
                  res.writeHead(404); res.end('Not Found: ' + pathname);
                  return;
                }
                sendFile(altPath, st2);
              });
              return;
            }
            sendFile(filePath, stat);
          });
          function sendFile(fp, st) {
            const ext = path.extname(fp).toLowerCase();
            res.writeHead(200, {
              'Content-Type': MIME[ext] || 'application/octet-stream',
              'Content-Length': st.size,
              'Access-Control-Allow-Origin': '*'
            });
            fs.createReadStream(fp).pipe(res);
          }
        } catch (srvErr) {
          console.error('[server error]', srvErr);
          try { res.writeHead(500); res.end('Server Error: ' + srvErr.message); } catch (e) {}
        }
      });
      server.listen(PORT, function () {
        console.log('\n======================================================');
        console.log('  客舱核心风险差异化预警系统 · Mock Server 已启动');
        console.log('  - HTTP 服务地址:  http://localhost:' + PORT + '/');
        console.log('  - 看板页面:       http://localhost:' + PORT + '/dashboard-prototype.html');
        console.log('  - API 健康检查:   GET http://localhost:' + PORT + '/api/v1/health');
        console.log('  - 内置数据集:     GET http://localhost:' + PORT + '/api/v1/dev/builtin-status');
        console.log('  - V2版今日简报:   GET http://localhost:' + PORT + '/api/v2/briefing/today');
        console.log('======================================================\n');
      });
      server.on('error', function (e) {
        if (e.code === 'EADDRINUSE') {
          console.log('端口 ' + PORT + ' 已被占用，系统可能已在运行。请通过 http://localhost:' + PORT + '/ 访问');
        } else {
          console.error('Mock Server 启动失败:', e.message);
        }
      });
    } catch (startErr) {
      console.error('Node环境下启动HTTP Server失败：', startErr);
    }
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : (typeof global !== 'undefined' ? global : this)));
