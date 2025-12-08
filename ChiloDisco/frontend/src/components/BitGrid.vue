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
        <div class="heat">Heat: {{ (hoverInfo.heat * 100).toFixed(0) }}%</div>
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
let ripples = [] // { x, y, r, age, color }
let lastData = []

// Layout Computed
const cols = computed(() => {
  if (props.layout && props.layout.cols > 0) {
    return props.layout.cols
  }
  if (!container.value) return 64
  const w = container.value.clientWidth
  return Math.floor(w / (cellSize.value + props.gap))
})

const rows = computed(() => {
  if (props.layout && props.layout.rows > 0) {
    return props.layout.rows
  }
  return Math.ceil(props.data.length / cols.value)
})

function adjustZoom(delta) {
  const newSize = cellSize.value + delta * 2
  if (newSize >= 2 && newSize <= 32) {
    cellSize.value = newSize
    resize()
  }
}

function resize() {
  if (!container.value || !canvas.value) return
  
  const size = cellSize.value
  const gap = props.gap
  
  // If layout is provided, use it to set canvas size exactly
  if (props.layout && props.layout.cols > 0 && props.layout.rows > 0) {
    canvas.value.width = props.layout.cols * (size + gap)
    canvas.value.height = props.layout.rows * (size + gap)
  } else {
    // Fallback to filling container width
    const w = container.value.clientWidth
    const c = Math.floor(w / (size + gap))
    const r = Math.ceil(props.data.length / c)
    
    canvas.value.width = w
    canvas.value.height = r * (size + gap)
  }
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
    
    hoverInfo.value = {
      x: tooltipX,
      y: tooltipY,
      index,
      value: props.data[index],
      heat: decayBuffer[index] || 0
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
  if (newVal.length > decayBuffer.length) resize()

  // Detect changes
  // Optimization: Check random samples or just iterate if < 100k
  // For 65k, iteration is fast enough in JS (approx 1-2ms)
  const len = newVal.length
  let changed = false
  
  for (let i = 0; i < len; i++) {
    const v = newVal[i]
    const old = lastData[i] || 0
    
    if (v > old) {
      // Heat flash
      decayBuffer[i] = 1.0
      changed = true
      
      // Spawn ripple if it's a "new" bit (0->1)
      if (old === 0 && Math.random() > 0.9) { // Limit ripples to avoid chaos
         const c = cols.value
         const col = i % c
         const row = Math.floor(i / c)
         const x = col * (cellSize.value + props.gap) + cellSize.value/2
         const y = row * (cellSize.value + props.gap) + cellSize.value/2
         
         ripples.push({ x, y, r: 0, age: 1.0 })
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
  overflow-y: auto;
  position: relative;
}

canvas {
  display: block;
  cursor: crosshair;
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
.heat { color: #f59e0b; font-size: 11px; margin-top: 2px; }
</style>
