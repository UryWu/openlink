# AGENTS.md — openlink Development Guide

本文件是 openlink 项目的开发指南，涵盖项目架构、构建命令、代码规范、注释要求等，适用于 Claude / Agent 等自动化工具。

---

## Project Overview

openlink 是一个**浏览器本地代理**，使 Web AI 助手（Gemini/ChatGPT/DeepSeek 等）能通过沙箱化的 FastAPI 服务与 Chrome 扩展访问本地文件系统。

**架构**：三组件系统

1. **FastAPI Server**（`backend/app/main.py`）：HTTP 服务，在沙箱目录内执行文件系统操作
2. **Chrome Extension**（`extension/src/content/index.ts`）：内容脚本，拦截 AI 工具调用并代理到本地服务，提供输入补全 UI
3. **Vue 3 Dashboard**（`frontend/src/`）：Web 管理面板，挂在 `/app/`

---

## Architecture

### Request Flow

```
Web AI (Gemini/ChatGPT/DeepSeek/etc.)
  ↓ outputs <tool> tags in response
content script (extension/src/content/index.ts)
  ↓ MutationObserver detects tool tags, renders card UI
  ↓ HTTP POST to localhost:39527/exec (via background fetch)
FastAPI Server (backend/app/main.py)
  ↓ validates & sanitizes
Executor (backend/app/executor/executor.py)
  ↓ executes with sandbox
Security Layer (backend/app/core/security/sandbox.py)
  ↓ path validation & command filtering
Local Filesystem
```

### Key Components

**backend/app/schemas/types.py**：核心数据结构

- `ToolRequest`：来自浏览器的工具调用请求（name、args、可选 arguments 别名）
- `ToolResponse`：执行结果（status、output、error、stopStream）
- `AppConfig`：服务配置（root_dir、port、timeout、token）

**backend/app/core/security/sandbox.py**：安全执行

- `safe_path()`：通过 `os.path.realpath()` 校验所有文件路径在 RootDir 内
- `is_dangerous_command()`：拦截危险命令（rm -rf、sudo、curl、wget 等）

**backend/app/core/security/auth.py**：基于 token 的认证

- `load_or_create_token()`：读取 `~/.openlink/settings.json`，缺失时生成 32 字节 hex token
- `verify_token()`：FastAPI 依赖，基于 HTTPBearer + `secrets.compare_digest()` 常量时间比较

**backend/app/executor/executor.py**：工具执行调度器

- 所有操作走 asyncio 超时（默认 60s）
- 每次调用注入身份提醒，每 20 次注入完整 init prompt
- 工具名大小写不敏感查找

**backend/app/tools/**：单个工具实现

- `edit.py`：10 策略字符串替换级联（最复杂，约 330 行）
- 其他工具：exec_cmd、list_dir、read_file、write_file、glob、grep、web_fetch、question、skill、todo_write

**backend/app/skills/loader.py**：Skills 加载器

- 扫描 7 个目录下的 SKILL.md 文件，解析 YAML frontmatter

**backend/app/api/**：FastAPI 端点

- `GET /health`：服务状态与版本
- `GET /config`：当前配置
- `GET /prompt`：包含系统信息与 skills 列表的 init prompt
- `GET /skills`：可用 skills（name + description）
- `GET /tools`：已注册工具与参数
- `GET /files?q=`：RootDir 下的文件列表（最多 50，跳过 .git/node_modules）
- `POST /exec`：执行工具请求
- `POST /auth`：校验 token
- CORS 对所有 origin 启用

**extension/src/content/index.ts**：主内容脚本

- `getSiteConfig()`：按站点选择编辑器、发送按钮、填充方式
- `startDOMObserver()`：MutationObserver + debounce (800ms) + maxWait (3000ms) 工具检测
- `renderToolCard()`：在检测到的工具调用上方渲染手动执行 UI 卡片
- `fillAndSend()`：填充编辑器并可配置延迟自动发送
- `attachInputListener()`：输入事件上的斜杠命令（`/`）与 `@` 文件补全
- `showPickerPopup()`：可键盘导航的 skill/文件选择下拉
- `replaceTokenInEditor()`：跨平台 token 替换（value/execCommand/prosemirror/paste）

**frontend/src/**：Vue 3 SPA

- Pages：Dashboard、Connection、ToolConsole、FileBrowser、SkillsView、PromptViewer、Settings
- Stores (Pinia)：connection、tools、skills
- API client：Axios + Bearer token 拦截器

### Supported AI Platforms

| Platform | fillMethod | useObserver | Notes |
|----------|-----------|-------------|-------|
| Google AI Studio | value | true | Recommended; writes to System Instructions |
| Google Gemini | execCommand | true | |
| ChatGPT | prosemirror | true | |
| 通义千问 (Qwen) | value | true | |
| DeepSeek | paste | false | Uses injected.js |
| Kimi | execCommand | false | |
| Mistral | execCommand | false | |
| Perplexity | execCommand | false | |
| Arena.ai | value | true | |
| OpenRouter | value | false | |
| Grok | value | false | |
| GitHub Copilot | value | false | |
| t3.chat | value | false | |
| z.ai | value | false | |

---

## Build & Run Commands

### FastAPI Server

```bash
cd backend
uv sync
uv run python -m app.main -dir /path/to/workspace -port 39527
```

### Chrome Extension

```bash
cd extension
npm install
npm run build    # 输出到 extension/dist/
npm run dev      # 监听模式
```

### Vue Frontend

```bash
cd frontend
npm install
npm run dev      # 开发服务器（端口 5173）
npm run build    # 生产构建 → frontend/dist/
```

### Testing

```bash
cd backend
uv run pytest
```

### Verification

```bash
# 检查服务健康
curl http://127.0.0.1:39527/health

# 列出工具（带认证）
TOKEN=$(python -c "import json; print(json.load(open('$HOME/.openlink/settings.json'))['token'])")
curl http://127.0.0.1:39527/tools -H "Authorization: Bearer $TOKEN"

# 列出可用 skills
curl http://127.0.0.1:39527/skills -H "Authorization: Bearer <token>"

# 测试命令执行
curl -X POST http://127.0.0.1:39527/exec \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"name":"exec_cmd","args":{"command":"ls -la"}}'
```

### Scripts

```bash
./scripts/build.sh all          # 构建 extension + frontend
./scripts/deploy-extension.sh   # 打包 extension 准备发布
```

### Installing the Extension

1. 先构建：`cd extension && npm run build`
2. 打开 Chrome：`chrome://extensions/`
3. 启用「开发者模式」
4. 点击「加载已解压的扩展程序」
5. 选择 `extension/dist/` 目录

---

## Code Style Guidelines

### Python (Backend)

- 遵循 PEP 8
- 前向引用使用 `from __future__ import annotations`
- 所有函数签名加类型提示
- 工具定义用抽象基类（`BaseTool`）
- I/O 密集型端点用 `async def`
- Pydantic 模型配合 `model_validator` 做字段规范化
- 安全检查用 `os.path.realpath()` 解析符号链接

### TypeScript (Extension)

- 启用 strict mode
- 数据结构用 `interface`，联合类型用 `type`
- API 调用全部 async/await
- 匹配 `extension/src/content/index.ts` 现有代码风格
- 不使用 React — 内容脚本使用原生 DOM 操作

### Vue 3 (Frontend)

- Composition API + `<script setup lang="ts">`
- Pinia stores 使用 composable 模式
- Scoped CSS + 暗色主题 CSS 变量
- 路由组件懒加载

### Naming Conventions

- **Python**：函数/变量用 `snake_case`，类用 `PascalCase`
- **Python 文件**：`snake_case.py`
- **TypeScript**：变量/函数用 `camelCase`，类型/组件用 `PascalCase`
- **Vue 文件**：组件用 `PascalCase.vue`

### Error Handling

- Backend：返回 `ToolResult`，包含 `status="error"` 和描述性错误信息
- Extension：在工具卡片 UI 展示错误
- 不向客户端暴露内部路径或堆栈

### Security Patterns

- 始终用 `safe_path()`（来自 `core/security/sandbox.py`）校验文件路径
- 路径校验前总是先解析符号链接
- 执行 shell 前用 `is_dangerous_command()` 过滤
- token 比较使用 `secrets.compare_digest()`
- `web_fetch` 中做 SSRF 防护 — 解析 host 并检查私有 IP 段

### Git & Commits

- 提交聚焦单一关注点
- 写清晰的 commit message 说明「为什么」而不只是「做了什么」
- 未经用户明确要求不要提交

---

## Module Information

- **Backend**：Python >= 3.12，FastAPI + Pydantic + httpx + uvicorn
- **Package Manager**：uv
- **Frontend**：Vue 3 + Pinia + Vue Router + Axios，使用 Vite 构建
- **Extension**：TypeScript，Manifest V3，使用 Vite 构建

---

## Architecture Notes

- 服务使用 FastAPI lifespan 上下文管理器处理启动/关闭
- CORS 对所有 origin 启用（浏览器扩展所需）
- 工具执行使用 `asyncio.wait_for()` 加超时
- Skills 系统从 7 个目录加载 `SKILL.md` 文件，按 name 去重
- Vue 前端作为静态文件挂在 `/app/`，使用 SPA fallback 中间件

---

## 减少常见 LLM 编码错误的行为准则

> **权衡**：本准则偏向谨慎而非速度。对于简单任务，请自行判断。

### 1. 编码前先思考

**不要假设。不要隐藏困惑。把权衡摆出来。**

在实现之前：

- 明确说出你的假设。如果不确定，就问。
- 如果存在多种理解方式，列出来。
- 如果有更简单的方案，说出来。
- 如果有什么不清楚，停下来。说明哪里困惑。

### 2. 简单优先

**能解决问题的最少代码。不要投机性功能。**

- 不要添加未被要求的功能。
- 单次使用的代码不要进行抽象。
- 不要添加未被要求的「灵活性」。
- 不要为不可能发生的场景编写错误处理。
- 如果 200 行代码能缩写成 50 行，就重写。

### 3. 外科手术式修改

**只改必须改的。只清理自己弄乱的。**

- 不要「改进」相邻的代码或格式。
- 不要重构没有问题的部分。
- 匹配现有代码风格，即使你不喜欢。
- 如果发现死代码，可以提一句——但不要删除。

### 4. 目标驱动执行

**定义成功标准。循环直到验证通过。**

将任务转化为可验证的目标：

- 「加个验证」 → 「写测试，然后让测试通过」
- 「修这个 bug」 → 「用测试复现，然后修复」
- 「重构 X」 → 「确保重构前后测试都通过」

---

## 5. 注释规范

### 1. 注释要求（必须遵守）

- 本项目 **所有代码必须包含详细的中文注释**。
- 注释应说明以下内容：
  - 代码的功能
  - 所有变量含义
  - 重要逻辑步骤
  - 输入与输出
  - 可能的异常情况

### 2. 注释粒度

要求达到 **「读注释即可理解代码逻辑」** 的程度。

**示例1**：

```python
def calculate_total_price(price, quantity):
    """
    计算商品总价

    参数：
    price (float): 单价
    quantity (int): 商品数量

    返回：
    float: 商品总价
    """

    # 计算总价：单价 * 数量
    total = price * quantity

    # 返回计算结果
    return total
```

**示例2**：

```python
class AIConversation(Base):
    """AI对话模型"""
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)  # 用户会话ID，用于标识用户会话
    role = Column(Enum(RoleEnum), nullable=False)  # 消息角色，区分用户消息和AI助手回复
    content = Column(Text, nullable=False)  # 消息内容，存储用户问题或AI回复的文本
    conversation_metadata = Column(JSONB)  # 对话元数据，存储额外上下文，如工具使用、产品ID引用等
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 记录创建时间，自动设置为当前时间
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # 记录最后更新时间，自动更新为当前时间
```

### 3. 编码规范

注释好、明确好输入输出参数，使其更工程化，更适宜其他同事接手。
变量名小写，硬编码变量大写，尽量不要有魔法数字。

### 4. 在agent用bash命令的时候设置utf-8编码输出

参考：

```bash
uv run python -c 'import sys; sys.stdout.reconfigure(encoding="utf-8"); print("后面是执行的命令")'
```

---

*根据项目需要，可将上述准则与团队已有的编码规范、检查清单或自动化工具配置合并使用。*