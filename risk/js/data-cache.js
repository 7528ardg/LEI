/**
 * 本地数据缓存层（DataCache）
 * 功能：
 *   - 分级 TTL 缓存（业务数据按类型设置不同过期时间）
 *   - 版本校验（APP_VERSION 变更时自动丢弃旧缓存）
 *   - 即时显示 + 后台静默刷新（页面打开秒开，后台异步更新）
 *   - 数据哈希对比（避免不必要的 DOM 重渲染）
 *   - 离线降级（网络失败时使用缓存数据）
 *   - 缓存状态可视化（顶部状态条）
 */
(function (global) {
  'use strict';

  var PREFIX = '_cabin_dc_';

  // 分级 TTL（毫秒）
  var TTL = {
    hqOverview:  30 * 60 * 1000,  // 总部全景总览：30分钟（历史统计不常变）
    dimStats:    15 * 60 * 1000,  // 基地级维度统计：15分钟
    squadRisk:   15 * 60 * 1000,  // 分队风险明细：15分钟
    riskScores:   5 * 60 * 1000,  // 风险评分列表：5分钟（天气/航线变化快）
    measures:    10 * 60 * 1000,  // 管理建议：10分钟
    routeAlerts: 10 * 60 * 1000,  // 航线风险提醒：10分钟
    briefing:    10 * 60 * 1000,  // 今日简报：10分钟
    events:      10 * 60 * 1000,  // 全量事件列表：10分钟
    routes:      60 * 60 * 1000,  // 航线列表：1小时
    weather:      3 * 60 * 60 * 1000,  // 气象时间线：3小时
    typhoons:     3 * 60 * 60 * 1000,  // 台风数据：3小时
    weatherTimeline: 3 * 60 * 60 * 1000,
  };

  // 获取当前 APP_VERSION（兼容 HTML 内联定义）
  function getAppVersion() {
    try { return global.APP_VERSION || 'unknown'; } catch { return 'unknown'; }
  }

  // ---- 核心读写 ----

  function get(key) {
    try {
      var raw = localStorage.getItem(PREFIX + key);
      if (!raw) return null;
      var entry = JSON.parse(raw);
      if (entry.version !== getAppVersion()) {
        localStorage.removeItem(PREFIX + key);
        return null;
      }
      if (Date.now() - entry.savedAt > entry.ttl) {
        localStorage.removeItem(PREFIX + key);
        return null;
      }
      return entry.data;
    } catch (e) {
      console.warn('[DataCache] 读取失败:', key, e.message);
      return null;
    }
  }

  function set(key, data, ttl) {
    try {
      var entry = {
        savedAt: Date.now(),
        ttl: ttl || TTL[key] || 5 * 60 * 1000,
        version: getAppVersion(),
        data: data
      };
      localStorage.setItem(PREFIX + key, JSON.stringify(entry));
    } catch (e) {
      // localStorage 可能满了，清理过期缓存后重试
      console.warn('[DataCache] 写入失败，清理旧缓存后重试:', key, e.message);
      cleanExpired();
      try {
        localStorage.setItem(PREFIX + key, JSON.stringify(entry));
      } catch (e2) {
        console.error('[DataCache] 写入仍然失败:', key, e2.message);
      }
    }
  }

  // 获取缓存元信息（不返回数据本身）
  function getMeta(key) {
    try {
      var raw = localStorage.getItem(PREFIX + key);
      if (!raw) return null;
      var entry = JSON.parse(raw);
      return {
        savedAt: entry.savedAt,
        age: Date.now() - entry.savedAt,
        ttl: entry.ttl,
        expired: Date.now() - entry.savedAt > entry.ttl,
        version: entry.version,
        hasData: !!entry.data
      };
    } catch { return null; }
  }

  // 强制读取（忽略 TTL，仅校验版本）——用于离线降级
  function getStale(key) {
    try {
      var raw = localStorage.getItem(PREFIX + key);
      if (!raw) return null;
      var entry = JSON.parse(raw);
      if (entry.version !== getAppVersion()) return null;
      return entry.data;
    } catch { return null; }
  }

  // ---- 清理 ----

  function cleanExpired() {
    try {
      var keys = [];
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (k && k.indexOf(PREFIX) === 0) keys.push(k);
      }
      var cleaned = 0;
      keys.forEach(function(k) {
        try {
          var entry = JSON.parse(localStorage.getItem(k));
          if (entry && (entry.version !== getAppVersion() || Date.now() - entry.savedAt > entry.ttl)) {
            localStorage.removeItem(k);
            cleaned++;
          }
        } catch {
          localStorage.removeItem(k);
          cleaned++;
        }
      });
      if (cleaned > 0) console.log('[DataCache] 清理过期缓存:', cleaned, '项');
    } catch (e) {
      console.warn('[DataCache] 清理失败:', e.message);
    }
  }

  function clearAll() {
    try {
      var keys = [];
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (k && k.indexOf(PREFIX) === 0) keys.push(k);
      }
      keys.forEach(function(k) { localStorage.removeItem(k); });
      console.log('[DataCache] 已清除所有缓存:', keys.length, '项');
    } catch (e) {
      console.warn('[DataCache] 清除全部失败:', e.message);
    }
  }

  // ---- 数据哈希（用于对比数据是否变化，避免不必要的重渲染）----
  function hash(data) {
    try {
      var str = JSON.stringify(data);
      var h = 0;
      for (var i = 0; i < str.length; i++) {
        h = ((h << 5) - h) + str.charCodeAt(i);
        h |= 0;
      }
      return h;
    } catch { return 0; }
  }

  // ---- 缓存优先加载器 ----
  // 用法：DataCache.load('riskScores', baseId, asyncFn, renderFn)
  //   1. 先从缓存读取 → 如果有，立即调用 renderFn(缓存数据)（秒开）
  //   2. 后台调用 asyncFn 获取最新数据 → 对比哈希 → 有变化才重新 renderFn
  //   3. 网络失败时，如果有 stale 缓存，不报错（静默降级）
  function load(cacheKey, cacheParam, asyncFn, renderFn, opts) {
    opts = opts || {};
    var fullKey = cacheParam ? cacheKey + '_' + cacheParam : cacheKey;
    var ttl = opts.ttl || TTL[cacheKey] || 5 * 60 * 1000;
    var useStaleFallback = opts.staleFallback !== false; // 默认开启离线降级

    // 1. 先从缓存读取并立即渲染
    var cached = get(fullKey);
    if (cached) {
      try {
        renderFn(cached, { source: 'cache', savedAt: getMeta(fullKey).savedAt });
        CacheStatus.showCached(getMeta(fullKey).savedAt);
      } catch (e) {
        console.warn('[DataCache] 缓存渲染失败:', cacheKey, e.message);
      }
    }

    // 2. 后台异步获取最新数据
    return asyncFn().then(function(freshData) {
      // 写入缓存
      set(fullKey, freshData, ttl);
      // 对比哈希，有变化才重新渲染
      var freshHash = hash(freshData);
      var cachedHash = cached ? hash(cached) : 0;
      if (freshHash !== cachedHash) {
        try {
          renderFn(freshData, { source: 'network', savedAt: Date.now() });
          if (cached) {
            CacheStatus.showUpdated();
          } else {
            CacheStatus.hide();
          }
        } catch (e) {
          console.error('[DataCache] 最新数据渲染失败:', cacheKey, e.message);
        }
      } else {
        // 数据无变化
        CacheStatus.hide();
      }
      return freshData;
    }).catch(function(err) {
      console.warn('[DataCache] 后台刷新失败:', cacheKey, err.message);
      // 网络失败时的降级策略
      if (!cached && useStaleFallback) {
        var stale = getStale(fullKey);
        if (stale) {
          try {
            renderFn(stale, { source: 'stale', savedAt: getMeta(fullKey) ? getMeta(fullKey).savedAt : 0 });
            CacheStatus.showOffline();
          } catch (e) {
            console.error('[DataCache] 降级渲染失败:', cacheKey, e.message);
          }
        } else {
          CacheStatus.showOffline();
        }
      } else if (cached) {
        // 已有缓存显示着，网络失败不影响
        CacheStatus.showOffline();
      }
      throw err;
    });
  }

  // ---- 缓存状态条 ----
  var CacheStatus = {
    barEl: null,
    autoHideTimer: null,

    init: function() {
      if (this.barEl) return;
      var bar = document.getElementById('cacheStatusBar');
      if (!bar) {
        bar = document.createElement('div');
        bar.id = 'cacheStatusBar';
        document.body.appendChild(bar);
      }
      bar.style.cssText = [
        'position:fixed',
        'top:56px',
        'left:0',
        'right:0',
        'z-index:100',
        'padding:3px 16px',
        'font-size:12px',
        'display:none',
        'transition:opacity .3s',
        'backdrop-filter:blur(8px)',
        'text-align:center'
      ].join(';');
      this.barEl = bar;
    },

    show: function(message, type) {
      this.init();
      if (!this.barEl) return;
      var styles = {
        loading: 'background:rgba(46,139,255,.12);color:#2E8BFF;border-bottom:1px solid rgba(46,139,255,.25)',
        success: 'background:rgba(82,196,26,.10);color:#52C41A;border-bottom:1px solid rgba(82,196,26,.25)',
        stale:   'background:rgba(250,173,20,.10);color:#FAAD14;border-bottom:1px solid rgba(250,173,20,.25)',
        offline: 'background:rgba(245,34,45,.10);color:#F5222D;border-bottom:1px solid rgba(245,34,45,.25)'
      };
      this.barEl.style.display = 'block';
      // 简化设置方式
      var baseStyle = 'position:fixed;top:56px;left:0;right:0;z-index:100;padding:3px 16px;font-size:12px;display:block;transition:opacity .3s;backdrop-filter:blur(8px);text-align:center;';
      this.barEl.style.cssText = baseStyle + (styles[type] || styles.loading);
      this.barEl.innerHTML = message;
      if (this.autoHideTimer) { clearTimeout(this.autoHideTimer); this.autoHideTimer = null; }
      // 【修复·兜底机制】防止 loading 状态永久显示：设置最大 30 秒超时后自动隐藏
      // offline/stale 类型也设置超时（15秒），避免长期占据顶部空间
      var self = this;
      if (type === 'loading') {
        this.autoHideTimer = setTimeout(function() {
          console.warn('[CacheStatus] loading 状态超过 30 秒未关闭，强制隐藏（兜底机制触发）');
          self.hide();
        }, 30000);
      } else if (type === 'offline' || type === 'stale') {
        this.autoHideTimer = setTimeout(function() { self.hide(); }, 15000);
      }
    },

    hide: function() {
      if (this.barEl) this.barEl.style.display = 'none';
    },

    autoHide: function(delay) {
      var self = this;
      if (this.autoHideTimer) clearTimeout(this.autoHideTimer);
      this.autoHideTimer = setTimeout(function() { self.hide(); }, delay || 3000);
    },

    showCached: function(savedAt) {
      var time = new Date(savedAt).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
      this.show('📦 显示离线缓存（生成于 ' + time + '）· 后台正在刷新最新数据...', 'loading');
    },

    showUpdated: function() {
      var time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
      this.show('✅ 数据已更新至 ' + time, 'success');
      this.autoHide(3000);
    },

    showOffline: function() {
      this.show('⚠️ 网络连接失败 · 当前使用缓存数据（部分功能可能受限）', 'offline');
    },

    showStale: function(savedAt) {
      var time = new Date(savedAt).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
      this.show('⚠️ 缓存已过期（生成于 ' + time + '）· 网络不可用，使用旧数据', 'stale');
    }
  };

  // ---- 导出 ----
  global.DataCache = {
    TTL: TTL,
    get: get,
    set: set,
    getMeta: getMeta,
    getStale: getStale,
    cleanExpired: cleanExpired,
    clearAll: clearAll,
    hash: hash,
    load: load
  };

  global.CacheStatus = CacheStatus;

  // 启动时清理过期缓存
  setTimeout(function() { cleanExpired(); }, 100);

})(window);
