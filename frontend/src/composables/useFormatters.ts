// Shared formatting functions

const ZH_CN: Intl.DateTimeFormatOptions = {
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
}

const ZH_CN_TIME: Intl.DateTimeFormatOptions = {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
}

export function formatDate(value: string | number | undefined | null, fallback = '时间未知'): string {
  if (!value) return fallback
  const date = new Date(typeof value === 'number' ? value * 1000 : value)
  if (isNaN(date.getTime())) return fallback
  return date.toLocaleString('zh-CN', ZH_CN)
}

export function formatTime(value: string | number | undefined | null, fallback = '刚刚'): string {
  if (!value) return fallback
  const date = new Date(typeof value === 'number' ? value * 1000 : value)
  if (isNaN(date.getTime())) return fallback
  return date.toLocaleTimeString('zh-CN', ZH_CN_TIME)
}

export function formatDuration(seconds: number | undefined | null): string {
  if (!seconds || seconds <= 0) return '0s'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
  return `${Math.floor(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`
}

export function formatNumber(value: number | undefined | null): string {
  if (value === undefined || value === null) return '0'
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
  return String(value)
}

export function formatBytes(bytes: number | undefined | null): string {
  if (!bytes || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

export function formatPercent(value: number | undefined | null, decimals = 1): string {
  if (value === undefined || value === null) return '0%'
  return `${(value * 100).toFixed(decimals)}%`
}
