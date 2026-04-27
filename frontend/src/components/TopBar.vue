<template>
  <header class="topbar">
    <div class="topbar-left">
      <h1 class="page-title">{{ title }}</h1>
    </div>
    <div class="topbar-right">
      <!-- Hermès 状态 -->
      <div v-if="hermesStatus" class="status-badges">
        <div class="badge">
          <span class="status-dot" :class="hermesStatus.gateway_running ? 'success' : 'error'"></span>
          <span>Gateway {{ hermesStatus.gateway_running ? '运行中' : '已停止' }}</span>
        </div>
        <div class="badge">
          <span>v{{ hermesStatus.version || 'N/A' }}</span>
        </div>
      </div>
      <!-- 刷新按钮 -->
      <button class="btn btn-secondary" @click="$emit('refresh')" :disabled="loading">
        <span :class="{ spinning: loading }">⟳</span>
        {{ loading ? '刷新中...' : '刷新' }}
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
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

.btn.spinning {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
