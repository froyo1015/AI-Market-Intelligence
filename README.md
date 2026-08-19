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
