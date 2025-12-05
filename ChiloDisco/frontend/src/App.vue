<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-icon">⚡</span>
        <span>ChiloDisco</span>
      </div>
      <nav class="nav-menu">
        <a href="/" class="nav-item active">
          <span>📊 日志监控</span>
        </a>
        <a href="/plot" class="nav-item">
          <span>📈 数据大屏</span>
        </a>
        <a href="/bitmap" class="nav-item">
          <span>🗺️ Bitmap 热力图</span>
        </a>
        <a href="/downloads" class="nav-item">
          <span>💾 结果下载</span>
        </a>
        <a href="/settings" class="nav-item">
          <span>⚙️ 系统设置</span>
        </a>
      </nav>
    </aside>

    <main class="main-content">
      <div class="content-scrollable">
        <div style="max-width: 1600px; margin: 0 auto;">
          
          <header class="app-header">
            <div>
              <h2 style="margin: 0;">实时日志监控</h2>
              <span class="text-sm text-muted">AFL++ Custom Mutator Monitor</span>
            </div>
            <div class="controls">
              <button class="btn btn-glass" @click="togglePause" :class="{ 'btn-primary': !paused }">
                {{ paused ? '▶️ 继续刷新' : '⏸️ 暂停刷新' }}
              </button>
              
              <div class="flex-row items-center gap-2" style="background: rgba(0,0,0,0.2); padding: 4px 8px; border-radius: 6px;">
                  <span class="text-sm text-muted">频率</span>
                  <select v-model.number="interval" :disabled="paused" style="padding: 2px; border: none; background: transparent;">
                    <option :value="200">0.2s</option>
                    <option :value="500">0.5s</option>
                    <option :value="1000">1s</option>
                    <option :value="2000">2s</option>
                    <option :value="5000">5s</option>
                  </select>
              </div>

              <div class="flex-row items-center gap-2" style="background: rgba(0,0,0,0.2); padding: 4px 8px; border-radius: 6px;">
                  <span class="text-sm text-muted">行数</span>
                  <select v-model.number="maxLines" style="padding: 2px; border: none; background: transparent;">
                    <option :value="200">200</option>
                    <option :value="500">500</option>
                    <option :value="800">800</option>
                  </select>
              </div>
            </div>
          </header>

          <!-- Search Toolbar -->
          <div class="search-toolbar glass-panel">
            <div class="search-box">
              <span>🔍</span>
              <input 
                type="text" 
                v-model="searchQuery" 
                placeholder="搜索日志内容... (支持正则表达式)"
                class="search-input"
                @keydown.escape="searchQuery = ''"
              />
              <button v-if="searchQuery" @click="searchQuery = ''" class="btn btn-glass" style="padding: 2px 8px; font-size: 12px;">✕</button>
            </div>
            
            <div v-if="searchQuery" class="text-sm text-muted">
              {{ totalMatches }} 条匹配
            </div>
            
            <div class="flex-row gap-4">
              <label class="flex-row items-center gap-2 text-sm" title="只显示包含错误的行" style="cursor: pointer;">
                <input type="checkbox" v-model="filterError" />
                <span :style="{ color: filterError ? '#ef4444' : '' }">🔴 仅错误</span>
              </label>
              <label class="flex-row items-center gap-2 text-sm" title="只显示包含警告的行" style="cursor: pointer;">
                <input type="checkbox" v-model="filterWarn" />
                <span :style="{ color: filterWarn ? '#f59e0b' : '' }">🟡 仅警告</span>
              </label>
            </div>
          </div>

          <!-- Log Grid -->
          <div class="log-grid">
            <section class="log-card glass-panel" v-for="panel in filteredPanels" :key="panel.key" :style="{ borderColor: panel.accent ? panel.accent : '' }">
              <header class="card-header">
                <div>
                    <div class="file-name">{{ panel.filename }}</div>
                    <div class="text-sm text-muted">{{ getDisplayName(panel.key) }}</div>
                </div>
                <div class="meta-info">
                  <span :title="'最近修改：' + panel.mtimeText">{{ panel.mtimeText }}</span>
                  <span v-if="panel.bucketLabel" class="recency-dot" :style="{ color: panel.accent, boxShadow: '0 0 8px ' + panel.accent }"></span>
                  <span v-if="panel.matchCount > 0" class="badge" style="background:var(--accent-primary); padding: 2px 6px; border-radius: 4px; color: #fff;">{{ panel.matchCount }}</span>
                </div>
              </header>
              <pre class="log-body" ref="scrollers" @dblclick="copyLogContent($event, panel)"><code class="log-lines" v-html="panel.displayHtml"></code></pre>
            </section>
          </div>
          
          <footer style="margin-top: 2rem; text-align: center; color: var(--text-secondary); font-size: 0.8rem; padding-bottom: 1rem;">
              © 2025 ChiloDisco · Log Monitor
          </footer>

        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref, reactive, watch, nextTick } from 'vue'

// --- Logic Ported from app.js ---

// 日志键名中文映射
const logNameMap = {
  'LLM_LOG_PATH': 'LLM日志',
  'MAIN_LOG_PATH': '主日志',
  'MUTATOR_FIXER_LOG_PATH': '修复日志',
  'MUTATOR_GENERATOR_LOG_PATH': '生成器日志',
  'PARSER_LOG_PATH': '解析器日志',
  'STRUCTURAL_MUTATOR_LOG_PATH': '结构变异日志'
};

function getDisplayName(key) {
  return logNameMap[key] || key;
}

// Config
const savedInterval = localStorage.getItem('cd_interval');
const savedMaxLines = localStorage.getItem('cd_maxLines');
const interval = ref(savedInterval ? parseInt(savedInterval, 10) : 500);
const maxLines = ref(savedMaxLines ? parseInt(savedMaxLines, 10) : 500);
const panels = reactive([]);

// State
const searchQuery = ref('');
const filterError = ref(false);
const filterWarn = ref(false);
const paused = ref(false);
const totalMatches = ref(0);
const filteredPanels = reactive([]);

let timer = null;

// Persistence
const STICK_KEY_PREFIX = 'cd_stick_';
const FS_KEY_PREFIX = 'cd_fs_';

function getStick(key){
  try{ const v = sessionStorage.getItem(STICK_KEY_PREFIX + key); return v === null ? true : v === '1'; }catch(_){ return true; }
}
function setStick(key, val){
  try{ sessionStorage.setItem(STICK_KEY_PREFIX + key, val ? '1' : '0'); }catch(_){ /* ignore */ }
}
function loadFS(key){
  try{ const s = sessionStorage.getItem(FS_KEY_PREFIX + key); return s ? JSON.parse(s) : {}; }catch(_){ return {}; }
}
function saveFS(key, obj){
  try{ sessionStorage.setItem(FS_KEY_PREFIX + key, JSON.stringify(obj)); }catch(_){ /* ignore */ }
}

function isAtBottom(el){ if(!el) return true; return (el.scrollHeight - el.scrollTop - el.clientHeight) <= 8; }
function scrollToBottom(el){ if(!el) return; el.scrollTop = el.scrollHeight; }

const tsRegex = /(\b\d{4}[-\/]\d{2}[-\/]\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?\b)|(\b\d{2}:\d{2}:\d{2}\b)/g;

function hueForAge(ageSec){
  if (ageSec <= 2) return 140; 
  if (ageSec <= 5) return 105; 
  if (ageSec <= 10) return 80; 
  if (ageSec <= 20) return 60; 
  if (ageSec <= 40) return 40; 
  if (ageSec <= 60) return 25; 
  if (ageSec <= 90) return 12; 
  return 0;                    
}

function glowForAge(ageSec){
  if (ageSec <= 2) return { blur: 12, alpha: 0.9 };
  if (ageSec <= 5) return { blur: 10, alpha: 0.8 };
  if (ageSec <= 10) return { blur: 8, alpha: 0.7 };
  if (ageSec <= 20) return { blur: 6, alpha: 0.6 };
  if (ageSec <= 40) return { blur: 4, alpha: 0.45 };
  if (ageSec <= 60) return { blur: 3, alpha: 0.35 };
  if (ageSec <= 90) return { blur: 2, alpha: 0.25 };
  return { blur: 0, alpha: 0 };
}
function bucketLabel(ageSec){
  if (ageSec <= 2) return '0–2秒';
  if (ageSec <= 5) return '2–5秒';
  if (ageSec <= 10) return '5–10秒';
  if (ageSec <= 20) return '10–20秒';
  if (ageSec <= 40) return '20–40秒';
  if (ageSec <= 60) return '40–60秒';
  if (ageSec <= 90) return '60–90秒';
  return '≥90秒';
}
function humanSize(bytes){
  if (!bytes || bytes < 0) return '—';
  if (bytes < 1024) return bytes + ' B';
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const val = (bytes / Math.pow(1024, i)).toFixed(1);
  return val + ' ' + ['B','KB','MB','GB','TB'][i];
}
function fmtTime(iso){
  if (!iso) return '—';
  try{ const d = new Date(iso); return d.toLocaleString(); } catch(e){ return iso; }
}
function escapeHtml(s){
  return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
}

function smartHighlight(text) {
  let result = text;
  result = result.replace(/\b(ERROR|Error|error|FATAL|Fatal|fatal|CRASH|Crash|crash)\b/g, '<span class="highlight-error">$1</span>');
  result = result.replace(/\b(WARN|Warning|warning|CAUTION|Caution)\b/g, '<span class="highlight-warn">$1</span>');
  result = result.replace(/\b(SUCCESS|Success|OK|INFO|Info)\b/g, '<span class="highlight-success">$1</span>');
  result = result.replace(/\b(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|FROM|WHERE|JOIN|GROUP BY|ORDER BY|HAVING|LIMIT)\b/gi, '<span class="highlight-sql">$&</span>');
  result = result.replace(/([a-zA-Z]:\\|\/)[\w\-\/\\.]+\.\w+/g, '<span class="highlight-path">$&</span>');
  result = result.replace(/\b\d+\b/g, '<span class="highlight-number">$&</span>');
  return result;
}

function matchesSearch(line, query) {
  if (!query) return true;
  try {
    const regex = new RegExp(query, 'i');
    return regex.test(line);
  } catch (e) {
    return line.toLowerCase().includes(query.toLowerCase());
  }
}

function containsError(line) {
  return /\b(ERROR|Error|error|FATAL|Fatal|fatal|CRASH|Crash|crash)\b/.test(line);
}

function containsWarn(line) {
  return /\b(WARN|Warning|warning|CAUTION|Caution)\b/.test(line);
}

function highlightSearch(text, query) {
  if (!query) return text;
  try {
    const regex = new RegExp(`(${query})`, 'gi');
    return text.replace(regex, '<mark class="search-match">$1</mark>');
  } catch (e) {
    const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escaped})`, 'gi');
    return text.replace(regex, '<mark class="search-match">$1</mark>');
  }
}

function parseLineAgeSecFromContent(line, now){
  const m = line.match(tsRegex);
  if (!m) return null;
  for (const t of m){
    let d = null;
    if (/^\d{2}:\d{2}:\d{2}$/.test(t)){
      const today = new Date(now);
      const y = today.getFullYear();
      const mo = String(today.getMonth()+1).padStart(2,'0');
      const da = String(today.getDate()).padStart(2,'0');
      d = new Date(`${y}-${mo}-${da}T${t}`);
    }else{
      d = new Date(t.replace(' ', 'T'));
    }
    if (!isNaN(d)){
      return Math.max(0, (now - d)/1000.0);
    }
  }
  return null;
}

function colorizeLineObj(lineObj, fallbackHue, now, searchQ = '') {
  const raw = (lineObj?.s ?? '');
  const text = raw
    .replace(/^\uFEFF/, '')
    .replace(/^[\r\n]+/, '')
    .replace(/^[\s\t\u00A0\uFEFF\u2000-\u200B\u3000]+/, '');
  let ageSec = null;
  if (lineObj && lineObj.t){
    const dt = new Date(lineObj.t);
    if (!isNaN(dt)) ageSec = Math.max(0, (now - dt)/1000.0);
  }
  if (ageSec == null){
    ageSec = parseLineAgeSecFromContent(text, now);
  }
  const hue = hueForAge(ageSec ?? 999999);
  const effectiveHue = (ageSec == null) ? fallbackHue : hue;
  const glow = glowForAge(ageSec ?? 999999);
  const color = `hsl(${effectiveHue} 100% 55%)`;
  const inner = glow.blur;
  const outer = Math.round(glow.blur * 2);
  const alpha1 = glow.alpha;
  const alpha2 = Math.max(0, Math.min(1, glow.alpha * 0.6));
  const shadow = (glow.blur > 0)
    ? `0 0 ${inner}px hsla(${effectiveHue} 100% 60% / ${alpha1}), 0 0 ${outer}px hsla(${effectiveHue} 100% 60% / ${alpha2})`
    : 'none';
  
  let escaped = escapeHtml(text);
  escaped = smartHighlight(escaped);
  if (searchQ) {
    escaped = highlightSearch(escaped, searchQ);
  }
  
  const withTs = escaped.replace(tsRegex, (m) => `<span class="timestamp" style="color:${color}; text-shadow:${shadow}">${m}</span>`);
  return `<span style="color:${color}; text-shadow:${shadow}">${withTs}</span>`;
}

function rebuildPanelsFromLogs(logs){
  const keys = Object.keys(logs).sort();
  const map = new Map(panels.map(p => [p.key, p]));
  const next = [];
  for (const k of keys){
    const old = map.get(k);
    next.push(old ?? { key:k, filename:'', hue:120, accent:'hsl(120 100% 55%)', bucketLabel:'', mtimeText:'—', sizeText:'—', html:'(加载中...)', visibleRows: null });
    if (getStick(k) === null) setStick(k, true);
  }
  panels.splice(0, panels.length, ...next);
}

function bindScrollHandlers(){
  const scrollers = document.querySelectorAll('pre.log-body');
  scrollers.forEach((el, idx) => {
    if (el.__cd_bound) return;
    el.__cd_bound = true;
    el.addEventListener('scroll', () => {
      const p = panels[idx];
      if (!p) return;
      const stick = isAtBottom(el);
      setStick(p.key, stick);
    }, { passive: true });
  });
  scrollers.forEach((el, idx) => {
    const p = panels[idx];
    if (!p) return;
    if (getStick(p.key)) scrollToBottom(el);
  });
}

async function fetchLogs(){
  try{
    const r = await fetch('/api/logs?t='+Date.now(), { cache:'no-store' });
    const data = await r.json();
    const now = new Date(data.now);
    const nowIso = data.now;
    const logs = data.logs || {};
    rebuildPanelsFromLogs(logs);
    await nextTick();

    const scrollers = document.querySelectorAll('pre.log-body');
    const prevStates = panels.map((p, i) => {
      const el = scrollers[i];
      return {
        key: p.key,
        el,
        top: el ? el.scrollTop : 0,
        height: el ? el.scrollHeight : 0,
        wasAtBottom: isAtBottom(el),
        stick: getStick(p.key)
      };
    });

    for (const [idx, panel] of panels.entries()){
      const info = logs[panel.key];
      if (!info) continue;
      panel.filename = (info.path || '').split(/[/\\]/).pop() || '';
      const exists = !!info.exists;
      panel.sizeText = exists ? humanSize(info.size||0) : '不存在';
      panel.mtimeText = exists ? fmtTime(info.mtime) : '—';

      let ageSec = 999999;
      if (exists && info.mtime){
        const mt = new Date(info.mtime);
        ageSec = Math.max(0, (now - mt)/1000.0);
      }
      const hue = hueForAge(ageSec);
      panel.hue = hue;
      panel.accent = `hsl(${hue} 100% 55%)`;
      panel.bucketLabel = bucketLabel(ageSec);

      const all = Array.isArray(info.lines) ? info.lines : [];
      const sliced = all.slice(-Math.min(all.length, maxLines.value));
      const fs = loadFS(panel.key);
      const enriched = sliced.map(o => {
        let t = o.t;
        if (!t){ t = fs[o.s] || nowIso; fs[o.s] = t; }
        return { s: o.s, t };
      });
      const newFS = {};
      for (const row of enriched){ newFS[row.s] = row.t; }
      saveFS(panel.key, newFS);

      let filtered = enriched;
      if (filterError.value) filtered = filtered.filter(obj => containsError(obj.s));
      if (filterWarn.value) filtered = filtered.filter(obj => containsWarn(obj.s));
      if (searchQuery.value) filtered = filtered.filter(obj => matchesSearch(obj.s, searchQuery.value));
      
      panel.matchCount = filtered.length;
      const html = filtered.map(obj => colorizeLineObj(obj, hue, now, searchQuery.value)).join('\n');
      panel.html = html || '<span style="color:#7a8aa3">(空)</span>';
      panel.displayHtml = panel.html;
      panel.rawLines = enriched;
    }

    await nextTick();
    const scrollersAfter = document.querySelectorAll('pre.log-body');
    prevStates.forEach((st, i) => {
      const el = scrollersAfter[i];
      if (!el) return;
      if (st.stick || st.wasAtBottom){
        scrollToBottom(el);
      } else {
        el.scrollTop = st.top || 0;
      }
    });

    bindScrollHandlers();
  }catch(e){
    console.error('fetch logs error', e);
  }
}

function start(){
  stop();
  if (!paused.value) {
    timer = setInterval(fetchLogs, interval.value);
  }
}
function stop(){ if (timer) { clearInterval(timer); timer=null; } }

function togglePause() {
  paused.value = !paused.value;
  if (paused.value) stop(); else start();
}

function copyLogContent(event, panel) {
  const text = panel.rawLines ? panel.rawLines.map(o => o.s).join('\n') : '';
  if (text) {
    navigator.clipboard.writeText(text).then(() => {
      if (window.ChiloDisco?.toast) {
        window.ChiloDisco.toast.success('日志内容已复制到剪贴板！');
      }
      const target = event.currentTarget;
      target.style.boxShadow = '0 0 40px rgba(0, 255, 159, 0.8)';
      setTimeout(() => { target.style.boxShadow = ''; }, 500);
    }).catch(() => {
        if (window.ChiloDisco?.toast) window.ChiloDisco.toast.error('复制失败，请重试！');
    });
  }
}

// Watchers
watch([searchQuery, filterError, filterWarn, panels], () => {
  let total = 0;
  const filtered = [];
  for (const panel of panels) {
    if (searchQuery.value || filterError.value || filterWarn.value) {
      total += panel.matchCount || 0;
    }
    if (searchQuery.value || filterError.value || filterWarn.value) {
      if ((panel.matchCount || 0) > 0) filtered.push(panel);
    } else {
      filtered.push(panel);
    }
  }
  totalMatches.value = total;
  filteredPanels.splice(0, filteredPanels.length, ...filtered);
}, { deep: true });

watch(interval, (newVal) => {
  localStorage.setItem('cd_interval', newVal);
  start();
});
watch(maxLines, (newVal) => {
  localStorage.setItem('cd_maxLines', newVal);
  fetchLogs();
});
watch([searchQuery, filterError, filterWarn], () => fetchLogs());

// Keyboard shortcuts
const handleKeydown = (e) => {
    if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
        togglePause();
    }
    if (e.ctrlKey && e.key === 'f') {
        e.preventDefault();
        const s = document.querySelector('.search-input');
        if (s) { s.focus(); s.select(); }
    }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown);
  fetchLogs();
  start();
  window.addEventListener('resize', () => fetchLogs());
})
</script>

<style scoped>
/* Scoped overrides if needed, most styles are global in styles.css */
/* Specifically for page header overrides matching index.html inline styles */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 1rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--glass-border);
}
.controls {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.search-toolbar {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-bottom: 1.5rem;
  background: rgba(0,0,0,0.2);
  padding: 0.75rem;
  border-radius: 0.75rem;
  border: 1px solid var(--glass-border);
}
.search-box {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  position: relative;
}
.search-input {
  width: 100%;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
}
.search-input:focus {
 outline: none;
}
.log-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 1.5rem;
}
.log-card {
  display: flex;
  flex-direction: column;
  height: 500px;
  transition: transform 0.2s, box-shadow 0.2s;
}
.log-card:hover {
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}
.card-header {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--glass-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255,255,255,0.02);
}
.file-name {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  color: var(--accent-primary);
}
.meta-info {
  font-size: 0.8rem;
  color: var(--text-secondary);
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.log-body {
  flex: 1;
  overflow: auto;
  padding: 0.5rem;
  margin: 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  background: rgba(0,0,0,0.3);
  color: #d1d5db;
  white-space: pre-wrap;
  word-break: break-all;
}
.log-body::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.05);
}
.recency-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  background-color: var(--text-secondary);
  box-shadow: 0 0 5px currentColor;
}
</style>
