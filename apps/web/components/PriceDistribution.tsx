"use client";

import { useState } from "react";
import type { AnalysisResponse, Coverage, FieldDefinition } from "../lib/contracts";
import type { ConfiguredProductMarker } from "../lib/client/product-draft";
import { money, number } from "../lib/client/display";
import { familyColor, familyLabel } from "../lib/client/families";
import { buildTraitDrilldown } from "../lib/client/trait-drilldown";
import { ErrorState, Icon, Loading } from "./Icons";
import { HelpTip } from "./HelpTip";

interface Props {
  data: AnalysisResponse | null; loading: boolean; error: string | null; onRetry: () => void;
  activeFamily: string | null; onClearFamily: () => void; activeGap: number | null;
  range: "core" | "full"; onRange: (range: "core" | "full") => void;
  configuredProduct?: ConfiguredProductMarker | null;
  fields?: readonly FieldDefinition[]; coverage?: Record<string, Coverage>;
  highlightKey?: string | null; onHighlight?: (key: string | null) => void;
}

export function PriceDistribution({ data, loading, error, onRetry, activeFamily, onClearFamily, activeGap, range, onRange, configuredProduct = null, fields = [], coverage, highlightKey = null, onHighlight }: Props) {
  const [selection, setSelection] = useState<{ response: AnalysisResponse; index: number } | null>(null);
  const bins = data?.histogram.bins || [];
  const scores = data?.demoScores;
  const selected = selection?.response === data ? bins[selection.index] : bins.find(bin => bin.count > 0);
  const drilldown = activeFamily && data ? buildTraitDrilldown(data, fields, coverage, activeFamily) : null;
  const scoreBins = activeFamily ? drilldown?.bins || [] : (scores?.bins || []).map(bin => ({ ...bin, contributions: bin.families }));
  const selectedScore = selected ? scoreBins.find(bin => bin.index === selected.index) : null;
  const series = activeFamily ? drilldown?.series || [] : (scores?.families || []).map(key => ({ key, label: familyLabel(key), color: familyColor(key) }));
  const highlighted = series.some(item => item.key === highlightKey) ? highlightKey : null;
  const scoreMax = activeFamily ? Math.max(10, Math.ceil(Math.max(0, ...scoreBins.map(bin => bin.score ?? 0)) / 10) * 10) : 100;
  const plot = { x: 66, y: 40, width: 830, height: 286 };
  const gap = activeGap === null ? null : data?.gaps.items[activeGap];
  const rangeMin = data?.histogram.lower ?? 0, rangeMax = data?.histogram.upper ?? 1;
  const priceX = (price: number) => plot.x + (price - rangeMin) / (rangeMax - rangeMin || 1) * plot.width;
  const barWidth = plot.width / (bins.length || 1);
  const opacity = (key: string) => highlighted && highlighted !== key ? .18 : 1;
  const configuredValid = configuredProduct !== null && Number.isFinite(configuredProduct.price) && configuredProduct.price > 0 &&
    Number.isFinite(configuredProduct.score) && configuredProduct.score >= 0 && configuredProduct.score <= 100;
  const configuredName = typeof configuredProduct?.name === "string" && configuredProduct.name.trim() ? configuredProduct.name.trim() : "Your product";
  const chartReady = !loading && !error && data?.histogram.status === "ready" && bins.length > 0 && Boolean(scores) && (!activeFamily || Boolean(drilldown)) &&
    Number.isFinite(rangeMin) && Number.isFinite(rangeMax) && rangeMax > rangeMin;
  const configuredInRange = configuredValid && configuredProduct.price >= rangeMin && configuredProduct.price <= rangeMax;
  const showMarker = chartReady && configuredInRange && !activeFamily;
  const showPriceGuide = chartReady && configuredInRange && Boolean(activeFamily);
  const markerX = showMarker || showPriceGuide ? priceX(configuredProduct!.price) : 0;
  const markerY = showMarker ? plot.y + plot.height - configuredProduct!.score / 100 * plot.height : 0;
  const markerLabelX = markerX > plot.x + plot.width * .66 ? markerX - 174 : markerX + 14;
  const markerLabelY = markerY < plot.y + 38 ? markerY + 14 : markerY - 35;
  const targetBand = showMarker ? bins.find(bin => configuredProduct!.price >= bin.lower &&
    (bin.upperInclusive ? configuredProduct!.price <= bin.upper : configuredProduct!.price < bin.upper)) : undefined;
  const configuredOutside = configuredValid && chartReady && !configuredInRange;
  const outsideStatus = configuredOutside ? `${configuredProduct.price < rangeMin ? "Below" : "Above"} the ${data?.histogram.range === "full" ? "full observed price range" : "displayed core price range"}. Your marker is not plotted.` : "";
  const markerDescription = configuredValid ? `${configuredName}: ${money(configuredProduct.price)} per 100g; manual demo score ${configuredProduct.score.toFixed(1)} out of 100. No pricing model is connected.` : "";
  const configuredStatus = !configuredValid ? "Enter a positive price per 100g and a demo score from 0 to 100 to preview a position."
    : loading ? "Waiting for the current price range. Preview position is not shown."
    : error ? "Price analysis is unavailable. Preview position is not shown."
    : !chartReady ? "Price bands are unavailable for this cohort. Preview position is not shown."
    : activeFamily ? `${configuredOutside ? `${outsideStatus} ` : "Your price is shown as a vertical guide without a score position. "}Return to All families to see your total demo score position.`
    : configuredOutside ? outsideStatus
    : targetBand ? `Preview in ${money(targetBand.lower)} to ${targetBand.upperInclusive ? "including" : "below"} ${money(targetBand.upper)} /100g: ${number(targetBand.count)} observed listing${targetBand.count === 1 ? "" : "s"}.`
    : "Preview position is shown on the current price range.";

  return <section id="landscape" className="price-distribution panel" aria-labelledby="landscape-title">
    <div className="section-heading"><div><p className="eyebrow"><span className="section-index">01</span> PRICE DISTRIBUTION</p><div className="heading-with-help"><h2 id="landscape-title">Pricing, piece by piece.</h2><HelpTip label="About pricing scores and the chart"><p>X shows observed pricing in pounds per 100g. All families shows a 0–100 demonstration pricing score, averaged across listings in each price band.</p><p>Every score and coloured family layer is fictional and generated reproducibly from listing IDs. They are not derived from product traits, observed prices or a fitted pricing model.</p><p>Selecting a family replaces the stacks with that family’s fictional score, split into its top 10 traits by known evidence count in the current cohort. Remaining traits are grouped as Other traits. The split uses stable fictional weights, not measured effects or model importance; all pieces add to the original family layer.</p><p>The family score axis rescales to show the smaller contributions. Legend buttons highlight a colour independently of the selected family. Empty price bands have no score; they are not scored as zero.</p>{scores && <p>{scores.definition}</p>}<p>{data ? `${number(data.pricedCount)} of ${number(data.totalMatched)} matching listings have usable prices; ${number(data.excludedPriceCount)} remain in the matrix without a plotted price.` : "All matching listings are analysed, independently of matrix pagination."} Price context remains unreviewed. Gap and brand analyses use observed prices only.</p></HelpTip></div></div><span className="tag demo-score-badge">DEMO SCORES · FICTIONAL</span></div>
    <div className="distribution-range"><div role="group" aria-label="Price chart range"><button aria-pressed={range === "core"} onClick={() => onRange("core")}>Core range</button><button aria-pressed={range === "full"} onClick={() => onRange("full")}>Full range</button></div><HelpTip label="About the price range"><p>Core range uses the full cohort’s Q1 − 1.5 × IQR to Q3 + 1.5 × IQR bounds. Full range includes every usable observed price. Brand rankings always use the full filtered cohort.</p>{data?.histogram.rangeFallbackReason && <p>{data.histogram.rangeFallbackReason}</p>}<p>{data ? `${number(data.histogram.plottedCount)} priced listings in this view; ${number(data.histogram.belowRangeCount)} below and ${number(data.histogram.aboveRangeCount)} above.` : "The chart updates with your cohort."}</p></HelpTip><span>{data ? `${number(data.histogram.plottedCount)} listings · ${number(data.histogram.belowRangeCount + data.histogram.aboveRangeCount)} outside view` : "Loading…"}</span>{activeFamily && <button className="text-button clear-family" onClick={onClearFamily}>All families <Icon name="close" size={12} /></button>}</div>
    {activeFamily && <div className="distribution-drilldown" role="status"><strong>{familyLabel(activeFamily)} traits</strong><span>{drilldown ? `${series.length - (drilldown.remainingCount ? 1 : 0)} traits${drilldown.remainingCount ? ` + ${drilldown.remainingCount} in Other traits` : ""} · fictional split of the family score` : "Trait breakdown unavailable"}</span><span>{coverage ? "Top traits by known evidence count" : "Alphabetical trait order · coverage unavailable"}</span></div>}
    {configuredProduct && <div className={`configured-product-summary ${configuredOutside ? "is-outside" : ""}`} role="status" aria-live="polite">
      <div className="configured-product-summary-heading"><span className="configured-product-key" aria-hidden="true">◇</span><strong>{configuredName}</strong><span className="tag configured-product-demo">MANUAL DEMO</span><HelpTip label="About your configured product preview"><p>The diamond uses your entered price per 100g and your manually chosen 0–100 total demo score. It is independent of the family bars, whose fictional scores are seeded from observed listing IDs.</p><p>Inside a family, only a vertical price guide is shown. Your total manual score cannot be interpreted as a family score; return to All families to see the diamond.</p><p>No pricing model is connected. Changing this preview does not add an observed listing or change price bands, gaps, brand rankings or evidence.</p><p>A marker outside the displayed range is not drawn or clamped to a different price. Full range covers observed prices and may still exclude your configured price.</p></HelpTip></div>
      {configuredValid && <div className="configured-product-numbers"><span><strong>{money(configuredProduct.price)}</strong> /100g</span><span>Manual demo score <strong>{configuredProduct.score.toFixed(1)} /100</strong></span></div>}
      <p className="configured-product-status">{configuredStatus}</p><p className="configured-product-model-note">Manual preview · no pricing model connected.</p>
      {activeFamily && <button type="button" className="text-button configured-product-all-families" onClick={onClearFamily}>Show total demo score <Icon name="arrow" size={12} /></button>}
      {configuredOutside && range === "core" && <button type="button" className="text-button configured-product-full-range" onClick={() => onRange("full")}>Try full observed range <Icon name="arrow" size={12} /></button>}
    </div>}
    <div className="distribution-body" aria-busy={loading}>
      {loading ? <Loading text="Loading pricing…" /> : error ? <ErrorState message={error} onRetry={onRetry} /> : data && bins.length > 0 && scores && (!activeFamily || drilldown) ? <>
        <div className="distribution-chart-scroll" tabIndex={0} aria-label="Scrollable demo pricing score chart">
          <svg className="distribution-chart" viewBox="0 0 930 395" role="group" aria-label={`${activeFamily ? `${familyLabel(activeFamily)} family demo score` : "Demonstration pricing score"} from 0 to ${scoreMax} on Y; observed price in pounds per 100 grams on X. Each bar averages fictional scores for a price band. Colours show fictional ${activeFamily ? "trait splits of this family’s contribution" : "family contributions"}. ${data.histogram.plottedCount} observed listings in view.`}>
            <text x={plot.x} y={20} className="chart-axis-title">{activeFamily ? "FAMILY SCORE · DEMO" : "PRICING SCORE · DEMO"}</text>
            {[0, .25, .5, .75, 1].map(fraction => { const value = fraction * scoreMax, y = plot.y + plot.height - fraction * plot.height; return <g key={value}><line x1={plot.x} x2={plot.x + plot.width} y1={y} y2={y} className="chart-grid-line" /><text x={plot.x - 12} y={y + 4} textAnchor="end" className="chart-tick">{value}</text></g>; })}
            {gap && <g className="price-gap-band"><rect x={priceX(gap.lower)} y={plot.y} width={Math.max(1, priceX(gap.upper) - priceX(gap.lower))} height={plot.height} fill="#efba78" fillOpacity=".12" stroke="#efba78" strokeDasharray="4 5" /><title>Observed price gap: {money(gap.lower)} to below {money(gap.upper)} per 100g</title></g>}
            {bins.map((bin, index) => {
              const x = plot.x + index * barWidth + 3;
              const demo = scoreBins.find(item => item.index === bin.index);
              let cumulative = 0;
              return <g key={index} className={`distribution-bin ${selected?.index === index ? "is-selected" : ""}`} role="button" tabIndex={0} aria-pressed={selected?.index === index} aria-label={`${money(bin.lower)} to ${bin.upperInclusive ? "including" : "below"} ${money(bin.upper)} per 100g. ${bin.count} listings. ${demo?.score == null ? "No demo score" : activeFamily ? `Mean fictional ${familyLabel(activeFamily)} contribution ${demo.score.toFixed(1)} demo points` : `Mean demo pricing score ${demo.score.toFixed(1)} out of 100`}.`} onMouseEnter={() => setSelection({ response: data, index })} onFocus={() => setSelection({ response: data, index })} onClick={() => setSelection({ response: data, index })} onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelection({ response: data, index }); } }}>
                <rect x={x - 1} y={plot.y} width={barWidth - 4} height={plot.height} fill="transparent" className="distribution-bin-target" />
                {series.map(item => {
                  const contribution = demo?.contributions[item.key] || 0;
                  cumulative += contribution;
                  return contribution > 0 ? <rect key={item.key} x={x} y={plot.y + plot.height - cumulative / scoreMax * plot.height} width={barWidth - 6} height={contribution / scoreMax * plot.height} fill={item.color} fillOpacity={opacity(item.key)}><title>{item.label}: {contribution.toFixed(1)} demo points</title></rect> : null;
                })}
                {bin.count === 0 && <line x1={x + 4} x2={x + barWidth - 10} y1={plot.y + plot.height - 2} y2={plot.y + plot.height - 2} stroke="#64737e" strokeWidth="2"><title>No observations; no score</title></line>}
              </g>;
            })}
            {showMarker && <g className="configured-product-marker" role="img" tabIndex={0} aria-label={markerDescription}>
              <title>{markerDescription}</title>
              <line className="configured-product-crosshair" x1={markerX} x2={markerX} y1={plot.y} y2={plot.y + plot.height} />
              <line className="configured-product-crosshair" x1={plot.x} x2={plot.x + plot.width} y1={markerY} y2={markerY} />
              <g className="configured-product-point" transform={`translate(${markerX} ${markerY})`}><polygon className="configured-product-diamond-outline" points="0,-12 12,0 0,12 -12,0" /><polygon className="configured-product-diamond" points="0,-8 8,0 0,8 -8,0" /></g>
              <g className="configured-product-marker-label"><rect x={markerLabelX} y={markerLabelY} width={160} height={24} rx={4} /><text x={markerLabelX + 9} y={markerLabelY + 16}>YOUR PRODUCT · DEMO</text></g>
            </g>}
            {showPriceGuide && <g className="configured-product-price-guide" role="img" aria-label={`${configuredName}: ${money(configuredProduct!.price)} per 100g. Price guide only; no family score assigned.`}>
              <title>{configuredName}: {money(configuredProduct!.price)} /100g. Your total demo score is only shown in All families.</title>
              <line className="configured-product-crosshair" x1={markerX} x2={markerX} y1={plot.y} y2={plot.y + plot.height} />
              <g className="configured-product-marker-label"><rect x={markerX > plot.x + plot.width * .8 ? markerX - 104 : markerX + 10} y={plot.y + 8} width={94} height={24} rx={4} /><text x={markerX > plot.x + plot.width * .8 ? markerX - 95 : markerX + 19} y={plot.y + 24}>YOUR PRICE</text></g>
            </g>}
            {Array.from({ length: 6 }, (_, index) => <text key={index} x={plot.x + index / 5 * plot.width} y={plot.y + plot.height + 25} textAnchor={index === 0 ? "start" : index === 5 ? "end" : "middle"} className="chart-tick">{money(rangeMin + index / 5 * (rangeMax - rangeMin))}</text>)}
            <text x={plot.x + plot.width / 2} y={383} textAnchor="middle" className="chart-axis-title">PRICING · £ /100g</text>
          </svg>
        </div>
        <div className="distribution-legend" aria-label={activeFamily ? `${familyLabel(activeFamily)} demo trait contributions` : "Demo family contributions"}>{series.map(item => <button type="button" key={item.key} className="distribution-legend-button" style={{ opacity: highlighted && highlighted !== item.key ? .5 : 1 }} aria-pressed={highlighted === item.key} disabled={!onHighlight} onClick={() => onHighlight?.(highlighted === item.key ? null : item.key)}><i style={{ background: item.color }} />{item.label}</button>)}</div>
        <div className="distribution-bin-detail" aria-live="polite">{selected && <><strong>{money(selected.lower)} – {money(selected.upper)} /100g</strong><span>{number(selected.count)} listings · {selectedScore?.score == null ? "No score" : activeFamily ? `${familyLabel(activeFamily)} demo contribution ${selectedScore.score.toFixed(1)} points` : `Demo score ${selectedScore.score.toFixed(1)} /100`}</span><HelpTip label="About this selected price band"><p>{selected.upperInclusive ? "The upper boundary is included." : "The upper boundary is excluded."} Scores are fictional per-listing values averaged in this band. {activeFamily && "Trait colours partition this family’s fictional contribution; they do not measure trait importance. "}Hover, tap or keyboard-focus a different bar to inspect it.</p></HelpTip>{selectedScore?.score != null && <div>{series.map(item => <span key={item.key}><i style={{ background: item.color }} />{item.label} <strong>{(selectedScore.contributions[item.key] || 0).toFixed(1)}</strong></span>)}</div>}</>}</div>
        {gap && <p className="distribution-gap-note">Price gap · {money(gap.lower)} – &lt; {money(gap.upper)} /100g</p>}
      </> : data ? <div className="empty-state"><Icon name="grid" size={28} /><h3>{data.pricedCount && !scores ? "Demo scores unavailable." : activeFamily && !drilldown && data.pricedCount ? "Family trait breakdown unavailable." : data.pricedCount ? "One observed price in this cohort." : "No usable prices in this cohort."}</h3><HelpTip label="About unavailable chart values"><p>{data.pricedCount && !scores ? "The response contains no demo score data. Listing counts are never used as scores." : activeFamily && !drilldown && data.pricedCount ? "This family has no matching schema traits or demo contribution. Return to All families to see the total score chart." : data.pricedCount ? "Broaden the cohort to display separate price bands." : "Listings with missing or conflicting prices remain available in the matrix."}</p></HelpTip></div> : null}
    </div>
  </section>;
}
