# -*- coding: utf-8 -*-
"""客舱小助手 · 一键构建 / 一键回归（M1-M3 收尾工具）
--------------------------------------------------------------------------------
用法：
  python _build_all.py            # 默认 all：构建 → 全套回归
  python _build_all.py build      # 只构建（见下方 BUILD_STEPS：引擎同步 → 各模块补丁 → kb-admin
                                  #   → spring 9模块 → 4合1 10模块 → UX 美化 → 落地页 → 在线版瘦壳）
  python _build_all.py verify     # 只回归（全量语法检查 + 全套逻辑/针/零密钥验证）
--------------------------------------------------------------------------------
规则：
  - 构建链任一步失败立即终止并返回非零
  - 回归任一脚本失败则最终汇总显示 FAILED 并返回非零
"""
import io
import os
import re
import shlex
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))

BUILD_STEPS = [
    # ===== 2026-09-21 加在最前：行尾必须先是 LF，否则下面所有按 LF 匹配标记块的补丁都会失配 =====
    # 根因：core.autocrlf=true + 无 .gitattributes → 任何一次 git checkout/还原更改都会把工作区
    #       文件写成 CRLF（实测 index.html 等 5 个壳被写成纯 CRLF，导航补丁当场抛「缺收口」）。
    (u'行尾归一·CRLF→LF(护住标记块匹配)', u'python _normalize_lf_20260921.py'),
    (u'同步数据包引擎(4源)', u'python _sync_packs.py --check'),
    # 2026-09-21 新增：库管理总台的「全量数据包引擎」同样单一来源（docs/_fullpack_engine.js），
    # 消费端 kb-admin.template.html。构建期用 --check 卡住漂移，避免运行时与校验脚本两套实现。
    (u'同步全量数据包引擎(kb-admin单一来源)', u'python _sync_fullpack.py --check'),
    (u'同步日期匹配引擎(3源)', u'python _sync_date_match.py --check'),
    (u'同步时节引擎(单一来源)', u'python _sync_season.py --check'),
    (u'同步大撤专项(2源)', u'python _sync_dache.py --check'),
    (u'同步CBT练习场景数据(quiz单一来源)', u'python _sync_cbt.py'),
    (u'培训考核题库 = 原题库 + CBT练习独立分类(幂等)', u'python _apply_cbt_bank_20260918.py'),
    (u'注入CBT分区/CBT答题板块(幂等)', u'python _apply_cbt_scene_20260918.py'),
    (u'扩展成就系统(CBT题库,幂等)', u'python _apply_cbt_achv_20260918.py'),
    (u'你问我答·接入CBT题库资源库(幂等)', u'python _sync_qa_cbt.py'),
    (u'你问我答·天气意图误吞手册问法修复', u'python _apply_qa_weather_guard_20260918.py'),
    (u'你问我答·跳转目标修复(CBT/大撤去对应板块,幂等)', u'python _apply_qa_jumpfix_20260919.py'),
    (u'你问我答·跨板块桥接(深链/深跳/面包屑,幂等)', u'python _apply_qa_bridge_20260919.py'),
    (u'你问我答·会话记忆(持久化/多轮/抽屉,幂等)', u'python _apply_qa_memory_20260919.py'),
    (u'你问我答·状态与反馈(aria-busy/失败出路/形象联动,幂等)', u'python _apply_qa_ux_20260919.py'),
    (u'你问我答·能力增强(语音/跨板块数据/跨域引导/场景推荐,幂等)', u'python _apply_qa_capability_20260919.py'),
    (u'注入导航升级(#1/#3/#4/#5/#9,幂等)', u'python _apply_nav_20260917.py'),
    (u'同步壳层弹窗引擎(index→两模板)', u'python _sync_shell_js.py'),
    (u'kb-admin AI 客户端对齐(降级链+熔断,幂等)', u'python _apply_kbadmin_ai_chain_20260919.py'),
    # ===== 2026-09-19 彻底无密钥 / 本地模式 / 话术向导增强（必须在打包产物之前）=====
    (u'你问我答·琴模块副本去重(幂等)', u'python _dedupe_qa_piano_20260919.py'),
    (u'你问我答·首屏快问行(幂等)', u'python _apply_qa_quickstart_20260919.py'),
    (u'你问我答·话术向导增强(产品名直触发+换个风格,幂等)', u'python _apply_qa_wizard2_20260919.py'),
    # ===== 2026-09-21 批1 增强：答案卡工具条（复制/朗读/收藏/置信度）+「我的」面板（收藏/练习/字号）
    #   A 锚定 QUICKSTART_END，故必须排在 quickstart 之后；B 锚定 A 的 END，故 A 必须在前。=====
    (u'你问我答·答案卡增强(复制/朗读/收藏/置信度徽标,幂等)', u'python _apply_qa_answer_tools_20260921.py'),
    (u'你问我答·我的面板(收藏/练习趋势/字号三档,幂等)', u'python _apply_qa_mypanel_20260921.py'),
    (u'你问我答·AI赋魂(问法改写/指代消解/未明示需求/强制溯源,幂等)', u'python _apply_qa_ai_brain_20260921.py'),
    # ===== 2026-09-21 销售板块话术库修复+补充（结构/红线/口径/冗余/报价/场景/库外商品/酒类补齐）
    #   幂等（重复执行 Δ=0，全项 skip）；自带 node --check 语法闸，失败则不落盘。
    #   必须在 _gzip_build / _build_4in1 / _build_hosted 之前，产物才能带上修复后的 beauty.html。=====
    (u'销售板块话术库修复+补充(结构/红线/口径/去重/补充,幂等)', u'python _apply_scriptlib_fix_20260921.py'),
    # 2026-09-21 补：话术库是独立数据块，生成引擎的 tsSanitize 管不到它。
    # 本补丁补上 scriptLibGuard() 四道闸（入库/复制/渲染兜底/本地读入），
    # 顺带修「块级 const 未挂 window 导致按钮 ReferenceError」与「整段文案塞进 onclick 破串」。
    # 必须排在 _apply_scriptlib_fix 之后（其口径修复以 fix 后的文案为锚点）。
    (u'销售话术库入库闸(保存/复制/渲染/读入,幂等)', u'python _apply_scriptlib_guard_20260921.py'),
    # ===== 2026-09-19 平板 3D「无模型」：可用性甄别（WebGL 探测/兜底/三分文案）=====
    (u'你问我答·3D可用性甄别(WebGL探测+回落2D+三分文案,幂等)', u'python _apply_qa_3dfix_20260919.py'),
    # ===== 2026-09-19 设计审核 P0-C：标题层级与 skip-link（必须在打包产物之前）=====
    (u'可访问性·标题层级+skip-link(幂等)', u'python _apply_a11y_20260919.py'),
    (u'壳层设计审核修复·顶栏对比度/字号/触控44px+平板档(幂等)', u'python _apply_shell_sync_20260919.py'),
    # 2026-09-21 补入：cc-home.html / daily.html 的唯一生成器原先不在链里，
    # 改了模板跑一键构建会「成功」却发布陈旧模块且全程不报错。必须排在打包步骤之前。
    (u'构建 CC之家模块', u'python _build_home.py'),
    (u'构建 日常问题模块', u'python _build_daily.py'),
    (u'构建 kb-admin(库管理)', u'python _build_kbadmin.py'),
    # 2026-09-22 接入：站点侧把模块内联 base64 大图抽成 assets/img/*（首屏瘦身，见 _verify_inlineimg）。
    #   必须在打包步骤之前跑：_build_4in1 会把 assets/img 回填成 data URI（保单文件自包含），
    #   _build_hosted 会把 assets/img 拷进在线版目录 —— 两者都要拿到「已外置」的模块。
    #   本步幂等（无大图即跳过）。注意：_build_home/_build_daily/_build_kbadmin 是从模板重建模块的，
    #   模板里仍是内联形态 → 不接这一步，「一键构建」会把站点重新养胖。
    (u'站点图集外置(内联大图→assets/img,幂等)', u'python _extract_inline_images_20260921.py'),
    (u'构建 spring(9模块单文件)', u'python _gzip_build.py'),
    (u'构建 4合1(10模块离线版)', u'python _build_4in1.py'),
    (u'UX 美化注入(幂等,构建后补挂产物)', u'python _apply_ux_polish.py'),
    (u'你问我答·跳转落地页(9板块接收侧,幂等)', u'python _apply_qa_landing_20260919.py'),
    # 2026-09-21 接入：_build_hosted 原先不在链里，「一键构建」既不产在线版也不刷新瘦壳。
    # 它内部会重建 _gzip_build/_build_4in1/_apply_ux_polish（幂等），故必须放在所有模块补丁之后，
    # 这样壳内产物才能带上 landing/ux_polish 等最后的改动。
    (u'构建在线版(瘦壳+mods/*.gz,含壳内产物重建)', u'python _build_hosted.py'),
    # 收尾再抽一次：_apply_ux_polish / landing 等最后几步也可能往模块里塞图，
    # 站点根目录的模块必须是「已外置」形态，否则一次 git add 就把 9MB 的 qa.html 推回去。
    (u'站点图集外置·产物收尾(幂等)', u'python _extract_inline_images_20260921.py'),
]

# M1-M3 逻辑验证套件（Node 先行、Python 收尾）
VERIFY_SCRIPTS = [
    u'python _normalize_lf_20260921.py --check',   # 行尾全部 LF（CRLF 会让补丁的标记块匹配静默/硬停）
    u'node _verify_packs.js',      # 引擎单测 46
    u'node _verify_packs_e2e.js',  # 消费端真实数据 23
    u'node _verify_packs_m13.js',  # kb-admin 数据包中心 30
    u'node _verify_packs_m14.js',  # 备份内容层隔离 14
    u'node _verify_packs_m15.js',  # 产物内嵌特征 40
    u'node _verify_packs_m2.js',   # 在线更新 27
    # 2026-09-21 库管理总台：全量数据包「导出 → 识别 → 还原 → 一致性」
    u'node _verify_kb_fullpack.js',     # 引擎级往返（8 源 4914 条逐条深比对 / 篡改拦截 / 编辑删除往返，51 项）
    u'node _verify_kb_console_e2e.js',  # 真实浏览器端到端（查看/编辑/删除/导出下载/重新导入/还原复核/撤销，29 项）
    u'node _verify_scriptlib_guard.js',          # 销售话术库入库闸（红线拦截/自动改写不误伤/1045 条全库扫描，34 项）
    # 2026-09-22 站点图集外置：真实起静态服务加载 qa/cc-home iframe，断言 img 无加载失败、assets/img 无 404（6 项）
    u'node _verify_inlineimg_20260921.js',
    u'python _apply_scriptlib_guard_20260921.py --check',  # 入库闸四道闸 + 库内口径修复 在位
    u'node _verify_date_match.js',  # 日期匹配引擎回归（节日词/修饰语/农历/通用节点/相对时间/跨年/表外估算）
    u'node _verify_se_lazy.js',     # SeasonEngine 懒获取回归（反序注入不再静默降级农历/节气）
    u'node _verify_fest_hookup.js',        # 节日识别 → 话术挂载 端到端
    u'node _verify_script_gen.js 20260829',  # 话术生成引擎回归（6类x12套组合 × 品类匹配审计）
    u'node _verify_full_script.js 20260829', # 全话术链路回归（随机24套×3次：开场→落地前下单 结构/语义/违禁词/品牌重复/句级重复）
    u'node _verify_prod_cats.js',  # 商品库×品类路由×竞品库结构核验（字段完整/分型不误判/场景覆盖/工作台可选中/竞品价格合法）
    u'node _verify_batches.js',    # 批量补录批次数据合规核验（品类白名单/违禁词/价格行/话术分类/id 唯一）
    u'node _verify_ai_price.js',   # 竞品分析 AI 更新价格（JSON 解析/覆盖层/预设与自定义应用）
    u'node _verify_qa_wakeup.js',   # 你问我答跨板块唤醒（33 用例：日常/手册/大撤/医疗/绩效/事件报告/病假）
    u'node _verify_qa_assoc.js',    # 你问我答候选追问+联想记忆（未收录表述候选收集/确认写入记忆/精确模糊命中/都不是跳过/撤销/200条上限/失效降级）
    u'node _verify_qa_bridge.js',   # 你问我答跨板块桥接（URL 深链 / cc:nav-jump 深跳 / cc:crumb 上报 / jumpTo 带上下文；真实浏览器 22 项）
    u'node _verify_qa_memory.js',   # 你问我答会话记忆（落盘+reload 恢复 / AI 请求真的带历史 / 记忆抽屉撤销与清空；真实浏览器 17 项）
    u'node _verify_qa_capability.js',  # 你问我答能力增强（语音降级 / 跨板块数据进上下文 / 跨域引导 / 场景推荐；真实浏览器 15 项）
    u'node _verify_qa_landing.js',     # 你问我答跳转落地闭环（URL 通道 / 填入搜索框 / qa→板块接住并消费 / TTL 与边界；真实浏览器 12 项）
    u'node _verify_qa_jumpfix.js',     # 你问我答跳转目标（CBT→培训考核 / 大撤→答题 / 手册→手册奖惩，且不再误显「去日常库再问」；20 项）
    u'node _qa_enh_verify_20260921.js', # 你问我答批1增强（答案卡工具条复制/朗读/收藏/置信度 + 我的面板收藏/练习趋势/字号；31 项）
    u'node _e2e_apk_www_test.js',      # APK 内容 + 虚拟域实测（直接读 APK 内 assets/www + https://cabin.local；29 项）
    u'python _verify_packs_m3.py', # 发布管线 19
    u'python _verify_assets.py',   # 形象IP 素材完整性（母版/抠图/精灵/原稿_clean 覆盖/模型登记）
    u'node _verify_ccsheet_static.js',  # 十种弹窗交互引擎静态守护（index/两模板：CCSheet/动效层/--embed-bottom/深色打通/更多面板走引擎）
    u'node _verify_nav_20260917.js',  # 导航升级守护（三壳一致/12模块元数据/深跳桥/限高内滚+关闭三路径）
    u'python _apply_ux_polish.py --check',  # UX 美化标记块在位（14 个模块/模板）
    u'python _sync_cbt.py --check',         # CBT 练习场景数据 = docs/_cbt_kb.js 单一来源
    u'python _apply_cbt_bank_20260918.py --check',   # 培训考核题库 = 原题库 2181 + CBT练习 785（独立分类）
    u'python _apply_cbt_scene_20260918.py --check',  # 培训考核 CBT练习分区 + 大撤应急 CBT 答题板块
    u'python _apply_cbt_achv_20260918.py --check',   # CBT 题库专项成就（15 枚）
    u'python _sync_qa_cbt.py --check',               # 你问我答 CBT题库 资源库 = docs/_kb_cbt_new.js
    u'python _apply_qa_weather_guard_20260918.py --check',  # 天气意图不误吞手册/题库问法
    u'python _apply_qa_bridge_20260919.py --check',         # 你问我答跨板块桥接标记块在位
    u'python _apply_qa_memory_20260919.py --check',         # 你问我答会话记忆标记块在位
    u'python _apply_qa_ux_20260919.py --check',             # 你问我答状态与反馈标记块在位
    u'python _apply_qa_capability_20260919.py --check',     # 你问我答能力增强标记块在位
    u'python _apply_qa_landing_20260919.py --check',        # 你问我答跳转落地页（9 板块）标记块在位
    u'python _apply_qa_jumpfix_20260919.py --check',        # 你问我答跳转目标修复在位
    u'python _apply_kbadmin_ai_chain_20260919.py --check',  # kb-admin AI 降级链对齐（E 组）
    u'python _dedupe_qa_piano_20260919.py',                   # 琴模块恰好 1 份
    u'python _apply_qa_quickstart_20260919.py --check',        # 首屏快问行在位
    u'python _apply_qa_wizard2_20260919.py --check',           # 话术向导增强在位
    u'python _apply_qa_answer_tools_20260921.py --check',      # 答案卡工具条（复制/朗读/收藏/置信度）在位
    u'python _apply_qa_mypanel_20260921.py --check',           # 「我的」面板（收藏/练习/字号）在位
    u'python _apply_qa_ai_brain_20260921.py --check',          # AI 赋魂（问法改写/指代消解/未明示需求/强制溯源）在位
    u'node _verify_qa_ai_brain.js',                            # AI 赋魂四件事 + 三处接缝未被后续补丁踩坏（41 项）
    u'node _verify_perf_decrypt_link.js',                      # 绩效跨板块链路：performance 加密落库 → qa 解密还原（真实路径 20 项；来源：2026-09-21 审查 P0）
    u'python _apply_qa_3dfix_20260919.py --check',             # 3D 可用性甄别在位（2026-09-19）
    u'python _apply_a11y_20260919.py --check',                 # 标题层级 + skip-link 在位（设计审核 P0-C）
    u'python _apply_shell_sync_20260919.py --check',           # 顶栏对比度/字号/44px 触控 + 平板档（设计审核 P0-A/B）
    u'node _ai_restore_verify_20260919.js',                    # AI 已恢复（2026-09-19 深夜用户指令）；localmode 验证器随之退役
    u'python _verify_nokey_all.py --quiet',                     # 全链路零密钥审计（源/gz/壳载荷/www/PWA/APK）
    u'python _verify_hosted.py --quiet',                        # 在线版瘦壳体检（模块已置空/fetch 逻辑/JS 语法/mods 可解压）
    u'python _check_needles.py --quiet',                        # 最终产物针检查（移动端加固针/3D 针/反向针/壳内载荷取证）
    u'node _verify_embed_gap_20260922.js',                      # 嵌入态「死带空白」回归：5 视口 × 切 tab 后 + 独立打开，main 底边须贴合 iframe 底边
    u'python _check_apk_sync.py',                           # APK 内 assets/www 与源同步（落后即失败，防「改了源没装配」）
]

# 全量语法检查覆盖：全部模块源 + 三外壳/产物（排除 .tmp_ 调试文件）
SYNTAX_FILES = [
    u'index.html',
    u'cc-home.html',
    u'qa.html', u'quiz.html', u'performance.html', u'beauty.html',
    u'medical.html', u'daily.html', u'manual.html', u'report.html',
    u'risk-lite.html', u'kb-admin.html', u'kb-admin.template.html',
    u'issues.html',
    u'spring-assistant.html', u'客舱小助手（离线完整版）.html',
]


def run(cmd, label, fail_on_err=True):
    print(u'\n==> ' + label)
    print(u'    ' + cmd)
    # 2026-09-21：不再用 shell=True + 裸 python。shell=True 依赖系统 PATH 解析解释器，
    # venv / 多 Python 并存时子步骤会跑在另一个解释器上；改用 sys.executable 保证与本进程一致。
    argv = shlex.split(cmd)
    if argv and argv[0] in ('python', 'python3', 'py'):
        argv = [sys.executable] + argv[1:]
    try:
        r = subprocess.run(argv, cwd=HERE)
    except FileNotFoundError as e:
        print(u'!! 命令可执行文件缺失：%s（%s）' % (argv[0], e))
        if fail_on_err:
            sys.exit(2)
        return 2
    if r.returncode != 0:
        print(u'!! %s 失败（exit=%d）' % (label, r.returncode))
        if fail_on_err:
            sys.exit(r.returncode)
    return r.returncode


def syntax_check():
    print(u'\n===== 全量语法检查 =====')
    node = 'node'
    fails = 0
    # 2026-09-21：临时文件改为「固定路径 + 覆盖写，不再 os.remove」。
    # 原因：每个文件都删一次，在做过大批量归档/清理的会话里累计删除数会触发
    # 文件安全护栏（SAFE_DELETE_BULK_CONFIRM_REQUIRED）而中断回归；且该文件本就
    # 被根级 /_* 规则 gitignore，留一个缓存文件无害。
    tmp = os.path.join(HERE, '_syntax_check_tmp.js')
    for name in SYNTAX_FILES:
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            print(u'  [SKIP] %s（文件不存在）' % name)
            continue
        s = io.open(path, encoding='utf-8', newline='').read()
        parts = re.findall(r'<script[^>]*>(.*?)</script>', s, re.S)
        js = '\n;\n'.join(parts)
        with io.open(tmp, 'w', encoding='utf-8', newline='') as f:
            f.write(js)
        try:
            r = subprocess.run([node, '--check', tmp], capture_output=True, text=True)
        except FileNotFoundError:
            print(u'  !! 未找到 node（请把 node 加入 PATH），无法执行语法检查')
            sys.exit(2)
        ok = r.returncode == 0
        print(u'  %s -> %s' % (name, 'SYNTAX_OK' if ok else 'SYNTAX_ERR'))
        if not ok:
            fails += 1
            print(r.stderr[:1200])
    if fails:
        print(u'!! 语法检查 %d 个文件失败' % fails)
        sys.exit(1)
    print(u'  语法检查通过（%d 文件）' % len(SYNTAX_FILES))


def build_all():
    print(u'===== 构建链 =====')
    for label, cmd in BUILD_STEPS:
        run(cmd, label)
    for name in [u'spring-assistant.html', u'客舱小助手（离线完整版）.html', u'kb-admin.html']:
        p = os.path.join(HERE, name)
        if os.path.exists(p):
            print(u'  %s %.2f MB' % (name, os.path.getsize(p) / 1048576))
    print(u'构建链完成。')


def verify_all():
    print(u'\n===== 逻辑回归 =====')
    fails = 0
    for script in VERIFY_SCRIPTS:
        print(u'\n--- ' + script + ' ---')
        r = run(script, script, fail_on_err=False)
        if r != 0:
            fails += 1
    print(u'\n===== 汇总 =====')
    print(u'语法：OK')
    print(u'逻辑：%d 套失败 / 共 %d 套' % (fails, len(VERIFY_SCRIPTS)))
    if fails:
        sys.exit(1)
    print(u'VO 全部通过：构建产物与数据包体系（M1-M3）回归 199+ 项全绿。')


def main():
    mode = u'all'
    if len(sys.argv) > 1 and sys.argv[1] in (u'build', u'verify'):
        mode = sys.argv[1]
    print(u'客舱小助手 一键工具 —— 模式：%s' % (u'构建+回归' if mode == u'all' else (u'构建' if mode == u'build' else u'回归')))
    if mode in (u'build', u'all'):
        build_all()
    if mode in (u'verify', u'all'):
        syntax_check()
        verify_all()


if __name__ == '__main__':
    main()