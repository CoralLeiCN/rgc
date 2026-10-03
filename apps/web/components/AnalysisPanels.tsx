"use client";

import { useState } from "react";
import type { AnalysisResponse } from "../lib/contracts";
import { money, number } from "../lib/client/display";
import { ErrorState, Icon, Loading } from "./Icons";
import { HelpTip } from "./HelpTip";

interface AnalysisProps {
  data: AnalysisResponse | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

interface GapProps extends AnalysisProps {
  activeGap?: number | null;
  onFocusGap?: (index: number | null) => void;
}

function percentLabel(value: number) {
  return `${value > 0 ? "+" : ""}${new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1 }).format(value)}%`;
}

export function GapFinder({ data, loading, error, onRetry, activeGap, onFocusGap }: GapProps) {
  const [showAll, setShowAll] = useState(false);
  const gaps = data?.gaps;
  const visible = gaps?.items.map((gap, index) => ({ gap, index })).filter(({ index }) => showAll || index < 3 || index === activeGap) || [];
  return <section id="gap-finder" className="gap-finder panel analysis-panel" aria-labelledby="gap-title">
    <div className="section-heading"><div><p className="eyebrow"><span className="section-index">02</span><Icon name="expand" size={12} />GAP FINDER</p><div className="heading-with-help"><h2 id="gap-title">Gaps in the observed range.</h2><HelpTip label="About observed price gaps"><p>Empty interior price bands must be bracketed by bands containing observed listings. Prices use one usable latest observation per listing, in GBP per 100 g.</p><p>Gaps depend on the cohort, displayed price range and band resolution. They describe collected observations, not unmet demand or a profitable opportunity.</p>{data && <><p>{number(data.histogram.belowRangeCount + data.histogram.aboveRangeCount)} usable priced listings are outside this chart range. Brand comparisons continue to use the full filtered cohort.</p><p>{data.method.gapMeaning}</p></>}<p>This section uses observed prices, independently of the chart’s fictional pricing scores.</p></HelpTip></div></div>{gaps?.status === "ready" && !loading && <span className="analysis-count">{gaps.items.length}<span>band{gaps.items.length === 1 ? "" : "s"}</span></span>}</div>
    {loading ? <Loading text="Checking the observed price range…" /> : error ? <ErrorState message={error} onRetry={onRetry} /> : data && gaps ? <>
      <div className="gap-cohort-summary"><div><strong>{number(gaps.analyzedPricedCount)}</strong><span>listings in chart range</span></div><div><strong>{number(gaps.distinctPriceCount)}</strong><span>distinct prices in range</span></div><div><strong>{data.histogram.binCount}</strong><span>price bands</span></div></div>
      {gaps.status !== "ready" ? <div className="analysis-empty"><span className="analysis-empty-icon"><Icon name="expand" size={25} /></span><h3>{gaps.status === "insufficient_sample" ? "Insufficient priced listings." : "Insufficient price variation."}</h3><p>{gaps.reason || "There is not enough observed price variation to identify interior gaps."}</p><span className="analysis-readiness">Minimum: {gaps.minimumPricedCount} priced listings · {gaps.minimumDistinctPrices} distinct prices</span></div> : gaps.items.length === 0 ? <div className="analysis-empty"><span className="analysis-empty-icon"><Icon name="grid" size={25} /></span><div className="heading-with-help"><h3>No empty interior bands.</h3><HelpTip label="About this gap result"><p>Every interior price band contains observed listings at the current resolution. Changing the cohort or chart range can change this result.</p></HelpTip></div></div> : <>
        <ol className="gap-list" aria-label="Empty interior price bands">{visible.map(({ gap, index }) => <li key={`${gap.lower}-${gap.upper}`} className={`gap-card ${activeGap === index ? "is-active" : ""}`}>
          <div className="gap-card-heading"><span className="gap-index">{String(index + 1).padStart(2, "0")}</span><span className="gap-empty-tag">0 observed listings</span></div>
          <div className="gap-price-range"><span className="gap-range-mark" aria-hidden="true"><i /><i /></span><strong>{money(gap.lower)} <span>to &lt;</span> {money(gap.upper)}</strong><span>/100 g</span></div>
          <div className="gap-neighbours"><span>{number(gap.leftListingCount)} listings in the adjacent lower band</span><span>{number(gap.rightListingCount)} in the adjacent upper band</span></div>
          <div className="gap-card-footer"><span>{gap.emptyBinCount} consecutive empty band{gap.emptyBinCount === 1 ? "" : "s"}</span>{onFocusGap && <button className="text-button" aria-pressed={activeGap === index} onClick={() => onFocusGap(activeGap === index ? null : index)}>{activeGap === index ? "Clear highlight" : "Show on chart"}<Icon name={activeGap === index ? "close" : "arrow"} size={12} /></button>}</div>
        </li>)}</ol>
        {gaps.items.length > 3 && <button className="analysis-show-all" onClick={() => setShowAll(!showAll)}>{showAll ? "Show fewer gaps" : `Show all ${gaps.items.length} empty bands`}<Icon name="chevron" size={13} style={{ transform: showAll ? "rotate(-90deg)" : "rotate(90deg)" }} /></button>}
      </>}
    </> : <div className="analysis-empty"><p>Price-band analysis unavailable.</p></div>}
  </section>;
}

export function BrandAnalysis({ data, loading, error, onRetry }: AnalysisProps) {
  const [showAll, setShowAll] = useState(false);
  const analysis = data?.brandAnalysis;
  const minimum = Math.max(3, analysis?.minimumPricedCount || 3);
  const ranking = (analysis?.ranking || []).filter(brand => brand.pricedCount >= minimum);
  const shown = showAll ? ranking : ranking.slice(0, 8);
  const median = data?.summary?.median ?? null;
  const axisMax = Math.max(median || 0, ...ranking.map(brand => brand.median), 0.01) * 1.05;
  const baseline = median === null ? null : median / axisMax * 100;

  return <section id="brand-analysis" className="brand-analysis panel analysis-panel" aria-labelledby="brand-analysis-title">
    <div className="section-heading"><div><p className="eyebrow"><span className="section-index">03</span><Icon name="layers" size={12} />BRAND PRICE POSITION</p><div className="heading-with-help"><h2 id="brand-analysis-title">Brands standing out on price.</h2><HelpTip label="About brand price positions"><p>Brands are ordered by median observed GBP per 100 g. Each needs at least {minimum} usable priced listings. Percentages compare a brand’s median with the full filtered cohort median.</p><p>Higher median price describes positioning. It does not measure sales, profit, quality or a trait-adjusted brand effect, and is independent of the fictional demo score.</p>{data && analysis && <><p>{number(analysis.excludedBrandCount)} named brands have fewer than {minimum} usable priced listings. {number(data.unknownBrandPricedCount)} priced listings have no supported brand and remain in the cohort reference.</p>{analysis.truncatedBrandCount > 0 && <p>The highest {ranking.length} brand medians are listed; {number(analysis.truncatedBrandCount)} further eligible brands are outside this list.</p>}<p>{data.method.brandMeaning}</p><p>{data.method.observationBasis}</p></>}</HelpTip></div></div><span className="tag lilac">Higher median first</span></div>
    {loading ? <Loading text="Comparing observed brand prices…" /> : error ? <ErrorState message={error} onRetry={onRetry} /> : data && analysis ? <>
      <div className="brand-reference"><div><span className="eyebrow">COHORT MEDIAN</span><strong>{median === null ? "Unavailable" : money(median)}{median !== null && <span>/100 g</span>}</strong></div><p>{number(data.pricedCount)} priced listings<span>{number(analysis.eligibleBrandCount)} brands with at least {minimum} priced listings</span></p></div>
      {analysis.status !== "ready" || shown.length === 0 ? <div className="analysis-empty"><span className="analysis-empty-icon"><Icon name="layers" size={25} /></span><h3>No brands meet the sample threshold.</h3><p>{analysis.reason || `Each brand needs at least ${minimum} listings with a usable observed unit price to enter this ranking.`}</p><span className="analysis-readiness">{number(analysis.totalNamedBrands)} named brands in the priced cohort · minimum n = {minimum} per brand.</span></div> : <>
        <div className="table-scroll brand-table-scroll" tabIndex={0} aria-label="Brands ranked by median observed unit price"><table className="brand-price-table"><caption className="sr-only">Brand price position among filtered source listings. Higher median price is descriptive and does not measure performance, sales or profit. Each brand needs at least {minimum} priced listings.</caption><thead><tr><th scope="col">Brand / priced listings</th><th scope="col">Median <span>£ /100 g</span></th><th scope="col">vs cohort median</th><th scope="col"><span className="label-with-help">High outliers<HelpTip label="About high price outliers"><p>Counts use the full cohort’s upper price fence: Q3 + 1.5 × IQR.</p>{data.summary && <p>Current upper fence: {money(data.summary.upperFence)} /100 g.</p>}<p>{data.method.outlierMethod}</p></HelpTip></span></th></tr></thead><tbody>{shown.map((brand, index) => <tr key={brand.brand}><th scope="row"><div className="brand-identity"><span className="brand-rank">{String(index + 1).padStart(2, "0")}</span><div><span className="brand-name" title={brand.brand}>{brand.brand}</span><span className="brand-sample">n = {number(brand.pricedCount)} listings</span></div></div><div className="brand-position-track" role="img" aria-label={`Brand median ${money(brand.median)} per 100 grams; cohort median ${median === null ? "unavailable" : money(median)}`}><span style={{ width: `${brand.median / axisMax * 100}%` }} />{baseline !== null && <i style={{ left: `${baseline}%` }} />}</div></th><td className="brand-median">{money(brand.median)}</td><td><span className={`brand-relative ${brand.premiumPercent > 0 ? "above-median" : brand.premiumPercent < 0 ? "below-median" : "at-median"}`}>{percentLabel(brand.premiumPercent)}</span></td><td><span className={`brand-outlier-count ${brand.highOutlierCount ? "has-outliers" : ""}`}>{number(brand.highOutlierCount)}</span><span className="brand-outlier-denominator"> / {number(brand.pricedCount)}</span></td></tr>)}</tbody></table></div>
        <div className="brand-rank-footer"><span className="brand-reference-key"><i />Cohort median reference</span><span>{shown.length} of {number(analysis.eligibleBrandCount)} eligible brands shown</span></div>
        {ranking.length > 8 && <button className="analysis-show-all" onClick={() => setShowAll(!showAll)}>{showAll ? "Show top 8 brands" : `Show all ${ranking.length} listed brands`}<Icon name="chevron" size={13} style={{ transform: showAll ? "rotate(-90deg)" : "rotate(90deg)" }} /></button>}
      </>}
    </> : <div className="analysis-empty"><p>Brand price positions unavailable.</p></div>}
  </section>;
}
