/* =============================================================================
 * 客舱小助手 · 数据包引擎 v1（M1.1 单一来源）
 * -----------------------------------------------------------------------------
 * 目的：让"内容数据包"（知识库/销售/题库）以 JSON 覆盖层形式覆盖内嵌基线，
 *       实现"改内容不改代码"。本文件为纯逻辑、零 DOM 依赖，
 *       浏览器挂 window.PACKS / Node 挂 module.exports（供单测与构建校验）。
 *
 * 覆盖语义（与方案文档一致）：
 *   1. 优先级：数据包覆盖层 > 内嵌基线
 *   2. 合并：按 packs_index 中 installedAt 升序逐包执行，同 key 后装者胜
 *   3. delete：从最终视图移除该 key（对基线与已 upsert 的覆盖均生效）
 *   4. 过期：appliedUntil < 今天 → 不参与合并但保留在索引（expired 标记，不删数据）
 *   5. 损坏防护：magic 不符 / JSON 损坏 → 静默忽略该包（控制台仅 warn）
 *
 * 存储抽象：所有函数首参为 store，接口 { getItem(k)->string|null,
 *           setItem(k,v), removeItem(k) }；浏览器传 localStorage，测试传内存实现。
 * -----------------------------------------------------------------------------
 * 数据包 JSON 结构（存 localStorage 键 pack:{packId}）：
 * {
 *   magic: 'cabin-data-pack-v1',
 *   packId: 'sales-2026-09',      // 全局唯一；同 packId 重装 = 整包覆盖升级
 *   type: 'kb' | 'sales' | 'quiz' | 'notice',   // notice 消费端 M2 接入
 *   lib: '',                       // 仅 kb 包：空=全库应用，'ccm'|'mgm'|'svc'|'daily'=单库
 *   title: '秋季机上销售包',
 *   version: 3,                    // 展示用；排序靠 installedAt
 *   issuedAt: '2026-08-29',
 *   appliedUntil: '2026-12-31',    // 缺省=永不过期
 *   items: [ { op:'upsert'|'delete', key:'estee-007', data:{...} } ]
 * }
 * packs_index 索引（存 localStorage 键 packs_index）：
 * { magic:'cabin-packs-index-v1', packs:[ {packId,type,title,version,installedAt,source} ] }
 * ============================================================================= */
(function (global) {
  'use strict';

  var PACKS_MAGIC = 'cabin-data-pack-v1';
  var PACKS_INDEX_MAGIC = 'cabin-packs-index-v1';
  var PACKS_INDEX_KEY = 'packs_index';
  var PACK_KEY_PREFIX = 'pack:';

  function fmtDay(d) {
    var y = d.getFullYear();
    var m = d.getMonth() + 1;
    var dd = d.getDate();
    return y + '-' + (m < 10 ? '0' + m : '' + m) + '-' + (dd < 10 ? '0' + dd : '' + dd);
  }

  /* ---------------- 索引读写 ---------------- */
  function readIndex(store) {
    try {
      var raw = store.getItem(PACKS_INDEX_KEY);
      if (!raw) return null;
      var idx = JSON.parse(raw);
      if (!idx || idx.magic !== PACKS_INDEX_MAGIC || !Array.isArray(idx.packs)) return null;
      return idx;
    } catch (e) { return null; }
  }
  function writeIndex(store, packs) {
    try {
      store.setItem(PACKS_INDEX_KEY, JSON.stringify({ magic: PACKS_INDEX_MAGIC, packs: packs }));
      return true;
    } catch (e) { return false; }
  }
  /* ---------------- 包读写 ---------------- */
  function readPack(store, packId) {
    try {
      var raw = store.getItem(PACK_KEY_PREFIX + packId);
      if (!raw) return null;
      var p = JSON.parse(raw);
      if (!p || p.magic !== PACKS_MAGIC || p.packId !== packId) return null;
      return p;
    } catch (e) { return null; }
  }
  /* 写入原始包数据（不校验语义，供 installPack 内部使用；失败抛给调用方判定） */
  function writePackRaw(store, pack) {
    store.setItem(PACK_KEY_PREFIX + pack.packId, JSON.stringify(pack));
  }

  /* ---------------- 包索引元信息列表 ---------------- */
  /* optType 为空返回全部类型；now 注入当前时间（测试固定日期用） */
  function listPacks(store, optType, now) {
    var idx = readIndex(store);
    if (!idx) return [];
    var today = fmtDay(now || new Date());
    var out = [];
    for (var i = 0; i < idx.packs.length; i++) {
      var e = idx.packs[i];
      if (optType && e.type !== optType) continue;
      var p = readPack(store, e.packId);
      var until = p && p.appliedUntil ? String(p.appliedUntil) : '';
      out.push({
        packId: e.packId,
        type: e.type,
        title: e.title || e.packId,
        version: e.version != null ? e.version : 1,
        installedAt: e.installedAt || '',
        source: e.source || 'import',
        appliedUntil: until,
        expired: !!(until && until < today),
        itemCount: p && Array.isArray(p.items) ? p.items.length : 0,
        valid: !!p
      });
    }
    return out;
  }
  function countPackType(store, type, now) {
    var list = listPacks(store, type, now);
    var active = 0, expired = 0;
    for (var i = 0; i < list.length; i++) {
      if (list[i].expired) expired++; else active++;
    }
    return { total: list.length, active: active, expired: expired, packs: list };
  }

  /* ---------------- 核心：构建某类型的最终覆盖视图 ---------------- */
  /* opts: { now:Date, lib:string }；lib 仅对 kb 包生效（空=全库，'ccm' 等=单库）
   * 返回 { map:{key:data}, kills:[keys], expired:[packIds] }
   *   map   = 所有 upsert 后最终生效的数据（已按后装者胜消解）
   *   kills = 声明过 delete 的 key 集合（对基线生效）
   *   expired = 因过期而未参与合并的 packId 列表 */
  function buildPackMap(store, type, opts) {
    opts = opts || {};
    var today = fmtDay(opts.now || new Date());
    var queryLib = opts.lib || '';
    var map = {};
    var kills = [];
    var expired = [];
    var idx = readIndex(store);
    if (!idx) return { map: map, kills: kills, expired: expired };
    var pending = [];
    for (var i = 0; i < idx.packs.length; i++) {
      var e = idx.packs[i];
      if (e.type !== type) continue;
      var p = readPack(store, e.packId);
      if (!p || !Array.isArray(p.items)) continue;
      if (p.lib && queryLib && p.lib !== queryLib) continue;  // 包声明单库且与查询库不符
      if (p.appliedUntil && String(p.appliedUntil) < today) { expired.push(e.packId); continue; }
      pending.push({ p: p, installedAt: e.installedAt || '' });
    }
    pending.sort(function (a, b) {
      return a.installedAt < b.installedAt ? -1 : (a.installedAt > b.installedAt ? 1 : 0);
    });
    for (var j = 0; j < pending.length; j++) {
      var items = pending[j].p.items;
      for (var k = 0; k < items.length; k++) {
        var it = items[k];
        if (!it || !it.key) continue;
        if (it.op === 'delete') {
          delete map[it.key];
          if (kills.indexOf(it.key) < 0) kills.push(it.key);
        } else if (it.op === 'upsert') {
          map[it.key] = it.data;  // 后装者胜；同 key 被重新 upsert 时"复活"，kills 仍记录
        }
      }
    }
    return { map: map, kills: kills, expired: expired };
  }

  /* ---------------- 消费端辅助：把覆盖视图应用到基线数组 ---------------- */
  /* arr: 内嵌基线数组（必须可原地修改——splice/下标赋值，绝不重建，保持外部引用）
   * res: buildPackMap 返回结果
   * keyOf: item -> key 字符串
   * 顺序：先按 kills 移除基线命中项，再按 map upsert（命中就地替换并去重，缺失 push） */
  function applyMapToArray(arr, res, keyOf) {
    keyOf = keyOf || function (it) { return it && it.id ? String(it.id) : ''; };
    var map = res.map || {};
    var kills = res.kills || [];
    var upserted = 0, deleted = 0;
    if (kills.length) {
      for (var i = arr.length - 1; i >= 0; i--) {
        if (kills.indexOf(keyOf(arr[i])) >= 0) { arr.splice(i, 1); deleted++; }
      }
    }
    var keys = Object.keys(map);
    if (!keys.length) return { upserted: upserted, deleted: deleted };
    var idxByKey = {};
    for (var j2 = 0; j2 < arr.length; j2++) {
      var kj = keyOf(arr[j2]);
      if (!idxByKey.hasOwnProperty(kj)) idxByKey[kj] = [];
      idxByKey[kj].push(j2);
    }
    for (var m = 0; m < keys.length; m++) {
      var mk = keys[m];
      var hit = idxByKey.hasOwnProperty(mk) ? idxByKey[mk] : null;
      if (hit && hit.length) {
        arr[hit[0]] = map[mk];
        for (var r = hit.length - 1; r >= 1; r--) arr.splice(hit[r], 1);  // 去重（保留首个位置）
      } else {
        arr.push(map[mk]);
      }
      upserted++;
    }
    return { upserted: upserted, deleted: deleted };
  }

  /* ---------------- 安装 / 移除 / 迁移 ---------------- */
  function installPack(store, pack, source, now) {
    if (!pack || pack.magic !== PACKS_MAGIC) return { ok: false, reason: 'magic' };
    if (!pack.packId || typeof pack.packId !== 'string') return { ok: false, reason: 'packId' };
    if (!pack.type) return { ok: false, reason: 'type' };
    if (!Array.isArray(pack.items)) return { ok: false, reason: 'items' };
    var idx = readIndex(store) || { packs: [] };
    var ts = (now || new Date()).toISOString();
    // 同 packId 重装 = 整包覆盖升级（删除旧索引条目再追加，保持时间序）
    idx.packs = idx.packs.filter(function (e) { return e.packId !== pack.packId; });
    idx.packs.push({
      packId: pack.packId,
      type: pack.type,
      title: pack.title || pack.packId,
      version: pack.version != null ? pack.version : 1,
      installedAt: ts,
      source: source || 'import'
    });
    try { writePackRaw(store, pack); } catch (e) { return { ok: false, reason: 'storage' }; }
    if (!writeIndex(store, idx.packs)) return { ok: false, reason: 'index' };
    return { ok: true, packId: pack.packId, installedAt: ts };
  }
  function removePack(store, packId) {
    var idx = readIndex(store);
    if (!idx) return { ok: false, reason: 'no-index' };
    var n0 = idx.packs.length;
    idx.packs = idx.packs.filter(function (e) { return e.packId !== packId; });
    if (idx.packs.length === n0) return { ok: false, reason: 'not-found' };
    try { store.removeItem(PACK_KEY_PREFIX + packId); } catch (e) {}
    writeIndex(store, idx.packs);
    return { ok: true };
  }
  /* 旧版知识覆盖层（kb_overlay_v1）→ kb-legacy 数据包（幂等，已迁移则跳过）
   * opts: { legacyKey, legacyMagic, now }；成功后删除旧键 */
  function migrateLegacyOverlay(store, opts) {
    opts = opts || {};
    var key = opts.legacyKey || 'kb_overlay_v1';
    var magic = opts.legacyMagic || 'kb-overlay-v1';
    // 幂等优先：已迁移过（无论旧键是否仍在）→ already，不再重复建包
    var idx0 = readIndex(store);
    var already0 = idx0 && idx0.packs.some(function (e) { return e.packId === 'kb-legacy'; });
    if (already0) return { ok: false, reason: 'already' };
    var raw;
    try { raw = store.getItem(key); } catch (e) { return { ok: false, reason: 'read' }; }
    if (!raw) return { ok: false, reason: 'empty' };
    var ov;
    try { ov = JSON.parse(raw); } catch (e) { return { ok: false, reason: 'corrupt' }; }
    if (!ov || ov.magic !== magic || !ov.byLib || typeof ov.byLib !== 'object') return { ok: false, reason: 'magic' };
    var items = [];
    for (var lib in ov.byLib) {
      if (!Object.prototype.hasOwnProperty.call(ov.byLib, lib)) continue;
      var arr = ov.byLib[lib];
      if (!Array.isArray(arr)) continue;
      for (var i = 0; i < arr.length; i++) {
        var e = arr[i];
        if (!e || !e.q) continue;
        items.push({ op: 'upsert', key: e.src || (lib + '-' + i), data: e });
      }
    }
    if (!items.length) return { ok: false, reason: 'empty-items' };
    var pack = {
      magic: PACKS_MAGIC,
      packId: 'kb-legacy',
      type: 'kb',
      lib: '',
      title: '旧版知识覆盖层（自动迁移）',
      version: 1,
      issuedAt: '',
      appliedUntil: '',
      items: items
    };
    var r = installPack(store, pack, 'migrate', opts.now);
    if (!r.ok) return r;
    try { store.removeItem(key); } catch (e) {}
    return { ok: true, itemCount: items.length };
  }

  var PACKS = {
    MAGIC: PACKS_MAGIC,
    INDEX_MAGIC: PACKS_INDEX_MAGIC,
    INDEX_KEY: PACKS_INDEX_KEY,
    readIndex: readIndex,
    writeIndex: writeIndex,
    readPack: readPack,
    listPacks: listPacks,
    countPackType: countPackType,
    buildPackMap: buildPackMap,
    applyMapToArray: applyMapToArray,
    installPack: installPack,
    removePack: removePack,
    migrateLegacyOverlay: migrateLegacyOverlay
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = PACKS;           // Node（单测 / 构建校验）
  }
  if (typeof window !== 'undefined') {
    window.PACKS = PACKS;             // 浏览器（qa / beauty / quiz / kb-admin）
  } else if (typeof globalThis !== 'undefined') {
    globalThis.PACKS = PACKS;
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));