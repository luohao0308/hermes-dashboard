<template>
  <div class="state-unauthorized">
    <span class="lock-icon">🔒</span>
    <p class="lock-message">{{ message ?? t('unauthorizedState.message') }}</p>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n"
const { t } = useI18n()
withDefaults(defineProps<{
  message?: string
}>(), {
  message: undefined,
})
</script>

<style scoped>
.state-unauthorized {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  gap: 12px;
}

.lock-icon {
  font-size: 40px;
  opacity: 0.6;
}

.lock-message {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0;
  text-align: center;
}
</style>
