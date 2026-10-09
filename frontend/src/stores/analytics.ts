import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { StatsResponse, ConversationMeta } from '@/types'
import { fetchStats, fetchConversations, deleteConversation } from '@/api/endpoints'

export const useAnalyticsStore = defineStore('analytics', () => {
  const stats = ref<StatsResponse | null>(null)
  const conversations = ref<ConversationMeta[]>([])
  const selectedConvId = ref<string>('')
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function loadConversations() {
    try {
      conversations.value = await fetchConversations()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载会话列表失败'
    }
  }

  async function load() {
    loading.value = true
    error.value = null
    try {
      stats.value = await fetchStats(selectedConvId.value || undefined)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function select(convId: string) {
    selectedConvId.value = convId
    await load()
  }

  async function remove(convId: string) {
    try {
      await deleteConversation(convId)
      conversations.value = conversations.value.filter(c => c.convId !== convId)
      if (selectedConvId.value === convId) {
        selectedConvId.value = ''
        await load()
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '删除失败'
    }
  }

  async function init() {
    await loadConversations()
    await load()
  }

  return {
    stats, conversations, selectedConvId, loading, error,
    load, loadConversations, select, remove, init,
  }
})
