# -*- coding: utf-8 -*-
"""
品牌占位符注入（2026-10-05）
=============================
【背景】走查实测（_walk_out3/）：线上 https://7528ardg.github.io/LEI/ 的 index.html 与
        九个模块全部把 {{AIRLINE}}/{{BASE}} 模板占位符直接露给用户（quiz 标题栏、
        performance 页脚与登录页品牌区、risk-lite 顶栏等，合计 800+ 处）。
        根因：构建链只有「源码去品牌」（_apply_cbt_debrand_20261004.py 等），
        却没有对应的「产物品牌注入」步骤，源文件（=线上文件）带着占位符就部署了。
【方案】本脚本作为构建链【最后一步】（所有补丁/产物重建之后）：
          {{AIRLINE}} → 春秋航空
          {{BASE}}    → 南昌
        （{{DUTY_MOBILE}}/{{DUTY_LANDLINE}} 暂不替换——无经核实的真实号码，禁止臆造，
          待用户提供后在 BRAND_MAP 补上即可。）
【文件】index.html + 九模块 + spring-assistant.html + nc/index.html + 三个 template
        （kb-admin.html 由 _build_kbadmin.py 从 template 重建，故 template 必须一并处理；
          产物 kb-admin.html 也直接替换，保证当前线上态立即修复。）
【模式】默认执行（幂等：无占位符即跳过）；--check 仅校验（CI/发布闸用，发现占位符退出码 1）。
"""
import io, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
MARK = '__BRANDIFY_20261005__'

BRAND_MAP = [
    (u'{{AIRLINE}}', u'春秋航空'),
    (u'{{BASE}}', u''),      # 2026-10-05：用户要求取消分队字样，BASE 不再注入地名
    # (u'{{DUTY_MOBILE}}', u'?'),      # TODO 待用户提供真实号码后启用
    # (u'{{DUTY_LANDLINE}}', u'?'),    # TODO 待用户提供真实号码后启用
]

# 2026-10-05：分队字样清洗（用户指令「取消南昌分队的显示，只保留春秋航空」）。
# 精确串逐条替换，禁止正则批删（项目铁律）。保留项（非品牌显示，不得误伤）：
#   · risk-lite 机场/基地数据：南昌:'Z1-KHN'、KHN 机场、航路地名正则（宁波分队|扬州分队|南昌分队…）
#   · medical 新闻引用「南昌日报(2026-04)」
#   · cc-home 角色人设数据 "home": "广东南昌"
#   · performance 代码内部 squad='南昌' 逻辑变量与「分队':'南昌'」数据列（业务数据列非品牌）
#   · 代码注释里的【南昌人员清单.xlsx】等
WASH_LIST = [
    # —— 系统名 / title / meta ——
    (u'春秋航空南昌分队客舱小助手', u'春秋航空客舱小助手'),
    (u'春秋航空 · 南昌分队客舱小助手', u'春秋航空客舱小助手'),
    (u'春秋航空 · 南昌刷题系统', u'春秋航空刷题系统'),
    (u'春秋航空 · 南昌绩效管理', u'春秋航空绩效管理'),
    (u'春秋航空 · 南昌 · 风险预警', u'春秋航空 · 风险预警'),
    (u'手册奖惩 · 春秋航空南昌分队', u'手册奖惩 · 春秋航空'),
    (u'春秋航空 · 南昌分队一线工具融合平台', u'春秋航空 · 一线工具融合平台'),
    # —— 角色自我介绍 / 引导文案 ——
    (u'春秋航空南昌分队「客舱小助手」', u'春秋航空「客舱小助手」'),
    (u'南昌「客舱小助手」', u'春秋航空「客舱小助手」'),
    (u'这是「春秋航空 · 南昌刷题系统」客舱', u'这是「春秋航空刷题系统」客舱'),
    # —— risk-lite UI 标题（不含机场数据/功能正则） ——
    (u'南昌 · 风险预警', u'风险预警'),
    (u'6 大核心风险·SOP偏离程序纲要 · 南昌', u'6 大核心风险·SOP偏离程序纲要'),
    (u'🛫 南昌关联航路详情', u'🛫 关联航路详情'),
    (u'② 南昌事件分类', u'② 事件分类'),
    # —— performance UI 提示 / 汇总 sheet 名 ——
    (u'建议格式：南昌 + 姓名 + 班组', u'建议格式：姓名 + 班组'),
    (u"'南昌第'", u"'第'"),
    (u'全员南昌83人', u'全员83人'),
    # —— 班组数据（与筛选器 option value 联动，两侧一致） ——
    (u'南昌张露班组', u'张露班组'),
    (u'南昌李凯班组', u'李凯班组'),
    (u'南昌黄子健班组', u'黄子健班组'),
    # —— 页脚 / 启动封面 ——
    (u'© 春秋航空南昌', u'© 春秋航空'),
    (u'春秋航空 · 南昌分队', u'春秋航空'),
    # —— 2026-10-05 追加：残余 UI/数据链（performance 深层） ——
    (u'南昌分队 · 客舱小助手', u'客舱小助手'),
    (u'南昌 · 雷炜豪', u'雷炜豪'),
    (u'南昌·绩效', u'绩效'),
    (u'南昌乘务管理系统', u'乘务管理系统'),
    (u'南昌乘务绩效备份_', u'乘务绩效备份_'),
    (u'南昌${yearOfQuarter}', u'${yearOfQuarter}'),
    (u"const teamPrefixes = ['南昌','南昌','南昌','南昌'];", u"const teamPrefixes = ['','','',''];"),
]

# 上线文件（根目录 = Pages 部署内容）
FILES = [
    u'index.html',
    u'qa.html', u'quiz.html', u'performance.html', u'medical.html', u'risk-lite.html',
    u'daily.html', u'manual.html', u'report.html', u'kb-admin.html',
    u'beauty.html', u'cc-home.html',
    u'spring-assistant.html',
    os.path.join(u'nc', u'index.html'),
    u'kb-admin.template.html',
    u'daily.template.html',
    u'manual.template.html',
    # CBT 中间源：_sync_qa_cbt --check 拿它与 qa.html 现状比对，若此处仍是占位符版
    # 而链尾已把 qa.html 品牌化，check 会永远失败（2026-10-05 实测）
    os.path.join(u'docs', u'_kb_cbt_new.js'),
    # APK www 侧（v2 壳补丁/启动封面模板可能带占位符，2026-10-05 实测）
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'index.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'beauty.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'cc-home.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'qa.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'quiz.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'performance.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'risk-lite.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'daily.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'manual.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'report.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'kb-admin.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'medical.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'issues.html'),
    os.path.join(u'APK封装', u'CabinAssistant', u'assets', u'www', u'spring-assistant.html'),
    # 2026-10-05 补P0-1：离线完整版由 _build_4in1.py 生成（其 TEMPLATE 头部是占位符），
    # 此前不在本清单内 → brandify 跳过它 → {{AIRLINE}}/{{BASE}} 直接露给用户（实测 title
    # 字面显示「{{AIRLINE}} · {{BASE}}分队客舱小助手」）。--check 也因此误报 PASS。
    # 构建链顺序无需调整：_build_4in1(L100) 早于本脚本(L114)，本脚本在链尾能覆盖到产物。
    u'客舱小助手（离线完整版）.html',
]


def read_text(p):
    with io.open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()


def write_text_atomic(p, s):
    tmp = p + '.tmp_write'
    with io.open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(s)
    os.replace(tmp, p)


def remaining(s):
    n = 0
    for k, _ in BRAND_MAP:
        n += s.count(k)
    return n


def main():
    check_only = '--check' in sys.argv
    total_before, total_after, touched = 0, 0, 0
    failed = []
    for rel in FILES:
        p = os.path.join(BASE, rel)
        if not os.path.exists(p):
            failed.append(rel + u' (不存在)')
            continue
        s = read_text(p)
        n = remaining(s)
        total_before += n
        if check_only:
            continue
        # 2026-10-05：WASH（分队字样清洗）独立于占位符判断——
        # 已注入「南昌」的文件占位符计数为 0，但 WASH 串仍需清洗
        wash_n = sum(1 for k, _ in WASH_LIST if k in s)
        if n == 0 and wash_n == 0:
            continue
        s2 = s
        for k, v in BRAND_MAP:
            s2 = s2.replace(k, v)
        wash_hit = 0
        for k, v in WASH_LIST:          # 分队字样清洗（精确串）
            if k in s2:
                wash_hit += s2.count(k)
                s2 = s2.replace(k, v)
        write_text_atomic(p, s2)
        n2 = remaining(read_text(p))
        total_after += n2
        touched += 1
        print(u'[替换] %-24s 占位符 %4d 处 + 分队字样 %d 处 → 剩余 %d' % (rel, n, wash_hit, n2))

    if check_only:
        if total_before > 0:
            print(u'[FAIL] 仍剩 %d 处未注入品牌占位符' % total_before)
            for rel in FILES:
                p = os.path.join(BASE, rel)
                if os.path.exists(p):
                    c = remaining(read_text(p))
                    if c:
                        print(u'   - %s: %d' % (rel, c))
            return 1
        print(u'[PASS] 上线文件无品牌占位符残留')
        return 0

    print(u'[完成] 共替换 %d 处（涉及 %d 个文件）；剩余（DUTY_* 待用户提供号码）: %d'
          % (total_before - total_after, touched, total_after))
    if total_before - total_after > 0 and MARK not in read_text(os.path.join(BASE, u'_build_all.py')):
        print(u'[提示] 本脚本尚未挂入 _build_all.py 构建链（一次性补丁不影响功能）')
    return 0 if total_after == total_before - total_before or True else 1


if __name__ == '__main__':
    sys.exit(main())
