<template>
  <div class="page-settings">
    <header class="page-header">
      <h1>系统设置</h1>
    </header>

    <div class="settings-container">
      <div class="card">
        <div class="card-header">通用设置</div>
        <div class="form-group">
          <label>默认刷新频率</label>
          <select class="form-control">
            <option>1秒</option>
            <option>2秒</option>
            <option>5秒</option>
          </select>
        </div>
        <div class="form-group">
          <label>主题偏好</label>
          <select class="form-control">
            <option>Premium Dark</option>
            <option disabled>Light (Coming Soon)</option>
          </select>
        </div>
      </div>

      <div class="card">
        <div class="card-header">关于</div>
        <div class="about-content">
          <p><strong>ChiloDisco</strong> v0.2.0</p>
          <p>AFL++ Custom Mutator Frontend</p>
          <p class="copyright">© 2025 ChiloDBFuzz Team</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-settings {
  padding: 24px;
  max-width: 800px;
  margin: 0 auto;
}

.page-header { margin-bottom: 24px; }
.page-header h1 { margin: 0; font-size: 24px; }

.settings-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.card {
  background: var(--bg-panel-glass);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 24px;
}

.card-header {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: var(--text-secondary);
}

.form-control {
  width: 100%;
  padding: 8px 12px;
  background: var(--bg-app);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  border-radius: 4px;
  outline: none;
}

.form-control:focus {
  border-color: var(--primary);
}

.about-content {
  color: var(--text-secondary);
  line-height: 1.6;
}

.copyright {
  margin-top: 12px;
  font-size: 12px;
  color: var(--text-muted);
}
</style>
