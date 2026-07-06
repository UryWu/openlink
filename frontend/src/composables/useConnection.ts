import { onMounted, onUnmounted } from 'vue'
import { useConnectionStore } from '@/stores/connection'

/**
 * Auto health-check on mount, with optional polling interval.
 * Returns reactive connection state from the store.
 */
export function useConnection(options?: { pollIntervalMs?: number }) {
  const store = useConnectionStore()
  let timer: ReturnType<typeof setInterval> | null = null

  onMounted(async () => {
    await store.checkHealth()
    if (options?.pollIntervalMs && options.pollIntervalMs > 0) {
      timer = setInterval(() => store.checkHealth(), options.pollIntervalMs)
    }
  })

  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })

  return store
}
