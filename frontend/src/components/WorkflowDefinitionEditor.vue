<template>
  <div v-if="open" class="modal-backdrop" @click.self="$emit('close')">
    <section class="workflow-editor" role="dialog" aria-modal="true">
      <div class="editor-header">
        <div>
          <h3>{{ mode === 'create' ? 'Create Workflow' : 'Edit Workflow' }}</h3>
          <span>{{ mode === 'create' ? 'New definition' : 'Existing definition' }}</span>
        </div>
        <button class="icon-btn" type="button" @click="$emit('close')" aria-label="Close">
          <X :size="16" />
        </button>
      </div>

      <div class="editor-actions">
        <button type="button" class="btn" @click="loadSample">
          <WandSparkles :size="14" />
          Load Sample
        </button>
      </div>

      <label class="field-label" for="workflow-json">JSON</label>
      <textarea
        id="workflow-json"
        v-model="jsonText"
        class="json-input"
        spellcheck="false"
      />

      <div v-if="displayError" class="error-text">{{ displayError }}</div>

      <div class="editor-footer">
        <button type="button" class="btn" @click="$emit('close')">Cancel</button>
        <button type="button" class="btn btn-primary" :disabled="saving" @click="save">
          <Save :size="14" />
          {{ saving ? 'Saving' : 'Save' }}
        </button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Save, WandSparkles, X } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
  mode: 'create' | 'edit'
  initialJson: string
  sampleJson: string
  saving?: boolean
  error?: string | null
}>()

const emit = defineEmits<{
  close: []
  save: [payload: Record<string, unknown>]
}>()

const jsonText = ref(props.initialJson)
const localError = ref<string | null>(null)

watch(
  () => [props.open, props.initialJson],
  () => {
    jsonText.value = props.initialJson
    localError.value = null
  },
)

const displayError = computed(() => localError.value || props.error)

function loadSample() {
  jsonText.value = props.sampleJson
  localError.value = null
}

function save() {
  localError.value = null
  let parsed: unknown
  try {
    parsed = JSON.parse(jsonText.value)
  } catch {
    localError.value = 'Invalid JSON'
    return
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    localError.value = 'Workflow JSON must be an object'
    return
  }
  const payload = parsed as Record<string, unknown>
  if (typeof payload.name !== 'string' || payload.name.trim() === '') {
    localError.value = 'Workflow name is required'
    return
  }
  if (props.mode === 'create' && (typeof payload.runtime_id !== 'string' || payload.runtime_id.trim() === '')) {
    localError.value = 'runtime_id is required'
    return
  }
  if (!Array.isArray(payload.nodes) || payload.nodes.length === 0) {
    localError.value = 'At least one node is required'
    return
  }
  emit('save', payload)
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.35);
}

.workflow-editor {
  width: min(860px, 100%);
  max-height: min(760px, 92vh);
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  background: #ffffff;
  box-shadow: 0 24px 80px rgba(15, 23, 42, 0.22);
  padding: 18px;
}

.editor-header,
.editor-actions,
.editor-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.editor-header h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 900;
}

.editor-header span {
  display: block;
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 12px;
}

.field-label {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.json-input {
  min-height: 420px;
  resize: vertical;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: #0f172a;
  color: #e2e8f0;
  padding: 14px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  line-height: 1.55;
}

.json-input:focus {
  border-color: #93c5fd;
  outline: none;
  box-shadow: 0 0 0 3px rgba(147, 197, 253, 0.22);
}

.btn,
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: #ffffff;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
}

.btn {
  min-height: 34px;
  padding: 0 12px;
}

.icon-btn {
  width: 34px;
  height: 34px;
}

.btn-primary {
  color: #ffffff;
  background: #2563eb;
  border-color: #2563eb;
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.error-text {
  border: 1px solid #fecdd3;
  border-radius: 10px;
  background: #fff1f2;
  color: #be123c;
  padding: 10px 12px;
  font-size: 12px;
  font-weight: 800;
}

@media (max-width: 720px) {
  .modal-backdrop {
    padding: 12px;
  }

  .workflow-editor {
    max-height: 94vh;
  }

  .json-input {
    min-height: 320px;
  }
}
</style>
