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

### `bump_version.sh`

**功能：** 批量更新项目版本号 + 同步 lockfile（仅做文件编辑，不做 git 操作）

版本号散落在后端 / 前端 / 扩展各自生态的多处文件，过去手工改极易遗漏。本脚本集中处理：

| 组件 | 读取 / 写入位置 |
|------|-----------------|
| backend | `pyproject.toml` / `VERSION` / `main.py` / `schemas/types.py` / `api/endpoints/health.py` / `uv.lock` |
| frontend | `package.json` / `package-lock.json` |
| extension | `public/manifest.json` / `package.json` / `package-lock.json` |

每个组件的"当前版本"从其生态的权威字段读取：backend ← `pyproject.toml`，frontend ← `package.json`，extension ← `manifest.json`（Chrome 真正加载时看的字段）。

**用法：**

```bash
./scripts/bump_version.sh <version>                    # 全部组件统一升到 <version>
./scripts/bump_version.sh patch|minor|major            # 全部组件按当前各自版本递增
./scripts/bump_version.sh 1.2.0 --backend 1.1.5        # 仅后端用 1.1.5，其余用 1.2.0
./scripts/bump_version.sh patch --frontend minor       # 后端/扩展 +=patch，前端 +=minor
```

**参数：**

| 参数 | 说明 |
|------|------|
| `<version>` | 目标版本（`X.Y.Z`）或递增类型（`patch` / `minor` / `major`） |
| `--backend X.Y.Z` | 后端单独使用该版本，覆盖主参数 |
| `--frontend X.Y.Z` | 前端单独使用该版本 |
| `--extension X.Y.Z` | 扩展单独使用该版本 |

**行为：**

- 解析每个组件的目标版本 → 用 sed 替换该组件所有版本号文件 → 自动跑 `npm install` / `uv sync` 同步 lockfile → grep 验证无旧版本残留
- 完成后**只**打印 `git diff --stat` 和建议的 commit message
- `git commit` / `git tag` / `git push` 全部保留手工控制（避免脚本生成你不想要的注释）

**典型发布流程：**

```bash
./scripts/bump_version.sh 1.2.0          # 改文件 + 同步 lockfile
git diff                                # 复核
git add -A
git commit -m "chore: 升级版本到 v1.2.0"
git tag -a v1.2.0 -m "v1.2.0版本新增特性"
git push origin main
git push origin v1.2.0
```

**注意：** 脚本中 sed 已对版本号中的 `.` 做转义，避免误改 `uv.lock` 中的无关数字字段。如果新增了版本号文件，需同步更新脚本中 `COMPONENT_FILES` 字典。

#### Windows 等价版本：`bump_version.ps1`

`bump_version.sh` 是给 Git Bash / Linux / macOS 用的。Windows 原生 cmd 环境请用 PowerShell 版本，行为完全一致：

```powershell
.\bump_version.ps1 1.2.0
.\bump_version.ps1 patch
.\bump_version.ps1 1.2.0 --Backend 1.1.5
.\bump_version.ps1 patch --Frontend minor
```

**注意：**
- 调用时参数是 `-Backend` / `-Frontend` / `-Extension`（PowerShell 参数命名习惯首字母大写），不是 bash 版的 `--backend`
- 实现细节：通过 `[System.IO.File]::ReadAllText` + 显式 UTF-8（无 BOM）编码读写文件，绕开 PowerShell 5.x 的 `Get-Content` / `Set-Content` 默认使用 ANSI 代码页导致的乱码问题
- 同样**不**做 commit / tag / push
