<template>
  <div class="app-layout">
    <!-- Sidebar -->
    <aside class="sidebar" :class="{ collapsed: isCollapsed }">
      <div class="brand">
        <div class="logo-icon">
          <Zap class="icon" />
        </div>
        <span class="brand-text" v-if="!isCollapsed">ChiloDisco</span>
      </div>

      <nav class="nav-menu">
        <router-link to="/" class="nav-item" title="日志监控">
          <Activity class="icon" />
          <span class="label" v-if="!isCollapsed">日志监控</span>
        </router-link>
        <router-link to="/plot" class="nav-item" title="数据大屏">
          <BarChart2 class="icon" />
          <span class="label" v-if="!isCollapsed">数据大屏</span>
        </router-link>
        <router-link to="/bitmap" class="nav-item" title="Bitmap 热力图">
          <Grid class="icon" />
          <span class="label" v-if="!isCollapsed">Bitmap</span>
        </router-link>
        <router-link to="/downloads" class="nav-item" title="结果下载">
          <Download class="icon" />
          <span class="label" v-if="!isCollapsed">结果下载</span>
        </router-link>
        <div class="spacer"></div>
        <router-link to="/settings" class="nav-item" title="系统设置">
          <Settings class="icon" />
          <span class="label" v-if="!isCollapsed">系统设置</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <button class="collapse-btn" @click="toggleCollapse">
          <ChevronLeft v-if="!isCollapsed" class="icon" />
          <ChevronRight v-else class="icon" />
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Zap, Activity, BarChart2, Grid, Download, Settings, ChevronLeft, ChevronRight } from 'lucide-vue-next'

const isCollapsed = ref(false)
const toggleCollapse = () => isCollapsed.value = !isCollapsed.value
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: var(--bg-app);
  color: var(--text-primary);
}

/* Sidebar */
.sidebar {
  width: var(--sidebar-width);
  background: var(--bg-panel-glass);
  backdrop-filter: var(--glass-blur);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 10;
}

.sidebar.collapsed {
  width: var(--sidebar-width-collapsed);
}

.brand {
  height: var(--header-height);
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 12px;
  border-bottom: 1px solid var(--border-color);
}

.logo-icon {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, var(--primary), var(--secondary));
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 15px var(--primary-glow);
}

.logo-icon .icon {
  color: white;
  width: 20px;
  height: 20px;
}

.brand-text {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 18px;
  letter-spacing: -0.5px;
  white-space: nowrap;
  opacity: 1;
  transition: opacity 0.2s;
}

.collapsed .brand-text {
  opacity: 0;
  width: 0;
  overflow: hidden;
}

.collapsed .brand {
  padding: 0;
  justify-content: center;
}

/* Nav Menu */
.nav-menu {
  flex: 1;
  padding: 24px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.2s;
  white-space: nowrap;
  overflow: hidden;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}

.nav-item.router-link-active {
  background: rgba(59, 130, 246, 0.1);
  color: var(--primary);
  box-shadow: inset 2px 0 0 0 var(--primary); /* Left border indicator */
}

.nav-item .icon {
  width: 20px;
  height: 20px;
  min-width: 20px;
}

.collapsed .nav-item {
  padding: 12px;
  justify-content: center;
}

.spacer {
  flex: 1;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
}

.collapsed .sidebar-footer {
  justify-content: center;
}

.collapse-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 8px;
  border-radius: var(--radius-sm);
  transition: color 0.2s;
}

.collapse-btn:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.05);
}

/* Main Content */
.main-content {
  flex: 1;
  overflow: hidden; /* Scroll handled inside views */
  position: relative;
  background: radial-gradient(circle at top right, rgba(59, 130, 246, 0.05), transparent 40%),
              radial-gradient(circle at bottom left, rgba(139, 92, 246, 0.05), transparent 40%);
}

/* Transitions */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
