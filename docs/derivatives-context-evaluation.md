# D-6 — Shadow derivatives context evaluation

This offline evaluator reads only a derivatives evidence bundle and a
daily_intelligence_context_v1 wrapper. It writes
`derivatives_context_evaluation.json` exclusively under outputs/shadow/derivatives.
It neither mutates nor executes production consumers.

## Contract and metrics

`derivatives_context_evaluation_v1` contains input hashes, evaluated_at (the
context's declared cutoff, not wall-clock freshness), validation_status,
availability status, metrics, evidence references and normalized errors.

- data_availability: present instrument/metric slots / 4 expected slots
  (BTCUSDT, ETHUSDT; funding_rate, open_interest). Stale presence still counts.
- freshness_success_rate: current facts / all supplied facts, recomputed at
  context cutoff using existing funding interval + 1800s and OI 7200s policy.
- evidence_quality: mean known effective quality (minimum source score capped
  by timeliness), plus known/unknown counts. Not truth or direction confidence.
- provenance_completeness: complete fact provenance chains / fact count.
- current_vs_stale: explicit counts and each fraction of all facts. No division
  by stale count, so all-current data does not produce infinity.
- missing_data_frequency: missing slots / expected slots, sample_count=1.
  This is snapshot coverage frequency, NOT a historical provider failure rate.
  No history is fabricated or accumulated by this phase.

Ratios carry numerator/denominator; zero denominator yields null, not success.
Missing bundle + empty unavailable context is a valid unavailable evaluation.
Malformed/inconsistent input is invalid; quality/availability metrics are null
to avoid suggesting trust in rejected input. No raw input or exception text is
copied into the output. Hashes and evidence IDs retain audit links.

## Validation scope

Check contracts, bundle hash, unique fact IDs, observation/instrument content
hashes, receipt/normalization/capture reference linkage, preserved source records,
context observation values and identities, input artifact links, timestamps,
and recomputed freshness/quality/eligibility. Current and excluded references
must partition the bundle; stale facts cannot enter current context.
Source receipt hashes are retained/linked, not reverified against raw bytes:
these two inputs do not contain original responses. This consistency evaluation
does not replace upstream schema/receipt validation or prove provider authenticity.
Canonical daily intelligence is opaque and is never reinterpreted.

## Execution

`python -m src.shadow.derivatives.context_evaluation --bundle PATH --context PATH
--output outputs/shadow/derivatives/NEW_RUN/derivatives_context_evaluation.json`

Output creation is exclusive; existing artifacts cannot be overwritten. No
workflow/publication integration. The evaluation validator deterministically
rebuilds the result from the same two inputs.
