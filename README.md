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
