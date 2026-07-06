<template>
  <div class="skills-view">
    <h1 class="page-title">技能管理</h1>

    <div v-if="loading" class="loading">加载中…</div>

    <div v-if="!loading && skills.length === 0" class="empty">
      未找到任何技能。在 .skills/ 或 skills/ 目录中放置 SKILL.md 文件。
    </div>

    <div class="skills-grid">
      <div v-for="s in skills" :key="s.name" class="skill-card">
        <div class="skill-name">{{ s.name }}</div>
        <div class="skill-desc">{{ s.description }}</div>
        <div class="skill-source" v-if="s.source">{{ s.source }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useSkillsStore } from '@/stores/skills'
import { useConnectionStore } from '@/stores/connection'
import { storeToRefs } from 'pinia'

const skillsStore = useSkillsStore()
const connStore = useConnectionStore()
const { skills, loading } = storeToRefs(skillsStore)

onMounted(async () => {
  if (connStore.connected || await connStore.checkHealth()) {
    skillsStore.loadSkills()
  }
})
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 600; margin-bottom: 24px; }

.loading, .empty {
  color: var(--color-muted);
  font-size: 14px;
  padding: 32px 0;
}

.skills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.skill-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 16px 20px;
}

.skill-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-accent);
  font-family: monospace;
  margin-bottom: 6px;
}

.skill-desc {
  font-size: 13px;
  color: var(--color-text);
  line-height: 1.6;
}

.skill-source {
  font-size: 11px;
  color: var(--color-muted);
  margin-top: 8px;
  background: rgba(0,0,0,0.2);
  padding: 2px 8px;
  border-radius: 3px;
  display: inline-block;
}
</style>
