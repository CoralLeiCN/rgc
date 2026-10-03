(function () {
  'use strict';
  const M = window.LayeredPrice, $ = id => document.getElementById(id), money = n => '£' + n.toFixed(2);
  const state = { selected: M.products[175], topN: 4, cut: 1, peeledTo: null, density: 3, pointSize: 2,
    camera: { eye: { x: 1.8, y: -1.85, z: 0.95 }, center: { x: 0, y: 0, z: -0.1 }, up: { x: 0, y: 0, z: 1 } } };
  state.proposal = Math.round(M.unitPrice(state.selected) * 1.08 * 100) / 100;
  const scene = $('layer-scene');
  let ready = false, busy = false, pending = false, geometryDirty = true, scheduled = false, failed = false;
  let pointerStart = null, orbitDragged = false;
  let cachedCloudKey = '', cachedClouds = [], cachedSamplesKey = '', cachedSamples;
  function plottedLayers() {
    const layers = M.layers(state.topN), end = state.peeledTo ? layers.findIndex(l => l.key === state.peeledTo) : layers.length - 1;
    return { all: layers, visible: layers.slice(0, Math.max(0, end) + 1) };
  }
  function geometry() {
    const layers = plottedLayers(), key = state.topN + ':' + state.cut + ':' + state.density;
    if (key !== cachedCloudKey) { cachedClouds = M.cloud(layers.all, state.cut, state.density); cachedCloudKey = key; }
    const samplesKey = key + ':' + state.peeledTo;
    if (samplesKey !== cachedSamplesKey) {
      cachedSamples = { x: [], y: [], z: [], customdata: [], colors: [] };
      layers.visible.forEach((layer, index) => {
        const cloud = cachedClouds[index];
        cloud.x.forEach((x, i) => {
          cachedSamples.x.push(x); cachedSamples.y.push(cloud.y[i]); cachedSamples.z.push(cloud.z[i]);
          cachedSamples.customdata.push([...cloud.customdata[i], layer.name]); cachedSamples.colors.push(layer.color);
        });
      });
      cachedSamplesKey = samplesKey;
    }
    // One opaque point batch avoids a transparency/compositing pass for every
    // orbit frame. Trait colors and all product/sample coordinates are retained.
    const samples = cachedSamples;
    const traces = [{ type: 'scatter3d', uid: 'trait-samples', mode: 'markers', x: samples.x, y: samples.y, z: samples.z, customdata: samples.customdata,
      name: 'Trait layers', meta: { role: 'trait-samples' }, showlegend: false,
      marker: { size: state.pointSize, color: samples.colors, opacity: 1, symbol: 'circle', line: { width: 0 } },
      hovertemplate: '%{customdata[0]} · %{customdata[1]}<br>%{customdata[4]}: £%{customdata[2]:.2f} /100 g<br>Display sample at £%{z:.2f}<extra></extra>' }];
    const visible = M.products.filter(p => p.x <= state.cut + 1e-9);
    traces.push({ type: 'scatter3d', uid: 'products', mode: 'markers', x: visible.map(p => p.x), y: visible.map(p => p.y), z: visible.map(p => p.fit),
      customdata: visible.map(p => p.id), text: visible.map(p => p.name), name: 'Full benchmarks', meta: { role: 'products' }, marker: { size: state.pointSize + 0.7, color: '#dffff4', opacity: 1, line: { width: 0 } },
      hovertemplate: '%{text}<br>Full benchmark £%{z:.2f} /100 g<extra></extra>', showlegend: false });
    const p = state.selected, selectedVisible = p.x <= state.cut + 1e-9;
    if (selectedVisible) {
      let height = 0;
      const stack = { x: [], y: [], z: [], colors: [] };
      layers.visible.forEach(layer => {
        const top = height + layer.value(p);
        if (top > height + 1e-10) {
          stack.x.push(p.x, p.x, null); stack.y.push(p.y, p.y, null); stack.z.push(height, top, null);
          stack.colors.push(layer.color, layer.color, layer.color);
        }
        height = top;
      });
      traces.push({ type: 'scatter3d', uid: 'selected-stack', mode: 'lines', x: stack.x, y: stack.y, z: stack.z,
        connectgaps: false, line: { color: stack.colors, width: 4 }, meta: { role: 'selected-layer' }, hoverinfo: 'skip', showlegend: false });
      traces.push({ type: 'scatter3d', uid: 'proposal-gap', mode: 'lines', x: [p.x, p.x], y: [p.y, p.y], z: [p.fit, state.proposal],
        line: { color: '#e0c4ff', width: 6, dash: 'dash' }, hoverinfo: 'skip', showlegend: false });
      const colors = ['#ffffff', '#eff7f6', '#d8baff'];
      traces.push({ type: 'scatter3d', uid: 'selected-prices', mode: 'markers', x: [p.x, p.x, p.x], y: [p.y, p.y, p.y], z: [p.fit, M.unitPrice(p), state.proposal],
        text: ['Full benchmark', 'Actual price', 'Proposal'], customdata: [p.id, p.id, p.id], name: 'Selected product',
        marker: { size: 7, color: colors, symbol: ['circle-open', 'circle', 'diamond'], opacity: 1, line: { width: 2, color: colors } },
        hovertemplate: '%{text}<br>£%{z:.2f} /100 g<extra></extra>', showlegend: false });
    }
    const axis = title => ({ title: { text: title, font: { size: 10, color: '#bfd0da' } }, tickfont: { size: 8, color: '#95acb8' }, showbackground: true, backgroundcolor: '#091620', gridcolor: '#233b48', zerolinecolor: '#385261', showspikes: false });
    return { traces, layout: { margin: { l: 0, r: 0, t: 0, b: 0 }, paper_bgcolor: 'rgba(0,0,0,0)', font: { family: '-apple-system, sans-serif', color: '#dfebea' }, showlegend: false,
      uirevision: 'layer-map', scene: { camera: structuredClone(state.camera), dragmode: 'orbit', aspectmode: 'manual', aspectratio: { x: 1.3, y: 1.3, z: 0.9 },
        xaxis: { ...axis('Explanation-map coordinate 1'), range: [-0.05, 1.05], showticklabels: false }, yaxis: { ...axis('Explanation-map coordinate 2'), range: [-0.05, 1.05], showticklabels: false },
        zaxis: { ...axis('Cumulative price / £ per 100 g'), range: [0, Math.max(6.2, state.proposal * 1.1)], tickprefix: '£' },
        annotations: selectedVisible ? [{ x: p.x, y: p.y, z: state.proposal, text: p.id + ' · ' + money(state.proposal), showarrow: true, arrowcolor: '#d8baff', ax: 35, ay: -30, bgcolor: '#282039', bordercolor: '#7a6295', borderpad: 5, font: { size: 10, color: '#edddff' } }] : [] } } };
  }
  function scheduleScene() {
    if (failed || busy || scheduled || pointerStart || !pending) return;
    scheduled = true;
    requestAnimationFrame(flushScene);
  }
  function renderScene(cameraOnly = false) {
    pending = true; geometryDirty = geometryDirty || !cameraOnly;
    scheduleScene();
  }
  async function flushScene() {
    scheduled = false;
    if (pointerStart) return;
    if (failed) return;
    if (!window.Plotly) { failed = true; $('layer-error').hidden = false; return; }
    const rebuild = geometryDirty || !ready;
    pending = false; geometryDirty = false; busy = true;
    try {
      if (rebuild) {
        const { traces, layout } = geometry();
        if (!ready) {
          // The vendored renderer defaults to 2x in each dimension (4x pixels).
          await Plotly.newPlot(scene, traces, layout, { responsive: true, displaylogo: false, displayModeBar: false, scrollZoom: true, plotGlPixelRatio: 1 }); ready = true;
          scene.on('plotly_click', event => {
            if (orbitDragged) return;
            const data = event.points && event.points[0] && event.points[0].customdata;
            const id = Array.isArray(data) ? data[0] : data;
            if (typeof id === 'string') select(id);
          });
          // Camera events only remember the view; they never rebuild the cloud.
          scene.on('plotly_relayout', event => { if (event['scene.camera']) state.camera = structuredClone(event['scene.camera']); });
          scene.on('plotly_webglcontextlost', () => { failed = true; $('layer-error').hidden = false; });
        } else await Plotly.react(scene, traces, layout);
      } else await Plotly.relayout(scene, { 'scene.camera': structuredClone(state.camera) });
    } catch (error) { failed = true; $('layer-error').hidden = false; console.error('Point-cloud scene failed:', error); }
    finally { busy = false; scheduleScene(); }
  }
  // Plotly can emit a point click at the end of a drag. Do not let that reset
  // the selected product/proposal and queue a full data redraw during an orbit.
  scene.addEventListener('pointerdown', event => { pointerStart = { x: event.clientX, y: event.clientY }; orbitDragged = false; }, true);
  window.addEventListener('pointermove', event => {
    if (pointerStart && Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y) > 4) orbitDragged = true;
  }, true);
  const finishPointer = () => { pointerStart = null; scheduleScene(); };
  window.addEventListener('pointerup', finishPointer, true);
  window.addEventListener('pointercancel', finishPointer, true);
  window.addEventListener('blur', finishPointer);
  function svgBars(layers) {
    const svg = $('stacked-bars'), ns = 'http://www.w3.org/2000/svg'; svg.replaceChildren();
    const el = (tag, attrs, parent = svg, text) => { const n = document.createElementNS(ns, tag); Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v)); if (text !== undefined) n.textContent = text; parent.appendChild(n); return n; };
    const sorted = [...M.products].sort((a, b) => a.x - b.x || a.y - b.y);
    const samples = Array.from({ length: 8 }, (_, i) => sorted[Math.round(i * (sorted.length - 1) / 7)]);
    if (!samples.some(p => p.id === state.selected.id)) samples[4] = state.selected;
    const max = Math.ceil(Math.max(...M.products.map(p => p.fit))), y = v => 166 - v / max * 139;
    for (let tick = 0; tick <= max; tick += 2) { el('line', { x1: 48, x2: 875, y1: y(tick), y2: y(tick), stroke: '#263946' }); el('text', { x: 38, y: y(tick) + 3, fill: '#9ab1bc', 'font-size': 10, 'text-anchor': 'end' }, svg, '£' + tick); }
    samples.forEach((p, index) => {
      const x = 72 + index * 102, g = el('g', { tabindex: 0, role: 'button', 'aria-label': `Select ${p.id}, ${p.name}; benchmark ${money(p.fit)} per 100 grams` });
      let cumulative = 0;
      layers.forEach(layer => { const value = layer.value(p); if (value > 1e-10) { const rectangle = el('rect', { x, y: y(cumulative + value), width: 47, height: value / max * 139, fill: layer.color, stroke: '#dfeff320', 'stroke-width': 0.6 }, g); el('title', {}, rectangle, layer.name + ': ' + money(value)); } cumulative += value; });
      el('text', { x: x + 23.5, y: y(p.fit) - 7, fill: '#dcebea', 'font-size': 10, 'text-anchor': 'middle' }, g, money(p.fit));
      el('text', { x: x + 23.5, y: 184, fill: p.id === state.selected.id ? '#d8baff' : '#adc0c7', 'font-size': 10, 'text-anchor': 'middle' }, g, p.id);
      if (p.id === state.selected.id) el('line', { x1: x - 3, x2: x + 50, y1: 193, y2: 193, stroke: '#d8baff', 'stroke-width': 2 }, g);
      g.addEventListener('click', () => select(p.id)); g.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(p.id); } });
    });
    el('text', { x: 48, y: 207, fill: '#91a9b4', 'font-size': 9 }, svg, 'Full benchmark stacks · representative samples · all values £ per 100 g');
  }
  function render() {
    const { all, visible } = plottedLayers(), p = state.selected;
    $('layer-product').value = p.id; $('layer-product-title').textContent = p.name;
    $('layer-product-meta').textContent = `${p.id} · ${p.sugar} g sugar /100 g · fictional product`;
    $('cutaway').value = state.cut;
    $('layer-legend').replaceChildren(); $('selected-stack').replaceChildren(); $('contribution-list').replaceChildren();
    all.forEach(layer => {
      const button = document.createElement('button'), swatch = document.createElement('i'); swatch.style.background = layer.color; button.appendChild(swatch); button.appendChild(document.createTextNode(layer.name));
      button.setAttribute('aria-pressed', String(state.peeledTo === layer.key)); button.setAttribute('title', 'Peel to ' + layer.name); button.addEventListener('click', () => { state.peeledTo = state.peeledTo === layer.key ? null : layer.key; render(); }); $('layer-legend').appendChild(button);
      const value = layer.value(p), segment = document.createElement('div'); segment.style.background = layer.color; segment.style.flexGrow = String(value); segment.style.flexBasis = '0';
      segment.title = layer.name + ': ' + money(value); if (value / p.fit > 0.12) segment.textContent = layer.name; if (value > 1e-10) $('selected-stack').appendChild(segment);
      const row = document.createElement('div'); row.className = 'contribution-row'; const name = document.createElement('span'), dot = document.createElement('i'); dot.style.background = layer.color; name.appendChild(dot); name.appendChild(document.createTextNode(layer.name)); const amount = document.createElement('b'); amount.textContent = money(value); row.appendChild(name); row.appendChild(amount); $('contribution-list').appendChild(row);
    });
    const visibleProducts = M.products.filter(p => p.x <= state.cut + 1e-9);
    const sampleCount = visibleProducts.reduce((total, product) => total + visible.filter(layer => layer.value(product) > 1e-10).length * state.density, 0);
    $('scene-status').textContent = `${visibleProducts.length} / ${M.products.length} fictional products · ${sampleCount.toLocaleString()} layer samples`;
    $('layer-note').textContent = state.peeledTo ? `Peeled to ${visible[visible.length - 1].name}. Upper samples are hidden; full benchmark anchors and exact product values stay fixed.` : '500 distinct fictional products. Colored returns sample each product’s trait layers; they are display marks, not additional products. No connecting mesh or interpolated terrain.';
    $('layer-fit').textContent = money(p.fit); $('layer-actual').textContent = money(M.unitPrice(p));
    $('layer-price').value = state.proposal.toFixed(2); $('layer-slider').value = state.proposal;
    const gap = (state.proposal / p.fit - 1) * 100; $('layer-gap').textContent = (gap >= 0 ? '+' : '−') + Math.abs(gap).toFixed(1) + '%';
    $('selected-visibility').textContent = p.x > state.cut + 1e-9 ? 'This product is beyond the scan slice. Use “Slice to product” to reveal its marker.' : 'Colored returns belong to this product’s contribution stack. The hollow marker is its full benchmark; the violet diamond is your proposed price.';
    svgBars(all); renderScene();
  }
  function select(id) { const p = M.products.find(p => p.id === id); if (!p) return; state.selected = p; state.proposal = M.unitPrice(p); render(); }
  function price(raw) { const value = Number(raw); if (String(raw).trim() !== '' && Number.isFinite(value)) state.proposal = Math.round(Math.min(10, Math.max(0.5, value)) * 100) / 100; render(); }
  M.products.forEach(p => { const option = document.createElement('option'); option.value = p.id; option.textContent = p.id + ' · ' + p.name + ' · sugar ' + p.sugar; $('layer-product').appendChild(option); });
  $('top-n').addEventListener('change', e => { state.topN = Number(e.target.value); state.peeledTo = null; render(); });
  $('sample-density').addEventListener('change', e => { state.density = Number(e.target.value); render(); });
  $('point-size').addEventListener('input', e => { state.pointSize = Number(e.target.value); renderScene(); });
  $('cutaway').addEventListener('input', e => { state.cut = Number(e.target.value); render(); });
  $('cut-product').addEventListener('click', () => { state.cut = Math.min(1, state.selected.x + 0.015); render(); });
  $('show-all').addEventListener('click', () => { state.peeledTo = null; state.cut = 1; render(); });
  $('layer-product').addEventListener('change', e => select(e.target.value));
  $('layer-price').addEventListener('change', e => price(e.target.value)); $('layer-slider').addEventListener('input', e => price(e.target.value));
  $('layer-reset').addEventListener('click', () => { state.proposal = M.unitPrice(state.selected); render(); });
  $('layer-3d').addEventListener('click', () => { state.camera.eye = { x: 1.8, y: -1.85, z: 0.95 }; renderScene(true); });
  $('layer-side').addEventListener('click', () => { state.camera.eye = { x: 2.7, y: -0.15, z: 0.18 }; renderScene(true); });
  $('layer-top').addEventListener('click', () => { state.camera.eye = { x: 0.05, y: 0.05, z: 2.7 }; renderScene(true); });
  render();
})();
