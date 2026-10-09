# 开发指南

## 环境要求

- Python >= 3.12
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) 包管理器
- Chrome 浏览器

## 项目结构

```
openlink/
├── backend/              # FastAPI Python 后端
│   ├── app/
│   │   ├── main.py       # 应用入口 + CLI
│   │   ├── config.py     # Pydantic 配置
│   │   ├── api/          # HTTP 端点
│   │   ├── tools/        # 12 个工具实现
│   │   ├── executor/     # 工具分发
│   │   ├── schemas/      # Pydantic 模型
│   │   ├── core/security/ # 认证 + 沙盒
│   │   └── skills/       # SKILL.md 加载器
│   ├── prompts/          # 初始化提示词
│   └── pyproject.toml
├── frontend/             # Vue 3 管理面板
│   └── src/
│       ├── api/          # Axios 客户端
│       ├── pages/        # 7 个页面
│       ├── components/   # UI 组件
│       └── stores/       # Pinia 状态管理
├── extension/            # Chrome 扩展（精简版）
│   └── src/
│       ├── content/      # 内容脚本（DOM 观察 + 工具卡片）
│       ├── injected/     # fetch 拦截脚本
│       └── background/   # Service Worker（fetch 代理）
├── install.sh            # Linux/macOS 安装脚本
├── install.ps1           # Windows 安装脚本
└── scripts/              # 构建/部署脚本
```

## 本地开发

### 启动后端

```bash
cd backend
uv sync
uv run openlink -dir /your/workspace

# 或直接运行
uv run python -m app.main -dir /your/workspace -port 39527
```

### 开发扩展

```bash
cd extension
npm install
npm run build      # 生产构建
npm run dev        # 监听模式（改动自动重新构建）
```

构建产物在 `extension/dist/`，在 Chrome 中加载该目录即可。

### 开发管理面板

```bash
cd frontend
npm install
npm run dev        # 启动 Vite 开发服务器（热更新）
npm run build      # 生产构建
```

生产构建后由 FastAPI 自动 Serve 于 `/app/` 路径。

### 调试

```bash
# 查看服务器状态
curl http://127.0.0.1:39527/health

# 带认证的 API 调用
TOKEN=$(python -c "import json; print(json.load(open('$HOME/.openlink/settings.json'))['token'])")
curl http://127.0.0.1:39527/tools -H "Authorization: Bearer $TOKEN"

# 执行工具
curl -X POST http://127.0.0.1:39527/exec \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"exec_cmd","args":{"command":"echo hello"}}'
```

## 添加新 AI 平台支持

在 `extension/src/content/index.ts` 的 `getSiteConfig()` 中添加新站点配置：

```typescript
if (h.includes('example.com'))
  return {
    editor: 'textarea#input',
    sendBtn: 'button[type="submit"]',
    stopBtn: null,
    fillMethod: 'value',
    useObserver: true,
    responseSelector: '.response',
    supported: true,
  };
```

同时在 `extension/public/manifest.json` 的 `content_scripts.matches` 和 `web_accessible_resources.matches` 中添加对应域名。

## 添加新工具

1. 在 `backend/app/tools/` 中创建新文件，继承 `BaseTool` 抽象类
2. 在 `backend/app/executor/executor.py` 的 `register_tools()` 中注册
3. 所有文件路径操作必须通过 `core/security/sandbox.py` 的 `safe_path()` 验证

示例：

```python
from app.tools.base import BaseTool, ToolContext, ToolResult

class MyTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "My custom tool"

    @property
    def parameters(self) -> dict:
        return {"arg1": "string (required) - description"}

    def validate(self, args: dict) -> str | None:
        if not args.get("arg1"):
            return "arg1 is required"
        return None

    async def execute(self, ctx: ToolContext) -> ToolResult:
        return ToolResult(status="success", output="done")
```

## 安全注意事项

- 所有文件路径操作必须经过 `safe_path()` 验证
- 命令执行前检查 `is_dangerous_command()`
- Token 比较使用 `secrets.compare_digest()` 常数时间比较
- web_fetch 使用了 SSRF 防护（阻止私有 IP 段）
