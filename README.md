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
