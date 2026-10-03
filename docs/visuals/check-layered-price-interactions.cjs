/* Run: node docs/visuals/check-layered-price-interactions.cjs
 * Checks the scene controller with a DOM/Plotly double, not GPU frame rate.
 */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const model = require('./layered-price-model.js');

class Element {
  constructor() { this.children = []; this.handlers = new Map(); this.style = {}; this.attributes = {}; this.value = ''; this.textContent = ''; this.hidden = true; }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...children) { this.children = children; }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  addEventListener(name, callback) { if (!this.handlers.has(name)) this.handlers.set(name, []); this.handlers.get(name).push(callback); }
  on(name, callback) { this.addEventListener(name, callback); }
  emit(name, event = {}) { for (const callback of this.handlers.get(name) || []) callback({ target: this, ...event }); }
}

const html = fs.readFileSync(path.join(__dirname, 'layered-price-landscape.html'), 'utf8');
const elements = new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(match => [match[1], new Element()]));
const get = id => { assert.ok(elements.has(id), `Control exists: ${id}`); return elements.get(id); };
const frameQueue = [], errors = [], calls = { newPlot: 0, react: 0, relayout: 0, cloud: 0 };
let traces, layout, config, holdNextReact = false, releaseReact;
const window = new Element();
window.LayeredPrice = { ...model, cloud(...args) { calls.cloud++; return model.cloud(...args); } };
window.Plotly = {
  async newPlot(scene, nextTraces, nextLayout, nextConfig) { calls.newPlot++; traces = nextTraces; layout = nextLayout; config = nextConfig; },
  async react(scene, nextTraces, nextLayout) {
    calls.react++; traces = nextTraces; layout = nextLayout;
    if (holdNextReact) { holdNextReact = false; await new Promise(resolve => { releaseReact = resolve; }); }
  },
  async relayout(scene, change) { calls.relayout++; layout.scene.camera = change['scene.camera']; scene.emit('plotly_relayout', change); }
};
const context = vm.createContext({
  window, Plotly: window.Plotly, structuredClone,
  document: { getElementById: get, createElement: () => new Element(), createElementNS: () => new Element(), createTextNode: text => ({ textContent: text }) },
  requestAnimationFrame: callback => { frameQueue.push(callback); return frameQueue.length; },
  console: { error: (...args) => errors.push(args) }
});
vm.runInContext(fs.readFileSync(path.join(__dirname, 'layered-price-landscape.js'), 'utf8'), context);

async function flush() {
  for (let i = 0; i < 100; i++) {
    while (frameQueue.length) frameQueue.shift()();
    await new Promise(resolve => setImmediate(resolve));
    if (!frameQueue.length) return;
  }
  assert.fail('Scene kept scheduling frames');
}
const data = () => traces.find(trace => trace.meta?.role === 'products');
const samples = () => traces.find(trace => trace.meta?.role === 'trait-samples');
const snapshot = value => JSON.stringify(value);
const anchorValues = () => snapshot([data().x, data().y, data().z, data().customdata]);
const update = (id, value, event = 'input') => { get(id).value = value; get(id).emit(event); };
const scene = get('layer-scene');

(async () => {
  await flush();
  assert.equal(calls.newPlot, 1);
  assert.equal(data().x.length, 500);
  assert.equal(samples().x.length, 7674);
  assert.equal(traces.length, 5, 'All visible geometry is batched into five traces');
  assert.equal(config.plotGlPixelRatio, 1, 'Avoid the default fourfold framebuffer pixel count');
  assert.ok(traces.every(trace => trace.type === 'scatter3d'));
  assert.ok(traces.filter(trace => trace.marker).every(trace => trace.marker.opacity === 1), 'Cloud does not trigger translucent marker passes');
  const originalAnchors = anchorValues(), originalSamples = samples().x;
  const originalProduct = get('layer-product').value, originalProposal = get('layer-price').value;
  const beforeOrbit = { ...calls };

  scene.emit('pointerdown', { clientX: 100, clientY: 100 });
  window.emit('pointermove', { clientX: 150, clientY: 135 });
  const camera = { eye: { x: 1.2, y: -2, z: 1.1 }, center: { x: 0, y: 0, z: -0.1 }, up: { x: 0, y: 0, z: 1 } };
  for (let i = 0; i < 40; i++) scene.emit('plotly_relayout', { 'scene.camera': camera });
  // Check both event orderings: a point click before or after the pointer ends.
  scene.emit('plotly_click', { points: [{ customdata: 'P500' }] });
  window.emit('pointerup');
  scene.emit('plotly_click', { points: [{ customdata: ['P500', 'a layer return'] }] });
  await flush();
  assert.deepEqual(calls, beforeOrbit, 'Orbit does not invoke react, relayout, newPlot, or cloud generation');
  assert.equal(get('layer-product').value, originalProduct, 'Dragging cannot select a product');
  assert.equal(get('layer-price').value, originalProposal, 'Dragging cannot reset a proposal');
  assert.equal(anchorValues(), originalAnchors);

  get('layer-top').emit('click');
  await flush();
  assert.equal(calls.relayout, 1, 'Camera preset only relayouts the camera');
  assert.equal(calls.react, 0);
  assert.equal(calls.cloud, 1);
  assert.equal(snapshot(layout.scene.camera.eye), snapshot({ x: 0.05, y: 0.05, z: 2.7 }));
  assert.equal(anchorValues(), originalAnchors);

  scene.emit('pointerdown', { clientX: 20, clientY: 20 });
  window.emit('pointerup');
  scene.emit('plotly_click', { points: [{ customdata: ['P500', 'a layer return'] }] });
  await flush();
  assert.equal(get('layer-product').value, 'P500', 'A stationary click still inspects a product');
  assert.equal(calls.react, 1);
  assert.equal(samples().x, originalSamples, 'Selection reuses cloud buffers');

  const beforeSliders = calls.react;
  for (let i = 0; i < 100; i++) update('point-size', 1 + (i % 7) * 0.5);
  await flush();
  assert.equal(calls.react, beforeSliders + 1, 'Rapid input events coalesce into one scene update');
  assert.equal(samples().x, originalSamples);
  assert.equal(calls.cloud, 1);
  update('layer-price', '6.25', 'change');
  await flush();
  assert.equal(anchorValues(), originalAnchors, 'Proposal changes preserve all benchmark coordinates and prices');
  assert.equal(samples().x, originalSamples);

  scene.emit('pointerdown', { clientX: 10, clientY: 10 });
  window.emit('pointermove', { clientX: 30, clientY: 30 });
  const beforeDeferred = calls.react;
  update('sample-density', 6, 'change');
  await flush();
  assert.equal(calls.react, beforeDeferred, 'Full cloud updates are deferred while dragging');
  window.emit('pointercancel');
  await flush();
  assert.equal(calls.react, beforeDeferred + 1);
  assert.equal(samples().x.length, 15348);
  assert.equal(data().x.length, 500, 'Display density never changes product count');

  // Inputs that arrive during an asynchronous render collapse to the latest state.
  holdNextReact = true;
  update('point-size', 2);
  await flush();
  const inFlight = calls.react;
  for (const value of [0.5, 0.7, 0.85]) update('cutaway', value);
  await flush();
  assert.equal(calls.react, inFlight, 'No overlapping Plotly renders');
  releaseReact();
  await flush();
  assert.equal(calls.react, inFlight + 1, 'Only the final queued state is rendered');
  assert.equal(data().x.length, model.products.filter(product => product.x <= 0.85 + 1e-9).length);
  get('show-all').emit('click');
  await flush();
  assert.equal(data().x.length, 500);
  assert.equal(calls.newPlot, 1, 'No WebGL scene re-creation after initial load');
  assert.equal(errors.length, 0);
  console.log('PASS: orbit isolation, drag/click separation, camera presets, batching, 500 product anchors, and queued updates.');
  console.log('DOM/Plotly controller checks only; GPU frame rate requires a browser.');
})().catch(error => { console.error(error); process.exitCode = 1; });
