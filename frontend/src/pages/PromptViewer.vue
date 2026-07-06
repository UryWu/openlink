<template>
  <div class="prompt-viewer">
    <h1 class="page-title">提示词</h1>
    <div class="toolbar">
      <button class="btn-primary" @click="load" :disabled="loading">
        {{ loading ? '加载中…' : '从服务器获取' }}
      </button>
      <button v-if="content" class="btn-ghost" @click="copy">
        📋 复制
      </button>
    </div>

    <div v-if="error" class="error">{{ error }}</div>

    <pre v-if="content" class="prompt-body">{{ content }}</pre>
    <div v-else-if="!loading" class="empty">点击"从服务器获取"加载提示词</div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { fetchPrompt } from '@/api/endpoints'
import { useConnectionStore } from '@/stores/connection'

const connStore = useConnectionStore()
const content = ref('')
const error = ref('')
const loading = ref(false)

async function load() {
  if (!connStore.connected) {
    await connStore.checkHealth()
    if (!connStore.connected) {
      error.value = '无法连接服务器'
      return
    }
  }
  loading.value = true
  error.value = ''
  try {
    content.value = await fetchPrompt()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function copy() {
  try {
    await navigator.clipboard.writeText(content.value)
  } catch {
    // fallback
    const ta = document.createElement('textarea')
    ta.value = content.value
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
}
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 600; margin-bottom: 24px; }

.toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.btn-primary {
  padding: 8px 16px;
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}
.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.5; cursor: default; }

.btn-ghost {
  padding: 8px 16px;
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}

.error { color: var(--color-danger); font-size: 13px; margin-bottom: 12px; }
.empty { color: var(--color-muted); font-size: 14px; padding: 32px 0; }

.prompt-body {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 20px;
  font-size: 13px;
  font-family: 'Cascadia Code', 'Fira Code', monospace;
  white-space: pre-wrap;
  max-height: 70vh;
  overflow-y: auto;
  line-height: 1.7;
}
</style>
