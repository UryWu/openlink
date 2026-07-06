# Changelog

本项目的所有重要变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [1.1.1] - 2026-07-06

### Fixed
- **executor**: 修复 `_build_init_prompt()` 路径查找错误。自迁移至 FastAPI 以来，
  该函数候选路径最多只遍历两级到 `backend/prompts/`，而仓库实际布局把
  `init_prompt.txt` 放在仓库根 `prompts/` 下，导致每次初始化都退化到内置的英文
  fallback 文本。改为三级遍历，将根目录候选置首，并保留旧的两级与同级候选以兼容
  未来重打包布局。
- **executor**: 在 fallback 注释中标注 "操作员错配部署" 语义，便于排错。

### Changed
- 项目版本从 `1.0.0` 统一升级到 `1.1.1`，覆盖 8 个源点（后端、前端、扩展、FastAPI
  app、HealthResponse 默认值、`/health` 直接返回值、`backend/VERSION`、`uv.lock`）。
  `/health` 实时返回 `{"version":"1.1.1"}` 已端到端验证。

## [1.1.0] - 2026-07-06

### Added
- **后端**: Python FastAPI 后端完整实现 12 个工具
  （exec_cmd / list_dir / read_file / write_file / edit / glob / grep /
   web_fetch / question / skill / todo_write / invalid），替换原 Go 服务。
- **前端**: Vue 3 + Pinia 管理面板（Dashboard / Connection / ToolConsole /
  FileBrowser / SkillsView / PromptViewer / Settings），由 FastAPI
  在 `/app/` 提供静态文件。
- **工具**: 端口释放脚本 `kill_backend_server_via_port_39527.bat`，一键释放
  端口。
- **扩展**: 三尺寸 PNG 图标（16 / 48 / 128）。
- **启动器**: `start.bat` 一键启动脚本。
- **技能**: 项目级 `skills/` 目录加载支持。

### Removed
- 原 Go 后端（`cmd/server/`、`internal/`、`go.mod`、`goreleaser.yml`）。
- Chrome 扩展 React popup 与相关依赖。

### Fixed
- `/prompt` 路径查找逻辑，统一读根目录 `prompts/init_prompt.txt`。

## 早于 v1.1.0

项目最初以 Go 实现（`cmd/server/` + React 扩展 popup）。
后续架构演进请参考 git 历史：`ae70580` 之前的提交为 Go 时代；
`aea2ef1` 起的提交对应 FastAPI + Vue 3 迁移。