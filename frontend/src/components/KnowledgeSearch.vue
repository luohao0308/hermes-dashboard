<template>
  <section class="knowledge-search">
    <div class="knowledge-header">
      <div>
        <h2>事故知识库</h2>
        <p>搜索 Trace、RCA 和 Runbook 记录</p>
      </div>
      <form class="search-form" @submit.prevent="search">
        <input v-model="query" type="search" placeholder="搜索 gateway、tool、timeout..." />
        <button :disabled="loading || query.trim().length === 0">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '搜索中' : '搜索' }}
        </button>
      </form>
    </div>

    <div v-if="error" class="error-box">{{ error }}</div>

    <div class="results-list">
      <article v-for="item in results" :key="`${item.source}-${item.item_id}`" class="result-item">
        <div class="result-source">{{ item.source }}</div>
        <div class="result-main">
          <div class="result-title">
            <strong>{{ item.title || item.item_id }}</strong>
            <span>{{ item.item_type || item.status || 'record' }}</span>
          </div>
          <p>{{ item.summary || '暂无摘要' }}</p>
          <div class="result-meta">
            <span v-if="item.session_id">Session {{ shortId(item.session_id) }}</span>
            <span v-if="item.run_id">Run {{ shortId(item.run_id) }}</span>
            <span>{{ formatDate(item.created_at) }}</span>
          </div>
        </div>
      </article>
      <div v-if="!loading && searched && results.length === 0" class="empty">没有匹配记录</div>
      <div v-if="!searched && !loading" class="empty">输入关键词后搜索历史事故资产</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { API_BASE } from '../config'

interface KnowledgeItem {
  source: string
  item_id: string
  run_id?: string | null
  session_id?: string | null
  title: string
  summary: string
  item_type?: string | null
  status?: string | null
  created_at?: string | null
}

const query = ref('')
const loading = ref(false)
const error = ref('')
const searched = ref(false)
const results = ref<KnowledgeItem[]>([])

async function search() {
  const q = query.value.trim()
  if (!q) return
  loading.value = true
  error.value = ''
  searched.value = true
  try {
    const res = await fetch(`${API_BASE}/api/agent/knowledge/search?q=${encodeURIComponent(q)}&limit=20`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    results.value = data.results || []
  } catch (e) {
    results.value = []
    error.value = '搜索失败，请确认 Bridge 服务可达。'
  } finally {
    loading.value = false
  }
}

function shortId(value: string): string {
  return value.slice(0, 8)
}

function formatDate(value?: string | null): string {
  if (!value) return '时间未确认'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped>
.knowledge-search {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.knowledge-header,
.result-item,
.error-box {
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
}

.knowledge-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px;
}

.knowledge-header h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 18px;
}

.knowledge-header p {
  margin: 3px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
}

.search-form {
  display: flex;
  gap: 10px;
  width: min(520px, 100%);
}

.search-form input {
  flex: 1;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 13px;
}

.search-form button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid var(--accent-color);
  border-radius: var(--radius-md);
  background: var(--accent-soft);
  color: var(--accent-color);
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.search-form button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.result-item {
  display: grid;
  grid-template-columns: 86px 1fr;
  gap: 14px;
  padding: 14px 16px;
}

.result-source {
  color: var(--accent-color);
  font-size: 11px;
  font-weight: 900;
  text-transform: uppercase;
}

.result-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-title strong {
  color: var(--text-primary);
  font-size: 13px;
}

.result-title span {
  padding: 2px 7px;
  border-radius: var(--radius-pill);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 800;
}

.result-main p {
  margin: 6px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 11px;
}

.empty,
.error-box {
  padding: 16px 20px;
  color: var(--text-secondary);
  font-size: 13px;
}

.error-box {
  border-color: rgba(239, 68, 68, 0.25);
  background: var(--error-soft);
}

.spinner {
  width: 12px;
  height: 12px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .knowledge-header,
  .search-form {
    align-items: stretch;
    flex-direction: column;
  }

  .result-item {
    grid-template-columns: 1fr;
  }
}
</style>
