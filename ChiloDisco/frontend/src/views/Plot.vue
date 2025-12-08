<template>
  <div class="page-plot">
    <header class="page-header">
      <h1>数据大屏</h1>
      <div class="controls">
        <label>刷新频率</label>
        <select v-model="interval" class="select-control" @change="restartPolling">
          <option :value="100">0.1s</option>
          <option :value="500">0.5s</option>
          <option :value="1000">1s</option>
          <option :value="2000">2s</option>
          <option :value="5000">5s</option>
        </select>
        <button class="btn-action" @click="exportChart">📊 导出图表</button>
        <button class="btn-action" @click="exportData">📄 导出CSV</button>
      </div>
    </header>

    <div class="dashboard-grid">
      <!-- Left: Main Chart -->
      <div class="card chart-section">
        <div class="card-header">
          <span>实时覆盖率趋势</span>
          <span class="meta-text">{{ meta.path || '' }}</span>
        </div>
        <div class="chart-container" ref="lineChartEl"></div>
      </div>

      <!-- Right: Gauges + Stats -->
      <div class="right-column">
        <div class="gauges-section">
          <div class="card gauge-card">
            <div class="card-header">Pending Total</div>
            <div class="gauge-container" ref="gauge1El"></div>
          </div>
          <div class="card gauge-card">
            <div class="card-header">Pending Favs</div>
            <div class="gauge-container" ref="gauge2El"></div>
          </div>
          <div class="card gauge-card">
            <div class="card-header">Execs / Sec</div>
            <div class="gauge-container" ref="gauge3El"></div>
          </div>
        </div>
        
        <!-- Stats Panel -->
        <div class="card stats-panel">
          <div class="card-header">实时指标</div>
          <div class="stats-compact-grid">
            <div class="stat-item">
              <span class="stat-icon">🔄</span>
              <div class="stat-content">
                <span class="stat-label">Cycles</span>
                <span class="stat-value">{{ latest('cycles_done') }}</span>
              </div>
            </div>
            <div class="stat-item">
              <span class="stat-icon">📌</span>
              <div class="stat-content">
                <span class="stat-label">Current</span>
                <span class="stat-value">{{ latest('cur_item') }}</span>
              </div>
            </div>
            <div class="stat-item">
              <span class="stat-icon">💥</span>
              <div class="stat-content">
                <span class="stat-label">Crashes</span>
                <span class="stat-value danger">{{ latest('saved_crashes') }}</span>
              </div>
            </div>
            <div class="stat-item">
              <span class="stat-icon">📏</span>
              <div class="stat-content">
                <span class="stat-label">Depth</span>
                <span class="stat-value">{{ latest('max_depth') }}</span>
              </div>
            </div>
            <div class="stat-item full-width">
              <span class="stat-icon">🎯</span>
              <div class="stat-content">
                <span class="stat-label">Total Execs</span>
                <span class="stat-value primary">{{ formatNumber(latest('total_execs')) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Bottom: Current Input Sample -->
      <div class="card cur-input-section" :style="curInputStyle">
        <div class="card-header">
          <span>当前输入样本</span>
          <span class="meta-text">{{ curInput.meta?.path || '（等待数据…）' }} · {{ curInput.meta?.size || 0 }}B</span>
          <span class="timer-badge" v-if="curInput.since_sec !== undefined">
            已运行 {{ formatDuration(curInput.since_sec) }}
          </span>
        </div>
        <pre class="cur-input-content">{{ curInput.content || '（空）' }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, shallowRef, computed, watch } from 'vue'
import * as echarts from 'echarts'

const interval = ref(1000)
const lineChartEl = ref(null)
const gauge1El = ref(null)
const gauge2El = ref(null)
const gauge3El = ref(null)

const charts = []
const dataSeries = shallowRef({})
const meta = ref({})
const curInput = ref({ content: '', meta: {}, since_sec: 0 })
let timer = null

function latest(key) {
  const arr = dataSeries.value[key]
  if (!arr || !arr.length) return '—'
  return arr[arr.length - 1]
}

function formatNumber(val) {
  if (val === '—' || val === undefined || val === null) return '—'
  return Number(val).toLocaleString()
}

function formatDuration(sec) {
  const s = Math.max(0, Math.floor(sec || 0))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const ss = s % 60
  const pad = (x) => (x < 10 ? '0' + x : '' + x)
  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(ss)}` : `${pad(m)}:${pad(ss)}`
}

// Color style based on age (matching version5.0 hueForAge)
function hueForAge(ageSec) {
  if (ageSec <= 2) return 140
  if (ageSec <= 5) return 105
  if (ageSec <= 10) return 80
  if (ageSec <= 20) return 60
  if (ageSec <= 40) return 40
  if (ageSec <= 60) return 25
  if (ageSec <= 90) return 12
  return 0
}

const curInputStyle = computed(() => {
  const age = curInput.value.since_sec || 0
  const h = hueForAge(age)
  const glow = Math.min(0.6, 0.1 + age * 0.005)
  return {
    borderColor: `hsl(${h}, 40%, 65%)`,
    boxShadow: `0 0 ${Math.round(glow * 20)}px hsla(${h}, 40%, 55%, ${glow})`
  }
})

async function fetchData() {
  try {
    const r = await fetch('/api/plot?t=' + Date.now())
    const json = await r.json()
    if (json.series) {
      dataSeries.value = json.series
      updateCharts(json.series)
    }
    if (json.meta) {
      meta.value = json.meta
    }
    if (json.cur_input) {
      curInput.value = json.cur_input
    }
  } catch (e) {
    console.error(e)
  }
}

function restartPolling() {
  if (timer) clearInterval(timer)
  timer = setInterval(fetchData, interval.value)
}

function initCharts() {
  const colorText = '#94a3b8'
  const colorSplit = 'rgba(148, 163, 184, 0.1)'
  
  // Register neon theme
  echarts.registerTheme('chiloNeon', {
    color: ['#00f0ff', '#8b5cf6', '#ff006e', '#00ff9f', '#ffed4e'],
    backgroundColor: 'transparent',
    textStyle: { fontFamily: 'JetBrains Mono, Noto Sans SC, monospace', color: '#e0e7ff' },
    tooltip: {
      backgroundColor: 'rgba(19,24,36,0.95)',
      borderColor: 'rgba(0,240,255,0.5)',
      borderWidth: 2,
      textStyle: { color: '#e0e7ff' },
      extraCssText: 'box-shadow: 0 0 20px rgba(0,240,255,0.4); backdrop-filter: blur(10px);'
    }
  })
  
  // Line Chart with neon style - Each series has its own Y axis for better visibility
  const lineChart = echarts.init(lineChartEl.value, 'chiloNeon')
  lineChart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 80, right: 120, top: 60, bottom: 60, containLabel: false },
    animation: true,
    animationDuration: 600,
    tooltip: { trigger: 'axis', axisPointer: { type: 'line' } },
    legend: { 
      data: [
        { name: 'map_size(%)', itemStyle: { color: '#00f0ff' } },
        { name: 'edges_found', itemStyle: { color: '#8b5cf6' } },
        { name: 'corpus_count', itemStyle: { color: '#ff006e' } },
        { name: 'saved_crashes', itemStyle: { color: '#ffed4e' } }
      ],
      textStyle: { color: colorText, fontSize: 12 },
      bottom: 10,
      icon: 'circle'
    },
    xAxis: { 
      type: 'value', 
      min: 'dataMin', 
      max: 'dataMax',
      boundaryGap: false, 
      axisLine: { lineStyle: { color: 'rgba(0,240,255,0.3)' } }, 
      axisLabel: { color: '#6b7280' },
      splitLine: { show: false }
    },
    yAxis: [
      { 
        type: 'value', 
        name: 'map%', 
        nameTextStyle: { color: '#00f0ff', fontSize: 10 },
        position: 'left', 
        offset: 0,
        scale: true,
        boundaryGap: ['5%', '10%'],
        axisLabel: { formatter: '{value}%', color: '#00f0ff', fontSize: 10 }, 
        axisLine: { show: true, lineStyle: { color: '#00f0ff' } },
        splitLine: { show: false }
      },
      { 
        type: 'value', 
        name: 'edges', 
        nameTextStyle: { color: '#8b5cf6', fontSize: 10 },
        position: 'left', 
        offset: 50,
        scale: true,
        boundaryGap: ['5%', '10%'],
        axisLabel: { color: '#8b5cf6', fontSize: 10 }, 
        axisLine: { show: true, lineStyle: { color: '#8b5cf6' } },
        splitLine: { show: false }
      },
      { 
        type: 'value', 
        name: 'corpus', 
        nameTextStyle: { color: '#ff006e', fontSize: 10 },
        position: 'right', 
        offset: 0,
        scale: true,
        boundaryGap: ['5%', '10%'],
        axisLabel: { color: '#ff006e', fontSize: 10 }, 
        axisLine: { show: true, lineStyle: { color: '#ff006e' } },
        splitLine: { show: false }
      },
      { 
        type: 'value', 
        name: 'crashes', 
        nameTextStyle: { color: '#ffed4e', fontSize: 10 },
        position: 'right', 
        offset: 50,
        scale: true,
        boundaryGap: ['5%', '10%'],
        axisLabel: { color: '#ffed4e', fontSize: 10 }, 
        axisLine: { show: true, lineStyle: { color: '#ffed4e' } },
        splitLine: { show: false }
      }
    ],
    series: []
  })
  charts.push(lineChart)

  // Gauges with neon style
  const createGauge = (el, color, name) => {
    const chart = echarts.init(el, 'chiloNeon')
    chart.setOption({
      series: [{
        type: 'gauge',
        startAngle: 200, endAngle: -20,
        min: 0, max: 100,
        splitNumber: 5,
        radius: '88%',
        center: ['50%', '60%'],
        pointer: { show: true, length: '62%', width: 4, itemStyle: { color: color } },
        progress: { show: true, overlap: false, roundCap: true, clip: false, itemStyle: { color: color } },
        axisLine: { lineStyle: { width: 14, color: [[0.3, color], [0.7, '#8b5cf6'], [1, '#ff006e']] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        title: { show: true, color: color, fontSize: 13, offsetCenter: [0, '70%'] },
        detail: { valueAnimation: true, fontSize: 28, color: color, offsetCenter: [0, '35%'], formatter: '{value}' },
        data: [{ value: 0, name: name }]
      }]
    })
    charts.push(chart)
    return chart
  }

  createGauge(gauge1El.value, '#00f0ff', 'pending_total')
  createGauge(gauge2El.value, '#8b5cf6', 'pending_favs')
  createGauge(gauge3El.value, '#00ff9f', 'execs_per_sec')
}

function updateCharts(s) {
  const t = s.t || []
  const mapSize = s.map_size || []
  const edges = s.edges_found || []
  const corpus = s.corpus_count || []
  const crashes = s.saved_crashes || []
  
  // Update line chart with neon gradient areas - each series uses its own Y axis
  charts[0].setOption({
    xAxis: { data: t },
    series: [
      { 
        name: 'map_size(%)', type: 'line', smooth: true, showSymbol: false, 
        data: t.map((ti, i) => [ti, mapSize[i]]),
        yAxisIndex: 0,
        lineStyle: { color: '#00f0ff', width: 3 },
        areaStyle: { 
          opacity: 0.25,
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0,240,255,0.4)' },
            { offset: 1, color: 'rgba(0,240,255,0.05)' }
          ])
        }
      },
      { 
        name: 'edges_found', type: 'line', smooth: true, showSymbol: false, 
        data: t.map((ti, i) => [ti, edges[i]]),
        yAxisIndex: 1,
        lineStyle: { color: '#8b5cf6', width: 3 },
        areaStyle: { 
          opacity: 0.25,
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(139,92,246,0.4)' },
            { offset: 1, color: 'rgba(139,92,246,0.05)' }
          ])
        }
      },
      { 
        name: 'corpus_count', type: 'line', smooth: true, showSymbol: false, 
        data: t.map((ti, i) => [ti, corpus[i]]),
        yAxisIndex: 2,
        lineStyle: { color: '#ff006e', width: 3 },
        areaStyle: { 
          opacity: 0.25,
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(255,0,110,0.4)' },
            { offset: 1, color: 'rgba(255,0,110,0.05)' }
          ])
        }
      },
      { 
        name: 'saved_crashes', type: 'line', smooth: true, showSymbol: false, 
        data: t.map((ti, i) => [ti, crashes[i]]),
        yAxisIndex: 3,
        lineStyle: { color: '#ffed4e', width: 3 },
        areaStyle: { 
          opacity: 0.25,
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(255,237,78,0.4)' },
            { offset: 1, color: 'rgba(255,237,78,0.05)' }
          ])
        }
      }
    ]
  })

  const last = (k) => { const a = s[k]; return a && a.length ? a[a.length - 1] : 0 }
  
  const pTotal = last('pending_total')
  charts[1].setOption({ series: [{ max: Math.max(10, pTotal * 1.6), data: [{ value: pTotal, name: 'pending_total' }] }] })
  
  const pFavs = last('pending_favs')
  charts[2].setOption({ series: [{ max: Math.max(10, pFavs * 1.6), data: [{ value: pFavs, name: 'pending_favs' }] }] })
  
  const execs = last('execs_per_sec')
  charts[3].setOption({ series: [{ max: Math.max(50, execs * 1.6), data: [{ value: Math.round(execs), name: 'execs_per_sec' }] }] })
}

function exportChart() {
  const url = charts[0].getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#0a0e1a' })
  const a = document.createElement('a')
  a.href = url
  a.download = `chilodisco_chart_${Date.now()}.png`
  a.click()
}

function exportData() {
  const s = dataSeries.value
  if (!s.t || s.t.length === 0) {
    alert('暂无数据可导出')
    return
  }
  
  const headers = ['Time(s)', 'Map Size(%)', 'Edges Found', 'Corpus Count', 'Saved Crashes', 'Pending Total', 'Pending Favs', 'Execs/Sec']
  let csv = headers.join(',') + '\n'
  
  for (let i = 0; i < s.t.length; i++) {
    const row = [
      s.t[i] || 0,
      s.map_size[i] || 0,
      s.edges_found[i] || 0,
      s.corpus_count[i] || 0,
      s.saved_crashes[i] || 0,
      s.pending_total[i] || 0,
      s.pending_favs[i] || 0,
      s.execs_per_sec[i] || 0
    ]
    csv += row.join(',') + '\n'
  }
  
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `chilodisco_data_${Date.now()}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

function resize() {
  charts.forEach(c => c.resize())
}

watch(interval, () => {
  restartPolling()
})

onMounted(() => {
  initCharts()
  fetchData()
  timer = setInterval(fetchData, interval.value)
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  clearInterval(timer)
  window.removeEventListener('resize', resize)
  charts.forEach(c => c.dispose())
})
</script>

<style scoped>
.page-plot {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  gap: 1rem;
  background: radial-gradient(circle at top right, #1e293b 0%, #0f172a 100%);
  overflow: hidden;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 600; letter-spacing: -0.5px; }

.controls { display: flex; gap: 1rem; align-items: center; }
.controls label { color: var(--text-muted); font-size: 0.875rem; }

.select-control, .btn-action {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  color: var(--text-primary);
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.875rem;
}
.select-control:hover, .btn-action:hover {
  background: rgba(255,255,255,0.1);
  border-color: #00f0ff;
}
.select-control option {
  background: #1e293b;
  color: #e0e7ff;
  padding: 0.5rem;
}

.dashboard-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 2fr 1fr;
  grid-template-rows: 1.5fr 1fr;
  gap: 1rem;
  min-height: 0;
  overflow: hidden;
}

.card {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 1rem;
  display: flex;
  flex-direction: column;
  padding: 1rem;
  box-shadow: 0 4px 24px rgba(0,0,0,0.2), inset 0 1px rgba(255,255,255,0.05);
  min-height: 0;
  overflow: hidden;
}

.card-header {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-bottom: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-shrink: 0;
}

.meta-text {
  font-weight: 400;
  font-size: 0.7rem;
  color: #6b7280;
  text-transform: none;
}

.timer-badge {
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid rgba(0, 240, 255, 0.3);
  color: #00f0ff;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-family: 'JetBrains Mono', monospace;
}

.chart-section {
  grid-column: 1 / 2;
  grid-row: 1 / 2;
}

.chart-container {
  flex: 1;
  min-height: 0;
}

.right-column {
  grid-column: 2 / 3;
  grid-row: 1 / 2;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-height: 0;
}

.gauges-section {
  display: flex;
  gap: 0.75rem;
  flex: 1;
  min-height: 0;
}

.gauge-card {
  flex: 1;
  min-height: 0;
  padding: 0.75rem;
}

.gauge-container {
  flex: 1;
  min-height: 0;
}

.stats-panel {
  flex-shrink: 0;
}

.stats-compact-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: rgba(0,0,0,0.2);
  border-radius: 8px;
}

.stat-item.full-width {
  grid-column: 1 / -1;
}

.stat-icon {
  font-size: 1.25rem;
}

.stat-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 0.65rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 1rem;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  color: #00f0ff;
}

.stat-value.danger { color: #ef4444; }
.stat-value.primary { color: #00ff9f; }

.cur-input-section {
  grid-column: 1 / 3;
  grid-row: 2 / 3;
  transition: box-shadow 0.6s ease, border-color 0.6s ease;
}

.cur-input-content {
  flex: 1;
  margin: 0;
  padding: 1rem;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.8rem;
  font-family: 'JetBrains Mono', monospace;
  color: #e0e7ff;
  background: rgba(0,0,0,0.3);
  border-radius: 8px;
  line-height: 1.5;
}
</style>
