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
