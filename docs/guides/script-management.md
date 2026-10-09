# 开发脚本管理

本文档介绍 OpenLink 项目的开发脚本管理结构。

## 脚本分类

### 用户入口脚本（项目根目录）
这些脚本面向最终用户，放置于项目根目录以方便访问：

- `install.sh` - Linux/macOS 安装脚本
- `install.ps1` - Windows PowerShell 安装脚本

### 开发维护脚本（scripts/ 目录）
这些脚本面向开发维护，统一存放在 `scripts/` 目录中：

```
scripts/
├── deploy-extension.sh     # 扩展构建和部署
├── test-platform.sh        # 平台功能测试
├── README.md              # 脚本文档
└── (未来可能增加更多脚本)
```

## 脚本规范

### 命名约定
- 使用描述性名称，前缀表示用途
- `deploy-*` 用于部署相关任务
- `test-*` 用于测试相关任务
- `build-*` 用于构建相关任务

### 脚本特性
- 可独立运行，有清晰的状态输出
- 包含必要的错误处理
- 带有说明注释头部

## 维护指导

当添加新的开发脚本时：

1. 将其添加到 `scripts/` 目录
2. 更新 `scripts/README.md` 说明文档
3. 如有必要，在 AGENTS.md 中提及使用方法