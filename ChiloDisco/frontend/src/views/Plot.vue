<template>
  <div class="page-plot">
    <header class="page-header">
      <h1>数据大屏</h1>
      <div class="controls">
        <select v-model="interval" class="select-control">
          <option :value="100">0.1s</option>
          <option :value="1000">1s</option>
          <option :value="5000">5s</option>
        </select>
        <button class="btn-action" @click="exportChart">导出图表</button>
      </div>
    </header>

    <div class="dashboard-grid">
      <!-- Left: Main Chart -->
      <div class="card chart-section">
        <div class="card-header">
          <span>实时覆盖率趋势</span>
        </div>
        <div class="chart-container" ref="lineChartEl"></div>
      </div>

      <!-- Right: Gauges Stack -->
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

      <!-- Bottom: Stats -->
      <div class="card stats-section">
        <div class="stats-grid">
          <div class="stat-compact">
            <div class="label">CYCLES DONE</div>
            <div class="value">{{ latest('cycles_done') }}</div>
          </div>
          <div class="stat-compact">
            <div class="label">SAVED CRASHES</div>
            <div class="value danger">{{ latest('saved_crashes') }}</div>
          </div>
          <div class="stat-compact">
            <div class="label">SAVED HANGS</div>
            <div class="value warning">{{ latest('saved_hangs') }}</div>
          </div>
          <div class="stat-compact">
            <div class="label">CORPUS COUNT</div>
            <div class="value">{{ latest('corpus_count') }}</div>
          </div>
          <div class="stat-compact">
            <div class="label">TOTAL EXECS</div>
            <div class="value primary">{{ latest('total_execs') }}</div>
          </div>
          <div class="stat-compact">
            <div class="label">LAST UPDATE</div>
            <div class="value muted">{{ formatTime(latest('last_update')) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, shallowRef } from 'vue'
import * as echarts from 'echarts'

const interval = ref(1000)
const lineChartEl = ref(null)
const gauge1El = ref(null)
const gauge2El = ref(null)
const gauge3El = ref(null)

const charts = []
const dataSeries = shallowRef({})
let timer = null

function latest(key) {
  const arr = dataSeries.value[key]
  if (!arr || !arr.length) return '—'
  return arr[arr.length - 1]
}

function formatTime(ts) {
  if (!ts || ts === '—') return '—'
  return new Date(ts * 1000).toLocaleTimeString()
}

async function fetchData() {
  try {
    const r = await fetch('/api/plot?t=' + Date.now())
    const json = await r.json()
    if (json.series) {
      dataSeries.value = json.series
      updateCharts(json.series)
    }
  } catch (e) {
    console.error(e)
  }
}

function initCharts() {
  const colorText = '#94a3b8'
  const colorSplit = 'rgba(148, 163, 184, 0.1)'
  
  // Line Chart
  const lineChart = echarts.init(lineChartEl.value)
  lineChart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 50, right: 50, top: 40, bottom: 30, containLabel: true },
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(15, 23, 42, 0.9)', borderColor: '#3b82f6', textStyle: { color: '#f1f5f9' } },
    legend: { 
      data: ['Map Size', 'Corpus', 'Crashes'],
      textStyle: { color: colorText },
      top: 0,
      right: 10,
      icon: 'circle'
    },
    xAxis: { type: 'category', boundaryGap: false, axisLine: { lineStyle: { color: colorSplit } }, axisLabel: { color: colorText } },
    yAxis: [
      { type: 'value', position: 'left', splitLine: { lineStyle: { color: colorSplit } }, axisLabel: { color: colorText } },
      { type: 'value', position: 'right', splitLine: { show: false }, axisLabel: { color: colorText } }
    ],
    series: []
  })
  charts.push(lineChart)

  // Gauges
  const createGauge = (el, color) => {
    const chart = echarts.init(el)
    chart.setOption({
      series: [{
        type: 'gauge',
        startAngle: 180, endAngle: 0,
        min: 0, max: 100,
        splitNumber: 1,
        radius: '100%',
        center: ['50%', '70%'],
        itemStyle: { color: color },
        progress: { show: true, width: 12 },
        pointer: { show: false },
        axisLine: { lineStyle: { width: 12, color: [[1, '#1e293b']] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        detail: { valueAnimation: true, offsetCenter: [0, -10], fontSize: 20, color: '#f1f5f9', formatter: '{value}' }
      }]
    })
    charts.push(chart)
    return chart
  }

  createGauge(gauge1El.value, '#3b82f6')
  createGauge(gauge2El.value, '#8b5cf6')
  createGauge(gauge3El.value, '#10b981')
}

function updateCharts(s) {
  const t = s.t || []
  const mapSize = s.map_size || []
  const corpus = s.corpus_count || []
  const crashes = s.saved_crashes || []
  
  charts[0].setOption({
    xAxis: { data: t },
    series: [
      { name: 'Map Size', type: 'line', smooth: true, showSymbol: false, data: mapSize, yAxisIndex: 0, itemStyle: { color: '#3b82f6' }, areaStyle: { opacity: 0.1 } },
      { name: 'Corpus', type: 'line', smooth: true, showSymbol: false, data: corpus, yAxisIndex: 1, itemStyle: { color: '#8b5cf6' }, areaStyle: { opacity: 0.1 } },
      { name: 'Crashes', type: 'line', smooth: true, showSymbol: false, data: crashes, yAxisIndex: 1, itemStyle: { color: '#ef4444' }, lineStyle: { width: 2, type: 'dashed' } }
    ]
  })

  const last = (k) => { const a = s[k]; return a && a.length ? a[a.length-1] : 0 }
  
  const pTotal = last('pending_total')
  charts[1].setOption({ series: [{ max: Math.max(100, pTotal*1.2), data: [{ value: pTotal }] }] })
  
  const pFavs = last('pending_favs')
  charts[2].setOption({ series: [{ max: Math.max(50, pFavs*1.2), data: [{ value: pFavs }] }] })
  
  const execs = last('execs_per_sec')
  charts[3].setOption({ series: [{ max: Math.max(100, execs*1.2), data: [{ value: Math.round(execs) }] }] })
}

function exportChart() {
  const url = charts[0].getDataURL({ type: 'png', backgroundColor: '#0f172a' })
  const a = document.createElement('a')
  a.href = url
  a.download = 'chart.png'
  a.click()
}

function resize() {
  charts.forEach(c => c.resize())
}

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
  gap: 1.5rem;
  background: radial-gradient(circle at top right, #1e293b 0%, #0f172a 100%);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 600; letter-spacing: -0.5px; }

.controls { display: flex; gap: 1rem; }
.select-control, .btn-action {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  color: var(--text-primary);
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
}
.select-control:hover, .btn-action:hover {
  background: rgba(255,255,255,0.1);
  border-color: var(--primary);
}

.dashboard-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 3fr 1fr;
  grid-template-rows: 1fr auto;
  gap: 1.5rem;
  min-height: 0;
}

.card {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 1rem;
  display: flex;
  flex-direction: column;
  padding: 1.25rem;
  box-shadow: 0 4px 24px rgba(0,0,0,0.2);
}

.card-header {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-bottom: 1rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  display: flex;
  justify-content: space-between;
}

.chart-section {
  grid-column: 1 / 2;
  grid-row: 1 / 2;
}

.gauges-section {
  grid-column: 2 / 3;
  grid-row: 1 / 2;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.gauge-card {
  flex: 1;
  min-height: 0;
  padding: 1rem;
}

.gauge-container {
  flex: 1;
  min-height: 0;
}

.stats-section {
  grid-column: 1 / 3;
  grid-row: 2 / 3;
  height: auto;
  padding: 1.5rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 2rem;
}

.stat-compact {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat-compact .label {
  font-size: 0.7rem;
  color: var(--text-muted);
  font-weight: 600;
  letter-spacing: 0.5px;
}

.stat-compact .value {
  font-size: 1.5rem;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  color: #f1f5f9;
}

.value.danger { color: #ef4444; }
.value.warning { color: #f59e0b; }
.value.primary { color: #3b82f6; }
.value.muted { color: #64748b; font-size: 1rem; }

.legend-hint {
  display: flex;
  gap: 1rem;
  align-items: center;
  font-size: 0.75rem;
  font-weight: normal;
  text-transform: none;
}
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 4px; }
.dot.blue { background: #3b82f6; }
.dot.purple { background: #8b5cf6; }
.dot.red { background: #ef4444; }
</style>
