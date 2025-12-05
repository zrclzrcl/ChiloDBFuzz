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
import { ref, computed, onMounted } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import BitGrid from '../components/BitGrid.vue'

const currentType = ref('sum')
const loading = ref(false)
const rawData = ref({
  sum: [],
  cumulative: [],
  bool: []
})
const meta = ref({ mapSize: 0 })

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
      meta.value = { mapSize: json.mapSize }
    }
  } catch (e) {
    console.error('Fetch bitmap failed', e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page-bitmap {
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

.title-group h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.subtitle {
  color: var(--text-muted);
  font-size: 14px;
  margin-top: 4px;
  display: block;
}

.controls {
  display: flex;
  gap: 12px;
}

.btn-group {
  display: flex;
  background: var(--bg-panel);
  border-radius: var(--radius-sm);
  padding: 4px;
  border: 1px solid var(--border-color);
}

.btn-group button {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-group button.active {
  background: var(--bg-app);
  color: var(--primary);
  box-shadow: var(--shadow-sm);
}

.btn-refresh {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-refresh:hover {
  border-color: var(--primary);
  color: var(--primary);
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
  background: var(--bg-panel-glass);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  height: 100%;
  padding: 16px;
  overflow: hidden;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}
</style>
