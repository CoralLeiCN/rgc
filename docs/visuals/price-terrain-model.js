/* Synthetic design fixtures. This module does not fit or validate a model. */
(function (root) {
  'use strict';
  const dimensions = {
    cocoa: { label: 'Cocoa', unit: '%', min: 50, max: 80, step: 1 },
    grams: { label: 'Net weight', unit: 'g', min: 60, max: 100, step: 2 },
    sugar: { label: 'Sugar', unit: 'g / 100 g', min: 5, max: 15, step: 0.5 }
  };
  const contexts = [
    { brand: 'Aurum', organic: true, nuts: false, origin: true },
    { brand: 'Forma', organic: false, nuts: true, origin: false },
    { brand: 'Field', organic: false, nuts: false, origin: true }
  ];
  // Hand-authored illustrative log-price function, not learned coefficients.
  // Brand is a display label; these fixtures cannot identify a brand effect.
  function benchmark(p) {
    return Math.exp(Math.log(2.65) + 0.018 * (p.cocoa - 65)
      - 0.48 * Math.log(p.grams / 80) - 0.014 * (p.sugar - 10)
      + 0.18 * Number(p.organic) + 0.11 * Number(p.nuts)
      + 0.13 * Number(p.origin) + 0.0007 * (p.cocoa - 65) * (p.sugar - 10));
  }
  const products = [];
  contexts.forEach((context, c) => {
    [50, 60, 70, 80].forEach((cocoa, a) => {
      [60, 80, 100].forEach((grams, b) => {
        [5, 10, 15].forEach((sugar, d) => {
          const id = 'S' + String(products.length + 1).padStart(3, '0');
          const p = { id, ...context, cocoa, grams, sugar };
          const offset = [-0.13, 0.07, 0.19, -0.05, 0.24, 0.02][(a + 2 * b + d + c) % 6];
          p.currentPack = Math.round(benchmark(p) * (1 + offset) * grams) / 100;
          p.name = `${context.brand} ${cocoa}% / ${grams} g`;
          products.push(Object.freeze(p));
        });
      });
    });
  });
  function unitPrice(p, packPrice = p.currentPack) { return packPrice * 100 / p.grams; }
  function metrics(p, proposedPack) {
    const fit = benchmark(p), current = unitPrice(p), proposed = unitPrice(p, proposedPack);
    return { fit, current, proposed, gap: proposed - fit,
      gapPercent: (proposed / fit - 1) * 100,
      changePercent: (proposedPack / p.currentPack - 1) * 100 };
  }
  function sliceValue(p, xKey, yKey, x, y) {
    if (xKey === yKey || !dimensions[xKey] || !dimensions[yKey]) throw new Error('Distinct supported axes required');
    return benchmark({ ...p, [xKey]: x, [yKey]: y });
  }
  function slicePeers(p, xKey, yKey) {
    const fixedKeys = [...Object.keys(dimensions).filter(k => k !== xKey && k !== yKey),
      'brand', 'organic', 'nuts', 'origin'];
    return products.filter(q => fixedKeys.every(k => q[k] === p[k]));
  }
  function range(key, count = 27) {
    const d = dimensions[key];
    return Array.from({ length: count }, (_, i) => d.min + (d.max - d.min) * i / (count - 1));
  }
  const api = Object.freeze({ dimensions, products: Object.freeze(products), benchmark,
    unitPrice, metrics, sliceValue, slicePeers, range });
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.PriceTerrain = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
