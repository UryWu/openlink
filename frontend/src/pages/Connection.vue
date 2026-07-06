<template>
  <div class="connection-page">
    <h1 class="page-title">连接配置</h1>

    <div class="card">
      <div class="card-header">
        <span class="card-label">服务器</span>
        <span class="dot" :class="{ green: store.connected }" />
        <span>{{ store.connected ? '已连接' : '未连接' }}</span>
      </div>

      <div class="field">
        <label>Server URL</label>
        <input v-model="serverUrl" type="text" class="input" placeholder="http://127.0.0.1:39527" />
      </div>

      <div class="field">
        <label>Token</label>
        <div class="token-row">
          <input
            :type="showToken ? 'text' : 'password'"
            v-model="localToken"
            class="input mono flex-1"
            :placeholder="hasSavedToken ? '已保存 · 留空不覆盖' : '请输入认证 token'"
          />
          <button class="btn-ghost" @click="showToken = !showToken">
            {{ showToken ? '🙈' : '👁️' }}
          </button>
          <button class="btn-primary" @click="saveToken" :disabled="saving">
            {{ saving ? '…' : '保存并验证' }}
          </button>
        </div>
      </div>

      <div v-if="validateMsg" class="validate-msg" :class="{ ok: validateOk }">
        {{ validateMsg }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useConnectionStore } from '@/stores/connection'

const store = useConnectionStore()

const serverUrl = ref('http://127.0.0.1:39527')
const localToken = ref('')
const showToken = ref(false)
const saving = ref(false)
const validateMsg = ref('')
const validateOk = ref(false)
const hasSavedToken = ref(false)

onMounted(async () => {
  hasSavedToken.value = !!store.token
  await store.checkHealth()
})

async function saveToken() {
  saving.value = true
  validateMsg.value = ''
  if (!localToken.value.trim()) {
    validateMsg.value = '请输入 token'
    saving.value = false
    return
  }
  try {
    const ok = await store.validateToken(localToken.value.trim())
    if (ok) {
      await store.setToken(localToken.value.trim())
      validateOk.value = true
      validateMsg.value = '✅ Token 验证通过'
      hasSavedToken.value = true
    } else {
      validateOk.value = false
      validateMsg.value = '❌ Token 验证失败'
    }
  } catch {
    validateOk.value = false
    validateMsg.value = '❌ 连接服务器失败'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.page-title { font-size: 22px; font-weight: 600; margin-bottom: 24px; }

.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 24px;
  max-width: 560px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.card-label { font-size: 16px; font-weight: 600; }

.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--color-danger); }
.dot.green { background: var(--color-success); }

.field { margin-bottom: 16px; }

.field label {
  display: block;
  font-size: 13px;
  color: var(--color-muted);
  margin-bottom: 4px;
}

.input {
  width: 100%;
  padding: 8px 12px;
  background: var(--color-bg);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 14px;
  outline: none;
}

.input:focus { border-color: var(--color-accent); }

.mono { font-family: 'Cascadia Code', 'Fira Code', monospace; }

.token-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.flex-1 { flex: 1; }

.btn-ghost {
  padding: 8px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 16px;
}

.btn-primary {
  padding: 8px 16px;
  background: var(--color-accent);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}

.btn-primary:hover { opacity: 0.9; }
.btn-primary:disabled { opacity: 0.5; cursor: default; }

.validate-msg { font-size: 13px; margin-top: 4px; color: var(--color-danger); }
.validate-msg.ok { color: var(--color-success); }
</style>
