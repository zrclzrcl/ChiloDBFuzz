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
      <!-- Main Line Chart -->
      <div class="card chart-card">
        <div class="card-header">实时趋势</div>
        <div class="chart-container" ref="lineChartEl"></div>
      </div>

      <!-- Gauges -->
      <div class="card gauge-card">
        <div class="card-header">Pending Total</div>
        <div class="chart-container" ref="gauge1El"></div>
      </div>
      <div class="card gauge-card">
        <div class="card-header">Pending Favs</div>
        <div class="chart-container" ref="gauge2El"></div>
      </div>
      <div class="card gauge-card">
        <div class="card-header">Execs / Sec</div>
        <div class="chart-container" ref="gauge3El"></div>
      </div>

      <!-- Stats -->
      <div class="card stats-card">
        <div class="card-header">核心指标</div>
        <div class="stats-grid">
          <div class="stat-item">
            <div class="label">Cycles</div>
            <div class="value">{{ latest('cycles_done') }}</div>
          </div>
          <div class="stat-item">
            <div class="label">Crashes</div>
            <div class="value danger">{{ latest('saved_crashes') }}</div>
          </div>
          <div class="stat-item">
            <div class="label">Paths</div>
            <div class="value">{{ latest('corpus_count') }}</div>
          </div>
          <div class="stat-item">
            <div class="label">Total Execs</div>
            <div class="value">{{ latest('total_execs') }}</div>
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
  // Theme colors
  const colorText = '#94a3b8'
  const colorSplit = 'rgba(148, 163, 184, 0.1)'
  
  // Line Chart
  const lineChart = echarts.init(lineChartEl.value)
  lineChart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 50, right: 50, top: 40, bottom: 40, containLabel: true },
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(15, 23, 42, 0.9)', borderColor: '#3b82f6', textStyle: { color: '#f1f5f9' } },
    legend: { textStyle: { color: colorText }, bottom: 0 },
    xAxis: { type: 'category', boundaryGap: false, axisLine: { lineStyle: { color: colorSplit } }, axisLabel: { color: colorText } },
    yAxis: [
      { type: 'value', name: 'Coverage %', position: 'left', splitLine: { lineStyle: { color: colorSplit } }, axisLabel: { color: colorText } },
      { type: 'value', name: 'Count', position: 'right', splitLine: { show: false }, axisLabel: { color: colorText } }
    ],
    series: []
  })
  charts.push(lineChart)

  // Gauges
  const createGauge = (el, name, color) => {
    const chart = echarts.init(el)
    chart.setOption({
      series: [{
        type: 'gauge',
        startAngle: 180, endAngle: 0,
        min: 0, max: 100,
        splitNumber: 5,
        itemStyle: { color: color },
        progress: { show: true, width: 18 },
        pointer: { show: false },
        axisLine: { lineStyle: { width: 18, color: [[1, '#1e293b']] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        title: { show: false },
        detail: { valueAnimation: true, offsetCenter: [0, '20%'], fontSize: 24, color: '#f1f5f9' }
      }]
    })
    charts.push(chart)
    return chart
  }

  createGauge(gauge1El.value, 'Pending', '#3b82f6')
  createGauge(gauge2El.value, 'Favs', '#8b5cf6')
  createGauge(gauge3El.value, 'Execs', '#10b981')
}

function updateCharts(s) {
  const t = s.t || []
  const mapSize = s.map_size || []
  const corpus = s.corpus_count || []
  
  // Update Line
  charts[0].setOption({
    xAxis: { data: t },
    series: [
      { name: 'Map Size', type: 'line', smooth: true, data: mapSize, yAxisIndex: 0, itemStyle: { color: '#3b82f6' }, areaStyle: { opacity: 0.2 } },
      { name: 'Corpus', type: 'line', smooth: true, data: corpus, yAxisIndex: 1, itemStyle: { color: '#8b5cf6' }, areaStyle: { opacity: 0.2 } }
    ]
  })

  // Update Gauges
  const last = (k) => { const a = s[k]; return a && a.length ? a[a.length-1] : 0 }
  
  const pTotal = last('pending_total')
  charts[1].setOption({ series: [{ max: Math.max(100, pTotal*1.2), data: [{ value: pTotal }] }] })
  
  const pFavs = last('pending_favs')
  charts[2].setOption({ series: [{ max: Math.max(50, pFavs*1.2), data: [{ value: pFavs }] }] })
  
  const execs = last('execs_per_sec')
  charts[3].setOption({ series: [{ max: Math.max(100, execs*1.2), data: [{ value: Math.round(execs) }] }] })
}

function exportChart() {
  // Simple export logic
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
  padding: 24px;
  gap: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h1 { margin: 0; font-size: 24px; }

.controls { display: flex; gap: 12px; }

.select-control, .btn-action {
  background: var(--bg-panel);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
}

.dashboard-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  grid-template-rows: 2fr 1fr;
  gap: 16px;
  min-height: 0;
}

.card {
  background: var(--bg-panel-glass);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.card-header {
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 12px;
  font-weight: 600;
}

.chart-container {
  flex: 1;
  min-height: 0;
}

.chart-card {
  grid-column: 1 / 2;
  grid-row: 1 / 3;
}

.stats-card {
  grid-column: 2 / 4;
  grid-row: 2 / 3;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  height: 100%;
  align-items: center;
}

.stat-item {
  text-align: center;
}

.stat-item .label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.stat-item .value {
  font-size: 24px;
  font-weight: 700;
  font-family: var(--font-mono);
}

.value.danger { color: var(--danger); }
</style>
