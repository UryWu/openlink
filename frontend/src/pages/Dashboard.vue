<template>
  <div class="dashboard">
    <h1 class="page-title">仪表盘</h1>

    <div class="cards">
      <div class="card">
        <div class="card-label">服务器状态</div>
        <div class="card-value">
          <span class="dot" :class="{ green: store.connected }" />
          {{ store.connected ? '在线' : '离线' }}
        </div>
        <div class="card-sub" v-if="store.lastHealth">
          v{{ store.lastHealth.version }} · {{ store.lastHealth.dir }}
        </div>
        <div class="card-sub error" v-if="store.error">{{ store.error }}</div>
      </div>

      <div class="card">
        <div class="card-label">Token</div>
        <div class="card-value mono">{{ store.maskedToken }}</div>
      </div>

      <div class="card">
        <div class="card-label">已注册工具</div>
        <div class="card-value">{{ tools.length }} 个</div>
        <div class="card-sub" v-if="tools.length">
          <span v-for="t in tools.slice(0,6)" :key="t.name" class="tag">{{ t.name }}</span>
          <span v-if="tools.length > 6" class="tag">+{{ tools.length - 6 }}</span>
        </div>
      </div>

      <div class="card">
        <div class="card-label">Skills</div>
        <div class="card-value">{{ skills.length }} 个</div>
      </div>
    </div>

    <div class="quick-actions">
      <h2>快速操作</h2>
      <div class="action-grid">
        <button class="action-btn" @click="checkAll">
          🔄 检查服务状态
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useConnectionStore } from '@/stores/connection'
import { useToolsStore } from '@/stores/tools'
import { useSkillsStore } from '@/stores/skills'

const store = useConnectionStore()
const toolsStore = useToolsStore()
const skillsStore = useSkillsStore()

const tools = ref(toolsStore.tools)
const skills = ref(skillsStore.skills)

async function checkAll() {
  await store.checkHealth()
  if (store.connected) {
    await Promise.all([toolsStore.loadTools(), skillsStore.loadSkills()])
    tools.value = toolsStore.tools
    skills.value = skillsStore.skills
  }
}

onMounted(checkAll)
</script>

<style scoped>
.page-title {
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 24px;
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 18px 20px;
}

.card-label {
  font-size: 12px;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.card-value {
  font-size: 20px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-sub {
  font-size: 12px;
  color: var(--color-muted);
  margin-top: 6px;
}

.card-sub.error { color: var(--color-danger); }

.mono { font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 14px; }

.dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  background: var(--color-danger);
  display: inline-block;
}
.dot.green { background: var(--color-success); }

.tag {
  display: inline-block;
  font-size: 11px;
  padding: 1px 6px;
  margin: 2px;
  background: rgba(108,138,255,0.12);
  color: var(--color-accent);
  border-radius: 3px;
}

.quick-actions h2 {
  font-size: 16px;
  margin-bottom: 12px;
}

.action-grid {
  display: flex;
  gap: 10px;
}

.action-btn {
  padding: 10px 20px;
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.15s;
}

.action-btn:hover {
  background: rgba(108,138,255,0.1);
}
</style>
