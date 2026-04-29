<template>
  <div class="provider-panel">
    <div class="section-header">
      <h3>模型管理</h3>
      <div class="header-actions">
        <button class="btn-add" @click="showAddForm = true">+ 添加自定义模型</button>
        <button class="btn-refresh" @click="fetchProviders">刷新</button>
      </div>
    </div>

    <div v-if="showAddForm" class="add-form">
      <h4>添加自定义模型</h4>
      <div class="form-grid">
        <div class="form-item">
          <label>Provider 名称</label>
          <input v-model="newProvider.name" placeholder="例如: deepseek" />
        </div>
        <div class="form-item">
          <label>API 地址</label>
          <input v-model="newProvider.base_url" placeholder="https://api.example.com/v1" />
        </div>
        <div class="form-item">
          <label>API 密钥</label>
          <input v-model="newProvider.api_key" type="password" placeholder="sk-..." />
        </div>
        <div class="form-item">
          <label>默认模型</label>
          <input v-model="newProvider.default_model" placeholder="model-name" />
        </div>
        <div class="form-item full-width">
          <label>模型列表（逗号分隔，可选）</label>
          <input v-model="newProvider.models_str" placeholder="model-1, model-2" />
        </div>
      </div>
      <div class="form-actions">
        <button class="btn-cancel" @click="showAddForm = false">取消</button>
        <button class="btn-submit" @click="addCustomProvider">添加</button>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else class="provider-grid">
      <div v-for="p in providers" :key="p.name" class="provider-card">
        <div class="provider-header">
          <span class="provider-name">{{ p.name }}</span>
          <span :class="['provider-status', p.enabled ? 'enabled' : 'disabled']">
            {{ p.enabled ? '已启用' : '已禁用' }}
          </span>
        </div>
        <div class="provider-model">默认模型: {{ p.default_model || 'N/A' }}</div>
        <div class="provider-features">
          <span v-for="f in p.supported_features" :key="f" class="feature-tag">{{ f }}</span>
        </div>
        <div class="provider-models">
          <div v-for="m in p.models" :key="m.id" class="model-item">
            <span class="model-name">{{ m.display_name || m.id }}</span>
            <span class="model-cost">${{ m.cost_per_1k_input }}/1k tokens</span>
          </div>
        </div>
        <button class="btn-test" @click="testProvider(p.name)">测试连接</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { API_BASE } from '../config'

interface ProviderInfo {
  name: string
  enabled: boolean
  default_model: string
  models: Array<{ id: string; display_name: string; cost_per_1k_input: number }>
  supported_features: string[]
}

const providers = ref<ProviderInfo[]>([])
const loading = ref(false)
const showAddForm = ref(false)
const newProvider = ref({
  name: '',
  base_url: '',
  api_key: '',
  default_model: '',
  models_str: '',
})

async function fetchProviders() {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/providers`)
    if (res.ok) {
      const data = await res.json()
      providers.value = data.providers || []
    }
  } catch {
    // API not available
  } finally {
    loading.value = false
  }
}

async function testProvider(name: string) {
  try {
    const res = await fetch(`${API_BASE}/api/providers/${name}/test`, { method: 'POST' })
    const data = await res.json()
    alert(data.ok ? `${name} 连接成功` : `${name} 连接失败`)
  } catch {
    alert(`测试 ${name} 失败`)
  }
}

async function addCustomProvider() {
  const { name, base_url, api_key, default_model, models_str } = newProvider.value
  if (!name || !base_url || !api_key) {
    alert('请填写必填字段：名称、API 地址、API 密钥')
    return
  }

  const models = models_str
    .split(',')
    .map(m => m.trim())
    .filter(m => m.length > 0)

  try {
    const res = await fetch(`${API_BASE}/api/providers/custom`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, base_url, api_key, default_model, models }),
    })
    if (res.ok) {
      alert('添加成功')
      showAddForm.value = false
      newProvider.value = { name: '', base_url: '', api_key: '', default_model: '', models_str: '' }
      await fetchProviders()
    } else {
      const data = await res.json()
      alert(`添加失败: ${data.detail || '未知错误'}`)
    }
  } catch {
    alert('添加失败，请检查网络连接')
  }
}

onMounted(fetchProviders)
</script>

<style scoped>
.provider-panel { display: flex; flex-direction: column; gap: 24px; }
.section-header { display: flex; justify-content: space-between; align-items: center; }
.section-header h3 { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.header-actions { display: flex; gap: 8px; }
.btn-refresh { padding: 6px 14px; background: var(--accent-soft); color: var(--accent-color); border: none; border-radius: var(--radius-md); font-size: 12px; cursor: pointer; }
.btn-add { padding: 6px 14px; background: var(--accent-color); color: white; border: none; border-radius: var(--radius-md); font-size: 12px; cursor: pointer; }
.add-form { background: var(--glass-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 20px; }
.add-form h4 { font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 16px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
.form-item { display: flex; flex-direction: column; gap: 4px; }
.form-item.full-width { grid-column: 1 / -1; }
.form-item label { font-size: 12px; color: var(--text-muted); }
.form-item input { padding: 8px 12px; background: var(--bg-tertiary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); color: var(--text-primary); font-size: 13px; }
.form-item input:focus { outline: none; border-color: var(--accent-color); }
.form-actions { display: flex; justify-content: flex-end; gap: 8px; }
.btn-cancel { padding: 6px 14px; background: var(--bg-tertiary); color: var(--text-secondary); border: none; border-radius: var(--radius-md); font-size: 12px; cursor: pointer; }
.btn-submit { padding: 6px 14px; background: var(--accent-color); color: white; border: none; border-radius: var(--radius-md); font-size: 12px; cursor: pointer; }
.provider-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
.provider-card { background: var(--glass-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 20px; }
.provider-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.provider-name { font-size: 16px; font-weight: 600; color: var(--text-primary); text-transform: capitalize; }
.provider-status { font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 600; }
.enabled { background: rgba(80, 250, 123, 0.15); color: #50fa7b; }
.disabled { background: rgba(255, 85, 85, 0.15); color: #ff5555; }
.provider-model { font-size: 12px; color: var(--text-muted); margin-bottom: 10px; }
.provider-features { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }
.feature-tag { font-size: 10px; padding: 2px 6px; background: var(--bg-tertiary); border-radius: 4px; color: var(--text-secondary); }
.provider-models { margin-bottom: 12px; }
.model-item { display: flex; justify-content: space-between; font-size: 12px; padding: 4px 0; color: var(--text-secondary); }
.model-cost { color: var(--text-muted); }
.btn-test { width: 100%; padding: 8px; background: var(--accent-soft); color: var(--accent-color); border: none; border-radius: var(--radius-md); font-size: 12px; cursor: pointer; }
.loading { text-align: center; padding: 40px; color: var(--text-muted); }
</style>
