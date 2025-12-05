<template>
  <div class="page-logs">
    <header class="page-header">
      <h1>实时日志监控</h1>
      <div class="controls">
        <select v-model="interval" class="select-control">
          <option :value="200">0.2s</option>
          <option :value="1000">1s</option>
          <option :value="2000">2s</option>
        </select>
        <select v-model="maxLines" class="select-control">
          <option :value="200">200行</option>
          <option :value="500">500行</option>
          <option :value="1000">1000行</option>
        </select>
      </div>
    </header>

    <div class="logs-grid">
      <div v-for="panel in panels" :key="panel.key" class="log-card">
        <div class="card-header">
          <div class="card-title">
            <span class="name">{{ getDisplayName(panel.key) }}</span>
            <span class="filename">{{ panel.filename }}</span>
          </div>
          <div class="meta">
            <span class="status-dot" :class="{ active: panel.isFresh }"></span>
            <span class="time">{{ panel.mtimeText }}</span>
          </div>
        </div>
        <div class="log-content" ref="logContainers">
          <pre v-html="panel.html"></pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'

const interval = ref(2000)
const maxLines = ref(500)
const panels = reactive([])
let timer = null

const logNameMap = {
  'LLM_LOG_PATH': 'LLM 交互',
  'MAIN_LOG_PATH': '主进程',
  'MUTATOR_FIXER_LOG_PATH': '修复器',
  'MUTATOR_GENERATOR_LOG_PATH': '生成器',
  'PARSER_LOG_PATH': '解析器',
  'STRUCTURAL_MUTATOR_LOG_PATH': '结构变异'
}

function getDisplayName(key) {
  return logNameMap[key] || key
}

// Color logic: Fresh = Bright, Old = Dim
function colorize(text, ageSec) {
  // Simple styling: 
  // < 5s: White + Glow
  // < 30s: Light Grey
  // > 30s: Dark Grey
  let color = 'var(--text-muted)'
  let shadow = 'none'
  
  if (ageSec < 5) {
    color = '#fff'
    shadow = '0 0 8px rgba(255,255,255,0.3)'
  } else if (ageSec < 30) {
    color = 'var(--text-secondary)'
  }
  
  // Escape HTML
  const safe = text.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]))
  return `<div style="color:${color}; text-shadow:${shadow}">${safe}</div>`
}

async function fetchLogs() {
  try {
    const r = await fetch('/api/logs?t=' + Date.now())
    const data = await r.json()
    const now = new Date(data.now)

    // Sync panels
    const keys = Object.keys(data.logs).sort()
    // Simple diff for panels list
    if (panels.length !== keys.length) {
      panels.splice(0, panels.length, ...keys.map(k => ({ key: k, html: '', filename: '', isFresh: false })))
    }

    for (let i = 0; i < keys.length; i++) {
      const key = keys[i]
      const info = data.logs[key]
      const p = panels[i]
      
      p.filename = info.path.split(/[/\\]/).pop()
      p.mtimeText = info.mtime ? new Date(info.mtime).toLocaleTimeString() : '-'
      
      // Calculate freshness based on file mtime
      const mtime = new Date(info.mtime)
      const fileAge = (now - mtime) / 1000
      p.isFresh = fileAge < 5

      // Process lines
      const lines = info.lines || []
      const html = lines.map(l => {
        let age = 999
        if (l.t) {
          age = (now - new Date(l.t)) / 1000
        }
        return colorize(l.s, age)
      }).join('')
      
      p.html = html
    }
    
    // Auto scroll? (Simplified for now)
    await nextTick()
    const containers = document.querySelectorAll('.log-content')
    containers.forEach(el => {
      // Smart scroll: if near bottom, scroll to bottom
      if (el.scrollHeight - el.scrollTop - el.clientHeight < 50) {
        el.scrollTop = el.scrollHeight
      }
    })

  } catch (e) {
    console.error(e)
  }
}

function start() {
  stop()
  timer = setInterval(fetchLogs, interval.value)
  fetchLogs()
}

function stop() {
  if (timer) clearInterval(timer)
}

onMounted(start)
onBeforeUnmount(stop)
</script>

<style scoped>
.page-logs {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 24px;
  gap: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}

.controls {
  display: flex;
  gap: 12px;
}

.select-control {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 6px 12px;
  border-radius: 4px;
  outline: none;
}

.logs-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 16px;
  min-height: 0;
}

.log-card {
  background: var(--bg-panel-glass);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.card-header {
  padding: 12px 16px;
  background: rgba(0,0,0,0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
}

.card-title {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.name {
  font-weight: 600;
  font-size: 14px;
}

.filename {
  font-size: 12px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
  transition: all 0.3s;
}

.status-dot.active {
  background: var(--success);
  box-shadow: 0 0 8px var(--success);
}

.time {
  font-size: 12px;
  color: var(--text-muted);
}

.log-content {
  flex: 1;
  overflow: auto;
  padding: 12px;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.5;
  background: rgba(0,0,0,0.1);
}

.log-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
