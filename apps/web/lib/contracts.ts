/** Public API v1. Snapshot schemas remain owned by the Python processing layer. */
export type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
export type AttributeState = "known" | "unknown" | "conflict" | "not_applicable";
export type ReviewStatus = "unreviewed" | "reviewed" | "needs_review";
export type SourceRole = "brand" | "retail" | "unknown";
export interface Attribute {
  value: JsonValue; status: AttributeState; unit: string | null;
  scope?: string | null; qualifier?: string | null; reviewStatus: ReviewStatus; truncated?: boolean;
}
export interface PriceSummary {
  observation_id: string; observed_at: string | null; currency: string | null;
  displayed_price: number | null; displayed_price_per_100g_gbp: number | null;
  total_edible_weight_g: number | null; quantity_status: string | null; model_eligible: boolean | null;
}
export interface Product {
  id: string; name: string; brand: string | null; retailer: string | null;
  source: string; role: SourceRole; reviewStatus: ReviewStatus;
  attributes: Record<string, Attribute>; known: number; conflicts: number;
  prices: PriceSummary[]; latestPriceConflict: boolean; sourceListingIds: string[];
}
export interface FieldDefinition {
  key: string; label: string; group: string; known: number; conflicts: number;
  numeric: boolean; numericKnown: number; type: string; unit: string | null;
  scope: string | null; description: string; qualifier: string;
  minimum: number | null; maximum: number | null; allowedValues: (string | number | boolean)[];
  modelRole: string | null; modelSelected: boolean; modelDefinition: JsonValue;
}
export interface SnapshotMeta {
  repository: string; revision: string; datasetVersion: string; sourceDatasetVersion: string;
  lastModified: string | null; schemaVersion: string; modelDesignVersion: string;
  schemaValidatedListings: number; contractHashes: Record<string, string>; snapshotPrefix: string;
  releaseReady: boolean; counts: Record<string, number>; sourceRoles: Record<string, number>;
  exclusionCounts: Record<string, number>; verifiedFiles: string[]; manifestSha256: string;
  omittedHeavyFiles: string[]; interpretation: string;
}
export interface SchemaContract {
  schemaVersion: string; modelDesignVersion: string; category: string; market: string;
  groups: string[]; states: AttributeState[]; reviewStatuses: ReviewStatus[];
  modelTarget: Record<string, JsonValue>; selectedPredictors: string[];
}
export interface Snapshot { meta: SnapshotMeta; contract: SchemaContract; fields: FieldDefinition[]; products: Product[]; }
export interface Axis { key: string; label: string; unit: string | null; }
export interface SchemaResponse {
  meta: SnapshotMeta; contract: SchemaContract; fields: FieldDefinition[];
  sources: { key: string; count: number }[]; axes: Axis[];
}
export type RuleOperator = AttributeState | "reviewed" | "range" | "equals";
export interface TraitRule { field: string; operator: RuleOperator; min?: number | null; max?: number | null; value?: string | number | boolean; }
export interface CohortQuery {
  search?: string; source?: string; role?: "all" | SourceRole;
  status?: "all" | "priced" | "unpriced" | "conflicts"; rules?: TraitRule[];
}
export interface Coverage {
  known: number; unknown: number; conflict: number; not_applicable: number; reviewed: number; total: number;
}
export interface ProductsResponse {
  products: Product[]; total: number; page: number; pageSize: number; totalPages: number;
  coverage: Record<string, Coverage>;
}
export interface EvidenceAttribute {
  value: JsonValue; status: AttributeState; unit: string | null; scope: string | null;
  qualifier: string | null; review_status: ReviewStatus; method: JsonValue; evidence: JsonValue;
}
export interface Evidence { attributes: Record<string, EvidenceAttribute>; prices: Record<string, JsonValue>[]; }
export interface ProductResponse { product: Product; evidence: Evidence; }
export interface Point {
  id: string; name: string; source: string; role: SourceRole; x: number; y: number; z: number;
  /** Trait-state counts across every schema field in each flat family, not model importance. */
  familyCoverage: Record<string, Coverage>;
}
export interface PointsResponse {
  points: Point[]; axes: [Axis, Axis, Axis]; totalMatched: number; completeCount: number;
  excludedCount: number; sampled: boolean; limit: number;
}
export interface CompareResponse { products: Product[]; }
export interface ErrorResponse { error: { code: string; message: string }; }

/** Descriptive observed-price analysis, with one usable latest observation per listing. */
export interface FamilyEvidenceStates {
  complete: number; partial: number; none: number; conflict: number; notApplicable: number;
}
export interface HistogramBrand { key: string; label: string; count: number; kind: "brand" | "other"; }
export interface PriceHistogramBin {
  index: number; lower: number; upper: number; upperInclusive: boolean; count: number;
  brands: Record<string, number>; familyStates: Record<string, FamilyEvidenceStates>;
}
export interface ObservedPriceSummary {
  min: number; max: number; median: number; q1: number; q3: number;
  lowerFence: number; upperFence: number; lowOutlierCount: number; highOutlierCount: number;
}
export interface ObservedPriceGap {
  lower: number; upper: number; upperInclusive: false; emptyBinCount: number;
  leftBinIndex: number; rightBinIndex: number; leftListingCount: number; rightListingCount: number;
}
export interface BrandPricePosition {
  brand: string; pricedCount: number; median: number; premiumPercent: number;
  lowOutlierCount: number; highOutlierCount: number;
}
export interface DemoScoreBin { index: number; score: number | null; families: Record<string, number>; }
export interface DemoScores {
  label: string; definition: string; version: "demo-score-1"; range: [0, 100];
  families: string[]; bins: DemoScoreBin[];
}
export interface AnalysisResponse {
  totalMatched: number; pricedCount: number; excludedPriceCount: number; unknownBrandPricedCount: number;
  summary: ObservedPriceSummary | null;
  histogram: {
    status: "ready" | "no_prices" | "insufficient_spread"; binCount: number;
    range: "core" | "full"; rangeFallbackReason: string | null; lower: number | null; upper: number | null;
    plottedCount: number; belowRangeCount: number; aboveRangeCount: number;
    brands: HistogramBrand[]; bins: PriceHistogramBin[];
  };
  gaps: {
    status: "ready" | "insufficient_sample" | "insufficient_spread"; reason: string | null;
    minimumPricedCount: number; minimumDistinctPrices: number; distinctPriceCount: number; analyzedPricedCount: number;
    items: ObservedPriceGap[];
  };
  brandAnalysis: {
    status: "ready" | "insufficient_sample"; reason: string | null; minimumPricedCount: number;
    totalNamedBrands: number; eligibleBrandCount: number; excludedBrandCount: number; truncatedBrandCount: number;
    ranking: BrandPricePosition[];
  };
  method: {
    unit: "GBP_per_100g"; observationBasis: string; quantileMethod: string;
    outlierMethod: string; gapMeaning: string; brandMeaning: string;
  };
  /** Explicitly requested synthetic illustration; omitted from ordinary observed-data responses. */
  demoScores?: DemoScores;
}

export interface TerrainDimension {
  key: string; label: string; fields: FieldDefinition[];
}
export interface TerrainResponse {
  color: TerrainDimension;
  z: TerrainDimension & { unit: string | null };
  rows: { id: string; name: string; price: number; score: number; z: number; categories: Record<string, number> }[];
  /** Number of complete in-range listings containing each category, before sampling. */
  categories: { key: string; label: string; count: number }[];
  totalMatched: number; pricedCount: number; completeCount: number; excludedCount: number;
  sampled: boolean; limit: number; priceRange: [number, number] | null;
  range: "core" | "full"; requestedRange: "core" | "full"; rangeFallbackReason: string | null;
  belowRangeCount: number; aboveRangeCount: number;
  /** Missing counts are within the displayed price range and may overlap. */
  missingScoreCount: number; missingZCount: number;
  scoreDefinition: string; scoreVersion: "trait-demo-1";
}
