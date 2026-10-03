import { PRICING_FIELDS, type PricingInput, type PricingResult } from "../pricing-contract";

export interface FixtureModel {
  model_id: string; tree_count: number; booster: string; booster_sha256: string;
  identity: { fixture: boolean }; release_ready: boolean;
  contract: { target: { price_basis_contract_version: string } };
  preprocessing: {
    features: string[]; columns: string[]; categories: Record<string, string[]>;
    ranges: Record<string, [number, number]>; combinations: string[][];
  };
  leaf_support: Record<string, Record<string, number>>;
}
interface Tree {
  feature: number[]; threshold: number[]; decision: number[];
  left: number[]; right: number[]; leaf: number[]; leafCount: number[];
  count: number[]; boundaries: number[]; categories: number[];
}
export interface PricingEngine { model: FixtureModel; trees: Tree[]; }

/** This reader admits only the pinned five-feature, non-linear v4 fixture. */
export function createPricingEngine(model: FixtureModel): PricingEngine {
  const keys = PRICING_FIELDS.map(field => field.key);
  if (model.model_id !== "lightgbm_without_brand" || model.identity.fixture !== true || model.release_ready !== false
      || model.contract.target.price_basis_contract_version !== "regular-consumer-price-1"
      || JSON.stringify(model.preprocessing.columns) !== JSON.stringify(keys)
      || JSON.stringify(model.preprocessing.features) !== JSON.stringify(keys)) throw new Error("Unsupported pricing model");
  const header = model.booster.split("\n\n")[0];
  if (!header.includes("version=v4\n") || !header.includes("objective=regression\n")
      || !header.includes("num_class=1\n") || !header.includes("num_tree_per_iteration=1\n")) throw new Error("Unsupported booster");
  const blocks = model.booster.split(/\nTree=\d+\n/).slice(1);
  if (blocks.length !== model.tree_count) throw new Error("Frozen tree count mismatch");
  const trees = blocks.map(block => {
    const fields = Object.fromEntries(block.split("\n\n")[0].split("\n").map(line => {
      const offset = line.indexOf("="); return [line.slice(0, offset), line.slice(offset + 1)];
    }));
    if (fields.is_linear !== "0") throw new Error("Linear leaves are unsupported");
    const array = (key: string) => fields[key]?.trim() ? fields[key].trim().split(/\s+/).map(Number) : [];
    const tree: Tree = { feature: array("split_feature"), threshold: array("threshold"), decision: array("decision_type"),
      left: array("left_child"), right: array("right_child"), leaf: array("leaf_value"), leafCount: array("leaf_count"),
      count: array("internal_count"), boundaries: array("cat_boundaries"), categories: array("cat_threshold") };
    if (tree.leaf.length !== Number(fields.num_leaves) || tree.feature.length !== tree.leaf.length - 1
        || tree.leafCount.length !== tree.leaf.length || tree.leaf.some(v => !Number.isFinite(v))) throw new Error("Malformed booster tree");
    return tree;
  });
  return { model, trees };
}

export function encodePricingInput(input: unknown, model: FixtureModel): { values: PricingInput; encoded: number[] } {
  if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("Supply product inputs.");
  const values = input as PricingInput;
  const keys = PRICING_FIELDS.map(field => field.key);
  if (values.scope !== "single_pack_chocolate_bar") throw new Error("Confirm this is one standard chocolate bar pack.");
  if (Object.keys(values).some(key => key !== "scope" && !keys.includes(key as typeof keys[number]))) throw new Error("Only the five modeled inputs and product scope are accepted.");
  const encoded = PRICING_FIELDS.map(field => {
    const value = values[field.key];
    if (field.key === "quantity.total_edible_weight_g") {
      const [low, high] = model.preprocessing.ranges[field.key];
      if (typeof value !== "number" || !Number.isFinite(value) || value < low || value > high) throw new Error(`Edible weight must be between ${low} and ${high} g.`);
      return Math.log(value);
    }
    const levels = model.preprocessing.categories[field.key];
    if (typeof value !== "string" || !levels.includes(value)) throw new Error(`Choose a supported ${field.label.toLowerCase()}.`);
    return levels.indexOf(value);
  });
  const combination = [values["identity.retailer"], values["composition.chocolate_type"], values["composition.recipe_class"]];
  if (!model.preprocessing.combinations.some(item => item.every((value, i) => value === combination[i]))) throw new Error("Unsupported retailer, type and recipe combination.");
  return { values, encoded };
}

function child(tree: Tree, node: number, value: number): number {
  let left: boolean;
  if (tree.decision[node] & 1) {
    const category = Math.trunc(value), group = tree.threshold[node];
    const begin = tree.boundaries[group], end = tree.boundaries[group + 1];
    const word = category >>> 5;
    left = category >= 0 && word < end - begin && Boolean((tree.categories[begin + word] >>> (category & 31)) & 1);
  } else {
    left = ((tree.decision[node] >> 2) & 3) === 1 && Math.abs(value) <= 1e-35
      ? Boolean(tree.decision[node] & 2) : value <= tree.threshold[node];
  }
  return left ? tree.left[node] : tree.right[node];
}

const count = (tree: Tree, node: number) => node < 0 ? tree.leafCount[~node] : tree.count[node];

/** Exact subset enumeration of the stored-path game (32 coalitions for five fields).
 * Unknown splits follow child observation counts, including repeated features.
 * Verified against LightGBM 4.6.0 native pred_contrib; no supplied background.
 */
function expected(tree: Tree, node: number, row: number[], coalition: number): number {
  if (node < 0) return tree.leaf[~node];
  const feature = tree.feature[node];
  if (coalition & (1 << feature)) return expected(tree, child(tree, node, row[feature]), row, coalition);
  const left = tree.left[node], right = tree.right[node], total = count(tree, node);
  if (!(total > 0)) throw new Error("Missing stored path counts");
  return (count(tree, left) * expected(tree, left, row, coalition) + count(tree, right) * expected(tree, right, row, coalition)) / total;
}

export function allocatePrice(reference: number, contributions: number[], raw: number) {
  if (![reference, raw, ...contributions].every(Number.isFinite)) throw new Error("Nonfinite price explanation");
  const reconstructionError = reference + contributions.reduce((sum, v) => sum + v, 0) - raw;
  if (Math.abs(reconstructionError) > 1e-6 + 1e-5 * Math.abs(raw)) throw new Error("Price explanation does not reconstruct");
  const deviation = raw - reference;
  const factor = deviation === 0 ? 1 : -Math.expm1(-deviation) / deviation;
  const referencePercent = 100 * Math.exp(-deviation);
  const percentages = contributions.map(value => 100 * factor * value);
  const reconciliationError = referencePercent + percentages.reduce((sum, value) => sum + value, 0) - 100;
  if (![referencePercent, ...percentages].every(Number.isFinite) || Math.abs(reconciliationError) > 1e-6) throw new Error("Price allocation does not reconcile");
  return { referencePercent, percentages, reconstructionError, reconciliationError };
}

export function predictPrice(engine: PricingEngine, input: unknown, identity: { runId: string; revision: string }): PricingResult {
  const { values, encoded } = encodePricingInput(input, engine.model);
  const coalitions = Array.from({ length: 32 }, (_, mask) => engine.trees.reduce((sum, tree) => sum + expected(tree, 0, encoded, mask), 0));
  // k! (4-k)! / 5!, indexed by coalition size.
  const weights = [1 / 5, 1 / 20, 1 / 30, 1 / 20, 1 / 5];
  const shap = PRICING_FIELDS.map((_, feature) => {
    let value = 0;
    for (let mask = 0; mask < 32; mask++) if (!(mask & (1 << feature))) {
      const size = mask.toString(2).replaceAll("0", "").length;
      value += weights[size] * (coalitions[mask | (1 << feature)] - coalitions[mask]);
    }
    return value;
  });
  const raw = coalitions[31], reference = coalitions[0], weight = values["quantity.total_edible_weight_g"] as number;
  const unitGbp = Math.exp(raw), packGbp = unitGbp * weight / 100;
  const referenceUnitGbp = Math.exp(reference), referencePackGbp = referenceUnitGbp * weight / 100;
  if (![unitGbp, packGbp, referenceUnitGbp, referencePackGbp].every(v => Number.isFinite(v) && v > 0)) throw new Error("Unrepresentable price prediction");
  const allocation = allocatePrice(reference, shap, raw);
  const attributions = PRICING_FIELDS.map((field, i) => ({ ...field, value: values[field.key], shapLog: shap[i], percent: allocation.percentages[i], packGbp: packGbp * allocation.percentages[i] / 100 }));
  const families = [...new Set(PRICING_FIELDS.map(field => field.family))].map(key => ({ key,
    percent: attributions.filter(field => field.family === key).reduce((sum, field) => sum + field.percent, 0),
    packGbp: attributions.filter(field => field.family === key).reduce((sum, field) => sum + field.packGbp, 0) }));
  const minimumLeafFamilies = Math.min(...engine.trees.map((tree, i) => {
    let node = 0; while (node >= 0) node = child(tree, node, encoded[tree.feature[node]]);
    return engine.model.leaf_support[String(i)][String(~node)];
  }));
  return { modelId: engine.model.model_id, ...identity, fixture: true, releaseReady: false,
    priceBasis: "regular-consumer-price-1", treeCount: engine.trees.length,
    unitGbp, packGbp, weightGrams: weight, predictedLog: raw, referenceLog: reference,
    referenceUnitGbp, referencePackGbp, referencePercent: allocation.referencePercent,
    attributions, families, reconstructionError: allocation.reconstructionError,
    reconciliationError: allocation.reconciliationError, minimumLeafFamilies,
    explanationMethod: "exact_tree_path_dependent_shap", allocationMethod: "proportional_exponential_allocation", interval: null };
}
