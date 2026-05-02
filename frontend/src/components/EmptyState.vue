<template>
  <div class="state-empty">
    <span class="empty-icon">{{ icon }}</span>
    <p class="empty-message">{{ message }}</p>
    <slot />
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  icon?: string
  message: string
}>(), {
  icon: '📭',
})
</script>

<style scoped>
.state-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  gap: 12px;
}

.empty-icon {
  font-size: 40px;
  opacity: 0.6;
}

.empty-message {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0;
  text-align: center;
}
</style>
