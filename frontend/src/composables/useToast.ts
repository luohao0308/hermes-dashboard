// Shared toast notification system

import { ref } from 'vue'
import type { ToastMessage } from '../types'

const toasts = ref<ToastMessage[]>([])
let toastId = 0

const DEFAULT_DURATION = 5000

export function useToast() {
  function addToast(type: ToastMessage['type'], message: string, duration = DEFAULT_DURATION) {
    const id = ++toastId
    toasts.value = [...toasts.value, { id, type, message }]
    if (duration > 0) {
      setTimeout(() => removeToast(id), duration)
    }
  }

  function removeToast(id: number) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  return {
    toasts,
    addToast,
    removeToast,
  }
}
