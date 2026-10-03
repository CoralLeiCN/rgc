(function () {
  'use strict';
  const D = window.RGCCollectionSnapshot, M = window.CollectionExplorer;
  const $ = id => document.getElementById(id), money = n => '£' + n.toFixed(2);
  const make = (tag, text, className) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; };
  const fieldsByKey = new Map(D.fields.map(f => [f.key, f]));
  const byId = new Map(D.products.map(p => [p.id, p]));
  const colors = { retail: '#69d7b9', brand: '#b19ce3', unknown: '#829cae' };
  const fullFieldCount = D.fields.length;
  const unitLabel = unit => ({ g_per_100g: 'g /100 g', kcal_per_100g: 'kcal /100 g', kJ_per_100g: 'kJ /100 g', GBP_per_100g: '£ /100 g', celsius: '°C' }[unit] || unit || '');
  const axes = [
    { key: 'observation_weight', label: 'Observed pack weight / g' },
    { key: 'composition.cocoa_percentage', label: 'Stated cocoa / %' },
    { key: 'displayed_unit', label: 'Displayed price / £ per 100 g' },
    { key: 'displayed_pack', label: 'Displayed pack price / £' },
    { key: 'coverage', label: `Known traits / % of ${fullFieldCount}` },
    { key: 'conflicts', label: 'Conflicting traits / count' },
    ...D.fields.filter(f => f.numeric && f.key !== 'composition.cocoa_percentage').map(f => ({ key: f.key, label: f.label + (f.unit ? ' / ' + unitLabel(f.unit) : '') + (f.numericKnown === 0 ? ' · no values' : '') }))
  ];
  const state = { search: '', role: 'all', source: 'all', status: 'all', page: 0, group: 'all', traitQuery: '', columns: 8, rules: [], pinned: [], compared: [], modelOnly: false,
    axes: ['observation_weight', 'composition.cocoa_percentage', 'displayed_unit'], selected: null, field: 'composition.cocoa_percentage',
    camera: { eye: { x: 1.65, y: -1.7, z: 1.1 }, up: { x: 0, y: 0, z: 1 } } };
  let filtered = [], plotted = [], missing = [], shownFields = [];
  const evidenceLoads = new Map();
  const plot = { ready: false, failed: false, busy: false, pending: false, geometryDirty: true, scheduled: false, start: null, dragged: false };
  const scene = $('collection-scene');
  const displayValue = attribute => {
    if (attribute.status === 'unknown') return 'Unknown';
    if (attribute.status === 'conflict') return 'Conflict';
    if (attribute.status === 'not_applicable') return 'Not applicable';
    const value = attribute.value;
    return (Array.isArray(value) ? value.join(', ') : typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value ?? 'Unknown')) + (attribute.unit ? ' ' + unitLabel(attribute.unit) : '');
  };
  function options(id, values, selected) {
    const select = $(id);
    for (const { key, label } of values) { const option = make('option', label); option.value = key; select.appendChild(option); }
    if (selected !== undefined) select.value = selected;
  }
  function chooseField(key) {
    if (!fieldsByKey.has(key)) return;
    state.field = key; $('schema-trait').value = key;
    renderRuleEditor(); renderDetails();
  }
  function renderRuleEditor() {
    const field = fieldsByKey.get(state.field);
    $('schema-operator').replaceChildren(); options('schema-operator', M.operators(field), M.operators(field)[0].key);
    $('schema-value').replaceChildren();
    options('schema-value', (field.type === 'boolean' ? [true, false] : field.allowedValues).map(value => ({ key: String(value), label: String(value).replaceAll('_', ' ') })));
    if (field.allowedValues.length) $('schema-value').value = String(field.allowedValues[0]);
    if (field.type === 'boolean') $('schema-value').value = 'true';
    for (const id of ['schema-min', 'schema-max']) {
      $(id).value = ''; $(id).min = field.minimum ?? ''; $(id).max = field.maximum ?? ''; $(id).step = field.type === 'integer' ? '1' : 'any';
    }
    $('schema-range-unit').textContent = unitLabel(field.unit);
    $('schema-filter-description').textContent = field.description;
    $('schema-filter-error').hidden = true;
    renderRuleInputs();
  }
  function renderRuleInputs() {
    const operator = $('schema-operator').value;
    $('schema-range').hidden = operator !== 'range';
    $('schema-value-label').hidden = operator !== 'equals';
    $('schema-filter-error').hidden = true;
  }
  function ruleLabel(rule) {
    const field = fieldsByKey.get(rule.field), label = field.label;
    if (rule.operator === 'range') return label + ': ' + (rule.min ?? 'any') + '–' + (rule.max ?? 'any') + (field.unit ? ' ' + unitLabel(field.unit) : '');
    if (rule.operator === 'equals') return label + ': ' + String(rule.value).replaceAll('_', ' ');
    return label + ': ' + M.operators(field).find(o => o.key === rule.operator).label;
  }
  function chip(text, remove) {
    const button = make('button', text); button.setAttribute('aria-label', 'Remove ' + text);
    const icon = make('span', '×'); icon.setAttribute('aria-hidden', 'true'); button.appendChild(icon); button.addEventListener('click', remove); return button;
  }
  function renderSchemaControls() {
    $('schema-rules').replaceChildren(...state.rules.map((rule, index) => chip(ruleLabel(rule), () => { state.rules.splice(index, 1); state.page = 0; render(); })));
    $('schema-clear-rules').disabled = !state.rules.length;
    $('schema-pinned').replaceChildren(...state.pinned.map(key => chip(fieldsByKey.get(key).label + ' · pinned', () => togglePin(key))));
  }
  function togglePin(key) {
    if (!fieldsByKey.has(key)) return;
    if (state.pinned.includes(key)) state.pinned = state.pinned.filter(item => item !== key);
    else state.pinned.push(key);
    refreshColumns();
  }
  function refreshColumns() {
    // Column selection changes table layout, never plot data or camera.
    shownFields = M.fields(D.fields, { group: state.group, query: state.traitQuery, limit: state.columns, pinned: state.pinned, modelOnly: state.modelOnly });
    $('collection-results').textContent = `${filtered.length.toLocaleString()} listings · ${shownFields.length} trait columns`;
    renderSchemaControls(); renderTable(); renderComparison(); renderDefinition();
  }
  function renderDefinition() {
    const field = fieldsByKey.get(state.field), counts = M.coverage(filtered, field.key);
    const tags = [make('span', field.type.replaceAll('_', ' ')), make('span', unitLabel(field.unit) || 'No unit'), make('span', field.scope + ' scope')];
    if (field.modelSelected) tags.push(make('span', 'Selected pricing input', 'pricing-input'));
    $('schema-field-tags').replaceChildren(...tags);
    $('schema-field-description').textContent = field.description;
    $('schema-field-constraints').textContent = field.numeric ? `Allowed range: ${field.minimum ?? 'no minimum'} to ${field.maximum ?? 'no maximum'} ${unitLabel(field.unit)}.` : field.allowedValues.length ? 'Allowed values: ' + field.allowedValues.join(', ') + '. Unknown is a separate evidence state.' : 'Free source text; filter by evidence state. Long values open in the evidence panel.';
    $('schema-field-coverage').textContent = `${counts.known} known · ${counts.unknown} unknown · ${counts.conflict} conflicts · ${counts.not_applicable} not applicable in the filtered cohort. ${counts.reviewed} reviewed.`;
    $('schema-field-qualifier').textContent = field.qualifier;
    $('schema-field-model').textContent = field.modelSelected ? 'Included in the selected pricing design. ' + (field.modelDefinition.required ? 'Required when preparing model inputs. ' : '') + 'A populated value still needs the published reviews and eligibility checks.' : 'Tracked by the schema; not selected in the current pricing design. Schema coverage alone does not make it a modeled price driver.';
    $('schema-pin-trait').textContent = state.pinned.includes(field.key) ? 'Unpin this trait' : 'Pin this trait to the matrix';
    $('schema-pin-trait').setAttribute('aria-pressed', String(state.pinned.includes(field.key)));
  }
  function renderComparison() {
    const selected = M.compare(D.products, state.compared);
    $('schema-comparison').hidden = selected.length === 0;
    const head = make('tr'); head.appendChild(make('th', 'Trait / evidence'));
    for (const p of selected) {
      const th = make('th', p.name); th.appendChild(make('small', p.source + (filtered.some(row => row.id === p.id) ? '' : ' · outside current filters')));
      const remove = make('button', 'Remove'); remove.setAttribute('aria-label', 'Remove ' + p.name + ' from comparison'); remove.addEventListener('click', () => { state.compared = state.compared.filter(id => id !== p.id); renderComparison(); }); th.appendChild(remove); head.appendChild(th);
    }
    $('schema-comparison-head').replaceChildren(head);
    const body = $('schema-comparison-body'); body.replaceChildren();
    const priceRow = make('tr'); priceRow.appendChild(make('th', 'Latest displayed £ /100 g · unreviewed'));
    for (const p of selected) { const price = M.axisValue(p, 'displayed_unit', fullFieldCount); priceRow.appendChild(make('td', price === null ? 'Unavailable' : money(price))); } body.appendChild(priceRow);
    for (const field of shownFields) {
      const row = make('tr'), label = make('th', field.label); label.appendChild(make('small', field.description)); row.appendChild(label);
      for (const p of selected) {
        const value = M.attribute(p, field.key), td = make('td'), button = make('button', displayValue(value), value.status);
        button.addEventListener('click', () => select(p.id, field.key)); td.appendChild(button); td.appendChild(make('small', (value.reviewStatus || 'unreviewed').replaceAll('_', ' ') + (value.scope ? ' · ' + value.scope : ''))); row.appendChild(td);
      }
      body.appendChild(row);
    }
    const already = state.compared.includes(state.selected);
    $('schema-compare-product').textContent = already ? 'Remove from comparison' : 'Add to comparison';
    $('schema-compare-product').disabled = !state.selected || !already && selected.length >= 4;
    $('schema-compare-status').textContent = selected.length ? selected.length + ' / 4 in shortlist' + (selected.length >= 4 && !already ? ' · remove a listing to add another.' : '') : 'Select listings to compare their trait evidence.';
  }
  function loadEvidence(source) {
    if (window.RGCCollectionEvidence?.[source]) return Promise.resolve(window.RGCCollectionEvidence[source]);
    if (!evidenceLoads.has(source)) evidenceLoads.set(source, new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'data/collection-evidence/' + encodeURIComponent(source) + '.js';
      script.onload = () => window.RGCCollectionEvidence?.[source] ? resolve(window.RGCCollectionEvidence[source]) : reject(new Error('Evidence asset has no matching source'));
      script.onerror = () => reject(new Error('Evidence asset could not load'));
      document.head.appendChild(script);
    }));
    return evidenceLoads.get(source);
  }
  function evidenceField(p, details) {
    const field = details?.attributes[state.field] || M.attribute(p, state.field);
    const review = field.review_status || field.reviewStatus || 'unreviewed';
    $('collection-field-state').textContent = field.status + ' · ' + review.replaceAll('_', ' ') + (field.scope ? ' · ' + field.scope + ' scope' : '');
    $('collection-field-value').textContent = displayValue(field);
    $('collection-field-method').textContent = field.method ? 'Extraction: ' + field.method.replaceAll('_', ' ') + (field.qualifier ? ' · ' + field.qualifier : '') : 'No supported source value is available for this trait.';
    const evidence = $('collection-evidence'); evidence.replaceChildren();
    for (const item of field.evidence || []) evidence.appendChild(make('p', 'Capture ' + item.capture_id + '\n' + item.pointer));
    if (field.truncated) evidence.appendChild(make('p', 'Long value shortened in the matrix. Full text loads in this panel.'));
  }
  function exclusionLabels(price) {
    const codes = price?.exclusion_reasons || [], labels = [];
    const groups = [
      ['category_scope', 'Confirm that this listing belongs in the comparable cohort.'],
      ['physical_identity', 'Review physical product and family identity.'],
      ['observation_edible_quantity', 'Review the edible pack weight for this observation.'],
      ['currency_or_tax', 'Confirm currency and consumer tax basis.'],
      ['regular_price', 'Establish a regular consumer price and promotion context.'],
      ['observation_time', 'Verify observation timing and availability.'],
      ['cocoa_percentage', 'Confirm the meaning and basis of the cocoa percentage.'],
      ['model_predictor', 'Review predictor values and their observation context.']
    ];
    for (const [prefix, label] of groups) if (codes.some(code => code.startsWith(prefix))) labels.push(label);
    const unmapped = codes.filter(code => !groups.some(([prefix]) => code.startsWith(prefix)));
    return [...labels, ...unmapped.map(code => code.replaceAll('_', ' '))];
  }
  function priceDetails(p, details) {
    const prices = details?.prices || p.prices, latest = prices[0];
    $('collection-exclusion-intro').textContent = latest ? latest.model_eligible ? 'The dataset marks this observation eligible. No fitted benchmark is connected to this page.' : 'This observation has not passed the dataset’s modeling checks.' : 'No normalized price observation is linked to this listing.';
    const list = $('collection-exclusions'); list.replaceChildren();
    const labels = exclusionLabels(latest);
    if (p.latestPriceConflict) labels.unshift('Same-time observations disagree on price or quantity; the price plot excludes this listing.');
    if (!details && latest) labels.push('Loading the exact review requirements…');
    for (const label of labels) list.appendChild(make('li', label));
    const history = $('collection-price-history'); history.replaceChildren();
    for (const observation of prices) {
      const amount = typeof observation.displayed_price === 'number' ? observation.displayed_price.toFixed(2) + ' ' + (observation.currency || 'currency unknown') : 'Price unknown';
      history.appendChild(make('div', amount + ' · ' + (observation.observed_at || 'Time unknown') + '\n' + observation.observation_id + (observation.tax_basis ? '\nTax: ' + observation.tax_basis + ' · promotion: ' + observation.promotion_status : ''), 'price-history-item'));
    }
    if (!prices.length) history.appendChild(make('p', 'No price observations in this snapshot.'));
  }
  function renderDetails() {
    const p = byId.get(state.selected);
    $('collection-field').value = state.field;
    renderDefinition(); renderComparison();
    if (!p) {
      $('collection-selected-title').textContent = 'No matching listings';
      for (const id of ['collection-selected-id', 'collection-price-context', 'collection-price-time', 'collection-coverage', 'collection-field-state', 'collection-field-value', 'collection-field-method', 'collection-evidence-loading', 'collection-exclusion-intro']) $(id).textContent = '';
      for (const id of ['collection-selected-tags', 'collection-evidence', 'collection-exclusions', 'collection-price-history']) $(id).replaceChildren();
      $('collection-selected-price').textContent = '—'; $('collection-coverage-bar').style.width = '0%'; return;
    }
    $('collection-selected-title').textContent = p.name;
    $('collection-selected-id').textContent = p.id;
    $('collection-selected-tags').replaceChildren(...[p.source, p.role + ' seller', p.reviewStatus].map(text => make('span', text)));
    const unit = M.axisValue(p, 'displayed_unit', fullFieldCount), price = M.latest(p);
    $('collection-selected-price').textContent = unit === null ? 'Unavailable' : money(unit);
    $('collection-price-context').textContent = p.latestPriceConflict ? 'Conflicting latest observations; no single headline price shown.' : price ? 'Displayed pack price: ' + (typeof price.displayed_price === 'number' ? price.displayed_price.toFixed(2) + ' ' + (price.currency || '?') : 'unknown') + ' · observed weight: ' + (price.total_edible_weight_g ?? 'unknown') + ' g. Regular-price and tax context remain unreviewed.' : 'No price observation is available.';
    $('collection-price-time').textContent = price ? 'Observed: ' + (price.observed_at || 'unknown time') + ' · ' + p.prices.length + ' observation(s)' : '';
    $('collection-coverage').textContent = `${p.known} / ${fullFieldCount} traits known · ${p.conflicts} conflicting. Coverage is not confidence.`;
    $('collection-coverage-bar').style.width = p.known / fullFieldCount * 100 + '%';
    const cached = window.RGCCollectionEvidence?.[p.source]?.[p.id];
    evidenceField(p, cached); priceDetails(p, cached);
    $('collection-evidence-loading').textContent = cached ? 'Evidence loaded from the pinned snapshot.' : 'Loading source evidence…';
    const selectedId = p.id, fieldKey = state.field;
    loadEvidence(p.source).then(source => {
      if (state.selected !== selectedId || state.field !== fieldKey) return;
      if (!source[p.id]) throw new Error('Listing missing from evidence asset');
      evidenceField(p, source[p.id]); priceDetails(p, source[p.id]);
      $('collection-evidence-loading').textContent = 'Evidence loaded from the pinned snapshot.';
    }).catch(() => { if (state.selected === selectedId && state.field === fieldKey) $('collection-evidence-loading').textContent = 'Evidence detail could not load. Indexed values remain visible; keep the data folder beside this page.'; });
  }
  function renderTable() {
    const head = make('tr'); head.appendChild(make('th', 'Source listing')); head.appendChild(make('th', 'Displayed £ /100 g'));
    for (const field of shownFields) {
      const th = make('th'), title = make('div', undefined, 'schema-column-title'), label = make('span', field.label + (field.unit ? ' / ' + unitLabel(field.unit) : ''));
      const pin = make('button', state.pinned.includes(field.key) ? '◆' : '◇'); pin.title = 'Pin ' + field.label; pin.setAttribute('aria-label', 'Pin ' + field.label); pin.setAttribute('aria-pressed', String(state.pinned.includes(field.key))); pin.addEventListener('click', () => togglePin(field.key)); title.appendChild(label); title.appendChild(pin); th.appendChild(title);
      th.appendChild(make('small', field.group + ' · ' + M.coverage(filtered, field.key).known.toLocaleString() + ' known here' + (field.modelSelected ? ' · pricing input' : ''))); head.appendChild(th);
    }
    $('collection-thead').replaceChildren(head);
    const body = $('collection-tbody'); body.replaceChildren();
    const page = filtered.slice(state.page * 25, (state.page + 1) * 25);
    for (const p of page) {
      const tr = make('tr'); tr.className = p.id === state.selected ? 'selected' : '';
      const identity = make('td'), choose = make('button', p.name); choose.addEventListener('click', () => select(p.id)); identity.appendChild(choose); identity.appendChild(make('small', p.source + ' · ' + p.role)); tr.appendChild(identity);
      const price = M.axisValue(p, 'displayed_unit', fullFieldCount); tr.appendChild(make('td', price === null ? 'Unavailable' : money(price)));
      for (const field of shownFields) {
        const cell = M.attribute(p, field.key), td = make('td'), button = make('button', displayValue(cell), 'trait-cell ' + cell.status);
        button.title = field.label + ': ' + displayValue(cell); button.addEventListener('click', () => select(p.id, field.key)); td.appendChild(button); tr.appendChild(td);
      }
      body.appendChild(tr);
    }
    if (!page.length) { const row = make('tr'), td = make('td', 'No listings match these filters.', 'empty-row'); td.colSpan = shownFields.length + 2; row.appendChild(td); body.appendChild(row); }
    $('collection-page').textContent = filtered.length ? `${state.page * 25 + 1}–${Math.min((state.page + 1) * 25, filtered.length)} of ${filtered.length.toLocaleString()}` : '0 listings';
    $('collection-prev').disabled = state.page === 0;
    $('collection-next').disabled = (state.page + 1) * 25 >= filtered.length;
  }
  function select(id, field) {
    if (!byId.has(id)) return;
    state.selected = id; if (field) { state.field = field; $('schema-trait').value = field; renderRuleEditor(); }
    const position = filtered.findIndex(p => p.id === id); if (position >= 0) state.page = Math.floor(position / 25);
    renderTable(); renderDetails(); requestPlot();
  }
  function requestPlot(cameraOnly = false) {
    plot.pending = true; plot.geometryDirty = plot.geometryDirty || !cameraOnly;
    schedulePlot();
  }
  function schedulePlot() {
    if (plot.failed || plot.busy || plot.scheduled || plot.start || !plot.pending) return;
    plot.scheduled = true; requestAnimationFrame(flushPlot);
  }
  async function flushPlot() {
    plot.scheduled = false;
    if (plot.start || plot.failed) return;
    if (!window.Plotly) { plot.failed = true; $('collection-plot-error').hidden = false; return; }
    const rebuild = plot.geometryDirty || !plot.ready;
    plot.pending = false; plot.geometryDirty = false; plot.busy = true;
    try {
      if (!rebuild) { await Plotly.relayout(scene, { 'scene.camera': structuredClone(state.camera) }); return; }
      const escape = s => String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
      const points = { type: 'scatter3d', uid: 'listings', mode: 'markers', x: plotted.map(p => p.coordinates[0]), y: plotted.map(p => p.coordinates[1]), z: plotted.map(p => p.coordinates[2]),
        customdata: plotted.map(p => p.product.id), text: plotted.map(p => escape(p.product.name)),
        marker: { size: 3.5, color: plotted.map(p => colors[p.product.role]), opacity: 1, line: { width: 0 } },
        hovertemplate: '%{text}<br>X: %{x:.2f}<br>Y: %{y:.2f}<br>Z: %{z:.2f}<extra>Unreviewed observation</extra>', showlegend: false };
      const selected = plotted.find(p => p.product.id === state.selected);
      const highlight = { type: 'scatter3d', uid: 'selection', mode: 'markers', x: selected ? [selected.coordinates[0]] : [], y: selected ? [selected.coordinates[1]] : [], z: selected ? [selected.coordinates[2]] : [],
        marker: { size: 7, color: '#f2dfad', symbol: 'circle-open', opacity: 1, line: { width: 2 } }, hoverinfo: 'skip', showlegend: false };
      const axis = key => ({ title: { text: axes.find(a => a.key === key).label, font: { size: 10 } }, tickfont: { size: 9 }, showbackground: true, backgroundcolor: '#0a1822', gridcolor: '#26424f', zerolinecolor: '#345361', showspikes: false });
      const layout = { margin: { l: 0, r: 0, t: 0, b: 0 }, paper_bgcolor: 'rgba(0,0,0,0)', font: { family: '-apple-system, sans-serif', color: '#a9c4d0' }, uirevision: state.axes.join(':'), showlegend: false,
        scene: { camera: structuredClone(state.camera), dragmode: 'orbit', aspectmode: 'cube', xaxis: axis(state.axes[0]), yaxis: axis(state.axes[1]), zaxis: axis(state.axes[2]) } };
      if (!plot.ready) {
        await Plotly.newPlot(scene, [points, highlight], layout, { plotGlPixelRatio: 1, responsive: true, displayModeBar: false, displaylogo: false, scrollZoom: true }); plot.ready = true;
        scene.on('plotly_relayout', event => { if (event['scene.camera']) state.camera = structuredClone(event['scene.camera']); });
        scene.on('plotly_click', event => { const id = event.points?.[0]?.customdata; if (!plot.dragged && typeof id === 'string') select(id); });
        scene.on('plotly_webglcontextlost', () => { plot.failed = true; $('collection-plot-error').hidden = false; });
      } else await Plotly.react(scene, [points, highlight], layout);
    } catch (error) { plot.failed = true; $('collection-plot-error').hidden = false; console.error('Collection scene:', error); }
    finally { plot.busy = false; schedulePlot(); }
  }
  function render() {
    filtered = M.filter(D.products, state);
    ({ plotted, excluded: missing } = M.points(filtered, state.axes, fullFieldCount));
    shownFields = M.fields(D.fields, { group: state.group, query: state.traitQuery, limit: state.columns, pinned: state.pinned, modelOnly: state.modelOnly });
    if (!filtered.some(p => p.id === state.selected)) state.selected = (plotted[0]?.product || filtered[0])?.id || null;
    state.page = Math.min(state.page, Math.max(0, Math.ceil(filtered.length / 25) - 1));
    $('collection-results').textContent = `${filtered.length.toLocaleString()} listings · ${shownFields.length} trait columns`;
    $('collection-plot-count').textContent = `${plotted.length.toLocaleString()} plotted / ${filtered.length.toLocaleString()} matching listings`;
    $('collection-plot-note').textContent = `${missing.length.toLocaleString()} listings lack usable values for these axes and remain in the matrix. One point per source listing; its latest dated price observation is used. Prices and traits are unreviewed. No fitted surface.`;
    renderSchemaControls(); renderTable(); renderDetails(); requestPlot();
  }
  scene.addEventListener('pointerdown', event => { plot.start = { x: event.clientX, y: event.clientY }; plot.dragged = false; }, true);
  window.addEventListener('pointermove', event => { if (plot.start && Math.hypot(event.clientX - plot.start.x, event.clientY - plot.start.y) > 4) plot.dragged = true; }, true);
  const finish = () => { plot.start = null; schedulePlot(); };
  window.addEventListener('pointerup', finish, true); window.addEventListener('pointercancel', finish, true); window.addEventListener('blur', finish);
  for (const [label, value] of [['Source listings', D.meta.counts.listings], ['Price observations', D.meta.counts.price_observations], ['Tracked traits', fullFieldCount], ['Rows eligible for model training', D.meta.counts.eligible_model_inputs]]) {
    const card = make('div', undefined, 'kpi'); card.appendChild(make('strong', value.toLocaleString())); card.appendChild(make('span', label)); $('collection-kpis').appendChild(card);
  }
  options('collection-source', [...new Set(D.products.map(p => p.source))].sort().map(key => ({ key, label: key })));
  options('collection-group', [...new Set(D.fields.map(f => f.group))].sort().map(key => ({ key, label: key })));
  options('collection-field', D.fields.map(f => ({ key: f.key, label: f.group + ' / ' + f.label })), state.field);
  options('schema-trait', D.fields.map(f => ({ key: f.key, label: f.group + ' / ' + f.label + (f.unit ? ' · ' + unitLabel(f.unit) : '') })), state.field);
  $('schema-summary').textContent = `${fullFieldCount} schema-defined traits · ${D.contract.selectedPredictors.length} selected pricing inputs · every listing schema validated`;
  $('schema-version').textContent = D.contract.schemaVersion + ' / ' + D.contract.modelDesignVersion;
  $('schema-readiness-note').textContent = `${D.meta.counts.eligible_model_inputs} rows admitted for training in this snapshot. Displayed prices are observations; a benchmark has not been fitted.`;
  $('collection-columns').children[2].textContent = 'All ' + fullFieldCount + ' traits';
  $('schema-trait').addEventListener('change', event => chooseField(event.target.value));
  $('schema-operator').addEventListener('change', renderRuleInputs);
  $('schema-pin-trait').addEventListener('click', () => togglePin(state.field));
  $('schema-model-only').addEventListener('change', event => { state.modelOnly = event.target.checked; refreshColumns(); });
  $('schema-add-rule').addEventListener('click', () => {
    const result = M.createRule(fieldsByKey.get(state.field), $('schema-operator').value, { min: $('schema-min').value, max: $('schema-max').value, value: $('schema-value').value });
    $('schema-filter-error').hidden = !result.error;
    if (result.error) { $('schema-filter-error').textContent = result.error; return; }
    if (!state.rules.some(rule => JSON.stringify(rule) === JSON.stringify(result.rule))) state.rules.push(result.rule);
    state.page = 0; render();
  });
  $('schema-clear-rules').addEventListener('click', () => { state.rules = []; state.page = 0; render(); });
  $('schema-compare-product').addEventListener('click', () => {
    if (!state.selected) return;
    if (state.compared.includes(state.selected)) state.compared = state.compared.filter(id => id !== state.selected);
    else if (state.compared.length < 4) state.compared.push(state.selected);
    renderComparison();
  });
  $('schema-clear-comparison').addEventListener('click', () => { state.compared = []; renderComparison(); });
  ['x', 'y', 'z'].forEach((name, i) => { options('collection-' + name, axes, state.axes[i]); $('collection-' + name).addEventListener('change', event => { state.axes[i] = event.target.value; render(); }); });
  for (const key of ['role', 'source', 'status']) $('collection-' + key).addEventListener('change', event => { state[key] = event.target.value; state.page = 0; render(); });
  for (const [id, key] of [['collection-group', 'group'], ['collection-columns', 'columns']]) $(id).addEventListener('change', event => { state[key] = key === 'columns' ? event.target.value === 'all' ? Infinity : Number(event.target.value) : event.target.value; refreshColumns(); });
  let searchTimer, traitTimer;
  $('collection-search').addEventListener('input', event => { clearTimeout(searchTimer); const value = event.target.value; searchTimer = setTimeout(() => { state.search = value; state.page = 0; render(); }, 150); });
  $('collection-trait-search').addEventListener('input', event => { clearTimeout(traitTimer); const value = event.target.value; traitTimer = setTimeout(() => { state.traitQuery = value; refreshColumns(); }, 150); });
  $('collection-field').addEventListener('change', event => chooseField(event.target.value));
  $('collection-prev').addEventListener('click', () => { state.page = Math.max(0, state.page - 1); renderTable(); });
  $('collection-next').addEventListener('click', () => { state.page = Math.min(Math.ceil(filtered.length / 25) - 1, state.page + 1); renderTable(); });
  $('collection-clear').addEventListener('click', () => { clearTimeout(searchTimer); state.search = ''; state.rules = []; $('collection-search').value = ''; for (const key of ['role', 'source', 'status']) { state[key] = 'all'; $('collection-' + key).value = 'all'; } state.page = 0; render(); });
  $('collection-orbit').addEventListener('click', () => { state.camera.eye = { x: 1.65, y: -1.7, z: 1.1 }; requestPlot(true); });
  $('collection-top').addEventListener('click', () => { state.camera.eye = { x: 0.05, y: 0.05, z: 2.7 }; requestPlot(true); });
  $('collection-snapshot-link').href = `https://huggingface.co/datasets/${D.meta.repository}/tree/${D.meta.revision}/${D.meta.snapshotPrefix}`;
  $('collection-provenance').textContent = `Snapshot ${D.meta.revision.slice(0, 8)} · ${D.meta.lastModified} · downloaded and checksum verified · source listings may refer to the same physical product`;
  renderRuleEditor(); render();
})();
