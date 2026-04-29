<template>
  <div class="review-dashboard">
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

    <div class="section-header">
      <h3>最近审查</h3>
      <button class="btn-refresh" @click="fetchReviews">刷新</button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
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

const stats = ref({ total_reviews: 0, completed_reviews: 0, average_cost_usd: 0 })
const reviews = ref<Review[]>([])
const loading = ref(false)

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    completed: '已完成',
    reviewing: '审查中',
    pending: '待处理',
    failed: '失败',
  }
  return labels[status] || status
}

async function fetchReviews() {
  loading.value = true
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
    loading.value = false
  }
}

onMounted(fetchReviews)
</script>

<style scoped>
.review-dashboard { display: flex; flex-direction: column; gap: 24px; }
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.stat-card { background: var(--glass-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 24px; text-align: center; }
.stat-value { font-size: 32px; font-weight: 700; color: var(--text-primary); }
.stat-label { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
.section-header { display: flex; justify-content: space-between; align-items: center; }
.section-header h3 { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.btn-refresh { padding: 6px 14px; background: var(--accent-soft); color: var(--accent-color); border: none; border-radius: var(--radius-md); font-size: 12px; cursor: pointer; }
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
</style>
