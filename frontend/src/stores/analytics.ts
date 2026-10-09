import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { StatsResponse, ConversationMeta, MessageItem } from '@/types'
import { fetchStats, fetchConversations, deleteConversation, exportConversation, fetchMessages } from '@/api/endpoints'

export const useAnalyticsStore = defineStore('analytics', () => {
  const stats = ref<StatsResponse | null>(null)
  const conversations = ref<ConversationMeta[]>([])
  const selectedConvId = ref<string>('')
  const clusterInterval = ref<number>(30)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 最近对话分页
  const messages = ref<MessageItem[]>([])
  const messagesTotal = ref(0)
  const messagesLoading = ref(false)
  const PAGE = 20

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
      stats.value = await fetchStats(selectedConvId.value || undefined, clusterInterval.value)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  /** 拉取最近对话第一页（重置）。convId 为空时拉全部会话的消息。 */
  async function loadMessages(convId?: string) {
    messagesLoading.value = true
    try {
      const r = await fetchMessages(convId, 0, PAGE)
      messages.value = r.items
      messagesTotal.value = r.total
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载消息失败'
    } finally {
      messagesLoading.value = false
    }
  }

  /** 加载下一页，追加。 */
  async function loadMoreMessages() {
    if (messagesLoading.value || messages.value.length >= messagesTotal.value) return
    messagesLoading.value = true
    try {
      const r = await fetchMessages(selectedConvId.value || undefined, messages.value.length, PAGE)
      messages.value = messages.value.concat(r.items)
      messagesTotal.value = r.total
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '加载消息失败'
    } finally {
      messagesLoading.value = false
    }
  }

  async function select(convId: string) {
    selectedConvId.value = convId
    await load()
    await loadMessages(convId || undefined)
  }

  async function remove(convId: string) {
    try {
      await deleteConversation(convId)
      conversations.value = conversations.value.filter(c => c.convId !== convId)
      if (selectedConvId.value === convId) {
        selectedConvId.value = ''
        await load()
        await loadMessages(undefined)
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '删除失败'
    }
  }

  async function exportMd(convId: string, filename?: string) {
    try {
      const md = await exportConversation(convId)
      const name = (filename && filename.trim()) || `${convId}.md`
      const finalName = name.endsWith('.md') ? name : `${name}.md`
      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = finalName
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '导出失败'
    }
  }

  async function init() {
    await loadConversations()
    await load()
    await loadMessages(selectedConvId.value || undefined)
  }

  return {
    stats, conversations, selectedConvId, clusterInterval, loading, error,
    messages, messagesTotal, messagesLoading,
    load, loadConversations, select, remove, init, exportMd,
    loadMessages, loadMoreMessages,
  }
})
