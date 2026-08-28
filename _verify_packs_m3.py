# -*- coding: utf-8 -*-
"""客舱小助手 · M3 发布管线验证（Python）
1) 协议校验 / sales 合规拦截 / sha256 / manifest 合并 / 版本保护（覆盖模块级常量走临时目录，不污染仓库）
2) 产物由 Node 子进程用数据包引擎做客户端消费互操作（manifest→computePackUpdates→installPack→读回）
运行：python _verify_packs_m3.py
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
import _build_packs_release as rel

results = []


def check(name, cond, extra=''):
    results.append((name, bool(cond), extra))


PACK_GOOD = {
    'magic': rel.PACK_MAGIC, 'packId': 'e2e-sales-2026', 'type': 'sales', 'title': 'e2e 销售包', 'version': 1,
    'issuedAt': '2026-08-29', 'items': [
        {'op': 'upsert', 'key': 'estee-001', 'data': {'id': 'estee-001', 'name': '人气精华', 'description': '价格实惠，含税一价全包', 'tags': ['人气'], 'coreBenefits': ['修护']}}
    ]
}
PACK_BAD = {
    'magic': rel.PACK_MAGIC, 'packId': 'e2e-bad-sales', 'type': 'sales', 'title': '违规包', 'version': 1,
    'issuedAt': '2026-08-29', 'items': [
        {'op': 'upsert', 'key': 'k1', 'data': {'name': '全网最低价手慢无', 'description': '', 'tags': [], 'coreBenefits': []}}
    ]
}
PACK_QUIZ = {
    'magic': rel.PACK_MAGIC, 'packId': 'e2e-quiz-2026', 'type': 'quiz', 'title': 'e2e 题库包', 'version': 1,
    'issuedAt': '2026-08-29', 'items': [{'op': 'upsert', 'key': 'Q-001', 'data': {'q': '新题', 'origNum': 'Q-001'}}]
}
PACK_BADMAGIC = {'packId': 'nope', 'type': 'sales', 'items': []}


def main():
    tmp = tempfile.mkdtemp(prefix='packs_m3_')
    incoming = os.path.join(tmp, 'incoming')
    outdir = os.path.join(tmp, 'out')
    manifest = os.path.join(tmp, 'manifest.json')
    os.makedirs(incoming)
    # 覆盖模块级路径（函数引用模块全局常量）
    rel.INCOMING, rel.OUT_DIR, rel.MANIFEST = incoming, outdir, manifest

    # ---------- 1. 校验单元 ----------
    check('validate: 合法包通过', rel.validate_pack(dict(PACK_GOOD), 'x') == (True, []))
    ok, errs = rel.validate_pack({'packId': 'a', 'type': 'sales', 'items': []}, 'x')
    check('validate: 缺 magic/非空 items 被拒', not ok and len(errs) >= 2)
    ok, errs = rel.validate_pack({'magic': rel.PACK_MAGIC, 'packId': 'a', 'type': 'bogus', 'items': [{'op': 'x'}]}, 'x')
    check('validate: 未知 type + 非法 op 被拒', not ok and len(errs) == 2)

    # ---------- 2. 合规拦截 ----------
    ok, hits = rel.check_compliance(dict(PACK_BAD))
    check('合规: 违规 sales 命中违禁词', not ok and len(hits) >= 1 and u'全网最低' in hits[0], ' | '.join(hits))
    ok, hits = rel.check_compliance(dict(PACK_GOOD))
    check('合规: 合规 sales 放行', ok and not hits)
    ok, hits = rel.check_compliance(dict(PACK_QUIZ))
    check('合规: 非 sales 类型跳过', ok and not hits)

    # ---------- 3. --check 模式（不落盘） ----------
    with io.open(os.path.join(incoming, '01-good.json'), 'w', encoding='utf-8') as f:
        json.dump(PACK_GOOD, f, ensure_ascii=False)
    with io.open(os.path.join(incoming, '02-bad.json'), 'w', encoding='utf-8') as f:
        json.dump(PACK_BAD, f, ensure_ascii=False)
    with io.open(os.path.join(incoming, '03-quiz.json'), 'w', encoding='utf-8') as f:
        json.dump(PACK_QUIZ, f, ensure_ascii=False)
    with io.open(os.path.join(incoming, '04-badmagic.json'), 'w', encoding='utf-8') as f:
        json.dump(PACK_BADMAGIC, f, ensure_ascii=False)
    files = rel.collect_files(['--file', os.path.join(incoming, '01-good.json')]) + \
        [os.path.join(incoming, f) for f in sorted(os.listdir(incoming)) if f.endswith('.json') and f.startswith('0')]
    files = sorted(set(files))
    pub, skip, fail, man = rel.publish(files, dry_run=True)
    check('check 模式: 0 个真实发布', len(pub) == 0)
    check('check 模式: 违规包进失败列表', any(u'合规' in why or u'最低价' in why or u'手慢无' in why for _, why in fail), 'fail=' + ';'.join(why for _, why in fail))
    check('check 模式: badmagic 包进失败列表', any(u'magic' in why for _, why in fail))
    check('check 模式: 不产生落盘文件', not os.path.exists(outdir) and not os.path.exists(manifest))

    # ---------- 4. 真实发布 ----------
    pub, skip, fail, man = rel.publish(files, dry_run=False)
    check('发布: 成功 2 个（sales+quiz）', len(pub) == 2 and len([p for p in pub if 'e2e-sales' in p[1]]) == 1 and len([p for p in pub if 'e2e-quiz' in p[1]]) == 1)
    check('发布: 违规/坏包各失败 1', len(fail) == 2)
    out_file = os.path.join(outdir, 'e2e-sales-2026.json')
    body = io.open(out_file, encoding='utf-8').read()
    check('发布: 包落盘且 sha256 与文件一致', os.path.exists(out_file) and
          rel.sha256_of(body) == next(e['sha256'] for e in man['packs'] if e['packId'] == 'e2e-sales-2026'))
    check('发布: manifest 两包 + 排序 + url 正确', len(man['packs']) == 2 and man['packs'][0]['packId'] < man['packs'][1]['packId'] and
          all(e['url'].startswith('packs/packs/') for e in man['packs']))
    check('发布: manifest magic/updatedAt', man['magic'] == rel.MANIFEST_MAGIC and man['updatedAt'])

    # ---------- 5. 版本保护 + 重发覆盖 ----------
    low = dict(PACK_QUIZ); low['version'] = 0
    ok, errs = rel.validate_pack(low, 'x')
    with io.open(os.path.join(incoming, '05-low.json'), 'w', encoding='utf-8') as f:
        json.dump(low, f, ensure_ascii=False)
    pub, skip, fail, man = rel.publish([os.path.join(incoming, '05-low.json')], dry_run=False)
    check('版本保护: 低版本被跳过', len(skip) == 1 and u'版本' in skip[0][1])
    up = dict(PACK_QUIZ); up['version'] = 2
    with io.open(os.path.join(incoming, '06-up.json'), 'w', encoding='utf-8') as f:
        json.dump(up, f, ensure_ascii=False)
    pub, skip, fail, man = rel.publish([os.path.join(incoming, '06-up.json')], dry_run=False)
    check('升级: 高版本覆盖并更新 sha256', len(pub) == 1 and next(e['version'] for e in man['packs'] if e['packId'] == 'e2e-quiz-2026') == 2)

    # ---------- 6. 客户端互操作（Node 引擎消费产物） ----------
    node_script = u"""
const fs = require('fs');
const PACKS = require('./docs/_packs_engine.js');
const out = { pass: true, msgs: [] };
const t = (n, c, m) => { out.msgs.push((c ? 'PASS  ' : 'FAIL  ') + n + (m ? '  [' + m + ']' : '')); if (!c) out.pass = false; };
function memStore(seed) { const d = Object.assign({}, seed); return { getItem: k => (k in d ? d[k] : null), setItem: (k, v) => { d[k] = String(v); }, removeItem: k => { delete d[k]; } }; }
const MANIFEST = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const DIR = process.argv[2];
// 客户端 computePackUpdates（与 M2 同语义）
const manifest = MANIFEST;
const ready = [];
(manifest.packs).forEach(p => { if (!p.packId || !p.url) return; ready.push(p); });
t('M3 互操作: 客户端从 manifest 识别新包', ready.length === 2, 'n=' + ready.length);
const st = memStore();
for (const p of ready) {
  const text = fs.readFileSync(require('path').join(DIR, p.url.replace('packs/packs/', '')), 'utf8');
  const pack = JSON.parse(text);
  const ok = pack.magic === PACKS.MAGIC && pack.packId === p.packId && Array.isArray(pack.items);
  if (!ok) { out.pass = false; out.msgs.push('FAIL  包协议不兼容: ' + p.packId); break; }
  const r = PACKS.installPack(st, pack, 'url');
  if (!r.ok) { out.pass = false; out.msgs.push('FAIL  installPack: ' + r.packId); break; }
}
t('M3 互操作: 安装全部成功', PACKS.readIndex(st) && PACKS.readIndex(st).packs.length === 2);
const m = PACKS.buildPackMap(st, 'quiz');
t('M3 互操作: quiz 覆盖引擎可读', m.map['Q-001'] && m.map['Q-001'].q === '新题');
const m2 = PACKS.buildPackMap(st, 'sales');
t('M3 互操作: sales 覆盖引擎可读', m2.map['estee-001'] && m2.map['estee-001'].name === '人气精华');
console.log(out.msgs.join('\\n'));
console.log(out.pass ? 'M3_INTEROP_OK' : 'M3_INTEROP_FAIL');
process.exit(out.pass ? 0 : 1);
"""
    r = subprocess.run(['node', '-e', node_script, manifest, outdir], capture_output=True, text=True, cwd=HERE)
    print(r.stdout)
    if r.stderr:
        print('NODE_ERR:', r.stderr[:800])
    check('互操作: Node 引擎消费管线产物成功', r.returncode == 0 and 'M3_INTEROP_OK' in r.stdout)
    check('互操作: 兼容字段结构（协议一致）', 'FAIL  包协议不兼容' not in r.stdout)

    shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    for name, ok, extra in results:
        print(('PASS  ' if ok else 'FAIL  ') + name + ('  [' + extra + ']' if (extra and not ok) else ''))
    print('--- 结果: %d 通过 / %d 失败 / 共 %d ---' % (passed, failed, len(results)))
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()