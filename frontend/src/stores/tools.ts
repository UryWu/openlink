import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ToolInfo, ToolRequest, ToolResponse } from '@/types'
import { fetchTools, execTool } from '@/api/endpoints'

export const useToolsStore = defineStore('tools', () => {
  const tools = ref<ToolInfo[]>([])
  const loading = ref(false)
  const lastResult = ref<ToolResponse | null>(null)
  const executing = ref(false)

  async function loadTools() {
    loading.value = true
    try {
      tools.value = await fetchTools()
    } finally {
      loading.value = false
    }
  }

  async function execute(req: ToolRequest): Promise<ToolResponse | null> {
    executing.value = true
    lastResult.value = null
    try {
      const res = await execTool(req)
      lastResult.value = res
      return res
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '请求失败'
      lastResult.value = { status: 'error', output: '', error: msg }
      return lastResult.value
    } finally {
      executing.value = false
    }
  }

  function clearResult() {
    lastResult.value = null
  }

  return { tools, loading, lastResult, executing, loadTools, execute, clearResult }
})
