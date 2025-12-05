<template>
  <div class="page-downloads">
    <header class="page-header">
      <h1>结果下载</h1>
    </header>

    <div class="downloads-grid">
      <div class="card download-card" v-for="item in items" :key="item.id">
        <div class="icon-box">
          <component :is="item.icon" />
        </div>
        <div class="info">
          <h3>{{ item.title }}</h3>
          <p>{{ item.desc }}</p>
        </div>
        <a :href="item.url" class="btn-download" download>
          <Download class="btn-icon" />
          下载
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { FileText, Database, Download, Archive } from 'lucide-vue-next'

const items = [
  { id: 1, title: 'Bitmap (Sum)', desc: '累计命中次数统计', url: '/api/download/bitmap?type=sum', icon: Database },
  { id: 2, title: 'Bitmap (Bool)', desc: '覆盖率布尔位图', url: '/api/download/bitmap?type=bool', icon: Database },
  { id: 3, title: 'Bitmap (All)', desc: '所有位图数据打包', url: '/api/download/bitmap/all', icon: Archive },
  { id: 4, title: 'Fuzz Stats', desc: '模糊测试统计数据 (CSV)', url: '/api/plot?format=csv', icon: FileText }, // Mock URL
]
</script>

<style scoped>
.page-downloads {
  padding: 24px;
}

.page-header { margin-bottom: 24px; }
.page-header h1 { margin: 0; font-size: 24px; }

.downloads-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
}

.card {
  background: var(--bg-panel-glass);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  transition: transform 0.2s, box-shadow 0.2s;
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: var(--primary);
}

.icon-box {
  width: 64px;
  height: 64px;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  color: var(--primary);
}

.icon-box svg {
  width: 32px;
  height: 32px;
}

.info h3 { margin: 0 0 8px 0; font-size: 18px; }
.info p { margin: 0 0 24px 0; color: var(--text-secondary); font-size: 14px; }

.btn-download {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--primary);
  color: white;
  padding: 8px 24px;
  border-radius: 20px;
  text-decoration: none;
  font-weight: 500;
  transition: background 0.2s;
}

.btn-download:hover {
  background: #2563eb;
}

.btn-icon { width: 16px; height: 16px; }
</style>
