"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { AnalysisResponse, CohortQuery, CompareResponse, ProductResponse, ProductsResponse, SchemaResponse, TerrainResponse } from "../lib/contracts";
import { cohortParams, useApi, useDebounced } from "../lib/client/api";
import { dateLabel, number } from "../lib/client/display";
import { createProductDraft, evaluateDraft } from "../lib/client/product-draft";
import { HelpTip } from "./HelpTip";
import { FamilyNavigator } from "./FamilyNavigator";
import { CohortBuilder } from "./CohortBuilder";
import { Comparison } from "./Comparison";
import { EvidencePanel } from "./EvidencePanel";
import { ProductConfigurator } from "./ProductConfigurator";
import { ErrorState, Icon, Loading } from "./Icons";
import { TerrainExplorer } from "./TerrainExplorer";
import { GapFinder, BrandAnalysis } from "./AnalysisPanels";
import { ColumnSettings, TraitMatrix, visibleFields } from "./TraitMatrix";

const initialCohort: CohortQuery = { search: "", role: "all", source: "all", status: "all", rules: [] };
const initialColumns: ColumnSettings = { group: "all", search: "", limit: 4, modelOnly: false, expandedFamilies: ["composition", "certifications"], pinned: ["composition.cocoa_percentage", "certifications.organic_claim"] };

function Wordmark() {
  return <a className="wordmark" href="/" aria-label="Piece of Cake Pricing home"><span className="brand-symbol" aria-hidden="true"><i /><i /><i /></span><span className="cake-wordmark">Piece of Cake<span>PRICING</span></span></a>;
}

function Header() {
  return <header className="masthead"><Wordmark /><nav aria-label="Workspace sections"><a className="nav-active" href="#price-landscape">Explore</a><a href="#gap-finder">Gaps</a><a href="#brand-analysis">Brands</a><a href="#trait-matrix">Traits</a><a href="#comparison">Compare</a></nav><div className="workspace-label"><span className="live-dot" />FMCG PRICING<span className="workspace-avatar" aria-hidden="true">UK</span></div></header>;
}

export default function Dashboard() {
  const schemaRequest = useApi<SchemaResponse>("/api/schema");
  return <><a className="skip-link" href="#main">Skip to collection explorer</a><Header />{schemaRequest.loading ? <main id="main" className="initial-loading"><Loading text="Opening the collection workspace…" /></main> : schemaRequest.error ? <main id="main" className="initial-loading"><h1>The collection is unavailable.</h1><ErrorState message={schemaRequest.error} onRetry={schemaRequest.retry} /></main> : schemaRequest.data ? <Workspace schema={schemaRequest.data} /> : null}<noscript><div className="no-script">Enable JavaScript to filter the collection, explore price bands and inspect product evidence.</div></noscript></>;
}

function Workspace({ schema }: { schema: SchemaResponse }) {
  const [cohort, setCohort] = useState<CohortQuery>(initialCohort);
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [fieldKey, setFieldKey] = useState("composition.cocoa_percentage");
  const [columns, setColumns] = useState<ColumnSettings>(initialColumns);
  const [activeFamily, setActiveFamily] = useState<string | null>(null);
  const [colorKey, setColorKey] = useState("composition.chocolate_type");
  const [heightKey, setHeightKey] = useState("composition.cocoa_percentage");
  const [filterTrait, setFilterTrait] = useState<{ key: string; request: number } | null>(null);
  const [compared, setCompared] = useState<string[]>([]);
  const [analysisRange, setAnalysisRange] = useState<"core" | "full">("core");
  const [draft, setDraft] = useState(createProductDraft);
  const draftEvaluation = useMemo(() => evaluateDraft(draft, schema.fields), [draft, schema.fields]);
  const [gapFocus, setGapFocus] = useState<{ query: string; index: number } | null>(null);
  const search = useDebounced(cohort.search || "");
  const searchPending = search !== (cohort.search || "");
  const cohortQuery = useMemo(() => cohortParams({ ...cohort, search }).toString(), [cohort, search]);
  const productsQuery = `${cohortQuery}${cohortQuery ? "&" : ""}page=${page}&pageSize=25`;
  const products = useApi<ProductsResponse>(`/api/products?${productsQuery}`);
  const analysisQuery = `${cohortQuery}${cohortQuery ? "&" : ""}range=${analysisRange}`;
  const analysis = useApi<AnalysisResponse>(`/api/analysis?${analysisQuery}`);
  const terrainQuery = `${cohortQuery}${cohortQuery ? "&" : ""}${new URLSearchParams({ color: colorKey, z: heightKey, range: analysisRange })}`;
  const terrain = useApi<TerrainResponse>(`/api/terrain?${terrainQuery}`);
  const activeGap = gapFocus?.query === analysisQuery ? gapFocus.index : null;
  const evidence = useApi<ProductResponse>(selectedId ? `/api/products/${encodeURIComponent(selectedId)}` : null);
  const comparison = useApi<CompareResponse>(compared.length ? `/api/compare?${new URLSearchParams({ ids: compared.join(",") })}` : null);
  const fields = useMemo(() => visibleFields(schema.fields, columns), [schema.fields, columns]);

  useEffect(() => {
    if (!selectedId && products.data?.products[0]) setSelectedId(products.data.products[0].id);
  }, [products.data, selectedId]);
  const changeCohort = useCallback((value: CohortQuery) => { setCohort(value); setPage(1); }, []);
  const selectProduct = useCallback((id: string, field?: string) => { setSelectedId(id); if (field) setFieldKey(field); }, []);
  const toggleCompare = useCallback((id: string) => setCompared(current => current.includes(id) ? current.filter(item => item !== id) : current.length < 4 ? [...current, id] : current), []);
  const togglePin = useCallback((key: string) => setColumns(current => ({ ...current, pinned: current.pinned.includes(key) ? current.pinned.filter(item => item !== key) : [...current.pinned, key] })), []);
  const focusFamily = useCallback((group: string | null) => {
    setActiveFamily(group);
    if (group) setColumns(current => ({ ...current, group: "all", search: "", modelOnly: false, expandedFamilies: current.expandedFamilies.includes(group) ? current.expandedFamilies : [...current.expandedFamilies, group] }));
  }, []);
  const filtered = Boolean(cohort.search || cohort.rules?.length || cohort.role !== "all" || cohort.source !== "all" || cohort.status !== "all");

  return <main id="main" className="workspace">
    <div className="page-intro"><div><p className="eyebrow"><span className="live-dot" />FMCG INTELLIGENCE <span>/</span> CHOCOLATE · UK</p><div className="hero-title-row"><h1>Piece of Cake <em>Pricing</em></h1><HelpTip label="About Piece of Cake Pricing"><p>Explore observed product prices, trait families, gaps and brand price positioning.</p><p>{number(schema.meta.counts.listings || schema.meta.schemaValidatedListings)} source listings · {number(schema.meta.counts.price_observations || 0)} price observations · {schema.fields.length} traits across {schema.contract.groups.length} families.</p><p>Demo pricing scores are calculated from known product traits using a fixed prototype recipe. Colour layers show the selected trait’s values or numeric ranges. The hosted pricing model is not connected. Gap and brand analyses use observed prices.</p></HelpTip></div><p className="intro-copy">FMCG Pricing made easy.</p></div><div className="snapshot-status"><span className="tag"><span className="live-dot" />UK · CHOCOLATE</span><HelpTip label="About the collection snapshot"><p>Snapshot: {dateLabel(schema.meta.lastModified)}. {schema.sources.length} sources in the {schema.contract.market.toUpperCase()} market.</p><p>Observed source claims and price context await review. {schema.meta.counts.eligible_model_inputs || 0} eligible model inputs are published; demo scores are not validated predictions.</p></HelpTip></div></div>
    <CohortBuilder schema={schema} cohort={cohort} onChange={changeCohort} requestedTrait={filterTrait} />
    <FamilyNavigator schema={schema} coverage={searchPending ? undefined : products.data?.coverage} total={searchPending ? undefined : products.data?.total} activeFamily={activeFamily} onFocus={focusFamily} onFilterTrait={key => { setFilterTrait(current => ({ key, request: (current?.request || 0) + 1 })); document.getElementById("cohort")?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" }); }} onColorTrait={setColorKey} onHeightTrait={setHeightKey} colorKey={colorKey} heightKey={heightKey} />
    <div className="exploration-grid">
      <TerrainExplorer schema={schema} data={searchPending ? null : terrain.data} loading={terrain.loading || searchPending} error={terrain.error} onRetry={terrain.retry} color={colorKey} z={heightKey} onColor={setColorKey} onZ={setHeightKey} range={analysisRange} onRange={setAnalysisRange} selectedId={selectedId} onSelect={selectProduct} configuredProduct={draftEvaluation.marker ? { ...draftEvaluation.marker, traits: draftEvaluation.traits } : null} gap={activeGap === null ? null : analysis.data?.gaps.items[activeGap] || null} />
      <ProductConfigurator schema={schema} draft={draft} onChange={setDraft} selectedProduct={evidence.data?.product || null} selectedLoading={evidence.loading}>
      <EvidencePanel schema={schema} data={evidence.data} loading={evidence.loading} error={evidence.error} onRetry={evidence.retry} fieldKey={fieldKey} onField={setFieldKey} pinned={columns.pinned} onPin={togglePin} compared={compared} onCompare={toggleCompare} coverage={products.data?.coverage[fieldKey]} />
      </ProductConfigurator>
    </div>
    <div className="analysis-grid">
      <GapFinder data={searchPending ? null : analysis.data} loading={analysis.loading || searchPending} error={analysis.error} onRetry={analysis.retry} activeGap={activeGap} onFocusGap={index => { setGapFocus(index === null ? null : { query: analysisQuery, index }); document.getElementById("price-landscape")?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" }); }} />
      <BrandAnalysis data={searchPending ? null : analysis.data} loading={analysis.loading || searchPending} error={analysis.error} onRetry={analysis.retry} />
    </div>
    <TraitMatrix schema={schema} data={searchPending ? null : products.data} loading={products.loading || searchPending} error={products.error} onRetry={products.retry} fields={fields} settings={columns} onSettings={setColumns} selectedId={selectedId} compared={compared} onSelect={selectProduct} onCompare={toggleCompare} onPage={setPage} onPin={togglePin} activeFamily={activeFamily} onFocusFamily={focusFamily} />
    <Comparison schema={schema} settings={columns} onSettings={setColumns} onPin={togglePin} activeFamily={activeFamily} onFocusFamily={focusFamily} data={comparison.data} loading={comparison.loading} error={comparison.error} onRetry={comparison.retry} fields={fields} ids={compared} onRemove={toggleCompare} onClear={() => setCompared([])} onSelect={selectProduct} />
    <footer className="footer"><div><span className="footer-logo cake-footer">Piece of Cake Pricing</span></div><p>{filtered ? "Filtered collection" : "Collection snapshot"} · schema {schema.meta.schemaVersion} · <a href={`https://huggingface.co/datasets/${schema.meta.repository}/tree/${schema.meta.revision}`} target="_blank" rel="noreferrer">revision {schema.meta.revision.slice(0, 8)} <Icon name="arrow" size={11} /></a></p></footer>
  </main>;
}
