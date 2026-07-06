#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

# ── Build extension ──────────────────────────────────────────────────────

build_extension() {
    log_info "构建 Chrome 扩展..."
    cd "$ROOT_DIR/extension"

    if ! command_exists npm; then
        log_error "npm 未安装"
        exit 1
    fi

    npm install
    npm run build

    if [ -d "dist" ]; then
        log_success "扩展构建成功: $ROOT_DIR/extension/dist"
        ls -la dist/
    fi
}

# ── Build frontend ───────────────────────────────────────────────────────

build_frontend() {
    log_info "构建 Vue 管理面板..."
    cd "$ROOT_DIR/frontend"

    if ! command_exists npm; then
        log_error "npm 未安装"
        exit 1
    fi

    npm install
    npm run build

    if [ -d "dist" ]; then
        log_success "管理面板构建成功: $ROOT_DIR/frontend/dist"
    fi
}

# ── Build all ────────────────────────────────────────────────────────────

build_all() {
    log_info "构建全部..."
    build_extension
    echo ""
    build_frontend
    log_success "全部构建完成！"
}

# ── Package extension ────────────────────────────────────────────────────

package_extension() {
    build_extension
    cd "$ROOT_DIR/extension/dist"
    DATE=$(date +%Y%m%d_%H%M%S)
    ZIP_NAME="$ROOT_DIR/openlink-extension-$DATE.zip"
    if command_exists zip; then
        zip -r "$ZIP_NAME" .
        log_success "扩展打包: $ZIP_NAME"
    else
        log_warn "zip 未安装，跳过打包"
    fi
}

# ── Cleanup ──────────────────────────────────────────────────────────────

cleanup() {
    log_info "清理构建产物..."
    cd "$ROOT_DIR"
    rm -rf extension/dist frontend/dist
    log_success "清理完成"
}

# ── Help ─────────────────────────────────────────────────────────────────

show_help() {
    echo "openlink 构建脚本"
    echo ""
    echo "用法: ./scripts/build.sh [command]"
    echo ""
    echo "命令:"
    echo "  extension    构建 Chrome 扩展"
    echo "  frontend     构建 Vue 管理面板"
    echo "  all          构建扩展 + 管理面板"
    echo "  package      构建扩展并打包 zip"
    echo "  clean        清理构建产物"
    echo "  help         帮助"
}

# ── Main ─────────────────────────────────────────────────────────────────

case "${1:-}" in
    extension) build_extension ;;
    frontend) build_frontend ;;
    all)       build_all ;;
    package)   package_extension ;;
    clean)     cleanup ;;
    help|-h|""|--help) show_help ;;
    *)         log_error "未知命令: $1"; show_help; exit 1 ;;
esac
