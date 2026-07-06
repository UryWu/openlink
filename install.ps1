$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  openlink 安装脚本" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# ── Check prerequisites ──────────────────────────────────────────────────

function Check-Cmd {
    param($Name, $Test)
    try {
        $null = Invoke-Expression $Test 2>$null
        Write-Host "✅ $Name" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "❌ 缺少依赖: $Name — 请先安装" -ForegroundColor Red
        return $false
    }
}

$hasPython = Check-Cmd "Python" "python --version"
$hasUV = Check-Cmd "uv" "uv --version"
$hasNpm = Check-Cmd "npm" "npm --version"

if (-not $hasPython) { Write-Error "需要 Python >= 3.12"; exit 1 }
if (-not $hasUV) { Write-Error "需要 uv 包管理器: https://docs.astral.sh/uv/"; exit 1 }

# ── Backend ──────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "── 安装后端依赖 ──" -ForegroundColor Yellow
Set-Location backend
uv sync
Write-Host "✅ 后端依赖安装完成" -ForegroundColor Green

# ── Extension ────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "── 构建 Chrome 扩展 ──" -ForegroundColor Yellow
Set-Location ../extension
if ($hasNpm) {
    npm install
    npm run build
    Write-Host "✅ 扩展构建完成 → extension/dist/" -ForegroundColor Green
} else {
    Write-Host "⚠️  未找到 npm，跳过扩展构建" -ForegroundColor Yellow
    Write-Host "   安装 Node.js 后运行: cd extension && npm install && npm run build"
}

# ── Frontend (optional) ──────────────────────────────────────────────────

Write-Host ""
Write-Host "── 构建管理面板（可选）──" -ForegroundColor Yellow
Set-Location ../frontend
if ($hasNpm) {
    npm install
    npm run build
    Write-Host "✅ 管理面板构建完成 → 访问 http://127.0.0.1:39527/app/" -ForegroundColor Green
} else {
    Write-Host "⚠️  跳过管理面板（需要 Node.js）" -ForegroundColor Yellow
}

Set-Location ..

# ── Done ─────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  安装完成！" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "启动服务器（让 AI 助手能读写指定项目目录）：" -ForegroundColor Yellow
Write-Host "  .\start.ps1                                # 默认：工作区 = openlink 仓库根"
Write-Host "  .\start.ps1 -Workspace D:\path\to\project  # 指定工作区"
Write-Host ""
Write-Host "  等价手动命令: cd backend && uv run python -m app.main -dir <workspace_path> -port 39527" -ForegroundColor Yellow
Write-Host ""
Write-Host "加载 Chrome 扩展：" -ForegroundColor Yellow
Write-Host "  1. 打开 chrome://extensions/"
Write-Host "  2. 启用「开发者模式」"
Write-Host "  3. 加载 extension\dist\ 目录"
Write-Host ""
Write-Host "启动管理面板（开发模式）：" -ForegroundColor Yellow
Write-Host "  cd frontend && npm run dev"
