<template>
  <div class="page-downloads">
    <header class="page-header">
      <div class="brand">
        <h2>AFL++ 结果与数据下载</h2>
      </div>
      <div class="controls">
        <button class="btn btn-glass" @click="refreshList">
          <span :class="{ 'spin': loading }">🔄</span> 刷新状态
        </button>
      </div>
    </header>

    <!-- Quick Actions Grid -->
    <div class="quick-actions">
      <!-- Plot Data -->
      <div class="glass-panel action-card">
        <div class="card-content">
          <div class="card-title" style="color: var(--neon-cyan)">📊 plot_data</div>
          <div class="card-desc">Plot原始数据 (JSON)</div>
          <div class="card-sub">用于前端绘图</div>
        </div>
        <a href="/api/download/plot_data" class="btn btn-primary full-width" download>⬇ 下载 plot_data</a>
      </div>

      <!-- CSV Batch -->
      <div class="glass-panel action-card">
        <div class="card-content">
          <div class="card-title" style="color: var(--neon-cyan)">📦 CSV 批量打包</div>
          <div class="card-desc">批量下载所有 CSV 文件</div>
          <div class="card-sub">自动跳过不存在的文件</div>
        </div>
        <a href="/api/download/csv/zip" class="btn btn-primary full-width" download>📥 打包下载 CSV</a>
      </div>

      <!-- AFL Queue -->
      <div class="glass-panel action-card">
        <div class="card-content">
          <div class="card-title" style="color: var(--neon-yellow)">📂 AFL Queue</div>
          <div class="card-desc">打包 AFL queue 文件夹</div>
          <div class="card-sub">包含所有测试用例</div>
        </div>
        <a href="/api/download/folder/queue" class="btn btn-glass full-width" download>📥 打包下载</a>
      </div>

      <!-- AFL Crashes -->
      <div class="glass-panel action-card">
        <div class="card-content">
          <div class="card-title" style="color: var(--neon-red)">💥 AFL Crashes</div>
          <div class="card-desc">打包 AFL crashes 文件夹</div>
          <div class="card-sub">包含所有崩溃样本</div>
        </div>
        <a href="/api/download/folder/crashes" class="btn btn-glass full-width btn-danger-outline" download>📥 打包下载</a>
      </div>

      <!-- Parsed SQL -->
      <div class="glass-panel action-card">
        <div class="card-content">
          <div class="card-title" style="color: var(--neon-purple)">📝 Parsed SQL</div>
          <div class="card-desc">打包 parsed_sql 文件夹</div>
          <div class="card-sub">解析后的 SQL 结构</div>
        </div>
        <a href="/api/download/folder/parsed_sql" class="btn btn-glass full-width" download>📥 打包下载</a>
      </div>

      <!-- Generated Mutator -->
      <div class="glass-panel action-card">
        <div class="card-content">
          <div class="card-title" style="color: var(--neon-green)">🧬 Generated Mutator</div>
          <div class="card-desc">打包 generated_mutator</div>
          <div class="card-sub">生成的变异器代码</div>
        </div>
        <a href="/api/download/folder/generated_mutator" class="btn btn-glass full-width" download>📥 打包下载</a>
      </div>

      <!-- Structural SQL -->
      <div class="glass-panel action-card">
        <div class="card-content">
          <div class="card-title" style="color: var(--neon-blue)">🏗️ Structural SQL</div>
          <div class="card-desc">打包 structural_sql</div>
          <div class="card-sub">结构化 SQL 数据</div>
        </div>
        <a href="/api/download/folder/structural_sql" class="btn btn-glass full-width" download>📥 打包下载</a>
      </div>

      <!-- Download All -->
      <div class="glass-panel action-card">
        <div class="card-content">
          <div class="card-title" style="color: var(--neon-pink)">💾 Download All</div>
          <div class="card-desc">下载所有数据</div>
          <div class="card-sub">包含上述所有内容</div>
        </div>
        <a href="/api/download/all" class="btn btn-glass full-width btn-primary-outline" download>📦 全部打包下载</a>
      </div>
    </div>

    <!-- File List Table -->
    <div class="glass-panel table-panel">
      <div class="panel-header">
        <h3>📄 文件列表</h3>
        <span class="badge-count">{{ fileList.length }} 个文件</span>
      </div>
      
      <div class="table-responsive">
        <table class="file-table">
          <thead>
            <tr>
              <th style="width: 100px">类型</th>
              <th>文件名</th>
              <th style="width: 120px">大小</th>
              <th style="width: 180px">修改时间</th>
              <th style="width: 100px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading && fileList.length === 0">
              <td colspan="5" class="text-center">加载中...</td>
            </tr>
            <tr v-else-if="fileList.length === 0">
              <td colspan="5" class="text-center">暂无文件</td>
            </tr>
            <tr v-for="(file, index) in fileList" :key="index" class="fade-in">
              <td>
                <span :class="['badge', file.badgeClass]">{{ file.type }}</span>
              </td>
              <td>
                <div class="file-path" :title="file.path">
                  <span class="key-text">{{ file.key }}</span>
                  <span class="path-text">{{ file.path }}</span>
                </div>
              </td>
              <td class="mono">{{ humanSize(file.size) }}</td>
              <td class="mono">{{ file.mtime }}</td>
              <td>
                <a :href="file.downloadUrl" class="btn-icon" :class="{ disabled: !file.exists }" :title="file.exists ? '下载' : '文件不存在'">
                  ⬇
                </a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const loading = ref(false)
const fileList = ref([])

const humanSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const fetchFiles = async () => {
  loading.value = true
  fileList.value = []
  
  try {
    // Fetch CSVs
    const csvRes = await fetch('/api/download/csv/list?t=' + Date.now())
    const csvData = await csvRes.json()
    
    // Fetch Logs
    const logRes = await fetch('/api/download/log/list?t=' + Date.now())
    const logData = await logRes.json()
    
    const combined = []
    
    // Process CSVs
    if (csvData.items) {
      csvData.items.forEach(item => {
        combined.push({
          type: 'CSV',
          key: item.key,
          path: item.path,
          size: item.size,
          mtime: item.mtime,
          exists: item.exists,
          badgeClass: 'badge-csv',
          downloadUrl: '/api/download/csv?key=' + encodeURIComponent(item.key)
        })
      })
    }
    
    // Process Logs
    if (logData.items) {
      logData.items.forEach(item => {
        combined.push({
          type: 'LOG',
          key: item.key,
          path: item.path,
          size: item.size,
          mtime: item.mtime,
          exists: item.exists,
          badgeClass: 'badge-log',
          downloadUrl: '/api/download/log?key=' + encodeURIComponent(item.key)
        })
      })
    }
    
    fileList.value = combined
  } catch (e) {
    console.error('Failed to fetch file list', e)
  } finally {
    loading.value = false
  }
}

const refreshList = () => {
  fetchFiles()
}

onMounted(() => {
  fetchFiles()
})
</script>

<style scoped>
/* Define Neon Colors locally to ensure they exist */
.page-downloads {
  --neon-cyan: #22d3ee;
  --neon-yellow: #facc15;
  --neon-red: #f87171;
  --neon-purple: #c084fc;
  --neon-green: #4ade80;
  --neon-blue: #60a5fa;
  --neon-pink: #f472b6;
  
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  height: 100%;
  overflow-y: auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  border: 1px solid transparent;
}

.btn-glass {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
}

.btn-glass:hover {
  background: rgba(255, 255, 255, 0.1);
}

.btn-primary {
  background: var(--accent-primary);
  color: white;
}

.btn-primary:hover {
  filter: brightness(1.1);
}

.btn-danger-outline {
  border-color: rgba(248, 113, 113, 0.5);
  color: var(--neon-red);
}

.btn-danger-outline:hover {
  background: rgba(248, 113, 113, 0.1);
}

.btn-primary-outline {
  border-color: rgba(96, 165, 250, 0.5);
  color: var(--neon-blue);
}

.btn-primary-outline:hover {
  background: rgba(96, 165, 250, 0.1);
}

.full-width {
  width: 100%;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* Quick Actions Grid */
.quick-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.glass-panel {
  background: rgba(30, 41, 59, 0.7);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.action-card {
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 16px;
  transition: transform 0.2s;
}

.action-card:hover {
  transform: translateY(-4px);
  border-color: rgba(255, 255, 255, 0.2);
}

.card-content {
  flex: 1;
  width: 100%;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
}

.card-desc {
  color: var(--text-secondary);
  font-size: 14px;
  margin-bottom: 4px;
}

.card-sub {
  color: var(--text-secondary);
  font-size: 12px;
  opacity: 0.7;
}

/* Table Panel */
.table-panel {
  padding: 24px;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.panel-header h3 {
  margin: 0;
  font-size: 18px;
}

.badge-count {
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.table-responsive {
  overflow-x: auto;
}

.file-table {
  width: 100%;
  border-collapse: collapse;
}

.file-table th,
.file-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.file-table th {
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 13px;
}

.file-table tr:last-child td {
  border-bottom: none;
}

.file-table tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

.badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.badge-csv {
  background: rgba(34, 211, 238, 0.15);
  color: #22d3ee;
}

.badge-log {
  background: rgba(192, 132, 252, 0.15);
  color: #c084fc;
}

.file-path {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.key-text {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--text-primary);
}

.path-text {
  font-size: 12px;
  color: var(--text-secondary);
  opacity: 0.7;
}

.mono {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--text-secondary);
}

.btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
  text-decoration: none;
  transition: all 0.2s;
}

.btn-icon:hover:not(.disabled) {
  background: var(--accent-primary);
  color: white;
}

.btn-icon.disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.text-center {
  text-align: center;
  color: var(--text-secondary);
  padding: 32px;
}

.fade-in {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
