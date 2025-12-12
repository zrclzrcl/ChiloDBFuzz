<template>
  <div class="page-bitmap">
    <header class="page-header">
      <div class="title-group">
        <h1>Bitmap 热力图</h1>
        <span class="subtitle" v-if="meta.mapSize">Size: {{ meta.mapSize }} bits</span>
      </div>
      
      <div class="controls">
        <div class="btn-group">
          <button 
            v-for="t in ['sum', 'cumulative', 'bool']" 
            :key="t"
            :class="{ active: currentType === t }"
            @click="currentType = t"
          >
            {{ t.toUpperCase() }}
          </button>
        </div>
        <button 
          class="btn-auto" 
          :class="{ active: autoRefresh }"
          @click="toggleAutoRefresh"
          title="自动刷新"
        >
          ⚡ {{ autoRefresh ? 'ON' : 'OFF' }}
        </button>
        <button class="btn-refresh" @click="fetchData" :disabled="loading">
          <RefreshCw :class="{ spinning: loading }" />
        </button>
      </div>
    </header>

    <div class="content-area">
      <div class="card grid-card">
        <BitGrid 
          v-if="currentData.length" 
          :data="currentData" 
          :layout="meta.layout"
          :type="currentType === 'bool' ? 'bool' : 'heat'" 
        />
        <div v-else class="empty-state">
          {{ loading ? '加载中...' : '暂无数据' }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import BitGrid from '../components/BitGrid.vue'

const currentType = ref('sum')
const loading = ref(false)

// 从localStorage读取保存的设置
const savedAutoRefresh = localStorage.getItem('cd_bitmap_autoRefresh')
const savedRefreshInterval = localStorage.getItem('cd_bitmap_refreshInterval')
const autoRefresh = ref(savedAutoRefresh !== null ? savedAutoRefresh === 'true' : true)
const refreshInterval = ref(savedRefreshInterval ? parseInt(savedRefreshInterval, 10) : 2000)
let timer = null

const rawData = ref({
  sum: [],
  cumulative: [],
  bool: []
})
const meta = ref({ mapSize: 0, layout: { rows: 0, cols: 0 } })

const currentData = computed(() => {
  return rawData.value[currentType.value] || []
})

async function fetchData() {
  loading.value = true
  try {
    const res = await fetch('/api/bitmap/frame')
    const json = await res.json()
    if (json.ok) {
      rawData.value = json.channels
      meta.value = { 
        mapSize: json.mapSize,
        layout: json.layout || { rows: 0, cols: 0 }
      }
    }
  } catch (e) {
    console.error('Fetch bitmap failed', e)
  } finally {
    loading.value = false
  }
}

function startAutoRefresh() {
  if (timer) clearInterval(timer)
  if (autoRefresh.value) {
    timer = setInterval(fetchData, refreshInterval.value)
  }
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  localStorage.setItem('cd_bitmap_autoRefresh', autoRefresh.value.toString())
  startAutoRefresh()
}

onMounted(() => {
  fetchData()
  startAutoRefresh()
})

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.page-bitmap {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  gap: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--glass-border);
}

.title-group h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.subtitle {
  color: var(--text-secondary);
  font-size: 0.875rem;
  margin-top: 4px;
  display: block;
}

.controls {
  display: flex;
  gap: 1rem;
}

.btn-group {
  display: flex;
  background: rgba(0,0,0,0.2);
  border-radius: 0.5rem;
  padding: 0.25rem;
  border: 1px solid var(--glass-border);
}

.btn-group button {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  padding: 0.5rem 1rem;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-group button.active {
  background: rgba(255,255,255,0.1);
  color: var(--accent-primary);
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.btn-refresh {
  background: rgba(0,0,0,0.2);
  border: 1px solid var(--glass-border);
  color: var(--text-primary);
  width: 36px;
  height: 36px;
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-refresh:hover {
  background: rgba(255,255,255,0.1);
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}

.btn-auto {
  background: rgba(0,0,0,0.2);
  border: 1px solid var(--glass-border);
  color: var(--text-secondary);
  padding: 0.5rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-auto.active {
  background: rgba(0, 255, 159, 0.15);
  border-color: rgba(0, 255, 159, 0.4);
  color: #00ff9f;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.content-area {
  flex: 1;
  min-height: 0;
}

.grid-card {
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
  border-radius: 0.75rem;
  height: 100%;
  padding: 1rem;
  overflow: hidden;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}
</style>
