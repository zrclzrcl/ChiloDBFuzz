<template>
  <div class="page-settings">
    <header class="page-header">
      <h1>系统设置</h1>
    </header>

    <div class="settings-grid">
      <!-- Visual Effects -->
      <div class="card">
        <div class="card-header">
          <component :is="Eye" class="icon" />
          视觉效果
        </div>
        <div class="card-body">
          <div class="setting-item">
            <div class="setting-info">
              <label>性能模式</label>
              <span class="desc">禁用复杂动画以提高性能</span>
            </div>
            <label class="switch">
              <input type="checkbox" v-model="settings.performanceMode" @change="saveSettings">
              <span class="slider"></span>
            </label>
          </div>
          <div class="setting-item">
            <div class="setting-info">
              <label>粒子特效</label>
              <span class="desc">显示背景粒子动画</span>
            </div>
            <label class="switch">
              <input type="checkbox" v-model="settings.particles" @change="saveSettings" :disabled="settings.performanceMode">
              <span class="slider"></span>
            </label>
          </div>
          <div class="setting-item">
            <div class="setting-info">
              <label>霓虹光晕</label>
              <span class="desc">启用边框发光效果</span>
            </div>
            <label class="switch">
              <input type="checkbox" v-model="settings.glow" @change="saveSettings" :disabled="settings.performanceMode">
              <span class="slider"></span>
            </label>
          </div>
        </div>
      </div>

      <!-- Diagnostics -->
      <div class="card">
        <div class="card-header">
          <component :is="Activity" class="icon" />
          诊断信息
        </div>
        <div class="card-body">
          <div class="setting-item">
            <div class="setting-info">
              <label>FPS 计数器</label>
              <span class="desc">显示实时帧率</span>
            </div>
            <label class="switch">
              <input type="checkbox" v-model="settings.fps" @change="saveSettings">
              <span class="slider"></span>
            </label>
          </div>
          <div class="setting-item">
            <div class="setting-info">
              <label>内存监控</label>
              <span class="desc">显示内存使用情况 (仅Chrome)</span>
            </div>
            <label class="switch">
              <input type="checkbox" v-model="settings.memory" @change="saveSettings">
              <span class="slider"></span>
            </label>
          </div>
        </div>
      </div>

      <!-- Data Management -->
      <div class="card">
        <div class="card-header">
          <component :is="Database" class="icon" />
          数据管理
        </div>
        <div class="card-body">
          <div class="setting-item">
            <div class="setting-info">
              <label>清除缓存</label>
              <span class="desc">清除本地存储的配置和缓存</span>
            </div>
            <button class="btn btn-danger" @click="clearCache">清除</button>
          </div>
          <div class="setting-item">
            <div class="setting-info">
              <label>重置默认</label>
              <span class="desc">恢复所有设置到默认状态</span>
            </div>
            <button class="btn btn-warning" @click="resetDefaults">重置</button>
          </div>
        </div>
      </div>
      
      <!-- About -->
      <div class="card">
        <div class="card-header">
          <component :is="Info" class="icon" />
          关于
        </div>
        <div class="card-body about-content">
          <p><strong>ChiloDisco</strong> v0.2.0</p>
          <p>AFL++ 自定义变异器前端监控系统</p>
          <p class="copyright">© 2025 ChiloDBFuzz Team</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, onMounted } from 'vue'
import { Eye, Activity, Database, Info } from 'lucide-vue-next'

const defaultSettings = {
  performanceMode: false,
  particles: true,
  glow: true,
  fps: false,
  memory: false
}

const settings = reactive({ ...defaultSettings })

onMounted(() => {
  const saved = localStorage.getItem('chilo_settings')
  if (saved) {
    try {
      Object.assign(settings, JSON.parse(saved))
    } catch (e) {
      console.error('Failed to load settings', e)
    }
  }
})

const saveSettings = () => {
  localStorage.setItem('chilo_settings', JSON.stringify(settings))
  // Dispatch event for other components to react
  window.dispatchEvent(new Event('settings-changed'))
}

const clearCache = () => {
  if(confirm('确定要清除所有缓存吗？')) {
    localStorage.clear()
    location.reload()
  }
}

const resetDefaults = () => {
  if(confirm('确定要恢复默认设置吗？')) {
    Object.assign(settings, defaultSettings)
    saveSettings()
  }
}
</script>

<style scoped>
.page-settings {
  padding: 24px;
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 32px;
}

.page-header h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
  background: linear-gradient(45deg, #a855f7, #ec4899);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 24px;
}

.card {
  background: rgba(30, 30, 35, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  border-color: rgba(168, 85, 247, 0.3);
}

.card-header {
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-main);
}

.card-header .icon {
  width: 18px;
  height: 18px;
  color: #a855f7;
}

.card-body {
  padding: 20px;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.setting-info label {
  font-size: 15px;
  color: var(--text-main);
}

.setting-info .desc {
  font-size: 12px;
  color: var(--text-muted);
}

/* Switch Toggle */
.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.1);
  transition: .4s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: .4s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: #a855f7;
}

input:checked + .slider:before {
  transform: translateX(20px);
}

input:disabled + .slider {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Buttons */
.btn {
  padding: 6px 16px;
  border-radius: 6px;
  border: none;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-danger {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.btn-danger:hover {
  background: rgba(239, 68, 68, 0.25);
}

.btn-warning {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.btn-warning:hover {
  background: rgba(245, 158, 11, 0.25);
}

.about-content {
  text-align: center;
  color: var(--text-muted);
}

.about-content p {
  margin: 8px 0;
}

.copyright {
  font-size: 12px;
  opacity: 0.6;
  margin-top: 16px !important;
}
</style>
