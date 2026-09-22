# -*- coding: utf-8 -*-
"""最终产物针检查
 1) 移动端加固：所有产物 HTML + 模块 gz 均需含 mobile-native-hardening / mobile-native-js
 2) CC 之家的 3D 层：cc-home 源码与 home.gz 需含 CC3D 接入（three + cc-3d.js + 3D 容器）
 3) 反向针：「你问我答」已按用户要求还原成原始问答页，qa 源码与 qa.gz 里**不得**再出现宠物/3D 注入
"""
import gzip
import re, io, os, sys
BASE = os.path.dirname(os.path.abspath(__file__))   # 2026-09-21：不再硬编码绝对路径
QUIET = '--quiet' in sys.argv
res = []


def rd(p):
    if not os.path.exists(p):
        return ''
    # 2026-09-21：验证器不能用 errors="ignore" —— 静默丢弃损坏字节会让针检查误判通过。
    # 解码失败必须显式报错，返回空串让针检查自然 FAIL。
    try:
        with io.open(p, encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError as e:
        print(u'!! 解码失败（视为 FAIL）：%s -> %s' % (p, e))
        return ''


def rdgz(p):
    if not os.path.exists(p):
        return ''
    try:
        with io.open(p, "rb") as f:
            return gzip.decompress(f.read()).decode("utf-8")
    except Exception as e:
        print(u'!! 解压/解码失败（视为 FAIL）：%s -> %s' % (p, e))
        return ''


htmls = ["spring-assistant.html",
         u"客舱小助手（离线完整版）.html",
         u"在线版/客舱小助手（在线版）.html",
         u"在线版/客舱小助手（离线完整版-在线部署）.html",
         "daily.html"]
for f in htmls:
    raw = rd(os.path.join(BASE, f))
    res.append(("HTML", f, "mobile-native-hardening" in raw and "mobile-native-js" in raw))

mods = ["qa", "quiz", "performance", "beauty", "medical", "risk",
        "daily", "manual", "report", "kbadmin", "issues"]
for m in mods:
    raw = rdgz(os.path.join(BASE, u"在线版/mods/%s.gz" % m))
    res.append(("GZ", m + ".gz", "mobile-native-hardening" in raw and "mobile-native-js" in raw))

# ---- CC 之家的 3D 层 ----
NEED3D = ("形象IP/models/cc-3d.js", "window.CC3D_READY")
for kind, name, rel, needles in (("SRC", "cc-home.html", "cc-home.html", ('id="hero3d"', "r3dSync")),
                                 ("GZ", "home.gz", u"在线版/mods/home.gz", ('id="hero3d"', "r3dSync"))):
    p = os.path.join(BASE, rel.replace(u"/", os.sep))
    if not os.path.exists(p):
        res.append((kind, name, False))
        continue
    raw = rdgz(p) if p.endswith(".gz") else rd(p)
    res.append((kind, name, all(n in raw for n in NEED3D) and all(n in raw for n in needles)))

# ---- CC 之家的背景图：必须内嵌自包含（含走廊背景），且不得再引用外部 backdrops 文件 ----
BD_NEED = ("var BDR = {", "hasbg", "var SHOW_PROPS", "var SHOW_SVG",
           "var BG_ORIG", "id=\"scBlur\"", "var SHOW_HERO2D")
BD_BAN = ("形象IP/backdrops/cc", 'loading="lazy"')
for kind, name, rel in (("SRC", u"cc-home.html(内嵌背景)", "cc-home.html"),
                        ("GZ", u"home.gz(内嵌背景)", u"在线版/mods/home.gz")):
    p = os.path.join(BASE, rel.replace(u"/", os.sep))
    if not os.path.exists(p):
        res.append((kind, name, False))
        continue
    raw = rdgz(p) if p.endswith(".gz") else rd(p)
    bad = [n for n in BD_BAN if n in raw]
    res.append((kind, name, all(n in raw for n in BD_NEED) and not bad))

# ---- 正向针：你问我答必须已接入 CC 形象（头像 / 背景栏 / 3D 层 / 控制条）----
PET_MARKS = ('id="petStage"', 'id="petBar"', 'id="petFig3d"', 'pet-stage-css',
             'CC_AVATAR', 'pet3dSync', 'id="petPhoto"', 'id="petArt"')
for kind, name, rel in (("SRC", u"qa.html(CC 形象)", "qa.html"),
                        ("GZ", u"qa.gz(CC 形象)", u"在线版/mods/qa.gz")):
    p = os.path.join(BASE, rel.replace(u"/", os.sep))
    if not os.path.exists(p):
        res.append((kind, name, False))
        continue
    raw = rdgz(p) if p.endswith(".gz") else rd(p)
    miss = [n for n in PET_MARKS if n not in raw]
    res.append((kind, name, len(miss) == 0))

# 在线版是否带上了 3D 资产（srcdoc iframe 的 base URL 继承父页，相对路径要真实存在）
md = os.path.join(BASE, u"在线版", u"形象IP", u"models")
if os.path.isdir(os.path.join(BASE, u"在线版")):
    n_glb = len([f for f in os.listdir(md) if f.startswith("cc") and f.endswith(".glb")]) if os.path.isdir(md) else 0
    res.append(("ASSET", u"在线版/形象IP/models/cc*.glb(%d)" % n_glb, n_glb > 0))

# ---- 零「内置密钥」守护（2026-09-19 晚随 AI 混合模式恢复调整口径）----
# 仍禁：内置 Key 字面量 / Bearer 内置令牌 / 4.7 旗舰引用 / 硅基流动 / Gist 云同步。
# 放行：open.bigmodel.cn（GLM-4-Flash 免费模型端点）、api.tavily.com / api.firecrawl.dev
#       （免Key搜索，2026-09-19 实测均 200+CORS*）、spring_ai_cfg（运行时 localStorage 键名）。
BAN_RX = [
    ("内置共享 Key", "4986b927"),
    ("Key 常量名", "BUILTIN_AI_KEY"),
    ("硅基流动端点", "api.siliconflow.cn"),
    ("Gist 云同步", "api.github.com"),
    ("4.7 引用", "glm-4.7"),
    ("4.7 服务商标识", "glm47"),
]
APIKEY_RX = re.compile(r"apiKey\s*:\s*['\"][^'\"]{8,}")
BEARER_RX = re.compile(r"Bearer\s+[A-Za-z0-9_\.\-]{20,}")
LOCAL_MARKS = {
    "qa": "__AI_RESTORE_20260919__",   # AI 接口已恢复（混合模式：免费模型 + 用户自填Key，源码零密钥）
    "beauty": "__AI_HYBRID_20260919__",     # 混合模式：免Key兜底 + GLM-4-Flash 可选
    "quiz": u"本地模式（2026-09-19：彻底无密钥",
    "kb-admin": "KBADMIN_LOCALMODE_v1",
    "home": u"本地模式（彻底无密钥）",
}
for kind, name, rel, key in (
        ("SRC", "qa.html", "qa.html", "qa"),
        ("GZ", "qa.gz", u"在线版/mods/qa.gz", "qa"),
        ("SRC", "beauty.html", "beauty.html", "beauty"),
        ("GZ", "beauty.gz", u"在线版/mods/beauty.gz", "beauty"),
        ("SRC", "quiz.html", "quiz.html", "quiz"),
        ("GZ", "quiz.gz", u"在线版/mods/quiz.gz", "quiz"),
        ("SRC", "kb-admin.html", "kb-admin.html", "kb-admin"),
        ("SRC", "cc-home.html", "cc-home.html", "home"),
        ("GZ", "home.gz", u"在线版/mods/home.gz", "home")):
    p = os.path.join(BASE, rel.replace(u"/", os.sep))
    if not os.path.exists(p):
        res.append((kind, name + u"(零密钥)", False))
        continue
    raw = rdgz(p) if p.endswith(".gz") else rd(p)
    hits = [n for n, lit in BAN_RX if lit in raw]
    if APIKEY_RX.search(raw):
        hits.append(u"apiKey 有值")
    if BEARER_RX.search(raw):
        hits.append(u"Bearer 内置令牌")
    res.append((kind, name + u"(零内置密钥)", (not hits) and (LOCAL_MARKS[key] in raw)))

# ---- 壳内载荷取证：离线单文件把模块 gzip+base64 内嵌，字面 grep 必然 0 命中 ----
# （不能只看模块源文件在不在位，必须解码壳内真实载荷，否则「改了源码没重建壳」查不出来）
import base64, re as _re
B64 = _re.compile(r'\b(qa|quiz|performance|beauty|medical|risk|daily|manual|report|kbadmin|issues|home)'
                  r'\s*:\s*"([A-Za-z0-9+/=]{120,})"')   # 2026-09-21：补全模块键（原先只 4 个，漏检等于留死角）
# 只查「内嵌载荷」的两个离线单文件；在线版是瘦壳，载荷刻意置空、按需 fetch mods/*.gz，
# 其正确性已由上面的 在线版/mods/*.gz 针覆盖（拿瘦壳查内嵌载荷必然误报，实测踩过）
SHELLS = ["spring-assistant.html", u"客舱小助手（离线完整版）.html"]
WANT = {"beauty": ("__AI_HYBRID_20260919__", u"api.firecrawl.dev"),   # 混合模式标记 + 免Key搜索层在位
        "qa": ("__AI_RESTORE_20260919__", "QA_QUICKSTART_BEGIN", "QA_WIZARD2_v1",
               "QA_ANSWER_TOOLS_20260921", "QA_MYPANEL_20260921"),   # AI 接口恢复（混合模式）+ 2026-09-21 批1 增强
        "quiz": (u"本地模式（2026-09-19：彻底无密钥",),
        "home": (u"本地模式（彻底无密钥）",)}
BAN_IN_SHELL = ("4986b927", "BUILTIN_AI_KEY",
                "api.github.com", "glm-4.7", "glm47")
# open.bigmodel.cn / api.tavily.com / api.firecrawl.dev 已放行（AI 混合模式：免费模型端点 + 免Key搜索）
for sh in SHELLS:
    p = os.path.join(BASE, sh.replace(u"/", os.sep))
    if not os.path.exists(p):
        res.append(("SHELL", sh + "(缺失)", False))
        continue
    s = rd(p)
    hits = {}
    for m in B64.finditer(s):
        # C1：与 rd() 口径一致——严格解码，损坏字节必须 FAIL，不得用 "ignore" 静默吞掉。
        # 解码失败时不计入 hits，后续 body 为 None -> 该模块探针缺失 -> 计入失败。
        try:
            hits[m.group(1)] = gzip.decompress(base64.b64decode(m.group(2))).decode("utf-8")
        except Exception as e:
            if not QUIET:
                print(u'!! 壳内载荷解码失败（视为缺失/损坏）：%s -> %s' % (m.group(1), e))
    for mod, needles in WANT.items():
        body = hits.get(mod)
        bad = [x for x in BAN_IN_SHELL if body and x in body]
        ok = body is not None and all(n in body for n in needles) and not bad
        res.append(("SHELL", u"%s/%s(零密钥/本地模式)%s" % (sh, mod, (u" 残留=" + u",".join(bad)) if bad else u""), ok))

# 价格抽取超时必须收敛（限流时最多等 20s 即回落本地解析，而不是 45s 干等）
p = os.path.join(BASE, "beauty.html")
raw = rd(p)
res.append(("SRC", "beauty.html(抽取超时20s)", "maxTokens: 1200, timeout: 20000" in raw))
res.append(("SRC", "beauty.html(旧超时45s已清)",
            "maxTokens: 1200, timeout: 45000" not in raw))

bad = 0
for kind, name, ok in res:
    if not ok:
        bad += 1
    if not QUIET or not ok:
        print(("%s %s %s" % (kind, name, "OK" if ok else "FAIL")))
print("SUMMARY: %d checked, %d fail" % (len(res), bad))
# 2026-09-21：补退出码 —— 原先只有 print，FAIL 也不阻断构建，等于针检查形同虚设
raise SystemExit(1 if bad else 0)
