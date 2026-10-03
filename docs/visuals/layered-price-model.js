/* Point-cloud geometry and exact attributions for 500 fictional products. */
(function (root) {
  'use strict';
  const source = typeof module !== 'undefined' && module.exports ? require('./price-terrain-model.js') : root.PriceTerrain;
  const traits = [
    { key: 'cocoa', name: 'Cocoa', color: '#ee796c' },
    { key: 'grams', name: 'Pack size', color: '#9d8bdb' },
    { key: 'sugar', name: 'Sugar', color: '#6caed9' },
    { key: 'organic', name: 'Organic', color: '#72c6a9' },
    { key: 'nuts', name: 'Nuts', color: '#e7b75e' },
    { key: 'origin', name: 'Single origin', color: '#d393bc' }
  ];
  const reference = Object.freeze({ cocoa: 50, grams: 100, sugar: 15, organic: false, nuts: false, origin: false });
  const base = source.benchmark(reference), factorial = [1, 1, 2, 6, 24, 120, 720];
  function contributions(product) {
    // Exact six-feature Shapley decomposition of the PRICE output against one
    // declared synthetic reference. This is not a fitted or causal explanation.
    const values = Array.from({ length: 64 }, (_, mask) => {
      const input = { ...reference };
      traits.forEach((t, j) => { if (mask & (1 << j)) input[t.key] = product[t.key]; });
      return source.benchmark(input);
    });
    return traits.map((t, j) => {
      let total = 0;
      for (let mask = 0; mask < 64; mask++) if (!(mask & (1 << j))) {
        const count = mask.toString(2).replace(/0/g, '').length;
        total += factorial[count] * factorial[5 - count] / factorial[6] * (values[mask | (1 << j)] - values[mask]);
      }
      return total;
    });
  }
  function project(rows) {
    const keys = traits.map(t => t.key), n = rows.length;
    const means = keys.map(k => rows.reduce((s, p) => s + Number(p[k]), 0) / n);
    // Price attributions already share currency units. Center without unit
    // variance scaling so tiny contributors do not dominate the layout.
    const scales = keys.map(() => 1);
    const vectors = rows.map(p => keys.map((k, j) => (Number(p[k]) - means[j]) / scales[j]));
    const covariance = keys.map((_, i) => keys.map((_, j) => vectors.reduce((sum, v) => sum + v[i] * v[j], 0) / n));
    const dot = (a, b) => a.reduce((sum, x, i) => sum + x * b[i], 0);
    function eigen(seed, orthogonalTo) {
      let vector = seed;
      for (let iteration = 0; iteration < 100; iteration++) {
        let next = covariance.map(row => dot(row, vector));
        if (orthogonalTo) { const amount = dot(next, orthogonalTo); next = next.map((v, i) => v - amount * orthogonalTo[i]); }
        const length = Math.hypot(...next);
        if (length < 1e-12) throw new Error('Projection is degenerate');
        vector = next.map(v => v / length);
      }
      return vector;
    }
    const first = eigen([0.21, 0.39, 0.61, 0.47, 0.19, 0.77]);
    const second = eigen([0.37, 0.73, 0.23, 0.59, 0.31, 0.83], first);
    const raw = vectors.map(v => [dot(v, first), dot(v, second)]);
    const min = [0, 1].map(j => Math.min(...raw.map(v => v[j])));
    const max = [0, 1].map(j => Math.max(...raw.map(v => v[j])));
    return raw.map(v => v.map((value, j) => (value - min[j]) / (max[j] - min[j])));
  }
  function fixtures() {
    let seed = 20261003;
    const random = () => {
      seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    const brands = ['Aurum', 'Forma', 'Field', 'Morrow', 'Vale'], seen = new Set(), rows = [];
    while (rows.length < 500) {
      const p = { cocoa: Math.round((50 + random() * 30) * 10) / 10,
        grams: 60 + Math.floor(random() * 41), sugar: Math.round((5 + random() * 10) * 10) / 10,
        organic: random() < 0.43, nuts: random() < 0.31, origin: random() < 0.56 };
      const signature = traits.map(t => p[t.key]).join('|');
      if (seen.has(signature)) continue;
      seen.add(signature);
      p.id = 'P' + String(rows.length + 1).padStart(3, '0');
      p.brand = brands[Math.floor(random() * brands.length)];
      p.name = `${p.brand} ${p.cocoa}% / ${p.grams} g`;
      p.currentPack = Math.round(source.benchmark(p) * (0.82 + random() * 0.44) * p.grams) / 100;
      rows.push(p);
    }
    return rows;
  }
  const attributed = fixtures().map(p => ({ ...p, contributions: contributions(p) }));
  const points = project(attributed.map(p => Object.fromEntries(traits.map((t, i) => [t.key, p.contributions[i]]))));
  const products = attributed.map((p, i) => Object.freeze({ ...p, x: points[i][0], y: points[i][1], contributions: Object.freeze(p.contributions), fit: source.benchmark(p) }));
  const ranking = traits.map((t, index) => ({ ...t, index, importance: products.reduce((sum, p) => sum + Math.abs(p.contributions[index]), 0) / products.length })).sort((a, b) => b.importance - a.importance);
  function layers(topN) {
    const shown = ranking.slice(0, topN).map(t => ({ key: t.key, name: t.name, color: t.color, value: p => p.contributions[t.index] }));
    if (topN < traits.length) { const indices = ranking.slice(topN).map(t => t.index); shown.push({ key: 'other', name: 'Other traits', color: '#8e9b9f', value: p => indices.reduce((s, i) => s + p.contributions[i], 0) }); }
    return [{ key: 'base', name: 'Reference price', color: '#465e72', value: () => base }, ...shown];
  }
  function cloud(activeLayers, cut = 1, samplesPerLayer = 3) {
    if (!Number.isInteger(samplesPerLayer) || samplesPerLayer < 1 || samplesPerLayer > 8) throw new Error('Invalid display sampling density');
    return activeLayers.map((layer, index) => {
      const output = { key: layer.key, name: layer.name, color: layer.color, x: [], y: [], z: [], customdata: [] };
      for (const p of products) {
        if (p.x > cut + 1e-9) continue;
        const thickness = layer.value(p);
        if (thickness < 1e-10) continue;
        const low = activeLayers.slice(0, index).reduce((sum, l) => sum + l.value(p), 0);
        for (let sample = 1; sample <= samplesPerLayer; sample++) {
          output.x.push(p.x); output.y.push(p.y);
          output.z.push(low + thickness * sample / samplesPerLayer);
          output.customdata.push([p.id, p.name, thickness, p.fit]);
        }
      }
      return output;
    });
  }
  const api = Object.freeze({ traits, reference, base, products: Object.freeze(products), ranking, layers, cloud, contributions, unitPrice: source.unitPrice });
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.LayeredPrice = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
