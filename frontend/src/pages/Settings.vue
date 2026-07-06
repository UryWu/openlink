<template>
  <div class="settings">
    <h1 class="page-title">设置</h1>

    <div class="card">
      <h2>自动执行</h2>
      <label class="toggle-row">
        <span>启用自动执行（检测到工具调用时自动运行）</span>
        <input type="checkbox" v-model="autoExecute" />
      </label>
      <p class="hint">当启用时，AI 页面检测到的工具调用将自动发送到后端执行。</p>
    </div>

    <div class="card">
      <h2>自动发送</h2>
      <label class="toggle-row">
        <span>启用自动发送（执行结果自动填充回 AI 输入框）</span>
        <input type="checkbox" v-model="autoSend" />
      </label>
      <p class="hint">结果将通过浏览器扩展自动回填到 AI 编辑器中。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const autoExecute = ref(localStorage.getItem('openlink-auto-execute') === 'true')
const autoSend = ref(localStorage.getItem('openlink-auto-send') === 'true')

// Persist to localStorage on change
import { watch } from 'vue'

watch(autoExecute, (v) => localStorage.setItem('openlink-auto-execute', String(v)))
watch(autoSend, (v) => localStorage.setItem('openlink-auto-send', String(v)))
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 600; margin-bottom: 24px; }

.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 16px;
  max-width: 560px;
}

.card h2 {
  font-size: 15px;
  margin-bottom: 12px;
}

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  cursor: pointer;
}

.toggle-row input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: var(--color-accent);
  cursor: pointer;
}

.hint {
  font-size: 12px;
  color: var(--color-muted);
  margin-top: 8px;
  line-height: 1.5;
}
</style>
