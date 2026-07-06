# 脚本工具目录

OpenLink 项目的辅助脚本。

## 脚本说明

### `build.sh`

**功能：** 构建项目各组件

```bash
./scripts/build.sh [command]
```

**可用命令：**

| 命令 | 说明 |
|------|------|
| `extension` | 构建 Chrome 扩展 → `extension/dist/` |
| `frontend` | 构建 Vue 管理面板 → `frontend/dist/` |
| `all` | 构建扩展 + 管理面板 |
| `package` | 构建扩展并打包 zip |
| `clean` | 清理构建产物 |

### `deploy-extension.sh`

**功能：** 扩展部署准备（构建 + 验证 + 打包）

```bash
./scripts/deploy-extension.sh
```

### `test-platform.sh`

**功能：** 测试各 AI 平台配置

### `bump_version.sh` / `bump_version.ps1`

**功能：** 批量更新项目版本号（仅做文件编辑，不做 git 操作）

> 📖 完整说明（含用法、SemVer 判断、lockfile 重新生成原理、加新文件时的同步步骤、已知陷阱）见 **[`docs/version-bumping.md`](../docs/version-bumping.md)**

快速参考：

```bash
./scripts/bump_version.sh 1.2.0                    # 全部组件统一升到 1.2.0
./scripts/bump_version.sh patch|minor|major        # 全部组件按各自当前版本递增
./scripts/bump_version.sh 1.2.0 --backend 1.1.5    # 仅后端用 1.1.5，其余用 1.2.0

# PowerShell 等价:
.\bump_version.ps1 1.2.0
.\bump_version.ps1 patch
.\bump_version.ps1 1.2.0 --Backend 1.1.5
```

每个组件的"当前版本"从其生态的权威字段读取：backend ← `pyproject.toml`，frontend ← `package.json`，extension ← `manifest.json`（Chrome 真正加载时看的字段）。

> ⚠️ **lockfile 不在脚本的 sed 列表里**——脚本只动源文件，lockfile 由 `uv lock` / `npm install` 重新生成。否则会把传递依赖（如 `pathspec 1.1.1`）错改成不存在的版本（`1.2.0`），导致 `uv sync` 报 404。

#### 典型发布流程

```bash
./scripts/bump_version.sh 1.2.0          # 改文件 + 重新生成 lockfile
git diff                                # 复核
git add -A
git commit -m "chore: 升级版本到 v1.2.0"
git tag -a v1.2.0 -m "v1.2.0 — <描述>"
git push origin main
git push origin v1.2.0
```
