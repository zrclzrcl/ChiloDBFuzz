<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-icon">⚡</span>
        <span>ChiloDisco</span>
      </div>
      <nav class="nav-menu">
        <router-link to="/" class="nav-item" active-class="active">
          <span>📊 日志监控</span>
        </router-link>
        <router-link to="/plot" class="nav-item" active-class="active">
          <span>📈 数据大屏</span>
        </router-link>
        <router-link to="/bitmap" class="nav-item" active-class="active">
          <span>🗺️ Bitmap 热力图</span>
        </router-link>
        <router-link to="/downloads" class="nav-item" active-class="active">
          <span>💾 结果下载</span>
        </router-link>
        <router-link to="/settings" class="nav-item" active-class="active">
          <span>⚙️ 系统设置</span>
        </router-link>
      </nav>
    </aside>

    <main class="main-content">
      <router-view></router-view>
    </main>
  </div>
</template>

<script setup>
// App layout logic only
</script>

<style>
/* Global Reset & Variables */
:root {
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --accent-primary: #00ff9f;
  --accent-secondary: #0ea5e9;
  --border-color: #334155;
  --font-mono: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  height: 100vh;
  overflow: hidden;
}

#app {
  height: 100%;
}

/* Layout */
.app-layout {
  display: flex;
  height: 100%;
}

/* Sidebar */
.sidebar {
  width: 240px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.brand {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  font-size: 18px;
  font-weight: 700;
  color: var(--accent-primary);
  border-bottom: 1px solid var(--border-color);
}

.brand-icon {
  margin-right: 10px;
  font-size: 24px;
}

.nav-menu {
  padding: 20px 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 12px 24px;
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: rgba(255,255,255,0.05);
  color: var(--text-primary);
}

.nav-item.active {
  background: rgba(0, 255, 159, 0.1);
  color: var(--accent-primary);
  border-left-color: var(--accent-primary);
}

/* Main Content */
.main-content {
  flex: 1;
  overflow: hidden;
  position: relative;
  display: flex;
  flex-direction: column;
}
</style>
