<template>
  <div class="analytics">
    <h1>对话统计</h1>

    <div class="toolbar">
      <label class="sel-label">会话：</label>
      <select class="sel" :value="store.selectedConvId" @change="onSelect(($event.target as HTMLSelectElement).value)">
        <option value="">全部会话</option>
        <option v-for="c in store.conversations" :key="c.convId" :value="c.convId">
          {{ c.convId.slice(0, 8) }} · {{ c.count }}轮 · {{ fmt(c.totalTokens) }} tok
        </option>
      </select>
      <button
        v-if="store.selectedConvId"
        class="del-btn"
        @click="onDelete(store.selectedConvId)">删除此会话</button>
      <template v-if="store.selectedConvId">
        <input class="name-input" v-model="exportName" placeholder="导出文件名（默认会话ID.md）" />
        <button class="exp-btn" @click="onExport(store.selectedConvId)">导出 MD</button>
      </template>
    </div>

    <div v-if="store.loading" class="hint">加载中…</div>
    <div v-else-if="store.error" class="hint err">{{ store.error }}</div>

    <template v-else-if="store.stats">
      <div class="cards">
        <div class="card"><div class="num">{{ store.stats.summary.count }}</div><div class="lbl">对话总数</div></div>
        <div class="card"><div class="num">{{ fmt(store.stats.summary.inputTokens) }}</div><div class="lbl">输入 tokens</div></div>
        <div class="card"><div class="num">{{ fmt(store.stats.summary.outputTokens) }}</div><div class="lbl">输出 tokens</div></div>
        <div class="card"><div class="num">{{ fmt(store.stats.summary.totalTokens) }}</div><div class="lbl">总 tokens</div></div>
      </div>

      <h2>平台分布</h2>
      <div class="bars">
        <div v-for="p in store.stats.byPlatform" :key="p.platform" class="bar-row">
          <span class="bar-label">{{ p.platform }}</span>
          <div class="bar-track"><div class="bar-fill" :style="{ width: barWidth(p.tokens) }"></div></div>
          <span class="bar-val">{{ fmt(p.tokens) }}</span>
        </div>
      </div>

      <h2>每日趋势</h2>
      <div class="chart">
        <svg :viewBox="`0 0 ${chartW} ${chartH}`" class="svg">
          <g v-for="t in yTicks" :key="'y' + t.value">
            <line :x1="padL" :y1="t.y" :x2="chartW - padR" :y2="t.y" class="grid" />
            <text :x="padL - 8" :y="t.y + 4" class="axis-text" text-anchor="end">{{ fmt(t.value) }}</text>
          </g>

          <line :x1="padL" :y1="plotH" :x2="chartW - padR" :y2="plotH" class="axis" />

          <polyline v-if="inPoints" :points="inPoints" class="line in" />
          <polyline v-if="outPoints" :points="outPoints" class="line out" />
          <polyline v-if="totalPoints" :points="totalPoints" class="line total" />

          <circle
            v-for="(p, i) in allDots" :key="'all' + i"
            :cx="p.x" :cy="p.yIn" r="3.5" class="dot in"
            @mouseenter="hover = { x: p.x, y: p.yIn, date: p.date, input: p.input, output: p.output, total: p.total }"
            @mouseleave="hover = null" />
          <circle
            v-for="(p, i) in allDots" :key="'allo' + i"
            :cx="p.x" :cy="p.yOut" r="3.5" class="dot out"
            @mouseenter="hover = { x: p.x, y: p.yOut, date: p.date, input: p.input, output: p.output, total: p.total }"
            @mouseleave="hover = null" />
          <circle
            v-for="(p, i) in allDots" :key="'alt' + i"
            :cx="p.x" :cy="p.yTotal" r="3.5" class="dot total"
            @mouseenter="hover = { x: p.x, y: p.yTotal, date: p.date, input: p.input, output: p.output, total: p.total }"
            @mouseleave="hover = null" />

          <g v-if="hover" :transform="`translate(${tooltipX}, ${tooltipY})`" class="tooltip">
            <rect x="0" :y="tipAbove ? -74 : 14" :width="tooltipW" height="72" rx="6" class="tip-bg" />
            <text x="10" :y="tipAbove ? -56 : 32" class="tip-title">{{ hover.date }}</text>
            <text x="10" :y="tipAbove ? -40 : 48" class="tip-line">输入: {{ fmt(hover.input) }}</text>
            <text x="10" :y="tipAbove ? -24 : 64" class="tip-line">输出: {{ fmt(hover.output) }}</text>
            <text x="10" :y="tipAbove ? -8 : 80" class="tip-line tip-total">总计: {{ fmt(hover.total) }}</text>
          </g>

          <text v-for="(p, i) in xLabels" :key="'x' + i" :x="p.x" :y="plotH + 16" class="axis-text" text-anchor="middle">{{ p.label }}</text>
        </svg>
        <div class="legend">
          <span class="dot in"></span>输入
          <span class="dot out"></span>输出
          <span class="dot total"></span>总计
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
import { computed, onMounted, ref } from 'vue'
import { useAnalyticsStore } from '@/stores/analytics'

const store = useAnalyticsStore()

onMounted(() => store.init())

function onSelect(convId: string) {
  store.select(convId)
}

async function onDelete(convId: string) {
  if (confirm('确定删除此会话的所有记录？')) {
    await store.remove(convId)
  }
}

const exportName = ref('')

async function onExport(convId: string) {
  await store.exportMd(convId, exportName.value)
}

const chartW = 860
const chartH = 240
const padL = 56
const padR = 16
const padT = 16
const padB = 34
const plotW = chartW - padL - padR
const plotH = chartH - padB

function fmt(n: number): string {
  return n.toLocaleString()
}

function time(ts: number): string {
  if (!ts) return '-'
  return new Date(ts).toLocaleString()
}

const days = computed(() => store.stats?.byDay ?? [])

const maxVal = computed(() => {
  let m = 1
  for (const d of days.value) m = Math.max(m, d.inputTokens, d.outputTokens, d.inputTokens + d.outputTokens)
  return m
})

const yTicks = computed(() => {
  const m = maxVal.value
  const vals = [0, Math.round(m / 2), m]
  return vals.map(v => ({
    value: v,
    y: padT + (1 - v / m) * (plotH - padT),
  }))
})

function xAt(i: number, n: number): number {
  if (n <= 1) return padL + plotW / 2
  return padL + (i / (n - 1)) * plotW
}

function yAt(v: number): number {
  return padT + (1 - v / maxVal.value) * (plotH - padT)
}

function valOf(d: { inputTokens: number; outputTokens: number }, key: 'inputTokens' | 'outputTokens' | 'total'): number {
  return key === 'total' ? d.inputTokens + d.outputTokens : d[key]
}

function points(key: 'inputTokens' | 'outputTokens' | 'total'): string {
  const ds = days.value
  if (ds.length === 0) return ''
  return ds.map((d, i) => `${xAt(i, ds.length)},${yAt(valOf(d, key))}`).join(' ')
}

const allDots = computed(() => {
  const ds = days.value
  return ds.map((d, i) => ({
    x: xAt(i, ds.length),
    yIn: yAt(d.inputTokens),
    yOut: yAt(d.outputTokens),
    yTotal: yAt(d.inputTokens + d.outputTokens),
    input: d.inputTokens,
    output: d.outputTokens,
    total: d.inputTokens + d.outputTokens,
    date: d.date,
  }))
})

const inPoints = computed(() => points('inputTokens'))
const outPoints = computed(() => points('outputTokens'))
const totalPoints = computed(() => points('total'))

const hover = ref<{ x: number; y: number; date: string; input: number; output: number; total: number } | null>(null)
const tooltipW = 140
const tooltipX = computed(() => {
  if (!hover.value) return 0
  const x = hover.value.x - tooltipW / 2
  return Math.max(padL, Math.min(chartW - padR - tooltipW, x))
})
const tipAbove = computed(() => !hover.value || hover.value.y > 90)
const tooltipY = computed(() => (hover.value ? hover.value.y : 0))

const xLabels = computed(() => {
  const ds = days.value
  const n = ds.length
  if (n === 0) return []
  const step = n > 8 ? Math.ceil(n / 8) : 1
  const out: { x: number; label: string }[] = []
  for (let i = 0; i < n; i += step) {
    out.push({ x: xAt(i, n), label: ds[i].date.slice(5) })
  }
  if (out.length && out[out.length - 1].label !== ds[n - 1].date.slice(5)) {
    out.push({ x: xAt(n - 1, n), label: ds[n - 1].date.slice(5) })
  }
  return out
})

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
.toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.sel-label { font-size: 13px; color: var(--color-muted); }
.sel {
  background: var(--color-surface); color: var(--color-text);
  border: 1px solid var(--color-border); border-radius: 6px;
  padding: 6px 10px; font-size: 13px; max-width: 360px;
}
.del-btn {
  background: transparent; color: var(--color-danger);
  border: 1px solid var(--color-danger); border-radius: 6px;
  padding: 6px 12px; font-size: 13px; cursor: pointer;
}
.del-btn:hover { background: rgba(248,113,113,0.1); }
.name-input {
  background: var(--color-surface); color: var(--color-text);
  border: 1px solid var(--color-border); border-radius: 6px;
  padding: 6px 10px; font-size: 13px; width: 220px;
}
.exp-btn {
  background: transparent; color: var(--color-accent);
  border: 1px solid var(--color-accent); border-radius: 6px;
  padding: 6px 12px; font-size: 13px; cursor: pointer;
}
.exp-btn:hover { background: rgba(108,138,255,0.1); }
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
.svg { width: 100%; height: auto; display: block; }
.grid { stroke: var(--color-border); stroke-width: 1; stroke-dasharray: 3 3; }
.axis { stroke: var(--color-border); stroke-width: 1; }
.axis-text { fill: var(--color-muted); font-size: 11px; }
.line { fill: none; stroke-width: 2; }
.line.in { stroke: var(--color-accent); }
.line.out { stroke: var(--color-success); }
.line.total { stroke: var(--color-warning); stroke-dasharray: 5 3; }
.dot { stroke-width: 0; cursor: pointer; }
.dot.in { fill: var(--color-accent); }
.dot.out { fill: var(--color-success); }
.dot.total { fill: var(--color-warning); }
.dot:hover { r: 5; }
.tooltip { pointer-events: none; }
.tip-bg { fill: var(--color-surface); stroke: var(--color-border); stroke-width: 1; opacity: 0.98; }
.tip-title { fill: var(--color-text); font-size: 11px; font-weight: 600; }
.tip-line { fill: var(--color-muted); font-size: 11px; }
.tip-total { fill: var(--color-warning); }
.legend { display: flex; gap: 16px; font-size: 12px; color: var(--color-muted); margin-top: 8px; }
.legend .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; }
.legend .dot.in { background: var(--color-accent); }
.legend .dot.out { background: var(--color-success); }
.legend .dot.total { background: var(--color-warning); }
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
