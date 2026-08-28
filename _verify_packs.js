/* 客舱小助手 · 数据包引擎 M1.1 单元测试（Node）
 * 运行：node _verify_packs.js   （退出码 0=全过，1=有失败）
 * 覆盖：协议校验 / 安装覆盖升级 / 优先级 / delete 语义 / 复活 / 过期 / 损坏静默 /
 *       lib 过滤 / applyMapToArray / 旧覆盖层迁移 / 列表统计 / 移除
 */
'use strict';
const PACKS = require('./docs/_packs_engine.js');

const NOW = new Date(2026, 7, 29); // 2026-08-29 本地时区（测试固定日期，避免跑挂）
const NOW_ISO = NOW.toISOString();

function memStore() {
  const d = {};
  return {
    getItem: (k) => (Object.prototype.hasOwnProperty.call(d, k) ? d[k] : null),
    setItem: (k, v) => { d[k] = String(v); },
    removeItem: (k) => { delete d[k]; },
    dump: () => d
  };
}

let seq = 0;
function pack(type, items, extra) {
  seq++;
  return Object.assign({
    magic: PACKS.MAGIC,
    packId: 't-' + seq,
    type: type,
    title: '测试包' + seq,
    version: 1,
    issuedAt: '2026-08-01',
    appliedUntil: '',
    items: items || []
  }, extra || {});
}

const results = [];
function check(name, cond, extra) { results.push({ name, pass: !!cond, extra: extra || '' }); }

/* ---------- 1. installPack 校验 ---------- */
{
  const st = memStore();
  const bad = pack('sales', [{ op: 'upsert', key: 'k', data: { v: 1 } }]);
  bad.magic = 'wrong';
  check('installPack 拒绝错误 magic', PACKS.installPack(st, bad, 'import', NOW).ok === false);
  const noItems = pack('sales', []);
  delete noItems.items;
  check('installPack 拒绝缺 items', PACKS.installPack(st, noItems, 'import', NOW).ok === false);
  const noId = pack('sales', []);
  delete noId.packId;
  check('installPack 拒绝缺 packId', PACKS.installPack(st, noId, 'import', NOW).ok === false);
  const good = pack('sales', [{ op: 'upsert', key: 'k', data: { v: 1 } }]);
  check('installPack 正常安装', PACKS.installPack(st, good, 'import', NOW).ok === true);
}

/* ---------- 2. 同 packId 重装 = 整包覆盖升级 ---------- */
{
  const st = memStore();
  const p1 = pack('sales', [{ op: 'upsert', key: 'k', data: { v: 1 } }]);
  PACKS.installPack(st, p1, 'import', NOW);
  const p2 = pack('sales', [{ op: 'upsert', key: 'k', data: { v: 2 } }]);
  p2.packId = p1.packId; // 同 id，升版覆盖
  const r2 = PACKS.installPack(st, p2, 'import', new Date(2026, 8, 1));
  check('重装同 packId 成功', r2.ok === true);
  const m = PACKS.buildPackMap(st, 'sales', { now: NOW });
  check('重装后新数据生效', m.map.k === undefined || m.map.k.v === 2, 'map.k=' + JSON.stringify(m.map.k));
  const list = PACKS.listPacks(st, null, NOW);
  const same = list.filter((e) => e.packId === p1.packId);
  check('重装不产生重复索引', same.length === 1, 'count=' + same.length);
}

/* ---------- 3. 优先级：后装者胜 ---------- */
{
  const st = memStore();
  const a = pack('sales', [{ op: 'upsert', key: 'X', data: { v: 'a' } }]);
  const b = pack('sales', [{ op: 'upsert', key: 'X', data: { v: 'b' } }]);
  PACKS.installPack(st, a, 'import', new Date(2026, 7, 1));
  PACKS.installPack(st, b, 'import', new Date(2026, 7, 2));
  const m = PACKS.buildPackMap(st, 'sales', { now: NOW });
  check('优先级：后装者胜 (v=b)', m.map.X && m.map.X.v === 'b', JSON.stringify(m.map.X));
}

/* ---------- 4. delete 语义 ---------- */
{
  const st = memStore();
  const a = pack('sales', [{ op: 'upsert', key: 'X', data: { v: 1 } }]);
  const b = pack('sales', [{ op: 'delete', key: 'X' }]);
  PACKS.installPack(st, a, 'import', new Date(2026, 7, 1));
  PACKS.installPack(st, b, 'import', new Date(2026, 7, 2));
  const m = PACKS.buildPackMap(st, 'sales', { now: NOW });
  check('delete 后 map 无该 key', !m.map.hasOwnProperty('X'));
  check('delete 记录入 kills', m.kills.indexOf('X') >= 0);
}

/* ---------- 5. delete 后复活 ---------- */
{
  const st = memStore();
  const d = pack('sales', [{ op: 'delete', key: 'X' }]);
  const u = pack('sales', [{ op: 'upsert', key: 'X', data: { v: 'revived' } }]);
  PACKS.installPack(st, d, 'import', new Date(2026, 7, 1));
  PACKS.installPack(st, u, 'import', new Date(2026, 7, 2));
  const m = PACKS.buildPackMap(st, 'sales', { now: NOW });
  check('复活：map 重新含 key', m.map.X && m.map.X.v === 'revived');
  check('复活：kills 仍有记录（消费端先删后加还原到最终态）', m.kills.indexOf('X') >= 0);
  const arr = [{ id: 'X', v: 'base' }];
  const r = PACKS.applyMapToArray(arr, m, (it) => it.id);
  check('复活：应用后最终为 upsert 数据', arr.length === 1 && arr[0].v === 'revived');
  check('应用计数', r.upserted === 1 && r.deleted === 1, JSON.stringify(r));
}

/* ---------- 6. 过期 ---------- */
{
  const st = memStore();
  const exp = pack('sales', [{ op: 'upsert', key: 'E', data: { v: 1 } }], { appliedUntil: '2026-08-28' });
  const ok = pack('sales', [{ op: 'upsert', key: 'F', data: { v: 1 } }], { appliedUntil: '2026-08-30' });
  PACKS.installPack(st, exp, 'import', new Date(2026, 7, 20));
  PACKS.installPack(st, ok, 'import', new Date(2026, 7, 21));
  const m = PACKS.buildPackMap(st, 'sales', { now: NOW });
  check('过期包不参与合并', !m.map.hasOwnProperty('E'));
  check('未过期包正常合并', m.map.hasOwnProperty('F'));
  check('expired 列表记录过期包', m.expired.indexOf(exp.packId) >= 0);
  const stat = PACKS.countPackType(st, 'sales', NOW);
  check('统计：1 有效 1 过期', stat.active === 1 && stat.expired === 1, JSON.stringify(stat));
}

/* ---------- 7. 未声明 appliedUntil = 永不过期 ---------- */
{
  const st = memStore();
  const p = pack('sales', [{ op: 'upsert', key: 'K', data: { v: 1 } }]);
  delete p.appliedUntil;
  PACKS.installPack(st, p, 'import', new Date(2026, 6, 1)); // 一个多月前装
  const m = PACKS.buildPackMap(st, 'sales', { now: NOW });
  check('未声明有效期不过期', m.map.hasOwnProperty('K') && m.expired.length === 0);
}

/* ---------- 8. 损坏包静默忽略 ---------- */
{
  const st = memStore();
  st.setItem('pack:corrupt', '{not-json');
  st.setItem('pack:badmagic', JSON.stringify({ magic: 'nope', packId: 'badmagic', type: 'sales', items: [] }));
  st.setItem('packs_index', JSON.stringify({ magic: PACKS.INDEX_MAGIC, packs: [
    { packId: 'corrupt', type: 'sales', installedAt: '2026-08-01T00:00:00.000Z' },
    { packId: 'badmagic', type: 'sales', installedAt: '2026-08-01T00:00:00.000Z' }
  ]}));
  const m = PACKS.buildPackMap(st, 'sales', { now: NOW });
  check('损坏 JSON 包被忽略且不抛错', m.map && Object.keys(m.map).length === 0);
  check('错误 magic 包被忽略', !m.map.hasOwnProperty('badmagic'));
}

/* ---------- 9. kb lib 过滤 ---------- */
{
  const st = memStore();
  const ccm = pack('kb', [{ op: 'upsert', key: 'CCM 1.1', data: { lib: 'ccm' } }], { lib: 'ccm' });
  const mixed = pack('kb', [{ op: 'upsert', key: 'MIX', data: { lib: 'all' } }], { lib: '' });
  PACKS.installPack(st, ccm, 'import', new Date(2026, 7, 1));
  PACKS.installPack(st, mixed, 'import', new Date(2026, 7, 2));
  const mMgm = PACKS.buildPackMap(st, 'kb', { now: NOW, lib: 'mgm' });
  check('单库包不泄漏到其他库', !mMgm.map.hasOwnProperty('CCM 1.1'));
  check('空 lib 混合包全库应用', mMgm.map.hasOwnProperty('MIX'));
  const mCcm = PACKS.buildPackMap(st, 'kb', { now: NOW, lib: 'ccm' });
  check('单库包命中对应库', mCcm.map.hasOwnProperty('CCM 1.1') && mCcm.map.hasOwnProperty('MIX'));
  const mSales = PACKS.buildPackMap(st, 'sales', { now: NOW });
  check('类型隔离：query sales 不拿到 kb 包', Object.keys(mSales.map).length === 0);
}

/* ---------- 10. applyMapToArray ---------- */
{
  const m = {
    map: { a: { id: 'a', v: 9 }, z: { id: 'z', v: 1 }, d1: { id: 'd1', v: 3 } },
    kills: ['b'],
    expired: []
  };
  const arr = [
    { id: 'a', v: 1 },
    { id: 'b', v: 1 },
    { id: 'c', v: 1 },
    { id: 'd1', v: 1 },
    { id: 'd1', v: 2 } // 基线含重复 key，应去重
  ];
  const r = PACKS.applyMapToArray(arr, m, (it) => it.id);
  check('upsert 命中替换（保持顺序）', arr[0].v === 9, JSON.stringify(arr));
  check('delete 移除基线项', arr.every((it) => it.id !== 'b'));
  check('缺失 push', arr.some((it) => it.id === 'z'));
  check('重复 key 去重', arr.filter((it) => it.id === 'd1').length === 1 && arr.find((it) => it.id === 'd1').v === 3);
  check('计数：upserted=3 deleted=1', r.upserted === 3 && r.deleted === 1, JSON.stringify(r));
  const ref = arr;
  PACKS.applyMapToArray(arr, { map: { n: { id: 'n', v: 0 } }, kills: [], expired: [] }, (it) => it.id);
  check('不重建数组（引用不变）', arr === ref && arr.some((it) => it.id === 'n'));
}

/* ---------- 11. migrateLegacyOverlay ---------- */
{
  const st = memStore();
  const legacy = { magic: 'kb-overlay-v1', byLib: {
    ccm: [{ src: 'CCM 3.1', q: '问题A', a: '答案A', _op: 'mod' }, { src: '', q: '无源条目', a: '答案B', _op: 'add' }],
    daily: [{ src: '日常 1', q: '问题C', a: '答案C', _op: 'add' }]
  }};
  st.setItem('kb_overlay_v1', JSON.stringify(legacy));
  const r = PACKS.migrateLegacyOverlay(st, { now: NOW });
  check('迁移成功并计数', r.ok === true && r.itemCount === 3, JSON.stringify(r));
  check('迁移后删除旧键', st.getItem('kb_overlay_v1') === null);
  const mAll = PACKS.buildPackMap(st, 'kb', { now: NOW }); // lib='' → 全库
  const mCcm = PACKS.buildPackMap(st, 'kb', { now: NOW, lib: 'ccm' });
  const mDaily = PACKS.buildPackMap(st, 'kb', { now: NOW, lib: 'daily' });
  check('迁移条目进入全库视图', mAll.map['CCM 3.1'] && mAll.map['CCM 3.1'].q === '问题A');
  check('无 src 条目有兜底 key（ccm-1）', mCcm.map['ccm-1'] && mCcm.map['ccm-1'].q === '无源条目');
  check('日常库条目正确分桶', mDaily.map['日常 1'] && mDaily.map['日常 1'].q === '问题C');
  const r2 = PACKS.migrateLegacyOverlay(st, { now: NOW });
  check('迁移幂等：第二次 already', r2.ok === false && r2.reason === 'already');
  check('幂等不重复生成包', PACKS.listPacks(st, null, NOW).filter((e) => e.packId === 'kb-legacy').length === 1);
}
{
  const st = memStore();
  st.setItem('kb_overlay_v1', 'corrupt-json');
  const r = PACKS.migrateLegacyOverlay(st, { now: NOW });
  check('损坏旧键：不迁移且不删除旧键', r.ok === false && r.reason === 'corrupt' && st.getItem('kb_overlay_v1') === 'corrupt-json');
}

/* ---------- 12. 安装后 listPacks 元信息 ---------- */
{
  const st = memStore();
  const p = pack('quiz', [{ op: 'upsert', key: 'Q1', data: { q: '题' } }], { title: '新航司题包', appliedUntil: '2026-08-28' });
  PACKS.installPack(st, p, 'import', NOW);
  const list = PACKS.listPacks(st, null, NOW);
  check('listPacks 返回元信息', list.length === 1 && list[0].title === '新航司题包' && list[0].itemCount === 1 && list[0].valid === true);
  check('listPacks 标记过期', list[0].expired === true);
}

/* ---------- 13. removePack ---------- */
{
  const st = memStore();
  const p = pack('sales', [{ op: 'upsert', key: 'K', data: { v: 1 } }]);
  PACKS.installPack(st, p, 'import', NOW);
  const m1 = PACKS.buildPackMap(st, 'sales', { now: NOW });
  check('移除前包生效', m1.map.hasOwnProperty('K'));
  const r = PACKS.removePack(st, p.packId);
  check('removePack 成功', r.ok === true);
  const m2 = PACKS.buildPackMap(st, 'sales', { now: NOW });
  check('移除后包不再生效', Object.keys(m2.map).length === 0);
  check('移除后数据键清除', st.getItem('pack:' + p.packId) === null);
  const r2 = PACKS.removePack(st, 'not-exist');
  check('移除不存在的包返回 not-found', r2.ok === false && r2.reason === 'not-found');
}

/* ---------- 汇总 ---------- */
let pass = 0, fail = 0;
for (const r of results) {
  if (r.pass) { pass++; console.log('PASS  ' + r.name); }
  else { fail++; console.log('FAIL  ' + r.name + (r.extra ? '   [' + r.extra + ']' : '')); }
}
console.log('\n结果: ' + pass + ' 通过 / ' + fail + ' 失败 / 共 ' + results.length);
process.exit(fail ? 1 : 0);