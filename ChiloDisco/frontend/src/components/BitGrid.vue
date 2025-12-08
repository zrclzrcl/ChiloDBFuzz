<template>
  <div class="bit-grid-wrapper">
    <!-- Toolbar -->
    <div class="bit-toolbar">
      <div class="toolbar-left">
        <span class="title">Bitmap View</span>
        <div class="zoom-controls">
          <button @click="adjustZoom(-1)" title="Zoom Out">-</button>
          <span class="zoom-level">{{ cellSize }}px</span>
          <button @click="adjustZoom(1)" title="Zoom In">+</button>
        </div>
      </div>
      <button class="btn-save" @click="downloadImage">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        Save Image
      </button>
    </div>

    <div class="bit-grid-container" ref="container">
      <canvas ref="canvas" 
        @mousemove="handleMouseMove" 
        @mouseleave="hoverInfo = null"
        @click="handleClick"
      ></canvas>
      
      <div v-if="hoverInfo" class="grid-tooltip" :style="{ top: hoverInfo.y + 'px', left: hoverInfo.x + 'px' }">
        <div class="idx">Index: {{ hoverInfo.index }}</div>
        <div class="val">Value: {{ hoverInfo.value }}</div>
        <div class="delta" v-if="hoverInfo.delta !== 0">
          Delta: <span :class="hoverInfo.delta > 0 ? 'delta-up' : 'delta-down'">{{ hoverInfo.delta > 0 ? '+' : '' }}{{ hoverInfo.delta }}</span>
        </div>
        <div class="heat">Heat: {{ (hoverInfo.heat * 100).toFixed(0) }}%</div>
        <div class="age" v-if="hoverInfo.lastChangeAge !== undefined">
          Last Change: {{ formatAge(hoverInfo.lastChangeAge) }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, computed } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
  layout: { type: Object, default: () => ({ rows: 0, cols: 0 }) },
  type: { type: String, default: 'bool' }, // 'bool' | 'heat'
  initialCellSize: { type: Number, default: 8 },
  gap: { type: Number, default: 1 }
})

const container = ref(null)
const canvas = ref(null)
const hoverInfo = ref(null)
const cellSize = ref(props.initialCellSize)

// Animation State
let animationId = null
let decayBuffer = new Float32Array(0)
let deltaBuffer = new Float32Array(0)  // Store last change magnitude
let lastChangeTime = new Float32Array(0)  // Store timestamp of last change (in seconds since start)
let ripples = [] // { x, y, r, age, color }
let lastData = []
let startTime = Date.now()

// Layout Computed - Always auto-fit to container width
const containerWidth = ref(0)

const cols = computed(() => {
  // Always calculate based on container width for responsive layout
  const w = containerWidth.value || 800
  const c = Math.floor(w / (cellSize.value + props.gap))
  return Math.max(1, c)  // Ensure at least 1 column
})

const rows = computed(() => {
  // Calculate rows based on data length and computed cols
  return Math.ceil(props.data.length / cols.value)
})

function adjustZoom(delta) {
  const newSize = cellSize.value + delta * 2
  if (newSize >= 2 && newSize <= 32) {
    cellSize.value = newSize
    resize()
  }
}

function formatAge(seconds) {
  if (seconds === undefined || seconds < 0) return '—'
  if (seconds < 1) return '<1s ago'
  if (seconds < 60) return `${Math.floor(seconds)}s ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  return `${Math.floor(seconds / 3600)}h ago`
}

function resize() {
  if (!container.value || !canvas.value) return
  
  const size = cellSize.value
  const gap = props.gap
  
  // Always fit to container width - responsive layout
  const w = container.value.clientWidth
  containerWidth.value = w  // Update reactive ref for cols computation
  
  const c = Math.max(1, Math.floor(w / (size + gap)))
  const r = Math.ceil(props.data.length / c)
  
  // Canvas width exactly fills container, no overflow
  canvas.value.width = c * (size + gap)
  canvas.value.height = r * (size + gap)
}

function downloadImage() {
  if (!canvas.value) return
  const link = document.createElement('a')
  link.download = `bitmap-${Date.now()}.png`
  link.href = canvas.value.toDataURL('image/png')
  link.click()
}

// --- Rendering Loop ---
function render() {
  const ctx = canvas.value?.getContext('2d')
  if (!ctx) return

  const w = canvas.value.width
  const h = canvas.value.height
  const size = cellSize.value
  const gap = props.gap
  const c = cols.value
  
  // 1. Clear / Fade background
  ctx.fillStyle = '#0f172a'
  ctx.fillRect(0, 0, w, h)

  // 2. Draw Cells
  // Use layout rows/cols if available to limit loop, otherwise use data length
  const limit = (props.layout && props.layout.rows && props.layout.cols) 
    ? (props.layout.rows * props.layout.cols) 
    : props.data.length
    
  const len = Math.min(props.data.length, limit)
  
  for (let i = 0; i < len; i++) {
    let val = props.data[i]
    let heat = decayBuffer[i] || 0
    
    // Decay heat
    if (heat > 0) {
      heat -= 0.01 // Slow decay
      if (heat < 0) heat = 0
      decayBuffer[i] = heat
    }

    // Skip empty
    if (val === 0 && heat === 0) continue

    const col = i % c
    const row = Math.floor(i / c)
    const x = col * (size + gap)
    const y = row * (size + gap)

    // Determine Color
    // Heat makes it white/bright. Value makes it blue/colored.
    if (val > 0) {
      // Active hit
      const lightness = 50 + (heat * 40) // 50% -> 90%
      ctx.fillStyle = `hsl(210, 100%, ${lightness}%)`
    } else {
      // Decaying ghost
      ctx.fillStyle = `hsla(210, 100%, 60%, ${heat})`
    }

    ctx.fillRect(x, y, size, size)
  }

  // 3. Draw Ripples
  ctx.lineWidth = 2
  for (let i = ripples.length - 1; i >= 0; i--) {
    const r = ripples[i]
    r.r += 1.0 // Expand speed
    r.age -= 0.02 // Fade speed

    if (r.age <= 0) {
      ripples.splice(i, 1)
      continue
    }

    ctx.beginPath()
    ctx.strokeStyle = `rgba(255, 255, 255, ${r.age})`
    ctx.arc(r.x, r.y, r.r, 0, Math.PI * 2)
    ctx.stroke()
  }

  // 4. Draw Hover Highlight
  if (hoverInfo.value) {
    const { index } = hoverInfo.value
    const col = index % c
    const row = Math.floor(index / c)
    const x = col * (size + gap)
    const y = row * (size + gap)

    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = 1
    ctx.strokeRect(x - 1, y - 1, size + 2, size + 2)
    
    // Optional: Crosshair effect
    ctx.fillStyle = 'rgba(255, 255, 255, 0.1)'
    ctx.fillRect(x, 0, size, h) // Vertical column
    ctx.fillRect(0, y, w, size) // Horizontal row
  }

  animationId = requestAnimationFrame(render)
}



function handleMouseMove(e) {
  const rect = canvas.value.getBoundingClientRect()
  const canvasX = e.clientX - rect.left
  const canvasY = e.clientY - rect.top
  
  const size = cellSize.value + props.gap
  const c = cols.value
  
  const col = Math.floor(canvasX / size)
  const row = Math.floor(canvasY / size)
  const index = row * c + col
  
  if (index >= 0 && index < props.data.length) {
    // Calculate tooltip position relative to container, not screen
    // Position tooltip near the hovered cell, offset slightly
    const cellX = col * size + size / 2
    const cellY = row * size
    
    // Offset tooltip to the right and slightly below the cell
    let tooltipX = cellX + 20
    let tooltipY = cellY - 10
    
    // Ensure tooltip stays within canvas bounds
    const containerRect = container.value?.getBoundingClientRect()
    if (containerRect) {
      // If tooltip would go off right edge, show on left side instead
      if (tooltipX + 140 > containerRect.width) {
        tooltipX = cellX - 150
      }
      // If tooltip would go above, show below
      if (tooltipY < 0) {
        tooltipY = cellY + size + 10
      }
    }
    
    const now = (Date.now() - startTime) / 1000
    const lastChange = lastChangeTime[index] || 0
    const age = lastChange > 0 ? (now - lastChange) : -1
    
    hoverInfo.value = {
      x: tooltipX,
      y: tooltipY,
      index,
      value: props.data[index],
      delta: deltaBuffer[index] || 0,
      heat: decayBuffer[index] || 0,
      lastChangeAge: age >= 0 ? age : undefined
    }
  } else {
    hoverInfo.value = null
  }
}

function handleClick(e) {
  // Manual ripple on click for fun
  const rect = canvas.value.getBoundingClientRect()
  ripples.push({
    x: e.clientX - rect.left,
    y: e.clientY - rect.top,
    r: 0,
    age: 1.0
  })
}

// Watch data for changes to trigger effects
watch(() => props.data, (newVal) => {
  if (!newVal) return
  
  // Resize if data grew
  if (newVal.length > decayBuffer.length) {
    const newSize = newVal.length
    const newDecay = new Float32Array(newSize)
    const newDelta = new Float32Array(newSize)
    const newTime = new Float32Array(newSize)
    newDecay.set(decayBuffer)
    newDelta.set(deltaBuffer)
    newTime.set(lastChangeTime)
    decayBuffer = newDecay
    deltaBuffer = newDelta
    lastChangeTime = newTime
    resize()
  }

  // Detect changes
  // Optimization: Check random samples or just iterate if < 100k
  // For 65k, iteration is fast enough in JS (approx 1-2ms)
  const len = newVal.length
  let changed = false
  const now = (Date.now() - startTime) / 1000
  
  for (let i = 0; i < len; i++) {
    const v = newVal[i]
    const old = lastData[i] || 0
    
    if (v !== old) {
      // Record the change magnitude (delta)
      deltaBuffer[i] = v - old
      lastChangeTime[i] = now
      
      // Heat flash (intensity based on delta magnitude)
      const deltaMag = Math.abs(v - old)
      decayBuffer[i] = Math.min(1.0, 0.5 + deltaMag * 0.1)
      changed = true
      
      // Spawn ripple if it's a "new" bit (0->nonzero) or large change
      if ((old === 0 && v > 0) || deltaMag >= 5) {
        if (Math.random() > 0.85) { // Limit ripples to avoid chaos
          const c = cols.value
          const col = i % c
          const row = Math.floor(i / c)
          const x = col * (cellSize.value + props.gap) + cellSize.value/2
          const y = row * (cellSize.value + props.gap) + cellSize.value/2
          
          ripples.push({ x, y, r: 0, age: 1.0 })
        }
      }
    }
  }
  
  if (changed || lastData.length !== len) {
    lastData = new Uint8Array(newVal) // Clone
  }
}, { deep: true }) // Note: deep watch on array can be expensive, but here we replace the array ref usually

onMounted(() => {
  window.addEventListener('resize', resize)
  
  // Watch layout changes to trigger resize
  watch(() => props.layout, () => {
    resize()
  }, { deep: true })

  resize()
  render()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  cancelAnimationFrame(animationId)
})
</script>

<style scoped>
.bit-grid-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #0f172a;
  border-radius: 0.5rem;
  overflow: hidden;
}

.bit-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem;
  background: rgba(30, 41, 59, 0.5);
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.zoom-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(0,0,0,0.2);
  padding: 2px;
  border-radius: 4px;
}

.zoom-controls button {
  background: transparent;
  border: none;
  color: var(--text-primary);
  width: 24px;
  height: 24px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 2px;
}

.zoom-controls button:hover {
  background: rgba(255,255,255,0.1);
}

.zoom-level {
  font-size: 0.75rem;
  color: var(--text-muted);
  min-width: 32px;
  text-align: center;
  font-family: var(--font-mono);
}

.btn-save {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  color: #3b82f6;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-save:hover {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.4);
}

.bit-grid-container {
  flex: 1;
  width: 100%;
  overflow-x: hidden;  /* No horizontal scroll */
  overflow-y: auto;
  position: relative;
}

canvas {
  display: block;
  cursor: crosshair;
  max-width: 100%;  /* Ensure canvas doesn't overflow */
}

.grid-tooltip {
  position: absolute;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(8px);
  border: 1px solid var(--primary);
  padding: 8px 12px;
  border-radius: 4px;
  pointer-events: none;
  z-index: 1000;
  box-shadow: 0 4px 20px rgba(0,0,0,0.6);
  min-width: 120px;
}

.idx { color: var(--text-muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
.val { color: var(--primary); font-weight: bold; font-family: var(--font-mono); font-size: 14px; margin-top: 2px; }
.delta { font-size: 12px; margin-top: 2px; font-family: var(--font-mono); }
.delta-up { color: #10b981; font-weight: 600; }
.delta-down { color: #ef4444; font-weight: 600; }
.heat { color: #f59e0b; font-size: 11px; margin-top: 2px; }
.age { color: #8b5cf6; font-size: 11px; margin-top: 2px; }
</style>
