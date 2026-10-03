/* Pure selection/plot logic. Unknown traits never become zero or false. */
(function (root) {
  'use strict';
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  const attribute = (product, key) => product.attributes[key] || { status: 'unknown', value: null, unit: null, reviewStatus: 'unreviewed' };
  const latest = product => product.prices[0] || null;
  const numeric = (product, key) => {
    const field = attribute(product, key);
    return field.status === 'known' && finite(field.value) ? field.value : null;
  };
  function axisValue(product, key, totalFields) {
    const price = latest(product);
    if (key === 'coverage') return product.known / totalFields * 100;
    if (key === 'conflicts') return product.conflicts;
    if (key === 'observation_weight') return price?.quantity_status === 'known' && finite(price.total_edible_weight_g) && price.total_edible_weight_g > 0 ? price.total_edible_weight_g : null;
    if (key === 'displayed_unit' || key === 'displayed_pack') {
      if (!price || price.currency !== 'GBP' || product.latestPriceConflict) return null;
      if (key === 'displayed_unit' && (price.quantity_status !== 'known' || !finite(price.total_edible_weight_g) || price.total_edible_weight_g <= 0)) return null;
      const value = price[key === 'displayed_unit' ? 'displayed_price_per_100g_gbp' : 'displayed_price'];
      return finite(value) && value > 0 ? value : null;
    }
    return numeric(product, key);
  }
  function filter(products, { search = '', role = 'all', source = 'all', status = 'all', rules = [] } = {}) {
    const query = search.trim().toLocaleLowerCase();
    return products.filter(p => (!query || [p.name, p.brand, p.source, p.id].join(' ').toLocaleLowerCase().includes(query)) &&
      (role === 'all' || p.role === role) && (source === 'all' || p.source === source) &&
      (status === 'all' || status === 'conflicts' && (p.conflicts > 0 || p.latestPriceConflict) ||
        status === 'priced' && axisValue(p, 'displayed_unit', 1) !== null ||
        status === 'unpriced' && axisValue(p, 'displayed_unit', 1) === null) && rules.every(rule => matchesRule(p, rule)));
  }
  function points(products, axes, totalFields) {
    const plotted = [], excluded = [];
    for (const product of products) {
      const coordinates = axes.map(key => axisValue(product, key, totalFields));
      if (coordinates.every(finite)) plotted.push({ product, coordinates });
      else excluded.push(product.id);
    }
    return { plotted, excluded };
  }
  function fields(all, { group = 'all', query = '', limit = 8, pinned = [], modelOnly = false } = {}) {
    const selected = [...new Set(pinned)].map(key => all.find(f => f.key === key)).filter(Boolean);
    const candidates = all.filter(f => !pinned.includes(f.key) && (!modelOnly || f.modelSelected) && (group === 'all' || f.group === group) &&
      (!query.trim() || (f.key + ' ' + f.label).toLowerCase().includes(query.trim().toLowerCase())))
      .sort((a, b) => b.known - a.known || a.key.localeCompare(b.key)).slice(0, limit);
    return [...selected, ...candidates];
  }
  function operators(field) {
    const states = [
      { key: 'known', label: 'Has a value' }, { key: 'unknown', label: 'Unknown' },
      { key: 'conflict', label: 'Conflicting' }, { key: 'not_applicable', label: 'Not applicable' },
      { key: 'reviewed', label: 'Reviewed' }
    ];
    if (field.numeric) return [{ key: 'range', label: 'Within range' }, ...states];
    if (field.type === 'enum' || field.type === 'boolean') return [{ key: 'equals', label: 'Equals' }, ...states];
    return states;
  }
  function createRule(field, operator, { min = '', max = '', value = '' } = {}) {
    if (!field || !operators(field).some(o => o.key === operator)) return { error: 'Choose a supported condition for this trait.' };
    const rule = { field: field.key, operator };
    if (operator === 'range') {
      const parse = raw => String(raw).trim() === '' ? null : Number(raw);
      const low = parse(min), high = parse(max), bounds = [low, high].filter(v => v !== null);
      if (!bounds.length) return { error: 'Enter a minimum or maximum.' };
      if (bounds.some(v => !finite(v))) return { error: 'Enter valid numbers.' };
      if (field.type === 'integer' && bounds.some(v => !Number.isInteger(v))) return { error: 'This trait uses whole numbers.' };
      if (low !== null && high !== null && low > high) return { error: 'Minimum must not exceed maximum.' };
      if (bounds.some(v => field.minimum != null && v < field.minimum || field.maximum != null && v > field.maximum)) return { error: 'Values must stay within the schema’s declared bounds.' };
      rule.min = low; rule.max = high;
    }
    if (operator === 'equals') {
      const allowed = field.type === 'boolean' ? [true, false] : field.allowedValues;
      const match = allowed.find(v => String(v) === String(value));
      if (match === undefined) return { error: 'Choose a value from the schema’s vocabulary.' };
      rule.value = match;
    }
    return { rule };
  }
  function matchesRule(product, rule) {
    const field = attribute(product, rule.field);
    if (['known', 'unknown', 'conflict', 'not_applicable'].includes(rule.operator)) return field.status === rule.operator;
    if (rule.operator === 'reviewed') return field.reviewStatus === 'reviewed';
    if (field.status !== 'known') return false;
    if (rule.operator === 'equals') return field.value === rule.value;
    if (rule.operator === 'range') return finite(field.value) && (rule.min === null || field.value >= rule.min) && (rule.max === null || field.value <= rule.max);
    return false;
  }
  function coverage(products, key) {
    const counts = { known: 0, unknown: 0, conflict: 0, not_applicable: 0, reviewed: 0, total: products.length };
    for (const p of products) { const a = attribute(p, key); counts[a.status]++; if (a.reviewStatus === 'reviewed') counts.reviewed++; }
    return counts;
  }
  function compare(products, ids) {
    const byId = new Map(products.map(p => [p.id, p]));
    return [...new Set(ids)].map(id => byId.get(id)).filter(Boolean);
  }
  const api = { attribute, latest, numeric, axisValue, filter, points, fields, operators, createRule, matchesRule, coverage, compare };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CollectionExplorer = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
