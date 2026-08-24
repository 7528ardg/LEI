# -*- coding: utf-8 -*-
"""美妆：新增低/中/高性价比三套话术套装 + 精选套装默认展开/选用按钮置顶"""
import io
import re

PATH = u'_work\\美妆销售话术生成系统.html'
with io.open(PATH, 'r', encoding='utf-8', newline='') as f:
    s = f.read()
was = ('\r' in s)
s = re.sub(r'\r+\n', '\n', s)
s = s.replace('\r', '\n')
log = []

# ========== A. 新增三套性价比套装（插在 set_eye_care 之后、数组结束前） ==========
anchor = "春秋航空正品保证，假一赔四。落地前下单，3-7天送到家。`\n            }\n        ];\n\n        // 当前展开的话术套装ID"
# 用更稳的锚点：set_eye_care 的 fullScript 结尾到 `];`
anchor2 = "落地前下单，3-7天送到家。`\n            }\n        ];"

THREE_SETS = r'''            },
            {
                id: 'set_value_low',
                name: '💰 性价比 · 亲民入门套装（低）',
                icon: '🟢',
                color: 'emerald',
                gradient: 'from-emerald-400 to-teal-600',
                targetAudience: '预算友好、追求高性价比的入门旅客',
                scientificBasis: '精选平价高口碑品牌，覆盖「洁面-精华-面霜-面膜-防晒-香水」完整链路，单价亲民、功效扎实',
                products: [
                    { brand: '珂润', name: '珂润润浸保湿洁颜泡沫', category: '洁面', role: '温和洁面' },
                    { brand: 'OLAY', name: 'OLAY光感小白瓶精华', category: '精华', role: '提亮精华' },
                    { brand: '明色', name: '明色胶原紧致美白面霜', category: '面霜', role: '锁水抗初老' },
                    { brand: '桃谷明色', name: '桃谷明色大米美容液面膜', category: '面膜', role: '急救补水' },
                    { brand: '密丝婷', name: '密丝婷小黄帽防晒乳', category: '防晒', role: '日常防晒' },
                    { brand: '梅森马吉拉', name: '梅森马吉拉慵懒周末女士香水', category: '香水', role: '入门香氛' }
                ],
                pairingLogic: '从平价好口碑品牌中挑选：珂润洁面温和不刺激、OLAY小白瓶含烟酰胺提亮、明色面霜主打胶原紧致、桃谷明色大米面膜亲民补水、密丝婷防晒平价大碗、再配一瓶梅森马吉拉慵懒周末香水做气质点睛。整套预算控制在千元以内，性价比拉满。',
                fullScript: `各位旅客朋友们好，今天给大家带来一套高性价比的护肤入门组合。预算有限，但该有的护肤步骤一个都不少，每一款都是经过市场验证的平价口碑款，价格亲民，效果实在。

**第一步：珂润润浸保湿洁颜泡沫**
清洁是护肤的第一步。珂润这款洁面泡沫是氨基酸配方，挤出来就是绵密泡沫，温和不刺激，敏感肌也能放心用。洗完脸不紧绷不假滑，很舒服的干净感。

**第二步：OLAY光感小白瓶精华**
清洁之后，这款小白瓶精华是OLAY的明星款，主打烟酰胺提亮，从源头淡化暗沉、均匀肤色。价格只有大牌美白精华的零头，效果却实实在在，是很多旅客的回购王。

**第三步：明色胶原紧致美白面霜**
精华之后用面霜锁住营养。明色这款面霜主打胶原紧致+美白，质地润而不油，用黄豆大小就能涂全脸，坚持用皮肤会更紧致透亮，性价比极高。

**第四步：桃谷明色大米美容液面膜**
日常护肤之外，还需要急救补水。这款大米面膜精华液浓稠，敷15分钟皮肤像喝饱水一样透亮。一盒多片，平价大碗，出差旅行带几片随时敷。

**第五步：密丝婷小黄帽防晒乳**
防晒是抗老最重要的一步，不防晒等于白护肤。密丝婷小黄帽是平价防晒里的口碑王，SPF50+高倍防护，质地清爽不油腻，涂上脸不泛白，学生党也能轻松负担。

**第六步：梅森马吉拉慵懒周末女士香水**
最后配一瓶入门香氛。梅森马吉拉慵懒周末是很多人的第一支沙龙香，干净的白麝香混着淡淡皂感，像周末睡到自然醒的味道，低调高级又不张扬，日常通勤、机上小憩都合适。

**搭配逻辑**
这套组合从清洁到提亮到锁水到防晒再到香氛，一条龙全覆盖，单件单价都不贵，整套带走也没有压力，特别适合预算有限但想认真护肤的旅客。春秋航空正品保证，假一赔四，机上价格比专柜和代购都划算。
`
            },
            {
                id: 'set_value_mid',
                name: '💎 性价比 · 品质进阶套装（中）',
                icon: '🔵',
                color: 'blue',
                gradient: 'from-blue-500 to-cyan-600',
                targetAudience: '追求品质与口碑、预算适中的进阶旅客',
                scientificBasis: '精选国际一线品牌口碑单品，覆盖「洁面-精华水-精华-面霜-面霜/眼霜-香水」，品质与价格平衡',
                products: [
                    { brand: '雅诗兰黛', name: '雅诗兰黛多效智妍洁面乳', category: '洁面', role: '温和清洁' },
                    { brand: '雅诗兰黛', name: '雅诗兰黛樱花微精华露', category: '化妆水', role: '补水提亮' },
                    { brand: '雅诗兰黛', name: '雅诗兰黛小棕瓶精华第七代', category: '精华', role: '节律修护' },
                    { brand: 'SK-II', name: 'SK-II大红瓶面霜', category: '面霜', role: '紧致锁水' },
                    { brand: '科颜氏', name: '科颜氏高保湿面霜', category: '面霜', role: '24h锁水' },
                    { brand: '古驰', name: '古驰花悦绽放女士香水', category: '香水', role: '气质香氛' }
                ],
                pairingLogic: '中档价位段精选一线大牌口碑款：雅诗兰黛洁面/樱花水/小棕瓶形成「清洁-调理-节律修护」主线，SK-II大红瓶与科颜氏高保湿面霜一紧致一锁水互补，再配古驰花悦绽放香水提升气场，整套品质扎实、价格适中。',
                fullScript: `各位旅客朋友们好，今天分享一套品质与价格都很均衡的进阶护肤组合。不想将就、又不想过度消费，这套正合适，每一款都是国际一线品牌的口碑款。

**第一步：雅诗兰黛多效智妍洁面乳**
清洁是第一步。雅诗兰黛这款洁面是氨基酸配方，温和清洁不破坏屏障，洗后柔嫩不紧绷，为后续护肤打好底。

**第二步：雅诗兰黛樱花微精华露**
洁面后先用精华水。樱花微精华露轻盈水状，快速渗透肌底，深层补水同时调节水油平衡，让皮肤呈现樱花般粉嫩透亮的光泽。

**第三步：雅诗兰黛小棕瓶精华第七代**
接下来是整套的灵魂——小棕瓶第七代。核心升级时钟肌因信源科技（CL18肽），二裂酵母含量提升至75%，修护肌底的同时同步肌肤昼夜节律。经常出差、跨时区飞行的旅客特别适合，晚上11点前用效果最好。

**第四步：SK-II大红瓶面霜**
精华之后用面霜锁住营养。大红瓶含Pitera精华加烟酰胺，紧致肌肤、提升轮廓，质地轻盈不厚重，油皮用也不闷。

**第五步：科颜氏高保湿面霜**
如果机舱干燥，可以叠加科颜氏高保湿面霜。冰川保护蛋白加角鲨烷，能在极端干燥环境下持续锁水24小时，是机上护肤的急救主力。白天用大红瓶提气，机上干燥时补一层高保湿，完美搭配。

**第六步：古驰花悦绽放女士香水**
最后配一瓶古驰花悦绽放。甜蜜花香中带一丝清新，喷上整个人气场都不一样，约会、通勤、旅行都百搭，是很多旅客点名要的香型。

**搭配逻辑**
这套从清洁到调理到修护到锁水再到香氛，覆盖完整护肤链路，单品牌都是硬口碑，组合起来1+1+1+1+1+1>6。品质不打折，价格又克制，是性价比与体验的最佳平衡点。春秋航空正品保证，假一赔四。
`
            },
            {
                id: 'set_value_high',
                name: '👑 性价比 · 尊享奢华套装（高）',
                icon: '🟡',
                color: 'amber',
                gradient: 'from-amber-400 to-orange-600',
                targetAudience: '追求极致体验、预算充裕的高端旅客',
                scientificBasis: '精选奢华贵妇级品牌，覆盖「洁面-精华水-精华-面霜-眼霜-香水」顶级链路，一瓶顶多瓶',
                products: [
                    { brand: '香奈儿', name: '香奈儿山茶花洁面乳', category: '洁面', role: '高端洁面' },
                    { brand: '海蓝之谜', name: '海蓝之谜精萃水', category: '化妆水', role: '修护精萃水' },
                    { brand: '海蓝之谜', name: '海蓝之谜浓缩修护精华', category: '精华', role: '密集修护' },
                    { brand: '海蓝之谜', name: '海蓝之谜经典面霜', category: '面霜', role: '奇迹修护' },
                    { brand: '海蓝之谜', name: '海蓝之谜修护眼霜', category: '眼霜', role: '眼部修护' },
                    { brand: '爱马仕', name: '爱马仕尼罗河花园女士香水', category: '香水', role: '顶级香氛' }
                ],
                pairingLogic: '贵妇级品牌一站式配齐：香奈儿洁面温柔起泡、海蓝之谜精萃水/浓缩修护精华/经典面霜/修护眼霜组成「神奇活性精萃」修护矩阵，再配爱马仕尼罗河花园香水收尾，整套即顶配礼盒。',
                fullScript: `各位旅客朋友们好，今天为大家带来一套真正的顶配护肤组合。如果追求极致体验，想把最好的都给自己，这套「尊享奢华套装」就是为高端旅客准备的。每一款都是贵妇级品牌的传奇单品。

**第一步：香奈儿山茶花洁面乳**
从洁面开始就与众不同。香奈儿山茶花洁面，泡沫绵密细腻，山茶花精萃温和滋润，洗完脸是那种高级的洁净感，不拔干不紧绷，为整套奢华护理拉开序幕。

**第二步：海蓝之谜精萃水**
护肤之水，选精萃水。蕴含灵魂成分神奇活性精萃（Miracle Broth™），深层补水同时修护肌底，质地清透不粘腻，为后续精华打开吸收通道。

**第三步：海蓝之谜浓缩修护精华**
这是整套的核心。高浓度神奇活性精萃，密集修护肌底损伤，改善细纹、松弛、暗沉，是很多贵妇旅客的"皮肤急救针"。长途飞行后肌肤状态不佳时用它，迅速拉回好状态。

**第四步：海蓝之谜经典面霜**
修护精华之后，用经典面霜锁住一切。神奇活性精萃源自深海巨藻经3-4个月发酵萃取，深层修护滋润，改善干燥、粗糙、敏感。经典面霜是海蓝之谜的灵魂，用前在掌心温热乳化，按压上脸，仪式感十足。

**第五步：海蓝之谜修护眼霜**
眼周皮肤最娇贵，配海蓝之谜修护眼霜。神奇活性精萃加咖啡因，淡化细纹、改善黑眼圈和浮肿，让双眼重现明亮年轻的神采。

**第六步：爱马仕尼罗河花园女士香水**
最后配一瓶爱马仕尼罗河花园。清新柑橘调混着木质香，像尼罗河畔的花园一样优雅诗意，喷上即是高级感本身。一瓶香水，就是一套完整的品味宣言。

**搭配逻辑**
香奈儿洁面、海蓝之谜精萃水/浓缩精华/经典面霜/修护眼霜、爱马仕香水——全套顶级链路一站式配齐，自用是极致的犒赏，送人更是拿得出手的尊贵之礼。机上购买比专柜划算，正品保证假一赔四。春秋航空，为您甄选万米高空的尊享体验。
`
            }
        ];'''

if anchor2 in s:
    s = s.replace(anchor2, THREE_SETS, 1)
    log.append('A 已新增低/中/高性价比三套')
else:
    log.append('WARN A 锚点未匹配')

# ========== B. 精选套装渲染：默认全部展开 ==========
old_exp = """curatedScriptSets.forEach(function(set, idx) {
                        const isExpanded = expandedScriptSetId === set.id;"""
new_exp = """curatedScriptSets.forEach(function(set, idx) {
                        const isExpanded = true;"""
if old_exp in s:
    s = s.replace(old_exp, new_exp, 1)
    log.append('B 已改为默认全部展开')
else:
    log.append('WARN B 展开锚点未匹配')

# ========== C. 选用按钮置顶：在标题按钮后插入按钮组，并移除底部按钮 ==========
# C1 在 </button>（标题）后、if(isExpanded) 前插入置顶选用按钮
old_head = """                        html += `</button>`;
                        if (isExpanded) {
                            const matched = getMatchedScript(set.id);"""
new_head = """                        html += `</button>`;
                        html += `<div class="flex items-center gap-2 px-4 py-2 border-t border-${set.color}-100 bg-${set.color}-50/30 flex-wrap">`;
                        html += `<span class="text-xs font-semibold text-gray-600">快速使用：</span>`;
                        html += `<button onclick="selectScriptSetProducts(${idx})" class="px-3 py-1.5 bg-gradient-to-r from-${set.color}-500 to-${set.color}-600 text-white rounded-lg text-xs font-semibold shadow hover:shadow-md transition-all">✅ 一键选用本套产品</button>`;
                        html += `<button onclick="copySetScript('${set.id}')" class="px-3 py-1.5 bg-white border border-gray-200 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50 transition-all">📋 复制完整话术</button>`;
                        html += `</div>`;
                        if (isExpanded) {
                            const matched = getMatchedScript(set.id);"""
if old_head in s:
    s = s.replace(old_head, new_head, 1)
    log.append('C1 选用按钮已置顶')
else:
    log.append('WARN C1 标题锚点未匹配')

# C2 移除底部重复按钮（原底部选用按钮）
old_foot = """                            html += `<div class="flex justify-end gap-2 pt-1">`;
                            if (matched && matched.matchedProducts.length > 0) {
                                html += `<button onclick="selectMatchedProducts('${set.id}')" class="px-4 py-2 gradient-button text-gray-800 rounded-lg text-sm font-medium shadow-md hover:shadow-lg transition-all">✨ 选用匹配产品</button>`;
                            }
                            html += `<button onclick="selectScriptSetProducts(${idx})" class="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium transition-colors">使用默认产品</button>`;
                            html += `</div></div>`;"""
new_foot = """                            html += `</div>`;"""
if old_foot in s:
    s = s.replace(old_foot, new_foot, 1)
    log.append('C2 底部按钮已移除')
else:
    log.append('WARN C2 底部锚点未匹配')

# ========== D. 新增 copySetScript 复制函数（插在 selectScriptSetProducts 前） ==========
anchor_copy = "        // 一键选用话术套装中的产品"
func_copy = """        // 复制套装完整话术
        window.copySetScript = function(setId) {
            const set = curatedScriptSets.find(function(x){ return x.id === setId; });
            if (!set) return;
            const matched = getMatchedScript(setId);
            const text = (matched && matched.customScript) ? matched.customScript : set.fullScript;
            const ta = document.createElement('textarea');
            ta.value = text;
            document.body.appendChild(ta);
            ta.select();
            try { document.execCommand('copy'); showAlert('已复制「' + set.name + '」完整话术'); }
            catch(e) { showAlert('复制失败，请手动复制'); }
            document.body.removeChild(ta);
        };

        // 一键选用话术套装中的产品"""
if anchor_copy in s:
    s = s.replace(anchor_copy, func_copy, 1)
    log.append('D 已新增 copySetScript')
else:
    log.append('WARN D copy锚点未匹配')

if was:
    s = s.replace('\n', '\r\n')
with io.open(PATH, 'w', encoding='utf-8', newline='') as f:
    f.write(s)
print('完成:')
for l in log:
    print('  ' + l)