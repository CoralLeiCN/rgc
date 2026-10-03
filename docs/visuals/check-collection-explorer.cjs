'use strict';
// Real-snapshot and controller regression checks; no GPU/browser is emulated.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const M = require('./collection-explorer-model.js');
const snapshotCode = fs.readFileSync(path.join(__dirname, 'data/collection-snapshot.js'), 'utf8');
const html = fs.readFileSync(path.join(__dirname, 'collection-explorer.html'), 'utf8');
const window = { listeners: {}, addEventListener(name, handler) { this.listeners[name] = handler; } };
const context = vm.createContext({ window, console, structuredClone, setTimeout, clearTimeout });
vm.runInContext(snapshotCode, context);
const D = window.RGCCollectionSnapshot;
assert.equal(D.products.length, D.meta.counts.listings);
assert.equal(D.products.reduce((n, p) => n + p.prices.length, 0), D.meta.counts.price_observations);
assert.equal(new Set(D.products.map(p => p.id)).size, D.products.length);
assert.equal(D.fields.length, D.meta.counts.tracked_attributes);
const axes = ['observation_weight', 'composition.cocoa_percentage', 'displayed_unit'];
const cloud = M.points(D.products, axes, D.fields.length);
assert.equal(cloud.plotted.length + cloud.excluded.length, D.products.length);
assert.ok(cloud.plotted.every(p => p.coordinates.every(Number.isFinite)));
const original = cloud.plotted[0].product;
const empty = { ...original, attributes: {}, prices: [] };
assert.equal(M.numeric(empty, 'composition.cocoa_percentage'), null);
assert.equal(M.axisValue(empty, 'displayed_unit', 103), null);
assert.equal(M.axisValue({ ...original, latestPriceConflict: true }, 'displayed_unit', 103), null);
assert.equal(M.axisValue({ ...original, prices: [{ ...original.prices[0], currency: 'USD' }] }, 'displayed_unit', 103), null);
assert.equal(M.axisValue({ ...original, prices: [{ ...original.prices[0], quantity_status: 'conflict' }] }, 'displayed_unit', 103), null);
assert.equal(M.numeric({ ...empty, attributes: { cocoa: { status: 'known', value: 0 } } }, 'cocoa'), 0);
assert.equal(M.numeric({ ...empty, attributes: { cocoa: { status: 'unknown', value: 0 } } }, 'cocoa'), null);
assert.equal(M.numeric({ ...empty, attributes: { organic: { status: 'known', value: false } } }, 'organic'), null);
assert.equal(M.filter(D.products, { search: 'zzqdoesnotexist' }).length, 0);
assert.equal(M.fields(D.fields, { group: 'nutrition', limit: 103 }).length, 12);
for (const source of new Set(D.products.map(p => p.source))) assert.ok(M.filter(D.products, { source }).every(p => p.source === source));
const cocoa = D.fields.find(field => field.key === 'composition.cocoa_percentage');
const range = M.createRule(cocoa, 'range', { min: '60', max: '90' });
assert.ok(range.rule);
assert.ok(M.createRule(cocoa, 'range', { min: '101' }).error);
assert.ok(M.createRule(cocoa, 'range', { min: '90', max: '60' }).error);
assert.ok(M.createRule(cocoa, 'range', {}).error);
assert.ok(M.createRule(D.fields.find(field => field.type === 'integer'), 'range', { min: '1.5' }).error);
const cocoaCohort = M.filter(D.products, { rules: [range.rule] });
assert.ok(cocoaCohort.length > 0 && cocoaCohort.every(p => M.numeric(p, cocoa.key) >= 60 && M.numeric(p, cocoa.key) <= 90));
const boolField = { key: 'example.claim', numeric: false, type: 'boolean', allowedValues: [] };
const falseRule = M.createRule(boolField, 'equals', { value: 'false' }).rule;
assert.equal(falseRule.value, false);
assert.equal(M.matchesRule(empty, falseRule), false);
assert.equal(M.matchesRule({ ...empty, attributes: { 'example.claim': { status: 'known', value: false } } }, falseRule), true);
assert.equal(M.coverage([empty], cocoa.key).unknown, 1);
assert.equal(M.fields(D.fields, { group: 'nutrition', pinned: [cocoa.key], limit: 2 })[0].key, cocoa.key);
assert.equal(M.fields(D.fields, { modelOnly: true, limit: Infinity }).length, D.contract.selectedPredictors.length);
assert.deepEqual(M.compare(D.products, [original.id, 'missing', original.id]).map(p => p.id), [original.id]);

class Element {
  constructor(tag = 'div') { this.tagName = tag; this.children = []; this.style = {}; this.listeners = {}; this.hidden = true; this.value = ''; this.textContent = ''; }
  appendChild(child) { this.children.push(child); return child; }
  replaceChildren(...children) { this.children = children; }
  addEventListener(name, handler) { this.listeners[name] = handler; }
  on(name, handler) { this.listeners[name] = handler; }
  setAttribute(name, value) { this[name] = value; }
}
const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
assert.equal(new Set(ids).size, ids.length);
const nodes = Object.fromEntries(ids.map(id => [id, new Element()]));
// Include actual static select options so dynamic option-label updates run.
for (const select of html.matchAll(/<select\b[^>]*id="([^"]+)"[^>]*>([\s\S]*?)<\/select>/g)) {
  for (const option of select[2].matchAll(/<option\b[^>]*value="([^"]*)"[^>]*>([^<]*)<\/option>/g)) {
    const child = new Element('option'); child.value = option[1]; child.textContent = option[2]; nodes[select[1]].appendChild(child);
  }
}
const head = new Element('head');
let evidenceLoads = 0;
head.appendChild = script => {
  evidenceLoads++;
  assert.match(script.src, /^data\/collection-evidence\/[a-z0-9-]+\.js$/);
  vm.runInContext(fs.readFileSync(path.join(__dirname, script.src), 'utf8'), context);
  queueMicrotask(script.onload);
  return script;
};
context.document = { head, getElementById(id) { assert.ok(nodes[id], 'Missing HTML element: ' + id); return nodes[id]; }, createElement: tag => new Element(tag) };
const frames = [];
context.requestAnimationFrame = handler => frames.push(handler);
window.CollectionExplorer = M;
const calls = { newPlot: 0, react: 0, relayout: 0 };
let last;
const Plotly = {
  async newPlot(_, traces, layout, config) { calls.newPlot++; last = { traces, layout, config }; },
  async react(_, traces, layout) { calls.react++; last = { traces, layout }; },
  async relayout() { calls.relayout++; }
};
context.Plotly = window.Plotly = Plotly;
vm.runInContext(fs.readFileSync(path.join(__dirname, 'collection-explorer.js'), 'utf8'), context);
async function flush() { for (let i = 0; i < 4; i++) { while (frames.length) await frames.shift()(); await new Promise(resolve => setImmediate(resolve)); } }
async function event(id, name, value) { nodes[id].listeners[name]({ target: { value } }); await flush(); }
(async () => {
  await flush();
  assert.equal(last.traces.length, 2); assert.equal(last.traces[0].x.length, cloud.plotted.length);
  assert.equal(last.config.plotGlPixelRatio, 1); assert.equal(last.traces[0].marker.opacity, 1);
  assert.equal(nodes['collection-tbody'].children.length, 25); assert.equal(nodes['collection-kpis'].children.length, 4);
  assert.equal(evidenceLoads, 1); assert.match(nodes['collection-evidence-loading'].textContent, /Evidence loaded/);
  const geometry = JSON.stringify(last.traces), before = calls.react;
  for (let i = 0; i < 40; i++) nodes['collection-scene'].listeners.plotly_relayout({ 'scene.camera': { eye: { x: i, y: 2, z: 1 } } });
  await flush(); assert.equal(calls.react, before); assert.equal(JSON.stringify(last.traces), geometry);
  await event('collection-top', 'click'); assert.equal(calls.relayout, 1); assert.equal(calls.react, before);
  const chosen = nodes['collection-selected-id'].textContent;
  nodes['collection-scene'].listeners.pointerdown({ clientX: 10, clientY: 10 });
  window.listeners.pointermove({ clientX: 70, clientY: 30 }); window.listeners.pointerup({});
  nodes['collection-scene'].listeners.plotly_click({ points: [{ customdata: cloud.plotted[1].product.id }] });
  await flush(); assert.equal(nodes['collection-selected-id'].textContent, chosen);
  nodes['collection-scene'].listeners.pointerdown({ clientX: 10, clientY: 10 }); window.listeners.pointerup({});
  nodes['collection-scene'].listeners.plotly_click({ points: [{ customdata: cloud.plotted[1].product.id }] });
  await flush(); assert.equal(nodes['collection-selected-id'].textContent, cloud.plotted[1].product.id);
  await event('collection-role', 'change', 'retail');
  assert.equal(last.traces[0].x.length, M.points(M.filter(D.products, { role: 'retail' }), axes, 103).plotted.length);
  const plotsBeforeColumns = calls.react;
  await event('collection-columns', 'change', 'all'); assert.equal(nodes['collection-thead'].children[0].children.length, 105);
  await event('collection-group', 'change', 'nutrition'); assert.equal(nodes['collection-thead'].children[0].children.length, 14);
  await event('collection-field', 'change', 'nutrition.sugars_g_per_100g'); assert.equal(nodes['collection-field-value'].textContent, 'Unknown');
  await event('schema-pin-trait', 'click'); assert.equal(nodes['schema-pin-trait']['aria-pressed'], 'true');
  await event('schema-compare-product', 'click'); assert.equal(nodes['schema-comparison'].hidden, false);
  assert.equal(nodes['schema-comparison-head'].children[0].children.length, 2);
  assert.equal(calls.react, plotsBeforeColumns, 'Column, trait and comparison controls must not replot the cloud');
  await event('collection-search', 'input', 'zzqdoesnotexist'); await new Promise(resolve => setTimeout(resolve, 170)); await flush();
  assert.equal(last.traces[0].x.length, 0); assert.equal(nodes['collection-selected-title'].textContent, 'No matching listings');
  await event('collection-clear', 'click'); assert.equal(last.traces[0].x.length, cloud.plotted.length);
  nodes['collection-scene'].listeners.plotly_webglcontextlost(); assert.equal(nodes['collection-plot-error'].hidden, false);
  await event('collection-next', 'click'); assert.ok(nodes['collection-tbody'].children.length > 0);
  console.log(`PASS: ${D.products.length} real listings, ${cloud.plotted.length} complete-axis points; unknown/conflict/currency rules; filters, 103 columns, evidence loading, camera isolation, drag/click separation and fallback.`);
  console.log('Controller checks only; live browser and GPU appearance remain unverified.');
})().catch(error => { console.error(error); process.exitCode = 1; });
