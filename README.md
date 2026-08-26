# AI-Market-Intelligence
AI市場監測與投資研究系統

## Evidence Foundation (Phase 6.1)

The existing market snapshot can be converted into versioned, deterministic
observation and evidence artifacts without any news API, external LLM, UI, or
database:

```bash
python -m src.evidence.pipeline
```

This writes:

- `src/output/observations.json`: canonical market price and feature observations.
- `src/output/evidence.json`: source-linked `market_move` evidence bundles.

The validator rejects unresolved observation/source references, unsupported
numbers, confidence mismatches, and causal claims. Daily bars are evidence of
observed movement only; they do not establish why the movement occurred.

## Macro Evidence Ingestion (Phase 6.2-A)

Generate the bounded DXY, US10Y, VIX, and front-month WTI proxy snapshot:

```bash
python -m src.macro_pipeline
```

Merge it explicitly into the Evidence Foundation:

```bash
python -m src.evidence.pipeline \
  --macro-snapshot src/output/macro_snapshot.json
```

The adapter requires no API key. It isolates failures by instrument and records
provider symbol, source URL, timestamp, price basis, asset mapping, and source
confidence. US10Y changes use basis points; DXY, VIX, and Oil changes use
percent. Oil is a front-month futures proxy rather than a physical spot price.

## Economic Calendar (Phase 6.2-B)

Generate a deterministic list of official BLS releases scheduled in the next
48 hours:

```bash
python -m src.calendar_pipeline
```

This writes `src/output/economic_calendar.json`. Events preserve the official
source URL, scheduled time, retrieval time, content hash, rule-based impact,
and candidate affected assets. The adapter does not infer causality or predict
market direction. This first calendar source covers BLS releases only; Fed,
Treasury, BEA, and private calendars remain explicitly outside its coverage.

## News Source Ingestion (Phase 6.2-C1)

Generate a source-grounded `news_items.json` from the Federal Reserve Board's
official all-press-releases RSS feed:

```bash
python -m src.news_pipeline
```

The first runtime source is Tier 1 and requires no API key. The ingestion
window is the latest 24 hours plus a six-hour overlap. The artifact retains
only feed-supplied headlines, a bounded excerpt, official URLs, publication and
retrieval timestamps, and stable hashes. A valid feed with no current items is
`complete`; access and validation failures are classified explicitly.

This phase does not create events, infer assets, score sentiment, rank news, or
call an LLM. It only collapses exact duplicate source records inside one feed;
cross-publisher and event-level deduplication remain part of C2.

## News Normalization (Phase 6.2-C2)

Convert the validated adapter artifact into canonical, source-traceable events:

```bash
python -m src.events.pipeline
```

- Input: `src/output/news_items.json`
- Output: `src/output/events.json`

The normalizer uses versioned headline rules for Federal Reserve central-bank,
regulatory, and macro-release events. It groups only deterministic near
duplicates, audits unsupported items, and preserves every input/source ID.
Publication time remains source metadata and is not inferred to be event time.
This phase leaves `summary` null and `candidate_assets` empty; it does not add
sentiment, ranking, market impact, LLM extraction, or intelligence.

## Evidence Consolidation (Phase 6.2-D)

Combine the existing factual artifacts into one traceable boundary:

```bash
python -m src.consolidation.pipeline
```

This reads `observations.json`, `evidence.json`, `economic_calendar.json`, and
`events.json`, then writes `src/output/evidence_bundle.json`. Every bundle
retains complete input records, source/observation/event/Evidence IDs, original
timestamps, freshness, data quality, and provenance. Exact duplicate Evidence
facts merge without dropping supporting records. Missing inputs are disclosed
as unavailable coverage and never replaced with synthetic evidence.

The consolidator does not add conclusions, sentiment, direction, predictions,
ranking, trading signals, LLM output, UI changes, or delivery changes.

## Cross-Asset Relationships (Phase 6.3-A)

Evaluate the frozen descriptive rules using only the consolidated artifact:

```bash
python -m src.signals.pipeline
```

Input: `src/output/evidence_bundle.json`
Output: `src/output/market_signals.json`

The output records `observed`, `not_observed`, `stale_data`, or
`insufficient_data` for eight deterministic same-window relationships. Every
value resolves to an input observation and every rule retains bundle, source,
observation, event and Evidence references. “Signal” here means a factual rule
evaluation—not a trade, prediction, sentiment label, ranking, regime, or
bullish/bearish classification.

## Market Regime (Phase 6.3-B)

Classify current observed conditions from the two validated upstream artifacts:

```bash
python -m src.regime.pipeline
```

- Inputs: `src/output/evidence_bundle.json` and
  `src/output/market_signals.json`
- Output: `src/output/market_regime.json`

The deterministic classifier reports `risk_on`, `risk_off`, or `mixed` only
when current evidence meets its coverage rules. Stale or insufficient evidence
produces a null classification instead of treating unknown conditions as
mixed. The artifact preserves all source, observation, event, Evidence, bundle
and signal references. It does not forecast, recommend trades, or emit trading
signals.

## Risk Monitor (Phase 6.3-C)

Generate a deterministic list of observable risk conditions:

```bash
python -m src.risk.pipeline
```

- Inputs: `evidence_bundle.json`, `market_signals.json`, and
  `market_regime.json`
- Output: `src/output/risk_monitor.json`

The monitor separates official events scheduled in the next 48 hours, data
quality problems, and current evidence-backed market stress. Every item keeps
artifact, bundle, source, observation, event, Evidence, Signal and Regime
Dimension references. It does not predict crashes, classify bullish/bearish
conditions, calculate a market forecast, or recommend trades.
