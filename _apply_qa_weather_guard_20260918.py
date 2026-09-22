# -*- coding: utf-8 -*-
"""你问我答 · 实时天气意图误吞手册问法 修复（2026-09-18）

问题：天气意图判定 isQuery 把「多少度 / 几度」视为天气关键词，
      导致「旋转座椅取出需要旋转多少度？」这类**手册/题库**问法被判为查天气，
      进而把「座椅取出需要旋转」当成城市去 geocoding → 返回「天气服务暂时连不上」，
      手册知识完全无法拉取。实测已复现。

修复：
  1) 天气关键词分为 强（天气/气温/下雨/降雨/降水/风速/风力/风大/热不热/冷不冷）
     与 弱（温度/多少度/几度）；
  2) 新增设备/器材/应急/题库语境排除（旋转·座椅·机门·滑梯·氧气·灭火·撤离·机型·角度·以内…）；
  3) 仅命中弱关键词时，必须另有天气语境线索（今天/明天/现在/实时/外面/当地/机场/气温…）才算查天气。
     真天气问法不受影响：「广州明天多少度」→ 通过；「外面热不热」→ 通过（强关键词）。

用法：python _apply_qa_weather_guard_20260918.py            # 执行
      python _apply_qa_weather_guard_20260918.py --check    # 校验
"""
import io, os, sys, shutil

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
QA = os.path.join(HERE, 'qa.html')

OLD = """const isQuery = t => {
    t = String(t || '').trim();
    if (!/(天气|气温|温度|下雨|降雨|降水|风速|风力|风大|热不热|冷不冷|多少度|几度)/.test(t)) return false;
    /* 规章/处置/注意类问法不是查实时天气，交回知识库（"客舱温度标准""雷雨天气怎么处置""下雨天注意什么"） */
    if (/(怎么办|怎么处理|怎么处置|怎么应对|怎么操作|怎么预防|怎么规定|如何处置|如何应对|如何处理|如何操作|预防|处置|规定|要求|标准|条例|手册|颠簸|除冰|防冰|影响|防范|防护|注意什么|注意哪些|注意事项)/.test(t)) return false;
    return true;
  };"""

NEW = """const isQuery = t => {
    t = String(t || '').trim();
    /* 天气关键词分强弱：强=明确的天气词；弱=温度/多少度/几度（歧义大，需天气语境兜底） */
    const strongWx = /(天气|气温|下雨|降雨|降水|风速|风力|风大|热不热|冷不冷)/.test(t);
    const weakWx   = /(温度|多少度|几度)/.test(t);
    if (!(strongWx || weakWx)) return false;
    /* 规章/处置/注意类问法不是查实时天气，交回知识库（"客舱温度标准""雷雨天气怎么处置""下雨天注意什么"） */
    if (/(怎么办|怎么处理|怎么处置|怎么应对|怎么操作|怎么预防|怎么规定|如何处置|如何应对|如何处理|如何操作|预防|处置|规定|要求|标准|条例|手册|颠簸|除冰|防冰|影响|防范|防护|注意什么|注意哪些|注意事项)/.test(t)) return false;
    /* 【2026-09-18 修复】设备/器材/应急/题库语境的「多少度·几度」不是天气：
       "旋转座椅取出需旋转多少度""机门向内侧收进多少度""氧气瓶压力多少 PSI" 等应回知识库 */
    if (/(旋转|座椅|机门|舱门|滑梯|氧气|灭火|安全带|撤离|应急|设备|器材|机型|A32\\d|B73\\d|角度|倾角|度数|不超过|以内|以上|以下|多少排|第几排|配备|数量|手册|题库|章节)/.test(t)) return false;
    /* 仅命中弱关键词时，必须另有天气语境线索，避免误吞手册问法 */
    if (!strongWx && !/(今天|明天|后天|现在|当前|此刻|实时|外面|室外|当地|本地|本地机场|机场|城市|气温|天气|下雨|航班天气)/.test(t)) return false;
    return true;
  };"""


def main():
    check = '--check' in sys.argv
    s = io.open(QA, encoding='utf-8', newline='').read().replace('\r\n', '\n')
    if NEW in s:
        print('  qa.html 天气意图守卫 -> UP-TO-DATE'); return
    if check:
        print('!! qa.html 天气意图守卫缺失（isQuery 仍是旧版）'); sys.exit(1)
    if OLD not in s:
        raise SystemExit('!! 未找到旧版 isQuery（可能已被改动，请人工核对）')
    bak = os.path.join(HERE, 'qa.bak_weather_guard_20260918.html')
    if not os.path.exists(bak):
        shutil.copy2(QA, bak); print('  备份 ->', os.path.basename(bak))
    out = s.replace(OLD, NEW, 1)
    io.open(QA, 'w', encoding='utf-8', newline='').write(out)
    print(f'  qa.html 天气意图守卫 已修复（{len(s)} -> {len(out)} chars）')


if __name__ == '__main__':
    main()
