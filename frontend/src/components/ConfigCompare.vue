<template>
  <div class="config-compare">
    <div class="panel-header">
      <div>
        <h2>{{ t('configCompare.title') }}</h2>
        <p class="subtitle">{{ t('configCompare.title') }}</p>
      </div>
      <button class="refresh-btn" :disabled="loading" @click="$emit('refresh')">
        <span v-if="loading" class="spinner"></span>
        {{ loading ? t('common.loading') : t('common.refresh') }}
      </button>
    </div>

    <!-- Version Selectors -->
    <div class="selector-row">
      <div class="selector-group">
        <label>{{ t('configCompare.beforeVersion') }}</label>
        <select v-model="beforeId" class="filter-select">
          <option value="">{{ t('configCompare.beforeVersion') }}...</option>
          <option v-for="v in versions" :key="v.id" :value="v.id">
            {{ v.version }} ({{ v.config_type }})
          </option>
        </select>
      </div>
      <div class="selector-group">
        <label>{{ t('configCompare.afterVersion') }}</label>
        <select v-model="afterId" class="filter-select">
          <option value="">{{ t('configCompare.afterVersion') }}...</option>
          <option v-for="v in versions" :key="v.id" :value="v.id">
            {{ v.version }} ({{ v.config_type }})
          </option>
        </select>
      </div>
      <button
        class="compare-btn"
        :disabled="!beforeId || !afterId || beforeId === afterId"
        @click="doCompare"
      >
        {{ t('configCompare.compare') }}
      </button>
    </div>

    <!-- Comparison Result -->
    <div v-if="result" class="compare-result">
      <!-- Score Delta -->
      <div class="delta-card">
        <span class="delta-label">{{ t('configCompare.scoreDelta') }}</span>
        <strong
          class="delta-value"
          :class="{
            'delta-positive': (result.score_delta ?? 0) > 0,
            'delta-negative': (result.score_delta ?? 0) < 0,
          }"
        >
          {{ result.score_delta != null ? (result.score_delta > 0 ? '+' : '') + result.score_delta.toFixed(1) : 'N/A' }}
        </strong>
        <span v-if="result.requires_approval" class="approval-badge">{{ t('configCompare.requiresApproval') }}</span>
        <span v-if="result.recommended" class="recommend-badge">{{ t('configCompare.recommended') }}</span>
      </div>

      <!-- Recommendation Notice -->
      <div v-if="result.recommended && result.requires_approval" class="recommend-notice">
        <span class="notice-icon">🛡</span>
        <div>
          <strong>{{ t('configCompare.recommendNoticeTitle') }}</strong>
          <p>{{ t('configCompare.recommendNoticeBody') }}</p>
        </div>
      </div>

      <!-- Changes -->
      <div v-if="result.changes.length > 0" class="changes-section">
        <h3>{{ t('configCompare.changes', { count: result.changes.length }) }}</h3>
        <div class="changes-list">
          <div v-for="change in result.changes" :key="change.field" class="change-item">
            <span class="change-field">{{ change.field }}</span>
            <div class="change-values">
              <span class="change-before">{{ formatValue(change.before) }}</span>
              <span class="change-arrow">→</span>
              <span class="change-after">{{ formatValue(change.after) }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="no-changes">
        <span>{{ t('configCompare.noDifferences') }}</span>
      </div>

      <!-- Version Details -->
      <div class="version-details">
        <div class="version-card">
          <h4>{{ t('configCompare.before') }}: {{ result.before.version }}</h4>
          <div class="version-meta">
            <span>{{ t('configCompare.type') }}: {{ result.before.config_type }}</span>
            <span>{{ t('configCompare.score') }}: {{ result.before.evaluation_score ?? 'N/A' }}</span>
            <span>{{ t('configCompare.by') }}: {{ result.before.created_by ?? 'unknown' }}</span>
          </div>
        </div>
        <div class="version-card">
          <h4>{{ t('configCompare.after') }}: {{ result.after.version }}</h4>
          <div class="version-meta">
            <span>{{ t('configCompare.type') }}: {{ result.after.config_type }}</span>
            <span>{{ t('configCompare.score') }}: {{ result.after.evaluation_score ?? 'N/A' }}</span>
            <span>{{ t('configCompare.by') }}: {{ result.after.created_by ?? 'unknown' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="!result && !loading" class="empty-state">
      <span class="empty-icon">🔄</span>
      <span>{{ t('configCompare.selectVersions') }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
import type { ConfigVersionItem, ConfigCompareData } from '../types'

defineProps<{
  versions: ConfigVersionItem[]
  result: ConfigCompareData | null
  loading?: boolean
}>()

const emit = defineEmits<{
  compare: [beforeId: string, afterId: string]
  refresh: []
}>()

const beforeId = ref('')
const afterId = ref('')

function doCompare() {
  if (beforeId.value && afterId.value) {
    emit('compare', beforeId.value, afterId.value)
  }
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return '∅'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}
</script>

<style scoped>
.config-compare {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.panel-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.subtitle {
  font-size: 13px;
  color: var(--text-muted);
  margin: 4px 0 0;
}

.selector-row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
}

.selector-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.selector-group label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.filter-select {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  font-size: 13px;
  color: var(--text-secondary);
  outline: none;
}

.compare-btn {
  padding: 10px 24px;
  background: var(--accent-color);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.compare-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.compare-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.refresh-btn:hover:not(:disabled) {
  background: var(--accent-soft);
  border-color: var(--accent-color);
  color: var(--accent-color);
}

.spinner {
  width: 10px;
  height: 10px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Result */
.compare-result {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.delta-card {
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.delta-label {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
}

.delta-value {
  font-size: 28px;
  font-weight: 700;
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.delta-positive {
  color: var(--color-success, #22c55e);
}

.delta-negative {
  color: var(--color-error, #ef4444);
}

.approval-badge {
  margin-left: auto;
  padding: 4px 12px;
  background: var(--color-warning-bg, #fef3c7);
  color: var(--color-warning, #d97706);
  border-radius: var(--radius-pill);
  font-size: 11px;
  font-weight: 600;
}

.recommend-badge {
  padding: 4px 12px;
  background: rgba(34, 197, 94, 0.15);
  color: #16a34a;
  border-radius: var(--radius-pill);
  font-size: 11px;
  font-weight: 600;
}

.recommend-notice {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  padding: 16px 20px;
  background: var(--glass-bg);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: var(--radius-lg);
}

.notice-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.recommend-notice strong {
  display: block;
  font-size: 13px;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.recommend-notice p {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary);
}

.changes-section {
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 24px;
}

.changes-section h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 16px;
}

.changes-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.change-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.change-field {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.change-values {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.change-before {
  color: var(--color-error, #ef4444);
  text-decoration: line-through;
}

.change-arrow {
  color: var(--text-muted);
}

.change-after {
  color: var(--color-success, #22c55e);
}

.no-changes {
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
  font-size: 13px;
}

.version-details {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.version-card {
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.version-card h4 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px;
}

.version-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

/* Empty */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  color: var(--text-muted);
  gap: 12px;
  font-size: 13px;
}

.empty-icon {
  font-size: 32px;
}
</style>
