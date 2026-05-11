<template>
  <div class="provider-panel">
    <div class="section-header">
      <div>
        <h3>模型管理</h3>
        <p>管理模型供应商、默认模型和连接状态。</p>
      </div>
      <div class="header-actions">
        <button class="btn-add" @click="showAddForm = true">
          <Plus :size="15" />
          添加自定义模型
        </button>
        <button class="btn-refresh" @click="fetchProviders">
          <RefreshCcw :size="15" :class="{ spinning: loading }" />
          刷新
        </button>
      </div>
    </div>

    <!-- 添加自定义模型表单 -->
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

    <!-- 编辑配置表单 -->
    <div v-if="editingProvider" class="add-form">
      <h4>编辑 {{ editingProvider.name }} 配置</h4>
      <div class="form-grid">
        <div class="form-item">
          <label>API 地址</label>
          <input v-model="editConfig.base_url" />
        </div>
        <div class="form-item">
          <label>API 密钥</label>
          <input v-model="editConfig.api_key" type="password" placeholder="留空表示不修改" />
        </div>
        <div class="form-item full-width">
          <label>默认模型</label>
          <select v-model="editConfig.default_model" class="model-select">
            <option v-for="m in editingProvider.models" :key="m.id" :value="m.id">
              {{ m.display_name || m.id }}
            </option>
          </select>
        </div>
      </div>
      <div class="form-actions">
        <button class="btn-cancel" @click="editingProvider = null">取消</button>
        <button class="btn-submit" @click="saveProviderConfig">保存</button>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else class="provider-grid">
      <div v-for="p in providers" :key="p.name" class="provider-card">
        <div class="provider-header">
          <div class="provider-title">
            <span class="provider-icon">
              <Cpu :size="18" />
            </span>
            <span class="provider-name">{{ p.name }}</span>
          </div>
          <span :class="['provider-status', p.enabled ? 'enabled' : 'disabled']">
            {{ p.enabled ? '已启用' : '已禁用' }}
          </span>
        </div>
        <div class="provider-model">
          默认模型:
          <select
            :value="p.default_model"
            class="inline-select"
            @change="changeDefaultModel(p.name, ($event.target as HTMLSelectElement).value)"
          >
            <option v-for="m in p.models" :key="m.id" :value="m.id">
              {{ m.display_name || m.id }}
            </option>
          </select>
        </div>
        <div class="provider-features">
          <span v-for="f in p.supported_features" :key="f" class="feature-tag">{{ f }}</span>
        </div>
        <div class="provider-models">
          <div v-for="m in p.models" :key="m.id" class="model-item">
            <span class="model-name" :class="{ 'is-default': m.id === p.default_model }">
              {{ m.display_name || m.id }}
            </span>
            <span v-if="m.id === p.default_model" class="default-badge">默认</span>
            <span class="model-cost">${{ m.cost_per_1k_input || 0 }}/1k tokens</span>
          </div>
        </div>
        <div class="provider-actions">
          <button class="btn-test" @click="testProvider(p.name)">
            <Wifi :size="14" />
            测试连接
          </button>
          <button class="btn-edit" @click="startEdit(p)">
            <Settings2 :size="14" />
            编辑配置
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Cpu, Plus, RefreshCcw, Settings2, Wifi } from 'lucide-vue-next'
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
const editingProvider = ref<ProviderInfo | null>(null)
const editConfig = ref({ base_url: '', api_key: '', default_model: '' })
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
    alert(data.ok ? `${name} 连接成功` : `${name} 连接失败: ${data.error || '未知原因'}`)
  } catch {
    alert(`测试 ${name} 失败`)
  }
}

async function changeDefaultModel(name: string, modelId: string) {
  try {
    const res = await fetch(`${API_BASE}/api/providers/${name}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ default_model: modelId }),
    })
    if (res.ok) {
      await fetchProviders()
    }
  } catch {
    alert('修改失败')
  }
}

function startEdit(p: ProviderInfo) {
  editingProvider.value = p
  editConfig.value = {
    base_url: (p as any).base_url || '',
    api_key: '',
    default_model: p.default_model,
  }
}

async function saveProviderConfig() {
  if (!editingProvider.value) return
  const name = editingProvider.value.name
  const updates: Record<string, any> = {
    default_model: editConfig.value.default_model,
  }
  if (editConfig.value.base_url) updates.base_url = editConfig.value.base_url
  if (editConfig.value.api_key) updates.api_key = editConfig.value.api_key

  try {
    const res = await fetch(`${API_BASE}/api/providers/${name}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    })
    if (res.ok) {
      editingProvider.value = null
      await fetchProviders()
    } else {
      alert('保存失败')
    }
  } catch {
    alert('保存失败')
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
.section-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.section-header h3 { margin: 0; font-size: 18px; font-weight: 800; color: var(--text-primary); }
.section-header p { margin: 4px 0 0; color: var(--text-muted); font-size: 12px; }
.header-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.btn-refresh,
.btn-add,
.btn-cancel,
.btn-submit,
.btn-test,
.btn-edit {
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 14px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: #ffffff;
  color: var(--text-secondary);
  box-shadow: var(--shadow-sm);
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-refresh:hover,
.btn-test:hover,
.btn-edit:hover,
.btn-cancel:hover {
  border-color: #bfdbfe;
  background: var(--accent-soft);
  color: var(--accent-color);
}
.btn-add,
.btn-submit {
  background: var(--accent-color);
  border-color: var(--accent-color);
  color: #ffffff;
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.18);
}
.add-form {
  background: #ffffff;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--glass-shadow);
}
.add-form h4 { font-size: 14px; font-weight: 900; color: var(--text-primary); margin: 0 0 16px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
.form-item { display: flex; flex-direction: column; gap: 6px; }
.form-item.full-width { grid-column: 1 / -1; }
.form-item label { font-size: 12px; font-weight: 800; color: var(--text-muted); }
.form-item input,
.model-select,
.inline-select {
  min-height: 36px;
  padding: 0 12px;
  background: #ffffff;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  color: var(--text-primary);
  font-size: 13px;
  box-shadow: var(--shadow-sm);
}
.form-item input:focus,
.model-select:focus,
.inline-select:focus { outline: none; border-color: var(--accent-color); }
.form-actions { display: flex; justify-content: flex-end; gap: 8px; }
.provider-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
.provider-card {
  background: #ffffff;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--glass-shadow);
}
.provider-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 14px; }
.provider-title { display: flex; align-items: center; min-width: 0; gap: 10px; }
.provider-icon { width: 40px; height: 40px; display: grid; place-items: center; border-radius: 12px; color: #2563eb; background: #eff6ff; }
.provider-name { min-width: 0; overflow: hidden; text-overflow: ellipsis; font-size: 16px; font-weight: 900; color: var(--text-primary); text-transform: capitalize; }
.provider-status { white-space: nowrap; font-size: 11px; padding: 4px 9px; border-radius: var(--radius-pill); font-weight: 900; }
.enabled { background: #ecfdf5; color: #047857; }
.disabled { background: #fef2f2; color: #b91c1c; }
.provider-model { font-size: 12px; color: var(--text-muted); margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.inline-select { min-height: 32px; flex: 1; min-width: 0; font-size: 12px; }
.provider-features { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 14px; }
.feature-tag { font-size: 10px; padding: 4px 7px; background: #f8fafc; border: 1px solid var(--border-subtle); border-radius: var(--radius-pill); color: var(--text-secondary); font-weight: 800; }
.provider-models { margin-bottom: 14px; border-top: 1px solid var(--border-subtle); }
.model-item { display: flex; align-items: center; gap: 8px; font-size: 12px; padding: 9px 0; color: var(--text-secondary); border-bottom: 1px solid var(--border-subtle); }
.model-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.model-name.is-default { color: var(--accent-color); font-weight: 900; }
.default-badge { font-size: 10px; padding: 2px 7px; background: var(--accent-soft); color: var(--accent-color); border-radius: var(--radius-pill); font-weight: 900; }
.model-cost { color: var(--text-muted); white-space: nowrap; }
.provider-actions { display: flex; gap: 8px; }
.btn-test,
.btn-edit { flex: 1; }
.model-select { width: 100%; }
.loading {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
  background: #ffffff;
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-lg);
}
.spinning { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 720px) {
  .section-header,
  .provider-header,
  .provider-model,
  .provider-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .header-actions,
  .btn-refresh,
  .btn-add,
  .btn-test,
  .btn-edit {
    width: 100%;
  }

  .form-grid,
  .provider-grid {
    grid-template-columns: 1fr;
  }

  .form-item.full-width {
    grid-column: auto;
  }
}
</style>
