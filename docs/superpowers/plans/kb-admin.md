# kb-admin（手册知识库管理板块）Implementation Plan

> Status: APPROVED
> Source: docs/superpowers/specs/2026-08-28-kb-admin-design.md
> Mode: default（完整 Planner → Architect → Critic loop）
> Iterations: 1 / 3
> Author: 用户（春秋航空乘务员 · 管理员）
> Last updated: 2026-08-28

## Requirements summary

为知识库（CCM/MGM/SVC/Daily 四库共 489 条）建设管理员维护工作台 kb-admin.html（第 10 个模块）：上传新版手册 PDF → pdf.js 提取文本 → 章节树解析 → 与四库条目三路加权匹配 → 覆盖率地图 + 差异审核清单 → 确认后写入本机覆盖层并可导出增量更新包；提供存量「体检」扫描（裸缺口章节 / 弱覆盖标注 / 标签质量问题）；可选 SpringAI 生成候选条目。qa.html 启动时静默合并覆盖层，乘务员端即时生效。全部离线可用。

## Acceptance criteria

* AC-1 外壳三处（index.html / \_build\_4in1.py / \_gzip\_build.py）均有「📇 库管理」页签、`kbadmin` 模块映射、EMBED\_CSS 与 iframe 容器；切换正常。

* AC-2 kb-admin.html 自包含 pdf.js（worker 以 Blob URL 内联），离线打开不请求网络。

* AC-3 章节树解析：对含编号 `3.1.2.1` 的文本，正确输出 {全编号, 标题, 起始页}。

* AC-4 覆盖率地图：mock 数据下 已覆盖/新增/变更/缺口 判定正确（src 前缀 + 标题关键词 + t 标签三路）。

* AC-5 差异审核：确认后写入 `localStorage['kb_overlay_v1']`（条目带 `_op:'add'|'mod'`）；增量包导出/导入带 magic+version 校验；JS 片段可复制。

* AC-6 qa.html 合并：add 追加、mod 按 src 替换、损坏数据静默忽略并报日志；合并后可检索到新条目。

* AC-7 存量体检输出：裸缺口章节 / 弱覆盖标注（"以手册原文为准"类）/ 标签质量问题，可导出 Markdown。

* AC-8 AI 候选：配置 `spring_ai_cfg` 时生成候选标「AI 候选」；未配置或失败自动回退，不崩溃。

* AC-9 重新构建两个单文件版，语法校验通过，9 个既有模块回归不受影响。

## RALPLAN-DR

### Principles

* 跟随 spec，不扩 Out-of-scope（不做 PDF 渲染 / 在线编辑 / 全员管理入口）。

* 最小代码：qa.html 只插入自包含 IIFE 合并段（≤30 行），不重构 kbSearch/SRC\_CFG。

* 外科手术式：只加新文件 + 三处外壳最小注入点 + qa.html 一段合并逻辑，不改任何既有模块行为。

* 离线自洽：kb-admin.html 自包含 pdf.js，worker Blob URL 内联；运行失败有明确人话提示。

* 可验证：解析/匹配/合并/体检均为纯函数，可被 node mock 驱动测试。

### Decision drivers

* 维护复杂度（三处外壳一致性的历史教训 → 用 check 断言 + 单一手改源）。

* 离线体积（自包含 kb-admin.html，构建脚本零额外内联逻辑）。

* 稳健性（qa.html 是乘务员生产入口，合并必须 fail-safe + storage 事件联动）。

* 演示效果（覆盖率地图 + 体检报告作为立项素材）。

### Viable options

**Option A（favored）**: 独立自包含 kb-admin.html（pdf.js 内联进模块文件）

* 实现思路：kb-admin.html 一个文件包含 pdf.js 源码内联（开发/上线同一文件），worker 用 Blob URL；构建脚本仅加模块映射与页签。

* 改动文件：`kb-admin.html`（新，\~1.5MB 自包含）、`qa.html:2031` 前插合并段、`index.html`（页签/MOD\_SRC/EMBED\_CSS/wrap/theme）、`_build_4in1.py`、`_gzip_build.py`、`libs/`（pdf.js 素材，构建后并入 kb-admin.html）、`_check_js.py` 可选加文件。

* Pros：离线保证天然成立；构建脚本改动最小；符合 9 个既有模块"单文件自包含"风格。

* Cons：kb-admin.html 源文件大（\~1.5MB），编辑工具打开较缓；与 spec 3.1 的"构建时内联"写法不同（本 plan 用自包含达成同一离线目标，更简单）。

**Option B**: 模块文件小、构建脚本内联 pdf.js（inline\_risk\_deps 同款）

* Pros：源文件小。

* Cons：构建脚本多一段内联逻辑与占位符，多一处失效面（历史教训：占位符曾引发 SYNTAX\_ERR）；开发与构建产物不一致，排障难。

* Rejected rationale：spec 目标只是"离线可用"，自包含更简单可靠；B 的复杂化不值得。

**Option C**: 复用 performance.html 的权限/备份基建

* Pros：复用认证。

* Cons：performance.html 已 4MB，模块耦合爆炸；spec §2 已定方案 A；违背最小代码。

* Rejected rationale：spec 决策记录明确独立模块，且绩效模块是乘务员生产入口，混入管理功能回归风险高。

## Implementation steps

1. 下载 pdfjs-dist\@3.11.174 legacy UMD（`libs/pdf.js` + `libs/pdf.worker.js`）— 验证 `window.pdfjsLib` 结构与文件可用性。
2. 新建 `kb-admin.html`（自包含：

   * `<script>` 内联 pdf.js 与 pdf.worker.js 源码；`PDFJS_WORKER_SRC` 常量 + `GlobalWorkerOptions.workerSrc = URL.createObjectURL(new Blob([...]))`；`getDocument` 失败降级 `{disableWorker:true}`，再失败给明确报错。

   * 纯函数：`extractPdfText`（逐页 getTextContent + ===PAGE N===）、`parseSections(text)`（`/^\s*(\d+(?:\.\d+)+)\s+(.{2,30})$/m` 层级）、`matchLib(entries, sections)`（三路加权 + 覆盖状态）、`scanHealth(entries)`、`overlay*`（读写/导出/导入/JS片段）。

   * 内嵌四库数据源快照：将 qa.html 中 `KB / KB_CCM_RAW / KB_MGM_RAW / KB_SVC_RAW` 四个数组原样粘贴为 `BASE_LIBS`，供匹配/体检用（与 qa 同步维护的约定：构建时由脚本自动维持一致，见 step 4）。

   * UI：自带顶栏 + Tab（上传解析/覆盖率地图/差异审核/体检报告/覆盖层管理）+ AI 候选开关 + 内嵌隐藏标记（`.embed` 时隐藏顶栏）。
3. `qa.html:2031`（`/* ===== 四库来源路由` 注释行前）插入 IIFE 合并段：读 `localStorage['kb_overlay_v1']` → 校验 magic/version → add append、mod 按 src 替换 → 任一步失败 `console.warn` 并静默跳过；另挂 `storage` 事件监听实现动态合并（解决外壳 iframe 缓存后不重载问题）。
4. 三处外壳注入（一致性依赖 `__KBADMIN_TAB__` 断言，见 Verification）：

   * `index.html`：`.module-tabs` 末尾加页签按钮（report 之后）；`MOD_SRC` 加 `kbadmin:'kb-admin.html'`；`EMBED_CSS` 加 `kbadmin` 条目；`main.sys-area` 加 `wrap-kbadmin` iframe；`applyTheme` 数组加 `'kbadmin'`。

   * `_build_4in1.py`：SOURCES 加 `kbadmin:u'kb-admin.html'`；TEMPLATE 内同 index 四处改动。

   * `_gzip_build.py`：同上（无 risk 模块）。
5. 同步源文件契约：在 `_sync_kb.py` 或构建脚本中加入「从 qa.html 提取四库数组 → 与 docs/_kb_\*.js 比对 → 与 kb-admin.html 的 BASE\_LIBS 比对」的一致性命中断言（qa 内嵌四库 == docs 源 == kb-admin BASE\_LIBS），防止三处漂移。
6. 重新构建：`python _build_4in1.py` + `python _gzip_build.py`；`python _check_js.py` + node --check 覆盖三个外壳与 kb-admin.html；node mock 跑解析/覆盖/合并/体检/AI 降级测试；体积确认。

## Workspace setup

* 实施前运行 `git status --short` 与 `git branch --show-current`。

* 当前工作区含未提交的「全局备份」功能改动。本 plan 是纯增量（新文件 + 最小注入点），在现有工作区上直接实施；如果用户希望先保护基线，可先提交备份功能（用户已表示"先不提交"，本 plan 尊重该决定，仅在实施完成后提醒）。

* 当前分支若为 main/master，建议后在 git 操作前再确认 worktree 策略（本次不涉及破坏性 git 操作）。

## Risks & mitigations

| Risk                                       | Mitigation                                                                                |
| ------------------------------------------ | ----------------------------------------------------------------------------------------- |
| 三处外壳页签/映射/EMBED\_CSS 漂移                    | Verification 用 `Microsoft.PowerShell`/node 断言「kbadmin」字符串在每个外壳出现次数一致；build 后 node --check |
| pdf.js worker Blob URL 在旧 iOS/WebView 创建失败 | `getDocument` 先 worker，异常降级 `{disableWorker:true}`（pdf.js legacy 支持主线程解码），再失败显示引导文案；不白屏   |
| qa.html 合并段与 iframe 缓存不同步（先开 qa 后更新再切回不生效） | storage 事件监听动态合并 + kb-admin 更新成功 toast 提示「可立即生效」                                          |
| 覆盖层损坏/被篡改                                  | magic+version 校验，失败 `console.warn` + 静默忽略，绝不影响既有检索                                        |
| glm-4-flash 输出非严格 JSON（历史教训）               | 正则提取 JSON + 解析失败标「生成失败」不阻塞审核流；few-shot + temperature≤1.0                                  |
| kb-admin.html 自包含体积极大影响编辑/构建               | 只读量大、改动点集中，构建照常 gzip；`_check_js.py` 纳入                                                    |
| 四库数据三处漂移（qa/docs/kb-admin BASE\_LIBS）      | step 5 一致性命中断言；实施时仅 source of truth 为 qa.html，其余由脚本/手工同步并断言                               |

## Verification steps

* AC-1：node 脚本断言三外壳均含 `kbadmin` 页签文本、`MOD_SRC`/`MODULES` 映射、`EMBED_CSS.kbadmin`、wrap-kbadmin。

* AC-3：node mock 驱动 kb-admin.html 内 `parseSections`，断言含 `3.1.2.1` 的样例输出 3 条结构正确。

* AC-4：mock 迷你四库 + 迷你手册 → `matchLib` 输出分类与期望一致。

* AC-5：mock localStorage → overlay 写入/导出/导入回环（沿用备份测试手法）。

* AC-6：node 构造 KB\_CCM\_RAW 快照 + overlay mock → 合并后新条目可检索、mod 替换生效、损坏 payload 被忽略。

* AC-7：对现有四库跑 `scanHealth`，报告条目数、裸缺口章节、弱覆盖标注计数，与 spec §9 期望一致。

* AC-8：mock fetch 成功/失败 → 候选生成 / 降级两态。

* AC-9：`python _check_js.py` + node --check（4 文件）+ 构建后体积 < 7MB；9 模块 EMBED 回归由 `_check_js.py` 保障语法，行为回归列出给用户手动抽查项。

## ADR

* **Decision**: 独立自包含 kb-admin.html（第 10 模块），pdf.js 内联，覆盖层 + 增量包双通道落库，qa.html 启动/事件双合并。

* **Drivers**: spec §2 用户决策（管理员工具/PDF/规则+AI/覆盖层模式/方案 A）；最小代码；离线自洽；三处外壳一致性由断言兜底。

* **Alternatives considered**: A（chosen）；B 构建内联（rejected —— 失效面多、历史有 SYNTAX\_ERR 教训）；C 挂 performance（rejected —— 耦合爆炸、违背 spec）。

* **Why chosen**: 自包含最贴近既有 9 模块架构，构建零内联逻辑，离线保证最稳；三处一致性问题用断言而非靠人肉同步。

* **Consequences**: kb-admin.html 源文件较大（\~1.5MB）；BASE\_LIBS 与 qa 内嵌四库需保持同步（step5 断言管控）；覆盖层为工作态、源文件为发布态的双轨带来"更新需回写源文件"的手工步骤（增量包导出已闭环）。

* **Follow-ups**: pdf.js 版本升级评估；覆盖层自动回写 docs/_kb_\*.js 的脚本化；增量包自动发布 Pages（均 out of scope）。

## Review trail

* Planner draft v1: 最小方案 A（自包含模块）3 步拆分。

* Architect challenge v1: steelman 针对 worker 降级与 qa 缓存不同步；tension 三处：覆盖面 vs 维护成本、解析完整 vs 离线稳定、即时生效 vs 数据正统；synthesis 维持 A + worker 降级 + storage 事件。

* Critic verdict v1: REVISE — 发现 qa iframe 缓存导致覆盖层不生效的竞态、glm JSON 解析风险、三处页签漂移未设防。

* Planner draft v2: 采纳三点 → qa 加 storage 事件 + toast；AI JSON 正则兜底；Verification 加三外壳断言。

* Architect challenge v2: 确认无新增矛盾。

* Critic verdict v2: APPROVED（改进全部合入；reservation 均已转 mitigation/verification）。

* Final iterations: 1 / 3

