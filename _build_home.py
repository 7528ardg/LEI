# -*- coding: utf-8 -*-
"""
构建「CC 之家」独立模块 -> cc-home.html（幂等，可重跑）
数据来源：_pet_roster.py（24 形态/房间/关系/互动剧场/离线小知识）+ 形象IP/sprites/*.webp
用法：python _build_home.py [--check]
"""
import io, os, sys, json, base64

ROOT = os.path.dirname(os.path.abspath(__file__))   # 2026-09-21：不再硬编码绝对路径，项目可整体搬移
OUT = os.path.join(ROOT, 'cc-home.html')
SPR = os.path.join(ROOT, '形象IP', 'sprites')
CHECK = '--check' in sys.argv

sys.path.insert(0, ROOT)
from _pet_roster import ROSTER, INTERACTIONS, OFFLINE_KB  # noqa: E402

_SCP = os.path.join(ROOT, '_pet_scenes.json')
_CTP = os.path.join(ROOT, '_pet_cutouts.json')
_BDP = os.path.join(ROOT, '_bd_embed.json')
_ORP = os.path.join(ROOT, '_bd_orig_home.json')


def _load_json(p, default):
    """安全读取 JSON：文件缺失/损坏返回 default；用 with 关闭句柄（原先 io.open(...) 不关闭）。"""
    if not os.path.exists(p):
        return default
    try:
        with io.open(p, encoding='utf-8', newline='') as f:
            return json.load(f)
    except Exception as e:
        print('[warn] 读取 %s 失败（%s），按缺省处理' % (os.path.basename(p), str(e)[:80]))
        return default


SCENES = _load_json(_SCP, {})
CUTOUTS = _load_json(_CTP, {})

# 背景图内嵌包（由 _bd_embed.py 生成：24 张房间背景 + 1 张走廊背景，WebP base64）
_bd = _load_json(_BDP, {'fmt': 'webp', 'data': {}})
BMIME = 'image/webp' if _bd.get('fmt') == 'webp' else 'image/jpeg'
ROOMBG = dict((k, 'data:' + BMIME + ';base64,' + v) for k, v in _bd.get('data', {}).items())
if not ROOMBG:
    print('[ERR] 缺 _bd_embed.json（背景图内嵌包），请先跑 _bd_embed.py'); raise SystemExit(1)
_miss = [str(i) for i in range(1, 25) if str(i) not in ROOMBG]
if _miss:
    print('[ERR] 背景图内嵌包缺 %s' % ','.join(_miss)); raise SystemExit(1)

# 房间背景源二选一（2026-09-14 用户：「全部原图直出」）
#   有 _bd_orig_home.json（24 张【原稿】，已擦水印的优先）→ 原图直出；
#   否则回落到 _bd_embed.json 的 AI 房间背景图。删掉该文件即可一键切回。
_ori = _load_json(_ORP, {})
ORI = dict((k, 'data:' + ('image/webp' if _ori.get('fmt') == 'webp' else 'image/jpeg') +
            ';base64,' + v) for k, v in _ori.get('data', {}).items())
ORI_AR = _ori.get('ar', {})          # 每张原图的宽高比（用于「原图完整可见」的取景计算）
BG_ORIG = bool(ORI) and all(str(i) in ORI for i in range(1, 25))
BDR = dict(ROOMBG)
if BG_ORIG:
    for i in range(1, 25):
        BDR[str(i)] = ORI[str(i)]
    print('[ok] 房间背景 = 原图直出（_bd_orig_home.json，%d 张，base64 约 %.2f MB）'
          % (len(ORI), sum(len(v) for v in ORI.values()) / 1048576))
else:
    print('[ok] 房间背景 = AI 房间背景图（_bd_embed.json）')

sprites = {}
for c in ROSTER:
    fp = os.path.join(SPR, 'sp%02d.webp' % c['i'])
    if not os.path.exists(fp):
        print('[ERR] 缺精灵 %s，请先跑 _pet_assets.py' % os.path.basename(fp)); raise SystemExit(1)
    sprites[str(c['i'])] = 'data:image/webp;base64,' + base64.b64encode(open(fp, 'rb').read()).decode()

# 陈设词 -> 图标（房间用具象小图标摆出来，避免另做美术）
GLYPH = {
    '落地窗': '🪟', '候机椅': '💺', '登机牌架': '🎫', '绿飞机剪影': '✈️',
    '长木桌': '🪵', '抹茶拿铁': '🍵', '千层蛋糕': '🍰', '暖吊灯': '💡',
    '吧台': '🧁', '茶壶': '🫖', '蛋糕柜': '🧊', '小碟子': '🥏',
    '短沙发': '🛋', '羊毛毯': '🧣', '玩偶': '🧸', '游戏机': '🎮',
    '雨棚': '⛱', '水洼': '💧', '行李车': '🛒', '伞架': '☂️',
    '圣诞树': '🎄', '彩灯串': '✨', '铃铛': '🔔', '礼物箱': '🎁',
    '书架': '📚', '藤椅': '🪑', '台灯': '🛋', '摊开的航图': '🗺',
    '雪坡': '🏔', '松树': '🌲', '滑雪板': '🎿', '暖炉': '🔥',
    '楼群': '🏙', '路灯': '💡', '自动售货机': '🥤', '班车': '🚌',
    '篝火': '🔥', '帐篷': '⛺', '折叠椅': '🪑', '星空': '🌌',
    '窗边座': '🪟', '咖啡': '☕', '笔记本': '📓', '雨痕': '🌧',
    '料理台': '🥣', '不锈钢碗': '🥣', '草莓': '🍓', '烤箱': '🔥',
    '花树': '🌸', '石灯': '🏮', '木廊': '🪵', '落瓣': '🌸',
    '霓虹灯牌': '🌃', '透明伞': '☂', '卷帘门': '🚪',
    '三角钢琴': '🎹', '谱架': '🎼', '落地灯': '💡', '绒毯': '🧶',
    '长椅': '🪑', '薄雪': '❄', '礼盒': '🎁',
    '绿硬地': '🟩', '球网': '🥅', '球筐': '🥎',
    '书桌': '🪵', '绿色笔记本': '📗', '档案盒': '🗂',
    '椰树': '🌴', '白沙': '🏖', '矮桌': '🪵', '躺椅': '🛏',
    '木栈桥': '🌉', '白浪': '🌊', '冲浪板': '🏄', '救生圈': '🛟',
    '闸机': '🚧', '行李箱': '🧳', '航班牌': '📋',
    '座椅排': '💺', '餐车': '🛒', '橙汁': '🧃', '舷窗': '🪟',
    '池水': '🏊', '白罩衫': '👕', '冰饮': '🍹',
    '警示线': '🚧', '护板架': '🛡', '机械臂': '🦾', '黄昏机坪': '🌇',
}

def glyph(name):
    if name in GLYPH:
        return GLYPH[name]
    for k, v in GLYPH.items():
        if k in name or name in k:
            return v
    return '📦'

HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,interactive-widget=resizes-content">
<meta name="theme-color" content="#00A650">
<meta name="apple-mobile-web-app-title" content="CC之家">
<title>CC 之家 · 春秋全能助手</title>
<style>
:root{
  --primary:#00A650; --primary-d:#0B7A43; --primary-l:#E8F6EE; --gold:#F5B800;
  --ink:#0F1A14; --ink2:#3C4A42; --muted:#64756B; --line:#E2EAE5;
  --bg:#F4F8F5; --card:#fff; --radius:14px;
  --shadow:0 1px 2px rgba(10,60,35,.05),0 8px 28px rgba(10,60,35,.08);
  --font-sans:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent;}
html,body{margin:0;height:100%;}
body{background:var(--bg);color:var(--ink);font-family:var(--font-sans);font-size:15px;line-height:1.7;
  display:flex;flex-direction:column;overflow:hidden;}
button{font-family:inherit;}

/* ---------- 顶栏 ---------- */
.hd{flex:none;display:flex;align-items:center;gap:9px;padding:10px 14px;background:#fff;
  border-bottom:1px solid var(--line);z-index:5;flex-wrap:wrap;}
.hd .logo{display:flex;align-items:center;gap:8px;min-width:0;}
.hd .badge{width:32px;height:32px;border-radius:10px;background:linear-gradient(135deg,#00A650,#0B7A43);
  color:#fff;display:flex;align-items:center;justify-content:center;font-size:1rem;flex:none;}
.hd h1{margin:0;font-size:15.5px;font-weight:800;letter-spacing:.01em;white-space:nowrap;}
.hd h1 small{font-weight:600;font-size:11.5px;color:var(--muted);margin-left:5px;}
.hd .sp{flex:1;}
.chipbtn{font-size:11.5px;font-weight:700;color:var(--ink2);background:#F2F6F3;border:1px solid var(--line);
  border-radius:9px;padding:5px 10px;cursor:pointer;white-space:nowrap;}
.chipbtn:active{transform:scale(.96);}
.chipbtn.on{background:var(--primary);color:#fff;border-color:var(--primary);}
.netchip{font-size:11px;font-weight:800;border-radius:999px;padding:3px 10px;white-space:nowrap;}
.netchip.glm{background:var(--primary-l);color:var(--primary-d);}
.netchip.keyless{background:#FFF4D6;color:#8A6100;}
.netchip.offline{background:#EEF2F0;color:#64756B;}

/* ---------- 视图容器 ---------- */
.main{flex:1;min-height:0;position:relative;overflow:hidden;}
.view{position:absolute;inset:0;display:none;overflow-y:auto;-webkit-overflow-scrolling:touch;}
.view.on{display:block;}

/* ---------- 大厅 ---------- */
.hall-hd{padding:16px 16px 4px;}
.hall-hd h2{margin:0 0 4px;font-size:19px;font-weight:800;}
.hall-hd p{margin:0;color:var(--muted);font-size:12.5px;}
/* 大厅改为可走动的走廊：网格卡片退化成「全部房间」抽屉 */
.view#viewHall.on{display:flex;flex-direction:column;min-height:0;}
.hall-hd{flex:none;}
.doors{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:11px;padding:12px 12px 30px;}
.door{position:relative;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;background:#fff;
  cursor:pointer;transition:.18s;box-shadow:var(--shadow);text-align:left;padding:0;}
.door:hover{transform:translateY(-3px);border-color:#9FD3B8;}
.door .th{position:relative;padding-top:64%;background:#0E2A1C;overflow:hidden;}
.door .th img{position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;object-position:top center;}
.door .th .no{position:absolute;right:7px;top:7px;font-size:10px;font-weight:800;color:#fff;
  background:rgba(0,0,0,.5);border-radius:999px;padding:1.5px 8px;font-family:ui-monospace,Menlo,monospace;}
.door .th .tone{position:absolute;left:7px;top:7px;font-size:10px;font-weight:800;color:#06251A;
  background:rgba(255,255,255,.9);border-radius:999px;padding:1.5px 8px;}
.door .tx{padding:9px 11px 11px;}
.door .rn{font-size:13.5px;font-weight:800;color:var(--ink);}
.door .nm{font-size:11.5px;color:var(--muted);margin-top:1px;}
.door .dg{font-size:11px;color:#8A9A91;margin-top:5px;padding-top:5px;border-top:1px dashed var(--line);
  display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden;}
.gridview .gv-hd{position:sticky;top:0;z-index:2;display:flex;align-items:center;gap:9px;
  padding:11px 13px;background:#fff;border-bottom:1px solid var(--line);}
.gridview .gv-hd b{font-size:14.5px;}
.gridview .gv-hd .x{margin-left:auto;font-size:12.5px;font-weight:800;background:#F2F6F3;
  border:1px solid var(--line);border-radius:9px;padding:5px 12px;cursor:pointer;}

/* ---------- 房间 ---------- */
.room{position:relative;height:clamp(300px,42vh,520px);overflow:hidden;perspective:1000px;perspective-origin:70% 44%;}
/* 房间铺满内容区：背景图要"铺完整"，不留下方大片死白（按钮栏固定高度，其余给房间） */
.view#viewRoom.on{display:flex;flex-direction:column;min-height:0;}
.view#viewRoom .room{flex:1 1 auto;height:auto;min-height:clamp(280px,42vh,520px);}
.view#viewRoom .roombar{flex:none;}
.room .sky{position:absolute;inset:0;background:linear-gradient(178deg,var(--rs1,#0E3B26),var(--rs2,#04160E));
  transition:background .5s;}
.room .wall{position:absolute;left:0;right:0;top:0;height:58%;
  background:linear-gradient(180deg,rgba(255,255,255,.10),transparent);
  border-bottom:1px solid rgba(255,255,255,.10);}
.room .floor{position:absolute;left:-42%;right:-42%;bottom:-56%;height:150%;
  background-image:linear-gradient(var(--rl,#35C98A) 1px,transparent 1px),
                   linear-gradient(90deg,var(--rl,#35C98A) 1px,transparent 1px);
  background-size:44px 44px;transform:perspective(600px) rotateX(64deg);transform-origin:50% 100%;opacity:.32;
  -webkit-mask-image:linear-gradient(180deg,transparent 0%,#000 44%,#000 100%);
          mask-image:linear-gradient(180deg,transparent 0%,#000 44%,#000 100%);}
.room .glow{position:absolute;left:64%;bottom:-24%;width:360px;height:360px;transform:translateX(-50%) translateZ(-160px);
  background:radial-gradient(circle,var(--ra,#00A650) 0%,transparent 62%);opacity:.32;filter:blur(8px);transition:opacity .5s;}
.room .fx{position:absolute;inset:0;pointer-events:none;opacity:0;transition:opacity .5s;}
/* 用户 2026-09-14：取消雨元素图片（雨水/白露/寒露）的下雨特效，雪 / 樱花 / 星光不受影响 */
.room[data-fx="rain"] .fx{display:none!important;}
.room[data-fx="rain"] .fx{opacity:.5;background-image:repeating-linear-gradient(102deg,rgba(255,255,255,.55) 0 1px,transparent 1px 16px);
  background-size:auto 60px;animation:rf .55s linear infinite;}
.room[data-fx="snow"] .fx{opacity:.75;background-image:radial-gradient(2px 2px at 12% 20%,#fff,transparent),
  radial-gradient(2.4px 2.4px at 38% 62%,#fff,transparent),radial-gradient(1.8px 1.8px at 66% 30%,#fff,transparent);
  background-size:170px 170px;animation:rs 7s linear infinite;}
.room[data-fx="petal"] .fx{opacity:.85;background-image:radial-gradient(3.4px 2px at 20% 18%,#F7B6CF,transparent),
  radial-gradient(3px 1.8px at 58% 44%,#FBD7E4,transparent);background-size:210px 210px;animation:rs 11s linear infinite;}
.room[data-fx="spark"] .fx{opacity:.9;background-image:radial-gradient(2px 2px at 30% 70%,#FFD27A,transparent),
  radial-gradient(2.4px 2.4px at 52% 86%,#FFB347,transparent);background-size:120px 160px;animation:rr 4.2s linear infinite;}
@keyframes rf{from{background-position:0 0}to{background-position:-16px 60px}}
@keyframes rs{from{background-position:0 0}to{background-position:34px 170px}}
@keyframes rr{from{background-position:0 0}to{background-position:0 -160px}}

.room .furn{position:absolute;inset:0;transition:opacity .4s;}
.room .prop{position:absolute;display:flex;flex-direction:column;align-items:center;gap:2px;
  transform:translate(-50%,-50%);}
.room .prop .box{width:52px;height:52px;border-radius:12px;display:flex;align-items:center;justify-content:center;
  font-size:24px;background:linear-gradient(150deg,rgba(255,255,255,.22),rgba(0,0,0,.14)),var(--rpTop,#14532F);
  border:1.5px solid rgba(255,255,255,.22);
  transform:perspective(320px) rotateX(58deg) rotateZ(45deg);
  box-shadow:0 14px 20px rgba(0,0,0,.42);}
.room .prop .lb{font-size:10px;font-weight:700;color:rgba(255,255,255,.72);white-space:nowrap;
  text-shadow:0 1px 4px rgba(0,0,0,.7);}
.room .cast{position:absolute;left:50%;bottom:52px;width:150px;height:26px;transform:translateX(-50%);border-radius:50%;
  background:radial-gradient(ellipse at center,rgba(0,0,0,.6),transparent 72%);filter:blur(3px);}
.room .ped{position:absolute;left:50%;bottom:26px;width:190px;height:190px;transform:translateX(-50%) rotateX(66deg) rotateZ(45deg);
  border-radius:30px;background:linear-gradient(150deg,rgba(255,255,255,.22),rgba(0,0,0,.12)),var(--rpTop2,#14532F);
  box-shadow:0 0 0 1.5px var(--rl,#35C98A) inset,0 0 34px -4px var(--ra,#00A650);}
.room .hero{position:absolute;left:50%;bottom:46px;width:196px;height:258px;margin-left:-98px;
  transform-style:preserve-3d;animation:rfloat 6.4s ease-in-out infinite;}
.room .hero .back{position:absolute;inset:0;border-radius:14px;background:var(--rpEdge,#04170E);transform:translateZ(-18px);}
.room .hero .card{position:absolute;inset:0;border-radius:14px;overflow:hidden;
  transform:rotateY(calc(-14deg + var(--px,0) * 9deg)) rotateX(calc(2deg - var(--py,0) * 5deg)) translateZ(40px);
  transition:transform .24s cubic-bezier(.2,.7,.3,1);
  box-shadow:0 30px 50px rgba(0,0,0,.5),0 0 0 1.5px rgba(255,255,255,.3) inset;}
.room .hero .card img{width:100%;height:100%;object-fit:cover;object-position:top center;display:block;}
.room .hero .card::after{content:'';position:absolute;top:2px;right:-9px;width:9px;height:calc(100% - 4px);
  background:linear-gradient(180deg,rgba(255,255,255,.5),rgba(255,255,255,.06));transform:skewY(-26deg);transform-origin:left center;}
/* ---------- 真 3D 形象层（three.js；模型到位时盖住纸片立牌） ----------
   注意：基础规则必须放在下面的 @media 断点之前，否则同优先级下会反过来盖掉断点（踩过） */
.room .hero3d{position:absolute;left:50%;bottom:32px;width:214px;height:288px;margin-left:-107px;
  z-index:2;opacity:0;transition:opacity .5s;pointer-events:none;}
#room.is3d .hero3d{opacity:1;}
#room.is3d .hero,#room.is3d .ped,#room.is3d .cast{opacity:0;transition:opacity .32s;pointer-events:none;}
/* 没有 3D 模型时用 2D 立牌：加画框与落影，读起来是"立在房间里的立牌"而不是一张贴纸 */
.room .hero .card{box-shadow:0 26px 44px rgba(0,0,0,.55),0 0 0 3px rgba(255,255,255,.5) inset,0 0 0 1px rgba(0,0,0,.28);}
.room .hero .back{border-radius:14px;background:linear-gradient(180deg,rgba(0,0,0,.5),rgba(0,0,0,.75));}
.room .r3dtag{position:absolute;left:50%;bottom:8px;margin-left:-107px;width:214px;text-align:center;
  z-index:3;font-size:9.5px;font-weight:800;color:#06251A;background:rgba(255,255,255,.82);
  border-radius:999px;padding:2px 8px;display:none;}
#room.is3d .r3dtag{display:block;}
/* 秋分琴房：贝多芬钢琴开关 + 手动换曲（只在秋分这间房出现） */
.room .pianobar{position:absolute;right:10px;top:10px;z-index:6;display:flex;gap:6px;align-items:center;}
.room .pianochip{cursor:pointer;white-space:nowrap;
  font-size:11.5px;font-weight:800;color:#06251A;background:color-mix(in srgb,var(--bg-card,#fff) 82%,transparent);
  border:1px solid rgba(255,255,255,.55);border-radius:999px;padding:4px 11px;
  backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
  box-shadow:0 6px 16px rgba(0,0,0,.28);-webkit-tap-highlight-color:transparent;}
.room .pianochip:active{transform:scale(.96);}
.room .pianochip.play{background:#00A650;color:#fff;border-color:#00A650;}
/* ==== SCENE_KIT ==== */
/* ==== BACKDROP_KIT ==== */
/* AI 生成的正式背景图：不再加模糊（主图已是 1280 原生高清），只做轻微调色 */
.room .sc-far.real{filter:saturate(1.03) brightness(1.04);}
/* 有了真实背景图，SVG 建筑只留一点点作透视暗示 */
#room.realbg .sc-svg{opacity:.16;transition:opacity .5s;}
#room.realbg .sc-mist{background:linear-gradient(180deg,rgba(255,255,255,.04),transparent 30%,rgba(3,14,9,.18) 100%);}

/* ==== CUTOUT_KIT ==== */
/* 抠图立牌：透明底人物直接站在房间里（无卡片框），带 drop-shadow */
.room .hero.cut{border-radius:0;overflow:visible;}
.room .hero.cut .cutimg{position:absolute;inset:0;width:100%;height:100%;
  object-fit:contain;object-position:bottom center;display:block;
  filter:drop-shadow(0 8px 12px rgba(0,0,0,.45)) drop-shadow(0 2px 3px rgba(0,0,0,.3));}
/* 走廊门牌上的抠图人物 */
.hall .hdoor .pn img.cutimg{object-fit:contain;object-position:bottom center;
  filter:drop-shadow(0 4px 6px rgba(0,0,0,.5));}

/* 立牌的落地阴影：贴在地板上，跟着立牌一起，避免"悬空" */
.room .hero3d::after,.room .hero::after{content:'';position:absolute;left:50%;bottom:-2.5%;
  width:104%;height:11%;transform:translateX(-50%);border-radius:50%;pointer-events:none;
  background:radial-gradient(ellipse at center,rgba(0,0,0,.52),rgba(0,0,0,.18) 58%,transparent 74%);
  filter:blur(3px);}
.room .hero3d::after{z-index:-1;}
/* ==================== 真实场景（照原图还原的 24 间房） ====================
   思路：① .sc-far 是「环境底色板」——从原图把人物区域用两侧真实环境拉伸填掉、重度模糊，
            只保留那个地方的光与色；② .sc-svg 用真·一点透视画出天花/后墙/侧墙/地板与材质；
         ③ .sc-furn 里的每件陈设按同一条透视公式摆位（越远越小越靠中越淡），与 3D 立牌同一套公式。
   ========================================================================= */
.room{--hy:42%;}
.room .sc{position:absolute;inset:0;overflow:hidden;background:#05090c;}
.room .sc-far{position:absolute;inset:-6%;background-size:cover;background-position:center;
  filter:blur(3.2px) saturate(1.06) brightness(var(--farB,1));transition:filter .5s;}
/* ---- 原图直出取景（_bd_orig_home.json 存在时）--------------------------------
   原稿是 2:3 竖构图、房间是宽幅（约 1.8~2:1）。铺满（cover）会按宽度放大，
   所以把取景锚点往上压（center 20%），让人物头部留在画面里；手机竖屏下房间本身
   就接近原稿比例，等于整张原样铺开。 */
.room .sc-blur{position:absolute;inset:0;background-size:cover;background-position:center;
  background-repeat:no-repeat;filter:blur(46px) saturate(1.3) brightness(1.02);display:none;}
#room.realbg .sc-blur{display:block;}
/* 原图直出时四周的暗角收一半 —— 用户 2026-09-14：「显黑」 */
#room.realbg .sc-grade{opacity:.55;}
.room .sc-far.orig{inset:0;background-size:cover;background-position:center 24%;
  background-repeat:no-repeat;filter:none;}
/* 备用档（ORI_FIT='full'）：整张原图完整可见，两侧由虚化放大版补边 */
.room .sc-far.orig.full{background-size:100% 100%;background-position:center bottom;
  -webkit-mask-image:linear-gradient(90deg,transparent 0,#000 7%,#000 93%,transparent 100%);
          mask-image:linear-gradient(90deg,transparent 0,#000 7%,#000 93%,transparent 100%);}
/* 铺满档（房间比例接近原稿）不羽化 —— 否则屏幕两边缘会被羽化掉 */
.room .sc-far.orig.full.nofx{background-size:cover;
  -webkit-mask-image:none;mask-image:none;}
#room.no2d .hero,#room.no2d .hero.cut{display:none!important;}
.room .sc-svg{position:absolute;inset:0;width:100%;height:100%;display:block;}
.room .sc-furn{position:absolute;inset:0;}
.room .sc-mist{position:absolute;inset:0;pointer-events:none;
  background:linear-gradient(180deg,rgba(255,255,255,.05),transparent 34%);}
.room .sc-grade{position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(125% 95% at 50% 44%,transparent 40%,rgba(0,0,0,var(--vig,.44)) 100%);}
.room .sc-grain{position:absolute;inset:0;pointer-events:none;opacity:.055;mix-blend-mode:overlay;
  background-image:radial-gradient(1px 1px at 20% 30%,#fff,transparent),
                   radial-gradient(1px 1px at 72% 62%,#fff,transparent);background-size:7px 7px;}

/* ---- 陈设：位置/大小由透视公式算，内部一律用 % 描述形状 ---- */
.room .it{position:absolute;transform-origin:50% 100%;}
.room .it .sh{position:absolute;left:50%;bottom:-3%;width:136%;height:24%;transform:translateX(-50%);
  background:radial-gradient(ellipse at center,rgba(0,0,0,.55),transparent 68%);filter:blur(3px);}
.room .fb{position:absolute;inset:0;border-radius:2px;
  background:linear-gradient(168deg,var(--c1),var(--c2));
  box-shadow:inset 0 1.5px 0 rgba(255,255,255,.26),inset -2px 0 0 rgba(0,0,0,.20),0 1px 2px rgba(0,0,0,.3);}
.room .ft{position:absolute;left:0;right:0;top:0;height:16%;border-radius:2px 2px 0 0;
  background:linear-gradient(180deg,rgba(255,255,255,.34),transparent);}
.room .fc{position:absolute;inset:0;border-radius:46%/16%;
  background:radial-gradient(84% 68% at 30% 24%,rgba(255,255,255,.5),transparent 62%),
             linear-gradient(180deg,var(--c1),var(--c2));}
.room .fo{position:absolute;inset:0;border-radius:50%;
  background:radial-gradient(72% 62% at 32% 26%,rgba(255,255,255,.6),transparent 64%),var(--c1);}
.room .fp{position:absolute;left:50%;transform:translateX(-50%);border-radius:2px;
  background:linear-gradient(90deg,var(--c2),var(--c1),var(--c2));}
.room .gd{position:absolute;border-radius:50%;filter:blur(7px);pointer-events:none;
  background:radial-gradient(circle,var(--c1),transparent 70%);}
.room .bk{position:absolute;background:linear-gradient(180deg,var(--c1),var(--c2));border-radius:1.5px;}
.room .lp{position:absolute;border-radius:50%;
  background:radial-gradient(circle at 40% 34%,#fff,var(--c1) 58%,transparent 76%);}
.room .lb2{position:absolute;border-radius:2px;background:var(--c1);
  box-shadow:0 0 0 1px rgba(255,255,255,.18) inset;}

/* ---- 走廊大厅 ---- */
.hall{position:relative;flex:1;min-height:0;overflow:hidden;background:#04100a;
  perspective:clamp(460px,62vw,900px);perspective-origin:50% 50%;}
/* 走廊背景图（AI 生成的「机组休息室」房间式大厅，内嵌 WebP）+ SVG 结构叠在上面做透视暗示 */
.hall.hasbg{background-position:center center;background-size:cover;background-repeat:no-repeat;}
.hall.hasbg .hl-svg{opacity:.34;transition:opacity .5s;}
.hall.hasbg .hl-doors{background:radial-gradient(ellipse at 50% 44%,transparent 26%,rgba(2,10,6,.46) 100%);}
.hall .hl-floor,.hall .hl-ceil,.hall .hl-end{position:absolute;}
.hall .hl-svg{position:absolute;inset:0;width:100%;height:100%;}
.hall .hl-doors{position:absolute;inset:0;}
.hall .hdoor{position:absolute;transform-origin:50% 100%;cursor:pointer;border:0;padding:0;background:none;}
.hall .hdoor .fr{position:absolute;inset:0;border-radius:3px;
  background:linear-gradient(170deg,var(--c1),var(--c2)) padding-box;
  box-shadow:inset 0 0 0 1.5px rgba(255,255,255,.22),inset 0 0 18px rgba(0,0,0,.35);}
.hall .hdoor .pn{position:absolute;inset:12% 14% 46%;border-radius:2px;overflow:hidden;background:#0B2A1C;}
.hall .hdoor .pn img{width:100%;height:100%;object-fit:cover;object-position:top center;display:block;}
.hall .hdoor .nb{position:absolute;left:8%;right:8%;bottom:9%;text-align:center;
  font-size:11px;font-weight:800;color:#EAFBF1;text-shadow:0 1px 3px rgba(0,0,0,.8);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.hall .hdoor .nu{position:absolute;right:9%;top:6%;font-size:9.5px;font-weight:800;color:#06251A;
  background:rgba(255,255,255,.92);border-radius:999px;padding:0 6px;font-family:ui-monospace,Menlo,monospace;}
.hall .hdoor .ht{position:absolute;left:50%;bottom:-6%;transform:translateX(-50%);height:4%;width:150%;
  background:radial-gradient(ellipse at center,rgba(0,0,0,.55),transparent 70%);filter:blur(3px);}
.hall .hdoor.hot .fr{box-shadow:inset 0 0 0 2px var(--pri),0 0 22px -2px var(--pri);}
.hall-ui{position:absolute;left:0;right:0;bottom:0;display:flex;gap:7px;align-items:center;
  padding:9px 11px;background:linear-gradient(0deg,rgba(3,14,9,.88),transparent);}
.hall-ui .hbtn{font-size:12px;font-weight:800;color:#EAFBF1;background:rgba(255,255,255,.12);
  border:1px solid rgba(255,255,255,.22);border-radius:10px;padding:7px 12px;cursor:pointer;
  backdrop-filter:blur(4px);-webkit-tap-highlight-color:transparent;}
.hall-ui .hbtn:active{transform:scale(.96);}
.hall-ui .hpos{margin-left:auto;font-size:11.5px;font-weight:800;color:#BFE6D2;
  background:rgba(0,0,0,.36);border-radius:999px;padding:5px 11px;}
.hall-ui .hpos b{color:#fff;}
.gridview{position:absolute;inset:0;overflow-y:auto;background:#F4F8F5;display:none;}
.gridview.on{display:block;}

@keyframes rfloat{0%,100%{transform:translateY(0) rotateZ(0)}50%{transform:translateY(-10px) rotateZ(-.8deg)}}
.room .roomtag{position:absolute;left:14px;top:12px;color:#fff;}
.room .roomtag .rn{font-size:19px;font-weight:800;text-shadow:0 2px 10px rgba(0,0,0,.6);}
.room .roomtag .sub{font-size:11.5px;color:rgba(255,255,255,.72);}
.room .bub{position:absolute;left:14px;top:74px;max-width:min(52%,420px);background:rgba(255,255,255,.95);
  border-radius:3px 13px 13px 13px;padding:10px 13px;font-size:13px;line-height:1.6;color:#12261C;
  box-shadow:0 8px 22px rgba(0,0,0,.3);}
.room .bub .who{font-size:10.5px;font-weight:800;color:var(--primary-d);margin-bottom:3px;}
.room .busy{position:absolute;left:14px;bottom:14px;font-size:11.5px;font-weight:700;color:#EAFBF1;
  background:rgba(0,0,0,.38);border:1px solid rgba(255,255,255,.18);border-radius:999px;padding:4px 12px;
  backdrop-filter:blur(4px);max-width:60%;}
.roombar{flex:none;display:flex;gap:8px;padding:11px 14px;background:#fff;border-top:1px solid var(--line);
  overflow-x:auto;scrollbar-width:none;}
.roombar::-webkit-scrollbar{display:none;}
.rbtn{font-size:12px;font-weight:800;border-radius:10px;padding:8px 13px;border:1px solid var(--line);
  background:#F7FAF8;color:var(--ink2);cursor:pointer;white-space:nowrap;}
.rbtn:active{transform:scale(.96);}
.rbtn.p{background:var(--primary);color:#fff;border-color:var(--primary);}

/* ---------- 剧场 ---------- */
#stage{position:fixed;inset:0;z-index:40;display:none;background:rgba(6,20,14,.62);
  backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);align-items:center;justify-content:center;padding:14px;}
#stage.on{display:flex;}
.st-box{width:100%;max-width:620px;max-height:88vh;background:#fff;border-radius:18px;display:flex;flex-direction:column;
  overflow:hidden;box-shadow:0 26px 70px rgba(0,0,0,.5);}
.st-h{display:flex;align-items:center;gap:9px;padding:13px 16px;border-bottom:1px solid var(--line);flex:none;}
.st-h b{font-size:15px;font-weight:800;}
.st-h .kind{font-size:10.5px;font-weight:800;color:#06251A;background:var(--gold);border-radius:999px;padding:2px 9px;}
.st-h .x{margin-left:auto;font-size:12px;font-weight:800;color:var(--ink2);background:#F2F6F3;border:1px solid var(--line);
  border-radius:9px;padding:5px 11px;cursor:pointer;}
.st-body{flex:1;min-height:0;overflow-y:auto;padding:15px 16px;display:flex;flex-direction:column;gap:11px;}
.line{display:flex;gap:9px;align-items:flex-start;animation:lin .28s ease-out;}
@keyframes lin{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.line img{width:34px;height:34px;border-radius:50%;flex:none;object-fit:cover;object-position:top center;
  border:1.5px solid var(--line);}
.line .b{background:#F4F8F5;border-radius:3px 13px 13px 13px;padding:9px 13px;font-size:13.5px;max-width:86%;}
.line .b .n{font-size:10.5px;font-weight:800;color:var(--primary-d);margin-bottom:2px;}
.line.narr{justify-content:center;}
.line.narr .b{background:transparent;color:var(--muted);font-size:12.5px;font-style:italic;text-align:center;max-width:94%;}
.st-f{display:flex;gap:8px;padding:11px 16px;border-top:1px solid var(--line);flex:none;flex-wrap:wrap;}
.st-f .rbtn{flex:1;text-align:center;min-width:96px;}

/* ---------- 聊天 ---------- */
/* 2026-09-14（晚）：聊天背景 = 当前角色的原稿原图（替代原来的纯白空白，用户要求）。
   .chat-bg 铺满整个聊天视图、随 enter()/形象设置切换实时联动；
   上面一层可读性蒙层；气泡 / 快捷提问 / 输入条全部改毛玻璃浮在原图上（与 qa 板块同一套做法）。
   2026-09-15（用户：聊天框背景看不清人物、过于放大）：原来整层 background-size:cover，
   竖版原画在宽屏聊天框里被裁到只剩躯干。改成双层 ——
   元素本体 = 角色配色渐变（补两侧空边）；::before = 原画 auto 100%（整张完整可见、贴底居中），
   左右羽化融入渐变；::after = 可读性蒙层（保持在最上）。 */
#viewChat{background:#07140D;}
.chat-bg{position:absolute;inset:0;background:#07140D;transition:background .4s;}
.chat-bg::before{content:'';position:absolute;inset:0;pointer-events:none;
  background-image:var(--ccArt,none);background-size:auto 100%;background-position:center bottom;
  background-repeat:no-repeat;
  -webkit-mask-image:linear-gradient(90deg,transparent 0,#000 8%,#000 92%,transparent 100%);
          mask-image:linear-gradient(90deg,transparent 0,#000 8%,#000 92%,transparent 100%);}
.chat-bg::after{content:'';position:absolute;inset:0;pointer-events:none;
  background:linear-gradient(180deg,rgba(4,18,11,.50) 0%,rgba(4,18,11,.16) 26%,rgba(4,18,11,.08) 55%,rgba(4,18,11,.34) 100%);}
.chatwrap{position:relative;z-index:1;display:flex;flex-direction:column;height:100%;}
.chat-scroll{flex:1;min-height:0;overflow-y:auto;padding:14px;}
/* 2026-09-19（用户：聊天泡过长）—— 原来块级气泡宽度 auto 会一律撑到 max-width:86%，
   短消息也拖成大长条；改 width:fit-content 让气泡跟随文字长度收缩（仍受 86% 封顶换行）。 */
.bub2{background:color-mix(in srgb,#fff 78%,transparent);
  border:1px solid color-mix(in srgb,var(--line) 55%,transparent);
  border-radius:3px 13px 13px 13px;padding:10px 13px;font-size:13.8px;
  backdrop-filter:blur(10px) saturate(1.1);-webkit-backdrop-filter:blur(10px) saturate(1.1);
  box-shadow:var(--shadow);width:fit-content;max-width:86%;margin-bottom:10px;white-space:pre-line;}
.bub2.me{margin-left:auto;border-radius:13px 3px 13px 13px;
  background:color-mix(in srgb,var(--primary) 88%,transparent);color:#fff;border-color:transparent;}
.chat-in{flex:none;display:flex;gap:8px;padding:11px 14px;padding-bottom:calc(11px + env(safe-area-inset-bottom));
  border-top:1px solid color-mix(in srgb,var(--line) 45%,transparent);
  background:color-mix(in srgb,#fff 62%,transparent);
  backdrop-filter:blur(14px) saturate(1.12);-webkit-backdrop-filter:blur(14px) saturate(1.12);}
.chat-in input{flex:1;min-width:0;font-size:16px;padding:10px 12px;border:1px solid var(--line);border-radius:11px;
  background:color-mix(in srgb,#fff 80%,transparent);color:var(--ink);font-family:inherit;}
.chat-in button{font-size:12.5px;font-weight:800;padding:0 16px;border-radius:11px;border:none;
  background:var(--primary);color:#fff;cursor:pointer;}
.tips{display:flex;gap:7px;flex-wrap:wrap;padding:0 14px 10px;}
.tips button{font-size:11.5px;font-weight:700;color:var(--ink2);
  background:color-mix(in srgb,#fff 66%,transparent);
  border:1px solid color-mix(in srgb,var(--line) 55%,transparent);
  backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
  border-radius:999px;padding:5px 11px;cursor:pointer;}
.tips button.mem-clear{color:#8A4B00;background:color-mix(in srgb,#FFF4E0 78%,transparent);
  border-color:color-mix(in srgb,#E8C48A 70%,transparent);margin-left:auto;}

/* ---------- 形象设置 ---------- */
#petModal{position:fixed;inset:0;z-index:50;display:none;background:rgba(5,18,12,.6);
  backdrop-filter:blur(4px);align-items:center;justify-content:center;padding:14px;}
#petModal.on{display:flex;}
.pm-box{width:100%;max-width:760px;max-height:88vh;background:#fff;border-radius:18px;display:flex;flex-direction:column;
  overflow:hidden;box-shadow:0 26px 70px rgba(0,0,0,.45);}
.pm-h{display:flex;align-items:center;gap:9px;padding:14px 17px;border-bottom:1px solid var(--line);flex:none;}
.pm-h b{font-size:15.5px;font-weight:800;}
.pm-h .sub{font-size:11.5px;color:var(--muted);}
.pm-h .x{margin-left:auto;font-size:12.5px;font-weight:800;color:var(--ink2);background:#F2F6F3;
  border:1px solid var(--line);border-radius:9px;padding:5px 12px;cursor:pointer;}
.pm-grid{flex:1;min-height:0;overflow-y:auto;padding:14px 17px 18px;display:grid;
  grid-template-columns:repeat(auto-fill,minmax(96px,1fr));grid-auto-rows:max-content;align-content:start;gap:11px;}
.pm-c{border:1.5px solid var(--line);border-radius:13px;overflow:hidden;background:#fff;cursor:pointer;
  transition:.16s;text-align:center;}
.pm-c:hover{border-color:#9FD3B8;transform:translateY(-2px);}
.pm-c.on{border-color:var(--primary);box-shadow:0 0 0 2px rgba(0,166,80,.2);}
.pm-c .th{position:relative;padding-top:150%;background:#F0F5F2;overflow:hidden;}
.pm-c .th img{position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;object-position:top center;}
.pm-c .th .tone{position:absolute;left:5px;top:5px;font-size:9.5px;font-weight:800;color:#06251A;
  background:rgba(255,255,255,.86);border-radius:999px;padding:1px 7px;}
.pm-c .nm{font-size:12px;font-weight:800;padding:6px 4px 1px;}
.pm-c .cd{font-size:9px;color:#8A9A91;padding:0 4px 7px;font-family:ui-monospace,Menlo,monospace;}
.pm-c.on .nm{color:var(--primary-d);}

.toast{position:fixed;left:50%;bottom:26px;transform:translateX(-50%);background:rgba(10,30,20,.92);color:#fff;
  font-size:12.5px;font-weight:700;padding:9px 16px;border-radius:11px;z-index:90;opacity:0;transition:.25s;pointer-events:none;}
.toast.on{opacity:1;}

@media (max-width:820px){
  .doors{grid-template-columns:repeat(auto-fill,minmax(138px,1fr));gap:10px;padding:12px 12px 36px;}
  .room{height:clamp(268px,42vh,440px);perspective:860px;}
  .room .hero{width:168px;height:218px;margin-left:-84px;bottom:46px;}
  .room .hero3d{width:176px;height:238px;margin-left:-88px;bottom:40px;}
  .room .ped{width:162px;height:162px;}
  .room .roomtag .rn{font-size:17px;}
  .room .bub{max-width:56%;font-size:12.5px;}
}
@media (max-width:560px){
  body{font-size:14.5px;}
  .hd{padding:9px 12px;gap:7px;}
  .hd h1{font-size:14.5px;}
  .hd h1 small{display:none;}
  .doors{grid-template-columns:repeat(auto-fill,minmax(calc(50% - 8px),1fr));gap:9px;padding:10px 10px 32px;}
  .room{height:256px;perspective:760px;}
  /* 手机端把立牌靠右，气泡限宽到 58%，避免气泡压住角色（实测 375/390/430 三档都重叠） */
  .room .hero{left:auto;right:10px;margin-left:0;width:132px;height:174px;bottom:46px;}
  .room .hero3d{left:auto;right:6px;margin-left:0;width:140px;height:190px;bottom:44px;}
  .room .r3dtag{left:auto;right:6px;margin-left:0;width:140px;bottom:4px;}
  .room .ped{left:auto;right:16px;width:130px;height:130px;bottom:24px;transform:rotateX(66deg) rotateZ(45deg);}
  .room .cast{left:auto;right:34px;width:104px;bottom:40px;transform:none;}
  .room .roomtag{left:11px;top:10px;max-width:56%;}
  .room .roomtag .rn{font-size:15.5px;}
  .room .bub{left:11px;top:62px;max-width:58%;font-size:12.2px;padding:8px 11px;}
  .room .busy{left:11px;bottom:11px;font-size:11px;max-width:58%;}
  .line .b{font-size:13px;}
  .st-f .rbtn{min-width:80px;font-size:11.5px;}
}
@media (max-width:390px){
  .doors{grid-template-columns:1fr 1fr;gap:8px;}
  .door .tx{padding:8px 9px 9px;}
  .room{height:240px;}
  .room .hero{right:8px;width:118px;height:156px;}
  .room .hero3d{right:5px;width:126px;height:172px;}
  .room .r3dtag{right:5px;width:126px;}
  .room .ped{right:12px;}
  .room .cast{right:28px;}
  .room .bub{max-width:56%;}
}
@media (prefers-reduced-motion:reduce){
  .room .hero{animation:none;}
  .room .fx{animation:none;}
  .line{animation:none;}
}
</style>
</head>
<body>

<header class="hd">
  <div class="logo">
    <div class="badge">🏠</div>
    <h1>CC 之家 <small>24 个形态 · 24 间房</small></h1>
  </div>
  <div class="sp"></div>
  <span class="netchip offline" id="netChip">离线值守</span>
  <button class="chipbtn" id="btnHall">🏛 大厅</button>
  <button class="chipbtn" id="btnSet">🐾 形象</button>
  <button class="chipbtn" id="btnRand">🎲 随便看看</button>
</header>

<div class="main">
  <!-- 大厅 -->
  <section class="view on" id="viewHall">
    <!-- 用户 2026-09-14：删除顶部文案，走廊整块铺满展示 -->
    <div class="hall" id="hall">
      <svg class="hl-svg" id="hlSvg" preserveAspectRatio="none"></svg>
      <div class="hl-doors" id="doors"></div>
      <div class="hall-ui">
        <button class="hbtn" id="hlBack">◀ 往回走</button>
        <button class="hbtn" id="hlFwd">往前走 ▶</button>
        <button class="hbtn" id="hlGrid">▦ 全部房间</button>
        <span class="hpos" id="hlPos">走廊 <b>1</b>/12</span>
      </div>
    </div>
    <div class="gridview" id="gridView"></div>
  </section>

  <!-- 房间 -->
  <section class="view" id="viewRoom">
    <div class="room" id="room" data-fx="glow" data-env="in">
      <div class="sc">
        <div class="sc-blur" id="scBlur"></div>
        <div class="sc-far" id="scFar"></div>
        <svg class="sc-svg" id="scSvg" preserveAspectRatio="none"></svg>
        <div class="sc-furn" id="scFurn"></div>
        <div class="sc-mist"></div>
        <div class="fx"></div>
        <div class="sc-grade"></div>
        <div class="sc-grain"></div>
      </div>
      <div class="hero" id="hero"><div class="back"></div><div class="card"><img id="heroImg" alt=""></div></div>
      <div class="hero3d" id="hero3d"></div>
      <div class="r3dtag" id="r3dtag">真 3D · 可拖动视角</div>
      <div class="pianobar" id="pianoBar" style="display:none">
        <button class="pianochip" id="pianoChip" title="秋分琴房 · 贝多芬钢琴三首，可开关">🎵 贝多芬 · 关</button>
        <button class="pianochip" id="pianoChipNext" title="换一首（月光第一乐章 / 致爱丽丝 / 悲怆第二乐章）">⏭</button>
      </div>
      <div class="roomtag">
        <div class="rn" id="rName">—</div>
        <div class="sub" id="rSub">—</div>
      </div>
      <div class="bub" id="rBub"><div class="who" id="rWho">—</div><span id="rSays">—</span></div>
      <div class="busy" id="rBusy">—</div>
    </div>
    <div class="roombar">
      <button class="rbtn p" id="btnHi">👋 打个招呼</button>
      <button class="rbtn" id="btnVisit">🚪 串门</button>
      <button class="rbtn" id="btnPlay">🎭 演一段</button>
      <button class="rbtn" id="btnChat">💬 聊两句</button>
      <button class="rbtn" id="btnNextRoom">➡️ 下一间</button>
      <button class="rbtn" id="btn3d">🧊 3D 开</button>
    </div>
  </section>

  <!-- 聊天 -->
  <section class="view" id="viewChat">
    <div class="chat-bg" id="chatBg"></div>
    <div class="chatwrap">
      <div class="chat-scroll" id="chatScroll"></div>
      <div class="tips" id="tips"></div>
      <div class="chat-in">
        <input id="chatInput" placeholder="跟她说点什么…" autocomplete="off">
        <button id="btnSend">发送</button>
      </div>
    </div>
  </section>
</div>

<!-- 剧场 -->
<div id="stage">
  <div class="st-box">
    <div class="st-h"><b id="stTitle">—</b><span class="kind" id="stKind">—</span>
      <button class="x" id="stX">关闭</button></div>
    <div class="st-body" id="stBody"></div>
    <div class="st-f">
      <button class="rbtn p" id="stNext">下一句</button>
      <button class="rbtn" id="stAuto">自动播放</button>
      <button class="rbtn" id="stAgain">重看</button>
      <button class="rbtn" id="stOther">换个剧本</button>
    </div>
  </div>
</div>

<!-- 形象设置 -->
<div id="petModal">
  <div class="pm-box">
    <div class="pm-h"><b>🐾 形象设置</b><span class="sub">共 24 个形态 · 房间随形态联动</span>
      <button class="x" id="pmX">完成</button></div>
    <div class="pm-grid" id="pmGrid"></div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script id="mobile-native-js">
/* 移动端/平板：安全区 + 键盘 + 触感（与本项目其它模块保持同一套做法） */
(function(){
  try{
    var d = document.documentElement;
    if (CSS && CSS.supports && CSS.supports('padding-top: env(safe-area-inset-top)')) {
      var s = document.createElement('style');
      s.textContent = '.hd{padding-top:calc(10px + env(safe-area-inset-top))!important;}' +
                      '.step2,.roombar{padding-bottom:calc(11px + env(safe-area-inset-bottom))!important;}';
      document.head.appendChild(s);
    }
  }catch(e){}
  if (navigator.vibrate) { window.__ccVib = function(n){ try{ navigator.vibrate(n||8); }catch(e){} }; }
  else { window.__ccVib = function(){}; }
  /* 软键盘：visualViewport 压缩，保证输入框可见 */
  if (window.visualViewport){
    var vv = window.visualViewport;
    var fix = function(){ document.body.style.height = vv.height + 'px'; };
    vv.addEventListener('resize', fix); vv.addEventListener('scroll', fix); fix();
  }
})();
</script>

<script>
window.CC_HOME = (function(){
  var ROSTER = __ROSTER__;
  var SPR = __SPRITES__;
  var BDR = __BDR__;          /* 背景图内嵌包：'1'..'24' 房间背景，'hall' 走廊背景 */
  var SHOW_PROPS = false;     /* 旧的 CSS 陈设道具层开关（现由背景图承担场景） */
  var SHOW_SVG = false;       /* 旧的 SVG 建筑层开关（现在背景图就是场景） */
  /* 2D 立牌用「抠图人物」还是「原图」：用户 2026-09-14 要求先用原图（带原画背景的立牌） */
  var USE_CUTOUT = false;
  /* 背景是不是「原稿原图」（_bd_orig_home.json 存在即为真）——是则走「模糊补边 + 清晰居中」
     的直出取景（原图是 2:3 竖构图，房间是宽幅，铺满会把人物裁掉） */
  var BG_ORIG = __BG_ORIG__;
  var ORIAR = __ORIAR__;      /* 每张原稿的宽高比（ORI_FIT='full' 时用来算完整取景） */
  /* 原图直出的铺法：'full' = **整张原图完整可见**（用户 2026-09-14：铺满会把人物裁掉、
     看不到全貌），两侧由虚化放大版补边；'cover' = 铺满 + 按头部取景（宽屏更满但会裁人） */
  var ORI_FIT = 'full';
  /* 取景锚点（background-position 的 Y%）：值越大画面越往下（露身子多、头更靠上）。
     Q 版三头身形态头特别大，用默认值会变成一张大脸 → 单独往下压一点 */
  var ORI_POS = { '1': 34, '3': 34, '4': 34, '5': 34, '6': 34 };
  var ORI_POS_DEF = 24;
  /* 2D 悬浮立牌开关：用户 2026-09-14「取消现有的 2D 悬浮状态」→ 房间只留背景原图（+可选 3D），
     不再叠一块悬浮的 2D 人物卡。需要恢复改成 true 即可 */
  var SHOW_HERO2D = false;
  var INTER = __INTER__;
  var OKB = __OKB__;
  var KEY = 'spring_cc_home_form';
  var K3D = 'spring_cc_home_3d';
  var cur = 0, view = 'hall', lastMode = 'offline';
  var $ = function(id){ return document.getElementById(id); };
  var pick = function(a){ return a[(Math.random() * a.length) | 0]; };
  var esc = function(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); };
  var byI = {}; ROSTER.forEach(function(c){ byI[c.i] = c; });
  function mix(hex, to, amt){
    var n = parseInt(String(hex).replace('#',''), 16);
    if (isNaN(n)) return hex;
    var r = ((n>>16)&255)+ (to-((n>>16)&255))*amt, g = ((n>>8)&255)+(to-((n>>8)&255))*amt, b=(n&255)+(to-(n&255))*amt;
    return '#' + ('000000' + ((Math.round(r)<<16)|(Math.round(g)<<8)|Math.round(b)).toString(16)).slice(-6);
  }
  function toast(t){
    var el = $('toast'); if (!el) return;
    el.textContent = t; el.classList.add('on');
    clearTimeout(el._t); el._t = setTimeout(function(){ el.classList.remove('on'); }, 1600);
  }
  /* 触感：浏览器要求在用户手势后才能 vibrate，否则会在控制台报 Blocked 错误。
     所以先等到用户第一次按下，再启用。 */
  var touched = false;
  function vib(n){ if (!touched || !window.__ccVib) return; window.__ccVib(n); }
  document.addEventListener('pointerdown', function(){ touched = true; }, true);

  /* ---------------- 视图切换 ---------------- */
  /* 聊天背景 = 当前角色的原稿原图（跟随 enter() / 形象设置切换实时联动）
     2026-09-15：双层化 —— 原画装进 ::before（auto 100% 整张可见，不再 cover 放大裁人），
     本体铺角色配色渐变补宽屏两侧空边（CSS 见 .chat-bg::before） */
  function chatBgSync(){
    var el = $('chatBg'); if (!el) return;
    var c = ROSTER[cur]; if (!c) return;
    var bg = BDR[String(c.i)] || '';
    if (bg){
      el.style.setProperty('--ccArt', 'url("' + bg + '")');
      var p = c.pal || {};
      el.style.background = 'linear-gradient(180deg,' + (p.sky1 || '#0E3B26') + ' 0%,' +
        (p.floor || '#0B2B1B') + ' 58%,' + (p.sky2 || '#04160E') + ' 100%)';
    } else {
      el.style.setProperty('--ccArt', 'none');
      el.style.background = '';
    }
  }
  function go(v){
    view = v;
    ['viewHall','viewRoom','viewChat'].forEach(function(id){ $(id).classList.toggle('on', id === 'view' + v.charAt(0).toUpperCase() + v.slice(1)); });
    if (v === 'hall' && window.__sceneBuild) setTimeout(renderHall, 30);
    var gv = $('gridView'); if (gv && v !== 'hall') gv.classList.remove('on');
    if (v === 'chat'){ chatBgSync(); setTimeout(function(){ var i = $('chatInput'); if (i) i.focus(); }, 80); }
  }

  /* ---------------- 大厅（走廊）：实现见下方 SCENE_KIT_JS ---------------- */

  /* ---------------- 房间 ---------------- */
  function enter(i){
    cur = (i + ROSTER.length) % ROSTER.length;
    var c = ROSTER[cur], p = c.pal;
    chatBgSync();                      /* 聊天视图的背景跟着这位角色换 */
    var r = $('room');
    r.style.setProperty('--rs1', p.sky1);
    r.style.setProperty('--rs2', p.sky2);
    r.style.setProperty('--rl', p.line);
    r.style.setProperty('--ra', p.accent);
    r.style.setProperty('--rpTop', mix(p.floor, 255, 0.34));
    r.style.setProperty('--rpTop2', mix(p.floor, 255, 0.22));
    r.style.setProperty('--rpEdge', mix(p.floor, 0, 0.55));
    r.setAttribute('data-fx', c.fx || 'glow');
    $('heroImg').src = SPR[String(c.i)];
    r3dSync(c.i);
    $('rName').textContent = c.room;
    $('rSub').textContent = c.n + '（' + c.code + '）· ' + c.scene;
    $('rWho').textContent = c.n + ' · ' + c.alias;
    $('rSays').textContent = c.hi;
    $('rBusy').textContent = '在忙：' + c.doing;
    sceneBuild(c);   /* 真实场景：环境板 + 真透视建筑 + 按同一透视公式摆位的陈设/立牌 */
    try{ localStorage.setItem(KEY, String(cur)); }catch(e){}
    markGrid();
    go('room');
    /* 房间是 flex 撑满内容区的：视图显示后再按真实尺寸重算一次透视（否则量到 0 会算错） */
    var _rebuild = function(){ sceneBuild(ROSTER[cur]); };
    if (window.requestAnimationFrame) requestAnimationFrame(_rebuild); else setTimeout(_rebuild, 0);
    vib(8);
  }

/* ==== SCENE_KIT_JS ==== */
/* ============================================================================
   真实场景引擎
   · 一点透视：地平线 hy=42%h，灭点 vx=50%w
     地板上一点 (xw∈[0,1] 横向, q∈(0,1] 透视因子，1=最近)：
        screenX = vx + (xw-0.5)*2*q*w*0.62
        screenY = hy + (h-hy)*q          （bottom = h - screenY）
        尺寸    ∝ q
     陈设、2D 立牌、3D 立牌**共用**这条公式 → 三者永远站在同一块地板上。
   · 材质与光色全部来自原图真实采样（_pet_scenes.json）
   · 建筑（天花/后墙/侧墙/地板/材质/光束）用 SVG 画，保证透视精确
   ============================================================================ */
var SC = __SCENES__ || {};
var CUT = __CUTOUTS__ || {};   /* 透明底抠图人物（来自原图 matting） */
var HYR = 0.42;

function _hx(h){ return [parseInt(h.slice(1,3),16), parseInt(h.slice(3,5),16), parseInt(h.slice(5,7),16)]; }
function _hex2(a){ return '#' + ('000000' + ((Math.round(a[0])<<16)|(Math.round(a[1])<<8)|Math.round(a[2])).toString(16)).slice(-6); }
function lc(h, f){ var a = _hx(h); for (var k=0;k<3;k++){ a[k] = f >= 0 ? a[k] + (255-a[k])*f : a[k]*(1+f); } return _hex2(a); }
function ra(h, al){ var a = _hx(h); return 'rgba(' + a[0] + ',' + a[1] + ',' + a[2] + ',' + al + ')'; }
function grad(id, st, x1,y1,x2,y2){
  return '<linearGradient id="' + id + '" x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '">' +
    st.map(function(o){ return '<stop offset="' + o[0] + '" stop-color="' + o[1] + '"/>'; }).join('') +
    '</linearGradient>';
}
function rgrad(id, st){
  return '<radialGradient id="' + id + '">' +
    st.map(function(o){ return '<stop offset="' + o[0] + '" stop-color="' + o[1] + '"/>'; }).join('') +
    '</radialGradient>';
}

/* 光照基调 → 环境色 / 影调 */
var LIGHT = {
  daylight:  {amb:'#FFF6E6', tint:'#BFE3FF', vig:.34, exp:1.00},
  sun:       {amb:'#FFF2D2', tint:'#A8DEFF', vig:.30, exp:1.04},
  bright:    {amb:'#FFFDF6', tint:'#CFE9FF', vig:.30, exp:1.06},
  spring:    {amb:'#FFF0F4', tint:'#DDF0E4', vig:.30, exp:1.02},
  snowlight: {amb:'#EAF4FF', tint:'#D6E8FA', vig:.30, exp:1.03},
  warm:      {amb:'#FFDC9E', tint:'#C79A5E', vig:.42, exp:.98},
  warmlamp:  {amb:'#FFD08A', tint:'#8A5A2E', vig:.46, exp:.96},
  lamp:      {amb:'#FFD79B', tint:'#7C5630', vig:.48, exp:.95},
  cool:      {amb:'#E4F2FF', tint:'#9FBFD8', vig:.36, exp:1.00},
  metal:     {amb:'#DCE8EF', tint:'#8EA3B2', vig:.40, exp:.98},
  cabin:     {amb:'#DCEBFF', tint:'#93A9C6', vig:.40, exp:.99},
  dim:       {amb:'#C9B9A6', tint:'#6B5A4C', vig:.52, exp:.92},
  rainy:     {amb:'#C8D6DE', tint:'#7F98A8', vig:.42, exp:.95},
  neon:      {amb:'#FF9ED8', tint:'#2A3A6E', vig:.56, exp:.95},
  fire:      {amb:'#FFC978', tint:'#2E3A52', vig:.54, exp:.98},
  dusk:      {amb:'#FFB86B', tint:'#6E5A7A', vig:.44, exp:.98},
  nightcity: {amb:'#9FB6D8', tint:'#2C3A5E', vig:.54, exp:.95},
  string:    {amb:'#FFE0A8', tint:'#5C6A54', vig:.46, exp:.99}
};

function persp(w, h){
  var hy = h * HYR, vx = w * 0.5;
  return {
    hy: hy, vx: vx,
    onFloor: function(xw, q){
      return { x: vx + (xw - 0.5) * 2 * q * w * 0.62, yb: h - (hy + (h - hy) * q), s: q };
    }
  };
}

/* ---------------- 地板材质纹理（SVG） ---------------- */
function floorTex(id, tex, w, h, hy, vx, base){
  var L = [];
  var clip = '<clipPath id="' + id + '"><polygon points="0,' + (h*1.25) + ' ' + (w*0.18) + ',' + hy + ' ' +
             (w*0.82) + ',' + hy + ' ' + w + ',' + (h*1.25) + '"/></clipPath>';
  var g = '<g clip-path="url(#' + id + ')">';
  var ln = lc(base, 0.18), ln2 = lc(base, -0.3);
  function vlines(n, op){
    var o = '';
    for (var k = -n; k <= n; k++){
      var x = vx + (k / n) * w * 0.85;
      o += '<line x1="' + vx + '" y1="' + hy + '" x2="' + x + '" y2="' + (h*1.25) + '" stroke="' + ln2 +
           '" stroke-opacity="' + op + '" stroke-width="1"/>';
    }
    return o;
  }
  function hlines(count, r, op){
    var o = '', y0 = h * 1.25, span = y0 - hy;
    for (var m = 1; m <= count; m++){
      var y = hy + span * Math.pow(r, -m);
      o += '<line x1="0" y1="' + y + '" x2="' + w + '" y2="' + y + '" stroke="' + ln2 +
           '" stroke-opacity="' + op + '" stroke-width="1"/>';
    }
    return o;
  }
  if (tex === 'plank' || tex === 'court' || tex === 'deck'){
    L.push(vlines(5, .16), hlines(9, 1.34, .2));
    if (tex === 'court'){
      L.push('<rect x="' + (w*0.22) + '" y="' + (hy + (h*0.06)) + '" width="' + (w*0.56) + '" height="' + (h*0.5) +
             '" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="2"/>');
      L.push('<line x1="' + vx + '" y1="' + hy + '" x2="' + vx + '" y2="' + (h*1.25) + '" stroke="#fff" stroke-opacity=".38" stroke-width="2"/>');
    }
  } else if (tex === 'tile' || tex === 'metal' || tex === 'pool'){
    L.push(vlines(6, .2), hlines(10, 1.3, .22));
    if (tex === 'metal' || tex === 'pool'){
      L.push('<ellipse cx="' + (vx) + '" cy="' + (hy + (h-hy)*0.3) + '" rx="' + (w*0.4) + '" ry="' + (h*0.1) +
             '" fill="' + lc(base, 0.5) + '" opacity=".22"/>');
    }
  } else if (tex === 'carpet'){
    L.push(hlines(7, 1.4, .07), vlines(4, .05));
  } else if (tex === 'asphalt'){
    L.push(hlines(6, 1.45, .1));
    L.push('<ellipse cx="' + (w*0.34) + '" cy="' + (hy + (h-hy)*0.55) + '" rx="' + (w*0.16) + '" ry="' + (h*0.045) +
           '" fill="' + lc(base, 0.55) + '" opacity=".3"/>');
    L.push('<ellipse cx="' + (w*0.68) + '" cy="' + (hy + (h-hy)*0.78) + '" rx="' + (w*0.2) + '" ry="' + (h*0.05) +
           '" fill="' + lc(base, 0.5) + '" opacity=".26"/>');
  } else if (tex === 'concrete'){
    L.push(hlines(5, 1.5, .12));
    L.push('<line x1="0" y1="' + (hy + (h-hy)*0.45) + '" x2="' + w + '" y2="' + (hy + (h-hy)*0.45) +
           '" stroke="' + ln2 + '" stroke-opacity=".3" stroke-width="3"/>');
  } else if (tex === 'snow'){
    L.push('<ellipse cx="' + (w*0.3) + '" cy="' + (hy + (h-hy)*0.4) + '" rx="' + (w*0.34) + '" ry="' + (h*0.09) +
           '" fill="#cfe2f5" opacity=".35"/>');
    L.push('<ellipse cx="' + (w*0.72) + '" cy="' + (hy + (h-hy)*0.7) + '" rx="' + (w*0.3) + '" ry="' + (h*0.08) +
           '" fill="#dceaf8" opacity=".3"/>');
  } else if (tex === 'grass'){
    for (var m2 = 0; m2 < 26; m2++){
      var gx = (m2 * 7919 % 100) / 100 * w, gq = 0.1 + ((m2 * 104729 % 100) / 100) * 0.9;
      var gy = hy + (h - hy) * gq;
      L.push('<line x1="' + gx + '" y1="' + gy + '" x2="' + (gx + 2) + '" y2="' + (gy - 5 * gq) +
             '" stroke="' + lc(base, 0.32) + '" stroke-opacity=".5" stroke-width="1.2"/>');
    }
  } else if (tex === 'sand'){
    for (var m3 = 1; m3 <= 7; m3++){
      var sy = hy + (h - hy) * Math.pow(1.36, -m3) * 1.2;
      L.push('<path d="M0,' + sy + ' Q' + (w*0.5) + ',' + (sy - 5) + ' ' + w + ',' + sy + '" fill="none" stroke="' +
             lc(base, 0.25) + '" stroke-opacity=".35" stroke-width="1.4"/>');
    }
  } else if (tex === 'stone'){
    var cols = ['0,0.30,0.10,0.42', '0.34,0.66,0.12,0.40', '0.70,1.0,0.10,0.42',
                '0.02,0.36,0.44,0.72', '0.38,0.64,0.46,0.74', '0.66,0.98,0.45,0.72',
                '0.05,0.42,0.74,1.0', '0.44,0.70,0.76,1.0', '0.68,1.0,0.75,1.0'];
    for (var ci = 0; ci < cols.length; ci++){
      var p4 = cols[ci].split(',');
      L.push('<polygon points="' + (p4[0]*w) + ',' + (h*1.2*(p4[2]-p4[2]) + hy + (h-hy)*parseFloat(p4[2])) + ' ' +
             (p4[1]*w) + ',' + (hy + (h-hy)*parseFloat(p4[2])) + ' ' +
             (p4[1]*w) + ',' + (hy + (h-hy)*parseFloat(p4[3])) + ' ' +
             (p4[0]*w) + ',' + (hy + (h-hy)*parseFloat(p4[3])) + '" fill="none" stroke="' + ln2 + '" stroke-opacity=".22"/>');
    }
  }
  return clip + g + L.join('') + '</g>';
}

/* ---------------- 建筑：天花 / 后墙 / 侧墙 / 地板 / 光 ---------------- */
function svgScene(w, h, d){
  var P = persp(w, h), hy = P.hy, vx = P.vx;
  var env = d.env, ceil = d.ceilKey || '';
  var wall = d.wall || '#8C8C8C', wall2 = d.wall2 || wall, floor = d.floor || '#6E6259', ceilC = d.ceil || '#B9B4AE';
  var wallD = lc(wall, -0.5), wallL = lc(wall, 0.14), flD = lc(floor, -0.42), flL = lc(floor, 0.2);
  var A = [], defs = [];
  /* 背景图（内嵌 WebP）由 .sc-far 铺底，SVG 只画半透明建筑叠在上面 —— 这里不再画环境板 */
  var WOP = env === 'out' ? 0.72 : 0.60;      /* 建筑填充不透明度（让背景图透出来） */
  defs.push(grad('gWallA', [[0, ra(wallL, WOP)], [1, ra(wallD, WOP)]], 0, 0, 0, 1));
  defs.push(grad('gSideL', [[0, ra(lc(wall, -0.62), WOP)], [1, ra(lc(wall, -0.16), WOP)]], 0, 0, 1, 0));
  defs.push(grad('gSideR', [[0, ra(lc(wall2, -0.16), WOP)], [1, ra(lc(wall2, -0.62), WOP)]], 0, 0, 1, 0));
  defs.push(grad('gCeil', [[0, ra(lc(ceilC, -0.3), Math.min(1, WOP + 0.18))], [1, ra(lc(ceilC, 0.1), Math.min(1, WOP + 0.18))]], 0, 1, 0, 0));
  defs.push(grad('gFloor', [[0, flD], [0.34, floor], [1, flL]], 0, 0, 0, 1));
  var indoor = (env !== 'out');
  var bTop = hy * (ceil === 'high' ? 0.40 : (ceil === 'low' ? 0.66 : 0.56));
  var bL = w * 0.18, bR = w * 0.82;

  if (indoor){
    if (ceil){
      A.push('<polygon points="0,0 ' + w + ',0 ' + bR + ',' + bTop + ' ' + bL + ',' + bTop + '" fill="url(#gCeil)"/>');
      A.push('<line x1="' + bL + '" y1="' + bTop + '" x2="' + bR + '" y2="' + bTop + '" stroke="' + lc(ceilC, -0.45) + '" stroke-opacity=".5"/>');
    } else {
      A.push('<rect x="0" y="0" width="' + w + '" height="' + bTop + '" fill="url(#gCeil)"/>');
    }
    A.push('<polygon points="0,0 ' + bL + ',' + bTop + ' ' + bL + ',' + hy + ' 0,' + (h*1.3) + '" fill="url(#gSideL)"/>');
    A.push('<polygon points="' + w + ',0 ' + bR + ',' + bTop + ' ' + bR + ',' + hy + ' ' + w + ',' + (h*1.3) + '" fill="url(#gSideR)"/>');
    A.push('<rect x="' + bL + '" y="' + bTop + '" width="' + (bR - bL) + '" height="' + (hy - bTop) +
           '" fill="url(#gWallA)"/>');
    A.push('<rect x="' + bL + '" y="' + (hy - Math.max(3, h*0.016)) + '" width="' + (bR - bL) + '" height="' + Math.max(3, h*0.016) +
           '" fill="' + lc(wall, -0.62) + '"/>');
    /* 后墙竖向分缝（板材感） */
    for (var k = 1; k <= 5; k++){
      var xx = bL + (bR - bL) * k / 6;
      A.push('<line x1="' + xx + '" y1="' + bTop + '" x2="' + xx + '" y2="' + hy + '" stroke="' + lc(wall, -0.28) + '" stroke-opacity=".24"/>');
    }
  }
  /* 地板 */
  A.push('<polygon points="0,' + (h*1.25) + ' ' + bL + ',' + hy + ' ' + bR + ',' + hy + ' ' + w + ',' + (h*1.25) +
         '" fill="url(#gFloor)"/>');
  A.push(floorTex('fclip', d.tex, w, h, hy, vx, floor));
  if (!indoor){
    A.push('<rect x="0" y="' + (hy - h*0.03) + '" width="' + w + '" height="' + (h*0.03) + '" fill="' + lc(floor, -0.3) + '" opacity=".55"/>');
  }
  /* 反光（临地平线的一层湿润高光） */
  A.push('<rect x="0" y="' + hy + '" width="' + w + '" height="' + (h*0.14) + '" fill="url(#gRef)" opacity="' +
         (d.tex === 'asphalt' || d.tex === 'pool' || d.tex === 'metal' ? 0.5 : 0.22) + '"/>');
  defs.push(grad('gRef', [[0, lc(floor, 0.55)], [1, ra(floor, 0)]], 0, 0, 0, 1));

  /* ---------------- 光 ---------------- */
  var lg = LIGHT[d.lightKey] || LIGHT.daylight;
  var mods = (d.mods || []).slice();
  var allNames = (d.props || []).join(' ');
  if (/飞机|机坪/.test(allNames) && mods.indexOf('plane') < 0) mods.push('plane');
  if (/楼群|城市/.test(allNames) && mods.indexOf('skyline') < 0) mods.push('skyline');
  function has(m){ return mods.indexOf(m) >= 0; }
  if (indoor && (has('glasswall') || has('window') || d.lightKey === 'daylight' || d.lightKey === 'sun' ||
      d.lightKey === 'snowlight' || d.lightKey === 'bright' || d.lightKey === 'spring')){
    var wx = has('glasswall') ? bL : (bR - (bR-bL)*0.34), ww2 = has('glasswall') ? (bR-bL) : (bR-bL)*0.30;
    var wt = bTop + (hy-bTop)*0.12, wh = (hy-bTop)*0.72;
    defs.push(grad('gSky', [[0, lc(lg.tint, 0.5)], [0.55, lg.tint], [1, lc(lg.amb, 0.1)]], 0, 0, 0, 1));
    A.push('<rect x="' + wx + '" y="' + wt + '" width="' + ww2 + '" height="' + wh + '" fill="url(#gSky)"/>');
    A.push('<rect x="' + wx + '" y="' + wt + '" width="' + ww2 + '" height="' + wh + '" fill="none" stroke="' + lc(wall, -0.6) + '" stroke-width="2.5"/>');
    if (has('glasswall')){
      for (var m = 1; m <= 4; m++){
        var mx = wx + ww2 * m / 5;
        A.push('<line x1="' + mx + '" y1="' + wt + '" x2="' + mx + '" y2="' + (wt + wh) + '" stroke="' + lc(wall, -0.55) + '" stroke-width="2"/>');
      }
      A.push('<line x1="' + wx + '" y1="' + (wt + wh*0.52) + '" x2="' + (wx+ww2) + '" y2="' + (wt + wh*0.52) + '" stroke="' + lc(wall, -0.55) + '" stroke-width="2"/>');
    }
    /* 光束落到地板 */
    defs.push(grad('gShaft', [[0, ra(lg.amb, .42)], [1, ra(lg.amb, 0)]], 0, 0, 0, 1));
    A.push('<polygon points="' + wx + ',' + (wt+wh) + ' ' + (wx+ww2) + ',' + (wt+wh) + ' ' +
           (wx + ww2*1.5) + ',' + (h*1.2) + ' ' + (wx - ww2*0.5) + ',' + (h*1.2) + '" fill="url(#gShaft)" opacity=".55"/>');
  }
  if (has('ceilingstrip')){
    for (var s2 = 0; s2 < 3; s2++){
      var sy = bTop * (0.26 + s2*0.24), sw = (bR-bL) * (0.5 - s2*0.09);
      A.push('<rect x="' + (vx - sw/2) + '" y="' + sy + '" width="' + sw + '" height="' + Math.max(2, bTop*0.05) +
             '" rx="3" fill="' + lc(lg.amb, 0.25) + '" opacity=".8"/>');
    }
  }
  if (has('stringlights')){
    for (var c2 = 0; c2 < 3; c2++){
      var y0 = bTop + c2 * (hy-bTop)*0.28, amp = (hy-bTop)*0.16;
      var pts = '';
      for (var t2 = 0; t2 <= 16; t2++){
        var tx = bL + (bR-bL) * t2/16;
        var ty = y0 + Math.sin(t2/16*Math.PI) * amp;
        pts += tx + ',' + ty + ' ';
        if (t2 % 2 === 0) A.push('<circle cx="' + tx + '" cy="' + ty + '" r="' + Math.max(1.6, w*0.0035) +
             '" fill="' + (t2 % 4 === 0 ? '#FFE9A8' : '#9BFFD0') + '" opacity=".95"/>');
      }
      A.push('<polyline points="' + pts + '" fill="none" stroke="rgba(0,0,0,.35)" stroke-width="1.2"/>');
    }
    A.push('<circle cx="' + vx + '" cy="' + (bTop*0.4) + '" r="' + (w*0.16) + '" fill="url(#gWarm)" opacity=".28"/>');
    defs.push(rgrad('gWarm', [[0, '#FFD79B'], [1, 'rgba(255,215,155,0)']]));
  }
  if (has('neon')){
    var cols = ['#FF4D9E', '#4DD8FF'];
    for (var n2 = 0; n2 < 2; n2++){
      var ny = bTop + (hy-bTop) * (0.24 + n2*0.4), nx = bL + (bR-bL) * (n2 ? 0.42 : 0.12);
      A.push('<rect x="' + nx + '" y="' + ny + '" width="' + ((bR-bL)*0.3) + '" height="' + Math.max(4, h*0.014) +
             '" rx="4" fill="' + cols[n2] + '" opacity=".9"/>');
      A.push('<rect x="' + (nx - 6) + '" y="' + (ny - 8) + '" width="' + ((bR-bL)*0.3 + 12) + '" height="' + Math.max(20, h*0.03) +
             '" rx="10" fill="' + cols[n2] + '" opacity=".16"/>');
    }
    A.push('<ellipse cx="' + (vx) + '" cy="' + (hy + (h-hy)*0.5) + '" rx="' + (w*0.3) + '" ry="' + (h*0.06) +
           '" fill="#FF4D9E" opacity=".12"/>');
  }
  if (has('plane')){
    /* 机坪上的飞机剪影（远处地平线附近，别当家具放地板上） */
    var inWin = indoor && (has('glasswall') || has('window'));
    var plx = inWin ? (bL + (bR - bL) * 0.62) : (vx + (bR - bL) * 0.26);
    var ply = inWin ? (bTop + (hy - bTop) * 0.44) : (hy - (hy - bTop) * 0.16);
    var sc = (bR - bL) / 900;
    A.push('<g opacity=".58" transform="translate(' + plx.toFixed(1) + ',' + ply.toFixed(1) + ') scale(' + sc.toFixed(3) + ')">' +
      '<ellipse cx="0" cy="0" rx="132" ry="15" fill="' + lc(lg.tint, -0.34) + '"/>' +
      '<path d="M-18,-6 L-64,-48 L-38,-48 L6,-8 Z" fill="' + lc(lg.tint, -0.28) + '"/>' +
      '<path d="M-18,6 L-64,48 L-38,48 L6,8 Z" fill="' + lc(lg.tint, -0.28) + '"/>' +
      '<path d="M96,-2 L78,-30 L64,-30 L74,-2 Z" fill="' + lc(lg.tint, -0.3) + '"/>' +
      '<circle cx="104" cy="0" r="12" fill="' + lc(lg.tint, -0.24) + '"/>' +
      '</g>');
  }
  if (has('warnline')){
    A.push('<rect x="' + (bL) + '" y="' + (hy + (h-hy)*0.12) + '" width="' + (bR-bL) + '" height="' + (h*0.018) +
           '" fill="#F5C518" opacity=".55"/>');
    A.push('<rect x="' + (bL) + '" y="' + (hy + (h-hy)*0.34) + '" width="' + (bR-bL) + '" height="' + (h*0.018) +
           '" fill="#F5C518" opacity=".38"/>');
  }
  if (has('railing')){
    A.push('<rect x="0" y="' + (hy - h*0.17) + '" width="' + w + '" height="' + Math.max(2, h*0.008) +
           '" fill="' + lc(lg.tint, -0.2) + '" opacity=".75"/>');
    for (var rp = 0; rp <= 12; rp++){
      var rx = w * rp / 12;
      A.push('<rect x="' + rx + '" y="' + (hy - h*0.17) + '" width="' + Math.max(1.5, w*0.0025) + '" height="' + (h*0.17) +
             '" fill="' + lc(lg.tint, -0.3) + '" opacity=".5"/>');
    }
  }
  if (has('shutter')){
    A.push('<rect x="' + (bL + (bR-bL)*0.5) + '" y="' + (bTop + (hy-bTop)*0.18) + '" width="' + ((bR-bL)*0.36) +
           '" height="' + ((hy-bTop)*0.7) + '" fill="' + lc(wall, -0.5) + '"/>');
    for (var sh = 0; sh < 8; sh++){
      var shy = bTop + (hy-bTop)*(0.2 + sh*0.086);
      A.push('<line x1="' + (bL + (bR-bL)*0.5) + '" y1="' + shy + '" x2="' + (bL + (bR-bL)*0.86) + '" y2="' + shy +
             '" stroke="rgba(255,255,255,.12)"/>');
    }
  }
  if (has('skyline')){
    var bld = [0.06,0.16,0.05,0.22,0.09,0.28,0.12,0.19,0.07,0.24,0.1,0.16];
    for (var bi = 0; bi < 12; bi++){
      var bxx = w * bi / 12, bw = w/12 * 0.86, bh = (h-hy) * (0.2 + bld[bi]*2.4);
      A.push('<rect x="' + bxx + '" y="' + (hy - bh) + '" width="' + bw + '" height="' + bh + '" fill="' +
             lc(lg.tint, -0.5) + '" opacity=".82"/>');
      for (var wi = 0; wi < 6; wi++){
        if ((bi + wi) % 3 === 0) continue;
        A.push('<rect x="' + (bxx + bw*0.2 + (wi%2)*bw*0.36) + '" y="' + (hy - bh + bh*0.1 + Math.floor(wi/2)*bh*0.22) +
               '" width="' + (bw*0.16) + '" height="' + (bh*0.08) + '" fill="#FFE9A0" opacity=".55"/>');
      }
    }
  }
  if (has('stars')){
    for (var st2 = 0; st2 < 60; st2++){
      var sx = (st2 * 7919 % 1000) / 1000 * w, sy2 = (st2 * 104729 % 1000) / 1000 * (hy * 0.92);
      A.push('<circle cx="' + sx.toFixed(1) + '" cy="' + sy2.toFixed(1) + '" r="' + (0.7 + (st2 % 3) * 0.5) +
             '" fill="#fff" opacity="' + (0.35 + (st2 % 5) * 0.13) + '"/>');
    }
  }
  if (has('sea') || has('pool')){
    var wat = lc(lg.tint, 0.18), wy = hy + (h-hy) * 0.06;
    A.push('<rect x="0" y="' + wy + '" width="' + w + '" height="' + (h*1.25 - wy) + '" fill="' + wat + '" opacity=".92"/>');
    for (var wv = 1; wv <= 8; wv++){
      var q2 = Math.pow(1.33, -wv) * 1.15, yy = hy + (h-hy)*q2;
      A.push('<path d="M0,' + yy + ' Q' + (w*0.25) + ',' + (yy-4*q2) + ' ' + (w*0.5) + ',' + yy +
             ' T' + w + ',' + yy + '" fill="none" stroke="#fff" stroke-opacity="' + (0.34 - wv*0.03) + '" stroke-width="1.6"/>');
    }
  }
  if (has('corridor')){
    A.push('<rect x="0" y="' + (bTop + (hy-bTop)*0.16) + '" width="' + w + '" height="' + ((hy-bTop)*0.2) +
           '" fill="' + lc(wall, -0.62) + '"/>');
    for (var cp = 0; cp <= 8; cp++){
      A.push('<rect x="' + (w*cp/8) + '" y="' + (bTop + (hy-bTop)*0.16) + '" width="' + Math.max(3, w*0.008) +
             '" height="' + ((hy-bTop)*0.2) + '" fill="' + lc(wall, -0.7) + '"/>');
    }
  }
  if (has('slope')){
    A.push('<path d="M0,' + (hy + (h-hy)*0.1) + ' Q' + (w*0.4) + ',' + (hy - h*0.02) + ' ' + w + ',' + (hy + (h-hy)*0.26) +
           ' L' + w + ',' + (h*1.2) + ' L0,' + (h*1.2) + ' Z" fill="#E8F1FA" opacity=".9"/>');
  }
  if (has('puddle')){
    A.push('<ellipse cx="' + (w*0.36) + '" cy="' + (hy + (h-hy)*0.5) + '" rx="' + (w*0.14) + '" ry="' + (h*0.04) +
           '" fill="' + lc(lg.tint, 0.4) + '" opacity=".4"/>');
    A.push('<ellipse cx="' + (w*0.66) + '" cy="' + (hy + (h-hy)*0.74) + '" rx="' + (w*0.17) + '" ry="' + (h*0.045) +
           '" fill="' + lc(lg.tint, 0.32) + '" opacity=".34"/>');
  }
  /* ---- 环境密度：室内铺一块地毯，室外点几株草与石块，别让房间太空 ---- */
  if (indoor){
    var rgx = (bL + bR) / 2, rgy = hy + (h - hy) * 0.52;
    A.push('<ellipse cx="' + rgx + '" cy="' + rgy + '" rx="' + ((bR-bL)*0.34) + '" ry="' + ((h-hy)*0.2) +
           '" fill="' + lc(floor, 0.14) + '" opacity=".4"/>');
    A.push('<ellipse cx="' + rgx + '" cy="' + rgy + '" rx="' + ((bR-bL)*0.28) + '" ry="' + ((h-hy)*0.16) +
           '" fill="none" stroke="' + lc(floor, -0.24) + '" stroke-opacity=".35"/>');
    /* 墙上一块软木公告板 */
    A.push('<rect x="' + (bL + (bR-bL)*0.06) + '" y="' + (bTop + (hy-bTop)*0.16) + '" width="' + ((bR-bL)*0.15) +
           '" height="' + ((hy-bTop)*0.24) + '" fill="' + lc(wall, -0.2) + '" opacity=".7"/>');
  } else {
    for (var gi = 0; gi < 9; gi++){
      var gx2 = (gi * 7919 % 100) / 100 * w, gq2 = 0.10 + ((gi * 104729 % 100) / 100) * 0.86;
      var gy2 = hy + (h - hy) * gq2, gh2 = 4 + 10 * gq2;
      A.push('<path d="M' + gx2 + ',' + gy2 + ' q3,' + (-gh2*0.6) + ' 5,' + (-gh2) + ' M' + (gx2+4) + ',' + gy2 +
             ' q-3,' + (-gh2*0.5) + ' -5,' + (-gh2*0.9) + '" fill="none" stroke="' + lc(floor, -0.3) +
             '" stroke-opacity=".4" stroke-width="1.2"/>');
    }
    A.push('<ellipse cx="' + (w*0.22) + '" cy="' + (hy + (h-hy)*0.62) + '" rx="' + (w*0.022) + '" ry="' + (h*0.014) +
           '" fill="' + lc(floor, -0.34) + '" opacity=".5"/>');
    A.push('<ellipse cx="' + (w*0.82) + '" cy="' + (hy + (h-hy)*0.44) + '" rx="' + (w*0.016) + '" ry="' + (h*0.011) +
           '" fill="' + lc(floor, -0.3) + '" opacity=".45"/>');
  }
  return '<defs>' + defs.join('') + '</defs>' + A.join('');
}

/* ============================================================================
   陈设套件：每个模板返回「占自身盒子百分比」的内部 HTML
   c1/c2 = 主体色，c3 = 点缀色
   ========================================================================== */
function bx(cls, c1, c2, st){ return '<div class="' + cls + '" style="' + (st || '') + ';--c1:' + c1 + ';--c2:' + (c2 || c1) + '"></div>'; }

var TPL = {
  table: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'left:0;right:0;top:0;height:16%;border-radius:3px') +
    bx('fp', C.w2, C.w3, 'top:14%;width:5%;height:86%') +
    '<div style="position:absolute;left:0;right:0;top:16%;height:8%;background:rgba(0,0,0,.28)"></div>'; },
  counter: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'inset:0') + bx('ft', C.w3, C.w3, '') +
    bx('fb', C.w3, C.w3, 'left:0;right:0;top:0;height:11%;border-radius:3px') +
    bx('fb', lc(C.w2,-0.18), lc(C.w2,-0.26), 'left:8%;top:26%;width:36%;height:44%;border-radius:2px') +
    bx('fb', lc(C.w2,-0.18), lc(C.w2,-0.26), 'right:8%;top:26%;width:36%;height:44%;border-radius:2px') +
    '<div style="position:absolute;left:44%;top:44%;width:12%;height:4%;background:rgba(255,255,255,.5);border-radius:2px"></div>'; },
  cabinet: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'left:0;right:0;top:8%;bottom:0') +
    bx('fb', C.w3, C.w3, 'left:-3%;right:-3%;top:0;height:14%;border-radius:3px') +
    bx('fb', lc(C.w2,-0.24), lc(C.w2,-0.32), 'left:9%;top:22%;width:34%;height:66%;border-radius:2px') +
    bx('fb', lc(C.w2,-0.24), lc(C.w2,-0.32), 'right:9%;top:22%;width:34%;height:66%;border-radius:2px'); },
  chair: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w3, C.w2, 'left:0;right:0;bottom:26%;height:22%;border-radius:3px') +
    bx('fb', C.w3, C.w2, 'left:0;right:0;top:4%;height:26%;border-radius:4px') +
    bx('fp', C.w2, C.w1, 'top:48%;width:6%;height:54%') +
    bx('fp', lc(C.w2,-0.25), lc(C.w1,-0.25), 'top:44%;left:10%;width:6%;height:16%') +
    bx('fp', lc(C.w2,-0.25), lc(C.w1,-0.25), 'top:44%;left:auto;right:10%;width:6%;height:16%'); },
  sofa: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'left:6%;right:6%;top:0;height:44%;border-radius:6px') +
    bx('fb', C.w3, C.w2, 'left:0;right:0;bottom:24%;height:30%;border-radius:6px') +
    bx('fb', lc(C.w1,-0.2), lc(C.w2,-0.2), 'left:0;top:20%;width:9%;height:52%;border-radius:5px') +
    bx('fb', lc(C.w1,-0.2), lc(C.w2,-0.2), 'left:auto;right:0;top:20%;width:9%;height:52%;border-radius:5px') +
    bx('fp', C.w2, C.w1, 'top:70%;left:12%;width:6%;height:30%') +
    bx('fp', C.w2, C.w1, 'top:70%;right:12%;width:6%;height:30%'); },
  bench: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'left:0;right:0;top:20%;height:22%;border-radius:3px') +
    '<div style="position:absolute;left:0;right:0;top:34%;height:3%;background:rgba(0,0,0,.25)"></div>' +
    bx('fp', C.w2, C.w1, 'top:42%;left:8%;width:6%;height:58%') +
    bx('fp', C.w2, C.w1, 'top:42%;right:8%;width:6%;height:58%'); },
  shelf: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'inset:0') +
    bx('fb', lc(C.w2,-0.3), lc(C.w2,-0.38), 'left:5%;right:5%;top:6%;height:84%') +
    [0,1,2].map(function(r){
      var books = '';
      for (var b = 0; b < 7; b++){
        books += '<div style="position:absolute;left:' + (4 + b*13) + '%;bottom:0;width:10%;height:' + (52 + (b*37%40)) +
          '%;background:' + ['#C96A5A','#4E8F6B','#D8B45C','#5B7FB5','#B5729E','#7EA0C4','#C9964E'][b % 7] + ';border-radius:1px"></div>';
      }
      return '<div style="position:absolute;left:5%;right:5%;top:' + (6 + r*28) + '%;height:26%;overflow:hidden">' + books + '</div>';
    }).join(''); },
  lamp: function(C){ return '<div class="gd" style="left:50%;top:52%;width:260%;height:200%;transform:translate(-50%,-50%);--c1:' +
    ra(C.w3, .5) + '"></div>' +
    bx('fp', C.w2, C.w1, 'bottom:0;width:5%;height:' + (C.pole || 62) + '%') +
    '<div style="position:absolute;left:50%;bottom:' + (C.pole || 62) + '%;transform:translateX(-50%);width:' + (C.head || 40) +
    '%;height:' + (C.hh || 22) + '%;background:linear-gradient(180deg,' + lc(C.w3,0.2) + ',' + C.w2 +
    ');border-radius:50% 50% 22% 22%"></div>' +
    bx('lp', C.w3, C.w3, 'left:50%;bottom:' + ((C.pole || 62) - 4) + '%;transform:translateX(-50%);width:' + ((C.head||40)*0.5) +
    '%;height:' + ((C.hh||22)*0.5) + '%'); },
  pendant: function(C){ return '<div class="gd" style="left:50%;top:36%;width:240%;height:190%;transform:translate(-50%,-50%);--c1:' +
    ra(C.w3, .45) + '"></div>' +
    bx('fp', C.w2, C.w1, 'top:0;width:2.5%;height:42%') +
    '<div style="position:absolute;left:50%;top:40%;transform:translateX(-50%);width:' + (C.head||54) + '%;height:' + (C.hh||24) +
    '%;background:linear-gradient(180deg,' + lc(C.w3,0.25) + ',' + C.w2 + ');border-radius:50% 50% 30% 30%"></div>' +
    bx('lp', C.w3, C.w3, 'left:50%;top:58%;transform:translateX(-50%);width:' + ((C.head||54)*0.44) + '%;height:' + ((C.hh||24)*0.5) + '%'); },
  glasswall: function(C){ return bx('fb', lc(C.w3, .3), C.w3, 'inset:0;border-radius:4px') +
    '<div style="position:absolute;inset:6%;background:linear-gradient(180deg,rgba(255,255,255,.55),rgba(255,255,255,.1));border-radius:2px"></div>' +
    bx('fp', C.w2, C.w1, 'left:33%;top:0;height:100%;width:2.5%') +
    bx('fp', C.w2, C.w1, 'left:66%;top:0;height:100%;width:2.5%'); },
  window: function(C){ return bx('fb', C.w2, C.w1, 'inset:0;border-radius:4px') +
    '<div style="position:absolute;inset:9%;background:linear-gradient(180deg,' + lc(C.w3,.42) + ',' + lc(C.w3,.06) +
    ');border-radius:2px;overflow:hidden">' +
    '<div style="position:absolute;left:0;right:0;top:0;height:34%;background:rgba(255,255,255,.4)"></div>' +
    '<div style="position:absolute;left:12%;top:22%;width:1.6%;height:56%;background:rgba(255,255,255,.4);transform:rotate(14deg)"></div>' +
    '<div style="position:absolute;left:42%;top:14%;width:1.2%;height:66%;background:rgba(255,255,255,.32);transform:rotate(14deg)"></div>' +
    '</div>' +
    bx('fp', C.w2, C.w1, 'left:50%;top:9%;height:82%;width:2.2%') +
    bx('fb', C.w1, C.w2, 'left:-6%;right:-6%;bottom:-6%;height:10%;border-radius:2px'); },
  tree: function(C){ return '<div class="sh"></div>' +
    bx('fp', C.w2, lc(C.w1,-0.4), 'bottom:0;width:8%;height:46%') +
    bx('fo', C.w3, C.w3, 'left:14%;top:6%;width:72%;height:58%;opacity:.96') +
    bx('fo', lc(C.w3,.12), lc(C.w3,.12), 'left:2%;top:30%;width:46%;height:40%') +
    bx('fo', lc(C.w3,-0.12), lc(C.w3,-0.12), 'right:2%;top:28%;width:48%;height:42%'); },
  pine: function(C){ var t = '';
    [0,1,2].forEach(function(k){ t += '<div style="position:absolute;left:' + (14 - k*7) + '%;right:' + (14 - k*7) + '%;top:' +
      (8 + k*22) + '%;height:30%;background:linear-gradient(180deg,' + lc(C.w3,.08) + ',' + C.w3 +
      ');clip-path:polygon(50% 0,100% 100%,0 100%)"></div>'; });
    return '<div class="sh"></div>' + bx('fp', C.w2, lc(C.w1,-0.4), 'bottom:0;width:9%;height:26%') + t; },
  palm: function(C){ return '<div class="sh"></div>' +
    bx('fp', C.w2, lc(C.w1,-0.35), 'bottom:0;width:8%;height:72%;transform:translateX(-50%) rotate(6deg)') +
    [0,1,2,3,4].forEach ? [0,1,2,3,4].map(function(k){
      var ang = -80 + k * 40;
      return '<div style="position:absolute;left:50%;top:2%;width:56%;height:16%;background:linear-gradient(90deg,' + C.w3 + ',' +
        lc(C.w3,.2) + ');border-radius:50%;transform-origin:0 50%;transform:translate(-2%,0) rotate(' + ang + 'deg)"></div>';
    }).join('') : ''; },
  plane: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'left:6%;top:40%;width:88%;height:26%;border-radius:46% 12% 12% 46%') +
    '<div style="position:absolute;left:44%;top:62%;width:22%;height:26%;background:' + C.w2 +
    ';clip-path:polygon(0 0,100% 40%,100% 100%,0 60%)"></div>' +
    '<div style="position:absolute;left:16%;top:26%;width:36%;height:18%;background:' + lc(C.w2,.1) +
    ';clip-path:polygon(0 100%,30% 0,60% 100%)"></div>' +
    '<div style="position:absolute;left:34%;top:44%;width:1.8%;height:8%;background:rgba(255,255,255,.6);border-radius:50%"></div>' +
    '<div style="position:absolute;left:44%;top:44%;width:1.8%;height:8%;background:rgba(255,255,255,.6);border-radius:50%"></div>' +
    '<div style="position:absolute;left:54%;top:44%;width:1.8%;height:8%;background:rgba(255,255,255,.6);border-radius:50%"></div>'; },
  campfire: function(C){ return '<div class="gd" style="left:50%;bottom:8%;width:420%;height:320%;transform:translate(-50%,0);--c1:' +
    ra('#FF9A3C', .6) + '"></div>' +
    bx('fb', C.w2, lc(C.w1,-0.4), 'left:6%;bottom:0;width:88%;height:16%;border-radius:4px;transform:rotate(-8deg)') +
    bx('fb', C.w2, lc(C.w1,-0.42), 'left:6%;bottom:2%;width:88%;height:16%;border-radius:4px;transform:rotate(8deg)') +
    '<div style="position:absolute;left:50%;bottom:14%;transform:translateX(-50%);width:44%;height:84%;background:radial-gradient(60% 50% at 50% 70%,#FFF3B0,#FF9F2E 46%,rgba(255,110,20,.2) 74%,transparent);border-radius:50% 50% 44% 44%"></div>'; },
  tent: function(C){ return '<div class="sh"></div>' +
    '<div style="position:absolute;inset:0;background:linear-gradient(180deg,' + lc(C.w3,.14) + ',' + C.w3 +
    ');clip-path:polygon(50% 0,100% 100%,0 100%)"></div>' +
    '<div style="position:absolute;left:42%;bottom:0;width:16%;height:62%;background:' + lc(C.w3,-0.42) +
    ';clip-path:polygon(50% 0,100% 100%,0 100%)"></div>'; },
  piano: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'left:0;right:0;bottom:26%;height:40%;border-radius:5px') +
    '<div style="position:absolute;left:2%;right:-14%;bottom:60%;height:26%;background:' + lc(C.w1,.06) +
    ';transform:skewX(-24deg);border-radius:4px;box-shadow:0 3px 6px rgba(0,0,0,.4)"></div>' +
    bx('fb', '#F3EFE6', '#DCD6C8', 'left:6%;right:6%;bottom:26%;height:9%;border-radius:2px') +
    bx('fp', C.w2, C.w1, 'bottom:0;left:12%;width:5%;height:27%') +
    bx('fp', C.w2, C.w1, 'bottom:0;right:12%;width:5%;height:27%'); },
  board: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'inset:0;border-radius:3px') +
    [0,1,2,3].map(function(r){
      return '<div style="position:absolute;left:10%;top:' + (16 + r*19) + '%;width:' + (48 + (r*23 % 34)) + '%;height:8%;background:' +
        (r === 0 ? '#FFD24D' : 'rgba(255,255,255,.62)') + ';border-radius:2px"></div>';
    }).join('') +
    bx('fp', C.w2, lc(C.w1,-0.3), 'bottom:0;width:6%;height:14%'); },
  neon: function(C){ return '<div class="gd" style="left:50%;top:44%;width:340%;height:260%;transform:translate(-50%,-50%);--c1:' +
    ra(C.w3, .5) + '"></div>' +
    bx('fb', C.w1, C.w2, 'inset:0;border-radius:8px') +
    '<div style="position:absolute;left:8%;right:8%;top:34%;height:18%;background:' + C.w3 + ';border-radius:6px"></div>' +
    '<div style="position:absolute;left:16%;right:16%;top:62%;height:12%;background:' + C.w3 + ';border-radius:6px;opacity:.7"></div>'; },
  seatrow: function(C){ return '<div class="sh"></div>' +
    [0,1,2].map(function(k){
      return '<div style="position:absolute;left:' + (k*34) + '%;width:32%;top:0;bottom:0">' +
        '<div class="fb" style="left:0;right:0;top:22%;height:34%;--c1:' + C.w3 + ';--c2:' + C.w2 + ';border-radius:5px"></div>' +
        '<div class="fb" style="left:6%;right:6%;bottom:14%;height:26%;--c1:' + lc(C.w1,-0.05) + ';--c2:' + C.w2 + ';border-radius:4px"></div>' +
        '<div class="fp" style="bottom:0;width:9%;height:16%;--c1:' + C.w2 + ';--c2:' + C.w1 + '"></div>' +
        '</div>';
    }).join(''); },
  trolley: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'left:0;right:0;top:10%;bottom:14%;border-radius:3px') +
    bx('fb', lc(C.w3,.1), C.w3, 'left:-3%;right:-3%;top:0;height:13%;border-radius:3px') +
    '<div style="position:absolute;left:12%;bottom:16%;width:16%;height:16%;background:#2B2B2B;border-radius:50%"></div>' +
    '<div style="position:absolute;right:12%;bottom:16%;width:16%;height:16%;background:#2B2B2B;border-radius:50%"></div>' +
    bx('fp', C.w2, C.w1, 'bottom:0;left:20%;width:8%;height:16%') +
    bx('fp', C.w2, C.w1, 'bottom:0;right:20%;width:8%;height:16%'); },
  cart: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'left:0;right:0;top:16%;height:48%;border-radius:3px') +
    bx('fp', C.w2, C.w1, 'top:6%;left:12%;width:5%;height:14%') +
    bx('fp', C.w2, C.w1, 'top:6%;right:12%;width:5%;height:14%') +
    '<div style="position:absolute;left:14%;bottom:6%;width:18%;height:18%;background:#232323;border-radius:50%"></div>' +
    '<div style="position:absolute;right:14%;bottom:6%;width:18%;height:18%;background:#232323;border-radius:50%"></div>'; },
  stand: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'left:8%;right:8%;top:0;height:64%;border-radius:2px;transform:skewY(-3deg)') +
    bx('fp', C.w2, C.w1, 'bottom:0;left:20%;width:6%;height:38%;transform:rotate(9deg)') +
    bx('fp', C.w2, C.w1, 'bottom:0;right:20%;width:6%;height:38%;transform:rotate(-9deg)') +
    bx('fp', C.w2, C.w1, 'bottom:0;left:50%;width:6%;height:34%'); },
  boat: function(C){ return '<div class="sh"></div>' +
    '<div style="position:absolute;left:0;right:0;bottom:14%;height:60%;background:linear-gradient(180deg,' + C.w3 + ',' + lc(C.w3,-0.2) +
    ');border-radius:40% 40% 46% 46%"></div>' +
    bx('fb', C.w1, C.w2, 'left:6%;right:6%;bottom:0;height:22%;border-radius:0 0 40% 40%'); },
  lounge: function(C){ return '<div class="sh"></div>' +
    '<div style="position:absolute;left:0;right:0;bottom:18%;height:30%;background:' + C.w3 + ';border-radius:5px;transform:skewX(-6deg)"></div>' +
    '<div style="position:absolute;left:0;right:0;bottom:44%;height:26%;background:' + lc(C.w3,.08) + ';border-radius:5px;transform:rotate(-14deg);transform-origin:0 100%"></div>' +
    bx('fp', C.w2, C.w1, 'bottom:0;left:12%;width:6%;height:20%') +
    bx('fp', C.w2, C.w1, 'bottom:0;right:14%;width:6%;height:20%'); },
  cup: function(C){ return '<div class="gd" style="left:50%;bottom:30%;width:200%;height:170%;transform:translate(-50%,0);--c1:' +
    ra(C.w3, .3) + '"></div>' +
    bx('fc', lc(C.w1,.16), C.w2, 'left:18%;right:18%;bottom:8%;height:66%') +
    bx('fb', C.w3, lc(C.w3,-0.12), 'left:14%;right:14%;bottom:66%;height:12%;border-radius:3px') +
    '<div style="position:absolute;left:74%;bottom:34%;width:16%;height:22%;border:2.5px solid ' + lc(C.w1,.1) +
    ';border-radius:50%;border-left-color:transparent"></div>'; },
  bowl: function(C){ return '<div class="sh"></div>' +
    '<div style="position:absolute;left:8%;right:8%;bottom:8%;height:56%;background:linear-gradient(180deg,' + lc(C.w3,.28) + ',' +
    C.w3 + ');border-radius:0 0 60% 60%/0 0 100% 100%"></div>' +
    '<div style="position:absolute;left:4%;right:4%;bottom:60%;height:10%;background:' + lc(C.w3,.4) + ';border-radius:50%"></div>' +
    bx('fo', '#E4574E', '#C43F38', 'left:34%;top:24%;width:18%;height:30%') +
    bx('fo', '#5FA35E', '#3E7C3F', 'left:52%;top:30%;width:14%;height:24%'); },
  pot: function(C){ return '<div class="sh"></div>' +
    '<div style="position:absolute;left:28%;right:28%;bottom:6%;height:44%;background:linear-gradient(180deg,' + C.w1 + ',' + C.w2 +
    ');border-radius:3px 3px 34% 34%"></div>' +
    bx('fo', C.w3, lc(C.w3,-0.2), 'left:36%;top:0;width:28%;height:34%') +
    bx('fo', lc(C.w3,.16), lc(C.w3,.1), 'left:16%;top:16%;width:24%;height:28%') +
    bx('fo', lc(C.w3,-0.1), lc(C.w3,-0.24), 'right:16%;top:20%;width:24%;height:28%'); },
  box: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'inset:0;border-radius:3px') +
    bx('fb', C.w3, C.w3, 'left:42%;top:0;width:16%;height:100%') +
    bx('fb', lc(C.w3,.15), C.w3, 'left:0;right:0;top:56%;height:15%'); },
  luggage: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'left:4%;right:4%;top:14%;bottom:10%;border-radius:5px') +
    [0,1].map(function(k){ return '<div style="position:absolute;left:' + (16 + k*40) + '%;top:24%;width:22%;height:52%;border:1.5px solid rgba(255,255,255,.24);border-radius:3px"></div>'; }).join('') +
    bx('fb', C.w2, C.w1, 'left:34%;top:4%;width:32%;height:13%;border-radius:5px') +
    '<div style="position:absolute;left:18%;bottom:6%;width:12%;height:11%;background:#222;border-radius:50%"></div>' +
    '<div style="position:absolute;right:18%;bottom:6%;width:12%;height:11%;background:#222;border-radius:50%"></div>'; },
  gate: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'left:0;width:34%;top:0;bottom:0;border-radius:3px') +
    bx('fb', C.w1, C.w2, 'right:0;width:34%;top:0;bottom:0;border-radius:3px') +
    bx('fb', lc(C.w3,.1), C.w3, 'left:34%;right:34%;top:10%;height:16%;border-radius:3px') +
    '<div style="position:absolute;left:40%;top:34%;right:40%;height:44%;background:rgba(255,255,255,.14);border-radius:3px"></div>'; },
  rack: function(C){ return '<div class="sh"></div>' +
    bx('fp', C.w2, C.w1, 'left:6%;top:0;bottom:0;width:6%') +
    bx('fp', C.w2, C.w1, 'right:6%;top:0;bottom:0;width:6%') +
    [0,1,2].map(function(k){ return bx('fb', C.w3, C.w2, 'left:12%;right:12%;top:' + (6 + k*30) + '%;height:24%;'); }).join('') +
    bx('fb', lc(C.w1,.08), C.w2, 'left:-8%;top:8%;width:34%;height:78%;border-radius:2px;transform:rotate(-9deg)'); },
  robotarm: function(C){ var seg = '';
    [0,1,2].forEach(function(k){
      seg += '<div style="position:absolute;left:' + (30 - k*4) + '%;bottom:' + (12 + k*26) + '%;width:16%;height:30%;background:' +
        lc(C.w1, k*0.08) + ';border-radius:4px;transform:rotate(' + (k*9) + 'deg)"></div>' +
        '<div style="position:absolute;left:' + (33 - k*4) + '%;bottom:' + (40 + k*26) + '%;width:12%;height:11%;background:' +
        C.w3 + ';border-radius:50%"></div>';
    });
    return '<div class="sh"></div>' + bx('fb', C.w2, lc(C.w1,-0.3), 'left:16%;right:16%;bottom:0;height:13%;border-radius:4px') + seg; },
  stove: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'inset:0;border-radius:4px') +
    '<div style="position:absolute;left:12%;right:12%;top:22%;height:34%;background:radial-gradient(circle at 50% 50%,#FF8A3C,rgba(255,90,20,.2));border-radius:6px"></div>' +
    bx('fp', C.w2, C.w1, 'bottom:0;left:16%;width:6%;height:16%') +
    bx('fp', C.w2, C.w1, 'bottom:0;right:16%;width:6%;height:16%'); },
  sofa2: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'left:4%;right:4%;top:8%;height:38%;border-radius:7px') +
    bx('fb', lc(C.w3,.1), C.w2, 'left:0;right:0;bottom:26%;height:30%;border-radius:6px') +
    bx('fb', lc(C.w1,-0.2), lc(C.w2,-0.2), 'left:0;top:24%;width:8%;height:50%;border-radius:5px') +
    bx('fb', lc(C.w1,-0.2), lc(C.w2,-0.2), 'left:auto;right:0;top:24%;width:8%;height:50%;border-radius:5px'); },
  cloth: function(C){ return '<div class="sh"></div>' +
    '<div style="position:absolute;inset:8%;background:linear-gradient(160deg,' + C.w3 + ',' + lc(C.w3,-0.18) +
    ');border-radius:8px;transform:rotate(-4deg)"></div>' +
    '<div style="position:absolute;left:14%;right:14%;bottom:12%;height:22%;background:rgba(255,255,255,.16);border-radius:6px"></div>'; },
  plank: function(C){ return '<div class="sh"></div>' +
    '<div style="position:absolute;left:44%;top:0;bottom:0;width:13%;background:linear-gradient(180deg,' + C.w3 + ',' + lc(C.w3,-0.3) +
    ');border-radius:40% 40% 14% 14%;transform:rotate(6deg)"></div>' +
    '<div style="position:absolute;left:20%;top:26%;width:46%;height:14%;background:' + lc(C.w1,.2) + ';border-radius:40%;transform:rotate(10deg)"></div>' +
    '<div style="position:absolute;left:26%;bottom:18%;width:42%;height:12%;background:' + lc(C.w1,.2) + ';border-radius:40%;transform:rotate(-8deg)"></div>'; },
  ring: function(C){ return '<div class="sh"></div>' +
    '<div style="position:absolute;inset:0;border:14px solid ' + C.w3 + ';border-radius:50%;box-shadow:inset 0 0 0 3px ' +
    lc(C.w3,.3) + '"></div>' +
    [0,1,2,3].map(function(k){ return '<div style="position:absolute;inset:14%;border:3px solid ' + C.w3 + ';border-radius:50%;transform:rotate(' + (k*45) + 'deg) scaleX(.28);opacity:.7"></div>'; }).join(''); },
  net: function(C){ return '<div class="sh"></div>' +
    '<div style="position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.5) 1.5px,transparent 1.5px),linear-gradient(90deg,rgba(255,255,255,.5) 1.5px,transparent 1.5px);background-size:16% 14%"></div>' +
    bx('fp', C.w1, C.w2, 'left:0;top:0;bottom:0;width:5%') +
    bx('fp', C.w1, C.w2, 'right:0;top:0;bottom:0;width:5%'); },
  hoop: function(C){ return '<div class="sh"></div>' +
    bx('fp', C.w2, C.w1, 'left:46%;top:0;bottom:0;width:7%') +
    '<div style="position:absolute;left:20%;top:0;width:52%;height:16%;background:' + C.w3 + ';border-radius:3px"></div>' +
    '<div style="position:absolute;left:30%;top:16%;width:34%;height:11%;border:2.5px solid #FF6A3D;border-radius:3px"></div>' +
    '<div style="position:absolute;left:24%;top:26%;width:46%;height:20%;background-image:linear-gradient(90deg,rgba(255,255,255,.5) 1.4px,transparent 1.4px);background-size:18% 100%"></div>'; },
  vending: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'inset:0;border-radius:3px') +
    '<div style="position:absolute;left:10%;right:22%;top:11%;height:48%;background:' + lc(C.w3,.34) + ';border-radius:3px"></div>' +
    [0,1].map(function(r){ return [0,1].map(function(cc){
      return '<div style="position:absolute;left:' + (14 + cc*32) + '%;top:' + (15 + r*21) + '%;width:24%;height:15%;background:' +
        (r*2+cc ? '#4E8F6B' : '#D8B45C') + ';border-radius:2px"></div>'; }).join(''); }).join('') +
    '<div style="position:absolute;right:12%;top:16%;width:9%;height:7%;background:#26262A;border-radius:2px"></div>'; },
  bus: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'left:0;right:0;top:16%;height:52%;border-radius:5px') +
    '<div style="position:absolute;left:6%;top:24%;right:6%;height:22%;background:' + lc(C.w3,.4) + ';border-radius:3px"></div>' +
    '<div style="position:absolute;left:18%;bottom:8%;width:18%;height:20%;background:#232323;border-radius:50%"></div>' +
    '<div style="position:absolute;right:18%;bottom:8%;width:18%;height:20%;background:#232323;border-radius:50%"></div>'; },
  umbrella: function(C){ return '<div class="sh"></div>' +
    bx('fp', C.w2, C.w1, 'bottom:0;width:5%;height:66%') +
    '<div style="position:absolute;left:4%;right:4%;top:0;height:40%;background:linear-gradient(180deg,' + lc(C.w3,.35) + ',' + C.w3 +
    ');border-radius:50% 50% 16% 16%;opacity:.86"></div>'; },
  console: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'left:12%;right:12%;bottom:6%;height:66%;border-radius:4px') +
    '<div style="position:absolute;left:20%;right:20%;bottom:44%;height:22%;background:' + C.w3 + ';border-radius:2px"></div>' +
    bx('fb', C.w2, C.w1, 'left:6%;right:6%;top:4%;height:16%;border-radius:3px') +
    [0,1].map(function(k){ return '<div style="position:absolute;left:' + (14 + k*66) + '%;top:8%;width:10%;height:7%;background:rgba(255,255,255,.5);border-radius:2px"></div>'; }).join(''); },
  plush: function(C){ return '<div class="sh"></div>' +
    bx('fo', C.w3, lc(C.w3,-0.15), 'left:18%;top:14%;width:64%;height:60%') +
    bx('fo', lc(C.w3,.14), lc(C.w3,.06), 'left:8%;top:2;width:30%;height:30%;top:0') +
    bx('fo', lc(C.w3,.14), lc(C.w3,.06), 'right:8%;top:0;width:30%;height:30%') +
    bx('fo', lc(C.w3,-0.15), lc(C.w3,-0.3), 'left:34%;top:72%;width:32%;height:22%'); },
  seat: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'left:0;right:0;bottom:22%;height:30%;border-radius:4px') +
    bx('fb', C.w1, C.w2, 'left:4%;right:4%;top:12%;height:30%;border-radius:4px') +
    bx('fp', C.w2, C.w1, 'bottom:0;left:14%;width:7%;height:24%') +
    bx('fp', C.w2, C.w1, 'bottom:0;right:14%;width:7%;height:24%'); },
  generic: function(C){ return '<div class="sh"></div>' +
    bx('fb', C.w1, C.w2, 'left:10%;right:10%;bottom:0;height:62%;border-radius:3px') +
    bx('fo', C.w3, lc(C.w3,-0.2), 'left:26%;top:2%;width:48%;height:48%'); }
};
/* 陈设名 → 模板（按关键词匹配，先命中的赢） */
var KWMAP = [
  [/落地窗|舷窗/, 'glasswall'], [/窗/, 'window'],
  [/钢琴/, 'piano'], [/谱架/, 'stand'],
  [/书架/, 'shelf'], [/档案盒|礼物箱|礼盒/, 'box'], [/蛋糕柜|柜/, 'cabinet'],
  [/料理台|吧台|台面/, 'counter'], [/桌/, 'table'],
  [/短沙发|沙发/, 'sofa'], [/长椅|候机椅|折叠椅/, 'bench'], [/椅|窗边座/, 'chair'],
  [/躺椅/, 'lounge'], [/座椅排/, 'seatrow'],
  [/吊灯|彩灯/, 'pendant'], [/灯/, 'lamp'],
  [/圣诞树|花树|椰树/, 'tree'], [/松树/, 'pine'],
  [/飞机|机坪/, '__skip'], [/机械臂/, 'robotarm'], [/护板架/, 'rack'],
  [/餐车|行李车/, 'trolley'], [/班车/, 'bus'], [/自动售货机/, 'vending'], [/闸机/, 'gate'],
  [/篝火/, 'campfire'], [/帐篷/, 'tent'], [/暖炉|烤箱/, 'stove'],
  [/球网/, 'net'], [/球筐/, 'hoop'],
  [/行李箱/, 'luggage'], [/伞/, 'umbrella'], [/游戏机/, 'console'], [/玩偶/, 'plush'],
  [/毯|罩衫/, 'cloth'], [/滑雪板|冲浪板/, 'plank'], [/救生圈/, 'ring'],
  [/咖啡|拿铁|橙汁|冰饮|茶壶|碟/, 'cup'], [/碗|草莓/, 'bowl'],
  [/霓虹/, 'neon'], [/卷帘门|警示线/, 'board'], [/牌/, 'board'],
  [/楼群|黄昏|水洼|池水|白浪|白沙|薄雪|雪坡|绿硬地|雨痕|星空|落瓣|木廊/, '__skip'],
  [/植物|绿植/, 'pot'], [/水壶|杯/, 'cup']
];
function tplOf(name){
  for (var k = 0; k < KWMAP.length; k++){ if (KWMAP[k][0].test(name)) return KWMAP[k][1]; }
  return 'generic';
}

/* 每个模板的「q=1 时的基准尺寸」(宽, 高) 与配色取法 */
var SIZE = {
  table:[86,46], counter:[96,50], cabinet:[62,78], chair:[44,56], sofa:[116,54], sofa2:[120,56],
  bench:[104,42], shelf:[70,92], lamp:[34,64], pendant:[44,40], glasswall:[150,108], window:[96,84],
  tree:[78,104], pine:[66,110], palm:[86,116], plane:[128,50], campfire:[52,36], tent:[104,76],
  piano:[112,66], board:[60,72], neon:[62,44], seatrow:[124,54], trolley:[52,64], cart:[58,46],
  stand:[34,54], boat:[96,40], lounge:[86,42], cup:[24,26], bowl:[34,24], pot:[30,36], box:[42,38],
  luggage:[40,52], gate:[104,56], rack:[74,80], robotarm:[70,92], stove:[56,54], cloth:[56,40],
  plank:[26,86], ring:[40,40], net:[110,52], hoop:[64,110], vending:[48,74], bus:[104,48],
  umbrella:[48,74], console:[50,42], plush:[38,40], seat:[44,54], generic:[38,36]
};
var KC = {   /* 模板默认配色（会被房间主色替换两个） */
  wood:'#8A6242', dark:'#3A3A3E', light:'#E6E1D6', steel:'#B9C2C8'
};

function sceneBuild(c){
  var d = SC[String(c.i)] || {};
  var r = $('room');
  var w = r.clientWidth || 390, h = r.clientHeight || 300;
  var p = c.pal || {};
  var lg = LIGHT[d.lightKey] || LIGHT.daylight;
  r.setAttribute('data-env', d.env || 'in');
  r.style.setProperty('--farB', (d.env === 'out' ? 1.02 : 0.94));
  r.style.setProperty('--vig', String(lg.vig));
  /* 环境板 / 房间背景（2026-09-14：可切换为「原稿原图直出」） */
  var far = $('scFar');
  var blu = $('scBlur');
  if (!SHOW_HERO2D) r.classList.add('no2d'); else r.classList.remove('no2d');
  if (far){
    /* 注意：绝不能在这里再写 far.style.background（简写会清掉刚设的 backgroundImage） */
    var bg = BDR[String(c.i)] || '';
    far.classList.remove('real', 'orig');
    r.classList.remove('realbg');
    if (bg){
      /* 背景图已 base64 内嵌进页面：不依赖任何外部文件，也不需要预加载探测 */
      far.style.backgroundImage = 'url("' + bg + '")';
      far.classList.add('real');
      r.classList.add('realbg');            /* 背景图本身当场景，SVG 建筑退到近透明 */
      if (BG_ORIG){
        /* 原图直出：铺满房间，取景往上压（把人像头部留在画面里）。
           ORI_FIT='full' 时改成整张完整可见、两侧虚化补边 */
        far.classList.add('orig');
        if (blu) blu.style.backgroundImage = 'url("' + bg + '")';
        if (ORI_FIT === 'full'){
          far.classList.add('full');
          far.style.backgroundPosition = '';        /* 交给 .full 的 center bottom */
          var ar = ORIAR[String(c.i)] || 0.66667;
          if (w / h > ar * 1.12){
            /* 宽幅房间：contain，整张完整可见 + 两侧羽化 */
            far.classList.remove('nofx');
            var aw = h * ar;
            far.style.top = '0'; far.style.bottom = '0';
            far.style.left = ((w - aw) / 2 / w * 100).toFixed(3) + '%';
            far.style.width = (aw / w * 100).toFixed(3) + '%';
            far.style.right = 'auto';
            far.style.backgroundSize = '100% 100%';
          } else {
            /* 房间比例接近原稿（手机竖屏）：直接铺满，几乎不裁人 */
            far.classList.add('nofx');
            far.style.top = '0'; far.style.bottom = '0';
            far.style.left = '0'; far.style.width = '100%'; far.style.right = 'auto';
            far.style.backgroundSize = 'cover';
          }
        } else {
          far.classList.remove('full');
          far.style.top = ''; far.style.bottom = ''; far.style.left = '';
          far.style.width = ''; far.style.right = '';
          far.style.backgroundPosition = 'center ' +
            (ORI_POS[String(c.i)] || ORI_POS_DEF) + '%';
        }
      } else {
        far.style.top = ''; far.style.bottom = ''; far.style.left = '';
        far.style.width = ''; far.style.right = '';
        far.style.backgroundPosition = '';
        if (blu) blu.style.backgroundImage = 'none';
      }
    } else {
      if (blu) blu.style.backgroundImage = 'none';
      far.style.top = ''; far.style.bottom = ''; far.style.left = '';
      far.style.width = ''; far.style.right = '';
      far.style.backgroundSize = ''; far.style.backgroundPosition = '';
      far.style.backgroundImage = 'none';
      far.style.backgroundImage = 'linear-gradient(180deg,' + (p.sky1 || '#123') + ',' + (p.sky2 || '#012') + ')';
    }
  }
  /* 建筑：已停用。背景图本身就是场景，再叠一层半透明 SVG 建筑会在照片上留下
     "幽灵矩形"（看上去像图片没加载出来的占位符）→ 一律不画。需要恢复把 SHOW_SVG 改回 true */
  var sv = $('scSvg');
  if (sv){
    if (!SHOW_SVG){
      sv.innerHTML = '';
      sv.style.display = 'none';
    } else {
      sv.style.display = '';
      var mw = Math.max(200, Math.round(w)), mh = Math.max(120, Math.round(h));
      sv.setAttribute('viewBox', '0 0 ' + mw + ' ' + mh);
      var dd = {}; for (var kk in d) dd[kk] = d[kk]; dd.props = (c.roomProp || []);
      sv.innerHTML = svgScene(mw, mh, dd);
    }
  }
  /* 陈设：已停用（用户 2026-09-14：「删除现在 CC 之家里的全部图片和背景，用新的背景图代替」）
     —— 一律用背景图当场景，旧的 CSS 道具/图标层全部撤掉，避免压在照片上显脏、且与立牌撞位
     需要恢复时把 SHOW_PROPS 改回 true 即可，模板代码保留在下方 */
  var fu = $('scFurn');
  if (fu && !SHOW_PROPS) fu.innerHTML = '';
  if (fu && SHOW_PROPS){
    var props = (c.roomProp || []).slice(0, 6);
    var P = persp(w, h);
    var U = Math.max(0.72, Math.min(1.32, w / 420));
    var spots = [[0.18,0.72],[0.38,0.58],[0.30,0.92],[0.10,0.64],[0.52,0.86],[0.62,0.50]];
    var html = props.map(function(nm, k){
      var kind = tplOf(nm);
      if (kind === '__skip' || kind === 'glasswall' || kind === 'window') return '';
      var sp = spots[k % spots.length];
      var q = sp[1];
      var sz = SIZE[kind] || SIZE.generic;
      var iw = sz[0] * U * q, ih = sz[1] * U * q;
      var pos = P.onFloor(sp[0], q);
      var C = {
        w1: k % 2 ? lc(p.accent || '#00A650', -0.3) : (p.floor ? lc(p.floor, -0.2) : KC.wood),
        w2: lc(p.floor || '#6E6259', -0.45),
        w3: lc(p.accent || '#00A650', 0.12)
      };
      return '<div class="it" style="left:' + (pos.x / w * 100).toFixed(2) + '%;' +
        'bottom:' + Math.max(1.5, pos.yb / h * 100 - 5.5).toFixed(2) + '%;' +
        'width:' + (iw / w * 100).toFixed(2) + '%;height:' + (ih / h * 100).toFixed(2) + '%;' +
        'z-index:' + Math.round(q * 60) + ';' +
        'opacity:' + (0.62 + q * 0.38).toFixed(2) + ';' +
        'filter:blur(' + ((1 - q) * 1.5).toFixed(2) + 'px) contrast(' + (0.9 + q * 0.14).toFixed(2) + ');' +
        'transform:translateX(-50%) scale(1)">' + TPL[kind](C) + '</div>';
    }).join('');
    fu.innerHTML = html;
  }
  /* 立牌（2D 与 3D 共用同一透视公式，站在同一块地板上） */
  var P2 = persp(w, h);
  var bh = h * 0.76 * 0.80;   /* 高度 ∝ q */
  var bw2 = bh * 0.667;       /* 2D 立牌按精灵的 2:3，避免被裁掉头 */
  /* 房间已铺满内容区 → 窄屏上立牌会比以前大很多，容易顶出右边界：
     先按宽度上限（42% 房宽）收敛尺寸，必要时再把站位往左挪，保证完整站在房间里 */
  var BWMAX = w * 0.42;
  if (bw2 > BWMAX){ bw2 = BWMAX; bh = bw2 / 0.667; }
  var bw = bh * 0.78;         /* 3D 立牌的盒子（模型窄，留点余量） */
  var XW = 0.72;
  /* 让位余量按立牌宽度算：立牌卡片带 rotateY+translateZ 透视，实际渲染会比盒子宽约 5% */
  var _mgn = Math.max(12, bw2 * 0.10);
  var need = (w * 0.5 - _mgn - bw2) / (2 * 0.80 * w * 0.62);
  if (need < (XW - 0.5)) XW = 0.5 + Math.max(need, 0.02);
  var st = P2.onFloor(XW, 0.80);
  ['hero3d'].forEach(function(id){
    var e = $(id); if (!e) return;
    e.style.left = (st.x / w * 100).toFixed(2) + '%';
    e.style.bottom = (st.yb / h * 100).toFixed(2) + '%';
    e.style.width = (bw / w * 100).toFixed(2) + '%';
    e.style.height = (bh / h * 100).toFixed(2) + '%';
    e.style.marginLeft = '0';
    e.style.right = 'auto';
  });
  var he = $('hero');
  if (he && SHOW_HERO2D){
    /* 有抠图 → 透明人物直接站房间（无卡片框）；没有 → 退回带框精灵 */
    var cut = CUT[String(c.i)];
    var wantCut = !!(USE_CUTOUT && cut && cut.b64);
    if (he._cut !== !!wantCut){
      he._cut = !!wantCut;
      he.innerHTML = wantCut
        ? '<img id="heroImg" class="cutimg" alt="">'
        : '<div class="back"></div><div class="card"><img id="heroImg" alt=""></div>';
    }
    he.className = 'hero' + (wantCut ? ' cut' : '');
    he.style.left = (st.x / w * 100).toFixed(2) + '%';
    he.style.bottom = (st.yb / h * 100).toFixed(2) + '%';
    he.style.width = (bw2 / w * 100).toFixed(2) + '%';
    he.style.height = (bh / h * 100).toFixed(2) + '%';
    he.style.marginLeft = '0';
    he.style.right = 'auto';
    $('heroImg').src = wantCut
      ? ('data:image/webp;base64,' + cut.b64)
      : SPR[String(c.i)];
  }
  var tg = $('r3dtag');
  if (tg){
    tg.style.left = (st.x / w * 100).toFixed(2) + '%';
    tg.style.marginLeft = '0';
    tg.style.transform = 'translateX(-50%)';
    tg.style.width = 'auto';
    tg.style.bottom = Math.max(0, (st.yb / h * 100) - 7).toFixed(2) + '%';
  }
  /* 秋分琴房：只有秋分（15）这间房出现贝多芬开关（+换曲），换走就停 */
  var pc = $('pianoChip'), pbar = $('pianoBar');
  if (pbar) pbar.style.display = (c.i === 15) ? 'flex' : 'none';
  if (pc){
    if (c.i !== 15 && window.CCPiano && CCPiano.on){
      CCPiano.stop(); pc.textContent = CCPiano.label(); pc.classList.remove('play');
    }
  }
}
window.__sceneBuild = sceneBuild;
var _rb = null;
window.addEventListener('resize', function(){
  if (_rb) clearTimeout(_rb);
  _rb = setTimeout(function(){ if (ROSTER[cur]) sceneBuild(ROSTER[cur]); }, 160);
});

/* ============================================================================
   走廊大厅：两侧各 12 扇门向纵深收束，可以「往前走 / 往回走」
   ========================================================================== */
var walk = 0, WALK_SEG = 12;
function hlGeom(w, h){
  return { vx: w * 0.5, hy: h * 0.52, w: w, h: h };
}
function hallSvg(w, h){
  var g = hlGeom(w, h), vx = g.vx, hy = g.hy;
  var A = [], defs = [];
  defs.push(grad('hWall', [[0, '#0B2E20'], [1, '#04140D']], 0, 0, 0, 1));
  defs.push(grad('hCeil', [[0, '#061A11'], [1, '#0E3625']], 0, 0, 0, 1));
  defs.push(grad('hFloor', [[0, '#08251A'], [0.45, '#0C3324'], [1, '#12442F']], 0, 0, 0, 1));
  defs.push(grad('hEnd', [[0, '#0B3A26'], [1, '#061F15']], 0, 0, 1, 0));
  A.push('<rect x="0" y="0" width="' + w + '" height="' + h + '" fill="url(#hWall)"/>');
  A.push('<polygon points="0,0 ' + w + ',0 ' + (w*0.86) + ',' + (hy*0.30) + ' ' + (w*0.14) + ',' + (hy*0.30) + '" fill="url(#hCeil)"/>');
  A.push('<polygon points="0,' + h + ' ' + w + ',' + h + ' ' + (w*0.86) + ',' + hy + ' ' + (w*0.14) + ',' + hy + '" fill="url(#hFloor)"/>');
  /* 尽头墙 + 招牌 */
  A.push('<rect x="' + (w*0.36) + '" y="' + (hy*0.30) + '" width="' + (w*0.28) + '" height="' + (hy*0.70) + '" fill="url(#hEnd)"/>');
  A.push('<rect x="' + (w*0.40) + '" y="' + (hy*0.42) + '" width="' + (w*0.20) + '" height="' + (hy*0.12) + '" rx="8" fill="#00A650" opacity=".9"/>');
  A.push('<text x="' + (w*0.5) + '" y="' + (hy*0.52) + '" text-anchor="middle" font-size="' + Math.max(9, w*0.016) +
         '" font-weight="800" fill="#06251A" font-family="system-ui,sans-serif">CC 之家</text>');
  /* 透视辅助线：地板纵深线 */
  for (var k = -5; k <= 5; k++){
    var x2 = vx + (k / 5) * w * 0.9;
    A.push('<line x1="' + vx + '" y1="' + hy + '" x2="' + x2 + '" y2="' + h + '" stroke="#1C5A3E" stroke-opacity=".5" stroke-width="1"/>');
  }
  var span = h - hy;
  for (var m = 1; m <= 7; m++){
    var y = hy + span * Math.pow(1.34, -m) * 1.3;
    if (y > h) continue;
    A.push('<line x1="0" y1="' + y + '" x2="' + w + '" y2="' + y + '" stroke="#1C5A3E" stroke-opacity=".32"/>');
  }
  /* 顶灯 */
  for (var L = 0; L < 5; L++){
    var q3 = Math.pow(0.62, L), ly = hy*0.30 + (hy - hy*0.30) * (1 - q3) * 0.9;
    var lw = w * 0.10 * q3 + w*0.02;
    A.push('<rect x="' + (vx - lw/2) + '" y="' + ly + '" width="' + lw + '" height="' + Math.max(2, 6*q3) +
           '" rx="3" fill="#BFFFE0" opacity="' + (0.30 + 0.5*q3) + '"/>');
  }
  return '<defs>' + defs.join('') + '</defs>' + A.join('');
}
function renderHall(){
  var el = $('hall');
  if (!el) return;
  var w = el.clientWidth || 390, h = el.clientHeight || 300;
  var sv = $('hlSvg');
  sv.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
  sv.innerHTML = hallSvg(w, h);
  /* 走廊背景图（因地制宜：AI 生成的机组走廊背景板，内嵌 base64，不依赖外部文件） */
  if (BDR.hall){
    el.classList.add('hasbg');
    if (el.style.backgroundImage.indexOf('data:') < 0) el.style.backgroundImage = 'url("' + BDR.hall + '")';
  }
  var g = hlGeom(w, h), vx = g.vx, hy = g.hy;
  var doors = [];
  ROSTER.forEach(function(c, k){
    var lane = k % 2, seg = Math.floor(k / 2);
    var z = seg - walk - 0.35;
    if (z < -0.45 || z > 5.2) return;
    var dd = Math.min(1, 1 / (1 + Math.max(0, z) * 0.62));
    if (z < 0) dd = Math.min(1.18, 1 / (1 + z * 0.5));
    var side = lane ? 1 : -1;
    var x = vx + side * dd * (w * 0.50);
    var yb = hy + (h - hy) * dd;
    var dh = h * 0.46 * dd, dw = dh * 0.50;
    /* 只画基本完整的门牌：走到身后的门（z<0）会被挤出画面，只露一条边的话会变成
       一道莫名其妙的色带（用户 2026-09-14 反馈），直接不画 */
    var visW = Math.min(x + dw, w) - Math.max(x, 0);
    if (visW < dw * 0.92) return;
    var op = dd < 0.2 ? 0.42 + dd : 1;
    var hot = Math.abs(z) < 0.5 ? ' hot' : '';
    doors.push('<button class="hdoor' + hot + '" data-i="' + k + '" style="left:' + (x / w * 100).toFixed(2) +
      '%;top:' + ((yb - dh) / h * 100).toFixed(2) + '%;width:' + (dw / w * 100).toFixed(2) +
      '%;height:' + (dh / h * 100).toFixed(2) + '%;opacity:' + op.toFixed(2) +
      ';z-index:' + Math.round(dd * 90) + ';transform:perspective(700px) rotateY(' + (-side * (10 + 12 * dd)) + 'deg);' +
      '--c1:' + (c.pal ? lc(c.pal.accent, -0.24) : '#0E5A38') +
      ';--c2:' + (c.pal ? lc(c.pal.floor, -0.5) : '#06251A') + ';--pri:' + (c.pal ? c.pal.accent : '#00A650') + '">' +
      '<span class="fr"></span><span class="pn">' + (USE_CUTOUT && CUT[String(c.i)]
        ? '<img class="cutimg" src="data:image/webp;base64,' + CUT[String(c.i)].b64 + '" alt="">'
        : '<img src="' + SPR[String(c.i)] + '" alt="" decoding="async">') + '</span>' +
      '<span class="nu">' + esc(c.code.slice(-2)) + '</span>' +
      '<span class="nb">' + esc(c.room) + '</span></button>');
  });
  $('doors').innerHTML = doors.join('');
  var p2 = $('hlPos');
  if (p2) p2.innerHTML = '走廊 <b>' + (Math.round(walk * 2) + 1) + '</b>/24';
}
function walkBy(n){
  walk = Math.max(0, Math.min(WALK_SEG - 1, walk + n));
  renderHall();
}
function renderRoomGrid(){
  var g = $('gridView');
  if (!g) return;
  if (!g._built){
    var cards = ROSTER.map(function(c, i){
      return '<button class="door" data-i="' + i + '">' +
        '<div class="th"><img src="' + SPR[String(c.i)] + '" alt="" decoding="async">' +
        '<span class="tone">' + esc(c.tone) + '</span><span class="no">' + esc(c.code.slice(-2)) + '</span></div>' +
        '<div class="tx"><div class="rn">' + esc(c.room) + '</div>' +
        '<div class="nm">' + esc(c.n) + ' · ' + esc(c.code) + '</div>' +
        '<div class="dg">' + esc(c.doing) + '</div></div></button>';
    }).join('');
    g.innerHTML = '<div class="gv-hd"><b>全部 24 间房</b><span style="font-size:11.5px;color:#64756B">点门牌直接进房</span>' +
      '<button class="x" id="gvX">关掉</button></div><div class="doors">' + cards + '</div>';
    g._built = true;
    g.addEventListener('click', function(e){
      if (e.target && e.target.id === 'gvX'){ g.classList.remove('on'); return; }
      var d = e.target.closest ? e.target.closest('.door') : null;
      if (!d) return;
      g.classList.remove('on');
      enter(parseInt(d.getAttribute('data-i'), 10));
    });
  }
  g.classList.add('on');
}
function bindHall(){
  var b1 = $('hlBack'), b2 = $('hlFwd'), b3 = $('hlGrid');
  if (b1) b1.onclick = function(){ walkBy(-1); };
  if (b2) b2.onclick = function(){ walkBy(1); };
  if (b3) b3.onclick = function(){ renderRoomGrid(); };
  var el = $('hall');
  if (el){
    el.addEventListener('wheel', function(e){
      if (Math.abs(e.deltaY) < 4) return;
      walkBy(e.deltaY > 0 ? 1 : -1);
    }, { passive: true });
    var x0 = null;
    el.addEventListener('pointerdown', function(e){ x0 = e.clientX; });
    el.addEventListener('pointerup', function(e){
      if (x0 === null) return;
      var dx = e.clientX - x0; x0 = null;
      if (Math.abs(dx) > 44) walkBy(dx < 0 ? 1 : -1);
    });
    el.addEventListener('click', function(e){
      var d = e.target.closest ? e.target.closest('.hdoor') : null;
      if (!d) return;
      enter(parseInt(d.getAttribute('data-i'), 10));
    });
  }
  document.addEventListener('keydown', function(e){
    if (view !== 'hall') return;
    if (e.key === 'ArrowRight') walkBy(1);
    if (e.key === 'ArrowLeft') walkBy(-1);
  });
  window.addEventListener('resize', function(){
    if (view === 'hall') renderHall();
    else if (view === 'room') sceneBuild(ROSTER[cur]);
  });
}

  function nextRoom(dir){ enter((cur + (dir || 1) + ROSTER.length) % ROSTER.length); }

  /* ---------------- 真 3D 形象（three.js；缺模型自动回落到精灵立牌） ---------------- */
  /* 原图直出模式下，房间背景本身就是这位形态的原画（画面里已经有人物），
     再叠一个 3D 会像「同一个人出现两次」→ 默认关掉，用户按「🧊 3D 开」仍可打开 */
  var want3d = !BG_ORIG;
  try{
    var _s3 = localStorage.getItem(K3D);
    if (_s3 !== null) want3d = _s3 !== '0';
  }catch(e){}
  function r3dAvail(i){
    if (!window.CC3D || !CC3D.ready()) return false;
    return CC3D.can ? CC3D.can(i) : true;
  }
  function r3dBtn(){
    var b = $('btn3d'); if (!b) return;
    var on = want3d && r3dAvail(ROSTER[cur] ? ROSTER[cur].i : 0);
    b.textContent = on ? '🧊 3D 开' : '🧊 3D 关';
    b.classList.toggle('p', on);
  }
  function r3dSync(i){
    var el = $('hero3d'), r = $('room');
    if (!el) return;
    if (!(want3d && r3dAvail(i))){
      if (el.__cc3d) { try{ CC3D.destroy(el); }catch(e){} }
      r.classList.remove('is3d');
      r3dBtn(); return;
    }
    r.classList.remove('is3d');                    /* 换形态时先收回，就绪后再淡入 */
    if (!el.__cc3d){
      el.__cc3dOnReady = function(){ r.classList.add('is3d'); r3dBtn(); };
      el.__cc3dFallback = function(){ r.classList.remove('is3d'); r3dBtn(); };
      CC3D.mount(el, { form: i });
    } else {
      CC3D.setForm(el, i);
      setTimeout(function(){ if (el.__cc3d && el.__cc3d.has) r.classList.add('is3d'); }, 60);
    }
    r3dBtn();
  }
  function r3dInit(){
    var b = $('btn3d');
    if (b) b.onclick = function(){
      want3d = !want3d;
      try{ localStorage.setItem(K3D, want3d ? '1' : '0'); }catch(e){}
      toast(want3d ? '已开启 3D 形象' : '已关掉 3D（只看房间原画）');
      r3dSync(ROSTER[cur].i);
    };
    window.addEventListener('resize', function(){ if ($('room').classList.contains('is3d')) r3dSync(ROSTER[cur].i); });
    r3dBtn();
  }
  function hiLine(){
    var c = ROSTER[cur], last = $('rSays').textContent;
    var pool = [c.hi, c.motto, c.extra, c.who, c.tag];
    var out = pool[0];
    for (var k = 0; k < 8; k++){ out = pick(pool); if (out !== last) break; }
    $('rSays').textContent = out;
    vib(8);
  }
  function visit(){
    var c = ROSTER[cur];
    var v = pick(ROSTER.filter(function(x){ return x.i !== c.i; }));
    var relay = pick([c.buddy, c.friction ? c.friction : v.i]);
    var other = byI[relay] || v;
    var close = (relay === c.buddy);
    $('rSays').textContent = other.n + '敲门：「' + (close ? '我路过，进来坐坐。' : '……你在啊。我来看看你在忙什么。') + '」';
    $('rWho').textContent = other.n + ' · ' + other.alias + ' 来串门';
    toast(other.n + ' 来串门了');
    vib([10, 30, 10]);
    setTimeout(function(){
      $('rSays').textContent = pick([
        close ? c.n + '：' + '进来吧，正好有点事想问你。' : c.n + '：你又来了。',
        close ? c.n + '：茶在那边，自己倒。' : c.n + '：……我有在忙。',
        c.n + '：' + c.motto
      ]);
      $('rWho').textContent = c.n + ' · ' + c.alias;
    }, 2400);
  }

  /* ---------------- 剧场 ---------------- */
  var stLines = [], stIdx = 0, stTimer = null, stAuto = false;
  function playable(list, c){
    var mine = list.filter(function(x){ return x.who.indexOf(c.i) >= 0; });
    return mine.length ? mine : list;
  }
  function openStage(sc){
    stLines = sc.lines; stIdx = 0;
    $('stTitle').textContent = sc.t;
    $('stKind').textContent = sc.kind;
    $('stBody').innerHTML = '';
    $('stage').classList.add('on');
    step();
  }
  function step(){
    if (stIdx >= stLines.length){ stopAuto(); return; }
    var L = stLines[stIdx], body = $('stBody');
    if (L[0] === 0){
      var n = document.createElement('div');
      n.className = 'line narr';
      n.innerHTML = '<div class="b">' + esc(L[1]) + '</div>';
      body.appendChild(n);
    } else {
      var c = byI[L[0]] || ROSTER[0];
      var d = document.createElement('div');
      d.className = 'line';
      d.innerHTML = '<img src="' + SPR[String(c.i)] + '" alt=""><div class="b"><div class="n">' + esc(c.n) + '</div>' + esc(L[1]) + '</div>';
      body.appendChild(d);
    }
    stIdx++;
    body.scrollTop = body.scrollHeight;
    if (stAuto && stIdx >= stLines.length) stopAuto();
  }
  function startAuto(){
    stAuto = true; $('stAuto').textContent = '暂停';
    stopAuto._t = setInterval(function(){
      if (stIdx >= stLines.length){ stopAuto(); return; }
      step();
    }, 1500);
  }
  function stopAuto(){
    stAuto = false; $('stAuto').textContent = '自动播放';
    if (stopAuto._t){ clearInterval(stAuto._t); stopAuto._t = null; }
  }
  function playWith(c){
    var list = playable(INTER, c);
    openStage(pick(list));
  }

  /* ---------------- 聊天 + AI ----------------
     2026-09-15：撤掉免 Key 的 Pollinations 公共端点——公共池额度经常爆，
     实测会把 "The API key used for this request has reached its budget…"
     当正文原样塞进气泡。现在默认直连内置智谱 GLM（与「你问我答」同一把内置 Key，免配置）；
     2026-09-19 起为本地模式：不再读取任何密钥、不调用任何外部模型。
     注意：本文件是 cc-home.html 的生成器，改这里才会进产物（直接改 cc-home.html 会被重建冲掉）。 */
  /* 2026-09-19 本地模式（彻底无密钥）：不再内置任何 Key、不调用外部模型，也不读取任何密钥。 */
  /* 2026-09-19 本地模式（彻底无密钥）：不再内置任何 Key、不调用外部模型，也不读取任何密钥。 */
  /* 2026-09-19 本地模式（彻底无密钥）：不再内置任何 Key、不调用外部模型，也不读取任何密钥。 */
  /* 2026-09-19 本地模式（彻底无密钥）：不再内置任何 Key、不调用外部模型，也不读取任何密钥。 */
  /* 2026-09-19 本地模式（彻底无密钥）：不再内置任何 Key、不调用外部模型，也不读取任何密钥。 */
  /* 2026-09-19 本地模式（彻底无密钥）：不再内置任何 Key、不调用外部模型，也不读取任何密钥。 */
  /* 2026-09-19 本地模式（彻底无密钥）：不再内置任何 Key、不调用外部模型，也不读取任何密钥。 */
  /* 2026-09-19 本地模式（彻底无密钥）：不再内置任何 Key、不调用外部模型，也不读取任何密钥。 */
  /* 2026-09-19 本地模式（彻底无密钥）：不再内置任何 Key、不调用外部模型，也不读取任何密钥。 */
  /* 2026-09-19 本地模式（彻底无密钥）：不再内置任何 Key、不调用外部模型，也不读取任何密钥。 */
  /* 2026-09-19 本地模式（彻底无密钥）：不再内置任何 Key、不调用外部模型，也不读取任何密钥。 */
  /* 2026-09-19 本地模式（彻底无密钥）：不再内置任何 Key、不调用外部模型，也不读取任何密钥。 */
  /* 2026-09-19 本地模式（彻底无密钥）：不再内置任何 Key、不调用外部模型，也不读取任何密钥。 */
  var BUILTIN_AI = { apiKey: '', base: '' };
  var GLM_MODELS = [];   // 本地模式：不调用任何外部模型
  /* 本地模式：不再从 localStorage 读取任何密钥（历史配置键一并废弃） */
  function findCfg(){ return null; }
  function findCfg(){ return null; }
  function findCfg(){ return null; }
  function findCfg(){ return null; }
  function findCfg(){ return null; }
  function findCfg(){ return null; }
  function findCfg(){ return null; }
  function findCfg(){ return null; }
  function findCfg(){ return null; }
  function findCfg(){ return null; }
  function findCfg(){ return null; }
  function findCfg(){ return null; }
  function findCfg(){ return null; }
  function findCfg(){
    try{
      for (var i = 0; i < localStorage.length; i++){
        var k = localStorage.key(i);
        if (!/spring|ai|cc/i.test(k)) continue;
        var v = localStorage.getItem(k);
        if (!v || v.charAt(0) !== '{') continue;
        var o = JSON.parse(v);
        if (o && o.apiKey && String(o.apiKey).trim().length > 10) return o;
      }
    }catch(e){}
    return null;
  }
  /* 上游有时把错误当 200 正文返回（额度/欠费/鉴权），不能当聊天内容展示 */
  function looksLikeApiError(t){
    return /budget|raise the key|api\s*key|quota|unauthorized|invalid.*key|欠费|额度|鉴权失败|访问量过大|1305/i.test(String(t || ''));
  }
  /* 本地模式（2026-09-19）：不调用任何外部模型（源码零密钥、运行时零外发）。
     调用方按 lastMode === 'offline' 回落到本地预置内容。 */
  async function aiChat(messages){ lastMode = 'offline'; return null; }

  function sysPrompt(c){
    /* 2026-09-14（晚）：把每个形态「独有的设定 / 背景 / 语气」全部喂给 AI（数据单一来源 _pet_roster.py），
       让接入的 AI 自动按角色作答，而不是泛泛的客服腔 */
    return '你是春秋航空广州分队「客舱小助手」的数字乘务员团队中的一员，现在由你来接待用户：' +
      '「' + c.n + '」（' + c.code + '，别称「' + (c.alias || '') + '」，气质底色「' + c.tone + '」）。\n' +
      '【你的身份背景】今年 ' + (c.age || 23) + ' 岁，' + (c.home || '广东广州') + '人。' +
      '被问到年龄、出生地、家乡这类问题时自然大方地回答，并可以顺势聊一句家乡和这行的缘分。\n' +
      '【你独有的设定与背景】' + (c.story || '') + '\n' +
      '【你此刻的状态】' + (c.tag || '') + '，你正在' + (c.doing || '') + '。' +
      '你在自己的房间「' + c.room + '」——' + (c.scene || '') + '，房里有：' + (c.roomProp || []).join('、') + '。' +
      '可以自然地提到这些陈设和你手头的事。\n' +
      '【你的说话语气】第一人称、中文。像这样开口打招呼：「' + c.hi + '」；像这样关心人：「' + (c.care || '') + '」；' +
      '被调侃时这样回：「' + (c.tease || '') + '」；查不到时这样老实交代：「' + (c.unknown || '') + '」。' +
      '你的口头禅是「' + c.motto + '」' + ((c.extra || '') ? ('；只有熟人才知道的小细节：' + c.extra) : '') + '。' +
      '回答必须始终带着「' + c.n + '」自己的味道，不要退化成通用客服。\n' +
      '【答题规矩】知识类问题优先给准话，闲聊才聊你自己；一次回答不超过三句；' +
      '严禁编造规章条文、数值与章节号，不确定就直说「以公司现行规定/手册原文为准」；你的制作人是雷炜豪。';
  }
  function offlineReply(text, c){
    var t = String(text || '');
    var hit = OKB.filter(function(x){ return t.indexOf(x.q) >= 0 || x.q.indexOf(t) >= 0; })[0];
    if (hit) return hit.a;
    if (/你好|在吗|嗨|hi|hello/i.test(t)) return c.hi;
    if (/你是谁|什么形态|叫什么/.test(t)) return c.who;
    /* 身份背景问答（2026-09-15：年龄 / 出生地 / 家乡 进了数据表 _pet_roster.py） */
    if (/多大|几岁|年龄|年纪/.test(t)) return '今年 ' + (c.age || 23) + ' 岁。' + c.motto;
    if (/哪里人|哪儿人|出生地|家乡|老家|籍贯|是哪里/.test(t)) return '我是' + (c.home || '广东广州') + '人。' + c.motto;
    if (/忙|做什么|干嘛/.test(t)) return '我' + c.doing + '。' + c.motto;
    if (/房间|家|哪儿/.test(t)) return '这是「' + c.room + '」，陈设是：' + (c.roomProp || []).join('、') + '。';
    if (/制作人|谁做/.test(t)) return c.maker;
    return '（离线值守中）我' + c.doing + '，手头五套手册都在。你要查具体条目，去「你问我答」问「立春」，那边检索更全。\n' + c.extra;
  }
  function pushBub(role, text){
    var d = document.createElement('div');
    d.className = 'bub2' + (role === 'me' ? ' me' : '');
    d.textContent = text;
    $('chatScroll').appendChild(d);
    $('chatScroll').scrollTop = $('chatScroll').scrollHeight;
  }
  function setNet(m){ lastMode = m; var el = $('netChip'); el.className = 'netchip ' + m;
    el.textContent = m === 'glm' ? '在线 · GLM' : '离线值守'; }
  /* ---------------- 聊天记忆（2026-09-15） ----------------
     每位角色一份独立对话记忆，存 localStorage（cc_home_chat_v1）：
     · 重开 App / 换天回来，接着上次聊；
     · AI 上下文 = 角色设定 + 最近 CTX_MAX 条记忆（不再从 DOM 反抓——
       旧做法会把「正在想…」占位气泡也当回复发出去，且刷新即失忆）。 */
  var MEM_KEY = 'cc_home_chat_v1', MEM_MAX = 40, CTX_MAX = 16;
  function memLoad(i){
    try{
      var d = JSON.parse(localStorage.getItem(MEM_KEY) || '{}');
      return Array.isArray(d[i]) ? d[i] : [];
    }catch(e){ return []; }
  }
  function memPush(i, role, text){
    try{
      var d = JSON.parse(localStorage.getItem(MEM_KEY) || '{}');
      var arr = Array.isArray(d[i]) ? d[i] : [];
      arr.push({ r: role, t: String(text), ts: Date.now() });
      while (arr.length > MEM_MAX) arr.shift();
      d[i] = arr;
      localStorage.setItem(MEM_KEY, JSON.stringify(d));
    }catch(e){}
  }
  function memClear(i){
    try{
      var d = JSON.parse(localStorage.getItem(MEM_KEY) || '{}');
      delete d[i];
      localStorage.setItem(MEM_KEY, JSON.stringify(d));
    }catch(e){}
  }
  function renderMemBubbles(i){
    var sc = $('chatScroll'); if (!sc) return;
    sc.innerHTML = '';
    memLoad(i).forEach(function(m){ pushBub(m.r === 'user' ? 'me' : 'bot', m.t); });
  }
  /* ---------------- 实时天气（2026-09-16 · Open-Meteo 免 Key） ----------------
     24 位角色都能答天气：识别天气提问 → 抽城市（默认角色家乡，再退广州）→
     geocoding + forecast 拉实时数据（缓存 20 分钟，断网回落最近一次成功数据）。
     在线：数据注入 system prompt，GLM 按各角色自己的口吻播报；
     离线/断网：WXH.offline 用角色口吻模板播报兜底。 */
  var WXH = (function(){
    var CK = 'cc_wx_cache_v1', TTL = 20 * 60 * 1000;
    var WMO = {0:['晴','☀️'],1:['基本晴','🌤️'],2:['多云','⛅'],3:['阴','☁️'],45:['有雾','🌫️'],48:['雾凇','🌫️'],51:['毛毛雨','🌦️'],53:['毛毛雨','🌦️'],55:['浓毛毛雨','🌧️'],56:['冻毛毛雨','🌧️'],57:['冻毛毛雨','🌧️'],61:['小雨','🌦️'],63:['中雨','🌧️'],65:['大雨','🌧️'],66:['冻雨','🌧️'],67:['冻雨','🌧️'],71:['小雪','🌨️'],73:['中雪','❄️'],75:['大雪','❄️'],77:['米雪','🌨️'],80:['阵雨','🌦️'],81:['阵雨','🌧️'],82:['强阵雨','⛈️'],85:['阵雪','🌨️'],86:['阵雪','❄️'],95:['雷阵雨','⛈️'],96:['雷阵雨·伴冰雹','⛈️'],99:['雷阵雨·大冰雹','⛈️']};
    var SNOW = [71,73,75,77,85,86];
    function wmo(c){ return WMO[c] || ['未知天气','🌡️']; }
    function isQuery(t){
      t = String(t || '').trim();
      if (!/(天气|气温|温度|下雨|降雨|降水|风速|风力|风大|热不热|冷不冷|多少度|几度)/.test(t)) return false;
      /* 规章/处置/注意类问法（"雷雨天气怎么处置""下雨天注意什么"）不是查实时天气，照常走 AI 知识链路 */
      if (/(怎么办|怎么处理|怎么处置|怎么应对|怎么操作|怎么预防|怎么规定|如何处置|如何应对|如何处理|如何操作|预防|处置|规定|要求|标准|条例|手册|颠簸|除冰|防冰|影响|防范|防护|注意什么|注意哪些|注意事项)/.test(t)) return false;
      return true;
    }
    function extractCity(t){
      var m = String(t || '').match(/([\u4e00-\u9fa5]{1,8}?)(?:市)?(?:的)?(?:天气|气温|温度|降雨|下雨|降水|风速|风力|热不热|冷不冷|多少度|几度)/);
      if (!m) return null;
      var s = m[1];
      var PRE = ['帮我查一下','帮我查查','帮我看看','我想知道','我想查','我要查','我想问','我想看看','我要看看','我要问','查一下','麻烦','请问','帮我','查查','看看','看下','问一下','问下','给我','说下','说说','我','先','再','还有','查','看','问','请'];
      var hit = true;
      while (hit){ hit = false; for (var i = 0; i < PRE.length; i++){ if (s.indexOf(PRE[i]) === 0){ s = s.slice(PRE[i].length); hit = true; break; } } }
      s = s.replace(/(今天|明天|后天|现在|当前|此刻|实时|外面|当地|航班|机场|公司|你们|我们|这里|那边)/g, '');
      s = s.replace(/(?:是不是|有没有|是否|的|会|要|还|在)+$/, '');
      if (s.length >= 2 && !/^(今天|明天|后天|现在|当前|天气|气温|温度|晴|阴|雨|风|外面|这里|那边|航班|公司)$/.test(s)) return s;
      return null;
    }
    function homeCity(home){
      var s = String(home || '').replace(/^(中国|华南|华北|华东|西南|东北|西北)/, '')
        .replace(/^(广东|广西|湖南|湖北|河南|河北|山东|山西|江苏|浙江|安徽|福建|江西|四川|贵州|云南|陕西|甘肃|青海|海南|台湾|辽宁|吉林|黑龙江)/, '');
      return s.length >= 2 ? s : '广州';
    }
    function readCache(city){
      try{
        var d = (JSON.parse(localStorage.getItem(CK) || '{}') || {})[city];
        if (d && Date.now() - d.ts < TTL) return d;
        if (d) { d.stale = true; return d; }   /* 过期也留着：断网兜底 */
      }catch(e){}
      return null;
    }
    function writeCache(city, d){
      try{ var all = JSON.parse(localStorage.getItem(CK) || '{}') || {}; all[city] = d; localStorage.setItem(CK, JSON.stringify(all)); }catch(e){}
    }
    async function fetchWx(city){
      var cached = readCache(city);
      if (cached && !cached.stale) return cached;
      try{
        var g = await fetch('https://geocoding-api.open-meteo.com/v1/search?name=' + encodeURIComponent(city) + '&count=1&language=zh&format=json').then(function(r){ return r.json(); });
        var hit = g && g.results && g.results[0];
        if (!hit) throw new Error('没找到城市「' + city + '」');
        var u = 'https://api.open-meteo.com/v1/forecast?latitude=' + hit.latitude + '&longitude=' + hit.longitude +
          '&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m' +
          '&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto&forecast_days=2';
        var d = await fetch(u).then(function(r){ if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });
        if (!d || !d.current || !d.daily) throw new Error('天气数据为空');
        var out = {
          city: hit.name, ts: Date.now(),
          cur: { temp: d.current.temperature_2m, app: d.current.apparent_temperature, hum: d.current.relative_humidity_2m, code: d.current.weather_code, wind: d.current.wind_speed_10m, time: d.current.time },
          t0: { code: d.daily.weather_code[0], max: d.daily.temperature_2m_max[0], min: d.daily.temperature_2m_min[0], pop: d.daily.precipitation_probability_max[0] },
          t1: { code: d.daily.weather_code[1], max: d.daily.temperature_2m_max[1], min: d.daily.temperature_2m_min[1], pop: d.daily.precipitation_probability_max[1] }
        };
        writeCache(hit.name, out);
        return out;
      }catch(e){
        if (cached) return cached;   /* 断网/接口异常：回落缓存 */
        throw e;
      }
    }
    /* 给 GLM 的一句话数据摘要（播报规矩在调用方拼） */
    function brief(w){
      return w.city + '此刻' + wmo(w.cur.code)[0] + '，气温 ' + w.cur.temp + '°C（体感 ' + w.cur.app + '°C），湿度 ' + w.cur.hum + '%，风速 ' + w.cur.wind + ' km/h；今天 ' + w.t0.min + '~' + w.t0.max + '°C 降水概率 ' + w.t0.pop + '%，明天 ' + w.t1.min + '~' + w.t1.max + '°C 降水概率 ' + w.t1.pop + '%。' + (w.stale ? '（注：这是最近一次联网的缓存数据）' : '');
    }
    function tipOf(w){
      var t = [];
      if (w.cur.code >= 51 || w.t0.pop >= 50) t.push('记得带伞');
      if (SNOW.indexOf(w.cur.code) >= 0 || SNOW.indexOf(w.t0.code) >= 0) t.push('雪天路滑注意保暖');
      if (w.cur.wind >= 30) t.push('风大，外场注意安全');
      if (w.t0.max >= 32) t.push('白天较热注意补水');
      if (w.t0.min <= 5) t.push('早晚偏冷多穿一层');
      if (!t.length) t.push('天气不错，适合飞行');
      return t.join('，');
    }
    /* 离线/AI 挂了的兜底播报：真实数据 + 角色口吻 */
    function offline(w, c){
      return '（瞄了眼实时云图）' + w.city + '现在' + wmo(w.cur.code)[0] + '，' + Math.round(w.cur.temp) + '°C，体感 ' + Math.round(w.cur.app) + '°C；今天 ' + Math.round(w.t0.min) + '~' + Math.round(w.t0.max) + '°C，降水概率 ' + w.t0.pop + '%。' + tipOf(w) + (w.stale ? '（这是离线缓存的数据哦）' : '') + '\n' + (c ? c.motto : '');
    }
    return { isQuery: isQuery, extractCity: extractCity, homeCity: homeCity, fetch: fetchWx, brief: brief, offline: offline };
  })();
  async function send(text){
    var c = ROSTER[cur];
    if (!text) return;
    pushBub('me', text);
    memPush(cur, 'user', text);
    var thinking = document.createElement('div');
    thinking.className = 'bub2'; thinking.textContent = c.n + ' 正在想…';
    $('chatScroll').appendChild(thinking);
    $('chatScroll').scrollTop = $('chatScroll').scrollHeight;
    /* 上下文 = 角色设定 + 本角色持久记忆最近一段（最后一条正好是刚问的这句） */
    var hist = memLoad(cur).slice(-CTX_MAX).map(function(m){
      return { role: m.r === 'user' ? 'user' : 'assistant', content: m.t };
    });
    hist = [{ role:'system', content: sysPrompt(c) }].concat(hist);
    /* 【实时天气（2026-09-16）】天气提问 → Open-Meteo 免 Key 实时数据：
       在线时把数据拼进 system prompt，24 位角色各自用自己的口吻播报；
       离线 / AI 挂了 → WXH.offline 用角色口吻的模板播报兜底。 */
    var wxr = null;
    if (WXH.isQuery(text)){
      try{ wxr = await WXH.fetch(WXH.extractCity(text) || WXH.homeCity(c.home)); }catch(e){ wxr = null; }
      if (wxr){
        hist = [{ role:'system', content: sysPrompt(c) +
          '\n\n【实时天气数据（Open-Meteo，此刻真实数据）】用户正在问天气，数据：' + WXH.brief(wxr) +
          '\n【播报规矩】用「' + c.n + '」的口吻把这些数据自然地播报给用户（2~3 句）；所有温度、风速、湿度、概率数值必须逐字来自上方数据，不得编造或新增数值；可以结合你房间里的陈设或手头的事调侃一句。' }].concat(hist);
      }
    }
    if (!navigator.onLine){ setNet('offline'); }
    else {
      var r0 = await aiChat(hist);
      if (r0 && !looksLikeApiError(r0)){
        thinking.textContent = r0;
        memPush(cur, 'bot', r0);
        setNet('glm');
        return;
      }
    }
    var off = (wxr ? WXH.offline(wxr, c) : null) || offlineReply(text, c);
    thinking.textContent = off;
    memPush(cur, 'bot', off);
    setNet('offline');
  }
  function renderTips(){
    var c = ROSTER[cur];
    $('tips').innerHTML = ['你好', '你在忙什么', '今天天气怎么样', '这是哪儿', '你的制作人是谁', '有几套知识库', '你多大年纪', '你是哪里人']
      .map(function(q){ return '<button data-q="' + esc(q) + '">' + esc(q) + '</button>'; }).join('') +
      '<button class="mem-clear" data-q="__clear__">🗑 清空记忆</button>';
    $('tips').onclick = function(e){ var b = e.target.closest ? e.target.closest('button') : null; if (!b) return;
      var q = b.getAttribute('data-q');
      if (q === '__clear__'){ memClear(cur); renderMemBubbles(cur); toast('已清空和' + c.n + '的聊天记忆'); return; }
      send(q); };
  }

  /* ---------------- 直达角色聊天（2026-09-15） ----------------
     「你问我答」里点「CC 之家」时，qa 会把当前形态 index 写进 localStorage
     （cc_home_enter_chat）。两条到达路径都接住：
     ① home 模块第一次加载 → boot 里读标记（此时 storage 事件来不及）；
     ② home 模块已加载 → 监听 storage 事件（qa 写入时会广播到本 iframe）。
     目的：第一下就直接进角色对话框，不再停在大厅。 */
  function directEnterChat(idxRaw){
    var di = ((parseInt(idxRaw, 10) || 0) % ROSTER.length + ROSTER.length) % ROSTER.length;
    enter(di);
    renderMemBubbles(cur);
    renderTips();
    go('chat');
  }
  window.addEventListener('storage', function(e){
    if (e && e.key === 'cc_home_enter_chat' && e.newValue){
      try{ localStorage.removeItem('cc_home_enter_chat'); }catch(err){}
      directEnterChat(e.newValue);
    }
  });

  /* ---------------- 形象设置 ---------------- */
  function markGrid(){
    var g = $('pmGrid'); if (!g) return;
    var ns = g.querySelectorAll('.pm-c');
    for (var i = 0; i < ns.length; i++) ns[i].classList.toggle('on', i === cur);
  }
  function renderGrid(){
    var g = $('pmGrid');
    if (!g.childElementCount){
      g.innerHTML = ROSTER.map(function(c, i){
        return '<div class="pm-c" data-i="' + i + '"><div class="th"><img src="' + SPR[String(c.i)] + '" alt="" decoding="async">' +
          '<span class="tone">' + esc(c.tone) + '</span></div><div class="nm">' + esc(c.n) + '</div>' +
          '<div class="cd">' + esc(c.room) + '</div></div>';
      }).join('');
      g.onclick = function(e){
        var d = e.target.closest ? e.target.closest('.pm-c') : null;
        if (!d) return;
        enter(parseInt(d.getAttribute('data-i'), 10));
        $('petModal').classList.remove('on');
      };
    }
    markGrid();
  }

  /* ---------------- 3D 视差 ---------------- */
  function parallax(){
    var r = $('room'); if (!r) return;
    var raf = 0;
    var setp = function(px, py){
      if (raf) return;
      raf = requestAnimationFrame(function(){ raf = 0;
        r.style.setProperty('--px', px.toFixed(3)); r.style.setProperty('--py', py.toFixed(3)); });
    };
    r.addEventListener('pointermove', function(e){
      var b = r.getBoundingClientRect(); if (!b.width) return;
      setp(((e.clientX - b.left) / b.width - .5) * 2, ((e.clientY - b.top) / b.height - .5) * 2);
    });
    r.addEventListener('pointerleave', function(){ setp(0, 0); });
    window.addEventListener('deviceorientation', function(e){
      if (e.gamma == null || e.beta == null) return;
      setp(Math.max(-1, Math.min(1, e.gamma / 35)), Math.max(-1, Math.min(1, (e.beta - 45) / 45)));
    });
  }

  /* ---------------- 启动 ---------------- */
  function boot(){
    ROSTER.forEach(function(c){ c._g = (c.roomProp || []).map(function(nm){ return (window.__GLYPH && window.__GLYPH[nm]) || '📦'; }); });
    var i = 0;
    try{ var v = localStorage.getItem(KEY); if (v !== null) i = parseInt(v, 10) || 0; }catch(e){}
    if (location.hash && /^#r\d+$/.test(location.hash)) i = (parseInt(location.hash.slice(2), 10) - 1) || 0;
    cur = (i + ROSTER.length) % ROSTER.length;
    renderHall(); renderGrid(); renderTips();
    enter(cur); go('hall');
    setNet(navigator.onLine ? 'glm' : 'offline');
    window.addEventListener('online', function(){ setNet('glm'); });
    window.addEventListener('offline', function(){ setNet('offline'); });
    /* qa「CC 之家」直达：首次加载时 storage 事件赶不上，boot 里补读一次标记 */
    try{
      var _dc = localStorage.getItem('cc_home_enter_chat');
      if (_dc !== null && _dc !== ''){
        localStorage.removeItem('cc_home_enter_chat');
        directEnterChat(_dc);
      }
    }catch(e){}

    $('btnHall').onclick = function(){ go('hall'); renderHall(); };
    bindHall();
    r3dInit();
    /* 秋分琴房：贝多芬钢琴三首（只在秋分这间房出现）—— 🎵 开关 / ⏭ 手动换曲 */
    var pcChip = $('pianoChip');
    if (pcChip) pcChip.onclick = function(){
      if (!window.CCPiano) return;
      CCPiano.toggle();
      pcChip.textContent = CCPiano.label();
      pcChip.classList.toggle('play', CCPiano.on);
    };
    var pcNext = $('pianoChipNext');
    if (pcNext) pcNext.onclick = function(){
      if (!window.CCPiano || !pcChip) return;
      CCPiano.next();
      pcChip.textContent = CCPiano.label();
      pcChip.classList.toggle('play', CCPiano.on);
      toast(CCPiano.on ? ('换成《' + CCPiano.trackName() + '》') : ('已选中《' + CCPiano.trackName() + '》'));
    };
    $('btnSet').onclick = function(){ renderGrid(); $('petModal').classList.add('on'); };
    $('btnRand').onclick = function(){ nextRoom(1); };
    $('pmX').onclick = function(){ $('petModal').classList.remove('on'); };
    $('petModal').addEventListener('click', function(e){ if (e.target === $('petModal')) $('petModal').classList.remove('on'); });
    $('btnHi').onclick = hiLine;
    $('btnVisit').onclick = visit;
    $('btnPlay').onclick = function(){ playWith(ROSTER[cur]); };
    $('btnChat').onclick = function(){ renderMemBubbles(cur); renderTips(); go('chat'); };
    $('btnNextRoom').onclick = function(){ nextRoom(1); };
    $('stX').onclick = function(){ stopAuto(); $('stage').classList.remove('on'); };
    $('stNext').onclick = step;
    $('stAuto').onclick = function(){ stAuto ? stopAuto() : startAuto(); };
    $('stAgain').onclick = function(){ $('stBody').innerHTML = ''; stIdx = 0; step(); };
    $('stOther').onclick = function(){ playWith(ROSTER[cur]); };
    $('btnSend').onclick = function(){ var i = $('chatInput'); var v = i.value.trim(); if (!v) return; i.value = ''; send(v); };
    $('chatInput').addEventListener('keydown', function(e){
      if (e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); $('btnSend').click(); }
    });
    parallax();
    document.addEventListener('keydown', function(e){
      if (e.key === 'Escape'){ stopAuto(); $('stage').classList.remove('on'); $('petModal').classList.remove('on'); }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();

  return { enter: enter, roster: ROSTER, ai: aiChat, mode: function(){ return lastMode; } };
})();
</script>
</body>
</html>
'''

# 陈设图标表注入
GL = json.dumps(GLYPH, ensure_ascii=False)


def _sub(base, ph, rep, unique=True):
    """2026-09-21：模板锚点替换前断言「存在」+「唯一」。
    原实现直接 .replace，模板一旦改锚点就静默 no-op —— cc-home.html 会残留
    __ROSTER__ 之类的字面量或漏注入 3D/GLYPH，而 _check_needles 不查 cc-home，会漏检上线。
    unique=False 的锚点（如 </body> 可能在模板串里出现多次）只断言存在，仍只替换第一次。"""
    n = base.count(ph)
    if n == 0:
        raise SystemExit(u'!! cc-home 锚点缺失：%s' % ph)
    if unique and n != 1:
        raise SystemExit(u'!! cc-home 锚点不唯一（%d 处）：%s' % (n, ph))
    return base.replace(ph, rep, 1)


html = HTML
for _ph, _rep in (
        ('__ROSTER__', json.dumps(ROSTER, ensure_ascii=False)),
        ('__SPRITES__', json.dumps(sprites)),
        ('__BDR__', json.dumps(BDR)),
        ('__BG_ORIG__', 'true' if BG_ORIG else 'false'),
        ('__ORIAR__', json.dumps(ORI_AR)),
        ('__INTER__', json.dumps(INTERACTIONS, ensure_ascii=False)),
        ('__OKB__', json.dumps(OFFLINE_KB, ensure_ascii=False)),
        ('__SCENES__', json.dumps(SCENES, ensure_ascii=False)),
        ('__CUTOUTS__', json.dumps(CUTOUTS, ensure_ascii=False))):
    html = _sub(html, _ph, _rep)
# 图标表要在主脚本之前可见
html = _sub(html, '<script id="mobile-native-js">',
            '<script>window.__GLYPH = ' + GL + ';</script>\n<script id="mobile-native-js">',
            unique=False)
# 秋分琴房：贝多芬钢琴三首（Web Audio 合成，单一来源 _piano_player.js）
PIANO_SRC = io.open(os.path.join(ROOT, '_piano_player.js'), encoding='utf-8').read()
html = _sub(html, '</body>', '<script>\n' + PIANO_SRC + '\n</script>\n</body>', unique=False)

# 3D 三件套 + 「已就绪模型清单」（挂到 __GLYPH 之前，保证主脚本执行时 CC3D/CC3D_READY 已就绪）
MDIR = os.path.join(ROOT, '形象IP', 'models')
ready3d = []
if os.path.isdir(MDIR):
    for f in sorted(os.listdir(MDIR)):
        if f.startswith('cc') and f.endswith('.glb'):
            try:
                ready3d.append(int(f[2:4]))
            except ValueError:
                pass
LIB3D = ('<script src="形象IP/models/lib/three.min.js"></script>'
         '<script src="形象IP/models/lib/GLTFLoader.js"></script>'
         '<script src="形象IP/models/cc-3d.js"></script>'
         # ready.js 由 _glb_pack.py 生成（列出已就绪的模型）→ 不做无谓的 404 探测；
         # 模型陆续到位时只要重跑打包，页面刷新即可用上，无需重建页面
         '<script src="形象IP/models/js/ready.js"></script>'
         '<script>window.CC3D_READY=window.CC3D_READY||[];/* 构建时已有 %s 个模型 */</script>' % sorted(ready3d))
if '<script>window.__GLYPH = ' in html:
    html = html.replace('<script>window.__GLYPH = ', LIB3D + '<script>window.__GLYPH = ', 1)
print('[3d] 已就绪 3D 模型 %d/24：%s' % (len(ready3d), sorted(ready3d)))

print('[ok] 形态 %d ｜ 互动剧场 %d 段 ｜ 精灵 %d 张 ｜ 离线小知识 %d 条'
      % (len(ROSTER), len(INTERACTIONS), len(sprites), len(OFFLINE_KB)))
print('[out] cc-home.html  %.2f MB' % (len(html.encode('utf-8')) / 1048576))
if CHECK:
    print('[check] 干跑通过，未写入'); raise SystemExit(0)
_tmp = OUT + '.tmp_write'
with io.open(_tmp, 'w', encoding='utf-8', newline='') as f:   # 原子写：崩溃不会把 cc-home.html 截成半截
    f.write(html)
os.replace(_tmp, OUT)
print('[done] 已写出', OUT)
