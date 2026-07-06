#!/bin/bash
set -e

echo "OpenLink 扩展部署准备"
echo "======================"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 1. Build extension
echo "1. 构建扩展..."
cd "$ROOT_DIR/extension"
npm install
npm run build

if [ $? -ne 0 ]; then
    echo "❌ 构建失败"
    exit 1
fi
echo "✅ 构建成功"

# 2. Verify output files
echo "2. 验证构建文件..."
cd dist

REQUIRED_FILES=("manifest.json" "content.js" "background.js" "injected.js")

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✓ $file"
    else
        echo "   ✗ $file 缺失"
        exit 1
    fi
done
echo "✅ 所有必需文件存在"

# 3. Verify platforms in manifest
echo "3. 验证平台配置..."
PLATFORM_COUNT=$(grep -c '"matches"' manifest.json || echo 0)
echo "   找到 ${PLATFORM_COUNT} 个 match 配置"
if [ "$PLATFORM_COUNT" -lt 1 ]; then
    echo "⚠️  平台配置可能不足"
else
    echo "✅ 平台配置正常"
fi

# 4. Package extension
echo "4. 打包扩展..."
DATE=$(date +%Y%m%d_%H%M%S)
ZIP_NAME="$ROOT_DIR/openlink-extension-${DATE}.zip"

if command -v zip >/dev/null 2>&1; then
    zip -r "$ZIP_NAME" .
    echo "✅ 扩展包: $ZIP_NAME"
else
    echo "⚠️  zip 不可用，跳过打包"
fi

cd "$ROOT_DIR"

echo ""
echo "部署准备完成！"
echo ""
echo "加载扩展："
echo "  1. chrome://extensions/"
echo "  2. 开启开发者模式"
echo "  3. 加载 extension/dist/ 目录"
