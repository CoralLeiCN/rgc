export const PRICING_FIELDS = [
  { key: "quantity.total_edible_weight_g", label: "Edible weight", family: "quantity" },
  { key: "composition.chocolate_type", label: "Chocolate type", family: "composition" },
  { key: "composition.recipe_class", label: "Recipe class", family: "composition" },
  { key: "composition.nuts_presence", label: "Nuts presence", family: "composition" },
  { key: "identity.retailer", label: "Retailer", family: "selling_context" },
] as const;

export type PricingKey = typeof PRICING_FIELDS[number]["key"];
export type PricingInput = Record<PricingKey, string | number> & { scope: "single_pack_chocolate_bar" };
export interface PriceAttribution {
  key: string; label: string; family: string; value: string | number;
  shapLog: number; percent: number; packGbp: number;
}
export interface PricingResult {
  modelId: string; runId: string; revision: string; fixture: true; releaseReady: false;
  priceBasis: "regular-consumer-price-1"; treeCount: number;
  unitGbp: number; packGbp: number; weightGrams: number;
  predictedLog: number; referenceLog: number; referenceUnitGbp: number;
  referencePackGbp: number; referencePercent: number;
  attributions: PriceAttribution[];
  families: { key: string; percent: number; packGbp: number }[];
  reconstructionError: number; reconciliationError: number;
  minimumLeafFamilies: number;
  explanationMethod: "exact_tree_path_dependent_shap";
  allocationMethod: "proportional_exponential_allocation";
  interval: null;
}
