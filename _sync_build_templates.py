# -*- coding: utf-8 -*-
"""同步数据包弹窗改进到构建脚本模板（_gzip_build.py / _build_4in1.py），幂等"""
import io
import os

FILES = [r"c:\Users\Admin\Desktop\融合版\_gzip_build.py", r"c:\Users\Admin\Desktop\融合版\_build_4in1.py"]

# A. .modal-x 样式
old_a = ".modal-card h3{margin:0 0 6px;font-size:1.05rem;color:var(--text);}"
new_a = (".modal-card h3{margin:0 0 6px;font-size:1.05rem;color:var(--text);}"
         "\n.modal-x{width:28px;height:28px;border-radius:8px;border:none;background:var(--primary-mist);color:var(--text2);font-size:.9rem;line-height:1;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;transition:all .2s;font-family:var(--font-sans);margin-left:8px}"
         "\n.modal-x:hover{background:var(--danger-soft);color:var(--danger)}")

# B. packsModal h3 加 ✕
old_b = "<h3>📦 发现可用数据包更新</h3>"
new_b = "<h3 style=\"display:flex;align-items:center;justify-content:space-between;gap:8px\">📦 发现可用数据包更新<button class=\"modal-x\" onclick=\"closeModalId('packsModal')\" title=\"关闭\" aria-label=\"关闭\">✕</button></h3>"

# C. closeModalId + Escape
old_c = "function closePacksModal(){ document.getElementById('packsModal').classList.remove('show'); }"
new_c = ("function closePacksModal(){ document.getElementById('packsModal').classList.remove('show'); }\n"
         "function closeModalId(id){ const m=document.getElementById(id); if(m) m.classList.remove('show'); }\n"
         "document.addEventListener('keydown',function(e){ if(e.key==='Escape'){ ['packsModal','backupModal','profileModal'].forEach(function(id){ closeModalId(id); }); } });")

# D. showPacksBadge 加 toast
old_d = """function showPacksBadge(ready){
  const b = document.getElementById('packsBadge');
  if(!b) return;
  b.style.display = '';
  const span = b.querySelector('span');
  if(span) span.textContent = '新数据包(' + ready.length + ')';
}"""
new_d = """function showPacksBadge(ready){
  const b = document.getElementById('packsBadge');
  if(!b) return;
  b.style.display = '';
  const span = b.querySelector('span');
  if(span) span.textContent = '新数据包(' + ready.length + ')';
  try{ toast('发现 ' + ready.length + ' 个新数据包，点击顶栏 📦 可查看安装'); }catch(e){}
}"""

for path in FILES:
    with io.open(path, "r", encoding="utf-8") as f:
        src = f.read()
    n = 0
    missed = []
    for old, new in [(old_a, new_a), (old_b, new_b), (old_c, new_c), (old_d, new_d)]:
        if old in src:
            src = src.replace(old, new, 1)
            n += 1
        else:
            missed.append(old[:50])
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(src)
    os.replace(tmp, path)
    print(path.split("\\")[-1], "| applied:", n, "| missed:", missed)
