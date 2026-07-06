import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SkillInfo } from '@/types'
import { fetchSkills } from '@/api/endpoints'

export const useSkillsStore = defineStore('skills', () => {
  const skills = ref<SkillInfo[]>([])
  const loading = ref(false)

  async function loadSkills() {
    loading.value = true
    try {
      skills.value = await fetchSkills()
    } finally {
      loading.value = false
    }
  }

  return { skills, loading, loadSkills }
})
