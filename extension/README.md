# OpenLink Chrome Extension

精简版 Chrome 扩展，保持核心的 DOM 拦截功能：
- **Content Script**: DOM 观察器检测 AI 工具调用，渲染工具卡片 UI
- **Injected Script**: fetch 拦截（用于 DeepSeek 等需要注入脚本的平台）
- **Background Script**: fetch 代理转发请求至本地 FastAPI 后端

## 安装依赖

```bash
npm install
```

## 开发

```bash
npm run dev       # 监听模式
npm run build     # 生产构建
```

构建产物在 `dist/` 目录。

## 加载到 Chrome

1. 打开 `chrome://extensions/`
2. 开启"开发者模式"
3. 点击"加载已解压的扩展程序"
4. 选择 `dist/` 目录

## 前置条件

需要先启动 FastAPI 后端：

```bash
cd ../backend
uv run openlink -dir /your/workspace
```
