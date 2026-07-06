# DeepSeek 适配说明

> 适配站点：`https://chat.deepseek.com/`
> 适配版本：openlink v1.1.1+ (commits `1699006` 之后)
> 验证时间：2026-07

DeepSeek 是 openlink 目前支持的 AI 站点里**实现最曲折**的一个 —— 它的 UI 用纯 `<textarea>` + 语义 BEM 类名，跟其它站点的 contenteditable/Slate.js 完全不一样；它的 API 响应是 SSE 风格的 JSON 分片，需要拼回去才能匹配 `<tool>` 标签。本文档记录所有踩过的坑，方便后续维护和新增其它类似站点。

---

## 1. 站点配置 (`getSiteConfig`)

`extension/src/content/index.ts` 里的 DeepSeek 分支：

```ts
if (h.includes('deepseek.com'))
  return {
    editor: 'textarea[placeholder="Message DeepSeek"], textarea[name="search"], textarea',
    sendBtn: '.ds-button--primary.ds-button--filled.ds-button--circle',
    stopBtn: '.ds-button--primary.ds-button--filled.ds-button--circle',
    fillMethod: 'value',
    useObserver: false,
  };
```

### 1.1 编辑器

```html
<textarea class="_27c9245 ds-scroll-area ... d96f2d2a"
          placeholder="Message DeepSeek" rows="2"
          autocomplete="off" name="search"></textarea>
```

- **纯 `<textarea>`**，不是 contenteditable/ProseMirror/Slate
- 占位符 `Message DeepSeek` 是稳定标识（不会因为 hash class 变而失效）
- `fillMethod: 'value'` 直接走原生 value setter，比 Slate 时代的 `'paste'` 简单可靠

### 1.2 发送按钮

```html
<div role="button"
     class="ds-button ds-button--primary ds-button--filled ds-button--circle ds-button--m
            ds-button--icon-relative-m ds-button--disabled _52c986b bd74640a">
  <!-- ↑箭头 SVG -->
</div>
```

- **BEM 语义类名** (`ds-button--primary/--filled/--circle`)，比 hash class (`_52c986b`) 稳定得多
- `.ds-button--disabled` **不随输入状态切换** —— DeepSeek 用 React JS state 控制可点击性，class 只是视觉装饰。原计划用 `:not(.ds-button--disabled)` 过滤，但实测加上反而选不中按钮，故去掉
- upload 按钮是 `.ds-button--iconLabelPrimary.ds-button--capsule.ds-button--s`（capsule 小号），与发送按钮（filled circle 中号）形态不同，不会误中

### 1.3 停止按钮

- **没有独立 stop 按钮**。生成时同一个 filled-circle 按钮把图标换成 stop 图标
- `stopBtn` 用与 `sendBtn` 完全相同的选择器（无 `:not` 过滤），确保 `clickStopButton` 中途找得到

### 1.4 检测路径：`useObserver: false`

DeepSeek 的工具调用响应通过 **XHR + SSE 分片**传输，不在 DOM 树里（用户看到的是渲染后的 markdown，但原始字节是 JSON 增量）。所以走 `injected.js` 的 fetch/XHR 拦截路径，而不是 DOM MutationObserver。

响应容器结构（写在 config 注释里，未来切 observer 模式时备用）：
```
div.ds-message > div.ds-markdown.ds-assistant-message-main-content
```
外层 `_4f9bf79` / `_63c77b1` / `d7dc56a8` 都是 CSS Modules hash，会随部署变 —— 不要用作选择器。

---

## 2. 工具调用检测：`injected.ts` 的两层补丁

### 2.1 第一层：拦截传输通道

DeepSeek 不用 `fetch`，**用 `XMLHttpRequest`**。原始 `injected.ts` 只覆盖 `window.fetch`，所以工具调用从来没被捕获。

新版加了三层兜底（按可能性从高到低）：

| 层 | 选择 | 拦截位置 |
|---|---|---|
| `window.fetch` | OpenAI-compatible API | 包装构造函数，返回 wrapped Response |
| `window.EventSource` | 一些 AI 站点走 SSE | 包装构造函数，拦截 `addEventListener('message')` 和 `onmessage` setter |
| `XMLHttpRequest` | DeepSeek | 包装 `open()` 记录 URL；包装 `send()` 监听 `readystatechange=4` 扫描 `responseText` |
| `window.WebSocket` | 兜底 | 包装构造函数，拦截 `dispatchEvent('message')` 前的 `data` |

实际命中的是 XHR 层。

### 2.2 第二层：重组 SSE 碎片

DeepSeek 的 `/api/v0/chat/completion` 响应体长这样（精简版）：

```
event: ready
data: {"request_message_id":1,"response_message_id":2,"model_type":"default"}

event: update_session
data: {"updated_at":1783363746.0363178}

data: {"v":{"response":{"message_id":4,...,
         "fragments":[{"id":2,"type":"RESPONSE","content":"<","references":[],"stage_id":1}],
         ...}}}

data: {"p":"response/fragments/-1/content","o":"APPEND","v":"tool"}
data: {"v":" name"}
data: {"v":"=\""}
data: {"v":"list"}
data: {"v":"_dir"}
data: {"v":"\">\n"}
...
```

AI 的回复文本被切成单字符/单词级别的 `data: {"v":"..."}` 增量，`[\s\S]*?` 这种跨多行正则匹配不到 `<tool`（被 JSON 包装打散了）。

`reassembleSSEFragments()` 把所有 `data: {` 行的 JSON 解析后：
1. **Case 1**: `obj.v` 是字符串 → 直接 push（覆盖 APPEND 操作）
2. **Case 2**: `obj.v` 是对象且 `obj.v.response.fragments` 存在 → 把每个 fragment 的 `content` 也 push（覆盖**初始 state**，关键 —— 首字符 `<` 在这里)

拼回去后才是连续的 `<tool name="list_dir"> <parameter name="path">.</parameter> </tool>`，正则能命中。

### 2.3 第三层：解析器兼容 JSON 转义

`scanText` 先扫原始 body，再扫 reassembled 文本。原始 body 是 JSON，`"` 被转义成 `\"`。`parseXmlToolCall` 在匹配前先做 `s = raw.replace(/\\"/g, '"')` 归一化 —— 否则原始 body 那条路径上正则 `name="([^"]+)"` 会在 `\"` 处找不到 `"` 而 fail。

---

## 3. **关键 bug**：死循环（页面卡死的根因）

调试过程中用户报告"deepseek回复到一半整个浏览器标签页就卡死"。根因：

```ts
// ❌ 修复前 —— RE_TOOL 没有 g flag
const RE_TOOL = /<tool...<\/tool>/;

while ((match = RE_TOOL.exec(text)) !== null) {
  if (processed.has(full)) continue;   // dedup 命中
  // → exec() 再来一次 → 没有 g flag → 永远返回同一个 match
  // → 还是 dedup 命中 → continue → ...
}
```

非全局正则 `exec()` **不推进 lastIndex**，永远返回第一个 match。配合 dedup 集合的 `processed.has(full)` 检查，主线程被锁死。

```ts
// ✅ 修复后
const RE_TOOL = /<tool...<\/tool>/g;   // ← 加上 g
```

全局正则 `exec()` 每次推进 lastIndex，找不到下一个 match 时返回 `null`，循环正常退出。

教训：**在 `while ((re.exec(text)) !== null)` 模式里，正则必须带 `g` flag**，否则是无穷循环。

---

## 4. 调试开关

`injected.ts` 和 `content/index.ts` 顶部都有：

```ts
const DEBUG = false;  // flip to true to see verbose logs
const debugLog = (...args) => { if (DEBUG) console.log('[OpenLink]', ...args); };
```

日志分两类：

| 类别 | 默认 | 触发时机 |
|---|---|---|
| **信号日志**（始终开启） | `插件已加载` / `检测到工具调用` / `工具调用解析` / `工具调用解析失败` / `提取到工具调用` | 真实事件 |
| **调试日志**（`DEBUG=false` 关闭） | `fetch →` / `EventSource →` / `XHR ←` / `reassembled SSE` / `WebSocket →` / `GET .../prompt` | 排查用 |

排查新站点适配问题时，把 `const DEBUG = false` 改成 `true`，重 build，刷新扩展。

---

## 5. Manifest 配置

`extension/public/manifest.json` 已经有 `*://*.deepseek.com/*`，本次适配没改 manifest。如果以后要新增类似站点，记得同时加到 `content_scripts.matches` 和 `web_accessible_resources.matches` 两处（前者注入 content script，后者允许 content script 注入 `injected.js`）。

---

## 6. 给后续适配者的 checklist

加新站点时按这个顺序排查：

1. **传输通道**：Network → 看 AI 响应请求是 fetch / XHR / EventSource / WebSocket？
   - 如果不是 fetch，确认 `injected.ts` 里有对应拦截层
2. **响应格式**：body 是普通 JSON 还是 SSE (`data: ...`) 还是分片 JSON？
   - 如果是 SSE/分片，需要在 `reassembleSSEFragments` 里加类似的拼接逻辑
3. **响应文本里是否有首字符的"幽灵碎片"**？比如初始 state 里的某个字段
   - 如果有，记得在 reassembly 里也提取
4. **响应文本是否带 JSON 转义**（`\"` 而不是 `"`）？
   - 如果有，在 `parseXmlToolCall` 入口做归一化
5. **正则是否带 `g` flag**？
   - 检查所有 `re.exec(...)` 循环，正则必须 global

每一步都有现成的工具和日志（DEBUG 开关），出问题先翻 `const DEBUG = true` 看信号，再决定补哪一层。