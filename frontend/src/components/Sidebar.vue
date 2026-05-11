<template>
  <aside class="sidebar">
    <div class="sidebar-logo">
      <div class="logo-icon">AI</div>
      <span class="logo-text">{{ t('sidebar.logoText') }}</span>
    </div>

    <nav class="sidebar-nav">
      <div v-for="group in navGroups" :key="group.label" class="nav-group">
        <div class="nav-group-label">{{ group.label }}</div>
        <button
          v-for="item in group.items"
          :key="item.id"
          :class="['nav-item', { active: activeNav === item.id }]"
          type="button"
          @click="handleNavClick(item.id)"
        >
          <component :is="item.icon" class="nav-icon" :size="18" />
          <span class="nav-label">{{ item.label }}</span>
          <ChevronRight v-if="activeNav === item.id" class="nav-chevron" :size="14" />
        </button>
      </div>
    </nav>

    <div class="sidebar-footer">
      <div class="user-card">
        <div class="user-avatar">OP</div>
        <div class="user-meta">
          <span>Platform Ops</span>
          <small>Control Plane</small>
        </div>
      </div>
      <div class="connection-status">
        <span class="status-dot" :class="isConnected ? 'success' : 'error'"></span>
        <span class="status-text">{{ isConnected ? t('sidebar.connected') : t('sidebar.disconnected') }}</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Activity,
  BarChart3,
  BookOpen,
  Bot,
  ChevronRight,
  CreditCard,
  Diff,
  FileText,
  GitBranch,
  Globe,
  LayoutDashboard,
  Link2,
  MessageSquare,
  Server,
  Settings,
  ShieldCheck,
  Terminal,
  Wrench,
} from 'lucide-vue-next'
import type { Component } from 'vue'

const { t } = useI18n()

interface NavItem {
  id: string
  label: string
  icon: Component
}

interface NavGroup {
  label: string
  items: NavItem[]
}

const props = defineProps<{
  activeView?: string
  isConnected?: boolean
}>()

const emit = defineEmits<{
  'nav-change': [navId: string]
}>()

const navGroups = computed<NavGroup[]>(() => [
  {
    label: t('navGroup.observe'),
    items: [
      { id: 'dashboard', label: t('nav.dashboard'), icon: LayoutDashboard },
      { id: 'runs', label: t('nav.runs'), icon: Activity },
      { id: 'workflows', label: t('nav.workflows'), icon: GitBranch },
    ],
  },
  {
    label: t('navGroup.govern'),
    items: [
      { id: 'approvals', label: t('nav.approvals'), icon: ShieldCheck },
      { id: 'guardrails', label: t('nav.guardrails'), icon: Wrench },
    ],
  },
  {
    label: t('navGroup.improve'),
    items: [
      { id: 'eval', label: t('nav.eval'), icon: BarChart3 },
      { id: 'config-compare', label: t('nav.configCompare'), icon: Diff },
      { id: 'knowledge', label: t('nav.knowledge'), icon: BookOpen },
      { id: 'costs', label: t('nav.costs'), icon: CreditCard },
    ],
  },
  {
    label: t('navGroup.integrate'),
    items: [
      { id: 'providers', label: t('nav.providers'), icon: Server },
      { id: 'connectors', label: t('nav.connectors'), icon: Link2 },
      { id: 'environments', label: t('nav.environments'), icon: Globe },
    ],
  },
  {
    label: t('navGroup.admin'),
    items: [
      { id: 'audit', label: t('nav.audit'), icon: FileText },
      { id: 'system', label: t('nav.system'), icon: Settings },
      { id: 'agents', label: t('nav.agents'), icon: Bot },
      { id: 'chat', label: t('nav.chat'), icon: MessageSquare },
      { id: 'terminal', label: t('nav.terminal'), icon: Terminal },
    ],
  },
])

const activeNav = computed(() => {
  if (props.activeView === 'run-detail') return 'runs'
  if (props.activeView === 'workflow-detail') return 'workflows'
  if (props.activeView === 'session-detail') return 'history'
  return props.activeView || 'dashboard'
})

function handleNavClick(navId: string) {
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
  z-index: 100;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.92);
  border-right: 1px solid var(--border-color);
  box-shadow: 8px 0 30px rgba(15, 23, 42, 0.03);
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
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  color: white;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  border-radius: 10px;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0;
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.18);
}

.logo-text {
  color: #1e293b;
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0;
}

.sidebar-nav {
  flex: 1;
  padding: 18px 12px;
  overflow-y: auto;
}

.nav-group {
  margin-bottom: 20px;
}

.nav-group-label {
  padding: 0 12px 8px;
  color: #94a3b8;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.nav-item {
  width: 100%;
  min-height: 38px;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 9px 11px;
  border-radius: 10px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  transition: all 0.18s ease;
  text-align: left;
}

.nav-item:hover {
  color: #0f172a;
  background: #f8fafc;
}

.nav-item.active {
  color: #1d4ed8;
  background: #eff6ff;
  font-weight: 700;
}

.nav-icon {
  flex: 0 0 18px;
  color: currentColor;
}

.nav-label {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.nav-chevron {
  color: #60a5fa;
}

.sidebar-footer {
  padding: 14px 18px 18px;
  border-top: 1px solid var(--border-subtle);
}

.user-card,
.connection-status {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  background: #f8fafc;
}

.user-card {
  padding: 10px;
  margin-bottom: 10px;
}

.user-avatar {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 11px;
  font-weight: 900;
}

.user-meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.user-meta span {
  color: #0f172a;
  font-size: 12px;
  font-weight: 700;
}

.user-meta small {
  color: #64748b;
  font-size: 10px;
}

.connection-status {
  min-height: 36px;
  padding: 0 12px;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

@media (max-width: 768px) {
  .sidebar {
    display: none;
  }
}
</style>
