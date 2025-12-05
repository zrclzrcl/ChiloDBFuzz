<template>
  <div class="bit-grid-container" ref="container">
    <canvas ref="canvas" @mousemove="handleMouseMove" @mouseleave="hoverInfo = null"></canvas>
    
    <div v-if="hoverInfo" class="grid-tooltip" :style="{ top: hoverInfo.y + 'px', left: hoverInfo.x + 'px' }">
      <div class="idx">Index: {{ hoverInfo.index }}</div>
      <div class="val">Value: {{ hoverInfo.value }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'

const props = defineProps({
  data: { type: Array, default: () => [] },
  type: { type: String, default: 'bool' }, // 'bool' | 'heat'
  cellSize: { type: Number, default: 4 },
  gap: { type: Number, default: 1 }
})

const container = ref(null)
const canvas = ref(null)
const hoverInfo = ref(null)

// Computed layout
const cols = computed(() => {
  if (!container.value) return 64
  const w = container.value.clientWidth
  return Math.floor(w / (props.cellSize + props.gap))
})

function draw() {
  const ctx = canvas.value?.getContext('2d')
  if (!ctx || !props.data.length) return

  const w = container.value.clientWidth
  const total = props.data.length
  const c = cols.value
  const r = Math.ceil(total / c)
  
  const size = props.cellSize
  const gap = props.gap
  
  // Resize canvas
  canvas.value.width = w
  canvas.value.height = r * (size + gap)

  ctx.clearRect(0, 0, canvas.value.width, canvas.value.height)

  for (let i = 0; i < total; i++) {
    const val = props.data[i]
    if (val === 0 && props.type === 'bool') continue // Skip empty in bool mode for transparent bg
    
    const col = i % c
    const row = Math.floor(i / c)
    const x = col * (size + gap)
    const y = row * (size + gap)

    ctx.fillStyle = getColor(val)
    ctx.fillRect(x, y, size, size)
  }
}

function getColor(val) {
  if (props.type === 'bool') {
    return val > 0 ? '#00f0ff' : '#1e293b'
  } else {
    // Heatmap: Log scale or linear?
    if (val === 0) return '#1e293b'
    // Simple heatmap logic
    const intensity = Math.min(1, Math.log2(val + 1) / 8) // Assume max ~255 or higher
    // Interpolate from Blue to Purple to Pink
    return `hsl(${200 + intensity * 120}, 100%, ${30 + intensity * 40}%)`
  }
}

function handleMouseMove(e) {
  const rect = canvas.value.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  
  const size = props.cellSize + props.gap
  const c = cols.value
  
  const col = Math.floor(x / size)
  const row = Math.floor(y / size)
  const index = row * c + col
  
  if (index >= 0 && index < props.data.length) {
    hoverInfo.value = {
      x: e.clientX + 10, // Offset from mouse
      y: e.clientY + 10,
      index,
      value: props.data[index]
    }
  } else {
    hoverInfo.value = null
  }
}

watch(() => props.data, draw, { deep: true })
onMounted(() => {
  window.addEventListener('resize', draw)
  draw()
})
</script>

<style scoped>
.bit-grid-container {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  position: relative;
}

canvas {
  display: block;
}

.grid-tooltip {
  position: fixed;
  background: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(4px);
  border: 1px solid var(--primary);
  padding: 8px 12px;
  border-radius: 4px;
  pointer-events: none;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0,0,0,0.5);
}

.idx { color: var(--text-muted); font-size: 12px; }
.val { color: var(--primary); font-weight: bold; font-family: var(--font-mono); }
</style>
