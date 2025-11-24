(() => {
  const cfg = (window.__CD_BITMAP_CONFIG__ || {});
  const FRAME_URL = cfg.frameEndpoint || '/api/bitmap/frame';
  const DL_ALL = cfg.downloadAll || '/api/download/bitmap/all';
  const DL_ONE = cfg.downloadSingle || '/api/download/bitmap?type=';

  const c = document.getElementById('heatmap');
  const ctx = c.getContext('2d', { alpha: false });
  const seg = document.getElementById('seg-type');
  const labelType = document.getElementById('label-type');
  const metaSize = document.getElementById('meta-size');
  const metaLayout = document.getElementById('meta-layout');
  const metaMtime = document.getElementById('meta-mtime');
  const selInterval = document.getElementById('sel-interval');
  const selColors = document.getElementById('sel-colors');
  const chkNew = document.getElementById('chk-new');
  const chkDiff = document.getElementById('chk-diff');
  const chkStill = document.getElementById('chk-still');
  const btnDlAll = document.getElementById('btn-dl-all');
  const btnDlSel = document.getElementById('btn-dl-sel');

  let activeType = 'sum'; // 'sum' | 'cumulative' | 'bool'
  let pollMs = parseInt(selInterval.value, 10) || 1000;
  let timer = null;

  // 本地状态（TypedArray 或普通数组）
  let mapSize = 0;
  let layout = { rows: 0, cols: 0 };
  let last = { sum: [], cumulative: [], bool: [] };
  let stillCounter = [];  // 连续未变化计数
  const STILL_THRESHOLD = 60; // 连续60轮未变化视为“长期静默”

  // 动画叠加项：记录一个 index -> untilTs 的寿命
  const glowNew = new Map();   // bool 0->1
  const glowDiff = new Map();  // 任意通道变化
  const GLOW_MS = 1200;

  // 调色盘
  const palettes = {
    inferno: infernoPalette(),
    viridis: viridisPalette(),
    magma: magmaPalette(),
    gray: grayPalette(),
  };

  function setActiveType(t) {
    activeType = t;
    labelType.textContent = t;
    Array.from(seg.querySelectorAll('button')).forEach(b => {
      b.classList.toggle('active', b.dataset.type === t);
    });
    draw();
  }

  seg.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    const t = b.dataset.type;
    if (t) setActiveType(t);
  });

  selInterval.addEventListener('change', () => {
    pollMs = parseInt(selInterval.value, 10) || 1000;
    start();
  });

  selColors.addEventListener('change', draw);
  chkNew.addEventListener('change', draw);
  chkDiff.addEventListener('change', draw);
  chkStill.addEventListener('change', draw);
  btnDlAll.addEventListener('click', () => { window.location.href = DL_ALL; });
  btnDlSel.addEventListener('click', () => { window.location.href = DL_ONE + activeType; });

  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  function resizeCanvas() {
    // 保持像素基准绘制：根据容器宽度设置画布尺寸（高度按行列比）
    const wrapWidth = c.parentElement.clientWidth - 2;
    const ratio = (layout.rows && layout.cols) ? (layout.rows / layout.cols) : 1.0;
    const targetW = Math.max(256, Math.min(1024, wrapWidth));
    const targetH = Math.max(256, Math.round(targetW * ratio));
    c.width = targetW;
    c.height = targetH;
    draw();
  }

  async function fetchFrame() {
    try {
      const r = await fetch(FRAME_URL + '?t=' + Date.now(), { cache: 'no-store' });
      if (!r.ok) return;
      const data = await r.json();
      if (!data || !data.ok) return;

    mapSize = data.mapSize || 0;
    layout = data.layout || { rows: 0, cols: 0 };
    metaSize.textContent = mapSize;
    metaLayout.textContent = `${layout.rows} x ${layout.cols}`;
    // 以当前通道 mtime 为主展示（能基本反映新鲜度）
    const mt = ((data.files || {})[activeType] || {}).mtime || '';
    metaMtime.textContent = mt ? new Date(mt).toLocaleString() : '—';

    // 对齐数组长度
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

    draw();
    } catch (err) {
      // 静默处理错误，继续轮询
      console.debug('bitmap fetch error:', err);
    }
  }

  function paletteSample(pal, t) {
    // pal: Uint8ClampedArray of [r,g,b,...] length = 256*3
    const x = Math.max(0, Math.min(255, Math.round(t * 255)));
    return [pal[x*3], pal[x*3+1], pal[x*3+2]];
  }

  function draw() {
    if (!mapSize || !layout.rows || !layout.cols) return;
    const pal = palettes[selColors.value] || palettes.inferno;

    // 底图渲染
    const w = c.width, h = c.height;
    ctx.fillStyle = '#0b1220';
    ctx.fillRect(0, 0, w, h);

    // 找到当前通道与映射
    const arr = last[activeType] || [];
    const n = arr.length;
    if (n === 0) return;

    // 统计最大值用于归一化（sum/cumulative）。bool 用 0/1
    let vmax = 1;
    if (activeType !== 'bool') {
      // 使用稳健分位抑制极端值
      const sorted = arr.slice().sort((a,b)=>a-b);
      const hi = sorted[Math.max(0, Math.min(n-1, Math.floor(n * 0.995)))];
      vmax = Math.max(1, hi | 0);
    } else {
      vmax = 1;
    }

    const cellW = w / layout.cols;
    const cellH = h / layout.rows;

    // 预计算 glow 衰减并清理过期
    const now = performance.now();
    for (const [k, until] of glowNew) if (until < now) glowNew.delete(k);
    for (const [k, until] of glowDiff) if (until < now) glowDiff.delete(k);

    // 绘制网格（批量填充）
    ctx.save();
    ctx.translate(0.5, 0.5); // 轻微对齐像素
    for (let r = 0, idx = 0; r < layout.rows; r++) {
      for (let ccol = 0; ccol < layout.cols; ccol++, idx++) {
        if (idx >= n) break;
        const v = arr[idx] | 0;
        let t = 0;
        if (activeType === 'bool') {
          t = v > 0 ? 1 : 0;
        } else {
          // 对数压缩
          t = v > 0 ? (Math.log(1 + v) / Math.log(1 + vmax)) : 0;
        }
        const [r8, g8, b8] = paletteSample(pal, t);
        // 长期静默去饱和处理（叠加一层暗化）
        let alpha = 1.0;
        if (chkStill.checked && stillCounter[idx] >= STILL_THRESHOLD) {
          alpha = 0.55;
        }
        ctx.fillStyle = `rgba(${r8},${g8},${b8},${alpha})`;
        ctx.fillRect(Math.floor(ccol * cellW), Math.floor(r * cellH), Math.ceil(cellW), Math.ceil(cellH));
      }
    }
    ctx.restore();

    // 叠加层：新增与差异的“发光”
    if (chkNew.checked || chkDiff.checked) {
      ctx.save();
      // 使用叠加模式更显著
      ctx.globalCompositeOperation = 'lighter';
      const drawGlowFor = (map, color) => {
        ctx.fillStyle = color;
        for (const [idx, until] of map) {
          const life = Math.max(0, until - now) / GLOW_MS; // 0..1
          if (life <= 0) continue;
          const r = Math.floor(idx / layout.cols);
          const ccol = idx % layout.cols;
          const x = Math.floor(ccol * cellW);
          const y = Math.floor(r * cellH);
          const expand = 0.15 + 0.85 * life; // 发光扩散
          const w2 = Math.ceil(cellW * expand);
          const h2 = Math.ceil(cellH * expand);
          ctx.globalAlpha = 0.25 + 0.55 * life;
          ctx.fillRect(x - Math.floor((w2-cellW)/2), y - Math.floor((h2-cellH)/2), w2, h2);
        }
      };
      if (chkNew.checked) drawGlowFor(glowNew, 'rgba(16,185,129,0.8)'); // 绿色
      if (chkDiff.checked) drawGlowFor(glowDiff, 'rgba(59,130,246,0.8)'); // 蓝色
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
    // stops: [idx, 0xRRGGBB]
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
    // 左侧填充
    for(let x=0;x<pts[0][0];x++){
      const c=pts[0][1]; out[x*3]=(c>>16)&255; out[x*3+1]=(c>>8)&255; out[x*3+2]=c&255;
    }
    // 右侧填充
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




