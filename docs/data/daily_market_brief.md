# Daily Market Intelligence Brief

- Report date: 2026-08-28
- Intelligence status: `unavailable`
- Intelligence run: `run_20260827T172737Z_intelligence_8a26a166b9f81df1`
- Intelligence generated at: 2026-08-27T17:27:37.173176Z
- Input contract: `daily_intelligence_v1`
- Render mode: `deterministic_structured_only`

## Data Quality and Coverage

| Artifact | Run / generated at | Validation | Data | Record freshness | Artifact freshness | Age / max hours | Objects | Warnings |
|---|---|---|---|---|---|---:|---:|---:|
| evidence_bundle.json | `run_20260827T172737Z_consolidated_09d138d0e91042df`<br>2026-08-27T17:27:37.159456Z | validated | unavailable | current | current | 4e-06 / 24.0 | 0 | 5 |
| market_signals.json | `run_20260827T172737Z_relationships_2923ca683ae97030`<br>2026-08-27T17:27:37.160318Z | validated | unavailable | current | current | 4e-06 / 24.0 | 8 | 2 |
| market_regime.json | `run_20260827T172737Z_regime_29a799bae33da2c2`<br>2026-08-27T17:27:37.163872Z | validated | unavailable | current | current | 3e-06 / 24.0 | 1 | 2 |
| risk_monitor.json | `run_20260827T172737Z_risk_513224477d71c4e7`<br>2026-08-27T17:27:37.167543Z | validated | partial | current | current | 2e-06 / 24.0 | 7 | 3 |

### Data Quality Warnings

- upstream_unavailable:evidence_bundle.json
- upstream_unavailable:market_signals.json
- upstream_unavailable:market_regime.json
- upstream_partial:risk_monitor.json
- no_current_substantive_intelligence
- provenance_catalog_empty

### Data Windows

- Composed at: 2026-08-27T17:27:37.173176Z
- Report date: 2026-08-28
- input_generated_at: 2026-08-27T17:27:37.159456Z → 2026-08-27T17:27:37.167543Z
- observed_at: unknown → unknown
- scheduled_at: unknown → unknown
- occurred_at: unknown → unknown
- published_at: unknown → unknown
- retrieved_at: unknown → unknown
- detected_at: 2026-08-27T17:27:37.167543Z → 2026-08-27T17:27:37.167543Z

## Current Market Regime

- Classification: `unknown`
- Classification scope: current_observed_conditions
- Artifact status: `unavailable`
- Confidence label: `insufficient`
- Confidence score: 0.0

### Regime Dimensions

- `equity`: eligibility=`unavailable`, observed_state=`unavailable`, signal=`sig_equity_index_co_movement_v1_ff8d02ef65e2`
- `volatility`: eligibility=`unavailable`, observed_state=`unavailable`, signal=`sig_equity_volatility_inverse_move_v1_f1b870e3f543`
- `crypto`: eligibility=`unavailable`, observed_state=`unavailable`, signal=`sig_crypto_co_movement_v1_53689a02d99c`
- `dollar_yield`: eligibility=`unavailable`, observed_state=`unavailable`, signal=`sig_dollar_yield_co_movement_v1_c4a307baad88`
- `cross_asset_alignment`: eligibility=`unavailable`, observed_state=`unavailable`, signal=`sig_equity_crypto_co_movement_v1_e08cf7ffbcb7`

Regime warnings:

- 5 regime dimension(s) are unavailable.
- Current evidence does not meet classification coverage rules.

Limitations:

- The classification describes current observations only.
- It does not establish causality, persistence, or later outcomes.
- The classifier does not provide investment or trading instructions.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_regime_c5128a5e1164abbb`
- Object type: `market_regime`
- Source artifact: `market_regime.json`
- Source run: `run_20260827T172737Z_regime_29a799bae33da2c2`
- Source generated at: 2026-08-27T17:27:37.163872Z
- Validation status: `validated`
- Data status: `unavailable`
- observed_at: []
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260827T172737Z_consolidated_09d138d0e91042df`, `run_20260827T172737Z_regime_29a799bae33da2c2`, `run_20260827T172737Z_relationships_2923ca683ae97030`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: `sig_crypto_co_movement_v1_53689a02d99c`, `sig_dollar_yield_co_movement_v1_c4a307baad88`, `sig_equity_crypto_co_movement_v1_e08cf7ffbcb7`, `sig_equity_index_co_movement_v1_ff8d02ef65e2`, `sig_equity_volatility_inverse_move_v1_f1b870e3f543`
- Regime dimensions: `cross_asset_alignment`, `crypto`, `dollar_yield`, `equity`, `volatility`
- Risks: none
- Coverage inputs: none

</details>

## Cross-Asset Observations

### BTC-USD and ETH-USD daily co-movement

- Signal ID: `sig_crypto_co_movement_v1_53689a02d99c`
- Rule ID: `crypto_co_movement_v1`
- Relationship: `co_movement`
- State: `insufficient_data`
- Condition met: `unknown`
- Data quality: `unavailable`
- Confidence: `insufficient` (0.0)

Data-quality details:

- conflicting_inputs: []
- issues: ["missing_required_observation"]
- missing_inputs: ["BTC-USD:daily_change_pct","ETH-USD:daily_change_pct"]
- stale_observation_ids: []
- status: unavailable

Observed values:

- None in validated input.

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.
- One or more required observations are unavailable.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_05b8248084a9658d`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260827T172737Z_relationships_2923ca683ae97030`
- Source generated at: 2026-08-27T17:27:37.160318Z
- Validation status: `validated`
- Data status: `insufficient_data`
- observed_at: []
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260827T172737Z_consolidated_09d138d0e91042df`, `run_20260827T172737Z_relationships_2923ca683ae97030`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: `sig_crypto_co_movement_v1_53689a02d99c`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### DXY and major FX quote alignment

- Signal ID: `sig_dollar_fx_quote_alignment_v1_cb0110e8e493`
- Rule ID: `dollar_fx_quote_alignment_v1`
- Relationship: `quote_alignment`
- State: `insufficient_data`
- Condition met: `unknown`
- Data quality: `unavailable`
- Confidence: `insufficient` (0.0)

Data-quality details:

- conflicting_inputs: []
- issues: ["missing_required_observation"]
- missing_inputs: ["DXY:daily_change_pct","EURUSD:daily_change_pct","USDJPY:daily_change_pct"]
- stale_observation_ids: []
- status: unavailable

Observed values:

- None in validated input.

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.
- One or more required observations are unavailable.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_e6652a4e393a4bdb`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260827T172737Z_relationships_2923ca683ae97030`
- Source generated at: 2026-08-27T17:27:37.160318Z
- Validation status: `validated`
- Data status: `insufficient_data`
- observed_at: []
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260827T172737Z_consolidated_09d138d0e91042df`, `run_20260827T172737Z_relationships_2923ca683ae97030`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: `sig_dollar_fx_quote_alignment_v1_cb0110e8e493`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### DXY and US10Y daily co-movement

- Signal ID: `sig_dollar_yield_co_movement_v1_c4a307baad88`
- Rule ID: `dollar_yield_co_movement_v1`
- Relationship: `co_movement`
- State: `insufficient_data`
- Condition met: `unknown`
- Data quality: `unavailable`
- Confidence: `insufficient` (0.0)

Data-quality details:

- conflicting_inputs: []
- issues: ["missing_required_observation"]
- missing_inputs: ["DXY:daily_change_pct","US10Y:daily_change_bps"]
- stale_observation_ids: []
- status: unavailable

Observed values:

- None in validated input.

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.
- One or more required observations are unavailable.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_9b26a0f955e1e534`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260827T172737Z_relationships_2923ca683ae97030`
- Source generated at: 2026-08-27T17:27:37.160318Z
- Validation status: `validated`
- Data status: `insufficient_data`
- observed_at: []
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260827T172737Z_consolidated_09d138d0e91042df`, `run_20260827T172737Z_relationships_2923ca683ae97030`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: `sig_dollar_yield_co_movement_v1_c4a307baad88`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### Equity indexes and BTC-USD daily co-movement

- Signal ID: `sig_equity_crypto_co_movement_v1_e08cf7ffbcb7`
- Rule ID: `equity_crypto_co_movement_v1`
- Relationship: `co_movement`
- State: `insufficient_data`
- Condition met: `unknown`
- Data quality: `unavailable`
- Confidence: `insufficient` (0.0)

Data-quality details:

- conflicting_inputs: []
- issues: ["missing_required_observation"]
- missing_inputs: ["BTC-USD:daily_change_pct","QQQ:daily_change_pct","SPY:daily_change_pct"]
- stale_observation_ids: []
- status: unavailable

Observed values:

- None in validated input.

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.
- One or more required observations are unavailable.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_cf0222f802be82f4`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260827T172737Z_relationships_2923ca683ae97030`
- Source generated at: 2026-08-27T17:27:37.160318Z
- Validation status: `validated`
- Data status: `insufficient_data`
- observed_at: []
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260827T172737Z_consolidated_09d138d0e91042df`, `run_20260827T172737Z_relationships_2923ca683ae97030`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: `sig_equity_crypto_co_movement_v1_e08cf7ffbcb7`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### SPY and QQQ daily co-movement

- Signal ID: `sig_equity_index_co_movement_v1_ff8d02ef65e2`
- Rule ID: `equity_index_co_movement_v1`
- Relationship: `co_movement`
- State: `insufficient_data`
- Condition met: `unknown`
- Data quality: `unavailable`
- Confidence: `insufficient` (0.0)

Data-quality details:

- conflicting_inputs: []
- issues: ["missing_required_observation"]
- missing_inputs: ["QQQ:daily_change_pct","SPY:daily_change_pct"]
- stale_observation_ids: []
- status: unavailable

Observed values:

- None in validated input.

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.
- One or more required observations are unavailable.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_37523896535ca9f2`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260827T172737Z_relationships_2923ca683ae97030`
- Source generated at: 2026-08-27T17:27:37.160318Z
- Validation status: `validated`
- Data status: `insufficient_data`
- observed_at: []
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260827T172737Z_consolidated_09d138d0e91042df`, `run_20260827T172737Z_relationships_2923ca683ae97030`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: `sig_equity_index_co_movement_v1_ff8d02ef65e2`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### SPY and QQQ daily divergence

- Signal ID: `sig_equity_index_divergence_v1_5f45b91736c8`
- Rule ID: `equity_index_divergence_v1`
- Relationship: `divergence`
- State: `insufficient_data`
- Condition met: `unknown`
- Data quality: `unavailable`
- Confidence: `insufficient` (0.0)

Data-quality details:

- conflicting_inputs: []
- issues: ["missing_required_observation"]
- missing_inputs: ["QQQ:daily_change_pct","SPY:daily_change_pct"]
- stale_observation_ids: []
- status: unavailable

Observed values:

- None in validated input.

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.
- One or more required observations are unavailable.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_b5be00a5f39cc0b7`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260827T172737Z_relationships_2923ca683ae97030`
- Source generated at: 2026-08-27T17:27:37.160318Z
- Validation status: `validated`
- Data status: `insufficient_data`
- observed_at: []
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260827T172737Z_consolidated_09d138d0e91042df`, `run_20260827T172737Z_relationships_2923ca683ae97030`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: `sig_equity_index_divergence_v1_5f45b91736c8`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### Equity indexes and VIX inverse daily movement

- Signal ID: `sig_equity_volatility_inverse_move_v1_f1b870e3f543`
- Rule ID: `equity_volatility_inverse_move_v1`
- Relationship: `inverse_movement`
- State: `insufficient_data`
- Condition met: `unknown`
- Data quality: `unavailable`
- Confidence: `insufficient` (0.0)

Data-quality details:

- conflicting_inputs: []
- issues: ["missing_required_observation"]
- missing_inputs: ["QQQ:daily_change_pct","SPY:daily_change_pct","VIX:daily_change_pct"]
- stale_observation_ids: []
- status: unavailable

Observed values:

- None in validated input.

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.
- One or more required observations are unavailable.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_43a76b626a91d701`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260827T172737Z_relationships_2923ca683ae97030`
- Source generated at: 2026-08-27T17:27:37.160318Z
- Validation status: `validated`
- Data status: `insufficient_data`
- observed_at: []
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260827T172737Z_consolidated_09d138d0e91042df`, `run_20260827T172737Z_relationships_2923ca683ae97030`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: `sig_equity_volatility_inverse_move_v1_f1b870e3f543`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### Gold and DXY inverse daily movement

- Signal ID: `sig_gold_dollar_inverse_move_v1_4514042730ae`
- Rule ID: `gold_dollar_inverse_move_v1`
- Relationship: `inverse_movement`
- State: `insufficient_data`
- Condition met: `unknown`
- Data quality: `unavailable`
- Confidence: `insufficient` (0.0)

Data-quality details:

- conflicting_inputs: []
- issues: ["missing_required_observation"]
- missing_inputs: ["DXY:daily_change_pct","GOLD:daily_change_pct"]
- stale_observation_ids: []
- status: unavailable

Observed values:

- None in validated input.

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.
- One or more required observations are unavailable.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_551d1328d1e3a4ad`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260827T172737Z_relationships_2923ca683ae97030`
- Source generated at: 2026-08-27T17:27:37.160318Z
- Validation status: `validated`
- Data status: `insufficient_data`
- observed_at: []
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260827T172737Z_consolidated_09d138d0e91042df`, `run_20260827T172737Z_relationships_2923ca683ae97030`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: `sig_gold_dollar_inverse_move_v1_4514042730ae`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

## Upcoming Event Risks

- None in validated input.

## Data Quality Risks

### Degraded input coverage: existing_evidence

- Risk ID: `rsk_input_coverage_degraded_v1_1cf1af0ddcc53a1e`
- Rule ID: `input_coverage_degraded_v1`
- Category: `data_quality`
- Status: `detected`
- Attention level: `high`
- Description: The consolidated Evidence input reports incomplete or stale coverage.
- Related assets: []

Observed facts:

- artifact: evidence.json
- coverage_status: unavailable
- input_type: existing_evidence
- record_count: 0
- stale_record_count: 0

Time window:

- detected_at: 2026-08-27T17:27:37.167543Z

Limitations:

- This item concerns data reliability, not market prices.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_risk_9f064d3f3ba6a9fb`
- Object type: `data_quality_risk`
- Source artifact: `risk_monitor.json`
- Source run: `run_20260827T172737Z_risk_513224477d71c4e7`
- Source generated at: 2026-08-27T17:27:37.167543Z
- Validation status: `validated`
- Data status: `detected`
- observed_at: []
- scheduled_at: []
- detected_at: ["2026-08-27T17:27:37.167543Z"]

Evidence references:

- Artifact runs: `run_20260827T172737Z_consolidated_09d138d0e91042df`, `run_20260827T172737Z_regime_29a799bae33da2c2`, `run_20260827T172737Z_relationships_2923ca683ae97030`, `run_20260827T172737Z_risk_513224477d71c4e7`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: none
- Regime dimensions: none
- Risks: `rsk_input_coverage_degraded_v1_1cf1af0ddcc53a1e`
- Coverage inputs: `existing_evidence`

</details>

### Degraded input coverage: economic_calendar

- Risk ID: `rsk_input_coverage_degraded_v1_850c5ecba1c7d212`
- Rule ID: `input_coverage_degraded_v1`
- Category: `data_quality`
- Status: `detected`
- Attention level: `high`
- Description: The consolidated Evidence input reports incomplete or stale coverage.
- Related assets: []

Observed facts:

- artifact: economic_calendar.json
- coverage_status: unavailable
- input_type: economic_calendar
- record_count: 0
- stale_record_count: 0

Time window:

- detected_at: 2026-08-27T17:27:37.167543Z

Limitations:

- This item concerns data reliability, not market prices.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_risk_b08232cc9826f1f5`
- Object type: `data_quality_risk`
- Source artifact: `risk_monitor.json`
- Source run: `run_20260827T172737Z_risk_513224477d71c4e7`
- Source generated at: 2026-08-27T17:27:37.167543Z
- Validation status: `validated`
- Data status: `detected`
- observed_at: []
- scheduled_at: []
- detected_at: ["2026-08-27T17:27:37.167543Z"]

Evidence references:

- Artifact runs: `run_20260827T172737Z_consolidated_09d138d0e91042df`, `run_20260827T172737Z_regime_29a799bae33da2c2`, `run_20260827T172737Z_relationships_2923ca683ae97030`, `run_20260827T172737Z_risk_513224477d71c4e7`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: none
- Regime dimensions: none
- Risks: `rsk_input_coverage_degraded_v1_850c5ecba1c7d212`
- Coverage inputs: `economic_calendar`

</details>

### Degraded input coverage: market_observations

- Risk ID: `rsk_input_coverage_degraded_v1_accae6621acac1d4`
- Rule ID: `input_coverage_degraded_v1`
- Category: `data_quality`
- Status: `detected`
- Attention level: `high`
- Description: The consolidated Evidence input reports incomplete or stale coverage.
- Related assets: []

Observed facts:

- artifact: observations.json
- coverage_status: unavailable
- input_type: market_observations
- record_count: 0
- stale_record_count: 0

Time window:

- detected_at: 2026-08-27T17:27:37.167543Z

Limitations:

- This item concerns data reliability, not market prices.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_risk_a22a76dc4d4aca3d`
- Object type: `data_quality_risk`
- Source artifact: `risk_monitor.json`
- Source run: `run_20260827T172737Z_risk_513224477d71c4e7`
- Source generated at: 2026-08-27T17:27:37.167543Z
- Validation status: `validated`
- Data status: `detected`
- observed_at: []
- scheduled_at: []
- detected_at: ["2026-08-27T17:27:37.167543Z"]

Evidence references:

- Artifact runs: `run_20260827T172737Z_consolidated_09d138d0e91042df`, `run_20260827T172737Z_regime_29a799bae33da2c2`, `run_20260827T172737Z_relationships_2923ca683ae97030`, `run_20260827T172737Z_risk_513224477d71c4e7`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: none
- Regime dimensions: none
- Risks: `rsk_input_coverage_degraded_v1_accae6621acac1d4`
- Coverage inputs: `market_observations`

</details>

### Degraded input coverage: news_events

- Risk ID: `rsk_input_coverage_degraded_v1_c0af9ca21691ff9e`
- Rule ID: `input_coverage_degraded_v1`
- Category: `data_quality`
- Status: `detected`
- Attention level: `high`
- Description: The consolidated Evidence input reports incomplete or stale coverage.
- Related assets: []

Observed facts:

- artifact: events.json
- coverage_status: unavailable
- input_type: news_events
- record_count: 0
- stale_record_count: 0

Time window:

- detected_at: 2026-08-27T17:27:37.167543Z

Limitations:

- This item concerns data reliability, not market prices.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_risk_3e27d6138c9912df`
- Object type: `data_quality_risk`
- Source artifact: `risk_monitor.json`
- Source run: `run_20260827T172737Z_risk_513224477d71c4e7`
- Source generated at: 2026-08-27T17:27:37.167543Z
- Validation status: `validated`
- Data status: `detected`
- observed_at: []
- scheduled_at: []
- detected_at: ["2026-08-27T17:27:37.167543Z"]

Evidence references:

- Artifact runs: `run_20260827T172737Z_consolidated_09d138d0e91042df`, `run_20260827T172737Z_regime_29a799bae33da2c2`, `run_20260827T172737Z_relationships_2923ca683ae97030`, `run_20260827T172737Z_risk_513224477d71c4e7`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: none
- Regime dimensions: none
- Risks: `rsk_input_coverage_degraded_v1_c0af9ca21691ff9e`
- Coverage inputs: `news_events`

</details>

### Degraded input coverage: macro_observations

- Risk ID: `rsk_input_coverage_degraded_v1_d473656ecece5f8e`
- Rule ID: `input_coverage_degraded_v1`
- Category: `data_quality`
- Status: `detected`
- Attention level: `high`
- Description: The consolidated Evidence input reports incomplete or stale coverage.
- Related assets: []

Observed facts:

- artifact: observations.json
- coverage_status: unavailable
- input_type: macro_observations
- record_count: 0
- stale_record_count: 0

Time window:

- detected_at: 2026-08-27T17:27:37.167543Z

Limitations:

- This item concerns data reliability, not market prices.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_risk_a3bc41dc6c6ac48f`
- Object type: `data_quality_risk`
- Source artifact: `risk_monitor.json`
- Source run: `run_20260827T172737Z_risk_513224477d71c4e7`
- Source generated at: 2026-08-27T17:27:37.167543Z
- Validation status: `validated`
- Data status: `detected`
- observed_at: []
- scheduled_at: []
- detected_at: ["2026-08-27T17:27:37.167543Z"]

Evidence references:

- Artifact runs: `run_20260827T172737Z_consolidated_09d138d0e91042df`, `run_20260827T172737Z_regime_29a799bae33da2c2`, `run_20260827T172737Z_relationships_2923ca683ae97030`, `run_20260827T172737Z_risk_513224477d71c4e7`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: none
- Regime dimensions: none
- Risks: `rsk_input_coverage_degraded_v1_d473656ecece5f8e`
- Coverage inputs: `macro_observations`

</details>

### Current market regime coverage degraded

- Risk ID: `rsk_market_regime_coverage_degraded_v1_20d52c4a1b0f550c`
- Rule ID: `market_regime_coverage_degraded_v1`
- Category: `data_quality`
- Status: `detected`
- Attention level: `high`
- Description: The current-condition classifier reports partial or insufficient eligible coverage.
- Related assets: []

Observed facts:

- artifact_status: unavailable
- classification: unknown
- eligible_dimension_count: 0
- eligible_weight: 0.0

Time window:

- detected_at: 2026-08-27T17:27:37.167543Z

Limitations:

- No unavailable regime is treated as mixed.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_risk_6db037225cbfe23d`
- Object type: `data_quality_risk`
- Source artifact: `risk_monitor.json`
- Source run: `run_20260827T172737Z_risk_513224477d71c4e7`
- Source generated at: 2026-08-27T17:27:37.167543Z
- Validation status: `validated`
- Data status: `detected`
- observed_at: []
- scheduled_at: []
- detected_at: ["2026-08-27T17:27:37.167543Z"]

Evidence references:

- Artifact runs: `run_20260827T172737Z_consolidated_09d138d0e91042df`, `run_20260827T172737Z_regime_29a799bae33da2c2`, `run_20260827T172737Z_relationships_2923ca683ae97030`, `run_20260827T172737Z_risk_513224477d71c4e7`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: `sig_crypto_co_movement_v1_53689a02d99c`, `sig_dollar_yield_co_movement_v1_c4a307baad88`, `sig_equity_crypto_co_movement_v1_e08cf7ffbcb7`, `sig_equity_index_co_movement_v1_ff8d02ef65e2`, `sig_equity_volatility_inverse_move_v1_f1b870e3f543`
- Regime dimensions: `cross_asset_alignment`, `crypto`, `dollar_yield`, `equity`, `volatility`
- Risks: `rsk_market_regime_coverage_degraded_v1_20d52c4a1b0f550c`
- Coverage inputs: none

</details>

### Cross-asset relationship coverage degraded

- Risk ID: `rsk_market_signal_coverage_degraded_v1_19d895dc003dad90`
- Rule ID: `market_signal_coverage_degraded_v1`
- Category: `data_quality`
- Status: `detected`
- Attention level: `high`
- Description: One or more cross-asset relationship evaluations are stale or incomplete.
- Related assets: []

Observed facts:

- artifact_status: unavailable
- state_counts: {"insufficient_data":8,"not_observed":0,"observed":0,"stale_data":0}

Time window:

- detected_at: 2026-08-27T17:27:37.167543Z

Limitations:

- This item concerns analytical coverage only.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_risk_4bdb10474b452e59`
- Object type: `data_quality_risk`
- Source artifact: `risk_monitor.json`
- Source run: `run_20260827T172737Z_risk_513224477d71c4e7`
- Source generated at: 2026-08-27T17:27:37.167543Z
- Validation status: `validated`
- Data status: `detected`
- observed_at: []
- scheduled_at: []
- detected_at: ["2026-08-27T17:27:37.167543Z"]

Evidence references:

- Artifact runs: `run_20260827T172737Z_consolidated_09d138d0e91042df`, `run_20260827T172737Z_regime_29a799bae33da2c2`, `run_20260827T172737Z_relationships_2923ca683ae97030`, `run_20260827T172737Z_risk_513224477d71c4e7`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: `sig_crypto_co_movement_v1_53689a02d99c`, `sig_dollar_fx_quote_alignment_v1_cb0110e8e493`, `sig_dollar_yield_co_movement_v1_c4a307baad88`, `sig_equity_crypto_co_movement_v1_e08cf7ffbcb7`, `sig_equity_index_co_movement_v1_ff8d02ef65e2`, `sig_equity_index_divergence_v1_5f45b91736c8`, `sig_equity_volatility_inverse_move_v1_f1b870e3f543`, `sig_gold_dollar_inverse_move_v1_4514042730ae`
- Regime dimensions: none
- Risks: `rsk_market_signal_coverage_degraded_v1_19d895dc003dad90`
- Coverage inputs: none

</details>

## Observed Market Stress

- None in validated input.

## Sources and Provenance

### Input Runs

- evidence_bundle_run_id: `run_20260827T172737Z_consolidated_09d138d0e91042df`
- market_signals_run_id: `run_20260827T172737Z_relationships_2923ca683ae97030`
- market_regime_run_id: `run_20260827T172737Z_regime_29a799bae33da2c2`
- risk_monitor_run_id: `run_20260827T172737Z_risk_513224477d71c4e7`

### Source Registry

- None in validated input.

### Provenance Catalog IDs

- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence records: none

## Scope Limitations

- structured_assembly_only
- no_new_interpretation
- no_market_outlook_or_trade_action
