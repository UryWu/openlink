<template>
  <div class="app-layout">
    <Navbar />
    <div class="app-body">
      <aside class="sidebar">
        <StatusIndicator />
        <nav class="sidebar-nav">
          <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" class="nav-item">
            <span class="nav-icon">{{ item.icon }}</span>
            <span class="nav-label">{{ item.label }}</span>
          </RouterLink>
        </nav>
      </aside>
      <main class="main-content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import Navbar from './Navbar.vue'
import StatusIndicator from './StatusIndicator.vue'

const navItems = [
  { to: '/', label: '仪表盘', icon: '📊' },
  { to: '/connection', label: '连接', icon: '🔌' },
  { to: '/tools', label: '工具控制台', icon: '🔧' },
  { to: '/files', label: '文件浏览器', icon: '📁' },
  { to: '/skills', label: '技能管理', icon: '⚡' },
  { to: '/prompt', label: '提示词', icon: '📝' },
  { to: '/settings', label: '设置', icon: '⚙️' },
]
</script>

<style>
/* ── Reset & Global ─────────────────────────────────────────────────── */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

:root {
  --sidebar-w: 220px;
  --color-bg: #0f1117;
  --color-surface: #181b24;
  --color-border: #2a2d3a;
  --color-text: #e1e3ec;
  --color-muted: #8b8fa3;
  --color-accent: #6c8aff;
  --color-success: #4ade80;
  --color-danger: #f87171;
  --color-warning: #fbbf24;
}

html, body {
  height: 100%;
}

body {
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: var(--color-bg);
  color: var(--color-text);
  line-height: 1.6;
}

#app {
  height: 100%;
}
</style>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: var(--sidebar-w);
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  padding: 8px;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  color: var(--color-muted);
  text-decoration: none;
  font-size: 14px;
  transition: background 0.15s, color 0.15s;
}

.nav-item:hover {
  background: rgba(255,255,255,0.04);
  color: var(--color-text);
}

.nav-item.router-link-active {
  background: rgba(108,138,255,0.12);
  color: var(--color-accent);
}

.nav-icon {
  font-size: 16px;
  width: 22px;
  text-align: center;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}
</style>
