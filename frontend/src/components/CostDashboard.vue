<template>
  <div class="cost-dashboard">
    <div class="section-header">
      <h3>成本追踪</h3>
      <div class="period-tabs">
        <button v-for="p in periods" :key="p.key" :class="['tab', { active: period === p.key }]" @click="period = p.key; fetchCosts()">{{ p.label }}</button>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">${{ summary.total_cost_usd }}</div>
        <div class="stat-label">总成本</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ summary.request_count }}</div>
        <div class="stat-label">请求数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ formatTokens(summary.total_input_tokens) }}</div>
        <div class="stat-label">输入 Token</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ formatTokens(summary.total_output_tokens) }}</div>
        <div class="stat-label">输出 Token</div>
      </div>
    </div>

    <div class="section-header">
      <h3>按模型分类</h3>
    </div>
    <div v-if="breakdown.length === 0" class="empty">暂无使用数据</div>
    <div v-else class="breakdown-table">
      <div class="table-header">
        <span>供应商</span><span>模型</span><span>请求数</span><span>成本</span>
      </div>
      <div v-for="row in breakdown" :key="`${row.provider}-${row.model}`" class="table-row">
        <span>{{ row.provider }}</span>
        <span>{{ row.model }}</span>
        <span>{{ row.count }}</span>
        <span>${{ row.cost_usd }}</span>
      </div>
    </div>

    <div v-if="alerts.length > 0" class="alerts-section">
      <h3>预算告警</h3>
      <div v-for="a in alerts" :key="`${a.scope}-${a.provider}`" class="alert-card">
        <span class="alert-scope">{{ a.scope }}</span>
        <span class="alert-provider">{{ a.provider || '全部' }}</span>
        <span class="alert-spent">${{ a.spent_usd }} / ${{ a.limit_usd }}</span>
        <span v-if="a.exceeded" class="alert-exceeded">已超出</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { API_BASE } from '../config'

const periods = [
  { key: 'daily', label: '每日' },
  { key: 'weekly', label: '每周' },
  { key: 'monthly', label: '每月' },
]
const period = ref('monthly')
const summary = ref({ total_cost_usd: 0, request_count: 0, total_input_tokens: 0, total_output_tokens: 0 })
const breakdown = ref<Array<{ provider: string; model: string; count: number; cost_usd: number }>>([])
const alerts = ref<Array<{ scope: string; provider: string; spent_usd: number; limit_usd: number; exceeded: boolean }>>([])

function formatTokens(n: number): string {
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`
  return String(n)
}

async function fetchCosts() {
  try {
    const [s, b, a] = await Promise.all([
      fetch(`${API_BASE}/api/cost/summary?period=${period.value}`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE}/api/cost/breakdown`).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE}/api/cost/alerts`).then(r => r.ok ? r.json() : null),
    ])
    if (s) summary.value = s
    if (b) breakdown.value = b
    if (a) alerts.value = a
  } catch {
    // API not available
  }
}

onMounted(fetchCosts)
</script>

<style scoped>
.cost-dashboard { display: flex; flex-direction: column; gap: 24px; }
.section-header { display: flex; justify-content: space-between; align-items: center; }
.section-header h3 { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.period-tabs { display: flex; gap: 4px; }
.tab { padding: 6px 12px; background: var(--bg-tertiary); border: none; border-radius: var(--radius-md); font-size: 12px; color: var(--text-secondary); cursor: pointer; }
.tab.active { background: var(--accent-soft); color: var(--accent-color); }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.stat-card { background: var(--glass-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 20px; text-align: center; }
.stat-value { font-size: 24px; font-weight: 700; color: var(--text-primary); }
.stat-label { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.breakdown-table { background: var(--glass-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); overflow: hidden; }
.table-header { display: grid; grid-template-columns: 1fr 2fr 1fr 1fr; padding: 12px 16px; font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; border-bottom: 1px solid var(--border-subtle); }
.table-row { display: grid; grid-template-columns: 1fr 2fr 1fr 1fr; padding: 10px 16px; font-size: 13px; color: var(--text-secondary); border-bottom: 1px solid var(--border-subtle); }
.table-row:last-child { border-bottom: none; }
.alerts-section { margin-top: 8px; }
.alerts-section h3 { font-size: 14px; font-weight: 600; color: var(--error-color); margin-bottom: 8px; }
.alert-card { display: flex; gap: 12px; align-items: center; padding: 12px 16px; background: rgba(255, 85, 85, 0.08); border: 1px solid rgba(255, 85, 85, 0.2); border-radius: var(--radius-md); font-size: 13px; }
.alert-scope { font-weight: 600; color: var(--text-primary); }
.alert-provider { color: var(--text-secondary); }
.alert-spent { margin-left: auto; color: var(--text-primary); }
.alert-exceeded { color: #ff5555; font-weight: 700; font-size: 11px; }
.empty { text-align: center; padding: 40px; color: var(--text-muted); }
</style>
