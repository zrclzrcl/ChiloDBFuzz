(() => {
  const cfg = (window.__CD_BITMAP_CONFIG__ || {});
  const FRAME_URL = cfg.frameEndpoint || '/api/bitmap/frame';
  const DL_ALL = cfg.downloadAll || '/api/download/bitmap/all';
  const DL_ONE = cfg.downloadSingle || '/api/download/bitmap?type=';

  // 获取单个 canvas 和容器
  const card = document.querySelector('.grid-card[data-type]');
  if (!card) {
    console.warn('bitmap.js: no grid card found');
    return;
  }

  const canvas = card.querySelector('.heatmap-canvas');
  const ctx = canvas.getContext('2d', { alpha: false });
  const labelType = card.querySelector('.label-type');

  const segType = document.getElementById('seg-type');
  const selInterval = document.getElementById('sel-interval');
  const selColors = document.getElementById('sel-colors');
  const chkNew = document.getElementById('chk-new');
  const chkDiff = document.getElementById('chk-diff');
  const chkStill = document.getElementById('chk-still');
  const btnDlSel = document.getElementById('btn-dl-sel');
  const btnDlAll = document.getElementById('btn-dl-all');
  
  if (!segType || !selInterval || !selColors || !chkNew || !chkDiff || !chkStill || !btnDlSel || !btnDlAll) {
    console.warn('bitmap.js: required DOM elements not found');
    return;
  }

  let currentType = 'sum';
  let pollMs = parseInt(selInterval.value, 10) || 1000;
  let timer = null;

  // 状态
  let mapSize = 0;
  let layout = { rows: 0, cols: 0 };
  let last = { sum: [], cumulative: [], bool: [] };
  let stillCounter = [];

  // 动画叠加项
  const glowNew = new Map();
  const glowDiff = new Map();
  const GLOW_MS = 1200;
  const STILL_THRESHOLD = 60;

  // 调色盘
  const palettes = {
    inferno: infernoPalette(),
    viridis: viridisPalette(),
    magma: magmaPalette(),
    gray: grayPalette(),
  };

  // 类型切换
  segType.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', () => {
      const type = btn.dataset.type;
      if (type === currentType) return;
      currentType = type;
      segType.querySelectorAll('button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      card.dataset.type = type;
      if (labelType) {
        labelType.textContent = type === 'sum' ? 'Sum' : type === 'cumulative' ? 'Cumulative' : 'Bool';
      }
      resizeCanvas();
      drawCanvas();
    });
  });

  selInterval.addEventListener('change', () => {
    pollMs = parseInt(selInterval.value, 10) || 1000;
    start();
  });

  selColors.addEventListener('change', () => drawCanvas());
  chkNew.addEventListener('change', () => drawCanvas());
  chkDiff.addEventListener('change', () => drawCanvas());
  chkStill.addEventListener('change', () => drawCanvas());
  
  btnDlSel.addEventListener('click', () => {
    window.location.href = DL_ONE + currentType;
  });
  btnDlAll.addEventListener('click', () => {
    window.location.href = DL_ALL;
  });

  // Resize 监听
  let resizeTimer = null;
  window.addEventListener('resize', () => {
    if (resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => resizeCanvas(), 100);
  });

  function resizeCanvas() {
    const container = card;
    const containerRect = container.getBoundingClientRect();
    const headHeight = container.querySelector('.grid-head')?.offsetHeight || 0;
    
    // 获取可用空间（减去头部和 padding）
    const availableWidth = containerRect.width - 2; // 减去边框
    const availableHeight = containerRect.height - headHeight - 2;
    
    if (availableWidth <= 0 || availableHeight <= 0) {
      canvas.width = 512;
      canvas.height = 512;
      return;
    }

    // 根据布局比例计算最佳尺寸
    const ratio = (layout.rows && layout.cols) ? (layout.rows / layout.cols) : 1.0;
    
    let targetW = availableWidth;
    let targetH = Math.round(targetW * ratio);
    
    // 如果高度超出，按高度调整
    if (targetH > availableHeight) {
      targetH = availableHeight;
      targetW = Math.round(targetH / ratio);
    }
    
    // 确保最小尺寸
    targetW = Math.max(256, targetW);
    targetH = Math.max(256, targetH);
    
    canvas.width = targetW;
    canvas.height = targetH;
    drawCanvas();
  }

  async function fetchFrame() {
    try {
      const r = await fetch(FRAME_URL + '?t=' + Date.now(), { cache: 'no-store' });
      if (!r.ok) {
        mapSize = 0;
        layout = { rows: 0, cols: 0 };
        updateMeta();
        drawCanvas();
        return;
      }
      let data;
      try {
        data = await r.json();
      } catch (e) {
        console.debug('bitmap fetch: invalid JSON response', e);
        mapSize = 0;
        layout = { rows: 0, cols: 0 };
        drawCanvas();
        return;
      }
      if (!data || !data.ok) {
        mapSize = data?.mapSize || 0;
        layout = data?.layout || { rows: 0, cols: 0 };
        updateMeta();
        drawCanvas();
        return;
      }

      mapSize = data.mapSize || 0;
      layout = data.layout || { rows: 0, cols: 0 };
      updateMeta();

      const sum = (data.channels && Array.isArray(data.channels.sum)) ? data.channels.sum : [];
      const cumulative = (data.channels && Array.isArray(data.channels.cumulative)) ? data.channels.cumulative : [];
      const bool = (data.channels && Array.isArray(data.channels.bool)) ? data.channels.bool : [];
      const n = Math.max(sum.length, cumulative.length, bool.length);

      if (stillCounter.length !== n) {
        stillCounter = new Array(n).fill(0);
      }

      // 变化检测
      const now = performance.now();
      for (let i = 0; i < n; i++) {
        const s0 = last.sum[i] | 0; const s1 = sum[i] | 0;
        const c0 = last.cumulative[i] | 0; const c1 = cumulative[i] | 0;
        const b0 = last.bool[i] | 0; const b1 = bool[i] | 0;

        const changed = (s0 !== s1) || (c0 !== c1) || (b0 !== b1);
        if (changed) {
          stillCounter[i] = 0;
          if (chkDiff.checked) glowDiff.set(i, now + GLOW_MS);
          if (chkNew.checked && b0 === 0 && b1 > 0) glowNew.set(i, now + GLOW_MS);
        } else {
          stillCounter[i] = Math.min(1e9, (stillCounter[i] | 0) + 1);
        }
      }

      last.sum = sum;
      last.cumulative = cumulative;
      last.bool = bool;

      // 如果布局变化，重新调整 canvas 大小
      resizeCanvas();
      drawCanvas();
    } catch (err) {
      console.debug('bitmap fetch error:', err);
    }
  }

  function updateMeta() {
    const metaSize = card.querySelector('.meta-size');
    const metaLayout = card.querySelector('.meta-layout');
    if (metaSize) metaSize.textContent = mapSize || '—';
    if (metaLayout) {
      const l = layout.rows && layout.cols ? `${layout.rows} x ${layout.cols}` : '—';
      metaLayout.textContent = l;
    }
  }

  function paletteSample(pal, t) {
    const x = Math.max(0, Math.min(255, Math.round(t * 255)));
    return [pal[x*3], pal[x*3+1], pal[x*3+2]];
  }

  function drawCanvas() {
    const w = canvas.width, h = canvas.height;
    
    ctx.fillStyle = '#0b1220';
    ctx.fillRect(0, 0, w, h);
    
    if (!mapSize || !layout.rows || !layout.cols) {
      ctx.fillStyle = '#6b7280';
      ctx.font = '14px ui-sans-serif, system-ui';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('暂无数据', w / 2, h / 2);
      return;
    }
    
    const pal = palettes[selColors.value] || palettes.inferno;
    const arr = last[currentType] || [];
    const n = arr.length;
    if (n === 0) return;

    let vmax = 1;
    if (currentType !== 'bool') {
      const sorted = arr.slice().sort((a,b)=>a-b);
      const hi = sorted[Math.max(0, Math.min(n-1, Math.floor(n * 0.995)))];
      vmax = Math.max(1, hi | 0);
    } else {
      vmax = 1;
    }

    const cellW = w / layout.cols;
    const cellH = h / layout.rows;

    const now = performance.now();
    for (const [k, until] of glowNew) if (until < now) glowNew.delete(k);
    for (const [k, until] of glowDiff) if (until < now) glowDiff.delete(k);

    ctx.save();
    ctx.translate(0.5, 0.5);
    for (let r = 0, idx = 0; r < layout.rows; r++) {
      for (let ccol = 0; ccol < layout.cols; ccol++, idx++) {
        if (idx >= n) break;
        const v = arr[idx] | 0;
        let t = 0;
        if (currentType === 'bool') {
          t = v > 0 ? 1 : 0;
        } else {
          t = v > 0 ? (Math.log(1 + v) / Math.log(1 + vmax)) : 0;
        }
        const [r8, g8, b8] = paletteSample(pal, t);
        let alpha = 1.0;
        if (chkStill.checked && stillCounter[idx] >= STILL_THRESHOLD) {
          alpha = 0.55;
        }
        ctx.fillStyle = `rgba(${r8},${g8},${b8},${alpha})`;
        ctx.fillRect(Math.floor(ccol * cellW), Math.floor(r * cellH), Math.ceil(cellW), Math.ceil(cellH));
      }
    }
    ctx.restore();

    // 叠加层：新增与差异的"发光"
    if (chkNew.checked || chkDiff.checked) {
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      const drawGlowFor = (map, color) => {
        ctx.fillStyle = color;
        for (const [idx, until] of map) {
          const life = Math.max(0, until - now) / GLOW_MS;
          if (life <= 0) continue;
          const r = Math.floor(idx / layout.cols);
          const ccol = idx % layout.cols;
          const x = Math.floor(ccol * cellW);
          const y = Math.floor(r * cellH);
          const expand = 0.15 + 0.85 * life;
          const w2 = Math.ceil(cellW * expand);
          const h2 = Math.ceil(cellH * expand);
          ctx.globalAlpha = 0.25 + 0.55 * life;
          ctx.fillRect(x - Math.floor((w2-cellW)/2), y - Math.floor((h2-cellH)/2), w2, h2);
        }
      };
      if (chkNew.checked) drawGlowFor(glowNew, 'rgba(16,185,129,0.8)');
      if (chkDiff.checked) drawGlowFor(glowDiff, 'rgba(59,130,246,0.8)');
      ctx.restore();
      ctx.globalAlpha = 1;
    }
  }

  function start() {
    stop();
    timer = setInterval(fetchFrame, pollMs);
  }
  function stop() { if (timer) { clearInterval(timer); timer = null; } }

  // 简易内置调色板（256 级）
  function infernoPalette(){ return makeGradient([
    [0,   0x000004],
    [64,  0x1f0c48],
    [128, 0xb53679],
    [192, 0xfc8c3a],
    [255, 0xfcfdbf]
  ]);}
  function viridisPalette(){ return makeGradient([
    [0,   0x440154],
    [64,  0x3b528b],
    [128, 0x21918c],
    [192, 0x5ec962],
    [255, 0xfde725]
  ]);}
  function magmaPalette(){ return makeGradient([
    [0,   0x000004],
    [64,  0x3b0f6f],
    [128, 0xb5367a],
    [192, 0xfb8861],
    [255, 0xfbfbbf]
  ]);}
  function grayPalette(){ return makeGradient([
    [0,   0x000000],
    [255, 0xffffff]
  ]);}
  function makeGradient(stops){
    const out = new Uint8ClampedArray(256*3);
    const pts = stops.slice().sort((a,b)=>a[0]-b[0]);
    for(let i=0;i<pts.length-1;i++){
      const [x0, c0] = pts[i];
      const [x1, c1] = pts[i+1];
      const r0=(c0>>16)&255, g0=(c0>>8)&255, b0=c0&255;
      const r1=(c1>>16)&255, g1=(c1>>8)&255, b1=c1&255;
      const span = Math.max(1, x1 - x0);
      for(let x=x0;x<=x1;x++){
        const t = (x - x0) / span;
        const r = Math.round(r0 + (r1 - r0)*t);
        const g = Math.round(g0 + (g1 - g0)*t);
        const b = Math.round(b0 + (b1 - b0)*t);
        out[x*3]=r; out[x*3+1]=g; out[x*3+2]=b;
      }
    }
    for(let x=0;x<pts[0][0];x++){
      const c=pts[0][1]; out[x*3]=(c>>16)&255; out[x*3+1]=(c>>8)&255; out[x*3+2]=c&255;
    }
    for(let x=pts[pts.length-1][0]+1;x<256;x++){
      const c=pts[pts.length-1][1]; out[x*3]=(c>>16)&255; out[x*3+1]=(c>>8)&255; out[x*3+2]=c&255;
    }
    return out;
  }

  // 启动
  fetchFrame().then(()=>{
    resizeCanvas();
    start();
  }).catch(()=>{
    start();
  });
})();
