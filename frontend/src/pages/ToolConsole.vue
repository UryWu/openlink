<template>
  <div class="tool-console">
    <h1 class="page-title">工具控制台</h1>

    <div class="layout">
      <div class="panel">
        <h2>选择工具</h2>
        <div class="tool-list">
          <button
            v-for="t in toolsStore.tools"
            :key="t.name"
            class="tool-btn"
            :class="{ active: selected === t.name }"
            @click="selectTool(t.name)"
          >
            {{ t.name }}
          </button>
        </div>

        <div v-if="selectedTool" class="tool-info">
          <p class="desc">{{ selectedTool.description }}</p>
        </div>
      </div>

      <div class="panel flex-2">
        <ToolForm
          v-if="selectedTool"
          :tool="selectedTool"
          :executing="toolsStore.executing"
          @execute="doExecute"
        />

        <div v-if="toolsStore.lastResult" class="result-section">
          <h2>执行结果</h2>
          <ToolResultCard :result="toolsStore.lastResult" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToolsStore } from '@/stores/tools'
import { useConnectionStore } from '@/stores/connection'
import type { ToolRequest } from '@/types'
import ToolForm from '@/components/ToolForm.vue'
import ToolResultCard from '@/components/ToolResultCard.vue'

const toolsStore = useToolsStore()
const connStore = useConnectionStore()
const selected = ref('')

const selectedTool = computed(() =>
  toolsStore.tools.find(t => t.name === selected.value) || null
)

function selectTool(name: string) {
  selected.value = name
  toolsStore.clearResult()
}

async function doExecute(req: ToolRequest) {
  if (!connStore.connected) {
    await connStore.checkHealth()
    if (!connStore.connected) return
  }
  await toolsStore.execute(req)
}

onMounted(() => { toolsStore.loadTools() })
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 600; margin-bottom: 24px; }

.layout {
  display: flex;
  gap: 24px;
}

.panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 20px;
  min-width: 200px;
}

.panel h2 {
  font-size: 14px;
  color: var(--color-muted);
  margin-bottom: 12px;
}

.flex-2 { flex: 2; }

.tool-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tool-btn {
  padding: 8px 12px;
  background: transparent;
  color: var(--color-text);
  border: none;
  border-radius: 6px;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  font-family: 'Cascadia Code', 'Fira Code', monospace;
}

.tool-btn:hover { background: rgba(255,255,255,0.04); }
.tool-btn.active { background: rgba(108,138,255,0.15); color: var(--color-accent); }

.tool-info { margin-top: 16px; }

.desc {
  font-size: 13px;
  color: var(--color-muted);
  line-height: 1.6;
}

.result-section { margin-top: 20px; }
.result-section h2 { font-size: 14px; color: var(--color-muted); margin-bottom: 12px; }
</style>
