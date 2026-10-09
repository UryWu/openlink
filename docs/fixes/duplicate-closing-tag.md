# Hand-off：多余 `</tool>` 闭合标签过滤

> 日期：2026-10-09
> 分支：main（工作区有未提交改动）
> 仓库：https://github.com/UryWu/openlink

## 背景

AI 偶尔会输出多余的 `</tool>` 闭合标签，例如结尾出现两个 `</tool>`。这会影响扩展的 `<tool>` 正则匹配与去重逻辑。**必须在前端扩展侧过滤**——多余的闭合标签出现在 AI 回复文本里，等传给后端时早已解析完，后端拿不到原始错误文本。

## 已完成的改动（未提交）

在**四处**解析/扫描入口，加入折叠逻辑：

```js
text = text.replace(/(<\/(?:tool|tool_call)>)\s*(?:\1)+/g, '$1');
```

该正则把连续重复的 `</tool>` / `</tool_call>` 折叠为一个。

改动位置：

| 文件                              | 位置             | 说明                        |
| --------------------------------- | ---------------- | --------------------------- |
| `extension/src/injected/index.ts` | `scanText` 入口  | SSE 拦截路径                |
| `extension/src/content/index.ts`  | `scanText` 入口  | DOM 观察路径                |
| `extension/src/content/index.ts`  | 输入面板手动执行 | `let normalized = ...` 之后 |
| `extension/src/content/index.ts`  | 最新回复提取     | `let text = ...` 之后       |

## 验证

构建已完成（`cd extension && npm run build`）。

1. 在 `chrome://extensions` 重新加载 openlink 扩展。
2. 发送一条带多余 `</tool>` 的调用（结尾两个 `</tool>`）。
3. 确认被正常解析并执行，无「无法解析工具调用 XML」告警。

## 待办

1. **提交当前未提交改动**：`extension/src/content/index.ts`、`extension/src/injected/index.ts`。
2. **验证**上述场景。
3. 可选：将此折叠逻辑与已有的控制标记剥离合并为一个统一的「工具调用文本归一化」函数，减少四处重复代码。

## 关键文件

| 文件                              | 作用                                     |
| --------------------------------- | ---------------------------------------- |
| `extension/src/injected/index.ts` | SSE 拦截、`parseXmlToolCall`、`scanText` |
| `extension/src/content/index.ts`  | DOM 观察、输入面板、最新回复提取         |