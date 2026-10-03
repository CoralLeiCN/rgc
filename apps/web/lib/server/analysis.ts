import type {
  AnalysisResponse, BrandPricePosition,
  HistogramBrand, ObservedPriceGap, ObservedPriceSummary, PriceHistogramBin, Product,
} from "../contracts";
import { attribute, observedUnitPrice } from "./query";

export const HISTOGRAM_BINS = 20;
export const GAP_MINIMUM_PRICED = 20;
export const GAP_MINIMUM_DISTINCT = 5;
export const BRAND_MINIMUM_PRICED = 3;
const MAX_RANKED_BRANDS = 30;

type PricedListing = { price: number; brand: string | null };

function priceBinIndex(price: number, lower: number, upper: number): number {
  return Math.min(HISTOGRAM_BINS - 1, Math.floor((price - lower) / ((upper - lower) / HISTOGRAM_BINS)));
}

/** R-7 / linear interpolation quantile, with one equally weighted value per listing. */
export function quantile(sorted: readonly number[], probability: number): number {
  if (!sorted.length || probability < 0 || probability > 1) throw new Error("Invalid quantile input");
  const position = (sorted.length - 1) * probability;
  const lower = Math.floor(position), upper = Math.ceil(position);
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower);
}

function knownBrand(product: Product): string | null {
  const brand = attribute(product, "identity.brand");
  return brand.status === "known" && typeof brand.value === "string" && !brand.truncated ? brand.value.trim() || null : null;
}

function summarize(prices: number[]): ObservedPriceSummary | null {
  if (!prices.length) return null;
  const q1 = quantile(prices, 0.25), q3 = quantile(prices, 0.75);
  const lowerFence = q1 - 1.5 * (q3 - q1), upperFence = q3 + 1.5 * (q3 - q1);
  return {
    min: prices[0], max: prices[prices.length - 1], median: quantile(prices, 0.5), q1, q3, lowerFence, upperFence,
    lowOutlierCount: prices.filter((price) => price < lowerFence).length,
    highOutlierCount: prices.filter((price) => price > upperFence).length,
  };
}

function histogram(rows: PricedListing[], byBrand: Map<string, number[]>, summary: ObservedPriceSummary | null, requestedRange: "core" | "full"): AnalysisResponse["histogram"] {
  const fallback = requestedRange === "core" && summary !== null && summary.q1 === summary.q3;
  const range = fallback ? "full" : requestedRange;
  const lower = summary ? range === "core" ? Math.max(summary.min, summary.lowerFence) : summary.min : null;
  const upper = summary ? range === "core" ? Math.min(summary.max, summary.upperFence) : summary.max : null;
  const plotted = lower === null || upper === null ? [] : rows.filter((row) => row.price >= lower && row.price <= upper);
  const bounds = { range, rangeFallbackReason: fallback ? "The interquartile range is zero; showing the full observed price range." : null,
    lower, upper, plottedCount: plotted.length,
    belowRangeCount: lower === null ? 0 : rows.filter((row) => row.price < lower).length,
    aboveRangeCount: upper === null ? 0 : rows.filter((row) => row.price > upper).length };
  const leaders = [...byBrand].sort(([left, leftPrices], [right, rightPrices]) => rightPrices.length - leftPrices.length || left.localeCompare(right)).slice(0, 6);
  const groupByBrand = new Map(leaders.map(([brand], index) => [brand, `brand:${index}`]));
  const brands: HistogramBrand[] = leaders.map(([label], index) => ({ key: `brand:${index}`, label, count: 0, kind: "brand" }));
  const otherCount = rows.length - leaders.reduce((count, [, prices]) => count + prices.length, 0);
  if (otherCount > 0) brands.push({ key: "other", label: "Other / unknown", count: 0, kind: "other" });
  for (const row of plotted) {
    const key = row.brand === null ? "other" : groupByBrand.get(row.brand) ?? "other";
    brands.find((brand) => brand.key === key)!.count++;
  }
  if (!summary || lower === null || upper === null) return { ...bounds, status: "no_prices", binCount: HISTOGRAM_BINS, brands, bins: [] };
  if (lower === upper) return { ...bounds, status: "insufficient_spread", binCount: HISTOGRAM_BINS, brands, bins: [] };

  const width = (upper - lower) / HISTOGRAM_BINS;
  const bins: PriceHistogramBin[] = Array.from({ length: HISTOGRAM_BINS }, (_, index) => ({
    index, lower: lower + width * index,
    upper: index === HISTOGRAM_BINS - 1 ? upper : lower + width * (index + 1),
    upperInclusive: index === HISTOGRAM_BINS - 1, count: 0,
    brands: Object.fromEntries(brands.map((brand) => [brand.key, 0])),
  }));
  for (const row of plotted) {
    const index = priceBinIndex(row.price, lower, upper);
    const bin = bins[index];
    bin.count++;
    const brandKey = row.brand === null ? "other" : groupByBrand.get(row.brand) ?? "other";
    bin.brands[brandKey]++;
  }
  return { ...bounds, status: "ready", binCount: HISTOGRAM_BINS, brands, bins };
}

function gaps(bins: PriceHistogramBin[], pricedCount: number, distinctPriceCount: number): AnalysisResponse["gaps"] {
  const base = { minimumPricedCount: GAP_MINIMUM_PRICED, minimumDistinctPrices: GAP_MINIMUM_DISTINCT, distinctPriceCount, analyzedPricedCount: pricedCount };
  if (pricedCount < GAP_MINIMUM_PRICED) return {
    ...base, status: "insufficient_sample", reason: `At least ${GAP_MINIMUM_PRICED} priced listings in the displayed range are needed to describe gaps.`, items: [],
  };
  if (distinctPriceCount < GAP_MINIMUM_DISTINCT) return {
    ...base, status: "insufficient_spread", reason: `At least ${GAP_MINIMUM_DISTINCT} distinct observed prices in the displayed range are needed to describe gaps.`, items: [],
  };
  const occupied = bins.filter((bin) => bin.count > 0);
  const items: ObservedPriceGap[] = [];
  for (let index = 1; index < occupied.length; index++) {
    const left = occupied[index - 1], right = occupied[index];
    if (right.index - left.index > 1) items.push({
      lower: bins[left.index + 1].lower, upper: right.lower, upperInclusive: false,
      emptyBinCount: right.index - left.index - 1, leftBinIndex: left.index, rightBinIndex: right.index,
      leftListingCount: left.count, rightListingCount: right.count,
    });
  }
  items.sort((left, right) => right.emptyBinCount - left.emptyBinCount || left.lower - right.lower);
  return { ...base, status: "ready", reason: null, items };
}

function rankBrands(byBrand: Map<string, number[]>, summary: ObservedPriceSummary | null): AnalysisResponse["brandAnalysis"] {
  const qualified: BrandPricePosition[] = [];
  if (summary) for (const [brand, prices] of byBrand) {
    if (prices.length < BRAND_MINIMUM_PRICED) continue;
    const median = quantile([...prices].sort((left, right) => left - right), 0.5);
    qualified.push({ brand, pricedCount: prices.length, median, premiumPercent: (median / summary.median - 1) * 100,
      lowOutlierCount: prices.filter((price) => price < summary.lowerFence).length,
      highOutlierCount: prices.filter((price) => price > summary.upperFence).length });
  }
  qualified.sort((left, right) => right.median - left.median || right.pricedCount - left.pricedCount || left.brand.localeCompare(right.brand));
  return {
    status: qualified.length ? "ready" : "insufficient_sample",
    reason: qualified.length ? null : `No named brand has at least ${BRAND_MINIMUM_PRICED} priced listings in this cohort.`,
    minimumPricedCount: BRAND_MINIMUM_PRICED, totalNamedBrands: byBrand.size,
    eligibleBrandCount: qualified.length, excludedBrandCount: byBrand.size - qualified.length,
    truncatedBrandCount: Math.max(0, qualified.length - MAX_RANKED_BRANDS), ranking: qualified.slice(0, MAX_RANKED_BRANDS),
  };
}

export function analyzePrices(products: Product[], range: "core" | "full" = "core"): AnalysisResponse {
  const rows: PricedListing[] = [];
  const byBrand = new Map<string, number[]>();
  for (const product of products) {
    const price = observedUnitPrice(product);
    if (price === null) continue;
    const brand = knownBrand(product);
    rows.push({ price, brand });
    if (brand !== null) {
      const prices = byBrand.get(brand);
      if (prices) prices.push(price); else byBrand.set(brand, [price]);
    }
  }
  const prices = rows.map((row) => row.price).sort((left, right) => left - right);
  const summary = summarize(prices);
  const distribution = histogram(rows, byBrand, summary, range);
  const visiblePrices = prices.filter((price) => distribution.lower !== null && distribution.upper !== null && price >= distribution.lower && price <= distribution.upper);
  return {
    totalMatched: products.length, pricedCount: rows.length, excludedPriceCount: products.length - rows.length,
    unknownBrandPricedCount: rows.filter((row) => row.brand === null).length, summary, histogram: distribution,
    gaps: gaps(distribution.bins, visiblePrices.length, new Set(visiblePrices).size), brandAnalysis: rankBrands(byBrand, summary),
    method: {
      unit: "GBP_per_100g",
      observationBasis: "One latest dated observation per source listing; positive displayed GBP per 100g with known same-observation edible weight and no latest-price conflict. Undated observations rank last. Review status is unchanged.",
      quantileMethod: "R-7 linear interpolation over equally weighted source listings; no physical-product deduplication.",
      outlierMethod: "Prices strictly outside full-cohort Q1 - 1.5 × IQR and Q3 + 1.5 × IQR. These are descriptive price outliers, not model residuals.",
      gapMeaning: "Interior empty runs in 20 equal-width bins of the displayed range, bounded by occupied bins. Core range clips to full-cohort Tukey fences; zero IQR falls back to full range. Gap readiness counts only displayed listings. Bracket counts refer to adjacent occupied bins. Observed absence is not evidence of demand or a commercial opportunity.",
      brandMeaning: "Named brands ranked by median observed unit price within this filtered cohort, with at least 3 priced listings. Premium is relative to the full priced-cohort median. Higher price positioning does not establish sales performance, value, causality or like-for-like comparability.",
    },
  };
}
