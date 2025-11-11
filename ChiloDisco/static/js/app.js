const { createApp, onMounted, ref, reactive, watch, nextTick } = Vue;

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

createApp({
  setup(){
    // 从 localStorage 恢复用户的刷新频率和显示行数设置
    const savedInterval = localStorage.getItem('cd_interval');
    const savedMaxLines = localStorage.getItem('cd_maxLines');
    
    const interval = ref(savedInterval ? parseInt(savedInterval, 10) : 500);
    const maxLines = ref(savedMaxLines ? parseInt(savedMaxLines, 10) : 500);
    const panels = reactive([]);
    
    // 新增：搜索与过滤状态
    const searchQuery = ref('');
    const filterError = ref(false);
    const filterWarn = ref(false);
    const paused = ref(false);
    const totalMatches = ref(0);
    
    let timer = null;

    // —— 滚动 & 首次看到时间 持久化辅助 ——
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
      if (ageSec <= 2) return 140;       // 0–2s（鲜绿）
      if (ageSec <= 5) return 105;       // 2–5s（青绿→黄绿），拉开与首档差距
      if (ageSec <= 10) return 80;       // 5–10s（黄绿→黄）
      if (ageSec <= 20) return 60;       // 10–20s（黄→橙黄）
      if (ageSec <= 40) return 40;       // 20–40s（橙）
      if (ageSec <= 60) return 25;       // 40–60s（橙红）
      if (ageSec <= 90) return 12;       // 60–90s（红偏橙）
      return 0;                          // ≥90s（红）
    }
    // 发光强度：越新发光越强，越旧越弱
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

    // 智能高亮：识别 ERROR、WARN、SQL、文件路径等
    function smartHighlight(text) {
      let result = text;
      
      // 高亮 ERROR（红色加粗）
      result = result.replace(/\b(ERROR|Error|error|FATAL|Fatal|fatal|CRASH|Crash|crash)\b/g, 
        '<span class="highlight-error">$1</span>');
      
      // 高亮 WARN（黄色）
      result = result.replace(/\b(WARN|Warning|warning|CAUTION|Caution)\b/g, 
        '<span class="highlight-warn">$1</span>');
      
      // 高亮 SUCCESS/INFO（绿色）
      result = result.replace(/\b(SUCCESS|Success|OK|INFO|Info)\b/g, 
        '<span class="highlight-success">$1</span>');
      
      // 高亮 SQL 关键字（青色）
      result = result.replace(/\b(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|FROM|WHERE|JOIN|GROUP BY|ORDER BY|HAVING|LIMIT)\b/gi, 
        '<span class="highlight-sql">$&</span>');
      
      // 高亮文件路径（紫色）
      result = result.replace(/([a-zA-Z]:\\|\/)[\w\-\/\\.]+\.\w+/g, 
        '<span class="highlight-path">$&</span>');
      
      // 高亮数字（淡青色）
      result = result.replace(/\b\d+\b/g, 
        '<span class="highlight-number">$&</span>');
      
      return result;
    }

    // 检查行是否匹配搜索条件
    function matchesSearch(line, query) {
      if (!query) return true;
      try {
        const regex = new RegExp(query, 'i');
        return regex.test(line);
      } catch (e) {
        // 如果不是有效的正则，使用字符串匹配
        return line.toLowerCase().includes(query.toLowerCase());
      }
    }

    // 检查行是否包含错误
    function containsError(line) {
      return /\b(ERROR|Error|error|FATAL|Fatal|fatal|CRASH|Crash|crash)\b/.test(line);
    }

    // 检查行是否包含警告
    function containsWarn(line) {
      return /\b(WARN|Warning|warning|CAUTION|Caution)\b/.test(line);
    }

    // 高亮搜索匹配项
    function highlightSearch(text, query) {
      if (!query) return text;
      try {
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<mark class="search-match">$1</mark>');
      } catch (e) {
        // 如果正则无效，使用简单替换
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
      // 严格清洗行首：BOM、CR/LF、各类不可见与全角空白，仅作用于行首，保留行内格式
      const raw = (lineObj?.s ?? '');
      const text = raw
        .replace(/^\uFEFF/, '')                 // BOM
        .replace(/^[\r\n]+/, '')               // 开头换行
        .replace(/^[\s\t\u00A0\uFEFF\u2000-\u200B\u3000]+/, ''); // 行首空白
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
      
      // 应用智能高亮
      escaped = smartHighlight(escaped);
      
      // 应用搜索高亮
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
        // 初始化默认“跟随底部”
        if (getStick(k) === null) setStick(k, true);
      }
      panels.splice(0, panels.length, ...next);
    }

    function bindScrollHandlers(){
      const scrollers = document.querySelectorAll('pre.log-body');
      scrollers.forEach((el, idx) => {
        // 避免重复绑定
        if (el.__cd_bound) return;
        el.__cd_bound = true;
        el.addEventListener('scroll', () => {
          const p = panels[idx];
          if (!p) return;
          const stick = isAtBottom(el);
          setStick(p.key, stick);
        }, { passive: true });
      });
      // 初始若设置为跟随底部，则滚到底
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

        // 渲染前记录各面板滚动状态
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

          // 客户端 first-seen 时间缓存，增强逐行颜色的稳定性（跨页面返回时也生效）
          const all = Array.isArray(info.lines) ? info.lines : [];
          const sliced = all.slice(-Math.min(all.length, maxLines.value));
          const fs = loadFS(panel.key);
          const enriched = sliced.map(o => {
            let t = o.t;
            if (!t){ t = fs[o.s] || nowIso; fs[o.s] = t; }
            return { s: o.s, t };
          });
          // 保存当前窗口的映射，限制体积
          const newFS = {};
          for (const row of enriched){ newFS[row.s] = row.t; }
          saveFS(panel.key, newFS);

          // 应用过滤和搜索
          let filtered = enriched;
          
          // 过滤错误
          if (filterError.value) {
            filtered = filtered.filter(obj => containsError(obj.s));
          }
          
          // 过滤警告
          if (filterWarn.value) {
            filtered = filtered.filter(obj => containsWarn(obj.s));
          }
          
          // 搜索过滤
          if (searchQuery.value) {
            filtered = filtered.filter(obj => matchesSearch(obj.s, searchQuery.value));
          }
          
          panel.matchCount = filtered.length;
          
          const html = filtered.map(obj => colorizeLineObj(obj, hue, now, searchQuery.value)).join('\n');
          panel.html = html || '<span style="color:#7a8aa3">(空)</span>';
          panel.displayHtml = panel.html;
          panel.rawLines = enriched; // 保存原始数据供后续使用
        }

        await nextTick();
        // 根据 stickBottom 或是否已经在底部，调整滚动位置
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
      if (paused.value) {
        stop();
      } else {
        start();
      }
    }
    
    // 复制日志内容
    function copyLogContent(event, panel) {
      const text = panel.rawLines ? panel.rawLines.map(o => o.s).join('\n') : '';
      if (text) {
        navigator.clipboard.writeText(text).then(() => {
          // Toast 提示
          if (window.ChiloDisco?.toast) {
            window.ChiloDisco.toast.success('日志内容已复制到剪贴板！');
          }
          // 简单的视觉反馈
          const target = event.currentTarget;
          target.style.boxShadow = '0 0 40px rgba(0, 255, 159, 0.8)';
          setTimeout(() => {
            target.style.boxShadow = '';
          }, 500);
        }).catch(() => {
          if (window.ChiloDisco?.toast) {
            window.ChiloDisco.toast.error('复制失败，请重试！');
          }
        });
      }
    }
    
    // 计算总匹配数
    const filteredPanels = reactive([]);
    watch([searchQuery, filterError, filterWarn, panels], () => {
      let total = 0;
      const filtered = [];
      
      for (const panel of panels) {
        // 如果有搜索条件或过滤，显示匹配计数
        if (searchQuery.value || filterError.value || filterWarn.value) {
          total += panel.matchCount || 0;
        }
        
        // 只显示有匹配的面板（如果有搜索条件）
        if (searchQuery.value || filterError.value || filterWarn.value) {
          if ((panel.matchCount || 0) > 0) {
            filtered.push(panel);
          }
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
    
    // 当搜索或过滤条件改变时，重新渲染
    watch([searchQuery, filterError, filterWarn], () => {
      fetchLogs();
    });

    onMounted(() => {
      fetchLogs();
      start();
      // 移除 computeVisibleRows，避免未定义导致错误；如需在窗口变化时刷新，可仅调用 fetchLogs。
      window.addEventListener('resize', () => {
        fetchLogs();
      });
    });

    return { 
      interval, 
      maxLines, 
      panels, 
      getDisplayName,
      searchQuery,
      filterError,
      filterWarn,
      paused,
      totalMatches,
      filteredPanels,
      togglePause,
      copyLogContent
    };
  }
}).mount('#app');
