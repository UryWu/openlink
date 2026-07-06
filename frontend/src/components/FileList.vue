<template>
  <div class="file-list-wrapper">
    <div v-if="loading" class="loading">搜索中…</div>

    <div v-else-if="items.length === 0" class="empty">
      暂无文件。输入关键词搜索。
    </div>

    <table v-else class="file-table">
      <thead>
        <tr>
          <th>名称</th>
          <th class="col-path">路径</th>
          <th class="col-size">大小</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="item in items"
          :key="item.path"
          class="file-row"
          :class="{ dir: item.is_dir }"
          @click="$emit('preview', item)"
        >
          <td>
            <span class="file-icon">{{ item.is_dir ? '📁' : '📄' }}</span>
            {{ item.name }}
          </td>
          <td class="col-path path">{{ item.path }}</td>
          <td class="col-size size">{{ item.is_dir ? '-' : formatSize(item.size) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import type { FileItem } from '@/types'

defineProps<{
  items: FileItem[]
  loading: boolean
}>()

defineEmits<{
  preview: [item: FileItem]
}>()

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1_048_576).toFixed(1)} MB`
}
</script>

<style scoped>
.loading, .empty {
  color: var(--color-muted);
  font-size: 14px;
  padding: 16px 0;
}

.file-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.file-table th {
  text-align: left;
  color: var(--color-muted);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 8px 12px;
  background: rgba(0,0,0,0.15);
}

.file-row {
  cursor: pointer;
  border-bottom: 1px solid var(--color-border);
}

.file-row:hover { background: rgba(255,255,255,0.03); }

.file-row td {
  padding: 8px 12px;
}

.file-icon { margin-right: 6px; }

.col-path { max-width: 300px; }
.col-size { width: 80px; }

.path {
  font-family: monospace;
  color: var(--color-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
}

.size { color: var(--color-muted); }
</style>
