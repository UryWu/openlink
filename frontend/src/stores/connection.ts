import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchHealth, fetchAuth } from '@/api/endpoints'

export const useConnectionStore = defineStore('connection', () => {
  // ── State ────────────────────────────────────────────────────────────
  const token = ref(localStorage.getItem('openlink-token') || '')
  const serverUrl = ref('http://127.0.0.1:39527')
  const connected = ref(false)
  const lastHealth = ref<{ dir: string; version: string } | null>(null)
  const error = ref('')

  // ── Computed ─────────────────────────────────────────────────────────
  const maskedToken = computed(() => {
    if (!token.value) return '(未设置)'
    if (token.value.length <= 8) return '*'.repeat(token.value.length)
    return token.value.slice(0, 4) + '…' + token.value.slice(-4)
  })

  // ── Actions ──────────────────────────────────────────────────────────
  async function checkHealth(): Promise<boolean> {
    try {
      const health = await fetchHealth()
      connected.value = true
      lastHealth.value = { dir: health.dir, version: health.version }
      error.value = ''
      return true
    } catch (e: unknown) {
      connected.value = false
      error.value = e instanceof Error ? e.message : '无法连接服务器'
      return false
    }
  }

  async function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem('openlink-token', newToken)
    await checkHealth()
  }

  async function validateToken(t: string): Promise<boolean> {
    try {
      const res = await fetchAuth(t)
      return res.valid
    } catch {
      return false
    }
  }

  // ── Return ───────────────────────────────────────────────────────────
  return {
    token,
    serverUrl,
    connected,
    lastHealth,
    error,
    maskedToken,
    checkHealth,
    setToken,
    validateToken,
  }
})
