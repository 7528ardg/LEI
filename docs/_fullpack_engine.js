/* =============================================================================
 * 客舱小助手 · 全量数据包引擎 v1（库管理 · 导出/导入/一致性校验）
 * -----------------------------------------------------------------------------
 * 目的：把「库管理」中集中展示的全部数据源（六库 + 销售话术库 + 产品库）
 *       导出为一个自描述、可校验、可完整还原的数据包；
 *       导入时验证「能被正确识别」并「完整还原」，给出逐源逐条的一致性报告。
 *
 * 设计要点：
 *   1. 稳定 uid：条目在包内的唯一身份。
 *        kb 类（日常/ccm/mgm/svc/大撤/CBT） = 「源id#基线序号」
 *        script（销售话术）                 = 「源id#栏目key/脚本id」
 *        product（产品）                    = 「源id#产品id」
 *      编辑层与导入均按 uid 定位，保证「改哪一条就是哪一条」。
 *   2. 指纹 fp：条目做「键排序的稳定序列化」后 FNV-1a-32 哈希，
 *      导入时逐条复算比对 —— 校验的是内容而非只看条数。
 *   3. checksum：源级 = 该源全部 fp 序列再哈希；包级 = 全部源 checksum 再哈希。
 *      任一条被篡改/丢失/错位，校验必然失败。
 *   4. 零 DOM：浏览器挂 window.FULLPACK，Node 挂 module.exports，
 *      构建期校验脚本与运行时复用同一份逻辑（避免两套实现漂移）。
 *
 * 包结构：
 *   {
 *     magic:'cabin-fullpack-v1', kind:'full',
 *     packId, title, version, exportedAt, app, builder,
 *     sources:[ { id, kind, name, origin, count, checksum,
 *                 items:[ { uid, fp, data } ] } ],
 *     summary:{ sources:N, items:N, checksum:'...' }
 *   }
 *
 * 本文件由 _sync_fullpack.py 注入各模块；改这里后必须重跑 python _sync_fullpack.py。
 * ============================================================================= */
(function (global) {
  'use strict';

  var MAGIC = 'cabin-fullpack-v1';
  var EDIT_MAGIC = 'cabin-console-edit-v1';
  var KIND_KB = 'kb';
  var KIND_SCRIPT = 'script';
  var KIND_PRODUCT = 'product';
  var KINDS = [KIND_KB, KIND_SCRIPT, KIND_PRODUCT];
  var META_KEY = '_uid';   // 写进 data 的元字段：让导入后 uid 依旧稳定

  /* ---------------- 稳定序列化（键排序，跨环境可复现） ---------------- */
  function stableStringify(v) {
    if (v === null || v === undefined) return 'null';
    var t = typeof v;
    if (t === 'number') return isFinite(v) ? String(v) : 'null';
    if (t === 'boolean' || t === 'string') return JSON.stringify(v);
    if (Array.isArray(v)) {
      var out = [];
      for (var i = 0; i < v.length; i++) out.push(stableStringify(v[i]));
      return '[' + out.join(',') + ']';
    }
    if (t === 'object') {
      var keys = Object.keys(v).sort();
      var parts = [];
      for (var k = 0; k < keys.length; k++) {
        var val = v[keys[k]];
        if (val === undefined) continue;
        parts.push(JSON.stringify(keys[k]) + ':' + stableStringify(val));
      }
      return '{' + parts.join(',') + '}';
    }
    return 'null';
  }

  /* ---------------- FNV-1a 32bit（对 UTF-16 code unit，Node/浏览器一致） ---------------- */
  function hashStr(s) {
    var h = 0x811c9dc5;
    for (var i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
    }
    return ('00000000' + h.toString(16)).slice(-8);
  }
  function fingerprint(v) { return hashStr(stableStringify(v)); }

  /* ---------------- 稳定 uid ---------------- */
  function makeUid(src, item, index) {
    var id = src && src.id ? String(src.id) : 'src';
    var kind = src && src.kind ? src.kind : KIND_KB;
    if (kind === KIND_SCRIPT) {
      var cat = (item && (item.__cat || item.catKey)) ? String(item.__cat || item.catKey) : '_';
      var sid = (item && item.id != null) ? String(item.id) : String(index);
      return id + '#' + cat + '/' + sid;
    }
    if (kind === KIND_PRODUCT) {
      return id + '#' + ((item && item.id != null) ? String(item.id) : String(index));
    }
    return id + '#' + index;
  }

  /* ---------------- 条目规范化（挂 uid 元字段，导出/编辑统一形态） ---------------- */
  function normalizeItem(src, item, index) {
    var data = {};
    var k;
    for (k in item) { if (Object.prototype.hasOwnProperty.call(item, k)) data[k] = item[k]; }
    var uid = (item && item[META_KEY]) ? String(item[META_KEY]) : makeUid(src, item, index);
    data[META_KEY] = uid;
    return { uid: uid, fp: fingerprint(data), data: data };
  }

  /* 给基线数组固化 uid（幂等）。
     必须在「任何编辑发生之前」做一次：kb 类条目的 uid 由基线序号生成，
     若等到工作区已删/增过条目再按当前下标生成，uid 会整体错位一格，
     导致「改 A 条却写到了 B 条」。固化后 uid 终身不变，与位置无关。 */
  function stampUids(items, src) {
    items = Array.isArray(items) ? items : [];
    for (var i = 0; i < items.length; i++) {
      if (items[i] && typeof items[i] === 'object' && !items[i][META_KEY]) {
        items[i][META_KEY] = makeUid(src, items[i], i);
      }
    }
    return items;
  }

  /* 去掉 uid 元字段后的副本：用于「内容是否真的变了」的比较。
     导入一个未改动的导出包时，条目只多了 _uid，不应被记成「已修改」。 */
  function stripMeta(o) {
    if (!o || typeof o !== 'object') return o;
    if (Array.isArray(o)) return o.map(stripMeta);
    var c = {}, k;
    for (k in o) { if (k === META_KEY) continue; if (Object.prototype.hasOwnProperty.call(o, k)) c[k] = o[k]; }
    return c;
  }

  /* =========================================================================
   * 导出：构建全量数据包
   * sources: [ { id, name, kind, origin, items:[...] } ]
   * opts: { packId, title, version, exportedAt }
   * ========================================================================= */
  function buildFullPack(sources, opts) {
    opts = opts || {};
    if (!Array.isArray(sources)) throw new Error('sources 必须是数组');
    var outSources = [];
    var total = 0;
    var srcSums = [];
    for (var i = 0; i < sources.length; i++) {
      var s = sources[i] || {};
      var kind = s.kind || KIND_KB;
      if (KINDS.indexOf(kind) < 0) throw new Error('未知数据源 kind：' + kind);
      var items = Array.isArray(s.items) ? s.items : [];
      var norm = [];
      var fps = [];
      for (var j = 0; j < items.length; j++) {
        var n = normalizeItem(s, items[j], j);
        norm.push(n);
        fps.push(n.uid + ':' + n.fp);
        total++;
      }
      var checksum = hashStr(fps.join('|'));
      srcSums.push(String(s.id) + ':' + checksum);
      outSources.push({
        id: String(s.id),
        kind: kind,
        name: s.name || String(s.id),
        origin: s.origin || '',
        count: norm.length,
        checksum: checksum,
        items: norm
      });
    }
    var pack = {
      magic: MAGIC,
      kind: 'full',
      packId: opts.packId || ('full-' + (opts.exportedAt ? String(opts.exportedAt).slice(0, 10) : 'x')),
      title: opts.title || '库管理完整数据包',
      version: opts.version != null ? opts.version : 1,
      exportedAt: opts.exportedAt || new Date().toISOString(),
      app: '客舱小助手',
      builder: 'kb-admin·库管理',
      sources: outSources,
      summary: { sources: outSources.length, items: total, checksum: hashStr(srcSums.join('|')) }
    };
    return pack;
  }

  /* =========================================================================
   * 校验：包能否被正确识别且内容自洽
   * 返回 { ok, errors:[], warnings:[], stats:{sources,items,bySource:[]} }
   * ========================================================================= */
  function verifyPack(pack, opts) {
    opts = opts || {};
    var errors = [], warnings = [], bySource = [];
    if (!pack || typeof pack !== 'object') return { ok: false, errors: ['不是合法的 JSON 对象'], warnings: warnings, stats: null };
    if (pack.magic !== MAGIC) {
      // 兼容旧增量包协议：不是全量包就明确告知，避免"导入了但没还原"
      if (pack.magic === 'cabin-data-pack-v1') errors.push('这是旧版增量数据包（cabin-data-pack-v1），请在「📦 数据包」页导入；完整全量包 magic 应为 ' + MAGIC);
      else errors.push('magic 标识不符（期望 ' + MAGIC + '，实际 ' + String(pack.magic) + '）');
      return { ok: false, errors: errors, warnings: warnings, stats: null };
    }
    if (pack.kind && pack.kind !== 'full') warnings.push('kind 为 ' + pack.kind + '（期望 full），已按全量包解析');
    if (!Array.isArray(pack.sources)) { errors.push('缺少 sources 数组'); return { ok: false, errors: errors, warnings: warnings, stats: null }; }
    if (!pack.sources.length) errors.push('包内没有任何数据源');

    var total = 0, sums = [];
    for (var i = 0; i < pack.sources.length; i++) {
      var s = pack.sources[i] || {};
      var sid = String(s.id || ('#' + i));
      if (KINDS.indexOf(s.kind) < 0) warnings.push('数据源 ' + sid + ' 的 kind 未知（' + String(s.kind) + '），按 kb 处理');
      if (!Array.isArray(s.items)) { errors.push('数据源 ' + sid + ' 缺少 items 数组'); continue; }
      var fps = [], badFp = 0, badUid = 0;
      for (var j = 0; j < s.items.length; j++) {
        var it = s.items[j] || {};
        if (!it.uid) { badUid++; continue; }
        var fp = fingerprint(it.data);
        fps.push(it.uid + ':' + fp);
        if (it.fp && it.fp !== fp) badFp++;
      }
      if (badUid) errors.push('数据源 ' + sid + ' 有 ' + badUid + ' 条缺少 uid');
      if (badFp) errors.push('数据源 ' + sid + ' 有 ' + badFp + ' 条指纹与内容不符（内容被改动或传输损坏）');
      var checksum = hashStr(fps.join('|'));
      if (s.checksum && s.checksum !== checksum) errors.push('数据源 ' + sid + ' 校验和不一致（期望 ' + s.checksum + '，实算 ' + checksum + '）');
      if (s.count != null && s.count !== s.items.length) errors.push('数据源 ' + sid + ' 声明 ' + s.count + ' 条，实际 ' + s.items.length + ' 条');
      sums.push(sid + ':' + checksum);
      total += s.items.length;
      bySource.push({ id: sid, kind: s.kind, name: s.name || sid, count: s.items.length, checksum: checksum, fpMismatch: badFp });
    }
    var sum = hashStr(sums.join('|'));
    if (pack.summary) {
      if (pack.summary.items != null && pack.summary.items !== total) errors.push('包级声明 ' + pack.summary.items + ' 条，实际合计 ' + total + ' 条');
      if (pack.summary.checksum && pack.summary.checksum !== sum) errors.push('包级校验和不一致（期望 ' + pack.summary.checksum + '，实算 ' + sum + '）');
    } else {
      warnings.push('包内缺少 summary 段，已按各源校验和复核');
    }
    if (opts.expectSources) {
      for (var e = 0; e < opts.expectSources.length; e++) {
        var want = opts.expectSources[e];
        var hit = false;
        for (var b = 0; b < bySource.length; b++) if (bySource[b].id === want) { hit = true; break; }
        if (!hit) warnings.push('缺少数据源 ' + want + '（本包不完整）');
      }
    }
    return {
      ok: errors.length === 0,
      errors: errors,
      warnings: warnings,
      stats: { sources: bySource.length, items: total, checksum: sum, bySource: bySource }
    };
  }

  /* =========================================================================
   * 还原：把包内数据应用到当前工作区
   * mode: 'replace' 整包还原（目标源内条目 = 包内条目）
   *       'merge'   按 uid 合并（命中的覆盖，缺失的追加，不删现有）
   * current: { sourceId: [items] }（可选，merge 时作为基线与统计基准）
   * 返回 { ok, state:{sourceId:[items]}, report:[...] }
   * ========================================================================= */
  function applyFullPack(pack, opts) {
    opts = opts || {};
    var mode = opts.mode === 'merge' ? 'merge' : 'replace';
    var current = opts.current || {};
    var v = verifyPack(pack);
    var state = {}, report = [];
    if (!pack || !Array.isArray(pack.sources)) return { ok: false, errors: ['包结构不可用'], state: state, report: report, verify: v };

    for (var i = 0; i < pack.sources.length; i++) {
      var s = pack.sources[i] || {};
      var sid = String(s.id || ('#' + i));
      var packItems = [];
      var items = Array.isArray(s.items) ? s.items : [];
      for (var j = 0; j < items.length; j++) {
        var it = items[j] || {};
        if (!it.data) continue;
        packItems.push(it.data);
      }
      var base = Array.isArray(current[sid]) ? current[sid] : [];
      var out;
      var matched = 0, added = 0, updated = 0, removed = 0, fpMismatch = 0;
      if (mode === 'replace') {
        out = packItems;
        var baseByUid = {};
        for (var b = 0; b < base.length; b++) {
          var bu = (base[b] && base[b][META_KEY]) ? String(base[b][META_KEY]) : makeUid(s, base[b], b);
          if (!baseByUid.hasOwnProperty(bu)) baseByUid[bu] = true;
        }
        for (var p = 0; p < packItems.length; p++) {
          var pu = String(packItems[p][META_KEY] || '');
          if (baseByUid[pu]) { matched++; updated++; } else { added++; }
        }
        removed = Math.max(0, base.length - matched);
      } else {
        out = [];
        var idxByUid = {}, packByUid = {};
        for (var q = 0; q < base.length; q++) {
          var qu = (base[q] && base[q][META_KEY]) ? String(base[q][META_KEY]) : makeUid(s, base[q], q);
          if (!idxByUid.hasOwnProperty(qu)) idxByUid[qu] = [];
          idxByUid[qu].push(q);
        }
        for (var r = 0; r < packItems.length; r++) {
          var ru = String(packItems[r][META_KEY] || '');
          if (packByUid.hasOwnProperty(ru)) continue;
          packByUid[ru] = packItems[r];
        }
        for (var t = 0; t < base.length; t++) {
          var tu = (base[t] && base[t][META_KEY]) ? String(base[t][META_KEY]) : makeUid(s, base[t], t);
          if (packByUid.hasOwnProperty(tu)) {
            var pd = packByUid[tu];
            if (stableStringify(pd) !== stableStringify(base[t])) { updated++; } else { matched++; }
            out.push(pd);
          } else { out.push(base[t]); }
        }
        var keys = Object.keys(packByUid);
        for (var k = 0; k < keys.length; k++) {
          if (!idxByUid.hasOwnProperty(keys[k])) { out.push(packByUid[keys[k]]); added++; }
        }
      }
      // 逐条复算指纹，确认还原内容未被损坏
      for (var z = 0; z < out.length; z++) {
        var srcIt = null;
        for (var y = 0; y < items.length; y++) {
          if (items[y] && items[y].data && String(items[y].data[META_KEY] || '') === String(out[z][META_KEY] || '')) { srcIt = items[y]; break; }
        }
        if (srcIt && srcIt.fp && srcIt.fp !== fingerprint(out[z])) fpMismatch++;
      }
      state[sid] = out;
      report.push({
        id: sid, name: s.name || sid, kind: s.kind,
        packCount: items.length, outCount: out.length, baseCount: base.length,
        matched: matched, updated: updated, added: added, removed: removed,
        fpMismatch: fpMismatch,
        ok: (out.length === items.length) && fpMismatch === 0
      });
    }
    var okAll = v.ok;
    for (var g = 0; g < report.length; g++) if (!report[g].ok) okAll = false;
    return { ok: okAll, errors: v.errors, warnings: v.warnings, state: state, report: report, verify: v };
  }

  /* =========================================================================
   * 编辑层：库管理里人工改动的持久化
   *   edits = { mod:{ uid: data }, del:[uid], add:[ {uid,data} ] }
   * ========================================================================= */
  function emptyEdits() { return { mod: {}, del: [], add: [] }; }
  function editStats(edits) {
    edits = edits || emptyEdits();
    var mod = edits.mod ? Object.keys(edits.mod).length : 0;
    var del = Array.isArray(edits.del) ? edits.del.length : 0;
    var add = Array.isArray(edits.add) ? edits.add.length : 0;
    return { mod: mod, del: del, add: add, total: mod + del + add };
  }
  /* 把编辑层应用到基线数组，得到「工作区条目」 */
  function applyEdits(baseItems, edits, src) {
    baseItems = Array.isArray(baseItems) ? baseItems : [];
    edits = edits || emptyEdits();
    var mod = edits.mod || {}, del = Array.isArray(edits.del) ? edits.del : [], add = Array.isArray(edits.add) ? edits.add : [];
    var out = [];
    for (var i = 0; i < baseItems.length; i++) {
      var it = baseItems[i];
      var uid = (it && it[META_KEY]) ? String(it[META_KEY]) : makeUid(src || { id: 'x', kind: KIND_KB }, it, i);
      if (del.indexOf(uid) >= 0) continue;
      if (Object.prototype.hasOwnProperty.call(mod, uid)) { out.push(mod[uid]); continue; }
      out.push(it);
    }
    for (var a = 0; a < add.length; a++) {
      if (add[a] && add[a].data) out.push(add[a].data);
      else if (add[a]) out.push(add[a]);
    }
    return out;
  }

  /* 把「目标条目集合」相对「基线」的差异转成编辑层 —— 导入完整包后用它落盘，
     使工作区 == 包内数据，而基线仍保持内嵌原值（不改动源文件即可完成还原）。 */
  function diffToEdits(baseItems, targetItems, src) {
    baseItems = Array.isArray(baseItems) ? baseItems : [];
    targetItems = Array.isArray(targetItems) ? targetItems : [];
    var e = emptyEdits();
    var baseByUid = {}, baseUids = {};
    for (var i = 0; i < baseItems.length; i++) {
      var bu = (baseItems[i] && baseItems[i][META_KEY]) ? String(baseItems[i][META_KEY]) : makeUid(src || { id: 'x', kind: KIND_KB }, baseItems[i], i);
      if (!baseByUid.hasOwnProperty(bu)) { baseByUid[bu] = baseItems[i]; baseUids[bu] = true; }
    }
    var targetUids = {};
    for (var j = 0; j < targetItems.length; j++) {
      var t = targetItems[j];
      if (!t) continue;
      var tu = (t && t[META_KEY]) ? String(t[META_KEY]) : makeUid(src || { id: 'x', kind: KIND_KB }, t, j);
      if (targetUids.hasOwnProperty(tu)) continue;   // 包内重复 uid：保留首条
      targetUids[tu] = true;
      if (baseByUid.hasOwnProperty(tu)) {
        // 只多/少了 _uid 元字段不算内容改动（否则导入一份未改动的包会把全库标成「已改」）
        if (stableStringify(stripMeta(baseByUid[tu])) !== stableStringify(stripMeta(t))) e.mod[tu] = t;
      } else {
        e.add.push({ uid: tu, data: t });
      }
    }
    var bu2 = Object.keys(baseUids);
    for (var k = 0; k < bu2.length; k++) {
      if (!targetUids.hasOwnProperty(bu2[k])) e.del.push(bu2[k]);
    }
    return e;
  }

  /* 合并两个编辑层（b 覆盖 a）：用于「导入 → 落盘」时保留未涉及源的改动 */
  function mergeEdits(a, b) {
    var out = emptyEdits();
    a = a || emptyEdits(); b = b || emptyEdits();
    var k;
    for (k in a.mod) { if (Object.prototype.hasOwnProperty.call(a.mod, k)) out.mod[k] = a.mod[k]; }
    for (k in b.mod) { if (Object.prototype.hasOwnProperty.call(b.mod, k)) out.mod[k] = b.mod[k]; }
    var del = {};
    (a.del || []).forEach(function (u) { del[u] = true; });
    (b.del || []).forEach(function (u) { del[u] = true; });
    out.del = Object.keys(del);
    var seenAdd = {};
    (a.add || []).forEach(function (it) { seenAdd[String(it.uid)] = it; });
    (b.add || []).forEach(function (it) { seenAdd[String(it.uid)] = it; });
    out.add = Object.keys(seenAdd).map(function (u) { return seenAdd[u]; });
    return out;
  }

  /* =========================================================================
   * 往返自检（导出 → 校验 → 还原 → 逐条深比对）
   * 不依赖文件 IO，纯内存跑一遍，用于「导入后能被完整还原」的强断言
   * ========================================================================= */
  function roundTripCheck(sources, opts) {
    opts = opts || {};
    var t0 = (typeof Date !== 'undefined') ? Date.now() : 0;
    var pack = buildFullPack(sources, { exportedAt: opts.exportedAt || new Date().toISOString(), title: '往返自检包' });
    var v = verifyPack(pack);
    if (!v.ok) {
      return { ok: false, phase: 'verify', errors: v.errors, warnings: v.warnings, perSource: [], pack: pack };
    }
    var current = opts.current || {};
    var ap = applyFullPack(pack, { mode: 'replace', current: current });
    var perSource = [];
    for (var i = 0; i < sources.length; i++) {
      var s = sources[i];
      var sid = String(s.id);
      var origin = Array.isArray(s.items) ? s.items : [];
      var restored = ap.state[sid] || [];
      var diffs = [];
      var len = Math.max(origin.length, restored.length);
      for (var j = 0; j < len; j++) {
        var a = origin[j], b = restored[j];
        if (a === undefined) { diffs.push({ index: j, uid: (b && b[META_KEY]) || '', why: '多出条目' }); continue; }
        if (b === undefined) { diffs.push({ index: j, uid: (a && a[META_KEY]) || '', why: '缺少条目' }); continue; }
        var ua = (a && a[META_KEY]) ? String(a[META_KEY]) : makeUid(s, a, j);
        var ub = (b && b[META_KEY]) ? String(b[META_KEY]) : '';
        if (ua !== ub) { diffs.push({ index: j, uid: ua, why: 'uid 不一致：' + ua + ' vs ' + ub }); continue; }
        // 比内容：基线原始条目 + uid 元字段  ==  还原条目
        var expect = {};
        for (var k in a) { if (Object.prototype.hasOwnProperty.call(a, k)) expect[k] = a[k]; }
        expect[META_KEY] = ua;
        if (stableStringify(expect) !== stableStringify(b)) diffs.push({ index: j, uid: ua, why: '内容不一致' });
      }
      perSource.push({
        id: sid, name: s.name || sid,
        srcCount: origin.length, outCount: restored.length,
        same: origin.length === restored.length && diffs.length === 0,
        diffCount: diffs.length, diffs: diffs.slice(0, 10),
        fpMismatch: (ap.report[i] && ap.report[i].fpMismatch) || 0
      });
    }
    var ok = true;
    for (var p = 0; p < perSource.length; p++) if (!perSource[p].same) ok = false;
    var t1 = (typeof Date !== 'undefined') ? Date.now() : 0;
    return {
      ok: ok, phase: ok ? 'done' : 'compare',
      errors: [], warnings: v.warnings,
      perSource: perSource,
      report: ap.report,
      stats: { sources: perSource.length, items: v.stats ? v.stats.items : 0, ms: t1 - t0 },
      pack: opts.keepPack ? pack : undefined
    };
  }

  var FULLPACK = {
    MAGIC: MAGIC,
    EDIT_MAGIC: EDIT_MAGIC,
    META_KEY: META_KEY,
    KINDS: KINDS,
    stableStringify: stableStringify,
    stripMeta: stripMeta,
    hashStr: hashStr,
    fingerprint: fingerprint,
    makeUid: makeUid,
    stampUids: stampUids,
    normalizeItem: normalizeItem,
    buildFullPack: buildFullPack,
    verifyPack: verifyPack,
    applyFullPack: applyFullPack,
    emptyEdits: emptyEdits,
    editStats: editStats,
    applyEdits: applyEdits,
    diffToEdits: diffToEdits,
    mergeEdits: mergeEdits,
    roundTripCheck: roundTripCheck
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = FULLPACK;
  if (typeof window !== 'undefined') window.FULLPACK = FULLPACK;
  else if (typeof globalThis !== 'undefined') globalThis.FULLPACK = FULLPACK;
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
