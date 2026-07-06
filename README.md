# OpenLink

> ⚠️ **学习研究项目，非生产用途**
>
> 本项目是作者为**研究底层 Agent 工作原理**而创建的个人学习项目，代码结构和实现均以探索为目的，**不适合用于生产环境**。
>
> **目前实测效果并不理想**：网页版 AI 对工具调用的支持参差不齐，稳定性和准确性均有较大局限，距离实用仍有差距。
>
> OpenLink 通过浏览器扩展模拟用户操作来驱动网页 AI，**并不是一个 API 接口**，不适合作为日常 API 调用使用。请合理使用，勿滥用。

让网页版 AI（Gemini、AI Studio）直接访问你的本地文件系统和执行命令。

## 三组件架构

项目由三个独立组件组成，请勿混淆：

```
┌─────────────────────────────────────────────────────────┐
│  1. Chrome 扩展 (extension/)                             │
│     拦截 AI 网页输出的 <tool> 标签，转发给后端           │
│     运行在浏览器中，自动工作 —— 用户看不到它             │
│     必须手动加载到 Chrome                                 │
├─────────────────────────────────────────────────────────┤
│  2. FastAPI 后端 (backend/)                              │
│     接收扩展的请求，执行文件操作和命令                    │
│     运行在本地终端，localhost:39527                       │
├─────────────────────────────────────────────────────────┤
│  3. Vue 管理面板 (frontend/)                              │
│     在浏览器中管理服务器的 Web 页面                       │
│     打开 http://127.0.0.1:39527/app/ 使用               │
│     可选 —— 不影响核心功能                                │
└─────────────────────────────────────────────────────────┘
```

| 组件 | 目录 | 做什么 | 必须吗 | 怎么启动 |
|------|------|--------|--------|----------|
| **Chrome 扩展** | `extension/` | 拦截 AI 网页的工具调用，转发给后端 | ✅ 必须 | 手动加载到 Chrome |
| **FastAPI 后端** | `backend/` | 执行工具、文件操作、沙盒隔离 | ✅ 必须 | `start.bat` 或命令行 |
| **Vue 管理面板** | `frontend/` | 浏览器管理界面（文件浏览、工具控制台等） | ❌ 可选 | 后端自动 Serve 在 `/app/` |

**关键区别**：

- **Chrome 扩展 ≠ 管理面板**。扩展是自动在 AI 网页里工作的，不需要你打开任何页面。管理面板是你主动访问的一个网页，用来查看服务器状态、手动执行工具等。
- **扩展还在**，迁移后保留完整功能（content script / injected script / background script），只是去掉了原来用 React 写的 popup 弹窗。扩展对用户是透明的。

## 工作原理

```
AI 网页 → 输出 <tool> 指令 → Chrome 扩展拦截 → 本地 FastAPI 服务执行 → 结果返回 AI
```

## 快速安装

### 第一步：安装本地服务

**要求**：Python >= 3.12，[uv](https://docs.astral.sh/uv/) 包管理器。

```bash
git clone https://github.com/betgar/openlink.git
cd openlink/backend

# 安装依赖
uv sync

# 启动服务器（当前目录为工作区）
uv run openlink -dir /your/workspace -port 39527

# 或直接通过 Python 启动
uv run python -m app.main -dir /your/workspace
```

服务默认监听 `http://127.0.0.1:39527`。首次运行会自动在 `~/.openlink/settings.json` 中生成认证 token。

一键启动（Windows）：双击仓库根目录的 `start.bat`。

### 第二步：安装 Chrome 扩展

```bash
cd extension
npm install
npm run build
```

1. 打开 Chrome，访问 `chrome://extensions/`
2. 开启右上角「开发者模式」
3. 点击「加载已解压的扩展程序」，选择 `extension/dist/` 目录

### 第三步：开始使用

访问 [Gemini](https://gemini.google.com) 或 [AI Studio](https://aistudio.google.com)，点击页面右下角的「🔗 初始化」按钮。

如果提示「请先配置 API 地址」，点 ⚙️ 齿轮：
- API 地址：`http://127.0.0.1:39527`
- Token：从 `~/.openlink/settings.json` 复制 `token` 字段

### （可选）管理面板

```bash
cd frontend
npm install
npm run dev       # 开发模式（Vite 热更新）
npm run build     # 生产构建，由 FastAPI 自动 Serve 于 /app/
```

构建后访问 `http://127.0.0.1:39527/app/` 打开管理面板。

---

## 推荐平台

> **目前测试效果最佳的平台是 [Google AI Studio](https://aistudio.google.com)**

## 支持的 AI 平台

| 平台 | fillMethod | useObserver | 备注 |
|------|-----------|-------------|------|
| Google AI Studio | value | true | 推荐，原生支持系统提示词 |
| Google Gemini | execCommand | true | |
| ChatGPT | prosemirror | true | |
| 通义千问 | value | true | |
| DeepSeek | paste | false | |
| Kimi | execCommand | false | |
| Mistral | execCommand | false | |
| Perplexity | execCommand | false | |
| Grok | value | false | |
| GitHub Copilot | value | false | |
| z.ai | value | false | |
| Arena.ai | value | true | |
| OpenRouter | value | false | |
| t3.chat | value | false | |

---

## 可用工具

| 工具 | 说明 |
|------|------|
| `exec_cmd` | 执行 Shell 命令 |
| `list_dir` | 列出目录内容 |
| `read_file` | 读取文件内容（支持分页） |
| `write_file` | 写入文件内容（支持追加/覆盖） |
| `glob` | 按文件名模式搜索文件 |
| `grep` | 正则搜索文件内容（优先 rg，回退 re） |
| `edit` | 精确替换文件中的字符串（10 策略级联） |
| `web_fetch` | 获取网页内容（SSRF 防护） |
| `question` | 向用户提问并等待回答 |
| `skill` | 加载/列出 Skills |
| `todo_write` | 写入 .todos.json |

## API 端点

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/health` | 否 | 服务器状态 |
| GET | `/config` | 是 | 当前配置 |
| GET | `/prompt` | 是 | 初始化提示词 |
| GET | `/tools` | 是 | 已注册工具列表 |
| GET | `/skills` | 是 | 可用技能列表 |
| GET | `/files?q=` | 是 | 文件搜索（最多 50 条） |
| POST | `/exec` | 是 | 执行工具调用 |
| POST | `/auth` | 是 | 验证 token |

## 安全机制

- **沙箱隔离**：所有文件操作限制在工作目录内，路径穿越通过 `os.path.realpath()` 阻止
- **危险命令拦截**：`rm -rf`、`sudo`、`curl`、`mkfs`、`reboot` 等命令被屏蔽
- **Token 认证**：所有 API 端点受 Bearer token 保护（`secrets.compare_digest` 常数时间比较）
- **超时控制**：命令执行默认 60 秒超时，超时后进程终止
- **SSRF 防护**：`web_fetch` 阻止对私有 IP 段的请求

## 命令行参数

```bash
openlink [选项]

选项：
  -dir string    工作目录（默认：当前目录）
  -port int      监听端口（默认：39527）
  -timeout int   命令超时秒数（默认：60）
```

---

## 问题反馈

[提交 Issue](https://github.com/betgar/openlink/issues)

## 致谢

本项目在开发过程中参考了以下优秀的开源项目：

- [opencode](https://github.com/anomalyco/opencode)
- [MCP-SuperAssistant](https://github.com/srbhptl39/MCP-SuperAssistant)
- [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)

## 免责声明

本项目仅供学习和研究使用，**严禁用于任何商业用途**。
