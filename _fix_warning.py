# -*- coding: utf-8 -*-
"""绩效：修复预警人数与职位筛选不同步（乘务员筛选下出现乘务长数据）"""
import io
import re

PATH = u'_work\\广州综合绩效评定测试系统1.0(3).html'
with io.open(PATH, 'r', encoding='utf-8', newline='') as f:
    s = f.read()
was = ('\r' in s)
s = re.sub(r'\r+\n', '\n', s)
s = s.replace('\r', '\n')
log = []

# 1. 初始化时同步 AppState.filters.position = '乘务员'
old1 = """                    const positionFilter = document.getElementById('positionFilter');
                    if (positionFilter) positionFilter.value = '乘务员';"""
new1 = """                    const positionFilter = document.getElementById('positionFilter');
                    if (positionFilter) { positionFilter.value = '乘务员'; AppState.filters.position = '乘务员'; AppState.filters.team = AppState.filters.team || ''; }"""
if old1 in s:
    s = s.replace(old1, new1, 1)
    log.append('1 初始化同步 position')
else:
    log.append('WARN1 初始化锚点未匹配')

# 2. summary 渲染时，若 DOM positionFilter 与 state 不一致，以 DOM 为准（处理初始化/残留）
old2 = """                    list = Utils.filterSpecialPersonnel(list);
                    
                    if (AppState.filters.team) list = list.filter(p => p.team === AppState.filters.team);
                    if (AppState.filters.position) list = list.filter(p => p.position === AppState.filters.position);"""
new2 = """                    list = Utils.filterSpecialPersonnel(list);

                    // 职位筛选与下拉框保持同步（避免"乘务员筛选却计入乘务长"的错配）
                    const _domPosVal = document.getElementById('positionFilter')?.value;
                    if (_domPosVal) AppState.filters.position = _domPosVal;

                    if (AppState.filters.team) list = list.filter(p => p.team === AppState.filters.team);
                    if (AppState.filters.position) list = list.filter(p => p.position === AppState.filters.position);"""
if old2 in s:
    s = s.replace(old2, new2, 1)
    log.append('2 summary 渲染同步职位')
else:
    log.append('WARN2 summary 锚点未匹配')

# 3. 预警弹窗二次过滤改用 DOM 值（兜底）
old3 = """                            const currentPositionFilter = AppState.filters.position;
                            const filteredBelowAvg = currentPositionFilter 
                                ? belowAvg.filter(p => p.position === currentPositionFilter)
                                : belowAvg;"""
new3 = """                            const currentPositionFilter = document.getElementById('positionFilter')?.value || AppState.filters.position || '';
                            const filteredBelowAvg = currentPositionFilter 
                                ? belowAvg.filter(p => p.position === currentPositionFilter)
                                : belowAvg;"""
if old3 in s:
    s = s.replace(old3, new3, 1)
    log.append('3 预警弹窗二次过滤用 DOM 值')
else:
    log.append('WARN3 弹窗锚点未匹配')

# 4. 预警人数计算也基于已过滤 list（已在 summary 中 list=过滤后），此处兜底确保 stats 卡显示当前职位预警人数
old4 = """                    // 预警人数：低于平均绩效的人
                    const belowAvg = validPerfList.filter(p => (p.performance || 0) < avgPerf);"""
new4 = """                    // 预警人数：低于平均绩效的人（list 已按职位筛选，保证只统计当前筛选职位）
                    const belowAvg = validPerfList.filter(p => (p.performance || 0) < avgPerf);"""
if old4 in s:
    s = s.replace(old4, new4, 1)
    log.append('4 预警人数基于过滤后 list 计算')

if was:
    s = s.replace('\n', '\r\n')
with io.open(PATH, 'w', encoding='utf-8', newline='') as f:
    f.write(s)
print('完成:')
for l in log:
    print('  ' + l)