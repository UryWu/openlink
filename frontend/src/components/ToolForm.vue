<template>
  <div class="tool-form">
    <h2>{{ tool.name }}</h2>
    <p class="desc">{{ tool.description }}</p>

    <div class="args-editor">
      <label>Arguments (JSON)</label>
      <textarea
        v-model="argsText"
        class="json-input"
        rows="6"
        placeholder='{"filePath": "example.txt"}'
        spellcheck="false"
      />
      <div v-if="parseError" class="parse-error">{{ parseError }}</div>
    </div>

    <button class="btn-execute" :disabled="executing || !valid" @click="submit">
      {{ executing ? '执行中…' : '▶ 执行' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { ToolInfo, ToolRequest } from '@/types'

const props = defineProps<{
  tool: ToolInfo
  executing: boolean
}>()

const emit = defineEmits<{
  execute: [req: ToolRequest]
}>()

const argsText = ref('{}')
const parseError = ref('')

const valid = computed(() => {
  try {
    JSON.parse(argsText.value)
    parseError.value = ''
    return true
  } catch (e: unknown) {
    parseError.value = e instanceof Error ? e.message : 'JSON 格式错误'
    return false
  }
})

function submit() {
  if (!valid.value) return
  const args = JSON.parse(argsText.value)
  emit('execute', { name: props.tool.name, args })
}
</script>

<style scoped>
.tool-form {
  margin-bottom: 16px;
}

.tool-form h2 {
  font-size: 16px;
  color: var(--color-accent);
  font-family: monospace;
  margin-bottom: 4px;
}

.desc {
  font-size: 13px;
  color: var(--color-muted);
  margin-bottom: 16px;
}

.args-editor label {
  display: block;
  font-size: 13px;
  color: var(--color-muted);
  margin-bottom: 4px;
}

.json-input {
  width: 100%;
  padding: 10px 12px;
  background: var(--color-bg);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-family: 'Cascadia Code', 'Fira Code', monospace;
  font-size: 13px;
  resize: vertical;
  outline: none;
}

.json-input:focus { border-color: var(--color-accent); }

.parse-error {
  font-size: 12px;
  color: var(--color-danger);
  margin-top: 4px;
}

.btn-execute {
  margin-top: 12px;
  padding: 10px 24px;
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.btn-execute:hover { opacity: 0.9; }
.btn-execute:disabled { opacity: 0.5; cursor: default; }
</style>
