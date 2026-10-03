/* View layer for the fictional Price Terrain concept. No external API calls. */
(function () {
  'use strict';
  const M = window.PriceTerrain, $ = id => document.getElementById(id);
  const money = n => '£' + n.toFixed(2);
  const percent = n => (n >= 0 ? '+' : '−') + Math.abs(n).toFixed(1) + '%';
  const color = { mint: '#62ebc6', violet: '#c0a1ff', text: '#d1e1e1', muted: '#9aafb9' };
  const state = { selected: M.products.find(p => p.brand === 'Aurum' && p.cocoa === 70 && p.grams === 80 && p.sugar === 10),
    mode: 'terrain', xKey: 'cocoa', yKey: 'grams', camera: { eye: { x: 1.65, y: 1.8, z: 1.0 }, center: { x: 0, y: 0, z: -0.12 }, up: { x: 0, y: 0, z: 1 } } };
  state.proposedPack = Math.round(state.selected.currentPack * 1.1 * 100) / 100;
  let initialized = false, rendering = false, pending = false, chartFailed = false, cameraAnimation = 0;
  const scene = $('scene');
  function shownProducts() { return state.mode === 'terrain' ? M.slicePeers(state.selected, state.xKey, state.yKey) : M.products; }
  function label(key) { const d = M.dimensions[key]; return d.label + ' / ' + d.unit; }
  function coordinates(p, price) {
    return state.mode === 'terrain' ? [p[state.xKey], p[state.yKey], price] : [M.benchmark(p), p[state.yKey], price];
  }
  function lines(points, line, name) {
    return { type: 'scatter3d', mode: 'lines', x: points.map(p => p[0]), y: points.map(p => p[1]), z: points.map(p => p[2]),
      line, name, hoverinfo: 'skip', showlegend: false };
  }
  function marker(p, value, name, symbol, size, ink) {
    const [x, y, z] = coordinates(p, value);
    return { type: 'scatter3d', mode: 'markers', x: [x], y: [y], z: [z],
      name, customdata: [p.id], marker: { color: ink, size, symbol, line: { color: ink, width: 2 } },
      hovertemplate: `${name}<br>${p.name}<br>£%{z:.2f} / 100 g<extra></extra>`, showlegend: false };
  }
  function buildScene() {
    const p = state.selected, data = [], peers = shownProducts(), metric = M.metrics(p, state.proposedPack);
    const fits = M.products.map(M.benchmark);
    const fitMin = Math.floor(Math.min(...fits) * 2) / 2 - 0.2;
    const fitMax = Math.ceil(Math.max(...fits) * 2) / 2 + 0.2;
    const xs = state.mode === 'terrain' ? M.range(state.xKey) : Array.from({ length: 27 }, (_, i) => fitMin + (fitMax - fitMin) * i / 26);
    const ys = M.range(state.yKey);
    const zs = ys.map(y => xs.map(x => state.mode === 'terrain' ? M.sliceValue(p, state.xKey, state.yKey, x, y) : x));
    data.push({ type: 'surface', x: xs, y: ys, z: zs, name: state.mode === 'terrain' ? 'Illustrative conditional benchmark' : 'Agreement plane: observed = predicted',
      colorscale: [[0, '#123644'], [0.45, '#236b72'], [0.75, '#3b9d89'], [1, '#94d5a5']], showscale: false,
      opacity: 0.73, hovertemplate: 'Surface height: £%{z:.2f} / 100 g<extra></extra>',
      lighting: { ambient: 0.76, diffuse: 0.68, roughness: 0.85, specular: 0.15 },
      contours: { z: { show: true, usecolormap: false, color: '#75b9ad', width: 1, project: { z: true }, highlight: false } } });
    const curve = xs.map(x => [x, p[state.yKey], state.mode === 'terrain' ? M.sliceValue(p, state.xKey, state.yKey, x, p[state.yKey]) : x]);
    data.push(lines(curve, { color: color.mint, width: 7 }, 'Selected-product curve'));
    const stems = [];
    peers.forEach(q => {
      stems.push(coordinates(q, M.benchmark(q)), coordinates(q, M.unitPrice(q)), [null, null, null]);
    });
    data.push(lines(stems, { color: '#7594a3', width: 2 }, 'Observed gaps'));
    const anchors = peers.map(q => coordinates(q, M.benchmark(q)));
    data.push({ type: 'scatter3d', mode: 'markers', x: anchors.map(v => v[0]), y: anchors.map(v => v[1]), z: anchors.map(v => v[2]),
      customdata: peers.map(q => q.id), marker: { color: '#b3d4cf', size: 3, symbol: 'circle-open', line: { width: 1 } },
      text: peers.map(q => q.name), hovertemplate: '%{text}<br>Benchmark £%{z:.2f} / 100 g<extra></extra>', showlegend: false });
    const actuals = peers.map(q => coordinates(q, M.unitPrice(q)));
    data.push({ type: 'scatter3d', mode: 'markers', x: actuals.map(v => v[0]), y: actuals.map(v => v[1]), z: actuals.map(v => v[2]),
      customdata: peers.map(q => q.id), marker: { color: '#eef6f3', size: state.mode === 'terrain' ? 4.5 : 3.5, opacity: 0.85 },
      text: peers.map(q => q.name + ' · sugar ' + q.sugar + ' g / 100 g'), hovertemplate: '%{text}<br>Current £%{z:.2f} / 100 g<extra></extra>', showlegend: false });
    data.push(lines([coordinates(p, metric.fit), coordinates(p, metric.proposed)], { color: color.violet, width: 6, dash: 'dash' }, 'Proposed gap'));
    data.push(marker(p, metric.fit, 'Fixed illustrative benchmark', 'circle-open', 8, color.mint));
    data.push(marker(p, metric.current, 'Selected current price', 'circle', 6.5, color.text));
    data.push(marker(p, metric.proposed, 'Proposed price', 'diamond', 8, color.violet));
    const allHeights = [...zs.flat(), ...peers.map(q => M.unitPrice(q)), metric.proposed];
    const zMax = Math.ceil(Math.max(...allHeights) * 1.12 * 2) / 2;
    const axis = title => ({ title: { text: title, font: { size: 10, color: '#bdd0d4' } }, showbackground: true,
      backgroundcolor: '#10202b', gridcolor: '#29434d', linecolor: '#426069', zerolinecolor: '#426069',
      tickfont: { size: 9, color: '#9db6bd' }, showspikes: false, nticks: 5 });
    const layout = {
      paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: { family: '-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif', color: color.text },
      margin: { l: 0, r: 0, t: 8, b: 2 }, showlegend: false,
      uirevision: 'keep-camera-' + state.mode,
      scene: { camera: state.camera, dragmode: 'orbit', aspectmode: 'manual', aspectratio: { x: 1.45, y: 1.1, z: 0.78 },
        xaxis: { ...axis(state.mode === 'terrain' ? label(state.xKey) : 'Full-trait benchmark / £ per 100 g'), range: [xs[0], xs[xs.length - 1]] },
        yaxis: { ...axis(label(state.yKey)), range: [ys[0], ys[ys.length - 1]] },
        zaxis: { ...axis('Price / £ per 100 g'), range: [0, zMax], tickprefix: '£' },
        annotations: [{ x: coordinates(p, metric.proposed)[0], y: coordinates(p, metric.proposed)[1], z: metric.proposed,
          text: `${p.id} · proposal ${money(metric.proposed)}`, showarrow: true, arrowcolor: color.violet,
          arrowwidth: 1, ax: 35, ay: -26, bgcolor: '#211e34', bordercolor: '#655382', borderpad: 5, font: { size: 10, color: '#e0ccff' } }] }
    };
    return { data, layout };
  }
  async function renderScene() {
    if (chartFailed) return;
    if (!window.Plotly) { chartFailed = true; $('chart-error').hidden = false; return; }
    if (rendering) { pending = true; return; }
    rendering = true;
    try {
      const { data, layout } = buildScene();
      if (!initialized) {
        await Plotly.newPlot(scene, data, layout, { responsive: true, displaylogo: false, displayModeBar: false, scrollZoom: true });
        initialized = true;
        scene.on('plotly_click', event => {
          const id = event.points && event.points[0] && event.points[0].customdata;
          if (typeof id === 'string') selectProduct(id);
        });
        scene.on('plotly_relayout', event => { if (event['scene.camera']) state.camera = event['scene.camera']; });
        scene.on('plotly_webglcontextlost', () => { chartFailed = true; $('chart-error').hidden = false; });
      } else await Plotly.react(scene, data, layout);
    } catch (error) {
      chartFailed = true; $('chart-error').hidden = false;
      console.error('Price Terrain scene failed:', error);
    } finally {
      rendering = false;
      if (pending) { pending = false; renderScene(); }
    }
  }
  function sectionChart() {
    const p = state.selected, m = M.metrics(p, state.proposedPack), svg = $('section-chart');
    const ns = 'http://www.w3.org/2000/svg';
    svg.replaceChildren();
    const add = (tag, attrs, text) => { const n = document.createElementNS(ns, tag); Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v)); if (text !== undefined) n.textContent = text; svg.appendChild(n); return n; };
    const fitValues = M.products.map(M.benchmark);
    const xs = state.mode === 'terrain' ? M.range(state.xKey, 61) : Array.from({ length: 61 }, (_, i) => Math.min(...fitValues) + (Math.max(...fitValues) - Math.min(...fitValues)) * i / 60);
    const values = xs.map(x => state.mode === 'terrain' ? M.sliceValue(p, state.xKey, state.yKey, x, p[state.yKey]) : x);
    const min = Math.max(0, Math.min(...values, m.current, m.proposed) * 0.8), max = Math.max(...values, m.current, m.proposed) * 1.13;
    const sx = v => 48 + (v - xs[0]) / (xs[xs.length - 1] - xs[0]) * 512;
    const sy = v => 110 - (v - min) / (max - min) * 92;
    [min, (min + max) / 2, max].forEach(v => { add('line', { x1: 48, x2: 562, y1: sy(v), y2: sy(v), stroke: '#29414b' }); add('text', { x: 40, y: sy(v) + 3, fill: color.muted, 'font-size': 9, 'text-anchor': 'end' }, money(v)); });
    add('path', { d: values.map((v, i) => `${i ? 'L' : 'M'}${sx(xs[i])},${sy(v)}`).join(' '), fill: 'none', stroke: color.mint, 'stroke-width': 2.5 });
    const x = sx(state.mode === 'terrain' ? p[state.xKey] : m.fit), y = sy(m.proposed);
    add('line', { x1: x, x2: x, y1: sy(m.fit), y2: y, stroke: color.violet, 'stroke-width': 2, 'stroke-dasharray': '3 3' });
    add('circle', { cx: x, cy: sy(m.fit), r: 4.5, fill: '#0d1720', stroke: color.mint, 'stroke-width': 2 });
    add('circle', { cx: x, cy: sy(m.current), r: 4, fill: color.text });
    add('path', { d: `M${x},${y - 6}l6,6l-6,6l-6,-6Z`, fill: color.violet });
    add('text', { x: 48, y: 130, fill: color.muted, 'font-size': 9 }, state.mode === 'terrain' ? xs[0] + ' ' + M.dimensions[state.xKey].unit : money(xs[0]));
    add('text', { x: 562, y: 130, fill: color.muted, 'font-size': 9, 'text-anchor': 'end' }, state.mode === 'terrain' ? xs[xs.length - 1] + ' ' + M.dimensions[state.xKey].unit : money(xs[xs.length - 1]));
    add('text', { x: 300, y: 144, fill: color.muted, 'font-size': 9, 'text-anchor': 'middle' }, state.mode === 'terrain' ? label(state.xKey) : 'Full-trait benchmark / £ per 100 g');
  }
  function updateCopy() {
    const p = state.selected, m = M.metrics(p, state.proposedPack), peers = shownProducts(), terrain = state.mode === 'terrain';
    $('terrain-mode').setAttribute('aria-pressed', String(terrain)); $('fit-mode').setAttribute('aria-pressed', String(!terrain));
    $('x-control').hidden = !terrain;
    $('axis-note').textContent = terrain ? 'Height = price / £ per 100 g' : 'Horizontal = full-trait estimate · height = observed price';
    $('scene-kicker').textContent = terrain ? '01 / CONDITIONAL PRICE LANDSCAPE' : '02 / FULL-TRAIT MODEL COMPARISON';
    $('landscape-title').textContent = terrain ? 'A surface for the selected context' : 'Every trait, one benchmark per product';
    $('surface-label').textContent = terrain ? 'Conditional benchmark surface' : 'Agreement plane: observed = predicted';
    $('curve-label').textContent = terrain ? 'Selected-context fit curve' : 'Agreement line at selected depth';
    $('scene-count').textContent = terrain ? `${peers.length} products matching the fixed context` : `${peers.length} products · individual full-trait estimates`;
    const fixedKey = Object.keys(M.dimensions).find(k => k !== state.xKey && k !== state.yKey);
    $('context-note').textContent = terrain
      ? `Held fixed: ${label(fixedKey)} = ${p[fixedKey]}; ${p.brand}, organic ${p.organic ? 'yes' : 'no'}, nuts ${p.nuts ? 'yes' : 'no'}, single origin ${p.origin ? 'yes' : 'no'}. Only matching products are shown. Surface = hand-authored function, not a fitted model.`
      : 'Each open marker uses that product’s full trait vector. The plane is the equality reference z = x, not a second fitted model. The depth trait separates products; it does not replace other model inputs.';
    $('section-title').textContent = terrain ? 'The fitting curve through this product' : 'The selected product against agreement';
    $('section-note').textContent = terrain ? `${label(state.yKey)} = ${p[state.yKey]}. The mint curve holds all other traits fixed; the vertical gap shows the proposal’s difference.` : 'The mint line means observed price equals the full-trait benchmark. The vertical gap is the proposal’s difference.';
    $('product-picker').value = p.id; $('product-title').textContent = p.name;
    $('product-id').textContent = `${p.id} · fictional product · sugar ${p.sugar} g / 100 g`;
    $('trait-tags').replaceChildren();
    [p.organic ? 'Organic: yes' : 'Organic: no', p.nuts ? 'Nuts: yes' : 'Nuts: no', p.origin ? 'Single origin: yes' : 'Single origin: no'].forEach(t => { const n = document.createElement('span'); n.textContent = t; $('trait-tags').appendChild(n); });
    $('current-pack').textContent = money(p.currentPack); $('proposed-pack').textContent = money(state.proposedPack);
    $('price-input').value = state.proposedPack.toFixed(2); $('price-slider').value = state.proposedPack;
    $('benchmark-value').textContent = money(m.fit); $('proposed-unit').textContent = money(m.proposed);
    $('price-gap').textContent = percent(m.gapPercent); $('price-change').textContent = percent(m.changePercent);
    $('decision-readout').textContent = `Your proposal sits ${money(Math.abs(m.gap))} / 100 g ${m.gap >= 0 ? 'above' : 'below'} this illustrative benchmark. This gap does not establish whether shoppers will accept the price.`;
    $('matrix-count').textContent = terrain ? `${peers.length} matching products / 108 total · fixed context stated above` : '108 products · all trait contexts';
  }
  function renderTable() {
    const body = $('product-rows'); body.replaceChildren();
    const peers = [...shownProducts()].sort((a, b) => (a.id === state.selected.id ? -1 : b.id === state.selected.id ? 1 : a.id.localeCompare(b.id)));
    peers.forEach(p => {
      const row = document.createElement('tr'); if (p.id === state.selected.id) row.className = 'selected';
      const cell = document.createElement('td'), button = document.createElement('button');
      button.textContent = (p.id === state.selected.id ? '● ' : '') + p.name;
      button.setAttribute('aria-label', `Select ${p.name}, sugar ${p.sugar} grams per 100 grams`);
      button.addEventListener('click', () => selectProduct(p.id)); cell.appendChild(button); row.appendChild(cell);
      const gap = (M.unitPrice(p) / M.benchmark(p) - 1) * 100;
      const values = [p.cocoa + '%', p.grams + ' g', p.sugar + ' g', p.organic ? 'Yes' : 'No', p.nuts ? 'Yes' : 'No', p.origin ? 'Yes' : 'No', money(M.unitPrice(p)), money(M.benchmark(p)), percent(gap)];
      values.forEach((value, i) => { const td = document.createElement('td'); td.textContent = value; if (i === values.length - 1) td.className = gap >= 0 ? 'gap-positive' : 'gap-negative'; row.appendChild(td); });
      body.appendChild(row);
    });
  }
  function render(refreshTable = false) { updateCopy(); sectionChart(); if (refreshTable) renderTable(); renderScene(); }
  function selectProduct(id) { const p = M.products.find(q => q.id === id); if (!p) return; state.selected = p; state.proposedPack = p.currentPack; render(true); }
  function updatePrice(raw) { const price = Number(raw); if (raw === '' || !Number.isFinite(price)) { updateCopy(); return; } state.proposedPack = Math.round(Math.min(12, Math.max(0.5, price)) * 100) / 100; render(); }
  function changeAxis(key, value) {
    state[key] = value;
    if (state.xKey === state.yKey) { const other = key === 'xKey' ? 'yKey' : 'xKey'; state[other] = Object.keys(M.dimensions).find(k => k !== value); }
    $('x-axis').value = state.xKey; $('y-axis').value = state.yKey; render(true);
  }
  function cameraTo(eye) {
    if (!initialized || chartFailed) return;
    cancelAnimationFrame(cameraAnimation);
    const origin = { ...(state.camera.eye || { x: 1.65, y: 1.8, z: 1 }) }, start = performance.now();
    const duration = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 650;
    const step = time => {
      const t = duration ? Math.min(1, (time - start) / duration) : 1, ease = t * t * (3 - 2 * t);
      state.camera = { ...state.camera, eye: { x: origin.x + (eye.x - origin.x) * ease, y: origin.y + (eye.y - origin.y) * ease, z: origin.z + (eye.z - origin.z) * ease } };
      Plotly.relayout(scene, { 'scene.camera': state.camera });
      if (t < 1) cameraAnimation = requestAnimationFrame(step);
    };
    cameraAnimation = requestAnimationFrame(step);
  }
  M.products.forEach(p => { const option = document.createElement('option'); option.value = p.id; option.textContent = `${p.id} · ${p.name} · sugar ${p.sugar} g`; $('product-picker').appendChild(option); });
  $('product-picker').addEventListener('change', e => selectProduct(e.target.value));
  $('x-axis').addEventListener('change', e => changeAxis('xKey', e.target.value));
  $('y-axis').addEventListener('change', e => changeAxis('yKey', e.target.value));
  $('terrain-mode').addEventListener('click', () => { state.mode = 'terrain'; render(true); });
  $('fit-mode').addEventListener('click', () => { state.mode = 'fit'; render(true); });
  $('price-input').addEventListener('change', e => updatePrice(e.target.value));
  $('price-slider').addEventListener('input', e => updatePrice(e.target.value));
  $('reset-proposal').addEventListener('click', () => { state.proposedPack = state.selected.currentPack; render(); });
  $('orbit-view').addEventListener('click', () => cameraTo({ x: 1.65, y: 1.8, z: 1.0 }));
  $('top-view').addEventListener('click', () => cameraTo({ x: 0.05, y: 0.05, z: 2.7 }));
  $('side-view').addEventListener('click', () => cameraTo({ x: 0.05, y: -2.7, z: 0.1 }));
  render(true);
})();
