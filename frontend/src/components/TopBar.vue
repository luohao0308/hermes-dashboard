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
          <span>{{ hermesStatus.active_connections || 0 }} 个活跃连接</span>
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
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.topbar-left {
  display: flex;
  align-items: center;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
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
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  padding: 4px 10px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.btn.spinning {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
