<template>
  <div class="state-loading">
    <div class="spinner"></div>
    <p v-if="message" class="state-message">{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  message?: string
}>()
</script>

<style scoped>
.state-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  gap: 16px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-subtle);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.state-message {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0;
}
</style>
