# 春秋航空 · 广州分队客舱小助手

春秋航空广州分队一线工具融合平台

## 三种使用方式

### 1️⃣ 快速拆分版（线上首选，首屏秒开）

* 入口：`index.html`（约 18KB 外壳，首屏毫秒级）

* 十大模块**按需加载**：点击才下载对应系统，加载后缓存不重复请求

* 各模块独立文件：`qa.html` / `quiz.html` / `performance.html` / `beauty.html` / `medical.html` / `risk-lite.html` / `daily.html` / `manual.html` / `report.html` / `kb-admin.html`

### 2️⃣ 离线单文件版（完全独立，推荐离线使用）

* `客舱小助手（离线完整版）.html`（约 6MB，gzip 内嵌**十大模块**，双击即用，无任何网络依赖）

* `spring-assistant.html`（约 5.3MB，gzip 内嵌九模块，不含风险预警）

## 十大模块

* **💬 你问我答**：日常问题 / 乘务员手册 / 管理手册 / 服务规范 四库知识问答 + AI 自由问答与话术向导

* **📚 培训考核（刷题系统）**：题库 / 顺序练习 / 背题 / 错题重练 / 模拟考试 / 错题本 / 收藏 / 成就系统

* **📊 绩效管理**：汇总 / 绩效 / 飞行小时 / 销售 / 个人分析 / 班组排名 / 综合分析 / 档位追踪（含模拟预测警示）/ 智能预警 / 个人画像 / 备份恢复

* **💄 美妆话术**：产品库 / 智能话术匹配（品类·效果·品牌·数量）/ 精选话术套装 / 话术生成与衔接审查 / 肤质推荐 / 同品比拼 / AI 对话练习

* **🚑 医疗急救**：机上急救处置流程 / 常见病症 / 药品与设备 / 操作图鉴

* **⚠️ 风险预警（精简版）**：风险地图 / 指标监控 / 数据分析（离线单文件版未含）

* **❓ 日常问题**：高频业务问题速查

* **📕 手册奖惩**：手册要点 / 奖惩条款速查

* **🗂 事件报告**：事件报告流程速查

* **📇 库管理（管理员）**：上传新版手册 PDF → 自动解析章节 → 与四库匹配生成覆盖率地图与差异审核清单 → 确认后写入本机覆盖层（qa 问答自动生效）并可导出增量包；支持存量体检（裸缺口/弱覆盖/标签质量）与可选 AI 候选生成；**📦 数据包中心**可导入/导出/移除知识包·销售包·题库包（JSON 数据包覆盖内嵌基线，sales 包导入前自动合规检查）

## 数据包式内容更新

* 内容（知识库 / 美妆产品 / 题库）以 **JSON 数据包**形式覆盖内嵌基线，改内容无需重新发布整个 HTML

* 数据包类型：`kb`（知识库，可带 `lib` 限定单库）/ `sales`（美妆产品）/ `quiz`（题库）/ `notice`（预留）

* 格式：`{ "magic":"cabin-data-pack-v1", "packId":"sales-2026-09", "type":"sales", "title":"秋季机上销售包", "version":1, "issuedAt":"2026-08-29", "appliedUntil":"2026-12-31", "items":[{"op":"upsert"|"delete","key":"id","data":{...}}] }`

* 入口：库管理「📦 数据包」tab → 导入 JSON / 演示包；qa·美妆·考核导入后**自动生效**（跨模块 storage 事件）

* 数据包存本机 `packs_index` + `pack:{packId}`，**不随个人备份迁移**；旧版覆盖层（`kb_overlay_v1`）首次进入数据包中心自动迁移

* **在线发布（M2）**：App 启动时自动拉取 `packs/manifest.json`（<https://7528ardg.github.io/LEI/packs/manifest.json）比对版本，发现新包顶栏出现「📦> 新数据包」→ 一键安装自动生效；发布流程与格式见 `packs/README.md`

## 维护

* 十模块源码位于本目录 `qa.html` / `quiz.html` / `performance.html` / `beauty.html` / `medical.html` / `risk-lite.html` / `daily.html` / `manual.html` / `report.html` / `kb-admin.html`（改它们即改线上）

* `kb-admin.html` 为构建产物（含内联 pdf.js，约 3.2MB）：改 `kb-admin.template.html` 后运行 `python _build_kbadmin.py` 重新生成（四库数据自动从 qa.html 同步注入）

* 离线单文件版由构建脚本生成：`python _build_4in1.py`（十模块完整版）/ `python _gzip_build.py`（九模块版）

* 数据包引擎单一来源 `docs/_packs_engine.js`：改它后必须重跑 `python _sync_packs.py`（自动注入 qa/beauty/quiz/kb-admin.template.html，CI 用 `--check`），再跑 `python _build_kbadmin.py` + `_gzip_build.py` + `_build_4in1.py`

* 一键工具：`python _build_all.py`（默认 构建+全量回归）；`build` / `verify` 单独执行；数据包发布见 `packs/README.md` 与 `_build_packs_release.py`

* `_check_js.py`：全量语法校验（模块源 + 三外壳/产物）

* 更新后浏览器若显示旧版，请强制刷新（Ctrl+F5 / Cmd+Shift+R）

