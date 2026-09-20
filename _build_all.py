# -*- coding: utf-8 -*-
"""客舱小助手 · 一键构建 / 一键回归（M1-M3 收尾工具）
--------------------------------------------------------------------------------
用法：
  python _build_all.py            # 默认 all：构建 → 全套回归
  python _build_all.py build      # 只构建（sync check → kb-admin → spring → 4合1，任一步失败即停）
  python _build_all.py verify     # 只回归（全量语法检查 + 7 套逻辑验证）
--------------------------------------------------------------------------------
规则：
  - 构建链任一步失败立即终止并返回非零
  - 回归任一脚本失败则最终汇总显示 FAILED 并返回非零
"""
import io
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))

BUILD_STEPS = [
    (u'同步数据包引擎(4源)', u'python _sync_packs.py --check'),
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
    # ===== 2026-09-19 平板 3D「无模型」：可用性甄别（WebGL 探测/兜底/三分文案）=====
    (u'你问我答·3D可用性甄别(WebGL探测+回落2D+三分文案,幂等)', u'python _apply_qa_3dfix_20260919.py'),
    # ===== 2026-09-19 设计审核 P0-C：标题层级与 skip-link（必须在打包产物之前）=====
    (u'可访问性·标题层级+skip-link(幂等)', u'python _apply_a11y_20260919.py'),
    (u'壳层设计审核修复·顶栏对比度/字号/触控44px+平板档(幂等)', u'python _apply_shell_sync_20260919.py'),
    (u'构建 kb-admin(库管理)', u'python _build_kbadmin.py'),
    (u'构建 spring(9模块单文件)', u'python _gzip_build.py'),
    (u'构建 4合1(10模块离线版)', u'python _build_4in1.py'),
    (u'UX 美化注入(幂等,构建后补挂产物)', u'python _apply_ux_polish.py'),
    (u'你问我答·跳转落地页(9板块接收侧,幂等)', u'python _apply_qa_landing_20260919.py'),
]

# M1-M3 逻辑验证套件（Node 先行、Python 收尾）
VERIFY_SCRIPTS = [
    u'node _verify_packs.js',      # 引擎单测 46
    u'node _verify_packs_e2e.js',  # 消费端真实数据 23
    u'node _verify_packs_m13.js',  # kb-admin 数据包中心 30
    u'node _verify_packs_m14.js',  # 备份内容层隔离 14
    u'node _verify_packs_m15.js',  # 产物内嵌特征 40
    u'node _verify_packs_m2.js',   # 在线更新 27
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
    u'python _apply_qa_3dfix_20260919.py --check',             # 3D 可用性甄别在位（2026-09-19）
    u'python _apply_a11y_20260919.py --check',                 # 标题层级 + skip-link 在位（设计审核 P0-C）
    u'python _apply_shell_sync_20260919.py --check',           # 顶栏对比度/字号/44px 触控 + 平板档（设计审核 P0-A/B）
    u'node _ai_restore_verify_20260919.js',                    # AI 已恢复（2026-09-19 深夜用户指令）；localmode 验证器随之退役
    u'python _verify_nokey_all.py --quiet',                     # 全链路零密钥审计（源/gz/壳载荷/www/PWA/APK）
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
    r = subprocess.run(cmd, shell=True, cwd=HERE)
    if r.returncode != 0:
        print(u'!! %s 失败（exit=%d）' % (label, r.returncode))
        if fail_on_err:
            sys.exit(r.returncode)
    return r.returncode


def syntax_check():
    print(u'\n===== 全量语法检查 =====')
    node = 'node'
    fails = 0
    for name in SYNTAX_FILES:
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            print(u'  [SKIP] %s（文件不存在）' % name)
            continue
        s = io.open(path, encoding='utf-8', newline='').read()
        parts = re.findall(r'<script[^>]*>(.*?)</script>', s, re.S)
        js = '\n;\n'.join(parts)
        tmp = os.path.join(HERE, '__all_check_tmp.js')
        with io.open(tmp, 'w', encoding='utf-8') as f:
            f.write(js)
        r = subprocess.run([node, '--check', tmp], capture_output=True, text=True)
        os.remove(tmp)
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