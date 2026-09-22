# -*- coding: utf-8 -*-
u"""形象IP 素材完整性校验（构建期守门，加入 _build_all.py 的 VERIFY 链）。

背景：素材缺口过去靠人工盘点，出现过两类误判——
  1) 把「按设计不产出」当成「缺失」：cc02 / cc24 本来就无水印（_wm_erase.py 的
     CLEAN={2,24}），因此 原稿_clean/ 只有 22 个（cc01 + cc03~cc23），这是正确状态；
  2) 把「相对路径没按基准目录解析」当成「断链」：_pet_sprites.json 的 src 是相对
     路径，基准是 形象IP/sprites/ 或 形象IP/原稿/，不是项目根。

本脚本把「必须有」的项做成硬失败（FAIL），把「进度类」做成提示（WARN），
从而让真正的缺口自动暴露、误判不再复发。

用法：python _verify_assets.py
"""
import io
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
IP = os.path.join(BASE, u'形象IP')
DESKTOP_UI = os.path.join(os.path.expanduser('~'), 'Desktop', u'UI设定')

fails, warns = [], []


def need(cond, msg):
    if not cond:
        fails.append(msg)


def warn(cond, msg):
    if not cond:
        warns.append(msg)


# ---------- 1) 官方立绘母版 ----------
LIP = os.path.join(IP, u'CC-形象-立绘.png')
need(os.path.exists(LIP), u'官方立绘母版缺失: 形象IP/CC-形象-立绘.png'
     u'（恢复方式：从 桌面/UI设定/CC-形象-立绘.png 复制回来）')

# ---------- 2) 24 形态抠图 ----------
missing_cut = [i for i in range(1, 25)
               if not os.path.exists(os.path.join(IP, 'cutouts', 'cc%02d.png' % i))]
need(not missing_cut, u'抠图缺失: %s' % missing_cut)

# ---------- 3) 24 张精灵图 ----------
missing_spr = [i for i in range(1, 25)
               if not os.path.exists(os.path.join(IP, 'sprites', 'sp%02d.webp' % i))]
need(not missing_spr, u'精灵图缺失: %s' % missing_spr)

# ---------- 4) _pet_sprites.json 的 src 全部可解析 ----------
SPR_JSON = os.path.join(BASE, u'_pet_sprites.json')
if os.path.exists(SPR_JSON):
    d = json.load(io.open(SPR_JSON, encoding='utf-8'))
    srcs = set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ('src', 'source', 'img', 'image', 'file') and isinstance(v, str):
                    srcs.add(v)
                else:
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(d)
    # src 是相对路径，按下列基准目录依次解析（顺序即优先级）
    BASES = ['', IP, os.path.join(IP, 'sprites'), os.path.join(IP, u'原稿'),
             os.path.join(IP, u'原稿_clean'), os.path.join(IP, u'_draft'), DESKTOP_UI]
    unresolved = [s for s in sorted(srcs)
                  if not any(os.path.exists(os.path.join(b, s)) for b in BASES)]
    need(not unresolved, u'_pet_sprites.json 声明源图无法解析: %s' % unresolved)
else:
    need(False, u'_pet_sprites.json 缺失')

# ---------- 5) 原稿_clean 覆盖数应与 _wm_erase.py 的 CLEAN 集一致 ----------
CLEAN_DIR = os.path.join(IP, u'原稿_clean')
if os.path.isdir(CLEAN_DIR):
    have = set()
    for f in os.listdir(CLEAN_DIR):
        m = re.match(r'^cc(\d\d)\.png$', f)
        if m:
            have.add(int(m.group(1)))
    # 从 _wm_erase.py 读 CLEAN（本来就无水印、不产出 clean 版的编号）
    clean_exempt = set()
    wmp = os.path.join(BASE, u'_wm_erase.py')
    if os.path.exists(wmp):
        m = re.search(r'CLEAN\s*=\s*\{([^}]*)\}', io.open(wmp, encoding='utf-8').read())
        if m:
            clean_exempt = set(int(x) for x in re.findall(r'\d+', m.group(1)))
    expect = set(range(1, 25)) - clean_exempt
    need(have == expect,
         u'原稿_clean/ 覆盖 %d 个，期望 %d 个；多出=%s 缺失=%s'
         % (len(have), len(expect), sorted(have - expect), sorted(expect - have)))
else:
    need(False, u'形象IP/原稿_clean/ 目录缺失')

# ---------- 6) 已登记的 3D 模型文件与预览图成对存在 ----------
MODEL_JSON = os.path.join(BASE, u'_pet_models.json')
models = []
if os.path.exists(MODEL_JSON):
    models = json.load(io.open(MODEL_JSON, encoding='utf-8'))
    for r in models:
        g = os.path.join(IP, 'models', r.get('file', ''))
        p = os.path.join(IP, 'models', r.get('preview', ''))
        need(os.path.exists(g), u'_pet_models.json 登记的模型缺失: models/%s' % r.get('file'))
        need(os.path.exists(p), u'_pet_models.json 登记的预览缺失: models/%s' % r.get('preview'))

# ---------- 7) 孤儿预览图（有 preview 无 glb）——进度类，仅提示 ----------
mdir = os.path.join(IP, 'models')
if os.path.isdir(mdir):
    for f in sorted(os.listdir(mdir)):
        m = re.match(r'^(\d+)-preview\.png$', f)
        if m:
            i = int(m.group(1))
            warn(os.path.exists(os.path.join(mdir, 'cc%02d.glb' % i)),
                 u'孤儿预览图: models/%s 没有对应 cc%02d.glb' % (f, i))
        elif f.endswith('-preview.png') and not f[0].isdigit():
            stem = f[:-len('-preview.png')]
            warn(os.path.exists(os.path.join(mdir, stem + '.glb')),
                 u'孤儿预览图: models/%s 没有对应 %s.glb（历史遗留？）' % (f, stem))

# ---------- 8) 3D 进度（提示） ----------
if os.path.isdir(mdir):
    n = len([f for f in os.listdir(mdir) if f.endswith('.glb') and f.startswith('cc')])
    warn(n >= 24, u'3D 模型进度 %d/24（按计划推进中，非缺陷）' % n)

# ---------- 输出 ----------
print(u'[资产校验] 抠图 24 张 / 精灵 24 张 / 模型 %d 个'
      % len([f for f in os.listdir(mdir) if f.endswith('.glb')]) if os.path.isdir(mdir) else '')
for w in warns:
    print(u'  WARN  ' + w)
for f in fails:
    print(u'  FAIL  ' + f)
if fails:
    print(u'SUMMARY: %d 项失败 / %d 项提示' % (len(fails), len(warns)))
    sys.exit(1)
print(u'SUMMARY: 素材完整性 OK（%d 项提示，无失败）' % len(warns))
