# 📦 数据包发布指南（M2 在线更新 + M3 发布管线）

本目录随 GitHub Pages 上线，作为团队的**数据包发布源**。App（拆分版 / 单文件版）启动时
检查 `manifest.json`，发现新包会在顶栏显示「📦 新数据包」，一键安装后 qa·美妆·考核自动生效。

## 发布流程（推荐用 M3 管线，一分钟）

1. 在库管理「📦 数据包中心」生成 / 导出数据包 JSON（sales 包导出前自动合规检查）
2. 把 JSON 文件放进 `packs/incoming/`（可同时放多个）
3. 运行发布管线：

```bash
python _build_packs_release.py            # 扫描 incoming 全部发布（合规检查 + sha256 + manifest 自动合并）
python _build_packs_release.py --check    # 预检（不落盘），CI 可用
```

1. `git add packs && git commit && git push`（部署到 GitHub Pages）→ 全员在线自动提示更新

管线会自动完成：协议校验 → sales 合规拦截 → sha256 计算 → 包落盘 `packs/packs/<packId>.json` → 合并更新 `packs/manifest.json`（同 packId 高版本才覆盖，版本号低于线上则跳过）。

## 手工方式（不推荐，仅说明结构）

手工发布需自己在 `manifest.json` 里登记：

```json
{
  "packId": "sales-2026-09",      // 全局唯一；同 id 发更高 version 即全员升级
  "title": "秋季机上销售包",        // 顶栏弹窗显示的名称
  "type": "sales",                 // kb | sales | quiz | notice
  "version": 2,                    // 整数，高于用户本机版本才提示更新
  "updatedAt": "2026-08-29",       // 展示用
  "url": "packs/packs/sales-2026-09.json",
  "sha256": ""                     // 管线自动填；手工可留空（客户端跳过校验）
}
```

## 说明

* **差异规则**：用户本机未装该 packId → 提示新包；已装但清单版本号更高 → 提示升级；版本相同 → 不打扰

* **完整性**：https + sha256（管线自动写入）双重保障；manifest 或包下载失败一律静默（离线/404 不弹错）

* **合规**：管线对 `sales` 包自动跑 10 项违禁词检查，不通过则不发布；词表与 beauty/库管理保持一致

* **回滚**：用户可在库管理「📦 数据包中心」移除任意包恢复内嵌基线；删除 `packs/` 下对应包并重跑管线（或手动移除 manifest 条目）即停止推送

* **URL 覆盖**：如需自建发布源，可在 localStorage 写入 `packs_manifest_url` 指向自己的 manifest（例如内网地址）

* 发布前可先跑 `python _build_packs_release.py --check` 预览

