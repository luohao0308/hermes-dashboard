<template>
  <div class="review-dashboard">
    <!-- GitHub PR 列表 -->
    <div class="section-header">
      <h3>GitHub Pull Requests</h3>
      <div class="header-actions">
        <input
          v-model="repo"
          class="repo-input"
          placeholder="owner/repo"
          @keyup.enter="fetchPRs"
        />
        <button class="btn-refresh" @click="fetchPRs">刷新</button>
      </div>
    </div>

    <div v-if="prsLoading" class="loading">加载中...</div>
    <div v-else-if="prs.length === 0" class="empty">
      {{ repo ? '该仓库暂无 PR' : '请输入 GitHub 仓库地址（如 luohao0308/hermes-dashboard）' }}
    </div>
    <div v-else class="pr-list">
      <div v-for="pr in prs" :key="pr.number" class="pr-card">
        <div class="pr-header">
          <span class="pr-number">#{{ pr.number }}</span>
          <span class="pr-title">{{ pr.title }}</span>
          <span v-if="pr.draft" class="pr-draft">草稿</span>
        </div>
        <div class="pr-meta">
          <span>作者: {{ pr.author }}</span>
          <span>{{ formatDate(pr.updated_at) }}</span>
          <a :href="pr.html_url" target="_blank" class="pr-link">在 GitHub 查看</a>
        </div>
        <div class="pr-actions">
          <button
            class="btn-review"
            :disabled="reviewingPR === pr.number"
            @click="triggerReview(pr.number)"
          >
            {{ reviewingPR === pr.number ? '审查中...' : '开始审查' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 审查记录 -->
    <div class="section-header" style="margin-top: 32px;">
      <h3>审查记录</h3>
      <button class="btn-refresh" @click="fetchReviews">刷新</button>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_reviews }}</div>
        <div class="stat-label">总审查数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.completed_reviews }}</div>
        <div class="stat-label">已完成</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${{ stats.average_cost_usd }}</div>
        <div class="stat-label">平均成本</div>
      </div>
    </div>

    <div v-if="reviewsLoading" class="loading">加载中...</div>
    <div v-else-if="reviews.length === 0" class="empty">暂无审查记录</div>
    <div v-else class="review-list">
      <div
        v-for="review in reviews"
        :key="review.id"
        class="review-card"
        @click="$emit('view-detail', review.id)"
      >
        <div class="review-header">
          <span class="review-repo">{{ review.repo }}</span>
          <span class="review-pr">#{{ review.pr_number }}</span>
          <span :class="['review-status', `status-${review.status}`]">{{ statusLabel(review.status) }}</span>
        </div>
        <div class="review-title">{{ review.pr_title }}</div>
        <div class="review-meta">
          <span>作者: {{ review.pr_author }}</span>
          <span>{{ review.findings.length }} 个发现</span>
          <span>{{ review.models_used.join(', ') }}</span>
        </div>
      </div>
    </div>

    <!-- 审查结果弹窗 -->
    <div v-if="reviewResult" class="review-modal" @click.self="reviewResult = null">
      <div class="modal-content">
        <div class="modal-header">
          <h3>审查结果 - PR #{{ reviewResult.pr_number }}</h3>
          <button class="btn-close" @click="reviewResult = null">&times;</button>
        </div>
        <div class="modal-body">
          <div class="result-summary">
            <span>状态: {{ statusLabel(reviewResult.status) }}</span>
            <span>发现: {{ reviewResult.findings?.length || 0 }} 个问题</span>
            <span>模型: {{ reviewResult.models_used?.join(', ') }}</span>
          </div>
          <div v-if="reviewResult.findings?.length" class="findings-list">
            <div v-for="(f, i) in reviewResult.findings" :key="i" class="finding-item">
              <div class="finding-header">
                <span :class="['severity-tag', `sev-${f.severity}`]">{{ f.severity }}</span>
                <span class="finding-title">{{ f.title }}</span>
              </div>
              <div class="finding-desc">{{ f.description }}</div>
              <div v-if="f.file_path" class="finding-location">{{ f.file_path }}:{{ f.line_number }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { API_BASE } from '../config'

defineEmits<{ 'view-detail': [id: string] }>()

interface Review {
  id: string
  repo: string
  pr_number: number
  pr_title: string
  pr_author: string
  status: string
  findings: any[]
  models_used: string[]
  cost_usd: number
  started_at: string
}

interface PullRequest {
  number: number
  title: string
  author: string
  state: string
  created_at: string
  updated_at: string
  html_url: string
  draft: boolean
}

const repo = ref('luohao0308/hermes-dashboard')
const prs = ref<PullRequest[]>([])
const prsLoading = ref(false)
const reviewingPR = ref<number | null>(null)
const reviewResult = ref<any>(null)

const stats = ref({ total_reviews: 0, completed_reviews: 0, average_cost_usd: 0 })
const reviews = ref<Review[]>([])
const reviewsLoading = ref(false)

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    completed: '已完成',
    reviewing: '审查中',
    pending: '待处理',
    failed: '失败',
  }
  return labels[status] || status
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function fetchPRs() {
  if (!repo.value) return
  prsLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/github/prs?repo=${encodeURIComponent(repo.value)}&state=open&limit=20`)
    if (res.ok) {
      const data = await res.json()
      prs.value = data.pulls || []
    }
  } catch {
    // API not available
  } finally {
    prsLoading.value = false
  }
}

async function triggerReview(prNumber: number) {
  reviewingPR.value = prNumber
  try {
    const res = await fetch(`${API_BASE}/api/reviews/trigger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo: repo.value, pr_number: prNumber }),
    })
    if (res.ok) {
      const data = await res.json()
      reviewResult.value = data
      await fetchReviews()
    } else {
      const err = await res.json()
      alert(`审查失败: ${err.detail || '未知错误'}`)
    }
  } catch {
    alert('审查请求失败，请检查网络连接')
  } finally {
    reviewingPR.value = null
  }
}

async function fetchReviews() {
  reviewsLoading.value = true
  try {
    const [statsRes, reviewsRes] = await Promise.all([
      fetch(`${API_BASE}/api/reviews/stats`),
      fetch(`${API_BASE}/api/reviews?limit=20`),
    ])
    if (statsRes.ok) stats.value = await statsRes.json()
    if (reviewsRes.ok) {
      const data = await reviewsRes.json()
      reviews.value = data.reviews || []
    }
  } catch {
    // API not available yet
  } finally {
    reviewsLoading.value = false
  }
}

onMounted(() => {
  fetchPRs()
  fetchReviews()
})
</script>

<style scoped>
.review-dashboard { display: flex; flex-direction: column; gap: 24px; }
.section-header { display: flex; justify-content: space-between; align-items: center; }
.section-header h3 { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.header-actions { display: flex; gap: 8px; align-items: center; }
.repo-input { padding: 6px 12px; background: var(--bg-tertiary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); color: var(--text-primary); font-size: 13px; width: 260px; }
.repo-input:focus { outline: none; border-color: var(--accent-color); }
.btn-refresh { padding: 6px 14px; background: var(--accent-soft); color: var(--accent-color); border: none; border-radius: var(--radius-md); font-size: 12px; cursor: pointer; }
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.stat-card { background: var(--glass-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 24px; text-align: center; }
.stat-value { font-size: 32px; font-weight: 700; color: var(--text-primary); }
.stat-label { font-size: 13px; color: var(--text-muted); margin-top: 4px; }

/* PR 卡片 */
.pr-list { display: flex; flex-direction: column; gap: 12px; }
.pr-card { background: var(--glass-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 16px 20px; transition: border-color 0.2s; }
.pr-card:hover { border-color: var(--accent-color); }
.pr-header { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.pr-number { color: var(--accent-color); font-size: 13px; font-weight: 600; }
.pr-title { font-size: 14px; color: var(--text-primary); flex: 1; }
.pr-draft { font-size: 10px; padding: 2px 6px; background: var(--bg-tertiary); border-radius: 4px; color: var(--text-muted); }
.pr-meta { display: flex; gap: 16px; font-size: 12px; color: var(--text-muted); margin-bottom: 10px; }
.pr-link { color: var(--accent-color); text-decoration: none; }
.pr-link:hover { text-decoration: underline; }
.pr-actions { display: flex; justify-content: flex-end; }
.btn-review { padding: 6px 16px; background: var(--accent-color); color: white; border: none; border-radius: var(--radius-md); font-size: 12px; cursor: pointer; }
.btn-review:disabled { opacity: 0.6; cursor: not-allowed; }

/* 审查记录 */
.review-card { background: var(--glass-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 16px 20px; cursor: pointer; transition: border-color 0.2s; }
.review-card:hover { border-color: var(--accent-color); }
.review-header { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.review-repo { font-weight: 600; font-size: 13px; color: var(--text-primary); }
.review-pr { color: var(--accent-color); font-size: 13px; }
.review-status { margin-left: auto; font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 600; }
.status-completed { background: rgba(80, 250, 123, 0.15); color: #50fa7b; }
.status-reviewing { background: rgba(139, 233, 253, 0.15); color: #8be9fd; }
.status-pending { background: rgba(255, 183, 77, 0.15); color: #ffb74d; }
.status-failed { background: rgba(255, 85, 85, 0.15); color: #ff5555; }
.review-title { font-size: 14px; color: var(--text-primary); margin-bottom: 6px; }
.review-meta { display: flex; gap: 16px; font-size: 12px; color: var(--text-muted); }
.loading, .empty { text-align: center; padding: 40px; color: var(--text-muted); font-size: 14px; }

/* 弹窗 */
.review-modal { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal-content { background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); width: 90%; max-width: 700px; max-height: 80vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 20px; border-bottom: 1px solid var(--border-subtle); }
.modal-header h3 { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.btn-close { background: none; border: none; font-size: 20px; color: var(--text-muted); cursor: pointer; }
.modal-body { padding: 20px; }
.result-summary { display: flex; gap: 16px; font-size: 13px; color: var(--text-secondary); margin-bottom: 16px; }
.findings-list { display: flex; flex-direction: column; gap: 12px; }
.finding-item { background: var(--glass-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 12px; }
.finding-header { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.severity-tag { font-size: 10px; padding: 2px 8px; border-radius: 10px; font-weight: 700; text-transform: uppercase; }
.sev-critical { background: rgba(255, 85, 85, 0.15); color: #ff5555; }
.sev-high { background: rgba(255, 183, 77, 0.15); color: #ffb74d; }
.sev-medium { background: rgba(139, 233, 253, 0.15); color: #8be9fd; }
.sev-low { background: rgba(80, 250, 123, 0.15); color: #50fa7b; }
.finding-title { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.finding-desc { font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }
.finding-location { font-size: 11px; color: var(--text-muted); font-family: monospace; }
</style>
