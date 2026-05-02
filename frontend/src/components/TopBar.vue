<template>
  <header class="topbar">
    <div class="topbar-left">
      <h1 class="page-title">{{ title }}</h1>
    </div>
    <div class="topbar-right">
      <!-- Gateway Status -->
      <div v-if="hermesStatus" class="status-badges">
        <div class="badge">
          <span class="status-dot" :class="hermesStatus.gateway_running ? 'success' : 'error'"></span>
          <span>{{ hermesStatus.gateway_running ? t('topbar.gatewayRunning') : t('topbar.gatewayStopped') }}</span>
        </div>
        <div class="badge">
          <span>v{{ hermesStatus.version || 'N/A' }}</span>
        </div>
      </div>
      <!-- Language Switcher -->
      <button class="btn btn-lang" @click="toggleLocale" :title="currentLocale === 'zh-CN' ? 'Switch to English' : '切换到中文'">
        {{ currentLocale === 'zh-CN' ? 'EN' : '中' }}
      </button>
      <!-- Refresh Button -->
      <button class="btn btn-secondary" @click="$emit('refresh')" :disabled="loading">
        <span :class="{ spinning: loading }">⟳</span>
        {{ loading ? t('topbar.refreshing') : t('topbar.refresh') }}
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { setLocale, getLocale } from '../i18n'

const { t } = useI18n()

const currentLocale = computed(() => getLocale())

function toggleLocale() {
  const next = currentLocale.value === 'zh-CN' ? 'en-US' : 'zh-CN'
  setLocale(next as 'zh-CN' | 'en-US')
}

defineProps<{
  title: string
  hermesStatus?: Record<string, any> | null
  loading?: boolean
}>()

defineEmits<{
  refresh: []
}>()
</script>

<style scoped>
.topbar {
  height: var(--topbar-height);
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
}

.topbar-left {
  display: flex;
  align-items: center;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-badges {
  display: flex;
  align-items: center;
  gap: 12px;
}

.badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  padding: 8px 14px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  font-weight: 500;
}

.btn-lang {
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 36px;
  text-align: center;
}

.btn-lang:hover {
  color: var(--accent-color);
  border-color: var(--accent-color);
}

.btn.spinning {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
