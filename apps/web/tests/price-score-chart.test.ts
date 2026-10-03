import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { transformSync } from "esbuild";
import { handleAnalysis } from "../lib/server/handlers";
import type { AnalysisResponse, Coverage, Snapshot } from "../lib/contracts";
import { money, number } from "../lib/client/display";
import { familyColor, familyLabel } from "../lib/client/families";
import { buildTraitDrilldown } from "../lib/client/trait-drilldown";

const { fields } = JSON.parse(readFileSync(new URL("../snapshot/index.json", import.meta.url), "utf8")) as Snapshot;

type Node = { type: unknown; props: Record<string, unknown> };
const jsx = (type: unknown, props: Record<string, unknown>): Node => ({ type, props });
const module = { exports: {} as Record<string, unknown> };
vm.runInNewContext(transformSync(readFileSync(path.join(process.cwd(), "components/PriceDistribution.tsx"), "utf8"), { loader: "tsx", format: "cjs", target: "es2022", jsx: "automatic" }).code, {
  module, exports: module.exports,
  require(specifier: string) {
    if (specifier === "react") return { useState: () => [null, () => {}] };
    if (specifier === "react/jsx-runtime") return { jsx, jsxs: jsx, Fragment: "fragment" };
    if (specifier === "../lib/client/display") return { money, number };
    if (specifier === "../lib/client/families") return { familyColor, familyLabel };
    if (specifier === "../lib/client/trait-drilldown") return { buildTraitDrilldown };
    if (specifier === "./Icons") return { ErrorState: "ErrorState", Icon: "Icon", Loading: "Loading" };
    if (specifier === "./HelpTip") return { HelpTip: "HelpTip" };
    throw new Error(`Unexpected chart import: ${specifier}`);
  }
});
const chart = module.exports.PriceDistribution as (props: Record<string, unknown>) => Node;
function descendants(value: unknown): Node[] {
  if (Array.isArray(value)) return value.flatMap(descendants);
  if (!value || typeof value !== "object" || !("props" in value)) return [];
  const node = value as Node;
  return [node, ...descendants(node.props.children)];
}
function render(data: AnalysisResponse | null, props: Record<string, unknown> = {}) {
  return descendants(chart({ data, loading: false, error: null, onRetry() {}, activeFamily: null, onClearFamily() {}, activeGap: null, range: "core", onRange() {}, ...props }));
}
function textOf(value: unknown): string {
  if (Array.isArray(value)) return value.map(textOf).join("");
  if (value && typeof value === "object" && "props" in value) return textOf((value as Node).props.children);
  return typeof value === "string" || typeof value === "number" ? String(value) : "";
}
const fixture = async (query = "scoreMode=demo") => await (await handleAnalysis(new Request(`http://localhost/api/analysis?${query}`))).json() as AnalysisResponse;
const marker = (nodes: Node[]) => nodes.find(node => node.props.className === "configured-product-marker");
function barGeometry(nodes: Node[]) {
  return nodes.filter(node => typeof node.props.className === "string" && node.props.className.startsWith("distribution-bin "))
    .map(node => descendants(node).filter(child => child.type === "rect").map(child => ({
      x: child.props.x, y: child.props.y, width: child.props.width, height: child.props.height, fill: child.props.fill,
    })));
}

test("production chart heights encode demo scores even when listing counts are much larger", async () => {
  const data = await (await handleAnalysis(new Request("http://localhost/api/analysis?scoreMode=demo"))).json() as AnalysisResponse;
  const index = data.histogram.bins.findIndex(bin => bin.count > 0);
  data.histogram.bins[index].count = 1000;
  const firstFamily = data.demoScores!.families[0];
  data.demoScores!.bins[index] = { index, score: 50, families: Object.fromEntries(data.demoScores!.families.map(family => [family, family === firstFamily ? 50 : 0])) };
  const nodes = render(data);
  const bin = nodes.filter(node => typeof node.props.className === "string" && node.props.className.startsWith("distribution-bin "))[index];
  const scoreRects = descendants(bin).filter(node => node.type === "rect" && node.props.fill !== "transparent");
  assert.equal(scoreRects.length, 1);
  assert.equal(scoreRects[0].props.height, 143, "A score of 50 fills half the 286px scoring axis, independent of 1000 listings");
  assert.equal(scoreRects[0].props.y, 183);
  assert.ok(nodes.some(node => node.type === "text" && node.props.children === "PRICING SCORE · DEMO"));
  assert.ok(nodes.some(node => node.type === "text" && node.props.children === "PRICING · £ /100g"));
  assert.ok(nodes.some(node => node.type === "span" && node.props.children === "DEMO SCORES · FICTIONAL"));
});

test("the score chart never falls back to drawing listing counts as scores", async () => {
  const data = await (await handleAnalysis(new Request("http://localhost/api/analysis"))).json() as AnalysisResponse;
  assert.ok(data.pricedCount > 0);
  const nodes = render(data);
  assert.ok(!nodes.some(node => node.type === "svg"));
  assert.ok(nodes.some(node => node.type === "h3" && node.props.children === "Demo scores unavailable."));
});

test("configured product marker uses actual price and manual score at both endpoints and midpoint", async () => {
  const data = await fixture();
  const lower = data.histogram.lower!, upper = data.histogram.upper!;
  const cases = [
    { price: lower, score: 0, x: 66, y: 326 },
    { price: (lower + upper) / 2, score: 50, x: 481, y: 183 },
    { price: upper, score: 100, x: 896, y: 40 },
  ];
  for (const value of cases) {
    const nodes = render(data, { configuredProduct: { name: "Configured chocolate", price: value.price, score: value.score } });
    const overlay = marker(nodes);
    assert.ok(overlay);
    const point = descendants(overlay).find(node => node.props.className === "configured-product-point");
    assert.ok(point);
    const [x, y] = String(point.props.transform).slice("translate(".length, -1).split(" ").map(Number);
    assert.ok(Math.abs(x - value.x) < 1e-9);
    assert.ok(Math.abs(y - value.y) < 1e-9);
    assert.equal(descendants(overlay).filter(node => node.props.className === "configured-product-crosshair").length, 2);
    assert.match(String(overlay.props["aria-label"]), /Configured chocolate/);
    assert.match(String(overlay.props["aria-label"]), /manual demo score/);
    assert.ok(descendants(overlay).some(node => node.type === "text" && node.props.children === "YOUR PRODUCT · DEMO"));
    assert.ok(nodes.some(node => node.props.className === "configured-product-numbers" && textOf(node).includes(money(value.price))));
  }
});

test("out-of-range configured prices are never clamped and can request the full observed range", async () => {
  const data = await fixture();
  const requested: string[] = [];
  for (const [price, direction] of [[data.histogram.lower! / 2, "Below"], [data.histogram.upper! + 1, "Above"]] as const) {
    const nodes = render(data, { configuredProduct: { name: "Outside preview", price, score: 70 }, onRange: (range: string) => requested.push(range) });
    assert.equal(marker(nodes), undefined);
    const status = nodes.find(node => node.props.className === "configured-product-status");
    assert.ok(textOf(status).startsWith(direction));
    assert.match(textOf(status), /not plotted/);
    const button = nodes.find(node => node.props.className === "text-button configured-product-full-range");
    assert.ok(button);
    (button.props.onClick as () => void)();
  }
  assert.deepEqual(requested, ["full", "full"]);
  const full = await fixture("scoreMode=demo&range=full");
  const nodes = render(full, { range: "full", configuredProduct: { name: "Beyond observed prices", price: full.histogram.upper! + 1, score: 70 } });
  assert.equal(marker(nodes), undefined);
  assert.match(textOf(nodes.find(node => node.props.className === "configured-product-status")), /Above the full observed price range/);
  assert.equal(nodes.some(node => node.props.className === "text-button configured-product-full-range"), false);
});

test("configured position is hidden during loading, errors and unavailable price bands", async () => {
  const data = await fixture();
  const configuredProduct = { name: "Waiting preview", price: data.histogram.lower!, score: 50 };
  const states = [
    { props: { configuredProduct, loading: true }, message: /Waiting for the current price range/ },
    { props: { configuredProduct, error: "Unable to load" }, message: /Price analysis is unavailable/ },
  ];
  for (const { props, message } of states) {
    const nodes = render(data, props);
    assert.equal(marker(nodes), undefined, "Retained response data must not create a stale marker");
    assert.match(textOf(nodes.find(node => node.props.className === "configured-product-status")), message);
  }
  const empty = await fixture("scoreMode=demo&search=no-such-preview-product-123456789");
  const nodes = render(empty, { configuredProduct });
  assert.equal(marker(nodes), undefined);
  assert.match(textOf(nodes.find(node => node.props.className === "configured-product-status")), /Price bands are unavailable/);
  const noScores = await fixture("");
  assert.equal(marker(render(noScores, { configuredProduct })), undefined);
});

test("invalid marker numbers never produce SVG coordinates or misleading numeric summaries", async () => {
  const data = await fixture();
  const invalid = [
    ...[0, -1, Number.NaN, Number.POSITIVE_INFINITY].map(price => ({ name: "Invalid price", price, score: 50 })),
    ...[-1, 101, Number.NaN, Number.POSITIVE_INFINITY].map(score => ({ name: "Invalid score", price: data.histogram.lower!, score })),
  ];
  for (const configuredProduct of invalid) {
    const nodes = render(data, { configuredProduct });
    assert.equal(marker(nodes), undefined);
    assert.equal(nodes.some(node => node.props.className === "configured-product-numbers"), false);
    assert.match(textOf(nodes.find(node => node.props.className === "configured-product-status")), /positive price.*0 to 100/);
  }
});

test("manual marker can preview an empty band without changing observed data, bar heights or gap counts", async () => {
  const data = await fixture();
  const empty = data.histogram.bins.find(bin => bin.count === 0);
  assert.ok(empty);
  const before = JSON.stringify(data);
  const baseline = render(data, { activeGap: 0 });
  const nodes = render(data, { activeGap: 0, configuredProduct: { name: "Your new product", price: (empty.lower + empty.upper) / 2, score: 65 } });
  assert.ok(marker(nodes));
  assert.deepEqual(barGeometry(nodes), barGeometry(baseline));
  assert.equal(JSON.stringify(data), before);
  assert.match(textOf(nodes.find(node => node.props.className === "configured-product-status")), /0 observed listings/);
  assert.ok(nodes.some(node => node.props.className === "configured-product-model-note" && textOf(node).includes("no pricing model connected")));
  assert.equal(data.histogram.bins[empty.index].count, 0);
  assert.equal(nodes.filter(node => node.props.className === "price-gap-band").length, baseline.filter(node => node.props.className === "price-gap-band").length);
});

test("family legend highlights independently of drilldown and preserves total score geometry", async () => {
  const data = await fixture();
  const family = data.demoScores!.families[0];
  const focuses: (string | null)[] = [];
  const onHighlight = (value: string | null) => focuses.push(value);
  const ordinary = render(data, { onHighlight });
  const button = ordinary.find(node => node.props.className === "distribution-legend-button" && textOf(node) === familyLabel(family));
  assert.ok(button);
  assert.equal(button.type, "button");
  assert.equal(button.props["aria-pressed"], false);
  assert.equal(button.props.disabled, false);
  (button.props.onClick as () => void)();
  const focused = render(data, { onHighlight, highlightKey: family });
  const active = focused.find(node => node.props.className === "distribution-legend-button" && textOf(node) === familyLabel(family));
  assert.ok(active);
  assert.equal(active.props["aria-pressed"], true);
  (active.props.onClick as () => void)();
  assert.deepEqual(focuses, [family, null]);
  assert.deepEqual(barGeometry(focused), barGeometry(ordinary));
  assert.ok(focused.some(node => node.type === "text" && node.props.children === "PRICING SCORE · DEMO"));
});

test("Identity and Composition drilldowns replace family colours with top ten traits plus remaining traits", async () => {
  const data = await fixture();
  const before = JSON.stringify(data);
  for (const [family, count] of [["identity", 15], ["composition", 20]] as const) {
    const members = fields.filter(field => field.group === family);
    assert.equal(members.length, count);
    const coverage: Record<string, Coverage> = Object.fromEntries(members.map((field, index) => [field.key, { known: index, unknown: count - index, conflict: 0, not_applicable: 0, reviewed: 0, total: count }]));
    const nodes = render(data, { fields, coverage, activeFamily: family, activeGap: 0 });
    const expected = members.slice().reverse().slice(0, 10);
    const legend = nodes.filter(node => node.props.className === "distribution-legend-button");
    assert.deepEqual(legend.map(textOf), [...expected.map(field => field.label), "Other traits"]);
    assert.ok(nodes.some(node => node.type === "text" && node.props.children === "FAMILY SCORE · DEMO"));
    const overview = render(data, { activeGap: 0 });
    const gap = (items: Node[]) => items.filter(node => node.props.className === "price-gap-band").map(node => descendants(node).find(item => item.type === "rect")!.props);
    assert.deepEqual(gap(nodes), gap(overview), "Price gap X coordinates do not change with a trait drilldown");
    const axis = nodes.find(node => node.type === "svg")!;
    const scoreMax = Number(String(axis.props["aria-label"]).match(/from 0 to (\d+) on Y/)![1]);
    assert.ok(scoreMax >= 10 && scoreMax < 100);
    const chartBins = nodes.filter(node => typeof node.props.className === "string" && node.props.className.startsWith("distribution-bin "));
    for (const [index, bin] of chartBins.entries()) {
      const rects = descendants(bin).filter(node => node.type === "rect" && node.props.fill !== "transparent");
      const height = rects.reduce((sum, rect) => sum + Number(rect.props.height), 0);
      const parent = data.demoScores!.bins[index];
      assert.ok(Math.abs(height - (parent.score === null ? 0 : parent.families[family]) / scoreMax * 286) < 1e-9);
      assert.match(String(bin.props["aria-label"]), new RegExp(`${data.histogram.bins[index].count} listings`));
      if (data.histogram.bins[index].count === 0) assert.equal(rects.length, 0, "Empty bands never receive a synthetic family score");
    }
    assert.match(textOf(nodes.find(node => node.props.className === "distribution-drilldown")), new RegExp(`10 traits \\+ ${count - 10} in Other traits`));
    assert.equal(JSON.stringify(data), before, "Drilldown never changes the API's observed analysis or original synthetic totals");
  }
});

test("family score axis uses a bounded subtotal domain and leaves the overview at zero to one hundred", async () => {
  const data = await fixture();
  for (const bin of data.demoScores!.bins) if (bin.score !== null) bin.families.identity = 13;
  const nodes = render(data, { fields, activeFamily: "identity" });
  assert.match(String(nodes.find(node => node.type === "svg")?.props["aria-label"]), /from 0 to 20 on Y/);
  const first = nodes.find(node => typeof node.props.className === "string" && node.props.className.startsWith("distribution-bin "))!;
  const height = descendants(first).filter(node => node.type === "rect" && node.props.fill !== "transparent").reduce((sum, node) => sum + Number(node.props.height), 0);
  assert.ok(Math.abs(height - 13 / 20 * 286) < 1e-9);
  for (const bin of data.demoScores!.bins) bin.families.identity = 0;
  assert.match(String(render(data, { fields, activeFamily: "identity" }).find(node => node.type === "svg")?.props["aria-label"]), /from 0 to 10 on Y/);
  assert.match(String(render(data).find(node => node.type === "svg")?.props["aria-label"]), /from 0 to 100 on Y/);
});

test("trait legend toggles only its own highlight; returning to all families restores overview geometry", async () => {
  const data = await fixture();
  const highlights: (string | null)[] = [];
  let clears = 0;
  const props = { fields, activeFamily: "identity", onHighlight: (key: string | null) => highlights.push(key), onClearFamily: () => { clears++; } };
  const normal = render(data, props);
  const breakdown = buildTraitDrilldown(data, fields, undefined, "identity")!;
  const key = breakdown.series[0].key, label = breakdown.series[0].label;
  const first = normal.find(node => node.props.className === "distribution-legend-button" && textOf(node) === label)!;
  assert.equal(first.props["aria-pressed"], false);
  (first.props.onClick as () => void)();
  const highlighted = render(data, { ...props, highlightKey: key });
  const pressed = highlighted.find(node => node.props.className === "distribution-legend-button" && textOf(node) === label)!;
  assert.equal(pressed.props["aria-pressed"], true);
  (pressed.props.onClick as () => void)();
  assert.deepEqual(highlights, [key, null]);
  assert.equal(clears, 0, "Legend interaction cannot clear the selected family");
  assert.deepEqual(barGeometry(highlighted), barGeometry(normal));
  assert.ok(highlighted.some(node => node.type === "rect" && node.props.fillOpacity === .18));
  const staleHighlight = render(data, { ...props, highlightKey: "composition" });
  assert.ok(!staleHighlight.some(node => node.type === "rect" && node.props.fillOpacity === .18), "A stale family highlight never dims every trait");
  const reset = normal.find(node => node.props.className === "text-button clear-family")!;
  (reset.props.onClick as () => void)();
  assert.equal(clears, 1);
  assert.deepEqual(barGeometry(render(data, { fields, activeFamily: null, highlightKey: key })), barGeometry(render(data)));
});

test("family drilldown shows configured price exactly without projecting its total score onto the family axis", async () => {
  const data = await fixture();
  let clears = 0;
  for (const [price, x] of [[data.histogram.lower!, 66], [(data.histogram.lower! + data.histogram.upper!) / 2, 481], [data.histogram.upper!, 896]]) {
    const nodes = render(data, { fields, activeFamily: "identity", configuredProduct: { name: "Your chocolate", price, score: 95 }, onClearFamily: () => { clears++; } });
    assert.equal(marker(nodes), undefined);
    const guide = nodes.find(node => node.props.className === "configured-product-price-guide");
    assert.ok(guide);
    const lines = descendants(guide).filter(node => node.type === "line");
    assert.equal(lines.length, 1);
    assert.ok(Math.abs(Number(lines[0].props.x1) - x) < 1e-9);
    assert.equal(lines[0].props.x1, lines[0].props.x2);
    assert.equal(lines[0].props.y1, 40);
    assert.equal(lines[0].props.y2, 326);
    assert.match(textOf(nodes.find(node => node.props.className === "configured-product-status")), /Return to All families to see your total demo score position/);
    assert.match(String(guide.props["aria-label"]), /no family score assigned/);
    const button = nodes.find(node => node.props.className === "text-button configured-product-all-families")!;
    (button.props.onClick as () => void)();
  }
  assert.equal(clears, 3);
  for (const props of [
    { configuredProduct: { name: "Below", price: data.histogram.lower! / 2, score: 50 } },
    { configuredProduct: { name: "Above", price: data.histogram.upper! + 1, score: 50 } },
    { configuredProduct: { name: "Loading", price: data.histogram.lower!, score: 50 }, loading: true },
    { configuredProduct: { name: "Error", price: data.histogram.lower!, score: 50 }, error: "Unavailable" },
  ]) {
    const nodes = render(data, { fields, activeFamily: "identity", ...props });
    assert.equal(marker(nodes), undefined);
    assert.ok(!nodes.some(node => node.props.className === "configured-product-price-guide"));
  }
});

test("missing family metadata never silently presents total bars as family scores", async () => {
  const data = await fixture();
  const nodes = render(data, { activeFamily: "identity" });
  assert.ok(!nodes.some(node => node.type === "svg"));
  assert.ok(nodes.some(node => node.type === "h3" && node.props.children === "Family trait breakdown unavailable."));
  const fallback = render(data, { fields, activeFamily: "identity" });
  assert.match(textOf(fallback.find(node => node.props.className === "distribution-drilldown")), /Alphabetical trait order · coverage unavailable/);
});
