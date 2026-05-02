<template>
  <aside class="sidebar">
    <!-- Logo -->
    <div class="sidebar-logo">
      <div class="logo-icon">AI</div>
      <span class="logo-text">{{ t('sidebar.logoText') }}</span>
    </div>

    <!-- 导航菜单 -->
    <nav class="sidebar-nav">
      <div v-for="group in navGroups" :key="group.label" class="nav-group">
        <div class="nav-group-label">{{ group.label }}</div>
        <a
          v-for="item in group.items"
          :key="item.id"
          :class="['nav-item', { active: activeNav === item.id }]"
          @click="handleNavClick(item.id)"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ item.label }}</span>
        </a>
      </div>
    </nav>

    <!-- 底部信息 -->
    <div class="sidebar-footer">
      <div class="connection-status">
        <span class="status-dot" :class="isConnected ? 'success' : 'error'"></span>
        <span class="status-text">{{ isConnected ? t('sidebar.connected') : t('sidebar.disconnected') }}</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

interface NavItem {
  id: string
  label: string
  icon: string
}

interface NavGroup {
  label: string
  items: NavItem[]
}

defineProps<{
  isConnected?: boolean
}>()

const emit = defineEmits<{
  'nav-change': [navId: string]
}>()

const navGroups = computed<NavGroup[]>(() => [
  {
    label: t('navGroup.observe'),
    items: [
      { id: 'dashboard', label: t('nav.dashboard'), icon: '◈' },
      { id: 'runs', label: t('nav.runs'), icon: '▶' },
      { id: 'workflows', label: t('nav.workflows'), icon: '◇' },
    ],
  },
  {
    label: t('navGroup.govern'),
    items: [
      { id: 'approvals', label: t('nav.approvals'), icon: '☑' },
      { id: 'guardrails', label: t('nav.guardrails'), icon: '🛡' },
    ],
  },
  {
    label: t('navGroup.improve'),
    items: [
      { id: 'eval', label: t('nav.eval'), icon: '📊' },
      { id: 'config-compare', label: t('nav.configCompare'), icon: '⚖' },
      { id: 'knowledge', label: t('nav.knowledge'), icon: '◇' },
      { id: 'costs', label: t('nav.costs'), icon: '💰' },
    ],
  },
  {
    label: t('navGroup.integrate'),
    items: [
      { id: 'providers', label: t('nav.providers'), icon: '🧠' },
      { id: 'connectors', label: t('nav.connectors'), icon: '🔌' },
      { id: 'environments', label: t('nav.environments'), icon: '🌐' },
    ],
  },
  {
    label: t('navGroup.admin'),
    items: [
      { id: 'audit', label: t('nav.audit'), icon: '📋' },
      { id: 'system', label: t('nav.system'), icon: '⚙' },
      { id: 'agents', label: t('nav.agents'), icon: '◎' },
      { id: 'chat', label: t('nav.chat'), icon: '💬' },
      { id: 'terminal', label: t('nav.terminal'), icon: '▸' },
    ],
  },
])

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
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  z-index: 100;
}

.sidebar-logo {
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 24px;
  border-bottom: 1px solid var(--border-subtle);
}

.logo-icon {
  width: 36px;
  height: 36px;
  background: var(--gradient-prism);
  color: white;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  box-shadow: var(--shadow-glow);
}

.logo-text {
  font-weight: 600;
  font-size: 16px;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.sidebar-nav {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
}

.nav-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-group-label {
  padding: 0 16px 4px;
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 13px;
  font-weight: 500;
}

.nav-item:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--accent-soft);
  color: var(--accent-color);
  font-weight: 600;
}

.nav-icon {
  font-size: 18px;
  opacity: 0.8;
  width: 20px;
  text-align: center;
}

.nav-item.active .nav-icon {
  opacity: 1;
}

.sidebar-footer {
  padding: 20px 24px;
  border-top: 1px solid var(--border-subtle);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--text-muted);
  padding: 10px 14px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
}

.status-text {
  color: var(--text-secondary);
  font-weight: 500;
}
</style>
