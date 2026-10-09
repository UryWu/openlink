# 版本升级流程

OpenLink 三个组件（后端 FastAPI / 前端 Vue / Chrome 扩展）各有自己的版本号位置。过去手工改极易遗漏某处，bump 脚本集中处理。

> 脚本不做 git 操作（commit / tag / push 全部手工），避免脚本生成你不想要的注释。

---

## 版本号位置（权威字段）

| 组件 | 权威字段 | 同步文件 |
|------|----------|---------|
| **backend** | `backend/pyproject.toml` | `backend/VERSION` / `app/main.py` / `app/schemas/types.py` / `app/api/endpoints/health.py` |
| **frontend** | `frontend/package.json` | — |
| **extension** | `extension/public/manifest.json` | `extension/package.json` |

> ⚠️ **lockfile 不在脚本的 sed 列表里**——见下文。

---

## 用法

### Shell 版（`bump_version.sh`）

```bash
./scripts/bump_version.sh <version>                    # 全部组件统一升到 <version>
./scripts/bump_version.sh patch|minor|major            # 全部组件按当前各自版本递增
./scripts/bump_version.sh 1.2.0 --backend 1.1.5        # 仅后端用 1.1.5，其余用 1.2.0
./scripts/bump_version.sh patch --frontend minor       # 后端/扩展 +=patch，前端 +=minor
```

### 参数

| 参数 | 说明 |
|------|------|
| `<version>` | 目标版本（`X.Y.Z`）或递增类型（`patch` / `minor` / `major`） |
| `--backend X.Y.Z` | 后端单独使用该版本，覆盖主参数 |
| `--frontend X.Y.Z` | 前端单独使用该版本 |
| `--extension X.Y.Z` | 扩展单独使用该版本 |

### PowerShell 版（`bump_version.ps1`）

行为与 shell 版完全一致：

```powershell
.\bump_version.ps1 1.2.0
.\bump_version.ps1 patch
.\bump_version.ps1 1.2.0 --Backend 1.1.5
.\bump_version.ps1 patch --Frontend minor
```

> 参数名是 `-Backend` / `-Frontend` / `-Extension`（PowerShell 参数命名习惯首字母大写），不是 bash 版的 `--backend`。

---

## 脚本做了什么

1. **解析目标版本**：每个组件读自己的权威字段 → 计算目标（绝对版本或按 patch/minor/major 递增）
2. **sed 替换源文件**：`X.Y.Z` 字符串 → 目标版本（`.` 已转义，不会误改无关数字）
3. **lockfile 重新生成**：见下文 ⚠️
4. **验证**：grep 源文件确认无旧版本残留（lockfile 排除）
5. **打印 diff + 建议的 commit message**

### ⚠️ lockfile 重新生成（关键设计）

**绝对不要 sed lockfile**。uv.lock / package-lock.json 里塞满了传递依赖的版本号。一个全局 `sed s/1.1.1/1.2.0/g` 会把这些一起改了。历史上踩过这个坑：

```
real:  pathspec 1.1.1   (mypy 的传递依赖, PyPI 上有)
bump:  pathspec 1.2.0   (sed 错改)
uv sync  → 404 Not Found  (PyPI 上根本没有 pathspec 1.2.0)
```

**正确做法**：脚本只 sed 源文件（pyproject.toml / package.json / manifest.json），然后让包管理器自己重新生成 lockfile：

| 组件 | 重新生成命令 | 原理 |
|------|------------|------|
| backend | `uv lock` | 读 pyproject.toml，按当前 transitive deps 的真实版本写新 lockfile |
| frontend | `npm install` | 读 package.json，更新 package-lock.json |
| extension | `npm install` | 同上 |

这样 `pathspec` 永远是它该有的 `1.1.1`，跟 openlink 升到几都无关。

---

## 典型发布流程

```bash
# 1. 跑 bump 脚本
./scripts/bump_version.sh 1.2.0

# 2. 复核 diff（脚本会打印 --stat，但要看实际内容）
git diff

# 3. 提交
git add -A
git commit -m "chore: 升级版本到 v1.2.0"

# 4. 打 tag
git tag -a v1.2.0 -m "v1.2.0 — <简短描述本次变更>"

# 5. 推
git push origin main
git push origin v1.2.0
```

### 跳过 patch 直接发 minor/major？

可以。SemVer 判断：

- **patch** (`x.x.Z+1`)：bug fix
- **minor** (`x.Y+1.0`)：backward-compatible 新功能
- **major** (`X+1.0.0`)：breaking change

如果一个周期内**全是新功能**没有 bug fix，从 `1.1.1` 直接跳到 `1.2.0` 完全合规——不要为了"凑 patch 数"硬塞 `1.1.2` / `1.1.3`。

---

## 加新文件时怎么同步

如果以后在某个组件里新增了携带版本号的文件（比如新加了一个 `__init__.py` 里写 `__version__ = "..."`）：

1. 在 `bump_version.sh` 的 `COMPONENT_FILES[backend]` 字符串里加上新文件的路径 + `|plain` 或 `|json`
2. 在 `bump_version.ps1` 对应的 `Files` 数组里同步加上 `Path` + `Mode`
3. 跑一遍脚本 dry-run（`./bump_version.sh patch` 之类的，应该提示"already at X.Y.Z (skip)"）确认不报错
4. 真升一次（`./bump_version.sh patch`）看新文件是否被正确替换

---

## 已知陷阱

| 陷阱 | 触发 | 现象 | 解决 |
|------|------|------|------|
| 漏改某处 | 新增了版本号文件忘了同步脚本 | 脚本 grep 验证会报 "stale references" | 把新文件加进 `COMPONENT_FILES` |
| lockfile 破坏（已修复） | 旧版 sed 把 transitive deps 一起改 | uv sync 报 404 | 升级到新版脚本（不再 sed lockfile） |
| tag 推晚了 | 推 main 后忘了推 tag | 用户装不到该版本 | 总是 `git push origin main && git push origin v<ver>` 一起 |

---

## 相关脚本

- [`scripts/bump_version.sh`](../scripts/bump_version.sh) — shell 版
- [`scripts/bump_version.ps1`](../scripts/bump_version.ps1) — PowerShell 版
- [`scripts/build.sh`](../scripts/build.sh) — 编译各组件
- [`scripts/deploy-extension.sh`](../scripts/deploy-extension.sh) — 扩展打包