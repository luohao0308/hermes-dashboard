<template>
  <div class="cost-dashboard">
    <div class="section-header">
      <div>
        <h3>成本追踪</h3>
        <p>查看模型调用成本、请求量和预算告警。</p>
      </div>
      <div class="period-tabs">
        <button v-for="p in periods" :key="p.key" :class="['tab', { active: period === p.key }]" @click="period = p.key; fetchCosts()">{{ p.label }}</button>
      </div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon cost"><DollarSign :size="18" /></div>
        <div class="stat-value">${{ summary.total_cost_usd }}</div>
        <div class="stat-label">总成本</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon requests"><MousePointerClick :size="18" /></div>
        <div class="stat-value">{{ summary.request_count }}</div>
        <div class="stat-label">请求数</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon input"><ArrowDownToLine :size="18" /></div>
        <div class="stat-value">{{ formatTokens(summary.total_input_tokens) }}</div>
        <div class="stat-label">输入 Token</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon output"><ArrowUpFromLine :size="18" /></div>
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
import { ArrowDownToLine, ArrowUpFromLine, DollarSign, MousePointerClick } from 'lucide-vue-next'
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
.section-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.section-header h3 { margin: 0; font-size: 18px; font-weight: 800; color: var(--text-primary); }
.section-header p { margin: 4px 0 0; color: var(--text-muted); font-size: 12px; }
.period-tabs { display: inline-flex; gap: 4px; padding: 4px; background: #f8fafc; border: 1px solid var(--border-color); border-radius: 12px; box-shadow: var(--shadow-sm); }
.tab { min-height: 30px; padding: 0 12px; background: transparent; border: none; border-radius: 8px; font-size: 12px; font-weight: 800; color: var(--text-secondary); cursor: pointer; }
.tab.active { background: #ffffff; color: var(--accent-color); box-shadow: var(--shadow-sm); }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.stat-card { background: #ffffff; border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 20px; box-shadow: var(--glass-shadow); }
.stat-icon { width: 40px; height: 40px; display: grid; place-items: center; border-radius: 12px; margin-bottom: 14px; }
.stat-icon.cost { color: #059669; background: #ecfdf5; }
.stat-icon.requests { color: #2563eb; background: #eff6ff; }
.stat-icon.input { color: #7c3aed; background: #f5f3ff; }
.stat-icon.output { color: #d97706; background: #fffbeb; }
.stat-value { font-size: 24px; font-weight: 900; color: var(--text-primary); }
.stat-label { font-size: 12px; font-weight: 800; color: var(--text-muted); margin-top: 4px; }
.breakdown-table { background: #ffffff; border: 1px solid var(--border-color); border-radius: var(--radius-lg); overflow: hidden; box-shadow: var(--glass-shadow); }
.table-header { display: grid; grid-template-columns: 1fr 2fr 1fr 1fr; padding: 12px 16px; font-size: 11px; font-weight: 900; color: var(--text-muted); text-transform: uppercase; border-bottom: 1px solid var(--border-subtle); background: #f8fafc; }
.table-row { display: grid; grid-template-columns: 1fr 2fr 1fr 1fr; padding: 10px 16px; font-size: 13px; color: var(--text-secondary); border-bottom: 1px solid var(--border-subtle); }
.table-row:last-child { border-bottom: none; }
.alerts-section { margin-top: 8px; }
.alerts-section h3 { font-size: 14px; font-weight: 900; color: var(--error-color); margin-bottom: 8px; }
.alert-card { display: flex; gap: 12px; align-items: center; padding: 12px 16px; background: #fef2f2; border: 1px solid rgba(239, 68, 68, 0.22); border-radius: 10px; font-size: 13px; }
.alert-scope { font-weight: 900; color: var(--text-primary); }
.alert-provider { color: var(--text-secondary); }
.alert-spent { margin-left: auto; color: var(--text-primary); }
.alert-exceeded { color: #b91c1c; font-weight: 900; font-size: 11px; }
.empty { text-align: center; padding: 40px; color: var(--text-muted); background: #ffffff; border: 1px dashed var(--border-color); border-radius: var(--radius-lg); }
@media (max-width: 900px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 640px) {
  .section-header,
  .alert-card { align-items: stretch; flex-direction: column; }
  .period-tabs { width: 100%; }
  .tab { flex: 1; }
  .stats-grid { grid-template-columns: 1fr; }
  .breakdown-table { overflow-x: auto; }
  .table-header,
  .table-row { min-width: 560px; }
  .alert-spent { margin-left: 0; }
}
</style>
