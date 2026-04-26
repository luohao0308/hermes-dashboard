<template>
  <aside class="sidebar">
    <!-- Logo -->
    <div class="sidebar-logo">
      <div class="logo-icon">H</div>
      <span class="logo-text">Hermès</span>
    </div>

    <!-- 导航菜单 -->
    <nav class="sidebar-nav">
      <a
        v-for="item in navItems"
        :key="item.id"
        :class="['nav-item', { active: activeNav === item.id }]"
        @click="handleNavClick(item.id)"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span class="nav-label">{{ item.label }}</span>
      </a>
    </nav>

    <!-- 底部信息 -->
    <div class="sidebar-footer">
      <div class="connection-status">
        <span class="status-dot" :class="isConnected ? 'success' : 'error'"></span>
        <span class="status-text">{{ isConnected ? '已连接' : '未连接' }}</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface NavItem {
  id: string
  label: string
  icon: string
}

defineProps<{
  isConnected?: boolean
}>()

const emit = defineEmits<{
  'nav-change': [navId: string]
}>()

const navItems: NavItem[] = [
  { id: 'dashboard', label: '概览', icon: '◈' },
  { id: 'terminal', label: '终端', icon: '▸' },
  { id: 'tasks', label: '任务', icon: '◎' },
  { id: 'logs', label: '日志', icon: '☰' },
  { id: 'history', label: '历史', icon: '◷' },
  { id: 'chat', label: '聊天', icon: '💬' },
  { id: 'agents', label: '配置', icon: '🤖' },
]

const activeNav = ref('dashboard')

function handleNavClick(navId: string) {
  activeNav.value = navId
  emit('nav-change', navId)
}
</script>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  background: var(--bg-primary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  z-index: 100;
}

.sidebar-logo {
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px;
  border-bottom: 1px solid var(--border-color);
}

.logo-icon {
  width: 28px;
  height: 28px;
  background: var(--text-primary);
  color: white;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
}

.logo-text {
  font-weight: 600;
  font-size: 15px;
  color: var(--text-primary);
}

.sidebar-nav {
  flex: 1;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  text-decoration: none;
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: 13px;
}

.nav-item:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-weight: 500;
}

.nav-icon {
  font-size: 16px;
  opacity: 0.7;
}

.nav-item.active .nav-icon {
  opacity: 1;
}

.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid var(--border-color);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

.status-text {
  color: var(--text-secondary);
}
</style>
