# -*- coding: utf-8 -*-
"""病假单据邮寄信息接入与板块整合（2026-09-18）
1) daily.html 病假管理：k4 整合单据「提交方式」（现场勤务保障室 / 邮寄综合管理处 + 地址收件人电话），
   标题与标签支持「交到哪里/邮寄」问法；k10 收窄为「非空勤差异」并引用 k4，去掉重复的接收/复核表述。
2) qa.html 知识库：病假全攻略「单据时限」增补邮寄方式（地址收件人电话），t 标签新增 邮寄/寄到哪/综合管理处 等问法。
用法：python _patch_sick_mail.py            # 执行
      python _patch_sick_mail.py --check    # 校验（不一致非零退出）
"""
import io, os, sys
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
DAILY = os.path.join(HERE, 'daily.html')
QA = os.path.join(HERE, 'qa.html')

FIXES_DAILY = [
    # ---- k4：单据上交 → 整合提交方式（现场/邮寄 + 地址） ----
    ("""{id:'k4',cat:'sick',hot:true,src:'手册3.1.10.12.3',q:'病假单据最晚什么时候交？逾期怎么办？',
 t:['上交','时限','5个日历日','30日','月末','逾期'],
 a:`<ul>
   <li>原则上不晚于请假后 <strong>5 个日历日</strong>将病假单据上交总部。</li>
   <li>特殊情况无法按节点上交：最晚在<strong>每月 30 日</strong>上交上月 26 日–本月 25 日的病假单（挂号单原件、药费单原件、病假证明原件、病历记录本复印件）。</li>
   <li>逾期未交：加扣日常管理分 <strong>10 分</strong>，并按<strong>旷工</strong>处理。</li>
   <li>示例：11月6日的病假单，最晚需在 <strong>11月30日</strong> 提交。</li>
   </ul>`},""",
     """{id:'k4',cat:'sick',hot:true,src:'手册3.1.10.12.3 / 综合行政',q:'病假单据最晚什么时候交？交到哪里（邮寄地址）？',
 t:['上交','时限','5个日历日','30日','月末','逾期','邮寄','寄到哪','综合管理处','地址','单据','提交方式'],
 a:`<ul>
   <li>原则上不晚于请假后 <strong>5 个日历日</strong>将病假单据上交总部。</li>
   <li>特殊情况无法按节点上交：最晚在<strong>每月 30 日</strong>上交上月 26 日–本月 25 日的病假单（挂号单原件、药费单原件、病假证明原件、病历记录本复印件）。</li>
   <li><strong>提交方式二选一</strong>：① 现场交至<strong>机组勤务保障室</strong>；② <strong>邮寄</strong>至综合管理处（外站/不便现场办理时建议优先邮寄，用顺丰或挂号信并保留寄出凭证，寄出后致电确认）。</li>
   <li><strong>邮寄地址</strong>：上海市长宁区<strong>虹桥路 2599 号春秋航空总部办公楼 2 楼（永融对面入口）</strong>；<strong>收件人</strong>：客舱服务部综合管理处（收）；<strong>联系电话</strong>：021-32315100。综合行政专员于工作日收取，月初完成复核。</li>
   <li>逾期未交：加扣日常管理分 <strong>10 分</strong>，并按<strong>旷工</strong>处理。</li>
   <li>示例：11月6日的病假单，最晚需在 <strong>11月30日</strong> 提交。</li>
   </ul>`},"""),
    # ---- k10：收窄为「非空勤差异」，引用 k4 邮寄地址 ----
    ("""{id:'k10',cat:'sick',hot:false,src:'手册/综合行政',q:'非空勤人员及单据接收有什么规定？',
 t:['非空勤','24小时','行政专员','月初复核','推送'],
 a:`<ul>
   <li>非空勤员工需在提出病假后 <strong>24 小时内</strong>将病假单据交至综合管理处。</li>
   <li>综合行政专员于<strong>工作日收取</strong>病假单据，并在<strong>月初</strong>完成复核。</li>
   <li>分队需关注 SMP 内的病假推送信息，持续监控病假人员情况。</li>
   </ul>`},""",
     """{id:'k10',cat:'sick',hot:false,src:'手册/综合行政',q:'非空勤人员病假单据有什么不同要求？',
 t:['非空勤','24小时','行政专员','月初复核','推送','邮寄'],
 a:`<ul>
   <li>非空勤员工需在提出病假后 <strong>24 小时内</strong>将病假单据交至综合管理处（现场提交或邮寄均可，邮寄地址见「病假单据最晚什么时候交」）。</li>
   <li>综合行政专员于<strong>工作日收取</strong>病假单据，并在<strong>月初</strong>完成复核。</li>
   <li>分队需关注 SMP 内的病假推送信息，持续监控病假人员情况。</li>
   </ul>`},"""),
]

FIXES_QA = [
    # ---- 病假全攻略：单据时限增补邮寄方式 ----
    ('<li><b>单据时限</b>：病假期限结束后 <strong>24 小时内</strong>交至<strong>机组勤务保障室</strong>；超 24~72 小时加扣日常管理分 <strong>5 分</strong>，超 72 小时加扣 <strong>10 分</strong>并按旷工处理；每月 <strong>30 日</strong>前补齐上月 26 日–本月 25 日单据，未交再扣 10 分、以此类推直至上交。</li>',
     '<li><b>单据时限</b>：病假期限结束后 <strong>24 小时内</strong>交至<strong>机组勤务保障室</strong>（外站不便现场办理可<strong>邮寄</strong>至综合管理处：上海市长宁区<strong>虹桥路 2599 号春秋航空总部办公楼 2 楼（永融对面入口）</strong>，收件人：客舱服务部综合管理处（收），电话 021-32315100）；超 24~72 小时加扣日常管理分 <strong>5 分</strong>，超 72 小时加扣 <strong>10 分</strong>并按旷工处理；每月 <strong>30 日</strong>前补齐上月 26 日–本月 25 日单据，未交再扣 10 分、以此类推直至上交。</li>'),
    # ---- 问法标签增补 ----
    ("t:['病假','请假流程','病假怎么请','病假流程','请病假','病假材料','证件','单据','病假需要交','病假扣多少','病假扣分','封顶','单据时限','上交','30日','勤务保障','挂号','药费','病假证明','病历','报备','值班经理','AOC','医疗观察期','恢复派遣'],", None),
]


def read(p):
    return io.open(p, encoding='utf-8', newline='').read()


def apply_file(path, fixes):
    s = read(path)
    n = 0
    for old, new in fixes:
        if new is None:
            continue
        if old in s:
            s = s.replace(old, new, 1)
            n += 1
        elif new not in s:
            raise SystemExit('!! 目标字符串未找到（可能已被改动）：' + path + ' :: ' + old[:40])
    return s, n


def main():
    check = '--check' in sys.argv
    ds = read(DAILY)
    qs = read(QA)
    daily_new, dn = apply_file(DAILY, FIXES_DAILY)
    qa_new, qn = apply_file(QA, FIXES_QA)
    # qa t 标签：单独做插入（在 '病假扣多少' 前插入新问法，避免依赖整行唯一）
    INS = ",'邮寄','寄到哪','综合管理处','地址','单据邮寄'"
    anchor = "'病假扣多少','病假扣分'"
    nc = 0
    if anchor in qa_new and INS not in qa_new:
        qa_new = qa_new.replace(anchor, "'病假扣多少'" + INS + ",'病假扣分'", 1)
        nc = 1
    if check:
        if dn or qn or nc:
            print('!! 病假邮寄补丁尚未应用（daily=%d qa=%d tags=%d）' % (dn, qn, nc)); sys.exit(1)
        print('  病假邮寄补丁 -> UP-TO-DATE')
        return
    if not (dn or qn or nc):
        print('  病假邮寄补丁 -> UP-TO-DATE（无需改动）'); return
    io.open(DAILY, 'w', encoding='utf-8', newline='').write(daily_new)
    io.open(QA, 'w', encoding='utf-8', newline='').write(qa_new)
    print('  已应用：daily %d 处、qa %d 处、标签 %d 处' % (dn, qn, nc))


if __name__ == '__main__':
    main()