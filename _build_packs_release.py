# -*- coding: utf-8 -*-
"""客舱小助手 · M3 内容发布管线
=============================================================================
把"内容数据包"从制作区发布到线上发布源（packs/），供 App（M2）在线拉取更新。

输入：packs/incoming/*.json（或 --file 指定单个文件）
      每份为一份完整数据包（magic=cabin-data-pack-v1），来源可以是：
        - 库管理「📦 数据包中心」导出的 kb/sales/quiz 数据包
        - 手工按协议编写的 JSON
流程：协议校验 → sales 类型合规检查（与客户端同谱系词表）→ sha256 →
      落盘 packs/packs/<packId>.json → 合并更新 packs/manifest.json
用法：
  python _build_packs_release.py                 # 扫描 incoming 全部发布
  python _build_packs_release.py --file a.json   # 只发布指定文件（可在任意目录）
  python _build_packs_release.py --check         # 只校验不落盘（CI/预检）
=============================================================================
"""
import hashlib
import io
import json
import os
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
INCOMING = os.path.join(HERE, 'packs', 'incoming')
OUT_DIR = os.path.join(HERE, 'packs', 'packs')
MANIFEST = os.path.join(HERE, 'packs', 'manifest.json')

PACK_MAGIC = 'cabin-data-pack-v1'
MANIFEST_MAGIC = 'cabin-packs-manifest-v1'
BASE_MANIFEST_URL = 'https://7528ardg.github.io/LEI'
ALLOWED_TYPES = ['kb', 'sales', 'quiz', 'notice']

# 销售话术合规黑名单（与 beauty.html COMPLIANCE_RULES / kb-admin PACK_COMPLIANCE 三处同步，改动必须四处维护）
COMPLIANCE_RULES = [
    (u'比专柜', u'不要做渠道价格对比'),
    (u'比代购', u'不要做渠道价格对比'),
    (u'比免税店', u'不要做渠道价格对比'),
    (u'全网最低', u'价格实在'),
    (u'最低价', u'划算的价格'),
    (u'最便宜', u'价格实惠'),
    (u'手慢无', u'人气款，很多旅客回购'),
    (u'爆款', u'人气款'),
    (u'明星产品', u'人气产品'),
    (u'错过就没有', u'不要做饥饿营销'),
]


def sha256_of(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def load_json(path):
    try:
        with io.open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {'__error__': str(e)}


def validate_pack(pack, src):
    """返回 (ok, errors) ；errors 为人类可读列表"""
    errs = []
    if not isinstance(pack, dict):
        return False, [u'不是一个对象']
    if pack.get('magic') != PACK_MAGIC:
        errs.append(u'magic 不符（期望 ' + PACK_MAGIC + '）')
    if not pack.get('packId') or not isinstance(pack['packId'], str):
        errs.append(u'缺少 packId')
    if pack.get('type') not in ALLOWED_TYPES:
        errs.append(u'type 不支持：%s（允许 %s）' % (pack.get('type'), '/'.join(ALLOWED_TYPES)))
    if not isinstance(pack.get('items'), list) or not pack['items']:
        errs.append(u'items 必须为非空数组')
    else:
        for i, it in enumerate(pack['items']):
            if not isinstance(it, dict) or not it.get('key') or it.get('op') not in ('upsert', 'delete'):
                errs.append(u'items[%d] 必须包含 key 与 op(upsert|delete)' % i)
    return not errs, errs


def check_compliance(pack):
    """sales 包合规检查 → 返回 (ok, hits)；hits 形如 ['key=badword（建议…）']"""
    if pack.get('type') != 'sales':
        return True, []
    hits = []
    for it in pack.get('items', []):
        d = it.get('data') or {}
        if not isinstance(d, dict):
            continue
        fields = [d.get('name', ''), d.get('description', ''), ' '.join(d.get('tags') or []), ' '.join(d.get('coreBenefits') or [])]
        text = '\n'.join(str(x) for x in fields if x)
        for bad, good in COMPLIANCE_RULES:
            if bad in text:
                hits.append(u'%s 包含违禁词「%s」→ 建议：%s' % (it.get('key'), bad, good))
                break
    return (not hits), hits


def build_manifest(entries, packs_dir):
    """entries: [{packId,title,type,version,updatedAt,url,sha256}}]"""
    data = {'magic': MANIFEST_MAGIC, 'updatedAt': datetime.now().strftime('%Y-%m-%d'), 'packs': entries}
    return data


def read_manifest():
    if not os.path.exists(MANIFEST):
        return {'magic': MANIFEST_MAGIC, 'updatedAt': '', 'packs': []}
    m = load_json(MANIFEST)
    if not isinstance(m, dict) or m.get('magic') != MANIFEST_MAGIC:
        return {'magic': MANIFEST_MAGIC, 'updatedAt': '', 'packs': []}
    if not isinstance(m.get('packs'), list):
        m['packs'] = []
    return m


def publish(files, dry_run=False):
    manifest = read_manifest()
    today = datetime.now().strftime('%Y-%m-%d')
    published = []
    skipped = []
    failed = []

    for path in files:
        name = os.path.basename(path)
        pack = load_json(path)
        if '__error__' in pack:
            failed.append((name, u'文件解析失败：' + pack['__error__']))
            continue
        ok, errs = validate_pack(pack, name)
        if not ok:
            failed.append((name, '；'.join(errs)))
            continue
        ok, hits = check_compliance(pack)
        if not ok:
            failed.append((name, u'合规检查未通过：' + '；'.join(hits)))
            continue
        pack_id = pack['packId']
        entry = {
            'packId': pack_id,
            'title': pack.get('title') or pack_id,
            'type': pack.get('type'),
            'version': pack.get('version', 1),
            'updatedAt': pack.get('issuedAt') or today,
            'url': 'packs/packs/%s.json' % pack_id,
            'sha256': ''
        }
        # 版本保护：manifest 已有更高版本则跳过
        exist = next((e for e in manifest['packs'] if e['packId'] == pack_id), None)
        if exist and entry['version'] < exist['version']:
            skipped.append((name, u'manifest 版本 %s 高于本包 %s，已跳过' % (exist['version'], entry['version'])))
            continue

        body = json.dumps(pack, ensure_ascii=False, separators=(',', ':'))
        entry['sha256'] = sha256_of(body)
        if dry_run:
            print(u'[check] %s -> 通过（%s v%s，%d 条，sha256=%s…）' % (name, entry['type'], entry['version'], len(pack['items']), entry['sha256'][:12]))
        else:
            os.makedirs(OUT_DIR, exist_ok=True)
            out_path = os.path.join(OUT_DIR, '%s.json' % pack_id)
            with io.open(out_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(body)
        # 合并 manifest（同 id 覆盖，保持按 packId 排序）；仅真实发布写入 published
        manifest['packs'] = [e for e in manifest['packs'] if e['packId'] != pack_id]
        manifest['packs'].append(entry)
        manifest['packs'].sort(key=lambda e: e['packId'])
        manifest['updatedAt'] = today
        if not dry_run:
            published.append((name, pack_id))

    if not dry_run:
        # 清理 manifest 中已无对应文件的失效条目
        if os.path.isdir(OUT_DIR):
            exists = set(os.listdir(OUT_DIR))
            manifest['packs'] = [e for e in manifest['packs'] if e['url'].split('/')[-1] in exists or os.path.exists(os.path.join(HERE, e['url']))]
        manifest['packs'].sort(key=lambda e: e['packId'])
        with io.open(MANIFEST, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
            f.write('\n')
    return published, skipped, failed, manifest


def collect_files(args):
    files = []
    for i in range(len(args)):
        if args[i] == '--file' and i + 1 < len(args):
            files.append(args[i + 1])
    if files:
        return files
    if not os.path.isdir(INCOMING):
        return []
    return [os.path.join(INCOMING, f) for f in sorted(os.listdir(INCOMING)) if f.endswith('.json')]


def main():
    dry_run = '--check' in sys.argv
    files = collect_files(sys.argv[1:])
    if not files:
        print(u'未找到待发布文件（packs/incoming/*.json 为空，或用 --file 指定）')
        if dry_run:
            # check 模式下仍校验既有 manifest 指向的文件完整性
            m = read_manifest()
            missing = [e['url'] for e in m['packs'] if not os.path.exists(os.path.join(HERE, e['url']))]
            if missing:
                print(u'检查结果：manifest 有 %d 个失效条目 → %s' % (len(missing), '、'.join(missing)))
                sys.exit(1)
            print(u'检查结果：通过（包 0 个）')
        return
    published, skipped, failed, manifest = publish(files, dry_run)
    for name, pid in published:
        print(u'  发布  %s → %s' % (name, pid))
    for name, why in skipped:
        print(u'  跳过  %s：%s' % (name, why))
    for name, why in failed:
        print(u'  失败  %s：%s' % (name, why))
    total = len(published) + len(skipped) + len(failed)
    print(u'--- %s模式：%d 个文件 / 发布 %d / 跳过 %d / 失败 %d ---' % ('CHECK' if dry_run else '发布', total, len(published), len(skipped), len(failed)))
    if failed:
        print('RELEASE_FAILED')
        sys.exit(1)
    if not dry_run and published:
        print(u'发布完成：packs/manifest.json 已更新，git add packs && git commit && git push 后全员可在线获取。')


if __name__ == '__main__':
    main()