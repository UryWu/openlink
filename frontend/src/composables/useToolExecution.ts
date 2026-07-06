import { ref } from 'vue'
import type { ToolRequest, ToolResponse } from '@/types'
import { execTool } from '@/api/endpoints'
import { useConnectionStore } from '@/stores/connection'

/**
 * Composable for executing a tool and tracking its result.
 */
export function useToolExecution() {
  const connStore = useConnectionStore()
  const executing = ref(false)
  const result = ref<ToolResponse | null>(null)
  const error = ref('')

  async function execute(req: ToolRequest) {
    executing.value = true
    error.value = ''
    result.value = null
    try {
      if (!connStore.connected) {
        await connStore.checkHealth()
        if (!connStore.connected) {
          error.value = '服务器未连接'
          return null
        }
      }
      result.value = await execTool(req)
      return result.value
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '请求失败'
      error.value = msg
      result.value = { status: 'error', output: '', error: msg }
      return result.value
    } finally {
      executing.value = false
    }
  }

  function clear() {
    result.value = null
    error.value = ''
  }

  return { executing, result, error, execute, clear }
}
