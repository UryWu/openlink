#!/bin/sh
set -e

echo "========================================="
echo "  openlink 安装脚本"
echo "========================================="
echo ""

# ── Check prerequisites ──────────────────────────────────────────────────

check_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "❌ 缺少依赖: $1 — 请先安装"
    exit 1
  fi
}

check_cmd python3
echo "✅ Python $(python3 --version 2>&1)"

check_cmd uv
echo "✅ uv $(uv --version 2>&1)"

# ── Backend ──────────────────────────────────────────────────────────────

echo ""
echo "── 安装后端依赖 ──"
cd backend
uv sync
echo "✅ 后端依赖安装完成"

# ── Extension ────────────────────────────────────────────────────────────

echo ""
echo "── 构建 Chrome 扩展 ──"
cd ../extension
if command -v npm >/dev/null 2>&1; then
  npm install
  npm run build
  echo "✅ 扩展构建完成 → extension/dist/"
else
  echo "⚠️  未找到 npm，跳过扩展构建"
  echo "   安装 Node.js 后运行: cd extension && npm install && npm run build"
fi

# ── Frontend (optional) ──────────────────────────────────────────────────

echo ""
echo "── 构建管理面板（可选）──"
cd ../frontend
if command -v npm >/dev/null 2>&1; then
  npm install
  npm run build
  echo "✅ 管理面板构建完成 → 访问 http://127.0.0.1:39527/app/"
else
  echo "⚠️  跳过管理面板（需要 Node.js）"
fi

cd ..

# ── Done ─────────────────────────────────────────────────────────────────

echo ""
echo "========================================="
echo "  安装完成！"
echo "========================================="
echo ""
echo "启动服务器（让 AI 助手能读写指定项目目录）："
echo "  Windows:    .\start.ps1                                    # 工作区 = openlink 仓库根"
echo "             .\start.ps1 -Workspace /path/to/your/project   # 指定工作区"
echo ""
echo "  等价手动命令: cd backend && uv run python -m app.main -dir <workspace_path> -port 39527"
echo ""
echo "加载 Chrome 扩展："
echo "  1. 打开 chrome://extensions/"
echo "  2. 启用「开发者模式」"
echo "  3. 加载 extension/dist/ 目录"
echo ""
echo "启动管理面板（开发模式）："
echo "  cd frontend && npm run dev"
echo ""
