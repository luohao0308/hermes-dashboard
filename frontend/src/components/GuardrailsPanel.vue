<template>
  <div class="guardrails-panel">
    <div class="section-header">
      <h3>审查规则</h3>
      <p class="subtitle">配置严重程度过滤器和审查规则</p>
    </div>

    <div class="rules-grid">
      <div v-for="rule in rules" :key="rule.id" class="rule-card">
        <div class="rule-header">
          <span class="rule-name">{{ rule.name }}</span>
          <label class="toggle">
            <input type="checkbox" :checked="rule.enabled" @change="toggleRule(rule)" />
            <span class="toggle-slider"></span>
          </label>
        </div>
        <div class="rule-desc">{{ rule.description }}</div>
        <div class="rule-meta">
          <span :class="['severity-tag', `sev-${rule.severity}`]">{{ rule.severity }}</span>
          <span class="rule-action">{{ rule.action }}</span>
        </div>
      </div>
    </div>

    <div class="section-header" style="margin-top: 24px;">
      <h3>严重程度阈值</h3>
    </div>
    <div class="thresholds">
      <div v-for="item in severityOptions" :key="item.key" class="threshold-row">
        <span :class="['severity-tag', `sev-${item.key}`]">{{ item.label }}</span>
        <select :value="thresholds[item.key]" @change="updateThreshold(item.key, ($event.target as HTMLSelectElement).value)">
          <option value="show">显示</option>
          <option value="warn">警告</option>
          <option value="block">阻止</option>
          <option value="skip">跳过</option>
        </select>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Rule {
  id: string
  name: string
  description: string
  severity: string
  action: string
  enabled: boolean
}

const rules = ref<Rule[]>([
  { id: 'security', name: '安全问题', description: 'SQL 注入、XSS、认证绕过、密钥泄露', severity: 'critical', action: '阻止', enabled: true },
  { id: 'bugs', name: 'Bug 检测', description: '空指针、越界、竞态条件、资源泄漏', severity: 'high', action: '警告', enabled: true },
  { id: 'performance', name: '性能问题', description: 'N+1 查询、无界循环、缺少分页', severity: 'medium', action: '显示', enabled: true },
  { id: 'architecture', name: '架构问题', description: '耦合、单一职责违反、依赖问题', severity: 'medium', action: '显示', enabled: true },
  { id: 'style', name: '代码风格', description: '命名、格式、轻微风格问题', severity: 'low', action: '跳过', enabled: false },
])

const severityOptions = [
  { key: 'critical', label: '严重' },
  { key: 'high', label: '高' },
  { key: 'medium', label: '中' },
  { key: 'low', label: '低' },
  { key: 'style', label: '风格' },
]

const thresholds = ref<Record<string, string>>({
  critical: 'block',
  high: 'warn',
  medium: 'show',
  low: 'show',
  style: 'skip',
})

function toggleRule(rule: Rule) {
  rules.value = rules.value.map(r => r.id === rule.id ? { ...r, enabled: !r.enabled } : r)
}

function updateThreshold(key: string, value: string) {
  thresholds.value = { ...thresholds.value, [key]: value }
}
</script>

<style scoped>
.guardrails-panel { display: flex; flex-direction: column; gap: 16px; }
.section-header h3 { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.subtitle { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
.rules-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }
.rule-card { background: var(--glass-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 16px; }
.rule-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.rule-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.rule-desc { font-size: 12px; color: var(--text-muted); margin-bottom: 10px; }
.rule-meta { display: flex; gap: 8px; align-items: center; }
.severity-tag { font-size: 10px; padding: 2px 8px; border-radius: 10px; font-weight: 700; text-transform: uppercase; }
.sev-critical { background: rgba(255, 85, 85, 0.15); color: #ff5555; }
.sev-high { background: rgba(255, 183, 77, 0.15); color: #ffb74d; }
.sev-medium { background: rgba(139, 233, 253, 0.15); color: #8be9fd; }
.sev-low { background: rgba(80, 250, 123, 0.15); color: #50fa7b; }
.sev-style { background: var(--bg-tertiary); color: var(--text-muted); }
.rule-action { font-size: 11px; color: var(--text-muted); }
.toggle { position: relative; width: 36px; height: 20px; }
.toggle input { opacity: 0; width: 0; height: 0; }
.toggle-slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background: var(--bg-tertiary); border-radius: 10px; transition: 0.2s; }
.toggle-slider:before { content: ''; position: absolute; height: 16px; width: 16px; left: 2px; bottom: 2px; background: white; border-radius: 50%; transition: 0.2s; }
.toggle input:checked + .toggle-slider { background: var(--accent-color); }
.toggle input:checked + .toggle-slider:before { transform: translateX(16px); }
.thresholds { background: var(--glass-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 16px; }
.threshold-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border-subtle); }
.threshold-row:last-child { border-bottom: none; }
.threshold-row select { padding: 4px 8px; background: var(--bg-tertiary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); color: var(--text-primary); font-size: 12px; }
</style>
