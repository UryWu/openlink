# 对话记录 + Token 统计 — 设计文档

日期：2026-10-09

## 目标

记录所有经 openlink 扩展处理的 AI 对话（用户消息 + AI 回复），统计 token 用量，并在 Web 面板 `/app/` 展示。

## 范围

- 仅支持 DeepSeek（`chat.deepseek.com`）平台，其他平台后续扩展。
- Token 用 DeepSeek 官方离线 tokenizer 本地计算（零成本）。
- 数据存本地 JSONL，不使用数据库。

## 架构

```
DeepSeek 网页
  ↓ 用户发问、AI 回复（DOM 变化）
扩展 content script
  ↓ 检测到一轮 AI 回复完成
  ↓ 抓取 user 消息 + assistant 回复
  ↓ POST {apiUrl}/conversations
后端 FastAPI
  ↓ 用 DeepSeek 离线 tokenizer 计算 input/output tokens
  ↓ 追加写入 ~/.openlink/conversations.jsonl
  ↓
前端 /app/analytics 页面
  ↓ GET {apiUrl}/stats 聚合展示
```

## 数据存储

文件：`C:\Users\UryWu\.openlink\conversations.jsonl`

每行一条记录（JSON）：

```json
{
  "ts": 1759900000000,
  "platform": "chat.deepseek.com",
  "convId": "063a5438-...",
  "user": "用户消息文本",
  "assistant": "AI 回复文本",
  "inputTokens": 123,
  "outputTokens": 456
}
```

- `ts`：Unix 毫秒时间戳
- `platform`：来源站点 hostname
- `convId`：会话 ID（DeepSeek URL 中的会话段，可空）
- `user` / `assistant`：该轮消息文本
- `inputTokens` / `outputTokens`：后端计算

## 后端 API

### POST /conversations

接收一条对话记录，计算 token，追加写入。

请求体（Pydantic `ConversationIn`）：

```json
{
  "platform": "chat.deepseek.com",
  "convId": "abc",
  "user": "...",
  "assistant": "..."
}
```

服务端补充 `ts`、`inputTokens`、`outputTokens` 后写入。

响应：

```json
{ "status": "ok", "inputTokens": 123, "outputTokens": 456 }
```

### GET /stats

读取全部 JSONL，聚合返回。

响应结构：

```json
{
  "summary": {
    "count": 42,
    "inputTokens": 12345,
    "outputTokens": 67890,
    "totalTokens": 80235
  },
  "byDay": [
    { "date": "2026-10-09", "inputTokens": 1000, "outputTokens": 2000 }
  ],
  "byPlatform": [
    { "platform": "chat.deepseek.com", "count": 42, "tokens": 80235 }
  ],
  "recent": [
    {
      "ts": 1759900000000,
      "platform": "chat.deepseek.com",
      "user": "用户消息摘要（前 100 字）",
      "inputTokens": 123,
      "outputTokens": 456
    }
  ]
}
```

`recent` 最多返回最近 100 条。

## Token 计算

使用 DeepSeek 官方离线 tokenizer（`deepseek_tokenizer.py` + 对应 `tokenizer.json`），放在 `backend/app/utils/` 下。

- `inputTokens = count_tokens(user)`
- `outputTokens = count_tokens(assistant)`
- 若 tokenizer 加载失败，降级为启发式估算（中文按字符数、英文按空白分词），并记录一次 warning。

## 前端

### 页面

新增 `frontend/src/pages/Analytics.vue`，路由 `/analytics`。

组件：

1. **汇总卡片**（4 个）：对话总数、输入 tokens、输出 tokens、总 tokens
2. **每日趋势**：纯 SVG 折线图，展示每日 input/output token
3. **平台分布**：纯 CSS 横向条形，展示各平台 token 占比
4. **最近对话**：表格（时间、平台、消息摘要、输入/输出 token）

### 导航

在现有导航中新增「对话统计」入口，链接到 `/analytics`。

### Store

新增 `frontend/src/stores/analytics.ts`（Pinia），封装 `GET /stats` 调用与状态。

## 扩展

在 `extension/src/content/index.ts` 中：

1. 检测到一轮 AI 回复完成（复用现有 DOM observer / SSE 完成信号）。
2. 抓取该轮的 user 消息文本与 assistant 回复文本。
3. 取 `authToken` / `apiUrl`，`POST {apiUrl}/conversations`。
4. 失败静默（不打断用户），仅在 console 记录。

DeepSeek 用户消息 DOM 定位：

- 用户消息容器：`div._9663006`（class 可能变化，用启发式：AI 消息在 `div.ds-markdown`，其前一个兄弟为用户消息块）。
- 需实测确认选择器，做成可配置常量。

## 错误处理

- 后端写文件失败：返回 `status:error`，前端 toast，不崩溃。
- Token 计算失败：降级估算，不阻断写入。
- 扩展上报失败：console.warn，不打断对话。

## 测试

- 后端：`POST /conversations` 写入 → `GET /stats` 读回，断言汇总数值正确。
- Token：用已知文本断言 input/output token 数为正整数。
- 前端：`vue-tsc` 类型检查通过 + `vite build` 成功。
- 扩展：`vite build` 成功；手动在 DeepSeek 页面验证一条对话被上报。

## 非目标（YAGNI）

- 不支持 DeepSeek 以外平台（后续按需加）。
- 不做图表库依赖（纯 SVG/CSS）。
- 不做 token 精确 API 调用（用离线 tokenizer）。
- 不做数据库（用 JSONL）。
- 不做数据清理 / 归档策略（个人用量）。
