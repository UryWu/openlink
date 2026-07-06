<template>
  <div class="file-browser">
    <h1 class="page-title">文件浏览器</h1>

    <div class="toolbar">
      <input
        v-model="query"
        class="input"
        placeholder="搜索文件名…"
        @keydown.enter="doSearch"
      />
      <button class="btn-primary" @click="doSearch" :disabled="loading">搜索</button>
    </div>

    <FileList :items="files" :loading="loading" @preview="previewFile" />

    <div v-if="previewContent !== null" class="preview">
      <div class="preview-header">
        <span class="preview-path">{{ previewPath }}</span>
        <button class="btn-ghost" @click="previewContent = null">✕</button>
      </div>
      <pre class="preview-body">{{ previewContent }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { FileItem } from '@/types'
import { fetchFiles, execTool } from '@/api/endpoints'
import { useConnectionStore } from '@/stores/connection'
import FileList from '@/components/FileList.vue'

const connStore = useConnectionStore()
const query = ref('')
const files = ref<FileItem[]>([])
const loading = ref(false)
const previewContent = ref<string | null>(null)
const previewPath = ref('')

async function doSearch() {
  if (!connStore.connected) return
  loading.value = true
  try {
    files.value = await fetchFiles(query.value || undefined)
  } catch {
    files.value = []
  } finally {
    loading.value = false
  }
}

async function previewFile(item: FileItem) {
  if (item.is_dir) return
  try {
    const res = await execTool({ name: 'read_file', args: { filePath: item.path } })
    previewContent.value = res.output
    previewPath.value = item.path
  } catch {
    previewContent.value = '(无法读取文件)'
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

.input {
  flex: 1;
  padding: 8px 12px;
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 14px;
  outline: none;
}

.input:focus { border-color: var(--color-accent); }

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

.preview {
  margin-top: 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  overflow: hidden;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: rgba(0,0,0,0.2);
}

.preview-path {
  font-size: 12px;
  color: var(--color-muted);
  font-family: monospace;
}

.btn-ghost {
  background: transparent;
  border: none;
  color: var(--color-muted);
  cursor: pointer;
  font-size: 16px;
}

.preview-body {
  padding: 16px;
  font-size: 13px;
  font-family: 'Cascadia Code', 'Fira Code', monospace;
  max-height: 500px;
  overflow: auto;
  white-space: pre-wrap;
}
</style>
