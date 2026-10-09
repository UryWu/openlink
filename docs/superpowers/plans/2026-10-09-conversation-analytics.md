# 对话记录 + Token 统计 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 记录所有经 openlink 扩展处理的 DeepSeek 对话（用户消息 + AI 回复），用 DeepSeek 离线 tokenizer 统计 token，并在 `/app/analytics` 展示。

**架构：** 扩展抓取对话 → `POST /conversations`（后端算 token + 追加写 `~/.openlink/conversations.jsonl`）→ `GET /stats` 聚合 → 前端 Analytics 页面展示。

**技术栈：** FastAPI + Pydantic + `tokenizers`（DeepSeek tokenizer.json）；Vue 3 + Pinia + vue-router；TypeScript。

**规格：** `docs/superpowers/specs/2026-10-09-conversation-analytics-design.md`

---

## 文件结构

**后端：**
- 创建 `backend/app/utils/token_count.py` — tokenizer 单例 + `count_tokens(text)`
- 创建 `backend/app/core/conversations/store.py` — JSONL 追加写 + 读取
- 创建 `backend/app/api/endpoints/conversations.py` — `POST /conversations` + `GET /stats`
- 修改 `backend/app/schemas/types.py` — 新增 `ConversationIn`、`StatsResponse` 等模型
- 修改 `backend/app/api/router.py` — 挂载新路由
- 创建 `backend/tests/test_conversations.py` — 后端测试

**前端：**
- 创建 `frontend/src/types/index.ts`（追加类型）— `StatsResponse` 等
- 修改 `frontend/src/api/endpoints.ts` — `fetchStats()`
- 创建 `frontend/src/stores/analytics.ts` — Pinia store
- 创建 `frontend/src/pages/Analytics.vue` — 统计页面
- 修改 `frontend/src/router/index.ts` — `/analytics` 路由
- 修改 `frontend/src/components/Layout.vue` — 侧边栏入口

**扩展：**
- 修改 `extension/src/content/index.ts` — 抓取对话并上报

---

## 任务 1：后端 token 计数工具

**文件：**
- 创建：`backend/app/utils/token_count.py`
- 测试：`backend/tests/test_token_count.py`

- [ ] **步骤 1：编写失败的测试**

创建 `backend/tests/test_token_count.py`：

```python
import sys
sys.stdout.reconfigure(encoding="utf-8")

from app.utils.token_count import count_tokens


def test_count_tokens_positive():
    """英文文本应返回正整数 token 数。"""
    n = count_tokens("hello world")
    assert isinstance(n, int)
    assert n > 0


def test_count_tokens_chinese():
    """中文文本应返回正整数 token 数。"""
    n = count_tokens("你好，世界")
    assert n > 0


def test_count_tokens_empty():
    """空文本返回 0。"""
    assert count_tokens("") == 0
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd backend && uv run pytest tests/test_token_count.py -v`
预期：FAIL，报错 `ModuleNotFoundError: No module named 'app.utils.token_count'`

- [ ] **步骤 3：编写实现**

创建 `backend/app/utils/token_count.py`：

```python
"""DeepSeek 离线 tokenizer 封装。

使用本地 tokenizer.json 计算 token 数，零网络、零 API 成本。
tokenizer 单例懒加载；加载失败时降级为启发式估算。
"""

from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger("openlink.token")

# tokenizer.json 路径（与本文件同级的 deepseek_tokenizer 目录）
_TOKENIZER_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "deepseek_tokenizer",
    "tokenizer.json",
)

_tokenizer = None
_lock = threading.Lock()
_load_failed = False


def _get_tokenizer():
    """懒加载 tokenizer 单例；失败返回 None。"""
    global _tokenizer, _load_failed
    if _tokenizer is not None or _load_failed:
        return _tokenizer
    with _lock:
        if _tokenizer is not None or _load_failed:
            return _tokenizer
        try:
            from tokenizers import Tokenizer
            _tokenizer = Tokenizer.from_file(_TOKENIZER_PATH)
        except Exception as exc:
            logger.warning("tokenizer 加载失败，降级为启发式估算: %s", exc)
            _load_failed = True
    return _tokenizer


def _heuristic_count(text: str) -> int:
    """启发式估算：中文按字符、英文按空白分词。"""
    if not text:
        return 0
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    non_cjk = "".join(ch for ch in text if not ("\u4e00" <= ch <= "\u9fff"))
    words = len(non_cjk.split())
    return cjk + words


def count_tokens(text: str) -> int:
    """计算文本的 token 数。

    参数：
    text (str): 待计数文本

    返回：
    int: token 数；空文本返回 0
    """
    if not text:
        return 0
    tk = _get_tokenizer()
    if tk is None:
        return _heuristic_count(text)
    try:
        return len(tk.encode(text).ids)
    except Exception as exc:
        logger.warning("token 计数失败，降级估算: %s", exc)
        return _heuristic_count(text)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd backend && uv run pytest tests/test_token_count.py -v`
预期：PASS（3 个测试）

- [ ] **步骤 5：Commit**

```bash
git add backend/app/utils/token_count.py backend/tests/test_token_count.py
git commit -m "feat(backend): 新增 DeepSeek 离线 token 计数工具"
```

---

## 任务 2：JSONL 对话存储

**文件：**
- 创建：`backend/app/core/conversations/__init__.py`
- 创建：`backend/app/core/conversations/store.py`
- 测试：`backend/tests/test_conversation_store.py`

- [ ] **步骤 1：编写失败的测试**

创建 `backend/tests/test_conversation_store.py`：

```python
import sys
sys.stdout.reconfigure(encoding="utf-8")

import json
import os
import tempfile

from app.core.conversations.store import append_record, read_records


def test_append_and_read():
    """追加一条记录后应能读回。"""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "conv.jsonl")
        append_record(
            {
                "ts": 1000,
                "platform": "chat.deepseek.com",
                "convId": "abc",
                "user": "hi",
                "assistant": "hello",
                "inputTokens": 1,
                "outputTokens": 1,
            },
            path=path,
        )
        recs = read_records(path=path)
        assert len(recs) == 1
        assert recs[0]["user"] == "hi"


def test_read_missing_file():
    """文件不存在时返回空列表。"""
    assert read_records(path="/nonexistent/path/x.jsonl") == []
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd backend && uv run pytest tests/test_conversation_store.py -v`
预期：FAIL，`ModuleNotFoundError: No module named 'app.core.conversations'`

- [ ] **步骤 3：编写实现**

创建 `backend/app/core/conversations/__init__.py`（空文件）。

创建 `backend/app/core/conversations/store.py`：

```python
"""对话记录的 JSONL 持久化。

存储位置默认 ~/.openlink/conversations.jsonl，一行一条 JSON。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("openlink.conversations")


def _default_path() -> str:
    """默认存储路径：~/.openlink/conversations.jsonl。"""
    return os.path.join(os.path.expanduser("~"), ".openlink", "conversations.jsonl")


def append_record(record: dict[str, Any], path: str | None = None) -> None:
    """追加一条记录到 JSONL 文件。

    参数：
    record (dict): 对话记录
    path (str|None): 存储路径；默认 ~/.openlink/conversations.jsonl
    """
    p = path or _default_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_records(path: str | None = None) -> list[dict[str, Any]]:
    """读取全部记录；文件不存在返回空列表。

    参数：
    path (str|None): 存储路径；默认 ~/.openlink/conversations.jsonl

    返回：
    list[dict]: 记录列表（按写入顺序）
    """
    p = path or _default_path()
    if not os.path.isfile(p):
        return []
    out: list[dict[str, Any]] = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("跳过损坏的 JSONL 行: %s", line[:80])
    return out
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd backend && uv run pytest tests/test_conversation_store.py -v`
预期：PASS（2 个测试）

- [ ] **步骤 5：Commit**

```bash
git add backend/app/core/conversations/
git add backend/tests/test_conversation_store.py
git commit -m "feat(backend): 新增对话记录 JSONL 存储"
```

---

## 任务 3：对话 API 端点

**文件：**
- 修改：`backend/app/schemas/types.py`（追加模型）
- 创建：`backend/app/api/endpoints/conversations.py`
- 修改：`backend/app/api/router.py`
- 测试：`backend/tests/test_conversations_api.py`

- [ ] **步骤 1：在 types.py 追加模型**

在 `backend/app/schemas/types.py` 末尾追加：

```python
class ConversationIn(BaseModel):
    """扩展上报的一条对话记录（未含 token）。"""
    platform: str
    convId: Optional[str] = None
    user: str = ""
    assistant: str = ""


class ConversationAck(BaseModel):
    """POST /conversations 响应。"""
    status: str = "ok"
    inputTokens: int = 0
    outputTokens: int = 0


class SummaryStats(BaseModel):
    """汇总统计。"""
    count: int = 0
    inputTokens: int = 0
    outputTokens: int = 0
    totalTokens: int = 0


class DayStat(BaseModel):
    """按天统计。"""
    date: str
    inputTokens: int = 0
    outputTokens: int = 0


class PlatformStat(BaseModel):
    """按平台统计。"""
    platform: str
    count: int = 0
    tokens: int = 0


class RecentItem(BaseModel):
    """最近对话条目。"""
    ts: int
    platform: str
    user: str = ""
    inputTokens: int = 0
    outputTokens: int = 0


class StatsResponse(BaseModel):
    """GET /stats 响应。"""
    summary: SummaryStats
    byDay: list[DayStat] = []
    byPlatform: list[PlatformStat] = []
    recent: list[RecentItem] = []
```

- [ ] **步骤 2：编写失败的测试**

创建 `backend/tests/test_conversations_api.py`：

```python
import sys
sys.stdout.reconfigure(encoding="utf-8")

import json
import os
import tempfile

from fastapi.testclient import TestClient

from app.main import app
from app.core.conversations import store

client = TestClient(app, raise_server_exceptions=False)


def _token():
    return json.load(open(os.path.expanduser("~/.openlink/settings.json")))["token"]


def test_post_and_stats(monkeypatch):
    """POST 一条记录后 GET /stats 应反映其 token。"""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "conv.jsonl")
        monkeypatch.setattr(store, "_default_path", lambda: path)

        headers = {"Authorization": f"Bearer {_token()}"}
        r = client.post(
            "/conversations",
            json={"platform": "chat.deepseek.com", "user": "你好", "assistant": "你好呀"},
            headers=headers,
        )
        assert r.status_code == 200
        ack = r.json()
        assert ack["status"] == "ok"
        assert ack["inputTokens"] > 0

        s = client.get("/stats", headers=headers)
        assert s.status_code == 200
        data = s.json()
        assert data["summary"]["count"] == 1
        assert data["summary"]["totalTokens"] > 0
```

- [ ] **步骤 3：运行测试验证失败**

运行：`cd backend && uv run pytest tests/test_conversations_api.py -v`
预期：FAIL，404（`/conversations` 不存在）

- [ ] **步骤 4：编写端点实现**

创建 `backend/app/api/endpoints/conversations.py`：

```python
"""POST /conversations + GET /stats — 对话记录与 token 统计。"""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import APIRouter

from app.api.deps import auth_required
from app.core.conversations import store
from app.schemas.types import (
    ConversationIn,
    ConversationAck,
    StatsResponse,
    SummaryStats,
    DayStat,
    PlatformStat,
    RecentItem,
)
from app.utils.token_count import count_tokens

logger = logging.getLogger("openlink.conversations")

router = APIRouter(dependencies=[auth_required])


@router.post("/conversations", response_model=ConversationAck)
async def add_conversation(req: ConversationIn):
    """接收一条对话记录，计算 token 并持久化。"""
    it = count_tokens(req.user)
    ot = count_tokens(req.assistant)
    record = {
        "ts": int(time.time() * 1000),
        "platform": req.platform,
        "convId": req.convId,
        "user": req.user,
        "assistant": req.assistant,
        "inputTokens": it,
        "outputTokens": ot,
    }
    try:
        store.append_record(record)
    except Exception as exc:
        logger.exception("写入对话记录失败: %s", exc)
        return ConversationAck(status="error", inputTokens=it, outputTokens=ot)
    return ConversationAck(status="ok", inputTokens=it, outputTokens=ot)


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """聚合全部对话记录，返回统计。"""
    records = store.read_records()

    summary = SummaryStats()
    by_day: dict[str, DayStat] = {}
    by_platform: dict[str, PlatformStat] = {}

    for r in records:
        it = int(r.get("inputTokens", 0))
        ot = int(r.get("outputTokens", 0))
        summary.count += 1
        summary.inputTokens += it
        summary.outputTokens += ot

        ts = int(r.get("ts", 0))
        date = time.strftime("%Y-%m-%d", time.localtime(ts / 1000)) if ts else "unknown"
        d = by_day.setdefault(date, DayStat(date=date))
        d.inputTokens += it
        d.outputTokens += ot

        plat = r.get("platform", "unknown")
        p = by_platform.setdefault(plat, PlatformStat(platform=plat))
        p.count += 1
        p.tokens += it + ot

    summary.totalTokens = summary.inputTokens + summary.outputTokens

    recent = [
        RecentItem(
            ts=int(r.get("ts", 0)),
            platform=r.get("platform", ""),
            user=(r.get("user", "") or "")[:100],
            inputTokens=int(r.get("inputTokens", 0)),
            outputTokens=int(r.get("outputTokens", 0)),
        )
        for r in records[-100:][::-1]
    ]

    return StatsResponse(
        summary=summary,
        byDay=sorted(by_day.values(), key=lambda x: x.date),
        byPlatform=sorted(by_platform.values(), key=lambda x: x.tokens, reverse=True),
        recent=recent,
    )
```

- [ ] **步骤 5：挂载路由**

修改 `backend/app/api/router.py`，在 imports 加：

```python
from app.api.endpoints.conversations import router as conversations_router
```

在 `api_router.include_router(...)` 列表末尾加：

```python
api_router.include_router(conversations_router)
```

- [ ] **步骤 6：运行测试验证通过**

运行：`cd backend && uv run pytest tests/test_conversations_api.py -v`
预期：PASS

- [ ] **步骤 7：Commit**

```bash
git add backend/app/schemas/types.py backend/app/api/endpoints/conversations.py backend/app/api/router.py backend/tests/test_conversations_api.py
git commit -m "feat(backend): 新增对话记录与统计 API"
```

---

## 任务 4：前端类型与 API 封装

**文件：**
- 修改：`frontend/src/types/index.ts`
- 修改：`frontend/src/api/endpoints.ts`

- [ ] **步骤 1：追加类型**

在 `frontend/src/types/index.ts` 末尾追加：

```typescript
export interface SummaryStats {
  count: number
  inputTokens: number
  outputTokens: number
  totalTokens: number
}

export interface DayStat {
  date: string
  inputTokens: number
  outputTokens: number
}

export interface PlatformStat {
  platform: string
  count: number
  tokens: number
}

export interface RecentItem {
  ts: number
  platform: string
  user: string
  inputTokens: number
  outputTokens: number
}

export interface StatsResponse {
  summary: SummaryStats
  byDay: DayStat[]
  byPlatform: PlatformStat[]
  recent: RecentItem[]
}
```

- [ ] **步骤 2：追加 API 函数**

在 `frontend/src/api/endpoints.ts` 中，import 类型处加 `StatsResponse`，并在文件末尾（`export default api` 之前）加：

```typescript
export async function fetchStats(): Promise<StatsResponse> {
  const { data } = await api.get<StatsResponse>('/stats')
  return data
}
```

- [ ] **步骤 3：类型检查**

运行：`cd frontend && npx vue-tsc --noEmit`
预期：无新增错误

- [ ] **步骤 4：Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/endpoints.ts
git commit -m "feat(frontend): 新增统计 API 类型与封装"
```

---

## 任务 5：前端 Pinia store

**文件：**
- 创建：`frontend/src/stores/analytics.ts`

- [ ] **步骤 1：编写 store**

创建 `frontend/src/stores/analytics.ts`：

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { StatsResponse } from '@/types'
import { fetchStats } from '@/api/endpoints'

export const useAnalyticsStore = defineStore('analytics', () => {
  const stats = ref<StatsResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load() {
    loading.value = true
    error.value = null
    try {
      stats.value = await fetchStats()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  return { stats, loading, error, load }
})
```

- [ ] **步骤 2：类型检查**

运行：`cd frontend && npx vue-tsc --noEmit`
预期：无新增错误

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/stores/analytics.ts
git commit -m "feat(frontend): 新增 analytics store"
```

---

## 任务 6：Analytics 页面

**文件：**
- 创建：`frontend/src/pages/Analytics.vue`

- [ ] **步骤 1：编写页面**

创建 `frontend/src/pages/Analytics.vue`：

```vue
<template>
  <div class="analytics">
    <h1>对话统计</h1>

    <div v-if="store.loading" class="hint">加载中…</div>
    <div v-else-if="store.error" class="hint err">{{ store.error }}</div>

    <template v-else-if="store.stats">
      <div class="cards">
        <div class="card"><div class="num">{{ store.stats.summary.count }}</div><div class="lbl">对话总数</div></div>
        <div class="card"><div class="num">{{ fmt(store.stats.summary.inputTokens) }}</div><div class="lbl">输入 tokens</div></div>
        <div class="card"><div class="num">{{ fmt(store.stats.summary.outputTokens) }}</div><div class="lbl">输出 tokens</div></div>
        <div class="card"><div class="num">{{ fmt(store.stats.summary.totalTokens) }}</div><div class="lbl">总 tokens</div></div>
      </div>

      <h2>每日趋势</h2>
      <div class="chart">
        <svg :viewBox="`0 0 ${chartW} ${chartH}`" preserveAspectRatio="none" class="svg">
          <polyline :points="inPoints" class="line in" />
          <polyline :points="outPoints" class="line out" />
        </svg>
        <div class="legend">
          <span class="dot in"></span>输入
          <span class="dot out"></span>输出
        </div>
      </div>

      <h2>平台分布</h2>
      <div class="bars">
        <div v-for="p in store.stats.byPlatform" :key="p.platform" class="bar-row">
          <span class="bar-label">{{ p.platform }}</span>
          <div class="bar-track"><div class="bar-fill" :style="{ width: barWidth(p.tokens) }"></div></div>
          <span class="bar-val">{{ fmt(p.tokens) }}</span>
        </div>
      </div>

      <h2>最近对话</h2>
      <table class="tbl">
        <thead><tr><th>时间</th><th>平台</th><th>消息</th><th>输入</th><th>输出</th></tr></thead>
        <tbody>
          <tr v-for="(r, i) in store.stats.recent" :key="i">
            <td>{{ time(r.ts) }}</td>
            <td>{{ r.platform }}</td>
            <td class="msg">{{ r.user }}</td>
            <td>{{ r.inputTokens }}</td>
            <td>{{ r.outputTokens }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useAnalyticsStore } from '@/stores/analytics'

const store = useAnalyticsStore()

onMounted(() => store.load())

const chartW = 800
const chartH = 160

function fmt(n: number): string {
  return n.toLocaleString()
}

function time(ts: number): string {
  if (!ts) return '-'
  return new Date(ts).toLocaleString()
}

const maxDay = computed(() => {
  const days = store.stats?.byDay ?? []
  let m = 1
  for (const d of days) m = Math.max(m, d.inputTokens, d.outputTokens)
  return m
})

function points(key: 'inputTokens' | 'outputTokens'): string {
  const days = store.stats?.byDay ?? []
  if (days.length === 0) return ''
  const step = days.length > 1 ? chartW / (days.length - 1) : 0
  return days
    .map((d, i) => {
      const x = i * step
      const y = chartH - (d[key] / maxDay.value) * (chartH - 10) - 5
      return `${x},${y}`
    })
    .join(' ')
}

const inPoints = computed(() => points('inputTokens'))
const outPoints = computed(() => points('outputTokens'))

const maxPlatform = computed(() => {
  const ps = store.stats?.byPlatform ?? []
  let m = 1
  for (const p of ps) m = Math.max(m, p.tokens)
  return m
})

function barWidth(tokens: number): string {
  return `${(tokens / maxPlatform.value) * 100}%`
}
</script>

<style scoped>
.analytics { max-width: 960px; }
h1 { margin-bottom: 20px; }
h2 { margin: 28px 0 12px; font-size: 16px; color: var(--color-muted); }
.hint { color: var(--color-muted); padding: 20px 0; }
.hint.err { color: var(--color-danger); }
.cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.card {
  background: var(--color-surface); border: 1px solid var(--color-border);
  border-radius: 10px; padding: 16px; text-align: center;
}
.card .num { font-size: 24px; font-weight: 700; color: var(--color-accent); }
.card .lbl { font-size: 12px; color: var(--color-muted); margin-top: 4px; }
.chart { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 10px; padding: 12px; }
.svg { width: 100%; height: 160px; }
.line { fill: none; stroke-width: 2; }
.line.in { stroke: var(--color-accent); }
.line.out { stroke: var(--color-success); }
.legend { display: flex; gap: 16px; font-size: 12px; color: var(--color-muted); margin-top: 8px; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; }
.dot.in { background: var(--color-accent); }
.dot.out { background: var(--color-success); }
.bars { display: flex; flex-direction: column; gap: 8px; }
.bar-row { display: flex; align-items: center; gap: 10px; font-size: 13px; }
.bar-label { width: 180px; color: var(--color-muted); }
.bar-track { flex: 1; background: var(--color-surface); border-radius: 4px; height: 16px; overflow: hidden; }
.bar-fill { height: 100%; background: var(--color-accent); }
.bar-val { width: 80px; text-align: right; }
.tbl { width: 100%; border-collapse: collapse; font-size: 13px; }
.tbl th, .tbl td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--color-border); }
.tbl th { color: var(--color-muted); font-weight: 500; }
.tbl .msg { max-width: 360px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
```

- [ ] **步骤 2：类型检查**

运行：`cd frontend && npx vue-tsc --noEmit`
预期：无新增错误

- [ ] **步骤 3：Commit**

```bash
git add frontend/src/pages/Analytics.vue
git commit -m "feat(frontend): 新增对话统计页面"
```

---

## 任务 7：路由与侧边栏入口

**文件：**
- 修改：`frontend/src/router/index.ts`
- 修改：`frontend/src/components/Layout.vue`

- [ ] **步骤 1：加路由**

在 `frontend/src/router/index.ts` 的 routes 数组中，`/prompt` 之后加：

```typescript
    {
      path: '/analytics',
      name: 'Analytics',
      component: () => import('@/pages/Analytics.vue'),
    },
```

- [ ] **步骤 2：加侧边栏入口**

在 `frontend/src/components/Layout.vue` 的 `navItems` 中，`提示词` 之后加：

```typescript
  { to: '/analytics', label: '对话统计', icon: '📈' },
```

- [ ] **步骤 3：类型检查 + 构建**

运行：`cd frontend && npx vue-tsc --noEmit && npx vite build`
预期：typecheck 无新增错误；build 成功

- [ ] **步骤 4：Commit**

```bash
git add frontend/src/router/index.ts frontend/src/components/Layout.vue
git commit -m "feat(frontend): 挂载对话统计路由与侧边栏入口"
```

---

## 任务 8：扩展抓取并上报对话

**文件：**
- 修改：`extension/src/content/index.ts`

- [ ] **步骤 1：新增上报函数**

在 `extension/src/content/index.ts` 中（`executeToolCall` 附近）加：

```typescript
/** 上报一轮对话（user + assistant）到后端。失败静默。 */
async function reportConversation(userText: string, assistantText: string): Promise<void> {
  if (!userText || !assistantText) return;
  try {
    const { authToken, apiUrl } = await chrome.storage.local.get(['authToken', 'apiUrl']);
    if (!apiUrl) return;
    const headers: any = { 'Content-Type': 'application/json' };
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    const convId = getConversationId();
    await bgFetch(`${apiUrl}/conversations`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        platform: location.hostname,
        convId,
        user: userText.slice(0, 20000),
        assistant: assistantText.slice(0, 20000),
      }),
    });
  } catch (e) {
    console.warn('[OpenLink] 对话上报失败:', e);
  }
}
```

- [ ] **步骤 2：在 AI 回复完成时触发上报**

在 DeepSeek 回复完成的检测点（复用现有 DOM observer 对 AI 回复容器的扫描），当检测到一轮 AI 回复完成时，抓取该轮的 user 消息和 assistant 回复，调用 `reportConversation`。

DeepSeek 抓取逻辑：AI 回复容器为 `div.ds-markdown`；其对应的用户消息为 DOM 中该 `ds-markdown` 之前最近的用户消息块（选择器待实测）。为避免重复上报，用一个 `Set<string>`（按 `convId + 文本 hash`）去重。

- [ ] **步骤 3：构建**

运行：`cd extension && npx vite build`
预期：build 成功

- [ ] **步骤 4：Commit**

```bash
git add extension/src/content/index.ts
git commit -m "feat(extension): 抓取并上报 DeepSeek 对话"
```

---

## 任务 9：端到端验证

- [ ] **步骤 1：重启后端**

```bash
cd backend && uv run python -m app.main -dir <workspace> -port 39527
```

- [ ] **步骤 2：手动 POST 验证**

```bash
cd backend && uv run python -c "import sys,json,os,urllib.request; sys.stdout.reconfigure(encoding='utf-8'); tok=json.load(open(os.path.expanduser('~/.openlink/settings.json')))['token']; req=urllib.request.Request('http://127.0.0.1:39527/conversations', data=json.dumps({'platform':'chat.deepseek.com','user':'你好','assistant':'你好呀'}).encode(), headers={'Content-Type':'application/json','Authorization':'Bearer '+tok}); print(urllib.request.urlopen(req).read().decode())"
```

预期：返回 `{"status":"ok","inputTokens":...}`

- [ ] **步骤 3：验证 stats**

浏览器打开 `http://127.0.0.1:39527/app/analytics`，确认卡片/图表/表格显示数据。

- [ ] **步骤 4：验证扩展上报**

在 DeepSeek 页面发一轮对话，确认 `~/.openlink/conversations.jsonl` 新增一行，Analytics 页面出现该条。
