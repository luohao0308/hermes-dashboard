import { createApp } from 'vue'
import App from './App.vue'
import i18n from './i18n'
import './styles/minimal.css'

// Inject X-User-Role header into all fetch calls so RBAC endpoints
// (RCA, runbook, approvals, connectors, etc.) work without JWT.
// Backend RBAC falls back to this header in non-production environments.
{
  const origFetch = window.fetch
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const mergedInit: RequestInit = {
      ...init,
      headers: { 'X-User-Role': 'operator', ...init?.headers },
    }
    return origFetch(input, mergedInit)
  }
}

createApp(App).use(i18n).mount('#app')
