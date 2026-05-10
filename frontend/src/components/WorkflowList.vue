<template>
  <div class="workflow-list panel">
    <div class="section-header">
      <div>
        <h2 class="section-title">{{ t('workflows.title') }}</h2>
        <p class="section-subtitle">Compose, inspect and launch governed workflow definitions.</p>
      </div>
      <div class="header-actions">
        <button class="btn btn-primary" data-test="create-workflow" @click="$emit('create')">
          <Plus :size="15" />
          {{ t('workflows.createWorkflow') }}
        </button>
        <button class="btn" data-test="refresh-workflows" @click="$emit('refresh')" :disabled="loading">
          <RefreshCcw :size="15" :class="{ spinning: loading }" />
          {{ loading ? t('common.loading') : t('common.refresh') }}
        </button>
      </div>
    </div>

    <LoadingState v-if="loading" :message="t('workflows.loadingWorkflows')" />

    <EmptyState
      v-else-if="workflows.length === 0"
      :message="t('workflows.noWorkflows')"
    />

    <div v-else class="workflow-cards">
      <article
        v-for="wf in workflows"
        :key="wf.id"
        class="workflow-card"
        @click="$emit('select', wf)"
      >
        <div class="card-header">
          <div class="workflow-icon">
            <GitBranch :size="18" />
          </div>
          <div class="card-actions">
            <button class="card-action" type="button" @click.stop="$emit('edit', wf)" aria-label="Edit workflow">
              <Pencil :size="14" />
            </button>
            <span class="card-badge">v{{ wf.version }}</span>
          </div>
        </div>
        <span class="card-title">{{ wf.name }}</span>
        <p v-if="wf.description" class="card-desc">{{ wf.description }}</p>
        <div class="card-meta">
          <span class="meta-item">
            <Network :size="13" />
            {{ wf.nodes.length }} {{ t('workflows.nodes') }}
          </span>
          <span class="meta-item">
            <GitBranch :size="13" />
            {{ wf.edges.length }} {{ t('workflows.edges') }}
          </span>
          <span class="meta-item">
            <Clock3 :size="13" />
            Created {{ formatTime(wf.created_at) }}
          </span>
        </div>
        <ArrowUpRight class="card-arrow" :size="18" />
      </article>
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
import { ArrowUpRight, Clock3, GitBranch, Network, Pencil, Plus, RefreshCcw } from 'lucide-vue-next'
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
  create: []
  edit: [wf: WorkflowDefinition]
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
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.header-actions,
.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title {
  margin: 0;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 800;
}

.section-subtitle {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 12px;
}

.btn {
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 14px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  border: 1px solid var(--border-color);
  background: #ffffff;
  color: var(--text-secondary);
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
}

.btn:hover {
  border-color: #bfdbfe;
  color: var(--accent-color);
  background: var(--accent-soft);
}

.btn-primary {
  color: var(--accent-color);
  background: #eff6ff;
  border-color: #bfdbfe;
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.workflow-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.workflow-card {
  position: relative;
  min-height: 178px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: #ffffff;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  cursor: pointer;
  box-shadow: var(--glass-shadow);
  transition: all 0.2s ease;
}

.workflow-card:hover {
  border-color: #bfdbfe;
  box-shadow: 0 18px 40px rgba(37, 99, 235, 0.1);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-action {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: #ffffff;
  color: var(--text-muted);
  cursor: pointer;
}

.card-action:hover {
  border-color: #bfdbfe;
  color: var(--accent-color);
  background: var(--accent-soft);
}

.workflow-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  color: #059669;
  background: #ecfdf5;
}

.card-title {
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 900;
}

.card-badge {
  font-size: 11px;
  padding: 4px 9px;
  border-radius: var(--radius-pill);
  background: var(--accent-soft);
  color: var(--accent-color);
  font-weight: 900;
}

.card-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.4;
}

.card-meta {
  margin-top: auto;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  font-size: 12px;
  color: var(--text-muted);
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.card-arrow {
  position: absolute;
  right: 20px;
  bottom: 20px;
  color: #cbd5e1;
}

.workflow-card:hover .card-arrow {
  color: var(--accent-color);
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
  min-height: 32px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
  background: #ffffff;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
}

.pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 720px) {
  .section-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
  }

  .header-actions .btn {
    flex: 1;
  }

  .workflow-cards {
    grid-template-columns: 1fr;
  }

  .workflow-card {
    min-height: 168px;
  }
}
</style>
