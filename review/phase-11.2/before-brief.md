# Daily Market Intelligence Brief

- Report date: 2026-09-14
- Intelligence status: `partial`
- Intelligence run: `run_20260914T131130Z_intelligence_f58d7b660b0de42c`
- Intelligence generated at: 2026-09-14T13:11:30.000414Z
- Input contract: `daily_intelligence_v1`
- Render mode: `deterministic_structured_only`

# Today's Top Market Intelligence

## 1. Observed dollar and yield pressure

- Type: `market_stress`
- Story key: `macro_state:usd_strength`
- Why it matters: Current DXY daily change and US10Y daily basis-point change are both positive. Attention level is medium and the condition is linked to current evidence.
- Monitor next: Monitor the referenced observations for DXY, US10Y on the next validated run.
- Deterministic score: 68
- Theme: `macro_rates`
- Related assets: ["DXY","US10Y"]
- Freshness: `current`
- Validation: `validated`

Evidence references:

- Artifact runs: `run_20260914T131129Z_consolidated_968567af50093d84`, `run_20260914T131129Z_regime_97e0c35f8fe1a268`, `run_20260914T131129Z_relationships_18b455610e647bf1`, `run_20260914T131129Z_risk_3c2e09a2bb9dace8`
- Evidence bundles: `ebd_0da3a54682b4fdfab0c6`, `ebd_dcc60ec48e10fcf5fdd8`
- Sources: `src_yahoo_finance_dxy`, `src_yahoo_finance_us10y`
- Observations: `obs_dxy_daily_change_pct_2026_09_14t04_00_00z`, `obs_us10y_daily_change_bps_2026_09_14t05_00_00z`
- Events: none
- Evidence: `evd_dxy_market_move_2026_09_14t04_00_00z`, `evd_us10y_market_move_2026_09_14t05_00_00z`
- Signals: `sig_dollar_yield_co_movement_v1_f9fa2052cd84`
- Regime dimensions: none
- Risks: `rsk_observed_dollar_yield_pressure_v1_889009346623e0cd`
- Coverage inputs: none
- Source references: `src_yahoo_finance_dxy`, `src_yahoo_finance_us10y`
- Observed at: ["2026-09-14T04:00:00Z","2026-09-14T05:00:00Z"]
- Scheduled at: []
- Detected at: []

## 2. Observed: BTC-USD and ETH-USD daily co-movement

- Type: `cross_asset_signal`
- Story key: `crypto_state:positive_co_movement`
- Why it matters: The validated relationship condition is observed across BTC-USD, ETH-USD; BTC-USD daily_change_pct=1.0494 percent, ETH-USD daily_change_pct=0.7981 percent.
- Monitor next: Monitor the same validated metrics and their observation timestamps on the next run.
- Deterministic score: 61
- Theme: `crypto`
- Related assets: ["BTC-USD","ETH-USD"]
- Freshness: `current`
- Validation: `validated`

Evidence references:

- Artifact runs: `run_20260914T131129Z_consolidated_968567af50093d84`, `run_20260914T131129Z_relationships_18b455610e647bf1`
- Evidence bundles: `ebd_1cc23e6d3269b058b0b7`, `ebd_d77803dbba8ce50f7755`
- Sources: `src_yahoo_finance`
- Observations: `obs_btc_usd_daily_change_pct_2026_09_14t00_00_00z`, `obs_eth_usd_daily_change_pct_2026_09_14t00_00_00z`
- Events: none
- Evidence: `evd_btc_usd_market_move_2026_09_14t00_00_00z`, `evd_eth_usd_market_move_2026_09_14t00_00_00z`
- Signals: `sig_crypto_co_movement_v1_181838fc5090`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none
- Source references: `src_yahoo_finance`
- Observed at: ["2026-09-14T00:00:00Z"]
- Scheduled at: []
- Detected at: []

Top Intelligence warnings:

- fewer_than_three_eligible_items
- semantic_story_duplicates_suppressed

## Data Quality and Coverage

| Artifact | Run / generated at | Validation | Data | Record freshness | Artifact freshness | Age / max hours | Objects | Warnings |
|---|---|---|---|---|---|---:|---:|---:|
| evidence_bundle.json | `run_20260914T131129Z_consolidated_968567af50093d84`<br>2026-09-14T13:11:29.862702Z | validated | partial | stale | current | 3.8e-05 / 24.0 | 62 | 2 |
| market_signals.json | `run_20260914T131129Z_relationships_18b455610e647bf1`<br>2026-09-14T13:11:29.897857Z | validated | partial | stale | current | 2.8e-05 / 24.0 | 8 | 3 |
| market_regime.json | `run_20260914T131129Z_regime_97e0c35f8fe1a268`<br>2026-09-14T13:11:29.919500Z | validated | unavailable | stale | current | 2.2e-05 / 24.0 | 1 | 3 |
| risk_monitor.json | `run_20260914T131129Z_risk_3c2e09a2bb9dace8`<br>2026-09-14T13:11:29.954691Z | validated | partial | stale | current | 1.3e-05 / 24.0 | 5 | 2 |

### Data Quality Warnings

- upstream_partial:evidence_bundle.json
- upstream_partial:market_signals.json
- upstream_unavailable:market_regime.json
- upstream_partial:risk_monitor.json

### Data Windows

- Composed at: 2026-09-14T13:11:30.000414Z
- Report date: 2026-09-14
- input_generated_at: 2026-09-14T13:11:29.862702Z → 2026-09-14T13:11:29.954691Z
- observed_at: 2026-09-11T04:00:00Z → 2026-09-14T05:00:00Z
- scheduled_at: unknown → unknown
- occurred_at: unknown → unknown
- published_at: unknown → unknown
- retrieved_at: 2026-09-14T13:11:26.216983Z → 2026-09-14T13:11:28.325291Z
- detected_at: 2026-09-14T13:11:29.954691Z → 2026-09-14T13:11:29.954691Z

## Current Market Regime

- Classification: `unknown`
- Classification scope: current_observed_conditions
- Artifact status: `unavailable`
- Confidence label: `insufficient`
- Confidence score: 0.0

### Regime Dimensions

- `equity`: eligibility=`unavailable`, observed_state=`unavailable`, signal=`sig_equity_index_co_movement_v1_8f065ab294f5`
- `volatility`: eligibility=`unavailable`, observed_state=`unavailable`, signal=`sig_equity_volatility_inverse_move_v1_dbcab27b37c9`
- `crypto`: eligibility=`eligible`, observed_state=`risk_on`, signal=`sig_crypto_co_movement_v1_181838fc5090`
- `dollar_yield`: eligibility=`eligible`, observed_state=`risk_off`, signal=`sig_dollar_yield_co_movement_v1_f9fa2052cd84`
- `cross_asset_alignment`: eligibility=`unavailable`, observed_state=`unavailable`, signal=`sig_equity_crypto_co_movement_v1_1003a725cbf9`

Regime warnings:

- One or more input artifacts or observations are stale.
- 3 regime dimension(s) are unavailable.
- Current evidence does not meet classification coverage rules.

Limitations:

- The classification describes current observations only.
- It does not establish causality, persistence, or later outcomes.
- The classifier does not provide investment or trading instructions.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_regime_b07490496322cfc9`
- Object type: `market_regime`
- Source artifact: `market_regime.json`
- Source run: `run_20260914T131129Z_regime_97e0c35f8fe1a268`
- Source generated at: 2026-09-14T13:11:29.919500Z
- Validation status: `validated`
- Data status: `unavailable`
- observed_at: ["2026-09-11T04:00:00Z","2026-09-14T00:00:00Z","2026-09-14T04:00:00Z","2026-09-14T05:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260914T131129Z_consolidated_968567af50093d84`, `run_20260914T131129Z_regime_97e0c35f8fe1a268`, `run_20260914T131129Z_relationships_18b455610e647bf1`
- Evidence bundles: `ebd_0da3a54682b4fdfab0c6`, `ebd_1cc23e6d3269b058b0b7`, `ebd_d77803dbba8ce50f7755`, `ebd_dcc60ec48e10fcf5fdd8`, `ebd_efb67523f9fd126c432e`, `ebd_f328e3b73bb2cab1da94`, `ebd_f822b3eb11b1ca165802`
- Sources: `src_yahoo_finance`, `src_yahoo_finance_dxy`, `src_yahoo_finance_us10y`, `src_yahoo_finance_vix`
- Observations: `obs_btc_usd_daily_change_pct_2026_09_14t00_00_00z`, `obs_dxy_daily_change_pct_2026_09_14t04_00_00z`, `obs_eth_usd_daily_change_pct_2026_09_14t00_00_00z`, `obs_qqq_daily_change_pct_2026_09_11t04_00_00z`, `obs_spy_daily_change_pct_2026_09_11t04_00_00z`, `obs_us10y_daily_change_bps_2026_09_14t05_00_00z`, `obs_vix_daily_change_pct_2026_09_14t05_00_00z`
- Events: none
- Evidence: `evd_btc_usd_market_move_2026_09_14t00_00_00z`, `evd_dxy_market_move_2026_09_14t04_00_00z`, `evd_eth_usd_market_move_2026_09_14t00_00_00z`, `evd_qqq_market_move_2026_09_11t04_00_00z`, `evd_spy_market_move_2026_09_11t04_00_00z`, `evd_us10y_market_move_2026_09_14t05_00_00z`, `evd_vix_market_move_2026_09_14t05_00_00z`
- Signals: `sig_crypto_co_movement_v1_181838fc5090`, `sig_dollar_yield_co_movement_v1_f9fa2052cd84`, `sig_equity_crypto_co_movement_v1_1003a725cbf9`, `sig_equity_index_co_movement_v1_8f065ab294f5`, `sig_equity_volatility_inverse_move_v1_dbcab27b37c9`
- Regime dimensions: `cross_asset_alignment`, `crypto`, `dollar_yield`, `equity`, `volatility`
- Risks: none
- Coverage inputs: none

</details>

## Cross-Asset Observations

### BTC-USD and ETH-USD daily co-movement

- Signal ID: `sig_crypto_co_movement_v1_181838fc5090`
- Rule ID: `crypto_co_movement_v1`
- Relationship: `co_movement`
- State: `observed`
- Condition met: `true`
- Data quality: `available`
- Confidence: `high` (0.95)

Data-quality details:

- conflicting_inputs: []
- issues: []
- missing_inputs: []
- stale_observation_ids: []
- status: available

Observed values:

- `BTC-USD` daily_change_pct=1.0494 percent; as_of=2026-09-14T00:00:00Z; observation=`obs_btc_usd_daily_change_pct_2026_09_14t00_00_00z`; source=`src_yahoo_finance`
- `ETH-USD` daily_change_pct=0.7981 percent; as_of=2026-09-14T00:00:00Z; observation=`obs_eth_usd_daily_change_pct_2026_09_14t00_00_00z`; source=`src_yahoo_finance`

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_80d5f7af143cc30d`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260914T131129Z_relationships_18b455610e647bf1`
- Source generated at: 2026-09-14T13:11:29.897857Z
- Validation status: `validated`
- Data status: `observed`
- observed_at: ["2026-09-14T00:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260914T131129Z_consolidated_968567af50093d84`, `run_20260914T131129Z_relationships_18b455610e647bf1`
- Evidence bundles: `ebd_1cc23e6d3269b058b0b7`, `ebd_d77803dbba8ce50f7755`
- Sources: `src_yahoo_finance`
- Observations: `obs_btc_usd_daily_change_pct_2026_09_14t00_00_00z`, `obs_eth_usd_daily_change_pct_2026_09_14t00_00_00z`
- Events: none
- Evidence: `evd_btc_usd_market_move_2026_09_14t00_00_00z`, `evd_eth_usd_market_move_2026_09_14t00_00_00z`
- Signals: `sig_crypto_co_movement_v1_181838fc5090`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### DXY and major FX quote alignment

- Signal ID: `sig_dollar_fx_quote_alignment_v1_f5d10454f425`
- Rule ID: `dollar_fx_quote_alignment_v1`
- Relationship: `quote_alignment`
- State: `observed`
- Condition met: `true`
- Data quality: `available`
- Confidence: `medium` (0.75)

Data-quality details:

- conflicting_inputs: []
- issues: []
- missing_inputs: []
- stale_observation_ids: []
- status: available

Observed values:

- `DXY` daily_change_pct=0.5599 percent; as_of=2026-09-14T04:00:00Z; observation=`obs_dxy_daily_change_pct_2026_09_14t04_00_00z`; source=`src_yahoo_finance_dxy`
- `EURUSD` daily_change_pct=-0.6425 percent; as_of=2026-09-13T23:00:00Z; observation=`obs_eurusd_daily_change_pct_2026_09_13t23_00_00z`; source=`src_yahoo_finance`
- `USDJPY` daily_change_pct=0.2376 percent; as_of=2026-09-13T23:00:00Z; observation=`obs_usdjpy_daily_change_pct_2026_09_13t23_00_00z`; source=`src_yahoo_finance`

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_a754dd62d6fc13bf`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260914T131129Z_relationships_18b455610e647bf1`
- Source generated at: 2026-09-14T13:11:29.897857Z
- Validation status: `validated`
- Data status: `observed`
- observed_at: ["2026-09-13T23:00:00Z","2026-09-14T04:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260914T131129Z_consolidated_968567af50093d84`, `run_20260914T131129Z_relationships_18b455610e647bf1`
- Evidence bundles: `ebd_0da3a54682b4fdfab0c6`, `ebd_9357bda91890bbe117ad`, `ebd_f617a53c8efdc0549279`
- Sources: `src_yahoo_finance`, `src_yahoo_finance_dxy`
- Observations: `obs_dxy_daily_change_pct_2026_09_14t04_00_00z`, `obs_eurusd_daily_change_pct_2026_09_13t23_00_00z`, `obs_usdjpy_daily_change_pct_2026_09_13t23_00_00z`
- Events: none
- Evidence: `evd_dxy_market_move_2026_09_14t04_00_00z`, `evd_eurusd_market_move_2026_09_13t23_00_00z`, `evd_usdjpy_market_move_2026_09_13t23_00_00z`
- Signals: `sig_dollar_fx_quote_alignment_v1_f5d10454f425`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### DXY and US10Y daily co-movement

- Signal ID: `sig_dollar_yield_co_movement_v1_f9fa2052cd84`
- Rule ID: `dollar_yield_co_movement_v1`
- Relationship: `co_movement`
- State: `observed`
- Condition met: `true`
- Data quality: `available`
- Confidence: `medium` (0.75)

Data-quality details:

- conflicting_inputs: []
- issues: []
- missing_inputs: []
- stale_observation_ids: []
- status: available

Observed values:

- `DXY` daily_change_pct=0.5599 percent; as_of=2026-09-14T04:00:00Z; observation=`obs_dxy_daily_change_pct_2026_09_14t04_00_00z`; source=`src_yahoo_finance_dxy`
- `US10Y` daily_change_bps=1.0 basis_points; as_of=2026-09-14T05:00:00Z; observation=`obs_us10y_daily_change_bps_2026_09_14t05_00_00z`; source=`src_yahoo_finance_us10y`

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_7543c74bf6b4d232`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260914T131129Z_relationships_18b455610e647bf1`
- Source generated at: 2026-09-14T13:11:29.897857Z
- Validation status: `validated`
- Data status: `observed`
- observed_at: ["2026-09-14T04:00:00Z","2026-09-14T05:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260914T131129Z_consolidated_968567af50093d84`, `run_20260914T131129Z_relationships_18b455610e647bf1`
- Evidence bundles: `ebd_0da3a54682b4fdfab0c6`, `ebd_dcc60ec48e10fcf5fdd8`
- Sources: `src_yahoo_finance_dxy`, `src_yahoo_finance_us10y`
- Observations: `obs_dxy_daily_change_pct_2026_09_14t04_00_00z`, `obs_us10y_daily_change_bps_2026_09_14t05_00_00z`
- Events: none
- Evidence: `evd_dxy_market_move_2026_09_14t04_00_00z`, `evd_us10y_market_move_2026_09_14t05_00_00z`
- Signals: `sig_dollar_yield_co_movement_v1_f9fa2052cd84`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### Equity indexes and BTC-USD daily co-movement

- Signal ID: `sig_equity_crypto_co_movement_v1_1003a725cbf9`
- Rule ID: `equity_crypto_co_movement_v1`
- Relationship: `co_movement`
- State: `insufficient_data`
- Condition met: `unknown`
- Data quality: `partial`
- Confidence: `insufficient` (0.0)

Data-quality details:

- conflicting_inputs: []
- issues: ["observation_time_gap_exceeded","stale_observation"]
- missing_inputs: []
- stale_observation_ids: ["obs_qqq_daily_change_pct_2026_09_11t04_00_00z","obs_spy_daily_change_pct_2026_09_11t04_00_00z"]
- status: partial

Observed values:

- `BTC-USD` daily_change_pct=1.0494 percent; as_of=2026-09-14T00:00:00Z; observation=`obs_btc_usd_daily_change_pct_2026_09_14t00_00_00z`; source=`src_yahoo_finance`
- `QQQ` daily_change_pct=0.8734 percent; as_of=2026-09-11T04:00:00Z; observation=`obs_qqq_daily_change_pct_2026_09_11t04_00_00z`; source=`src_yahoo_finance`
- `SPY` daily_change_pct=0.8524 percent; as_of=2026-09-11T04:00:00Z; observation=`obs_spy_daily_change_pct_2026_09_11t04_00_00z`; source=`src_yahoo_finance`

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.
- Required observations fall outside the permitted comparison window.
- One or more required observations are stale; the relationship is not current.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_312f0da37dd6d096`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260914T131129Z_relationships_18b455610e647bf1`
- Source generated at: 2026-09-14T13:11:29.897857Z
- Validation status: `validated`
- Data status: `insufficient_data`
- observed_at: ["2026-09-11T04:00:00Z","2026-09-14T00:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260914T131129Z_consolidated_968567af50093d84`, `run_20260914T131129Z_relationships_18b455610e647bf1`
- Evidence bundles: `ebd_1cc23e6d3269b058b0b7`, `ebd_efb67523f9fd126c432e`, `ebd_f822b3eb11b1ca165802`
- Sources: `src_yahoo_finance`
- Observations: `obs_btc_usd_daily_change_pct_2026_09_14t00_00_00z`, `obs_qqq_daily_change_pct_2026_09_11t04_00_00z`, `obs_spy_daily_change_pct_2026_09_11t04_00_00z`
- Events: none
- Evidence: `evd_btc_usd_market_move_2026_09_14t00_00_00z`, `evd_qqq_market_move_2026_09_11t04_00_00z`, `evd_spy_market_move_2026_09_11t04_00_00z`
- Signals: `sig_equity_crypto_co_movement_v1_1003a725cbf9`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### SPY and QQQ daily co-movement

- Signal ID: `sig_equity_index_co_movement_v1_8f065ab294f5`
- Rule ID: `equity_index_co_movement_v1`
- Relationship: `co_movement`
- State: `stale_data`
- Condition met: `true`
- Data quality: `partial`
- Confidence: `low` (0.475)

Data-quality details:

- conflicting_inputs: []
- issues: ["stale_observation"]
- missing_inputs: []
- stale_observation_ids: ["obs_qqq_daily_change_pct_2026_09_11t04_00_00z","obs_spy_daily_change_pct_2026_09_11t04_00_00z"]
- status: partial

Observed values:

- `QQQ` daily_change_pct=0.8734 percent; as_of=2026-09-11T04:00:00Z; observation=`obs_qqq_daily_change_pct_2026_09_11t04_00_00z`; source=`src_yahoo_finance`
- `SPY` daily_change_pct=0.8524 percent; as_of=2026-09-11T04:00:00Z; observation=`obs_spy_daily_change_pct_2026_09_11t04_00_00z`; source=`src_yahoo_finance`

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.
- One or more required observations are stale; the relationship is not current.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_8a0b6bf7501b8811`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260914T131129Z_relationships_18b455610e647bf1`
- Source generated at: 2026-09-14T13:11:29.897857Z
- Validation status: `validated`
- Data status: `stale_data`
- observed_at: ["2026-09-11T04:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260914T131129Z_consolidated_968567af50093d84`, `run_20260914T131129Z_relationships_18b455610e647bf1`
- Evidence bundles: `ebd_efb67523f9fd126c432e`, `ebd_f822b3eb11b1ca165802`
- Sources: `src_yahoo_finance`
- Observations: `obs_qqq_daily_change_pct_2026_09_11t04_00_00z`, `obs_spy_daily_change_pct_2026_09_11t04_00_00z`
- Events: none
- Evidence: `evd_qqq_market_move_2026_09_11t04_00_00z`, `evd_spy_market_move_2026_09_11t04_00_00z`
- Signals: `sig_equity_index_co_movement_v1_8f065ab294f5`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### SPY and QQQ daily divergence

- Signal ID: `sig_equity_index_divergence_v1_aa5aa39a2489`
- Rule ID: `equity_index_divergence_v1`
- Relationship: `divergence`
- State: `stale_data`
- Condition met: `false`
- Data quality: `partial`
- Confidence: `low` (0.475)

Data-quality details:

- conflicting_inputs: []
- issues: ["stale_observation"]
- missing_inputs: []
- stale_observation_ids: ["obs_qqq_daily_change_pct_2026_09_11t04_00_00z","obs_spy_daily_change_pct_2026_09_11t04_00_00z"]
- status: partial

Observed values:

- `QQQ` daily_change_pct=0.8734 percent; as_of=2026-09-11T04:00:00Z; observation=`obs_qqq_daily_change_pct_2026_09_11t04_00_00z`; source=`src_yahoo_finance`
- `SPY` daily_change_pct=0.8524 percent; as_of=2026-09-11T04:00:00Z; observation=`obs_spy_daily_change_pct_2026_09_11t04_00_00z`; source=`src_yahoo_finance`

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.
- One or more required observations are stale; the relationship is not current.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_bac45ebc2f753199`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260914T131129Z_relationships_18b455610e647bf1`
- Source generated at: 2026-09-14T13:11:29.897857Z
- Validation status: `validated`
- Data status: `stale_data`
- observed_at: ["2026-09-11T04:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260914T131129Z_consolidated_968567af50093d84`, `run_20260914T131129Z_relationships_18b455610e647bf1`
- Evidence bundles: `ebd_efb67523f9fd126c432e`, `ebd_f822b3eb11b1ca165802`
- Sources: `src_yahoo_finance`
- Observations: `obs_qqq_daily_change_pct_2026_09_11t04_00_00z`, `obs_spy_daily_change_pct_2026_09_11t04_00_00z`
- Events: none
- Evidence: `evd_qqq_market_move_2026_09_11t04_00_00z`, `evd_spy_market_move_2026_09_11t04_00_00z`
- Signals: `sig_equity_index_divergence_v1_aa5aa39a2489`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### Equity indexes and VIX inverse daily movement

- Signal ID: `sig_equity_volatility_inverse_move_v1_dbcab27b37c9`
- Rule ID: `equity_volatility_inverse_move_v1`
- Relationship: `inverse_movement`
- State: `insufficient_data`
- Condition met: `unknown`
- Data quality: `partial`
- Confidence: `insufficient` (0.0)

Data-quality details:

- conflicting_inputs: []
- issues: ["observation_time_gap_exceeded","stale_observation"]
- missing_inputs: []
- stale_observation_ids: ["obs_qqq_daily_change_pct_2026_09_11t04_00_00z","obs_spy_daily_change_pct_2026_09_11t04_00_00z"]
- status: partial

Observed values:

- `QQQ` daily_change_pct=0.8734 percent; as_of=2026-09-11T04:00:00Z; observation=`obs_qqq_daily_change_pct_2026_09_11t04_00_00z`; source=`src_yahoo_finance`
- `SPY` daily_change_pct=0.8524 percent; as_of=2026-09-11T04:00:00Z; observation=`obs_spy_daily_change_pct_2026_09_11t04_00_00z`; source=`src_yahoo_finance`
- `VIX` daily_change_pct=12.3106 percent; as_of=2026-09-14T05:00:00Z; observation=`obs_vix_daily_change_pct_2026_09_14t05_00_00z`; source=`src_yahoo_finance_vix`

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.
- Required observations fall outside the permitted comparison window.
- One or more required observations are stale; the relationship is not current.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_1161c61e0fa98d1e`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260914T131129Z_relationships_18b455610e647bf1`
- Source generated at: 2026-09-14T13:11:29.897857Z
- Validation status: `validated`
- Data status: `insufficient_data`
- observed_at: ["2026-09-11T04:00:00Z","2026-09-14T05:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260914T131129Z_consolidated_968567af50093d84`, `run_20260914T131129Z_relationships_18b455610e647bf1`
- Evidence bundles: `ebd_efb67523f9fd126c432e`, `ebd_f328e3b73bb2cab1da94`, `ebd_f822b3eb11b1ca165802`
- Sources: `src_yahoo_finance`, `src_yahoo_finance_vix`
- Observations: `obs_qqq_daily_change_pct_2026_09_11t04_00_00z`, `obs_spy_daily_change_pct_2026_09_11t04_00_00z`, `obs_vix_daily_change_pct_2026_09_14t05_00_00z`
- Events: none
- Evidence: `evd_qqq_market_move_2026_09_11t04_00_00z`, `evd_spy_market_move_2026_09_11t04_00_00z`, `evd_vix_market_move_2026_09_14t05_00_00z`
- Signals: `sig_equity_volatility_inverse_move_v1_dbcab27b37c9`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### Gold and DXY inverse daily movement

- Signal ID: `sig_gold_dollar_inverse_move_v1_f004a46a0a2e`
- Rule ID: `gold_dollar_inverse_move_v1`
- Relationship: `inverse_movement`
- State: `observed`
- Condition met: `true`
- Data quality: `available`
- Confidence: `medium` (0.75)

Data-quality details:

- conflicting_inputs: []
- issues: []
- missing_inputs: []
- stale_observation_ids: []
- status: available

Observed values:

- `DXY` daily_change_pct=0.5599 percent; as_of=2026-09-14T04:00:00Z; observation=`obs_dxy_daily_change_pct_2026_09_14t04_00_00z`; source=`src_yahoo_finance_dxy`
- `GOLD` daily_change_pct=-1.3444 percent; as_of=2026-09-14T04:00:00Z; observation=`obs_gold_daily_change_pct_2026_09_14t04_00_00z`; source=`src_yahoo_finance`

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_28fef3d9a09d4f5b`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260914T131129Z_relationships_18b455610e647bf1`
- Source generated at: 2026-09-14T13:11:29.897857Z
- Validation status: `validated`
- Data status: `observed`
- observed_at: ["2026-09-14T04:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260914T131129Z_consolidated_968567af50093d84`, `run_20260914T131129Z_relationships_18b455610e647bf1`
- Evidence bundles: `ebd_0da3a54682b4fdfab0c6`, `ebd_fe6d7c6087cdc3b651f6`
- Sources: `src_yahoo_finance`, `src_yahoo_finance_dxy`
- Observations: `obs_dxy_daily_change_pct_2026_09_14t04_00_00z`, `obs_gold_daily_change_pct_2026_09_14t04_00_00z`
- Events: none
- Evidence: `evd_dxy_market_move_2026_09_14t04_00_00z`, `evd_gold_market_move_2026_09_14t04_00_00z`
- Signals: `sig_gold_dollar_inverse_move_v1_f004a46a0a2e`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

## Upcoming Event Risks

- None in validated input.

## Data Quality Risks

### Degraded input coverage: market_observations

- Risk ID: `rsk_input_coverage_degraded_v1_30e7e416c275be30`
- Rule ID: `input_coverage_degraded_v1`
- Category: `data_quality`
- Status: `detected`
- Attention level: `medium`
- Description: The consolidated Evidence input reports incomplete or stale coverage.
- Related assets: ["AAPL","BTC-USD","ETH-USD","EURUSD","GOLD","NVDA","QQQ","SPY","TSLA","USDJPY"]

Observed facts:

- artifact: observations.json
- coverage_status: partial
- input_type: market_observations
- record_count: 60
- stale_record_count: 30

Time window:

- detected_at: 2026-09-14T13:11:29.954691Z

Limitations:

- This item concerns data reliability, not market prices.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_risk_7ffdd87f186c3367`
- Object type: `data_quality_risk`
- Source artifact: `risk_monitor.json`
- Source run: `run_20260914T131129Z_risk_3c2e09a2bb9dace8`
- Source generated at: 2026-09-14T13:11:29.954691Z
- Validation status: `validated`
- Data status: `detected`
- observed_at: []
- scheduled_at: []
- detected_at: ["2026-09-14T13:11:29.954691Z"]

Evidence references:

- Artifact runs: `run_20260914T131129Z_consolidated_968567af50093d84`, `run_20260914T131129Z_regime_97e0c35f8fe1a268`, `run_20260914T131129Z_relationships_18b455610e647bf1`, `run_20260914T131129Z_risk_3c2e09a2bb9dace8`
- Evidence bundles: `ebd_05fbe96cc95d50e712d2`, `ebd_060aad8fbed41a3c769e`, `ebd_0c01ddc3d39769a81283`, `ebd_1bec0862cba8e1eeac86`, `ebd_1cc23e6d3269b058b0b7`, `ebd_1e535fb8dc8de7e357c0`, `ebd_1ed97c716d7c2f5fd8f7`, `ebd_2934921030eb4392aba5`, `ebd_2d0dadfb7bc092f888e0`, `ebd_323c05283f893fba1b38`, `ebd_384172f95c98552e75aa`, `ebd_51886f0408e0d792f9be`, `ebd_56f42187f2e69996f7d5`, `ebd_5ad3b1236f7874793b17`, `ebd_5d6c2e11d870b0dd84f5`, `ebd_6c36baced900a795bc01`, `ebd_6f85737b3a717445587c`, `ebd_7187b7fbcc84bd4df6d8`, `ebd_726c8d5d4e26f4de74c8`, `ebd_74f2018bebc389407a5e`, `ebd_76717533cb376a8d03df`, `ebd_7e829045f008c854518f`, `ebd_88843ca6b16eafd626a0`, `ebd_8ca954739b8c58709dd2`, `ebd_912747bd31585c389adf`, `ebd_9357bda91890bbe117ad`, `ebd_a03d1dc2f0eb18be2f7a`, `ebd_a4184900012d9b7e7633`, `ebd_a6e09c2d0cddb4fb079f`, `ebd_abcbe7b59378d2385e07`, `ebd_ac7857498741cc57e021`, `ebd_ade49e2793be9805e7d2`, `ebd_ae8e19e796ebfb967bd1`, `ebd_b1fdd53f735559be95a7`, `ebd_b52faef0c2b71a80b5c2`, `ebd_bd6e088c247f10b121ae`, `ebd_c150db01240ebe53265f`, `ebd_c7f2e4bc9be2aaf71a88`, `ebd_cef176a8f579e0120776`, `ebd_d4b90e5aaff569368799`, `ebd_d77803dbba8ce50f7755`, `ebd_d7832597e4e961a569c3`, `ebd_e2f4b6ca684b742d58f4`, `ebd_efb67523f9fd126c432e`, `ebd_f617a53c8efdc0549279`, `ebd_f7def5e00a00df6a6516`, `ebd_f822b3eb11b1ca165802`, `ebd_fd6bfdb673c16f61bb28`, `ebd_fd7c327e025cc80daa6d`, `ebd_fe6d7c6087cdc3b651f6`
- Sources: `src_yahoo_finance`
- Observations: `obs_aapl_daily_change_pct_2026_09_11t04_00_00z`, `obs_aapl_price_2026_09_11t04_00_00z`, `obs_aapl_sma20_2026_09_11t04_00_00z`, `obs_aapl_trend_2026_09_11t04_00_00z`, `obs_aapl_volatility_20d_2026_09_11t04_00_00z`, `obs_aapl_weekly_change_pct_2026_09_11t04_00_00z`, `obs_btc_usd_daily_change_pct_2026_09_14t00_00_00z`, `obs_btc_usd_price_2026_09_14t00_00_00z`, `obs_btc_usd_sma20_2026_09_14t00_00_00z`, `obs_btc_usd_trend_2026_09_14t00_00_00z`, `obs_btc_usd_volatility_20d_2026_09_14t00_00_00z`, `obs_btc_usd_weekly_change_pct_2026_09_14t00_00_00z`, `obs_eth_usd_daily_change_pct_2026_09_14t00_00_00z`, `obs_eth_usd_price_2026_09_14t00_00_00z`, `obs_eth_usd_sma20_2026_09_14t00_00_00z`, `obs_eth_usd_trend_2026_09_14t00_00_00z`, `obs_eth_usd_volatility_20d_2026_09_14t00_00_00z`, `obs_eth_usd_weekly_change_pct_2026_09_14t00_00_00z`, `obs_eurusd_daily_change_pct_2026_09_13t23_00_00z`, `obs_eurusd_price_2026_09_13t23_00_00z`, `obs_eurusd_sma20_2026_09_13t23_00_00z`, `obs_eurusd_trend_2026_09_13t23_00_00z`, `obs_eurusd_volatility_20d_2026_09_13t23_00_00z`, `obs_eurusd_weekly_change_pct_2026_09_13t23_00_00z`, `obs_gold_daily_change_pct_2026_09_14t04_00_00z`, `obs_gold_price_2026_09_14t04_00_00z`, `obs_gold_sma20_2026_09_14t04_00_00z`, `obs_gold_trend_2026_09_14t04_00_00z`, `obs_gold_volatility_20d_2026_09_14t04_00_00z`, `obs_gold_weekly_change_pct_2026_09_14t04_00_00z`, `obs_nvda_daily_change_pct_2026_09_11t04_00_00z`, `obs_nvda_price_2026_09_11t04_00_00z`, `obs_nvda_sma20_2026_09_11t04_00_00z`, `obs_nvda_trend_2026_09_11t04_00_00z`, `obs_nvda_volatility_20d_2026_09_11t04_00_00z`, `obs_nvda_weekly_change_pct_2026_09_11t04_00_00z`, `obs_qqq_daily_change_pct_2026_09_11t04_00_00z`, `obs_qqq_price_2026_09_11t04_00_00z`, `obs_qqq_sma20_2026_09_11t04_00_00z`, `obs_qqq_trend_2026_09_11t04_00_00z`, `obs_qqq_volatility_20d_2026_09_11t04_00_00z`, `obs_qqq_weekly_change_pct_2026_09_11t04_00_00z`, `obs_spy_daily_change_pct_2026_09_11t04_00_00z`, `obs_spy_price_2026_09_11t04_00_00z`, `obs_spy_sma20_2026_09_11t04_00_00z`, `obs_spy_trend_2026_09_11t04_00_00z`, `obs_spy_volatility_20d_2026_09_11t04_00_00z`, `obs_spy_weekly_change_pct_2026_09_11t04_00_00z`, `obs_tsla_daily_change_pct_2026_09_11t04_00_00z`, `obs_tsla_price_2026_09_11t04_00_00z`, `obs_tsla_sma20_2026_09_11t04_00_00z`, `obs_tsla_trend_2026_09_11t04_00_00z`, `obs_tsla_volatility_20d_2026_09_11t04_00_00z`, `obs_tsla_weekly_change_pct_2026_09_11t04_00_00z`, `obs_usdjpy_daily_change_pct_2026_09_13t23_00_00z`, `obs_usdjpy_price_2026_09_13t23_00_00z`, `obs_usdjpy_sma20_2026_09_13t23_00_00z`, `obs_usdjpy_trend_2026_09_13t23_00_00z`, `obs_usdjpy_volatility_20d_2026_09_13t23_00_00z`, `obs_usdjpy_weekly_change_pct_2026_09_13t23_00_00z`
- Events: none
- Evidence: `evd_aapl_market_move_2026_09_11t04_00_00z`, `evd_btc_usd_market_move_2026_09_14t00_00_00z`, `evd_eth_usd_market_move_2026_09_14t00_00_00z`, `evd_eurusd_market_move_2026_09_13t23_00_00z`, `evd_gold_market_move_2026_09_14t04_00_00z`, `evd_nvda_market_move_2026_09_11t04_00_00z`, `evd_qqq_market_move_2026_09_11t04_00_00z`, `evd_spy_market_move_2026_09_11t04_00_00z`, `evd_tsla_market_move_2026_09_11t04_00_00z`, `evd_usdjpy_market_move_2026_09_13t23_00_00z`
- Signals: none
- Regime dimensions: none
- Risks: `rsk_input_coverage_degraded_v1_30e7e416c275be30`
- Coverage inputs: `market_observations`

</details>

### Degraded input coverage: economic_calendar

- Risk ID: `rsk_input_coverage_degraded_v1_d8e840d99eca9d0e`
- Rule ID: `input_coverage_degraded_v1`
- Category: `data_quality`
- Status: `detected`
- Attention level: `medium`
- Description: The consolidated Evidence input reports incomplete or stale coverage.
- Related assets: []

Observed facts:

- artifact: economic_calendar.json
- coverage_status: partial
- input_type: economic_calendar
- record_count: 0
- stale_record_count: 0

Time window:

- detected_at: 2026-09-14T13:11:29.954691Z

Limitations:

- This item concerns data reliability, not market prices.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_risk_f9340c309604c397`
- Object type: `data_quality_risk`
- Source artifact: `risk_monitor.json`
- Source run: `run_20260914T131129Z_risk_3c2e09a2bb9dace8`
- Source generated at: 2026-09-14T13:11:29.954691Z
- Validation status: `validated`
- Data status: `detected`
- observed_at: []
- scheduled_at: []
- detected_at: ["2026-09-14T13:11:29.954691Z"]

Evidence references:

- Artifact runs: `run_20260914T131129Z_consolidated_968567af50093d84`, `run_20260914T131129Z_regime_97e0c35f8fe1a268`, `run_20260914T131129Z_relationships_18b455610e647bf1`, `run_20260914T131129Z_risk_3c2e09a2bb9dace8`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: none
- Regime dimensions: none
- Risks: `rsk_input_coverage_degraded_v1_d8e840d99eca9d0e`
- Coverage inputs: `economic_calendar`

</details>

### Current market regime coverage degraded

- Risk ID: `rsk_market_regime_coverage_degraded_v1_29e2609d7639e016`
- Rule ID: `market_regime_coverage_degraded_v1`
- Category: `data_quality`
- Status: `detected`
- Attention level: `high`
- Description: The current-condition classifier reports partial or insufficient eligible coverage.
- Related assets: ["BTC-USD","DXY","ETH-USD","EURUSD","GOLD","QQQ","SPY","USDJPY"]

Observed facts:

- artifact_status: unavailable
- classification: unknown
- eligible_dimension_count: 2
- eligible_weight: 0.35

Time window:

- detected_at: 2026-09-14T13:11:29.954691Z

Limitations:

- No unavailable regime is treated as mixed.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_risk_bc40e5e699a068a5`
- Object type: `data_quality_risk`
- Source artifact: `risk_monitor.json`
- Source run: `run_20260914T131129Z_risk_3c2e09a2bb9dace8`
- Source generated at: 2026-09-14T13:11:29.954691Z
- Validation status: `validated`
- Data status: `detected`
- observed_at: []
- scheduled_at: []
- detected_at: ["2026-09-14T13:11:29.954691Z"]

Evidence references:

- Artifact runs: `run_20260914T131129Z_consolidated_968567af50093d84`, `run_20260914T131129Z_regime_97e0c35f8fe1a268`, `run_20260914T131129Z_relationships_18b455610e647bf1`, `run_20260914T131129Z_risk_3c2e09a2bb9dace8`
- Evidence bundles: `ebd_0da3a54682b4fdfab0c6`, `ebd_1cc23e6d3269b058b0b7`, `ebd_d77803dbba8ce50f7755`, `ebd_dcc60ec48e10fcf5fdd8`, `ebd_efb67523f9fd126c432e`, `ebd_f328e3b73bb2cab1da94`, `ebd_f822b3eb11b1ca165802`
- Sources: `src_yahoo_finance`, `src_yahoo_finance_dxy`, `src_yahoo_finance_us10y`, `src_yahoo_finance_vix`
- Observations: `obs_btc_usd_daily_change_pct_2026_09_14t00_00_00z`, `obs_dxy_daily_change_pct_2026_09_14t04_00_00z`, `obs_eth_usd_daily_change_pct_2026_09_14t00_00_00z`, `obs_qqq_daily_change_pct_2026_09_11t04_00_00z`, `obs_spy_daily_change_pct_2026_09_11t04_00_00z`, `obs_us10y_daily_change_bps_2026_09_14t05_00_00z`, `obs_vix_daily_change_pct_2026_09_14t05_00_00z`
- Events: none
- Evidence: `evd_btc_usd_market_move_2026_09_14t00_00_00z`, `evd_dxy_market_move_2026_09_14t04_00_00z`, `evd_eth_usd_market_move_2026_09_14t00_00_00z`, `evd_qqq_market_move_2026_09_11t04_00_00z`, `evd_spy_market_move_2026_09_11t04_00_00z`, `evd_us10y_market_move_2026_09_14t05_00_00z`, `evd_vix_market_move_2026_09_14t05_00_00z`
- Signals: `sig_crypto_co_movement_v1_181838fc5090`, `sig_dollar_yield_co_movement_v1_f9fa2052cd84`, `sig_equity_crypto_co_movement_v1_1003a725cbf9`, `sig_equity_index_co_movement_v1_8f065ab294f5`, `sig_equity_volatility_inverse_move_v1_dbcab27b37c9`
- Regime dimensions: `cross_asset_alignment`, `crypto`, `dollar_yield`, `equity`, `volatility`
- Risks: `rsk_market_regime_coverage_degraded_v1_29e2609d7639e016`
- Coverage inputs: none

</details>

### Cross-asset relationship coverage degraded

- Risk ID: `rsk_market_signal_coverage_degraded_v1_39e00eadb5d390a2`
- Rule ID: `market_signal_coverage_degraded_v1`
- Category: `data_quality`
- Status: `detected`
- Attention level: `medium`
- Description: One or more cross-asset relationship evaluations are stale or incomplete.
- Related assets: ["BTC-USD","QQQ","SPY"]

Observed facts:

- artifact_status: partial
- state_counts: {"insufficient_data":2,"not_observed":0,"observed":4,"stale_data":2}

Time window:

- detected_at: 2026-09-14T13:11:29.954691Z

Limitations:

- This item concerns analytical coverage only.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_risk_a5d5d785a3e634ae`
- Object type: `data_quality_risk`
- Source artifact: `risk_monitor.json`
- Source run: `run_20260914T131129Z_risk_3c2e09a2bb9dace8`
- Source generated at: 2026-09-14T13:11:29.954691Z
- Validation status: `validated`
- Data status: `detected`
- observed_at: []
- scheduled_at: []
- detected_at: ["2026-09-14T13:11:29.954691Z"]

Evidence references:

- Artifact runs: `run_20260914T131129Z_consolidated_968567af50093d84`, `run_20260914T131129Z_regime_97e0c35f8fe1a268`, `run_20260914T131129Z_relationships_18b455610e647bf1`, `run_20260914T131129Z_risk_3c2e09a2bb9dace8`
- Evidence bundles: `ebd_1cc23e6d3269b058b0b7`, `ebd_efb67523f9fd126c432e`, `ebd_f328e3b73bb2cab1da94`, `ebd_f822b3eb11b1ca165802`
- Sources: `src_yahoo_finance`, `src_yahoo_finance_vix`
- Observations: `obs_btc_usd_daily_change_pct_2026_09_14t00_00_00z`, `obs_qqq_daily_change_pct_2026_09_11t04_00_00z`, `obs_spy_daily_change_pct_2026_09_11t04_00_00z`, `obs_vix_daily_change_pct_2026_09_14t05_00_00z`
- Events: none
- Evidence: `evd_btc_usd_market_move_2026_09_14t00_00_00z`, `evd_qqq_market_move_2026_09_11t04_00_00z`, `evd_spy_market_move_2026_09_11t04_00_00z`, `evd_vix_market_move_2026_09_14t05_00_00z`
- Signals: `sig_equity_crypto_co_movement_v1_1003a725cbf9`, `sig_equity_index_co_movement_v1_8f065ab294f5`, `sig_equity_index_divergence_v1_aa5aa39a2489`, `sig_equity_volatility_inverse_move_v1_dbcab27b37c9`
- Regime dimensions: none
- Risks: `rsk_market_signal_coverage_degraded_v1_39e00eadb5d390a2`
- Coverage inputs: none

</details>

## Observed Market Stress

### Observed dollar and yield pressure

- Risk ID: `rsk_observed_dollar_yield_pressure_v1_889009346623e0cd`
- Rule ID: `observed_dollar_yield_pressure_v1`
- Category: `market_stress`
- Status: `observed`
- Attention level: `medium`
- Description: Current DXY daily change and US10Y daily basis-point change are both positive.
- Related assets: ["DXY","US10Y"]

Observed facts:

- condition_met: true
- observations: [{"as_of":"2026-09-14T04:00:00Z","asset":"DXY","evidence_bundle_ids":["ebd_0da3a54682b4fdfab0c6"],"metric":"daily_change_pct","observation_id":"obs_dxy_daily_change_pct_2026_09_14t04_00_00z","source_id":"src_yahoo_finance_dxy","unit":"percent","value":0.5599},{"as_of":"2026-09-14T05:00:00Z","asset":"US10Y","evidence_bundle_ids":["ebd_dcc60ec48e10fcf5fdd8"],"metric":"daily_change_bps","observation_id":"obs_us10y_daily_change_bps_2026_09_14t05_00_00z","source_id":"src_yahoo_finance_us10y","unit":"basis_points","value":1.0}]
- signal_id: sig_dollar_yield_co_movement_v1_f9fa2052cd84
- signal_rule_id: dollar_yield_co_movement_v1

Time window:

- observed_at: ["2026-09-14T04:00:00Z","2026-09-14T05:00:00Z"]

Limitations:

- The observed condition does not imply persistence or causality.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_risk_f57a2041b380aadc`
- Object type: `market_stress_risk`
- Source artifact: `risk_monitor.json`
- Source run: `run_20260914T131129Z_risk_3c2e09a2bb9dace8`
- Source generated at: 2026-09-14T13:11:29.954691Z
- Validation status: `validated`
- Data status: `observed`
- observed_at: ["2026-09-14T04:00:00Z","2026-09-14T05:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260914T131129Z_consolidated_968567af50093d84`, `run_20260914T131129Z_regime_97e0c35f8fe1a268`, `run_20260914T131129Z_relationships_18b455610e647bf1`, `run_20260914T131129Z_risk_3c2e09a2bb9dace8`
- Evidence bundles: `ebd_0da3a54682b4fdfab0c6`, `ebd_dcc60ec48e10fcf5fdd8`
- Sources: `src_yahoo_finance_dxy`, `src_yahoo_finance_us10y`
- Observations: `obs_dxy_daily_change_pct_2026_09_14t04_00_00z`, `obs_us10y_daily_change_bps_2026_09_14t05_00_00z`
- Events: none
- Evidence: `evd_dxy_market_move_2026_09_14t04_00_00z`, `evd_us10y_market_move_2026_09_14t05_00_00z`
- Signals: `sig_dollar_yield_co_movement_v1_f9fa2052cd84`
- Regime dimensions: none
- Risks: `rsk_observed_dollar_yield_pressure_v1_889009346623e0cd`
- Coverage inputs: none

</details>

## Sources and Provenance

### Input Runs

- evidence_bundle_run_id: `run_20260914T131129Z_consolidated_968567af50093d84`
- market_signals_run_id: `run_20260914T131129Z_relationships_18b455610e647bf1`
- market_regime_run_id: `run_20260914T131129Z_regime_97e0c35f8fe1a268`
- risk_monitor_run_id: `run_20260914T131129Z_risk_3c2e09a2bb9dace8`

### Source Registry

- `src_yahoo_finance` — Yahoo Finance: Yahoo Finance market snapshot
  - URL: https://finance.yahoo.com/
  - Published at: unknown
  - Retrieved at: 2026-09-14T13:11:26.216983Z
  - Quality tier: 3
- `src_yahoo_finance_dxy` — Yahoo Finance: U.S. Dollar Index macro proxy
  - URL: https://finance.yahoo.com/quote/DX-Y.NYB/
  - Published at: unknown
  - Retrieved at: 2026-09-14T13:11:28.325291Z
  - Quality tier: 3
- `src_yahoo_finance_us10y` — Yahoo Finance: U.S. 10-Year Treasury Yield macro proxy
  - URL: https://finance.yahoo.com/quote/%5ETNX/
  - Published at: unknown
  - Retrieved at: 2026-09-14T13:11:28.325291Z
  - Quality tier: 3
- `src_yahoo_finance_vix` — Yahoo Finance: Cboe Volatility Index macro proxy
  - URL: https://finance.yahoo.com/quote/%5EVIX/
  - Published at: unknown
  - Retrieved at: 2026-09-14T13:11:28.325291Z
  - Quality tier: 3

### Provenance Catalog IDs

- Evidence bundles: `ebd_05fbe96cc95d50e712d2`, `ebd_060aad8fbed41a3c769e`, `ebd_0c01ddc3d39769a81283`, `ebd_0da3a54682b4fdfab0c6`, `ebd_1bec0862cba8e1eeac86`, `ebd_1cc23e6d3269b058b0b7`, `ebd_1e535fb8dc8de7e357c0`, `ebd_1ed97c716d7c2f5fd8f7`, `ebd_2934921030eb4392aba5`, `ebd_2d0dadfb7bc092f888e0`, `ebd_323c05283f893fba1b38`, `ebd_384172f95c98552e75aa`, `ebd_51886f0408e0d792f9be`, `ebd_56f42187f2e69996f7d5`, `ebd_5ad3b1236f7874793b17`, `ebd_5d6c2e11d870b0dd84f5`, `ebd_6c36baced900a795bc01`, `ebd_6f85737b3a717445587c`, `ebd_7187b7fbcc84bd4df6d8`, `ebd_726c8d5d4e26f4de74c8`, `ebd_74f2018bebc389407a5e`, `ebd_76717533cb376a8d03df`, `ebd_7e829045f008c854518f`, `ebd_88843ca6b16eafd626a0`, `ebd_8ca954739b8c58709dd2`, `ebd_912747bd31585c389adf`, `ebd_9357bda91890bbe117ad`, `ebd_a03d1dc2f0eb18be2f7a`, `ebd_a4184900012d9b7e7633`, `ebd_a6e09c2d0cddb4fb079f`, `ebd_abcbe7b59378d2385e07`, `ebd_ac7857498741cc57e021`, `ebd_ade49e2793be9805e7d2`, `ebd_ae8e19e796ebfb967bd1`, `ebd_b1fdd53f735559be95a7`, `ebd_b52faef0c2b71a80b5c2`, `ebd_bd6e088c247f10b121ae`, `ebd_c150db01240ebe53265f`, `ebd_c7f2e4bc9be2aaf71a88`, `ebd_cef176a8f579e0120776`, `ebd_d4b90e5aaff569368799`, `ebd_d77803dbba8ce50f7755`, `ebd_d7832597e4e961a569c3`, `ebd_dcc60ec48e10fcf5fdd8`, `ebd_e2f4b6ca684b742d58f4`, `ebd_efb67523f9fd126c432e`, `ebd_f328e3b73bb2cab1da94`, `ebd_f617a53c8efdc0549279`, `ebd_f7def5e00a00df6a6516`, `ebd_f822b3eb11b1ca165802`, `ebd_fd6bfdb673c16f61bb28`, `ebd_fd7c327e025cc80daa6d`, `ebd_fe6d7c6087cdc3b651f6`
- Sources: `src_yahoo_finance`, `src_yahoo_finance_dxy`, `src_yahoo_finance_us10y`, `src_yahoo_finance_vix`
- Observations: `obs_aapl_daily_change_pct_2026_09_11t04_00_00z`, `obs_aapl_price_2026_09_11t04_00_00z`, `obs_aapl_sma20_2026_09_11t04_00_00z`, `obs_aapl_trend_2026_09_11t04_00_00z`, `obs_aapl_volatility_20d_2026_09_11t04_00_00z`, `obs_aapl_weekly_change_pct_2026_09_11t04_00_00z`, `obs_btc_usd_daily_change_pct_2026_09_14t00_00_00z`, `obs_btc_usd_price_2026_09_14t00_00_00z`, `obs_btc_usd_sma20_2026_09_14t00_00_00z`, `obs_btc_usd_trend_2026_09_14t00_00_00z`, `obs_btc_usd_volatility_20d_2026_09_14t00_00_00z`, `obs_btc_usd_weekly_change_pct_2026_09_14t00_00_00z`, `obs_dxy_daily_change_pct_2026_09_14t04_00_00z`, `obs_eth_usd_daily_change_pct_2026_09_14t00_00_00z`, `obs_eth_usd_price_2026_09_14t00_00_00z`, `obs_eth_usd_sma20_2026_09_14t00_00_00z`, `obs_eth_usd_trend_2026_09_14t00_00_00z`, `obs_eth_usd_volatility_20d_2026_09_14t00_00_00z`, `obs_eth_usd_weekly_change_pct_2026_09_14t00_00_00z`, `obs_eurusd_daily_change_pct_2026_09_13t23_00_00z`, `obs_eurusd_price_2026_09_13t23_00_00z`, `obs_eurusd_sma20_2026_09_13t23_00_00z`, `obs_eurusd_trend_2026_09_13t23_00_00z`, `obs_eurusd_volatility_20d_2026_09_13t23_00_00z`, `obs_eurusd_weekly_change_pct_2026_09_13t23_00_00z`, `obs_gold_daily_change_pct_2026_09_14t04_00_00z`, `obs_gold_price_2026_09_14t04_00_00z`, `obs_gold_sma20_2026_09_14t04_00_00z`, `obs_gold_trend_2026_09_14t04_00_00z`, `obs_gold_volatility_20d_2026_09_14t04_00_00z`, `obs_gold_weekly_change_pct_2026_09_14t04_00_00z`, `obs_nvda_daily_change_pct_2026_09_11t04_00_00z`, `obs_nvda_price_2026_09_11t04_00_00z`, `obs_nvda_sma20_2026_09_11t04_00_00z`, `obs_nvda_trend_2026_09_11t04_00_00z`, `obs_nvda_volatility_20d_2026_09_11t04_00_00z`, `obs_nvda_weekly_change_pct_2026_09_11t04_00_00z`, `obs_qqq_daily_change_pct_2026_09_11t04_00_00z`, `obs_qqq_price_2026_09_11t04_00_00z`, `obs_qqq_sma20_2026_09_11t04_00_00z`, `obs_qqq_trend_2026_09_11t04_00_00z`, `obs_qqq_volatility_20d_2026_09_11t04_00_00z`, `obs_qqq_weekly_change_pct_2026_09_11t04_00_00z`, `obs_spy_daily_change_pct_2026_09_11t04_00_00z`, `obs_spy_price_2026_09_11t04_00_00z`, `obs_spy_sma20_2026_09_11t04_00_00z`, `obs_spy_trend_2026_09_11t04_00_00z`, `obs_spy_volatility_20d_2026_09_11t04_00_00z`, `obs_spy_weekly_change_pct_2026_09_11t04_00_00z`, `obs_tsla_daily_change_pct_2026_09_11t04_00_00z`, `obs_tsla_price_2026_09_11t04_00_00z`, `obs_tsla_sma20_2026_09_11t04_00_00z`, `obs_tsla_trend_2026_09_11t04_00_00z`, `obs_tsla_volatility_20d_2026_09_11t04_00_00z`, `obs_tsla_weekly_change_pct_2026_09_11t04_00_00z`, `obs_us10y_daily_change_bps_2026_09_14t05_00_00z`, `obs_usdjpy_daily_change_pct_2026_09_13t23_00_00z`, `obs_usdjpy_price_2026_09_13t23_00_00z`, `obs_usdjpy_sma20_2026_09_13t23_00_00z`, `obs_usdjpy_trend_2026_09_13t23_00_00z`, `obs_usdjpy_volatility_20d_2026_09_13t23_00_00z`, `obs_usdjpy_weekly_change_pct_2026_09_13t23_00_00z`, `obs_vix_daily_change_pct_2026_09_14t05_00_00z`
- Events: none
- Evidence records: `evd_aapl_market_move_2026_09_11t04_00_00z`, `evd_btc_usd_market_move_2026_09_14t00_00_00z`, `evd_dxy_market_move_2026_09_14t04_00_00z`, `evd_eth_usd_market_move_2026_09_14t00_00_00z`, `evd_eurusd_market_move_2026_09_13t23_00_00z`, `evd_gold_market_move_2026_09_14t04_00_00z`, `evd_nvda_market_move_2026_09_11t04_00_00z`, `evd_qqq_market_move_2026_09_11t04_00_00z`, `evd_spy_market_move_2026_09_11t04_00_00z`, `evd_tsla_market_move_2026_09_11t04_00_00z`, `evd_us10y_market_move_2026_09_14t05_00_00z`, `evd_usdjpy_market_move_2026_09_13t23_00_00z`, `evd_vix_market_move_2026_09_14t05_00_00z`

## Scope Limitations

- structured_assembly_only
- no_new_interpretation
- no_market_outlook_or_trade_action
