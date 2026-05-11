<template>
  <header class="topbar">
    <div class="topbar-left">
      <h1 class="page-title">{{ title }}</h1>
      <div class="title-divider"></div>
      <div class="live-status">
        <span class="status-pill" :class="hermesStatus?.gateway_running ? 'ok' : 'bad'">
          <span class="status-dot" :class="hermesStatus?.gateway_running ? 'success' : 'error'"></span>
          {{ hermesStatus?.gateway_running ? t('topbar.gatewayRunning') : t('topbar.gatewayStopped') }}
        </span>
      </div>
    </div>

    <div class="topbar-right">
      <button class="icon-btn" type="button" @click="$emit('refresh')" :disabled="loading" :title="t('topbar.refresh')">
        <RefreshCcw :size="16" :class="{ spinning: loading }" />
        <span class="refresh-label">{{ loading ? t('topbar.refreshing') : t('topbar.refresh') }}</span>
      </button>
      <button class="locale-btn" type="button" @click="toggleLocale" :title="currentLocale === 'zh-CN' ? 'Switch to English' : '切换到中文'">
        {{ currentLocale === 'zh-CN' ? 'EN' : '中' }}
      </button>
      <div class="version-badge">
        <Globe2 :size="14" />
        <span>v{{ hermesStatus?.version || 'N/A' }}</span>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Globe2, RefreshCcw } from 'lucide-vue-next'
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
  position: sticky;
  top: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 0 28px;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--border-color);
}

.topbar-left,
.topbar-right,
.live-status,
.version-badge {
  display: flex;
  align-items: center;
}

.topbar-left {
  min-width: 0;
  gap: 14px;
}

.page-title {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 0;
  white-space: nowrap;
}

.title-divider {
  width: 1px;
  height: 18px;
  background: var(--border-color);
}

.live-status {
  gap: 10px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 28px;
  padding: 0 10px;
  border-radius: var(--radius-pill);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.status-pill.ok {
  color: #047857;
  background: #ecfdf5;
}

.status-pill.bad {
  color: #b91c1c;
  background: #fef2f2;
}

.version-badge {
  gap: 5px;
  color: #94a3b8;
  font-size: 10px;
  font-weight: 700;
}

.topbar-right {
  gap: 10px;
}

.icon-btn,
.locale-btn,
.version-badge {
  height: 36px;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: #ffffff;
  color: #64748b;
  box-shadow: var(--shadow-sm);
}

.icon-btn {
  width: 36px;
  position: relative;
  display: grid;
  place-items: center;
  cursor: pointer;
}

.refresh-label {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

.icon-btn:hover,
.locale-btn:hover {
  color: var(--accent-color);
  background: var(--accent-soft);
}

.icon-btn:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.locale-btn {
  min-width: 38px;
  padding: 0 10px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 900;
}

.version-badge {
  gap: 7px;
  padding: 0 11px;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 980px) {
  .title-divider {
    display: none;
  }
}

@media (max-width: 640px) {
  .topbar {
    gap: 8px;
    padding: 0 14px;
  }

  .live-status {
    display: none;
  }

  .page-title {
    max-width: 128px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .topbar-right {
    gap: 6px;
  }

  .version-badge {
    padding: 0 8px;
  }
}
</style>
