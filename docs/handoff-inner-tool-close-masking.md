> 日期：2026-10-09
> 分支：main
> 仓库：https://github.com/UryWu/openlink
> 前置：docs/handoff-duplicate-closing-tag.md（重复闭合标签折叠）

## 背景

扩展提取 AI 消息里的 `<tool>` 块时用非贪婪正则：

```
/<tool(?:\s[^>]*)?>[\s\S]*?<\/tool(?:_call)?>/g
```

当**参数值内部**含裸 `</tool>` 时（例如 `node -e "...</tool>..."`），`[\s\S]*?` 会在参数值里的第一个 `</tool>` 处提前闭合，整个块被截断 → 后续参数丢失（如 `command is required`），或工具调用被丢弃。

这不是重复闭合标签问题（那由折叠正则处理），而是**非贪婪匹配遇到内嵌同名标签**的固有缺陷。XML 无序，无法用单个正则可靠区分「块尾 `</tool>`」与「参数值内 `</tool>`」。

## 方案

解析前把**参数值内部**的 `</tool>` / `</tool_call>` 掩码为占位符，提取/解析完成后再还原。

- 占位符：`'\u0000TOOLCLOSE\u0000'`（不可能出现在正常内容中）
- 掩码函数 `maskInnerToolCloses`：仅替换 `<parameter ...>...</parameter>` 内部
- 还原函数 `unmaskInnerToolCloses`：`split(占位符).join('</tool>')`

## 改动位置

| 文件                              | 位置                    | 说明                                                         |
| --------------------------------- | ----------------------- | ------------------------------------------------------------ |
| `extension/src/content/index.ts`  | helper 定义（顶部）     | `TOOL_CLOSE` / `TOOL_CLOSE_RE` / `TOOL_CLOSE_PLACEHOLDER` / mask / unmask |
| `extension/src/content/index.ts`  | `parseXmlToolCall` 首行 | 包一层 `unmaskInnerToolCloses(...)`                          |
| `extension/src/content/index.ts`  | `scanText`              | 折叠正则后加 `maskInnerToolCloses`                           |
| `extension/src/content/index.ts`  | 输入面板手动执行        | `normalized` 折叠后加 mask                                   |
| `extension/src/content/index.ts`  | 最新回复提取            | `text` 折叠后加 mask                                         |
| `extension/src/injected/index.ts` | helper 定义（顶部）     | 同 content                                                   |
| `extension/src/injected/index.ts` | `parseXmlToolCall` 首行 | 包一层 `unmaskInnerToolCloses(...)`                          |
| `extension/src/injected/index.ts` | `scanText`              | 折叠正则后加 `maskInnerToolCloses`                           |

## 验证

1. `cd extension && npm run build` —— 构建通过。
2. `chrome://extensions` 重新加载 openlink 扩展。
3. 发送一条参数值内**含裸 `</tool>`** 的工具调用（如 `node -e` 内含 `</tool>` 字面量）。
4. 确认命令完整执行、无截断、无「无法解析工具调用 XML」告警。

## 注意事项

- helper 用字符串拼接（`'<' + '/' + 'tool' + '>'`）构造闭合标签字面量，避免在本文件内出现裸 `</tool>` 被自身正则误伤。
- 占位符含 NUL 字符（`\u0000`），不会与正常文本冲突。
- 现有重复闭合标签折叠逻辑（`/(<\/(?:tool|tool_call)>)\s*(?:\1)+/g`）保持不变，mask 在其之后执行。

## 关键文件

| 文件                              | 作用                                     |
| --------------------------------- | ---------------------------------------- |
| `extension/src/injected/index.ts` | SSE 拦截、`parseXmlToolCall`、`scanText` |
| `extension/src/content/index.ts`  | DOM 观察、输入面板、最新回复提取         |
