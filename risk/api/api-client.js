/**
 * 客舱核心风险差异化预警系统 · 前端 API 客户端
 * 对接 mock-server.js，提供：
 *   - 鉴权（飞书 OAuth 模拟，Bearer Token）
 *   - 缓存（风险评分 5min，符合 §7.9）
 *   - 限流客户端提示（429 退避）
 *   - 错误统一处理
 *   - 请求重试
 *   - 请求/响应日志（便于调试）
 *   - 事件订阅（onRequest/onResponse/onError）
 */
(function (global) {
  'use strict';

  const CACHE_TTL = 5 * 60 * 1000;            // 风险评分缓存 5 分钟
  const CACHEABLE_PATHS = ['/api/v1/risk-scores']; // 仅列表查询缓存
  const RETRY_STATUS = [500, 502, 503, 504];  // 可重试状态码
  const MAX_RETRY = 2;

  const cache = new Map();
  // in-flight 请求去重（single-flight）：相同 GET 请求并发时只发一次，其余 await 同一 Promise
  const inflight = new Map();
  const listeners = { request: [], response: [], error: [] };

  function emit(type, payload) {
    (listeners[type] || []).forEach(fn => {
      try { fn(payload); } catch (e) { console.warn('[api] listener error', e); }
    });
  }

  function buildQuery(params) {
    if (!params) return '';
    const sp = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      // 过滤空值、undefined、null、空字符串（防止发送无效参数导致 400）
      if (v !== undefined && v !== null && v !== '' && !(typeof v === 'number' && isNaN(v))) {
        sp.append(k, v);
      }
    });
    const s = sp.toString();
    return s ? `?${s}` : '';
  }

  function cacheKey(method, path, query) {
    const q = buildQuery(query);
    return `${method} ${path}${q}`;
  }

  function isCacheable(method, path) {
    return method === 'GET' && CACHEABLE_PATHS.some(p => path.startsWith(p));
  }

  function getCache(key) {
    const entry = cache.get(key);
    if (!entry) return null;
    if (Date.now() - entry.t > CACHE_TTL) {
      cache.delete(key);
      return null;
    }
    return entry.v;
  }
  function setCache(key, value) {
    cache.set(key, { t: Date.now(), v: value });
  }
  function clearCache() {
    cache.clear();
  }

  function getToken() {
    try {
      const s = JSON.parse(localStorage.getItem('cabin_risk_session_v1') || 'null');
      return s?.token || null;
    } catch { return null; }
  }

  async function request(method, path, { query, body, retry = 0, useCache = true } = {}) {
    const fullQuery = buildQuery(query);
    const fullPath = `${path}${fullQuery}`;
    const ckey = cacheKey(method, path, query);

    // 缓存命中
    if (useCache && isCacheable(method, path)) {
      const cached = getCache(ckey);
      if (cached) {
        emit('response', { method, path: fullPath, cached: true, data: cached, ts: Date.now() });
        return { ...cached, _fromCache: true };
      }
    }

    // in-flight 去重：仅对 GET 请求合并并发（POST/PUT/DELETE 为写入操作，不去重）
    if (method === 'GET') {
      const pending = inflight.get(ckey);
      if (pending) return pending;
    }

    const promise = (async () => {
      emit('request', { method, path: fullPath, body, ts: Date.now() });

      // 调用 Mock 服务端
      const token = getToken();
      const headers = { 'Authorization': token ? `Bearer ${token}` : '' };
      const res = await global.CabinMockServer.handle(method, path, { query: query || {}, body });

      emit('response', { method, path: fullPath, status: res.status, data: res, ts: Date.now() });

      if (!res.ok) {
        // 重试逻辑
        if (RETRY_STATUS.includes(res.status) && retry < MAX_RETRY) {
          await new Promise(r => setTimeout(r, 300 * (retry + 1)));
          return request(method, path, { query, body, retry: retry + 1, useCache });
        }

        // 限流退避：自动等待 retry_after 后重试（最多重试 2 次，避免无限等待）
        if (res.status === 429) {
          const ra = res.error?.retry_after || 60;
          if (retry < MAX_RETRY) {
            emit('error', { method, path: fullPath, status: 429, retry_after: ra, autoRetry: true });
            await new Promise(r => setTimeout(r, ra * 1000 + 200)); // 多等 200ms 避免窗口边界
            return request(method, path, { query, body, retry: retry + 1, useCache });
          }
          // 超过最大重试次数才抛出
          emit('error', { method, path: fullPath, status: 429, retry_after: ra, autoRetry: false });
          const e = new Error(`请求被限流，请在 ${ra} 秒后重试`);
          e.status = 429; e.code = 'RATE_LIMITED'; e.retry_after = ra;
          throw e;
        }

        // 鉴权失败
        if (res.status === 401) {
          emit('error', { method, path: fullPath, status: 401 });
          const e = new Error('未登录或会话已过期');
          e.status = 401; e.code = 'UNAUTHORIZED';
          throw e;
        }

        emit('error', { method, path: fullPath, status: res.status, error: res.error });
        // 400 错误：参数校验失败，记录详细信息便于排查
        if (res.status === 400) {
          console.warn('[api] 400 Bad Request:', method, fullPath, '→', res.error?.code || 'UNKNOWN', ':', res.error?.message || '参数错误');
        }
        const e = new Error(res.error?.message || `请求失败 (${res.status})`);
        e.status = res.status; e.code = res.error?.code || 'ERROR';
        e.detail = res.error;
        throw e;
      }

      // 写缓存
      if (isCacheable(method, path)) setCache(ckey, res);

      return res;
    })();

    // 注册 in-flight（仅 GET），完成后清理
    if (method === 'GET') {
      inflight.set(ckey, promise);
      promise.finally(() => inflight.delete(ckey));
    }

    return promise;
  }

  // ============ 业务 API ============
  const api = {
    // —— 鉴权
    auth: {
      login: (payload) => request('POST', '/api/v1/auth/login', { body: payload }),
      logout: () => request('POST', '/api/v1/auth/logout'),
      me: () => request('GET', '/api/v1/auth/me')
    },

    // —— 风险评分
    riskScores: {
      list: (params) => request('GET', '/api/v1/risk-scores', { query: params }),
      get: (riskId) => request('GET', `/api/v1/risk-scores/${encodeURIComponent(riskId)}`, { useCache: false }),
      factors: (riskId) => request('GET', `/api/v1/risk-scores/${encodeURIComponent(riskId)}/factors`, { useCache: false })
    },

    // —— 因子溯源
    factors: {
      weather: (factorId) => request('GET', `/api/v1/factors/${encodeURIComponent(factorId)}/weather`, { useCache: false }),
      events: (factorId) => request('GET', `/api/v1/factors/${encodeURIComponent(factorId)}/events`, { useCache: false })
    },

    // —— 管理措施
    measures: {
      updateStatus: (measureId, payload) =>
        request('POST', `/api/v1/measures/${encodeURIComponent(measureId)}/status`, { body: payload, useCache: false })
    },

    // —— 晨间简报
    briefing: {
      today: (baseId) => request('GET', '/api/v1/briefing/today', { query: baseId ? { base: baseId } : null, useCache: false }),
      push: (payload) => request('POST', '/api/v1/briefing/push', { body: payload, useCache: false }),
      pushToUser: (targetUserId, baseId) => request('POST', '/api/v1/briefing/push', { body: { channel: 'feishu', target_user_id: targetUserId, base_id: baseId }, useCache: false })
    },

    // —— V2 专业版今日简报（六大模块，真实数据驱动）
    briefingV2: {
      today: (baseId) => request('GET', '/api/v2/briefing/today', { query: baseId ? { base: baseId } : null, useCache: false }),
      drilldown: (params) => request('GET', '/api/v2/briefing/drilldown', { query: params || {}, useCache: false })
    },

    // —— 报告导出
    reports: {
      export: (payload) => request('POST', '/api/v1/reports/export', { body: payload, useCache: false }),
      get: (taskId) => request('GET', `/api/v1/reports/${encodeURIComponent(taskId)}`, { useCache: false }),
      // 轮询任务直到完成
      waitUntilDone: async (taskId, { interval = 1000, timeout = 30000 } = {}) => {
        const start = Date.now();
        while (Date.now() - start < timeout) {
          const res = await request('GET', `/api/v1/reports/${encodeURIComponent(taskId)}`, { useCache: false });
          if (res.data.status === 'completed' || res.data.status === 'failed') return res;
          await new Promise(r => setTimeout(r, interval));
        }
        const e = new Error('任务超时'); e.code = 'TIMEOUT'; throw e;
      }
    },

    // 航线数据缓存（供自动识别基地等场景使用）
    _routesCache: null,
    bases: {
      list: () => request('GET', '/api/v1/bases')
    },

    // —— 航线管理
    routes: {
      list: async (params) => {
        const result = await request('GET', '/api/v1/routes', { query: params, useCache: false });
        // 全量查询时缓存航线数据，供自动识别基地等功能使用
        if (!params || !params.base_id) {
          CabinAPI._routesCache = result.data?.data || result.data || [];
        }
        return result;
      },
      create: (payload) => request('POST', '/api/v1/routes', { body: payload, useCache: false }),
      update: (routeId, payload) => request('PUT', `/api/v1/routes/${encodeURIComponent(routeId)}`, { body: payload, useCache: false }),
      delete: (routeId) => request('DELETE', `/api/v1/routes/${encodeURIComponent(routeId)}`, { useCache: false })
    },

    // —— 风险维度与事件统计
    riskDimensions: {
      list: () => request('GET', '/api/v1/risk-dimensions', { useCache: false }),
      overview: (params) => request('GET', '/api/v1/risk-dimensions/overview', { query: params, useCache: false }),
      stats: (dimensionId, params) => request('GET', `/api/v1/risk-dimensions/${encodeURIComponent(dimensionId)}/stats`, { query: params, useCache: false }),
      // 批处理接口：一次性返回所有维度的统计（减少浏览器并发请求，缓解同域名6连接限制）
      statsBatch: (payload) => request('POST', '/api/v1/risk-dimensions/stats/batch', { body: payload || {}, useCache: false }),
      events: (dimensionId, params) => request('GET', `/api/v1/risk-dimensions/${encodeURIComponent(dimensionId)}/events`, { query: params, useCache: false })
    },

    // —— 事件管理（导入/导出/CRUD）
    events: {
      list: (params) => request('GET', '/api/v1/events', { query: params || {}, useCache: false }),
      // count: 兼容旧代码调用 - 实际通过 list() 取 total 字段
      count: async (params) => {
        const res = await request('GET', '/api/v1/events', { query: { ...(params||{}), page_size: 1, page: 1 }, useCache: false });
        return { data: { total: (res && res.data && (res.data.total || res.data.total_rows)) || (res && (res.total || res.total_rows)) || 0 } };
      },
      get: (eventId) => request('GET', `/api/v1/events/${encodeURIComponent(eventId)}`, { useCache: false }),
      create: (payload) => request('POST', '/api/v1/events', { body: payload, useCache: false }),
      update: (eventId, payload) => request('PUT', `/api/v1/events/${encodeURIComponent(eventId)}`, { body: payload, useCache: false }),
      delete: (eventId) => request('DELETE', `/api/v1/events/${encodeURIComponent(eventId)}`, { useCache: false }),
      purgeAll: () => request('DELETE', '/api/v1/events/purge/all', { useCache: false }),
      template: () => request('GET', '/api/v1/events/template', { useCache: false }),
      importCsv: (csvText) => request('POST', '/api/v1/events/import', { body: { csv_text: csvText }, useCache: false }),
      importJson: (events) => request('POST', '/api/v1/events/import', { body: { events }, useCache: false }),
      import: (payload) => request('POST', '/api/v1/events/import', { body: payload.events ? { events: payload.events } : { csv_text: payload.csv_text || payload }, useCache: false }),
      export: (params) => request('GET', '/api/v1/events/export', { query: params, useCache: false })
      },

    // —— 开发工具：操作历史时间线查询
    dev: {
      listOpHistory: () => request('GET', '/api/v1/dev/op-history', { useCache: false })
    },

    // —— 天气按时间段查询
    weather: {
      timeline: (params) => request('GET', '/api/v1/weather/timeline', { query: params, useCache: false }),
      cacheStatus: () => request('GET', '/api/v1/weather/cache-status', { useCache: false }),
      refresh: (baseId) => request('POST', '/api/v1/weather/refresh', { body: baseId ? { base_id: baseId } : {}, useCache: false }),
      routeHourly: (routeId) => request('GET', `/api/v1/weather/route/${encodeURIComponent(routeId)}/hourly`, { useCache: false }),
      typhoons: () => request('GET', '/api/v1/weather/typhoons', { useCache: false })
    },

    // —— 基地坐标（地图定位与就近基地）
    baseCoords: {
      list: (params) => request('GET', '/api/v1/bases/coords', { query: params, useCache: false }),
      nearest: (lat, lon) => request('GET', '/api/v1/bases/coords', { query: { lat, lon }, useCache: false })
    },

    // —— 航线专项风险提醒（基于历史事件联动风险维度）
    routeRiskAlerts: {
      list: (params) => request('GET', '/api/v1/route-risk-alerts', { query: params, useCache: false })
    },

    // —— 简报审核（预览+发送）
    briefingReview: {
      preview: (payload) => request('POST', '/api/v1/briefing/preview', { body: payload, useCache: false }),
      send: (payload) => request('POST', '/api/v1/briefing/send', { body: payload, useCache: false })
    },

    // —— 审计
    audit: {
      list: (limit) => request('GET', '/api/v1/audit', { query: limit ? { limit } : null, useCache: false })
    },

    // —— 人工复核池（第6项：被拒导入事件 → 放行/删除/批量）
    rejectPool: {
      list: (params) => request('GET', '/api/v1/reject-pool', { query: params || {}, useCache: false }),
      count: () => request('GET', '/api/v1/reject-pool/count', { useCache: false }),
      approve: (rejectId, remark) => request('POST', `/api/v1/reject-pool/${encodeURIComponent(rejectId)}/approve`, { body: { remark: remark || '' }, useCache: false }),
      remove: (rejectId, remark) => request('POST', `/api/v1/reject-pool/${encodeURIComponent(rejectId)}/delete`, { body: { remark: remark || '' }, useCache: false }),
      batch: (action, rejectIds, remark) => request('POST', '/api/v1/reject-pool/batch', { body: { action, reject_ids: rejectIds, remark: remark || '' }, useCache: false })
    },

    // —— 健康检查
    health: () => request('GET', '/api/v1/health', { useCache: false }),

    // —— 乘务员档案
    crew: {
      list: (params) => request('GET', '/api/v1/crew', { query: params, useCache: false }),
      get: (crewId) => request('GET', `/api/v1/crew/${encodeURIComponent(crewId)}`, { useCache: false }),
      update: (crewId, payload) => request('PUT', `/api/v1/crew/${encodeURIComponent(crewId)}`, { body: payload, useCache: false })
    },

    // —— 重点人员管控
    keyPersonnel: {
      add: (payload) => request('POST', '/api/v1/key-personnel/add', { body: payload, useCache: false }),
      remove: (payload) => request('POST', '/api/v1/key-personnel/remove', { body: payload, useCache: false }),
      list: () => request('GET', '/api/v1/key-personnel', { useCache: false })
    },

    // —— 通用请求方法（用于未封装的端点）
    _request: (method, path, body) => request(method, path, { body, useCache: false }),

    // —— 工具方法
    utils: {
      clearCache,
      on: (type, fn) => {
        (listeners[type] = listeners[type] || []).push(fn);
        return () => {
          const idx = listeners[type].indexOf(fn);
          if (idx >= 0) listeners[type].splice(idx, 1);
        };
      },
      isLoggedIn: () => !!getToken()
    }
  };

  global.CabinAPI = api;
})(window);
