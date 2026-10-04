# Chocolate schema reconstructed from Bronze, 2026-10-04

A fresh initial schema was generated from the retained UK chocolate Bronze corpus
and then compared with `chocolate-schema-1`. The fresh proposal contains **75
fields**; the existing profile contains **103 attributes**. The full crosswalk below
accounts for all 103 old attributes.

The fresh proposal is a research result requiring further design and processing
work before adoption. It supplies original evidence, types, units, meanings,
scopes, qualifiers and semantic cases. It has no implemented extractor, validator,
model design or Silver/Gold build. The existing published schema remains the live
contract.

## Research scope and protocol

The [category-schema skill](../../../plugins/category-processing/skills/category-schema/SKILL.md)
was applied to the Bronze records at
`/Users/coral/repos/rgc/data/collections/chocolate/uk`.
The initial census and catalog-authoring scripts import no analytical schema,
source mappings or existing processing extractors. The proposal was semantically
refined and frozen before opening the old profile for comparison. Earlier
conversation included chocolate concepts and a cocoa example, so this exercise
makes no claim of cognitive blinding. It is a fresh reconstruction using Bronze,
not an independent human or agent blind evaluation.

| Inspected evidence | Scope |
| --- | --- |
| Product indexes and latest capture bodies | 3,743 readable indexes; no parse errors; all 3,743 latest capture bodies inventoried mechanically. |
| Sources | 24 seller/source keys; listing counts are below. |
| Retained captures | 4,347: 3,139 listings with one capture, 604 with two. Earlier capture bodies were counted but not semantically reviewed. |
| Raw structure | 12,057 normalized scalar paths, including page configuration, artifacts and collection metadata; this is not a count of analytical concepts. |
| Semantic sample | 96 deterministic listing summaries, four per source; 24 source-format summaries; 10 detailed targeted records. These cover 97 unique listings because one additional cocoa record was targeted. |
| Post-design comparison review | Three further originals reviewed to distinguish genuine ruby chocolate from a personalized sleeve name. These did not change the frozen fresh draft. |
| Images and original artifact bodies | Image pixels/OCR were not inspected and source artifact payloads were not independently rehashed. Raw index bytes were hashed and rechecked. |

Sample summaries were inspected for names, composition, quantities, source
formats and contextual claims. Product-specific declarations were examined in
structured JSON, retained product text and ingredient/nutrition sections.
Historical repeats and personalized variants cannot be counted as independent
semantic support. Census counts cover the corpus; semantic review covers the
stated sample, not every product.

The input-index inventory SHA-256 is
`18024a1a6cbcf9ddb318fee1910fe2c6ae4599fe4508dff2f02bbd67a3e28bdc`.
The frozen fresh catalog SHA-256 is
`f915e32ba90319c8c3dd9d4c74ecaa8e8ec4320e18aa50d3e8958e2811f410be`.

## Findings from the raw data

The corpus combines Shopify product/variant records, product JSON-LD and page
configuration, source-specific original product/detail objects, decoded HTML
sections, catalog card text and cached web-tool representations. These shapes
need source-aware interpretation. Product pages may contain navigation, brand
copy, other products, default variant labels, collection notes and expired
promotions. Presence of a matching word is insufficient to establish a fact.

At the raw identity path, 2,928 listings have a nonempty brand and 1,295 have a
nonempty GTIN. Brand is therefore missing or null on 815 listings; a source key
cannot supply the product brand. GTIN paths occur on 3,688 records, so 55 omit
that path and 2,393 have a null/empty value. These are raw structural counts;
other source representations may contain additional brand or barcode evidence.

Lexical searches found cocoa/percentage candidates on 2,792 listings and nutrition
basis candidates on 2,383. Searches covered retained information strings and
names, including page context and metadata. These are candidate counts, not
validated product facts, extraction coverage or individual model reviews.

The central semantic distinctions are:

- Declared product net mass, per-item mass and platform variant grams have
  different bases. Honeycomb declares 150g while its platform variant reports
  165 grams. NOMO names 12 bars of 32g while platform grams is 500. Love Cocoa
  has an implausible platform grams value of 75,000. Preserve and review each
  basis before deriving edible quantity.
- Cocoa percentage and ingredient/component share differ. Twix describes milk
  chocolate at 35%, caramel at 32% and biscuit at 26%; none of those establishes
  its cocoa-solids percentage.
- Minimum, actual and component declarations may coexist. Cadbury explicitly
  states milk solids 20% minimum and actual 23%. Those are different qualified
  assertions, rather than contradictory values for the same context.
- Nutrition columns need their original panel basis, quantity and preparation
  context. NOMO retains both per-100g and per-32g columns. Reference-intake
  percentages are separate information.
- Vegan/free-from, named certification, generic sourcing, facility handling and
  product ingredient statements require separate meanings and source scopes.
- Sensory analogies do not establish ingredients. Gorse chocolate describes a
  coconut scent; that wording does not establish coconut ingredient presence.
- Packaging properties attach to components. A recyclable paper-card outer box
  and compostable inner bag require separate subjects.
- Observed offer validity is distinct from capture time. A Co-op representation
  captured in October describes a deal ending on 29 September 2026.

## The fresh schema

The catalog has **63 product, quantity, composition, nutrition, claim, origin,
process, packaging and storage fields**, plus **nine offer fields and three
customer-review fields**. Identity/provenance, subject/component IDs, nutrition
basis, award records, evidence state and review status live in envelopes.
Repeated components, panels, awards and observations can carry distinct assertions
of the same concept. Lists require member-level source evidence.

Known, unknown, conflict and not-applicable remain distinct. Missing statements
cannot establish absence. Conflict requires equivalent subject, basis, qualifier
and observation context. No model target, predictor subset or encoder was chosen.
The proposed vocabulary and normalization policy require further semantic work;
research source paths are not configured extraction rules.

Every retained field has sampled original-source design evidence. A populated
offer-valid-from date was not established in the sampled structured fields, so
that concept was deferred outside the 75-field catalog. Evidence examples do
not imply semantically validated values or corpus-wide extraction coverage.

The complete machine-readable local draft is
`data/investigation/2026-10-04-schema-from-bronze/new-schema.json`.
It is an unpublished working proposal outside tracked analytical contracts. Its
field definitions and original capture/pointer references are reviewable there;
this document retains the field catalog below for clean-clone readability.

## Comparison with the existing schema

The comparison used the hash-verified existing profile at dataset revision
`d549ad91d63fb452af605df4a939c4e1f0a59bfa`, with profile SHA-256
`881da5b79167bde7c8ac54dce76d39a3962cb5f73540e0e062c34dfde81e6458`.
The repository [contract reference](../../../schemas/chocolate/dataset-contract.json)
pins that old schema. The current chocolate price study changes model policy,
not these 103 attribute meanings.

| Classification of old attributes | Count | Meaning |
| --- | --- | --- |
| Counterpart with renamed or restructured representation | 44 | Migration still needs explicit scope, type, unit and vocabulary checks. |
| Consolidated into broader concepts | 39 | A broad list/text field requires a derived view to reproduce the old dedicated indicator, role or typed measurement. |
| Moved to envelope or processing context | 8 | Identity, boundary, nutrition-panel basis or source roles need explicit downstream metadata. |
| Preserved only through original evidence | 4 | The fresh draft has no corresponding dedicated source-text attribute. |
| No explicit counterpart | 8 | These old tracked concepts remain gaps in the fresh catalog. |

**75 versus 103 is not a completeness score.** The old profile keeps prices and
promotions in separate observation tables; the fresh research catalog lists nine
offer concepts. Its three review concepts also add another observation domain.
The fresh envelope fields and repeated assertions are not included in its count.
Consolidating many old indicators into one list can reduce field count while
losing useful normalized distinctions.

Six fresh trait concepts have no direct old attribute mapping: source category,
personalization availability, platform mass, facility-handled allergens, added
sugars and manufacture place. Their underlying original evidence may already be
retained in Bronze or unmapped source claims. The remaining 12 unmatched fresh
fields belong to offer and customer-review observations.

The old schema already distinguishes ingredient allergens from may-contain
warnings, cocoa origin from manufacture, tasting notes from ingredients,
product/brand/packaging scope, and minimum/approximate qualifiers. It also already
excludes platform grams from edible mass without an established basis. These
are shared principles, not new discoveries unique to the fresh design.

The fresh draft has eight explicit catalog gaps: manufacturer name, original
flavour name, exact physical-product ID, non-GMO claim, single-origin claim,
single-estate claim, gift-packaging claim and premium claim. It also needs to
retain the old separate pack/piece-count meanings, numeric storage-temperature
bounds, shelf-life/date types, controlled vocabularies and claim polarity.
A general claim list currently lacks an explicit per-member affirmed/negated
polarity field; it cannot be treated as an equivalent old presence indicator.

A concrete vocabulary gap is ruby chocolate. The old style vocabulary includes
ruby; the frozen fresh vocabulary does not. Post-design review found source
product descriptions for `Ruby Chocolate Buttons` and `Naturally Pink Ruby
Chocolate`. Cadbury's personalized `"Ruby" Dairy Milk` is a counterexample: a
person's name does not establish ruby chocolate. Two additional product-description reviews
support retaining the old ruby style; the frozen proposal stays intact so this
comparison is reproducible.

## The missing cocoa example

For listing `chococo-10602653352202-53584171303178`, capture
`20261003T081437558349Z-efc34e4da7-000160`, the original pointer
`/raw_record/information/product_page_information/ingredients_source_statement/0/text`
contains `47% (min) cocoa solids, 23% milk solids.`

The fresh `composition.cocoa_solids` definition would represent 47 with a minimum
qualifier and its declared chocolate/component basis. The old
`composition.cocoa_percentage` **already permits that meaning**: its description
and percentage rule preserve minimum/exact qualifiers and constituent scope.
The previous missing cocoa value is therefore an extraction/review gap; replacing
the schema alone will not populate it. No Silver/Gold coverage improvement is
claimed from this schema-creation exercise.

## Recommended next design decisions

Use this reconstruction as a review input rather than replacing the working
schema with the frozen draft. Preserve the old tracked distinctions and
controlled vocabularies, then review useful additions and repeated panel/component
contexts. Keep offers and customer reviews separate from product traits in the
runtime representation. Prioritize evidence extraction repairs for minimum
cocoa wording and declared net/multipack quantities.

A subsequent draft needs stronger per-claim polarity and basis rules, an agreed
category boundary, broader source semantic review, image inspection where
relevant, and implementations for repeated contextual assertions. Converting the
catalog into a runnable profile requires the later processing stage; model design
and model-input preparation belong to Silver to Gold. Publication requires the
existing reviewed release workflow.

## Validation and local artifacts

All 3,743 index hashes were rechecked after research. All 148 schema/semantic-case
source references resolve to the original capture/pointer and preserve their
exact quoted substring or scalar value. Thirteen representative semantic cases
were checked, including missing scope, qualified percentages, conflicting mass
bases, nutrition columns, conditional dietary wording and navigation contamination.
The three post-design ruby/name references also resolve to the originals.
All 103 old attributes have an explicit crosswalk and every mapped new field exists.
These checks establish artifact consistency and traceability, not a tested parser,
validated category coverage or model readiness.

The local investigation directory also contains `research.json`,
`raw-index-inventory.json`, `field-inventory.json`, `semantic-samples.json`,
`design-freeze.json`, `comparison.json`, `verification.json` and the authoring,
research and verification scripts. These are research aids and working drafts;
they are not extra required runtime JSON contracts. The scripts distinguish
initial raw research from the later old-contract comparison.

The 27 documentation pytest cases, repository Ruff, explicit lint for all five
research scripts, documentation guard and whitespace checks passed. Runtime
semantic tests were not rerun because no processing logic or live contract changed.

Recheck the locally generated artifacts from the repository root:

```sh
python3 data/investigation/2026-10-04-schema-from-bronze/validate.py
```

## Source listing counts

| Source key | Listings |
| --- | --- |
| `asda` | 23 |
| `cadbury-gifts-direct` | 1,268 |
| `chococo` | 167 |
| `chocolarder` | 43 |
| `chocolate-co-uk` | 86 |
| `chocolate-shop` | 208 |
| `chocolate-trading-co` | 241 |
| `cocoa-runners` | 5 |
| `coop` | 11 |
| `divine` | 57 |
| `firetree` | 53 |
| `fortnum-mason` | 127 |
| `lindt-uk` | 56 |
| `love-cocoa` | 30 |
| `montezumas` | 91 |
| `moo-free` | 74 |
| `morrisons` | 51 |
| `nomo` | 60 |
| `ocado` | 301 |
| `pump-street` | 66 |
| `sainsburys` | 64 |
| `seed-and-bean` | 13 |
| `tonys-uk` | 237 |
| `waitrose` | 411 |

## Fresh field catalog

Types, units and meanings below are authored schema decisions. Component/panel/award
subjects retain separate assertion contexts; the local draft has the full evidence,
qualifier, vocabulary, bound and rationale records.

| Field | Type / unit | Scope | Meaning |
| --- | --- | --- | --- |
| `product.name` | string / none | product | Source product/variant display name. |
| `product.brand` | string / none | product | Product brand explicitly identified by the source. |
| `product.seller_sku` | string / none | observation | Seller-local SKU for the selected sellable variant. |
| `product.gtin` | string / none | product | Explicit product barcode, preserving leading zeros. |
| `product.variant_label` | string / none | product | Source option/title identifying the selected offered variant. |
| `product.source_category` | string_list / none | product | Product-specific source category labels. |
| `product.form` | enum / none | product | Physical offered form declared in product context. |
| `product.chocolate_style` | enum / none | product | Source-declared chocolate style, preserving component context. |
| `product.inclusions` | string_list / none | product | Explicit added ingredients or inclusions named for this product. |
| `product.assortment_components` | string_list / none | product | Source-named edible and nonfood components of an assortment or bundle. |
| `product.occasion` | string_list / none | product | Product-specific seasonal, celebration or gifting design claims. |
| `product.intended_use` | string_list / none | product | Explicit use such as eating, baking or preparing a drink. |
| `product.personalisation_available` | boolean / none | observation | Explicit availability of personalization for this offer. |
| `quantity.net_mass` | number / g | product | Declared edible net mass for the complete selected offer. |
| `quantity.item_count` | integer / item | product | Explicit count of edible items in the selected offer. |
| `quantity.item_mass` | number / g | component | Explicit mass of one named item within a multipack. |
| `quantity.platform_mass` | number / g | observation | Raw selected-platform variant grams field with net/shipping basis unresolved unless documented. |
| `quantity.serving_mass` | number / g | nutrition_panel | Explicit mass used for a declared nutrition serving or portion. |
| `composition.ingredients_statement` | string / none | product | Original product/component ingredient declaration. |
| `composition.ingredient_names` | string_list / none | component | Explicit named ingredients from a retained declaration. |
| `composition.cocoa_solids` | number / percent | product | Declared cocoa solids/content percentage for the named chocolate or product. |
| `composition.milk_solids` | number / percent | product | Declared milk solids percentage for the named chocolate/component. |
| `composition.ingredient_share` | number / percent | component | Explicit percentage share of a named ingredient or component within its stated parent. |
| `allergens.declared_contains` | string_list / none | product | Explicit allergen presence statement or supported ingredient declaration. |
| `allergens.may_contain` | string_list / none | product | Explicit precautionary may-contain or trace warning. |
| `allergens.free_from` | string_list / none | product | Explicit product-specific allergen absence/free-from claim. |
| `allergens.facility_handles` | string_list / none | facility | Explicit allergens handled in a production facility or kitchen. |
| `dietary.suitability` | string_list / none | product | Explicit vegan, vegetarian, kosher, halal or other suitability claim. |
| `nutrition.energy_kj` | number / kJ | nutrition_panel | Declared energy in kilojoules. Attach its explicit panel basis and component. |
| `nutrition.energy_kcal` | number / kcal | nutrition_panel | Declared energy in kilocalories. Attach its explicit panel basis and component. |
| `nutrition.fat` | number / g | nutrition_panel | Declared total fat. Attach its explicit panel basis and component. |
| `nutrition.saturates` | number / g | nutrition_panel | Declared saturated fat. Attach its explicit panel basis and component. |
| `nutrition.carbohydrate` | number / g | nutrition_panel | Declared carbohydrate. Attach its explicit panel basis and component. |
| `nutrition.sugars` | number / g | nutrition_panel | Declared total sugars. Attach its explicit panel basis and component. |
| `nutrition.added_sugars` | number / g | nutrition_panel | Declared added sugars, distinct from total sugars. Attach its explicit panel basis and component. |
| `nutrition.fibre` | number / g | nutrition_panel | Declared fibre. Attach its explicit panel basis and component. |
| `nutrition.protein` | number / g | nutrition_panel | Declared protein. Attach its explicit panel basis and component. |
| `nutrition.salt` | number / g | nutrition_panel | Declared salt. Attach its explicit panel basis and component. |
| `origin.cocoa_country` | string_list / none | component | Country explicitly associated with cocoa sourcing, retaining the original label and its component. Broader regions belong to cocoa_region. |
| `origin.cocoa_region` | string_list / none | component | Explicit cocoa-growing region, island, valley or locality. |
| `origin.cocoa_estate` | string_list / none | component | Named cocoa estate, farm or cooperative. |
| `origin.cocoa_variety` | string_list / none | component | Source-declared cocoa variety or cultivar. |
| `origin.manufacture_country` | string_list / none | product | Source-declared country or jurisdiction label for manufacture, with unresolved geographical normalization preserved. |
| `origin.manufacture_place` | string_list / none | product | Place or site explicitly associated with a named manufacturing step. |
| `process.declared_methods` | string_list / none | component | Explicit process claims such as bean-to-bar, handmade, hand-poured, flaked or cocoa infused in whisky. |
| `sensory.tasting_notes` | string_list / none | product | Source-described aroma, flavour and texture notes. |
| `claims.certification_names` | string_list / none | product | Source-declared named certification/scheme claims, with source scope and assurance unverified. |
| `claims.sourcing_statements` | string_list / none | product | Explicit sourcing/trading claims such as direct trade, farmer-owned or sail shipped. |
| `claims.sustainability_statements` | string_list / none | product | Product-context environmental/social claims retained as statements. |
| `claims.sugar_statements` | string_list / none | product | Explicit no/reduced/added-sugar claims, preserving conditions and declared basis. |
| `claims.ingredient_exclusions` | string_list / none | product | Explicit non-allergen absence claims, such as palm-oil-free or lecithin-free. |
| `claims.alcohol_statement` | string_list / none | product | Explicit contains-alcohol/alcohol-free statement; source contradictory cases retain conflict. |
| `award.name` | string / none | award | Name of a source-declared award associated with this product. |
| `award.year` | integer / year | award | Explicit award year associated with a named award record. |
| `award.grade` | string / none | award | Explicit award grade/medal/star count retained as stated. |
| `packaging.type` | string_list / none | packaging_component | Explicit container or packaging form. |
| `packaging.materials` | string_list / none | packaging_component | Explicit materials of a named packaging component. |
| `packaging.recyclable` | boolean / none | packaging_component | Explicit recyclability claim or disposal instruction. |
| `packaging.compostable` | boolean / none | packaging_component | Explicit compostability claim. |
| `packaging.plastic_free` | boolean / none | packaging_component | Explicit plastic-free packaging claim. |
| `packaging.reusable` | boolean / none | packaging_component | Explicit reusable container claim. |
| `storage.conditions` | string / none | product | Explicit storage advice including stated temperature range. |
| `storage.shelf_life_statement` | string / none | product | Explicit best-before or shelf-life wording; retain a reference to the pack when no duration is stated. |
| `offer.displayed_price` | number / currency_amount | observation | Source-displayed monetary amount for the selected offer. |
| `offer.reference_price` | number / currency_amount | observation | Explicit comparison/was/compare-at monetary amount, with its stated basis. |
| `offer.currency` | string / none | observation | Explicit currency for each price observation. |
| `offer.source_unit_price` | number / currency_per_declared_basis | observation | Source-displayed unit price with its explicit quantity and unit basis. |
| `offer.availability` | enum / none | observation | Product/variant availability stated at the source observation. |
| `offer.promotion_statement` | string / none | observation | Product-linked offer/discount wording. |
| `offer.purchase_conditions` | string_list / none | observation | Explicit constraints attached to this offer, including membership, quantity, subscription or personalization. |
| `offer.valid_to` | string / date_or_datetime | observation | Explicit end of stated offer validity. |
| `offer.tax_statement` | string / none | observation | Source-declared tax inclusion or other tax wording. |
| `review.rating` | number / source_rating_points | observation | Explicit product-level customer aggregate rating with count and scale. |
| `review.rating_scale` | number / source_rating_points | observation | Explicit denominator or maximum of the source rating scale. |
| `review.count` | integer / review | observation | Explicit count attached to the same product rating observation. |

## Complete old-to-new crosswalk

Counterparts describe proposed semantic relationships. Consolidated entries require
explicit derived-view rules; they are not implemented equivalences. Envelope and
evidence-only entries have no new attribute ID.

| Existing attribute | Fresh counterpart | Classification |
| --- | --- | --- |
| `identity.name` | `product.name` | Counterpart / restructured |
| `identity.sku` | `product.seller_sku` | Counterpart / restructured |
| `identity.variant_name` | `product.variant_label` | Counterpart / restructured |
| `identity.brand` | `product.brand` | Counterpart / restructured |
| `identity.gtin` | `product.gtin` | Counterpart / restructured |
| `identity.source_product_id` | — | Envelope / processing context |
| `identity.source_variant_id` | — | Envelope / processing context |
| `identity.product_family_id` | — | Envelope / processing context |
| `identity.retailer` | — | Envelope / processing context |
| `identity.product_group` | `product.form`, `product.intended_use` | Counterpart / restructured |
| `identity.boundary_status` | — | Envelope / processing context |
| `identity.source_role` | — | Envelope / processing context |
| `identity.manufacturer_name` | — | Catalog gap |
| `identity.flavour_name` | — | Catalog gap |
| `identity.physical_product_id` | — | Catalog gap |
| `composition.chocolate_type` | `product.chocolate_style` | Counterpart / restructured |
| `composition.cocoa_percentage` | `composition.cocoa_solids` | Counterpart / restructured |
| `composition.milk_solids_percentage` | `composition.milk_solids` | Counterpart / restructured |
| `composition.ingredients_text` | `composition.ingredients_statement` | Counterpart / restructured |
| `composition.ingredients` | `composition.ingredient_names` | Counterpart / restructured |
| `composition.allergen_ingredients` | `allergens.declared_contains` | Counterpart / restructured |
| `composition.may_contain_allergens` | `allergens.may_contain` | Counterpart / restructured |
| `composition.inclusions` | `product.inclusions` | Counterpart / restructured |
| `composition.cocoa_butter_percentage` | `composition.ingredient_share` | Consolidated; view required |
| `composition.nuts_presence` | `composition.ingredient_names`, `allergens.declared_contains` | Consolidated; view required |
| `composition.may_contain_nuts_presence` | `allergens.may_contain` | Consolidated; view required |
| `composition.palm_oil_presence` | `composition.ingredient_names`, `claims.ingredient_exclusions` | Consolidated; view required |
| `composition.alcohol_presence` | `claims.alcohol_statement` | Consolidated; view required |
| `composition.salt_added_presence` | `composition.ingredient_names` | Consolidated; view required |
| `composition.fruit_presence` | `product.inclusions`, `composition.ingredient_names` | Consolidated; view required |
| `composition.nut_types` | `composition.ingredient_names` | Consolidated; view required |
| `composition.flavour_labels` | `product.inclusions` | Consolidated; view required |
| `composition.sweeteners` | `composition.ingredient_names` | Consolidated; view required |
| `composition.filling_type` | `product.assortment_components`, `composition.ingredient_names` | Consolidated; view required |
| `composition.allergen_text` | — | Original evidence only |
| `dietary.vegan_claim` | `dietary.suitability` | Consolidated; view required |
| `dietary.vegetarian_claim` | `dietary.suitability` | Consolidated; view required |
| `dietary.gluten_free_claim` | `allergens.free_from` | Consolidated; view required |
| `dietary.dairy_free_claim` | `allergens.free_from` | Consolidated; view required |
| `dietary.nut_free_claim` | `allergens.free_from` | Consolidated; view required |
| `dietary.soy_free_claim` | `allergens.free_from` | Consolidated; view required |
| `dietary.palm_oil_free_claim` | `claims.ingredient_exclusions` | Consolidated; view required |
| `dietary.sugar_free_claim` | `claims.sugar_statements` | Consolidated; view required |
| `dietary.no_added_sugar_claim` | `claims.sugar_statements` | Consolidated; view required |
| `dietary.non_gmo_claim` | — | Catalog gap |
| `certifications.fairtrade_claim` | `claims.certification_names` | Consolidated; view required |
| `certifications.fair_trade_claim` | `claims.sourcing_statements` | Consolidated; view required |
| `certifications.organic_claim` | `claims.certification_names` | Consolidated; view required |
| `certifications.rainforest_alliance_claim` | `claims.certification_names` | Consolidated; view required |
| `certifications.kosher_claim` | `dietary.suitability`, `claims.certification_names` | Consolidated; view required |
| `certifications.halal_claim` | `dietary.suitability`, `claims.certification_names` | Consolidated; view required |
| `certifications.fsc_packaging_claim` | `claims.certification_names` | Consolidated; view required |
| `certifications.b_corp_claim` | `claims.certification_names` | Consolidated; view required |
| `certifications.named_schemes` | `claims.certification_names` | Counterpart / restructured |
| `nutrition.energy_kj_per_100g` | `nutrition.energy_kj` | Counterpart / restructured |
| `nutrition.energy_kcal_per_100g` | `nutrition.energy_kcal` | Counterpart / restructured |
| `nutrition.fat_g_per_100g` | `nutrition.fat` | Counterpart / restructured |
| `nutrition.saturates_g_per_100g` | `nutrition.saturates` | Counterpart / restructured |
| `nutrition.carbohydrate_g_per_100g` | `nutrition.carbohydrate` | Counterpart / restructured |
| `nutrition.sugars_g_per_100g` | `nutrition.sugars` | Counterpart / restructured |
| `nutrition.fibre_g_per_100g` | `nutrition.fibre` | Counterpart / restructured |
| `nutrition.protein_g_per_100g` | `nutrition.protein` | Counterpart / restructured |
| `nutrition.salt_g_per_100g` | `nutrition.salt` | Counterpart / restructured |
| `nutrition.serving_size_g` | `quantity.serving_mass` | Counterpart / restructured |
| `nutrition.declared_basis` | — | Envelope / processing context |
| `nutrition.source_text` | — | Original evidence only |
| `origin.cocoa_countries` | `origin.cocoa_country` | Counterpart / restructured |
| `origin.manufacture_country` | `origin.manufacture_country` | Counterpart / restructured |
| `origin.cocoa_regions` | `origin.cocoa_region` | Counterpart / restructured |
| `origin.cocoa_estates` | `origin.cocoa_estate` | Counterpart / restructured |
| `origin.cocoa_varieties` | `origin.cocoa_variety` | Counterpart / restructured |
| `origin.single_origin_claim` | — | Catalog gap |
| `origin.single_estate_claim` | — | Catalog gap |
| `packaging.type` | `packaging.type` | Counterpart / restructured |
| `packaging.materials` | `packaging.materials` | Counterpart / restructured |
| `packaging.recyclable_claim` | `packaging.recyclable` | Counterpart / restructured |
| `packaging.compostable_claim` | `packaging.compostable` | Counterpart / restructured |
| `packaging.reusable_claim` | `packaging.reusable` | Counterpart / restructured |
| `packaging.plastic_free_claim` | `packaging.plastic_free` | Counterpart / restructured |
| `packaging.gift_pack_claim` | — | Catalog gap |
| `packaging.components` | — | Envelope / processing context |
| `processing.bean_to_bar_claim` | `process.declared_methods` | Consolidated; view required |
| `processing.handmade_claim` | `process.declared_methods` | Consolidated; view required |
| `processing.roasted_claim` | `process.declared_methods` | Consolidated; view required |
| `processing.conched_claim` | `process.declared_methods` | Consolidated; view required |
| `processing.raw_claim` | `process.declared_methods` | Consolidated; view required |
| `processing.description` | — | Original evidence only |
| `storage.instructions` | `storage.conditions` | Counterpart / restructured |
| `storage.temperature_min_c` | `storage.conditions` | Consolidated; view required |
| `storage.temperature_max_c` | `storage.conditions` | Consolidated; view required |
| `storage.shelf_life_days` | `storage.shelf_life_statement` | Consolidated; view required |
| `storage.best_before_date` | `storage.shelf_life_statement` | Consolidated; view required |
| `marketing.claim_text` | — | Original evidence only |
| `marketing.tasting_notes` | `sensory.tasting_notes` | Counterpart / restructured |
| `marketing.awards` | `award.name`, `award.year`, `award.grade` | Counterpart / restructured |
| `marketing.ethical_claims` | `claims.sourcing_statements` | Counterpart / restructured |
| `marketing.sustainability_claims` | `claims.sustainability_statements` | Counterpart / restructured |
| `marketing.seasonal_occasions` | `product.occasion` | Counterpart / restructured |
| `marketing.premium_claim` | — | Catalog gap |
| `quantity.total_edible_weight_g` | `quantity.net_mass` | Counterpart / restructured |
| `quantity.unit_edible_weight_g` | `quantity.item_mass` | Counterpart / restructured |
| `quantity.pack_count` | `quantity.item_count` | Consolidated; view required |
| `quantity.piece_count` | `quantity.item_count` | Consolidated; view required |
