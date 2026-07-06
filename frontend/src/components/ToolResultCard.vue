<template>
  <div class="result-card" :class="result.status">
    <div class="result-header">
      <span class="result-status">
        {{ result.status === 'success' ? '✅ 成功' : '❌ 失败' }}
      </span>
      <span v-if="result.stopStream" class="stop-badge">🛑 Stop</span>
    </div>

    <pre v-if="result.output" class="result-output">{{ result.output }}</pre>

    <div v-if="result.error" class="result-error">
      {{ result.error }}
    </div>

    <div v-if="!result.output && !result.error" class="result-empty">
      (无输出)
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ToolResponse } from '@/types'

defineProps<{
  result: ToolResponse
}>()
</script>

<style scoped>
.result-card {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 16px;
}

.result-card.success { border-left: 3px solid var(--color-success); }
.result-card.error { border-left: 3px solid var(--color-danger); }

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.result-status {
  font-size: 13px;
  font-weight: 600;
}

.stop-badge {
  font-size: 11px;
  padding: 1px 6px;
  background: rgba(251,191,36,0.15);
  color: var(--color-warning);
  border-radius: 3px;
}

.result-output {
  font-family: 'Cascadia Code', 'Fira Code', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  max-height: 400px;
  overflow-y: auto;
  line-height: 1.6;
  color: var(--color-text);
}

.result-error {
  font-size: 13px;
  color: var(--color-danger);
}

.result-empty {
  font-size: 13px;
  color: var(--color-muted);
  font-style: italic;
}
</style>
