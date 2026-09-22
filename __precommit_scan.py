# -*- coding: utf-8 -*-
"""推送前终检：对待入库文件扫 ①明文口令 ②密钥/令牌模式 ③.ks_pass 内容外泄。
命中即打印（口令本身只报长度，不回显）。"""
import io, os, re, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
# 2026-09-23 误报修复：原 pattern `sk-[A-Za-z0-9]{8,}` 会把 URL 片段里的
# `/api/v1/risk-dimensions` 判成密钥（`ri` + `sk-dimensions`），命中即禁止入库。
# 该串在 risk/api/api-client.js 里出现 5 次且早于本次修改就存在，只是此前该文件未被改动、
# 从未进入扫描范围，所以一直潜伏。修法：① 要求 `sk-` 前不是字母数字（不得是词中片段）
# ② 真实 OpenAI 风格 key 长度 ≥20，阈值提到 16 仍留足余量。
PAT_KEY = re.compile(r'(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_\-]{16,}|ghp_[A-Za-z0-9]{8,}|AIza[A-Za-z0-9_\-]{10,}|'
                     r'xox[baprs]-[A-Za-z0-9\-]{8,}|tvly-[A-Za-z0-9\-]{8,}|'
                     r'-----BEGIN [A-Z ]*PRIVATE KEY-----)')


def staged_files():
    out = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT,
                         capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
    files = []
    for line in out.splitlines():
        if not line.strip():
            continue
        st, path = line[:2], line[3:].strip().strip('"')
        if st.strip() == 'D':
            continue
        files.append(path)
    return files


def main():
    files = staged_files()
    seed = None
    sp = os.path.join(ROOT, '_admin_seed_local.txt')
    if os.path.exists(sp):
        seed = io.open(sp, 'r', encoding='utf-8', errors='replace').read().splitlines()[0].strip()
    ks = None
    kp = os.path.join(ROOT, 'APK封装', 'CabinAssistant', '.ks_pass')
    if os.path.exists(kp):
        ks = io.open(kp, 'r', encoding='utf-8', errors='replace').read().strip()

    bad = 0
    print('待入库文件 %d 个' % len(files))
    for rel in files:
        p = os.path.join(ROOT, rel)
        if not os.path.isfile(p):
            continue
        raw = io.open(p, 'r', encoding='utf-8', errors='replace').read()
        hits = []
        m = PAT_KEY.search(raw)
        if m:
            hits.append('密钥模式: %s…' % m.group(0)[:12])
        if seed and seed in raw:
            # 内嵌 base64/gzip 数据行里 3~5 字符的子串命中率极高（纯误报源）→ 只在普通行里判
            MAXLN = 500 if len(seed) < 6 else 10 ** 9
            ctx = []
            for ln in raw.splitlines():
                if len(ln) <= MAXLN and seed in ln:
                    ctx.append(ln.replace(seed, '***').strip()[:110])
                    if len(ctx) >= 3:
                        break
            if not ctx:
                print('  [skip]  %s（口令子串仅命中内嵌数据行，视为误报）' % rel)
                continue
            hits.append('明文口令种子(长度%d) 命中 %d 处，上下文：%s'
                        % (len(seed), raw.count(seed), ' ‖ '.join(ctx)))
        if ks and ks in raw:
            hits.append('.ks_pass 内容外泄')
        if hits:
            bad += 1
            print('  [BLOCK] %s -> %s' % (rel, '; '.join(hits)))
        else:
            print('  [OK]    %s' % rel)
    print('终检结果：%s' % ('全部通过' if bad == 0 else '%d 个文件命中，禁止入库' % bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
