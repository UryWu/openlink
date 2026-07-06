<template>
  <header class="navbar">
    <div class="navbar-brand">
      <span class="logo">🔗</span>
      <span class="title">openlink</span>
      <span class="version">v1.0</span>
    </div>
    <div class="navbar-info">
      <span v-if="store.lastHealth" class="dir-badge" :title="store.lastHealth.dir">
        {{ store.lastHealth.dir }}
      </span>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useConnectionStore } from '@/stores/connection'

const store = useConnectionStore()
</script>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 16px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.navbar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo { font-size: 18px; }

.title {
  font-size: 15px;
  font-weight: 600;
}

.version {
  font-size: 11px;
  color: var(--color-muted);
  background: rgba(255,255,255,0.06);
  padding: 1px 6px;
  border-radius: 4px;
}

.dir-badge {
  font-size: 12px;
  color: var(--color-muted);
  max-width: 360px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
