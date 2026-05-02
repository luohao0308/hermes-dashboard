<template>
  <div class="workflow-list">
    <div class="section-header">
      <h2 class="section-title">{{ t('workflows.title') }}</h2>
      <button class="btn btn-primary" @click="$emit('refresh')">{{ t('common.refresh') }}</button>
    </div>

    <LoadingState v-if="loading" :message="t('workflows.loadingWorkflows')" />

    <EmptyState
      v-else-if="workflows.length === 0"
      :message="t('workflows.noWorkflows')"
    />

    <div v-else class="workflow-cards">
      <div
        v-for="wf in workflows"
        :key="wf.id"
        class="workflow-card"
        @click="$emit('select', wf)"
      >
        <div class="card-header">
          <span class="card-title">{{ wf.name }}</span>
          <span class="card-badge">v{{ wf.version }}</span>
        </div>
        <p v-if="wf.description" class="card-desc">{{ wf.description }}</p>
        <div class="card-meta">
          <span class="meta-item">{{ wf.nodes.length }} {{ t('workflows.nodes') }}</span>
          <span class="meta-item">{{ wf.edges.length }} {{ t('workflows.edges') }}</span>
          <span class="meta-item">Created {{ formatTime(wf.created_at) }}</span>
        </div>
      </div>
    </div>

    <div v-if="total > limit" class="pagination">
      <button :disabled="offset === 0" @click="$emit('pageChange', offset - limit)">{{ t('common.prev') }}</button>
      <span>{{ offset + 1 }}-{{ Math.min(offset + limit, total) }} / {{ total }}</span>
      <button :disabled="offset + limit >= total" @click="$emit('pageChange', offset + limit)">{{ t('common.next') }}</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { WorkflowDefinition } from '../types'
import LoadingState from './LoadingState.vue'
import EmptyState from './EmptyState.vue'

const { t } = useI18n()

defineProps<{
  workflows: WorkflowDefinition[]
  total: number
  limit: number
  offset: number
  loading: boolean
}>()

defineEmits<{
  refresh: []
  select: [wf: WorkflowDefinition]
  pageChange: [offset: number]
}>()

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString()
  } catch {
    return iso
  }
}
</script>

<style scoped>
.workflow-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.btn {
  padding: 8px 16px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border-subtle);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  transition: all 0.2s;
}

.btn:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.btn-primary {
  background: var(--accent-color);
  color: white;
  border-color: var(--accent-color);
}

.btn-primary:hover {
  opacity: 0.9;
}

.workflow-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.workflow-card {
  background: var(--glass-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.workflow-card:hover {
  border-color: var(--accent-color);
  box-shadow: var(--shadow-glow);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.card-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--accent-soft);
  color: var(--accent-color);
  font-weight: 600;
}

.card-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0 0 12px;
  line-height: 1.4;
}

.card-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-muted);
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 16px;
  font-size: 13px;
  color: var(--text-secondary);
}

.pagination button {
  padding: 6px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px;
}

.pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
