import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { StatsResponse } from '@/types'
import { fetchStats } from '@/api/endpoints'

export const useAnalyticsStore = defineStore('analytics', () => {
  const stats = ref<StatsResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load() {
    loading.value = true
    error.value = null
    try {
      stats.value = await fetchStats()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  return { stats, loading, error, load }
})
