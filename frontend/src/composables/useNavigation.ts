/**
 * Navigation configuration and composable for AI Workflow Control Plane.
 *
 * Extracted from App.vue to keep routing logic in a dedicated module.
 */

import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

// ---------------------------------------------------------------------------
// Route Configuration
// ---------------------------------------------------------------------------

/** Maps nav ID -> i18n key (static, locale-independent) */
const NAV_I18N_KEYS: Record<string, string> = {
  dashboard: 'nav.dashboard',
  runs: 'nav.runs',
  workflows: 'nav.workflows',
  approvals: 'nav.approvals',
  eval: 'nav.eval',
  'config-compare': 'nav.configCompare',
  providers: 'nav.providers',
  connectors: 'nav.connectors',
  environments: 'nav.environments',
  knowledge: 'nav.knowledge',
  costs: 'nav.costs',
  guardrails: 'nav.guardrails',
  system: 'nav.system',
  agents: 'nav.agents',
  'run-detail': 'nav.runDetail',
  'workflow-detail': 'nav.workflowDetail',
  'session-detail': 'nav.sessionDetail',
  chat: 'nav.chat',
  terminal: 'nav.terminal',
  audit: 'nav.audit',
}

/** Legacy static title map for backward compatibility (non-reactive contexts) */
export const NAV_TITLE_MAP: Record<string, string> = {
  dashboard: 'Dashboard',
  runs: 'Runs',
  workflows: 'Workflows',
  approvals: 'Approvals',
  eval: 'Eval',
  'config-compare': 'Config Diff',
  providers: 'Providers',
  connectors: 'Connectors',
  environments: 'Environments',
  knowledge: 'Knowledge',
  costs: 'Costs',
  guardrails: 'Tool Policies',
  system: 'System',
  agents: 'Agent Config',
  'run-detail': 'Run Detail',
  'workflow-detail': 'Workflow Detail',
  'session-detail': 'Session Detail',
  chat: 'Chat',
  terminal: 'Terminal',
  audit: 'Audit Log',
}

/** Maps nav ID -> hash route */
export const NAV_TO_HASH: Record<string, string> = {
  dashboard: '#/',
  runs: '#/runs',
  workflows: '#/workflows',
  approvals: '#/approvals',
  eval: '#/eval',
  'config-compare': '#/config-compare',
  providers: '#/providers',
  connectors: '#/connectors',
  environments: '#/environments',
  knowledge: '#/knowledge',
  costs: '#/costs',
  guardrails: '#/guardrails',
  system: '#/system',
  agents: '#/agents',
  terminal: '#/terminal',
  chat: '#/chat',
  audit: '#/audit',
}

/** Maps hash route -> nav ID */
export const HASH_TO_NAV: Record<string, string> = {
  '#/': 'dashboard',
  '#/runs': 'runs',
  '#/workflows': 'workflows',
  '#/approvals': 'approvals',
  '#/eval': 'eval',
  '#/config-compare': 'config-compare',
  '#/providers': 'providers',
  '#/connectors': 'connectors',
  '#/environments': 'environments',
  '#/knowledge': 'knowledge',
  '#/costs': 'costs',
  '#/guardrails': 'guardrails',
  '#/system': 'system',
  '#/agents': 'agents',
  '#/terminal': 'terminal',
  '#/chat': 'chat',
  '#/audit': 'audit',
  '': 'dashboard',
}

/** Nav IDs that belong to the Legacy group */
export const LEGACY_NAV_IDS = new Set<string>()

// ---------------------------------------------------------------------------
// Composable
// ---------------------------------------------------------------------------

export function useNavigation() {
  const { t } = useI18n()
  const currentNav = ref('dashboard')

  function isLegacyNav(navId: string): boolean {
    return LEGACY_NAV_IDS.has(navId)
  }

  function getTitle(navId: string): string {
    const key = NAV_I18N_KEYS[navId]
    return key ? t(key) : t('nav.dashboard')
  }

  /** Reactive title map that updates when locale changes */
  const navTitleMap = computed(() => {
    const map: Record<string, string> = {}
    for (const [navId, key] of Object.entries(NAV_I18N_KEYS)) {
      map[navId] = t(key)
    }
    return map
  })

  function setNav(navId: string) {
    currentNav.value = navId
    const hash = NAV_TO_HASH[navId]
    if (hash) window.location.hash = hash
  }

  return {
    currentNav,
    isLegacyNav,
    getTitle,
    setNav,
    navTitleMap,
  }
}
