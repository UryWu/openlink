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
