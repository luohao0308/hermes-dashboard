const trimTrailingSlash = (value: string) => value.replace(/\/+$/, '')

const defaultApiBase = import.meta.env.DEV ? 'http://localhost:8000' : ''

export const API_BASE = trimTrailingSlash(
  import.meta.env.VITE_API_BASE_URL || defaultApiBase
)

const configuredWsBase = import.meta.env.VITE_WS_BASE_URL
const fallbackWsBase = API_BASE
  ? API_BASE.replace(/^http/, 'ws')
  : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`

export const WS_BASE = trimTrailingSlash(configuredWsBase || fallbackWsBase)
