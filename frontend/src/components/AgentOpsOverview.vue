<template>
  <section class="ops-overview">
    <div class="overview-header">
      <div>
        <h2>AgentOps 概览</h2>
        <p>{{ summaryText }}</p>
      </div>
      <button class="overview-refresh" :disabled="loading" @click="emit('refresh')">
        <span v-if="loading" class="spinner"></span>
        {{ loading ? '同步中' : '同步' }}
      </button>
    </div>

    <div class="overview-grid">
      <div class="health-block">
        <div class="health-ring" :class="healthTone" :style="{ '--score': healthScore }">
          <span>{{ healthScore }}</span>
        </div>
        <div class="health-copy">
          <span class="eyebrow">运行健康度</span>
          <strong>{{ healthLabel }}</strong>
          <span>{{ healthReason }}</span>
        </div>
      </div>

      <div class="metric-block">
        <span class="metric-label">活跃任务</span>
        <strong>{{ activeTaskCount }}</strong>
        <span>{{ totalMessages }} 条消息</span>
      </div>

      <div class="metric-block">
        <span class="metric-label">错误日志</span>
        <strong>{{ errorLogCount }}</strong>
        <span>{{ warningLogCount }} 条警告</span>
      </div>

      <div class="metric-block">
        <span class="metric-label">Token 用量</span>
        <strong>{{ tokenTotal }}</strong>
        <span>近 {{ usageDays }} 天</span>
      </div>

      <div class="metric-block">
        <span class="metric-label">Agent 成功率</span>
        <strong>{{ evalSuccessRate }}</strong>
        <span>{{ evalRunText }}</span>
      </div>
    </div>

    <div class="ops-details">
      <div class="detail-group">
        <span class="detail-label">Bridge</span>
        <strong>{{ snapshot.health?.service || 'hermes-bridge' }}</strong>
        <span>{{ snapshot.health?.hermes_reachable ? 'Hermès 可达' : 'Hermès 未确认' }}</span>
      </div>
      <div class="detail-group">
        <span class="detail-label">模型</span>
        <strong>{{ modelName }}</strong>
        <span>{{ modelProvider }}</span>
      </div>
      <div class="detail-group">
        <span class="detail-label">能力面</span>
        <strong>{{ capabilityText }}</strong>
        <span>{{ cronCount }} 个定时任务</span>
      </div>
      <div class="detail-group">
        <span class="detail-label">配置</span>
        <strong>{{ configText }}</strong>
        <span>Gateway {{ status?.gateway_running ? '运行中' : '未运行' }}</span>
      </div>
    </div>

    <div v-if="signals.length > 0" class="signal-list">
      <div v-for="signal in signals" :key="signal.text" class="signal-item" :class="signal.tone">
        <span class="signal-dot"></span>
        <span>{{ signal.text }}</span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface OverviewTask {
  task_id: string
  status: 'running' | 'pending' | 'completed'
  message_count?: number
}

interface OverviewLog {
  type: 'info' | 'warning' | 'error' | 'debug'
}

interface OverviewHistoryItem {
  input_tokens?: number
  output_tokens?: number
}

interface OverviewSnapshot {
  health?: Record<string, any> | null
  analytics?: Record<string, any> | null
  evalSummary?: Record<string, any> | null
  modelInfo?: Record<string, any> | null
  config?: Record<string, any> | null
  skills?: Record<string, any> | any[] | null
  cronJobs?: Record<string, any> | any[] | null
  plugins?: Record<string, any> | any[] | null
}

const props = defineProps<{
  status: Record<string, any> | null
  isConnected: boolean
  tasks: OverviewTask[]
  logs: OverviewLog[]
  history: OverviewHistoryItem[]
  snapshot: OverviewSnapshot
  loading?: boolean
}>()

const emit = defineEmits<{
  refresh: []
}>()

const activeTaskCount = computed(() =>
  props.tasks.filter(task => task.status === 'running' || task.status === 'pending').length
)

const errorLogCount = computed(() => props.logs.filter(log => log.type === 'error').length)
const warningLogCount = computed(() => props.logs.filter(log => log.type === 'warning').length)

const totalMessages = computed(() =>
  props.tasks.reduce((sum, task) => sum + (task.message_count || 0), 0)
)

const historyTokenTotal = computed(() =>
  props.history.reduce((sum, item) => sum + (item.input_tokens || 0) + (item.output_tokens || 0), 0)
)

const analyticsTokenTotal = computed(() => {
  const analytics = props.snapshot.analytics || {}
  const direct = analytics.total_tokens || analytics.tokens || analytics.token_count
  if (typeof direct === 'number') return direct

  const usage = analytics.usage || analytics.data || analytics.days
  if (!Array.isArray(usage)) return 0
  return usage.reduce((sum: number, item: any) => {
    return sum + (item.total_tokens || item.tokens || item.input_tokens || 0) + (item.output_tokens || 0)
  }, 0)
})

const tokenTotal = computed(() => formatNumber(analyticsTokenTotal.value || historyTokenTotal.value))

const usageDays = computed(() => {
  const analytics = props.snapshot.analytics || {}
  if (typeof analytics.days === 'number') return analytics.days
  const data = analytics.usage || analytics.data
  return Array.isArray(data) && data.length > 0 ? data.length : 7
})

const evalSuccessRate = computed(() => {
  const summary = props.snapshot.evalSummary || {}
  const rate = typeof summary.success_rate === 'number' ? summary.success_rate : 0
  return `${Math.round(rate * 100)}%`
})

const evalRunText = computed(() => {
  const summary = props.snapshot.evalSummary || {}
  const total = summary.total_runs || 0
  const errors = summary.error_runs || 0
  return `${total} runs / ${errors} errors`
})

const healthScore = computed(() => {
  let score = 100
  if (!props.status?.gateway_running) score -= 30
  if (!props.isConnected) score -= 20
  if (errorLogCount.value > 0) score -= Math.min(20, errorLogCount.value * 4)
  if (warningLogCount.value > 3) score -= 8
  if (activeTaskCount.value === 0) score -= 5
  return Math.max(0, score)
})

const healthTone = computed(() => {
  if (healthScore.value >= 80) return 'good'
  if (healthScore.value >= 55) return 'warn'
  return 'bad'
})

const healthLabel = computed(() => {
  if (healthScore.value >= 80) return '稳定'
  if (healthScore.value >= 55) return '需要关注'
  return '需要介入'
})

const healthReason = computed(() => {
  if (!props.status?.gateway_running) return 'Gateway 未运行或未确认'
  if (!props.isConnected) return '实时推送未连接'
  if (errorLogCount.value > 0) return '最近日志包含错误'
  if (activeTaskCount.value > 0) return '有任务正在执行'
  return '当前没有活跃任务'
})

const summaryText = computed(() => {
  if (healthScore.value >= 80) return '系统处于可观察、可操作状态'
  if (healthScore.value >= 55) return '部分信号异常，建议查看详情'
  return '关键运行信号异常，建议优先排查'
})

const modelName = computed(() => {
  const info = props.snapshot.modelInfo || {}
  return info.model || info.name || info.current_model || props.status?.model || '未确认'
})

const modelProvider = computed(() => {
  const info = props.snapshot.modelInfo || {}
  return info.provider || info.vendor || info.platform || '模型信息'
})

const skillCount = computed(() => getCollectionCount(props.snapshot.skills, ['skills']))
const pluginCount = computed(() => getCollectionCount(props.snapshot.plugins, ['plugins']))
const cronCount = computed(() => getCollectionCount(props.snapshot.cronJobs, ['jobs', 'cron_jobs']))

const capabilityText = computed(() => `${skillCount.value} Skills / ${pluginCount.value} Plugins`)

const configText = computed(() => {
  const config = props.snapshot.config || {}
  return config.profile || config.environment || config.mode || '默认配置'
})

const signals = computed(() => {
  const result: Array<{ text: string; tone: 'good' | 'warn' | 'bad' }> = []
  if (!props.status?.gateway_running) {
    result.push({ text: 'Gateway 未运行，任务数据可能不是实时状态', tone: 'bad' })
  }
  if (!props.isConnected) {
    result.push({ text: 'SSE 实时推送断开，页面正在依赖轮询数据', tone: 'warn' })
  }
  if (errorLogCount.value > 0) {
    result.push({ text: `最近抓取到 ${errorLogCount.value} 条错误日志`, tone: 'bad' })
  }
  if (activeTaskCount.value > 0 && totalMessages.value === 0) {
    result.push({ text: '存在活跃任务但消息数为 0，可能刚启动或未产生输出', tone: 'warn' })
  }
  if (result.length === 0) {
    result.push({ text: '当前没有需要立即处理的运行信号', tone: 'good' })
  }
  return result
})

function getCollectionCount(value: unknown, keys: string[]): number {
  if (Array.isArray(value)) return value.length
  if (!value || typeof value !== 'object') return 0
  const record = value as Record<string, unknown>
  for (const key of keys) {
    const nested = record[key]
    if (Array.isArray(nested)) return nested.length
  }
  return 0
}

function formatNumber(value: number): string {
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`
  return String(value)
}
</script>

<style scoped>
.ops-overview {
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
  overflow: hidden;
}

.overview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-subtle);
}

.overview-header h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 700;
}

.overview-header p {
  margin: 2px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
}

.overview-refresh {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-width: 74px;
  height: 34px;
  padding: 0 14px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}

.overview-refresh:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.spinner {
  width: 12px;
  height: 12px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.overview-grid {
  display: grid;
  grid-template-columns: minmax(240px, 1.2fr) repeat(4, minmax(140px, 1fr));
  border-bottom: 1px solid var(--border-subtle);
}

.health-block,
.metric-block {
  min-height: 132px;
  padding: 22px 24px;
  border-right: 1px solid var(--border-subtle);
}

.metric-block:last-child {
  border-right: 0;
}

.health-block {
  display: flex;
  align-items: center;
  gap: 18px;
}

.health-ring {
  width: 78px;
  height: 78px;
  flex: 0 0 78px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: conic-gradient(var(--success-color) calc(var(--score, 1) * 1%), var(--bg-tertiary) 0);
  border: 1px solid var(--border-color);
}

.health-ring.good {
  color: var(--success-color);
}

.health-ring.warn {
  color: var(--warning-color);
}

.health-ring.bad {
  color: var(--error-color);
}

.health-ring span {
  width: 56px;
  height: 56px;
  display: grid;
  place-items: center;
  background: var(--bg-primary);
  border-radius: 50%;
  font-size: 20px;
  font-weight: 800;
}

.health-copy,
.metric-block,
.detail-group {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.eyebrow,
.metric-label,
.detail-label {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.health-copy strong,
.metric-block strong,
.detail-group strong {
  margin-top: 4px;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 700;
}

.metric-block strong {
  font-size: 28px;
  line-height: 1.2;
}

.health-copy span:last-child,
.metric-block span:last-child,
.detail-group span:last-child {
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 12px;
}

.ops-details {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border-bottom: 1px solid var(--border-subtle);
}

.detail-group {
  min-height: 92px;
  padding: 18px 24px;
  border-right: 1px solid var(--border-subtle);
}

.detail-group:last-child {
  border-right: 0;
}

.signal-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 16px 24px;
  background: var(--bg-secondary);
}

.signal-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 32px;
  padding: 7px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  background: var(--bg-primary);
  font-size: 12px;
}

.signal-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--success-color);
}

.signal-item.warn .signal-dot {
  background: var(--warning-color);
}

.signal-item.bad .signal-dot {
  background: var(--error-color);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1200px) {
  .overview-grid,
  .ops-details {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .overview-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .overview-grid,
  .ops-details {
    grid-template-columns: 1fr;
  }

  .health-block,
  .metric-block,
  .detail-group {
    border-right: 0;
    border-bottom: 1px solid var(--border-subtle);
  }
}
</style>
