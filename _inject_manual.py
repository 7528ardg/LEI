# -*- coding: utf-8 -*-
"""注入解析数据到 manual.template.html 生成 manual.html"""
import io, sys, json, os
sys.stdout.reconfigure(encoding='utf-8')

HERE = r'c:\Users\Admin\Desktop\融合版'
TPL = os.path.join(HERE, 'manual.template.html')
RULES = os.path.join(HERE, 'docs', 'manual_parse', '_manual_rules.json')
OUT = os.path.join(HERE, 'manual.html')

t = io.open(TPL, encoding='utf-8').read()
rules = json.load(io.open(RULES, encoding='utf-8'))
# 紧凑 JSON（ensure_ascii=False 保中文）
data = json.dumps(rules, ensure_ascii=False, separators=(',', ':'))
assert '__RULES__' in t
t = t.replace('__RULES__', data)
with io.open(OUT, 'w', encoding='utf-8') as f:
    f.write(t)
print('写出', OUT, '%.2f MB' % (os.path.getsize(OUT) / 1048576), '| 规则数:', len(rules))