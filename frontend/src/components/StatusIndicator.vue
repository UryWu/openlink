<template>
  <div class="status-bar">
    <span class="status-dot" :class="{ online: store.connected }" />
    <span class="status-label">{{ store.connected ? '已连接' : '未连接' }}</span>
    <button class="status-btn" @click="doCheck">{{ loading ? '…' : '测试' }}</button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useConnectionStore } from '@/stores/connection'

const store = useConnectionStore()
const loading = ref(false)

async function doCheck() {
  loading.value = true
  try {
    await store.checkHealth()
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.status-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-danger);
  flex-shrink: 0;
}

.status-dot.online {
  background: var(--color-success);
}

.status-label {
  font-size: 13px;
  color: var(--color-muted);
  flex: 1;
}

.status-btn {
  font-size: 11px;
  padding: 2px 8px;
  background: rgba(255,255,255,0.06);
  color: var(--color-muted);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  cursor: pointer;
}

.status-btn:hover {
  background: rgba(255,255,255,0.1);
  color: var(--color-text);
}
</style>
