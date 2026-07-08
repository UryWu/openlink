# Changelog

本项目的所有重要变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [1.3.0] - 2026-07-08

### Added
- **扩展 ⚙️ 弹窗添加"工具命令"标签页 + 工具输入面板**（`extension/src/content/index.ts`）：第二个面板内含文本框可输入或粘贴 `<tool>` XML，按 [执行] 直接 POST `/exec`，结果回显在下方。
- **工具结果区"自动插入到 AI 对话框"勾选框**（`id="openlink-tool-auto-insert"`）：持久化到 `chrome.storage.local`，与已勾选同步样式默认蓝色。
- **工具命令面板新增"最新ai回复"按钮**（`id="openlink-tool-fetch-latest"`）：注入拦截偶尔漏抓时（DeepSeek 偶发响应结构变更）兜底，从 DOM 重新提取最近一条 AI 助手消息里的 `<tool>` XML，按站点的 `responseSelector` 抓取。
- **工具命令输入框内容持久化**（`TOOL_INPUT_KEY = 'openlink-tool-input'`）：关闭弹窗再打开仍保留执行完的输入，仅 [清空] 按钮同时清 storage。
- **执行处理器支持多条 `<tool>` 调用**：`text.matchAll(/.../g)` + `Array.from` 一次抓所有 XML 段，逐条 POST `/exec`，结果按顺序用 `---` 拼接显示。
- **DeepSeek `responseSelector`** 加入 `getSiteConfig`：`.ds-markdown.ds-assistant-message-main-content`，给"最新ai回复"兜底按钮提供 DOM 锚点。
- **⚙️ 弹窗支持 8 方向 resize + 尺寸持久化**（`SETTINGS_SIZE_KEY = 'openlink-settings-dialog-size'`）：四角 + 四边各一个 handle，鼠标拖拽实时改 `width/height/left/top`，mouseup 时落盘。

### Changed
- **工具命令面板按钮列宽 50px → 60px**：容纳"最新ai回复"四字，工具列 + 结果列两边的"执行 / 清空 / 最新ai回复 / 插入 / 复制"按钮统一。
- **"最新ai回复"的提示改用 `showToast` 浮窗**：原来会写入结果框（跟 [执行] 重复占用空间），现在走右下角瞬时提示，3 秒自动消失。
- **"自动插入到 AI 对话框"复选框上移到结果区外**：上一版嵌在结果 wrap 里，要执行命令后才出现；现在常驻，弹窗初始就可见。
- **"插入"按钮改为蓝色**：和"执行"按钮同色（`#1677ff`），主从关系更清晰；之前是灰色边框容易被忽视。

### Fixed
- **后端工具错误响应被 `_REMINDER` 覆盖**（`backend/app/executor/executor.py`）：`output = "" + reminder` 是 truthy 字符串，让扩展端的 `result.output || result.error || ...` fallback 链直接返回 `[系统提示]...`，错误信息全丢。改为只在 `status != "error"` 时追加 reminder。
- **`read_file` 文件不存在时返回明确错误信息**（`backend/app/tools/read_file.py`）：拆分 `OSError` 为 `FileNotFoundError` / `IsADirectoryError` / `PermissionError` / 兜底 `OSError`，每条都带原始路径 + sandbox 解析后的绝对路径，让 AI 能自助纠错。
- **后端 `root_dir` 双重 backend 路径拼接**（`backend/app/main.py`）：lifespan 里 cwd 默认 `os.getcwd()` 时算成 backend 目录，用户传 `"backend/app/..."` 会拼成 `<backend>/backend/app/...`。改为 `os.path.abspath(os.path.join(os.getcwd(), ".."))` 显式 normalize 到仓库根。
- **`main.py` docstring 去掉过时的 Go 路径引用**：之前是 `"""FastAPI application entry point — mirrors cmd/server/main.go."""`，Go 实现早已清掉，留着只会在搜索时产生误导。
- **`build_extension.ps1` 自动关闭等待时间 3 秒 → 2 秒**：构建脚本结尾的 `Start-Sleep` 缩短，避免正常完成时多等 1 秒。

### Documentation
- **`docs/tool-error-response.md`**（248 行）：commit `3564945` 的开发复盘，三层数据模型（`ToolResult` → `ToolResponse` → JS `||` 链）逐层衰减表 + 两文件 diff 解释 + 端到端 curl 验证 + 5 条可推广教训。
- **`docs/sites/deepseek-adapt.md`**：DeepSeek 站点适配全流程文档，含 XHR/SSE/正则修复、关键死循环 bug 复盘、调试开关约定、给后续适配者的 checklist。

## [1.2.0] - 2026-07-07

### Added
- **扩展 DeepSeek 适配** (`extension/src/content/index.ts`, `injected/index.ts`)：
  `chat.deepseek.com` 加入 `getSiteConfig`，使用纯 `<textarea>` + BEM 语义类名（`.ds-button--primary--filled--circle`）。
  `fillMethod: 'value'`，`useObserver: false`，工具调用检测走 `injected.js` 的
  fetch / EventSource / WebSocket / XHR 四层拦截，新增的 EventSource 与 WebSocket
  是为以后类似站点做的兜底。
- **扩展 ⚙️ 弹窗新增"自动执行工具调用"勾选框**：控制检测到 `<tool>` 后是直接 POST
  `/exec` 还是先弹 inline 审批卡片让用户手动确认。
- **扩展 ⚙️ 弹窗新增"自动提交"勾选框**：取消勾选后，工具执行结果只填进 AI
  输入框、不自动点发送，需用户手动回车提交。绑定已有的 `chrome.storage.local.autoSend` 字段。
- **扩展 ⚙️ 弹窗新增自动提交延迟区间** `x` / `y` 输入：每次触发时随机选
  `[x, y]` 秒后自动提交（之前仅以默认值硬编码）。可选范围 0–60 秒。
- **扩展 autoExecute 关闭时的审批卡片**（`showToolApprovalPopup`）：inline 卡片，
  插到对应 AI 消息的工具栏下方（非全屏遮罩，不影响别处点击），展示工具名 +
  参数 JSON，按钮 "执行" / "忽略"。
- **扩展 ⚙️ 弹窗保存后不再自动触发 init**：之前保存 URL/Token 会自动
  `sendInitPrompt()`，现在只在用户手动点 🔗 时才初始化。
- **扩展浮动按钮样式统一**：⚙️ 按钮改为和 🔗 初始化同样的蓝胶囊 + 阴影。
- **扩展 ⚙️ 弹窗底部新增 [初始化] 按钮**：点 [初始化] = 先调 `saveSettings()`
  共享函数保存设置，校验通过后 `close()` + `sendInitPrompt()`，一次完成
  "配置 + 初始化"。校验失败保留弹窗让用户修正。
- **扩展移除浮动 🔗 初始化按钮**：功能已整合进 ⚙️ 弹窗的 [初始化] 按钮，
  浮动区只剩 ⚙️ 一个入口，简化界面。
- **文档 `docs/sites/deepseek-adapt.md`**：DeepSeek 适配全流程文档，含
  XHR/SSE/正则修复、关键死循环 bug 复盘、调试开关约定、给后续适配者的 checklist。
- **文档 `docs/version-bumping.md`**：版本升级流程独立文档，从
  `scripts/README.md` 抽出，含 SemVer 判断、lockfile 重新生成原理、典型发布流程。
- **框架 `skills/skill-creator/`**：技能创建框架（模板 + 验证脚本 + 打包工具）。

### Fixed
- **关键 bug `extension/src/injected/index.ts`**：`RE_TOOL` 正则漏 `g` flag，
  导致 `while ((re.exec(text)) !== null)` 配合 dedup `processed.has()` 形成**死循环**——
  主线程被锁死、整个标签页卡死。补回 `g` flag 让 `exec` 推进 `lastIndex`。
- **扩展 `autoExecute` 设置在 `injected.js` 路径失效**：原本只声明在
  `startDOMObserver` 闭包内，DeepSeek 走 injected → message → executeToolCall
  路径完全看不到。提到模块顶层，删除重复声明，`executeToolCall` 入口加守门。
- **扩展 `autoExecute` 默认值改回 `true`**：配合上述 fix，避免老用户刷新后工具
  不再自动执行的体验倒退。
- **后端 `backend/uv.lock` 中 `pathspec` 版本**：PyPI 上无 `pathspec 1.2.0`，
  `uv sync` 报 404。改用 `uv lock --upgrade-package openlink` 让 uv 重新解析
  到合法版本（pathspec 仍是 `1.1.1`）。
- **`scripts/bump_version.sh` 不再 sed lockfile**：旧逻辑 `sed s/1.1.1/1.2.0/g`
  会把 uv.lock / package-lock.json 里的传递依赖版本（如 `pathspec`、
  各种 npm 包）一起改坏。新逻辑只动源文件，lockfile 由 `uv lock` / `npm install`
  重新生成。`.ps1` 版同步修。verify 步骤也排除 lockfile 假阳性。
- **扩展 ⚙️ 弹窗 `delayMin/Max` 校验**：值必须 ≥ 0、≤ 60、且 `max ≥ min`，否则
  弹 alert 中断保存。

### Changed
- **解析器 `parseXmlToolCall`**：入口先做 `\"` → `"` 归一化，使原始 SSE body
  （JSON 转义引号）也能正确解析。
- **注入脚本 `reassembleSSEFragments`**：把 DeepSeek SSE 风格分片（多条
  `data: {"v":"..."}` 行）按顺序拼回连续文本，并把初始 state 的
  `response.fragments[].content` 也算上（首字符 `<` 在这里，否则工具文本被砍头）。
- **扩展 autoSend 字段**：之前只在 `fillAndSend` 里读、没 UI 入口写；现在通过
  ⚙️ 弹窗的 checkbox 写。
- **`scripts/bump_version.sh` 同步锁文件命令**：`uv sync` → `uv lock`，让 uv
  在改完 pyproject.toml 后重新生成 lockfile 而非按旧 lockfile 安装。
- **扩展 ⚙️ 弹窗按钮布局**：`[取消]` 移到布局最左边（容器改
  `justify-content: space-between`），`[保存] [初始化]` 包成右侧子组。
- **提取 `saveSettings()` 共享函数**：从原 [保存] handler 抽出共享给 [初始化]，
  返回 `Promise<boolean>`。`chrome.storage.local.set` 由 callback 改成
  `await Promise` 以配合 async 流程。
- **扩展 [初始化] 按钮去掉 🔗 emoji**：文字简化为 `初始化`。

### Removed
- **200ms 抖动逻辑**：用户反馈"无意义"，从延迟公式里移除，回归 `random(x, y)`。
- **工具成功后自动追加 init**：用户反馈 init prompt 太长（257 行）注入对话流
  太噪，撤销。init 仍只在手动点 🔗 时触发。
- **命令行 CLI 入口 `[project.scripts] openlink`**：之前注册在 pyproject.toml
  但 `run()` 没把参数转发给 uvicorn，CLI 参数被静默丢弃。脚本已删除。

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