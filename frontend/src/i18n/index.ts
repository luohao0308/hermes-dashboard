import { createI18n } from 'vue-i18n'
import zhCN from './zh-CN'
import enUS from './en-US'

const STORAGE_KEY = 'hermes_locale'

function detectLocale(): string {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'zh-CN' || stored === 'en-US') return stored
  const lang = navigator.language
  if (lang.startsWith('zh')) return 'zh-CN'
  return 'en-US'
}

const i18n = createI18n({
  legacy: false,
  locale: detectLocale(),
  fallbackLocale: 'en-US',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS,
  },
})

export function setLocale(locale: 'zh-CN' | 'en-US'): void {
  i18n.global.locale.value = locale
  localStorage.setItem(STORAGE_KEY, locale)
}

export function getLocale(): string {
  return i18n.global.locale.value
}

export default i18n
