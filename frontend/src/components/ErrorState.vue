<template>
  <div class="state-error">
    <span class="error-icon">⚠</span>
    <p class="error-message">{{ message }}</p>
    <button v-if="retryable" class="btn btn-secondary" @click="$emit('retry')">
      {{ t('errorState.retry') }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n"
const { t } = useI18n()
withDefaults(defineProps<{
  message: string
  retryable?: boolean
}>(), {
  retryable: false,
})

defineEmits<{
  retry: []
}>()
</script>

<style scoped>
.state-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  gap: 12px;
}

.error-icon {
  font-size: 40px;
  opacity: 0.7;
}

.error-message {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0;
  text-align: center;
}
</style>
