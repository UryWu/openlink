# openlink 文档索引

本目录收录 openlink 的开发文档、修复记录与设计规格。

## guides/ — 开发与使用指南

| 文档 | 说明 |
|------|------|
| [development.md](guides/development.md) | 开发指南 |
| [script-management.md](guides/script-management.md) | 开发脚本管理 |
| [version-bumping.md](guides/version-bumping.md) | 版本升级流程 |

## fixes/ — 问题修复记录

| 文档 | 说明 |
|------|------|
| [dsml-marker-fix.md](fixes/dsml-marker-fix.md) | 工具调用标签 DSML 乱码修复 |
| [duplicate-closing-tag.md](fixes/duplicate-closing-tag.md) | 多余闭合标签过滤 |
| [inner-tool-close-masking.md](fixes/inner-tool-close-masking.md) | 参数值内闭合标签掩码 |
| [tool-error-response.md](fixes/tool-error-response.md) | 工具错误响应被系统提示覆盖复盘 |
| [windows-chinese-path-fix.md](fixes/windows-chinese-path-fix.md) | Windows 中文路径失败修复 |

## sites/ — 站点适配

| 文档 | 说明 |
|------|------|
| [deepseek-adapt.md](sites/deepseek-adapt.md) | DeepSeek 站点适配全流程 |

## handoffs/ — 开发交接文档

| 文档 | 说明 |
|------|------|
| [analytics-clustering.md](handoffs/analytics-clustering.md) | 对话聚类功能开发交接 |

## superpowers/ — 设计与计划

| 目录 | 说明 |
|------|------|
| [specs/](superpowers/specs/) | 功能设计规格 |
| [plans/](superpowers/plans/) | 实现计划 |

## 其他文档

- 项目根 [AGENTS.md](../AGENTS.md)：架构、构建命令、模块信息
- [prompts/agent-rules.md](../prompts/agent-rules.md)：Agent 运行规范（注入 init prompt）
- [CHANGELOG.md](../CHANGELOG.md)：变更日志
