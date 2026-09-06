# Daily Market Intelligence Brief

- Report date: 2026-09-03
- Intelligence status: `partial`
- Intelligence run: `run_20260903T094942Z_intelligence_8638df744a4ecf19`
- Intelligence generated at: 2026-09-03T09:49:42.065323Z
- Input contract: `daily_intelligence_v1`
- Render mode: `deterministic_structured_only`

# Today's Top Market Intelligence

## 1. Current market regime: risk_on

- Type: `market_regime`
- Story key: `market_state:risk_on`
- Why it matters: The deterministic classifier used 5 eligible current dimensions; confidence is high.
- Monitor next: Monitor the existing regime dimensions and their current evidence coverage.
- Deterministic score: 81
- Theme: `market_regime`
- Related assets: ["BTC-USD","DXY","ETH-USD","QQQ","SPY","US10Y","VIX"]
- Freshness: `current`
- Validation: `validated`

Evidence references:

- Artifact runs: `run_20260903T094941Z_consolidated_b6515be033a2b0c9`, `run_20260903T094941Z_relationships_ec87c2fc99bc03db`, `run_20260903T094942Z_regime_104101e92401b5e8`
- Evidence bundles: `ebd_4cb1e81b79936ae9b10b`, `ebd_6416c8e31707f297c728`, `ebd_6dbbb75ebc1538cda8b4`, `ebd_7159cab27e384dda620c`, `ebd_a8e7955e1620946e1294`, `ebd_cb82f4dc2e067c02f2b1`, `ebd_f88af88c3ffe6dbbd6a6`
- Sources: `src_yahoo_finance`, `src_yahoo_finance_dxy`, `src_yahoo_finance_us10y`, `src_yahoo_finance_vix`
- Observations: `obs_btc_usd_daily_change_pct_2026_09_03t00_00_00z`, `obs_dxy_daily_change_pct_2026_09_03t04_00_00z`, `obs_eth_usd_daily_change_pct_2026_09_03t00_00_00z`, `obs_qqq_daily_change_pct_2026_09_02t04_00_00z`, `obs_spy_daily_change_pct_2026_09_02t04_00_00z`, `obs_us10y_daily_change_bps_2026_09_02t05_00_00z`, `obs_vix_daily_change_pct_2026_09_03t05_00_00z`
- Events: none
- Evidence: `evd_btc_usd_market_move_2026_09_03t00_00_00z`, `evd_dxy_market_move_2026_09_03t04_00_00z`, `evd_eth_usd_market_move_2026_09_03t00_00_00z`, `evd_qqq_market_move_2026_09_02t04_00_00z`, `evd_spy_market_move_2026_09_02t04_00_00z`, `evd_us10y_market_move_2026_09_02t05_00_00z`, `evd_vix_market_move_2026_09_03t05_00_00z`
- Signals: `sig_crypto_co_movement_v1_aecafb33f76e`, `sig_dollar_yield_co_movement_v1_680ed3bbbf67`, `sig_equity_crypto_co_movement_v1_2f9b6e9b0752`, `sig_equity_index_co_movement_v1_8549080eb48d`, `sig_equity_volatility_inverse_move_v1_61ace3e32c42`
- Regime dimensions: `cross_asset_alignment`, `crypto`, `dollar_yield`, `equity`, `volatility`
- Risks: none
- Coverage inputs: none
- Source references: `src_yahoo_finance`, `src_yahoo_finance_dxy`, `src_yahoo_finance_us10y`, `src_yahoo_finance_vix`
- Observed at: ["2026-09-02T04:00:00Z","2026-09-02T05:00:00Z","2026-09-03T00:00:00Z","2026-09-03T04:00:00Z","2026-09-03T05:00:00Z"]
- Scheduled at: []
- Detected at: []

## 2. Upcoming official event: U.S. International Trade in Goods and Services, July 2026

- Type: `upcoming_event`
- Story key: `event:evt_20260903_u_s_international_trade_in_goods_and_5ed967ecb2`
- Why it matters: The validated official calendar record is scheduled for 2026-09-03T12:30:00Z; impact is low.
- Monitor next: Monitor the official event record at 2026-09-03T12:30:00Z and any validated lifecycle update.
- Deterministic score: 80
- Theme: `upcoming_events`
- Related assets: ["DXY","QQQ","SPY","US10Y"]
- Freshness: `current`
- Validation: `validated`

Evidence references:

- Artifact runs: `run_20260903T094941Z_consolidated_b6515be033a2b0c9`, `run_20260903T094941Z_relationships_ec87c2fc99bc03db`, `run_20260903T094942Z_regime_104101e92401b5e8`, `run_20260903T094942Z_risk_7db934988052ef5e`
- Evidence bundles: `ebd_70eb06a1cf9a20519c76`
- Sources: `src_calendar_4a850d66272d3d7b`
- Observations: none
- Events: `evt_20260903_u_s_international_trade_in_goods_and_5ed967ecb2`
- Evidence: none
- Signals: none
- Regime dimensions: none
- Risks: `rsk_upcoming_official_event_v1_33fae68465aa5c86`
- Coverage inputs: none
- Source references: `src_calendar_4a850d66272d3d7b`
- Observed at: []
- Scheduled at: ["2026-09-03T12:30:00Z"]
- Detected at: []

## 3. Observed: DXY and major FX quote alignment

- Type: `cross_asset_signal`
- Story key: `macro_state:usd_weakness`
- Why it matters: The validated relationship condition is observed across DXY, EURUSD, USDJPY; DXY daily_change_pct=-0.3224 percent, EURUSD daily_change_pct=0.1161 percent, USDJPY daily_change_pct=-2.4869 percent.
- Monitor next: Monitor the same validated metrics and their observation timestamps on the next run.
- Deterministic score: 68
- Theme: `macro_rates`
- Related assets: ["DXY","EURUSD","USDJPY"]
- Freshness: `current`
- Validation: `validated`

Evidence references:

- Artifact runs: `run_20260903T094941Z_consolidated_b6515be033a2b0c9`, `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- Evidence bundles: `ebd_4546fec4d63b69066be0`, `ebd_c307bdcf93780136ea41`, `ebd_cb82f4dc2e067c02f2b1`
- Sources: `src_yahoo_finance`, `src_yahoo_finance_dxy`
- Observations: `obs_dxy_daily_change_pct_2026_09_03t04_00_00z`, `obs_eurusd_daily_change_pct_2026_09_02t23_00_00z`, `obs_usdjpy_daily_change_pct_2026_09_02t23_00_00z`
- Events: none
- Evidence: `evd_dxy_market_move_2026_09_03t04_00_00z`, `evd_eurusd_market_move_2026_09_02t23_00_00z`, `evd_usdjpy_market_move_2026_09_02t23_00_00z`
- Signals: `sig_dollar_fx_quote_alignment_v1_99e634155f1f`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none
- Source references: `src_yahoo_finance`, `src_yahoo_finance_dxy`
- Observed at: ["2026-09-02T23:00:00Z","2026-09-03T04:00:00Z"]
- Scheduled at: []
- Detected at: []

Top Intelligence warnings:

- semantic_story_duplicates_suppressed
- duplicate_or_same_theme_candidates_suppressed

## Data Quality and Coverage

| Artifact | Run / generated at | Validation | Data | Record freshness | Artifact freshness | Age / max hours | Objects | Warnings |
|---|---|---|---|---|---|---:|---:|---:|
| evidence_bundle.json | `run_20260903T094941Z_consolidated_b6515be033a2b0c9`<br>2026-09-03T09:49:41.942940Z | validated | partial | current | current | 3.4e-05 / 24.0 | 63 | 1 |
| market_signals.json | `run_20260903T094941Z_relationships_ec87c2fc99bc03db`<br>2026-09-03T09:49:41.980662Z | validated | partial | current | current | 2.4e-05 / 24.0 | 8 | 1 |
| market_regime.json | `run_20260903T094942Z_regime_104101e92401b5e8`<br>2026-09-03T09:49:42.005953Z | validated | available | current | current | 1.6e-05 / 24.0 | 1 | 0 |
| risk_monitor.json | `run_20260903T094942Z_risk_7db934988052ef5e`<br>2026-09-03T09:49:42.034513Z | validated | partial | current | current | 9e-06 / 24.0 | 3 | 2 |

### Data Quality Warnings

- upstream_partial:evidence_bundle.json
- upstream_partial:market_signals.json
- upstream_partial:risk_monitor.json

### Data Windows

- Composed at: 2026-09-03T09:49:42.065323Z
- Report date: 2026-09-03
- input_generated_at: 2026-09-03T09:49:41.942940Z → 2026-09-03T09:49:42.034513Z
- observed_at: 2026-09-02T04:00:00Z → 2026-09-03T05:00:00Z
- scheduled_at: 2026-09-03T12:30:00Z → 2026-09-03T12:30:00Z
- occurred_at: unknown → unknown
- published_at: unknown → unknown
- retrieved_at: 2026-09-03T09:49:36.956680Z → 2026-09-03T09:49:39.034222Z
- detected_at: 2026-09-03T09:49:42.034513Z → 2026-09-03T09:49:42.034513Z

## Current Market Regime

- Classification: `risk_on`
- Classification scope: current_observed_conditions
- Artifact status: `available`
- Confidence label: `high`
- Confidence score: 0.8375

### Regime Dimensions

- `equity`: eligibility=`eligible`, observed_state=`risk_on`, signal=`sig_equity_index_co_movement_v1_8549080eb48d`
- `volatility`: eligibility=`eligible`, observed_state=`risk_off`, signal=`sig_equity_volatility_inverse_move_v1_61ace3e32c42`
- `crypto`: eligibility=`eligible`, observed_state=`risk_on`, signal=`sig_crypto_co_movement_v1_aecafb33f76e`
- `dollar_yield`: eligibility=`eligible`, observed_state=`mixed`, signal=`sig_dollar_yield_co_movement_v1_680ed3bbbf67`
- `cross_asset_alignment`: eligibility=`eligible`, observed_state=`risk_on`, signal=`sig_equity_crypto_co_movement_v1_2f9b6e9b0752`

Regime warnings:

- None in validated input.

Limitations:

- The classification describes current observations only.
- It does not establish causality, persistence, or later outcomes.
- The classifier does not provide investment or trading instructions.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_regime_595c698a10d3a34e`
- Object type: `market_regime`
- Source artifact: `market_regime.json`
- Source run: `run_20260903T094942Z_regime_104101e92401b5e8`
- Source generated at: 2026-09-03T09:49:42.005953Z
- Validation status: `validated`
- Data status: `available`
- observed_at: ["2026-09-02T04:00:00Z","2026-09-02T05:00:00Z","2026-09-03T00:00:00Z","2026-09-03T04:00:00Z","2026-09-03T05:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260903T094941Z_consolidated_b6515be033a2b0c9`, `run_20260903T094941Z_relationships_ec87c2fc99bc03db`, `run_20260903T094942Z_regime_104101e92401b5e8`
- Evidence bundles: `ebd_4cb1e81b79936ae9b10b`, `ebd_6416c8e31707f297c728`, `ebd_6dbbb75ebc1538cda8b4`, `ebd_7159cab27e384dda620c`, `ebd_a8e7955e1620946e1294`, `ebd_cb82f4dc2e067c02f2b1`, `ebd_f88af88c3ffe6dbbd6a6`
- Sources: `src_yahoo_finance`, `src_yahoo_finance_dxy`, `src_yahoo_finance_us10y`, `src_yahoo_finance_vix`
- Observations: `obs_btc_usd_daily_change_pct_2026_09_03t00_00_00z`, `obs_dxy_daily_change_pct_2026_09_03t04_00_00z`, `obs_eth_usd_daily_change_pct_2026_09_03t00_00_00z`, `obs_qqq_daily_change_pct_2026_09_02t04_00_00z`, `obs_spy_daily_change_pct_2026_09_02t04_00_00z`, `obs_us10y_daily_change_bps_2026_09_02t05_00_00z`, `obs_vix_daily_change_pct_2026_09_03t05_00_00z`
- Events: none
- Evidence: `evd_btc_usd_market_move_2026_09_03t00_00_00z`, `evd_dxy_market_move_2026_09_03t04_00_00z`, `evd_eth_usd_market_move_2026_09_03t00_00_00z`, `evd_qqq_market_move_2026_09_02t04_00_00z`, `evd_spy_market_move_2026_09_02t04_00_00z`, `evd_us10y_market_move_2026_09_02t05_00_00z`, `evd_vix_market_move_2026_09_03t05_00_00z`
- Signals: `sig_crypto_co_movement_v1_aecafb33f76e`, `sig_dollar_yield_co_movement_v1_680ed3bbbf67`, `sig_equity_crypto_co_movement_v1_2f9b6e9b0752`, `sig_equity_index_co_movement_v1_8549080eb48d`, `sig_equity_volatility_inverse_move_v1_61ace3e32c42`
- Regime dimensions: `cross_asset_alignment`, `crypto`, `dollar_yield`, `equity`, `volatility`
- Risks: none
- Coverage inputs: none

</details>

## Cross-Asset Observations

### BTC-USD and ETH-USD daily co-movement

- Signal ID: `sig_crypto_co_movement_v1_aecafb33f76e`
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

- `BTC-USD` daily_change_pct=0.3966 percent; as_of=2026-09-03T00:00:00Z; observation=`obs_btc_usd_daily_change_pct_2026_09_03t00_00_00z`; source=`src_yahoo_finance`
- `ETH-USD` daily_change_pct=0.1149 percent; as_of=2026-09-03T00:00:00Z; observation=`obs_eth_usd_daily_change_pct_2026_09_03t00_00_00z`; source=`src_yahoo_finance`

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_e1e5acf50521e5a1`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- Source generated at: 2026-09-03T09:49:41.980662Z
- Validation status: `validated`
- Data status: `observed`
- observed_at: ["2026-09-03T00:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260903T094941Z_consolidated_b6515be033a2b0c9`, `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- Evidence bundles: `ebd_4cb1e81b79936ae9b10b`, `ebd_6416c8e31707f297c728`
- Sources: `src_yahoo_finance`
- Observations: `obs_btc_usd_daily_change_pct_2026_09_03t00_00_00z`, `obs_eth_usd_daily_change_pct_2026_09_03t00_00_00z`
- Events: none
- Evidence: `evd_btc_usd_market_move_2026_09_03t00_00_00z`, `evd_eth_usd_market_move_2026_09_03t00_00_00z`
- Signals: `sig_crypto_co_movement_v1_aecafb33f76e`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### DXY and major FX quote alignment

- Signal ID: `sig_dollar_fx_quote_alignment_v1_99e634155f1f`
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

- `DXY` daily_change_pct=-0.3224 percent; as_of=2026-09-03T04:00:00Z; observation=`obs_dxy_daily_change_pct_2026_09_03t04_00_00z`; source=`src_yahoo_finance_dxy`
- `EURUSD` daily_change_pct=0.1161 percent; as_of=2026-09-02T23:00:00Z; observation=`obs_eurusd_daily_change_pct_2026_09_02t23_00_00z`; source=`src_yahoo_finance`
- `USDJPY` daily_change_pct=-2.4869 percent; as_of=2026-09-02T23:00:00Z; observation=`obs_usdjpy_daily_change_pct_2026_09_02t23_00_00z`; source=`src_yahoo_finance`

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_8f62c52d1ce2034c`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- Source generated at: 2026-09-03T09:49:41.980662Z
- Validation status: `validated`
- Data status: `observed`
- observed_at: ["2026-09-02T23:00:00Z","2026-09-03T04:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260903T094941Z_consolidated_b6515be033a2b0c9`, `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- Evidence bundles: `ebd_4546fec4d63b69066be0`, `ebd_c307bdcf93780136ea41`, `ebd_cb82f4dc2e067c02f2b1`
- Sources: `src_yahoo_finance`, `src_yahoo_finance_dxy`
- Observations: `obs_dxy_daily_change_pct_2026_09_03t04_00_00z`, `obs_eurusd_daily_change_pct_2026_09_02t23_00_00z`, `obs_usdjpy_daily_change_pct_2026_09_02t23_00_00z`
- Events: none
- Evidence: `evd_dxy_market_move_2026_09_03t04_00_00z`, `evd_eurusd_market_move_2026_09_02t23_00_00z`, `evd_usdjpy_market_move_2026_09_02t23_00_00z`
- Signals: `sig_dollar_fx_quote_alignment_v1_99e634155f1f`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### DXY and US10Y daily co-movement

- Signal ID: `sig_dollar_yield_co_movement_v1_680ed3bbbf67`
- Rule ID: `dollar_yield_co_movement_v1`
- Relationship: `co_movement`
- State: `not_observed`
- Condition met: `false`
- Data quality: `available`
- Confidence: `medium` (0.75)

Data-quality details:

- conflicting_inputs: []
- issues: []
- missing_inputs: []
- stale_observation_ids: []
- status: available

Observed values:

- `DXY` daily_change_pct=-0.3224 percent; as_of=2026-09-03T04:00:00Z; observation=`obs_dxy_daily_change_pct_2026_09_03t04_00_00z`; source=`src_yahoo_finance_dxy`
- `US10Y` daily_change_bps=0.0 basis_points; as_of=2026-09-02T05:00:00Z; observation=`obs_us10y_daily_change_bps_2026_09_02t05_00_00z`; source=`src_yahoo_finance_us10y`

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_a3308f3fe164599a`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- Source generated at: 2026-09-03T09:49:41.980662Z
- Validation status: `validated`
- Data status: `not_observed`
- observed_at: ["2026-09-02T05:00:00Z","2026-09-03T04:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260903T094941Z_consolidated_b6515be033a2b0c9`, `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- Evidence bundles: `ebd_7159cab27e384dda620c`, `ebd_cb82f4dc2e067c02f2b1`
- Sources: `src_yahoo_finance_dxy`, `src_yahoo_finance_us10y`
- Observations: `obs_dxy_daily_change_pct_2026_09_03t04_00_00z`, `obs_us10y_daily_change_bps_2026_09_02t05_00_00z`
- Events: none
- Evidence: `evd_dxy_market_move_2026_09_03t04_00_00z`, `evd_us10y_market_move_2026_09_02t05_00_00z`
- Signals: `sig_dollar_yield_co_movement_v1_680ed3bbbf67`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### Equity indexes and BTC-USD daily co-movement

- Signal ID: `sig_equity_crypto_co_movement_v1_2f9b6e9b0752`
- Rule ID: `equity_crypto_co_movement_v1`
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

- `BTC-USD` daily_change_pct=0.3966 percent; as_of=2026-09-03T00:00:00Z; observation=`obs_btc_usd_daily_change_pct_2026_09_03t00_00_00z`; source=`src_yahoo_finance`
- `QQQ` daily_change_pct=0.2261 percent; as_of=2026-09-02T04:00:00Z; observation=`obs_qqq_daily_change_pct_2026_09_02t04_00_00z`; source=`src_yahoo_finance`
- `SPY` daily_change_pct=0.4437 percent; as_of=2026-09-02T04:00:00Z; observation=`obs_spy_daily_change_pct_2026_09_02t04_00_00z`; source=`src_yahoo_finance`

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_e5a17275ae98cfe3`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- Source generated at: 2026-09-03T09:49:41.980662Z
- Validation status: `validated`
- Data status: `observed`
- observed_at: ["2026-09-02T04:00:00Z","2026-09-03T00:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260903T094941Z_consolidated_b6515be033a2b0c9`, `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- Evidence bundles: `ebd_4cb1e81b79936ae9b10b`, `ebd_6dbbb75ebc1538cda8b4`, `ebd_a8e7955e1620946e1294`
- Sources: `src_yahoo_finance`
- Observations: `obs_btc_usd_daily_change_pct_2026_09_03t00_00_00z`, `obs_qqq_daily_change_pct_2026_09_02t04_00_00z`, `obs_spy_daily_change_pct_2026_09_02t04_00_00z`
- Events: none
- Evidence: `evd_btc_usd_market_move_2026_09_03t00_00_00z`, `evd_qqq_market_move_2026_09_02t04_00_00z`, `evd_spy_market_move_2026_09_02t04_00_00z`
- Signals: `sig_equity_crypto_co_movement_v1_2f9b6e9b0752`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### SPY and QQQ daily co-movement

- Signal ID: `sig_equity_index_co_movement_v1_8549080eb48d`
- Rule ID: `equity_index_co_movement_v1`
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

- `QQQ` daily_change_pct=0.2261 percent; as_of=2026-09-02T04:00:00Z; observation=`obs_qqq_daily_change_pct_2026_09_02t04_00_00z`; source=`src_yahoo_finance`
- `SPY` daily_change_pct=0.4437 percent; as_of=2026-09-02T04:00:00Z; observation=`obs_spy_daily_change_pct_2026_09_02t04_00_00z`; source=`src_yahoo_finance`

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_fb68d86192c4744d`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- Source generated at: 2026-09-03T09:49:41.980662Z
- Validation status: `validated`
- Data status: `observed`
- observed_at: ["2026-09-02T04:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260903T094941Z_consolidated_b6515be033a2b0c9`, `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- Evidence bundles: `ebd_6dbbb75ebc1538cda8b4`, `ebd_a8e7955e1620946e1294`
- Sources: `src_yahoo_finance`
- Observations: `obs_qqq_daily_change_pct_2026_09_02t04_00_00z`, `obs_spy_daily_change_pct_2026_09_02t04_00_00z`
- Events: none
- Evidence: `evd_qqq_market_move_2026_09_02t04_00_00z`, `evd_spy_market_move_2026_09_02t04_00_00z`
- Signals: `sig_equity_index_co_movement_v1_8549080eb48d`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### SPY and QQQ daily divergence

- Signal ID: `sig_equity_index_divergence_v1_c206ac641826`
- Rule ID: `equity_index_divergence_v1`
- Relationship: `divergence`
- State: `not_observed`
- Condition met: `false`
- Data quality: `available`
- Confidence: `high` (0.95)

Data-quality details:

- conflicting_inputs: []
- issues: []
- missing_inputs: []
- stale_observation_ids: []
- status: available

Observed values:

- `QQQ` daily_change_pct=0.2261 percent; as_of=2026-09-02T04:00:00Z; observation=`obs_qqq_daily_change_pct_2026_09_02t04_00_00z`; source=`src_yahoo_finance`
- `SPY` daily_change_pct=0.4437 percent; as_of=2026-09-02T04:00:00Z; observation=`obs_spy_daily_change_pct_2026_09_02t04_00_00z`; source=`src_yahoo_finance`

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_bd8ef3d179698cf8`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- Source generated at: 2026-09-03T09:49:41.980662Z
- Validation status: `validated`
- Data status: `not_observed`
- observed_at: ["2026-09-02T04:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260903T094941Z_consolidated_b6515be033a2b0c9`, `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- Evidence bundles: `ebd_6dbbb75ebc1538cda8b4`, `ebd_a8e7955e1620946e1294`
- Sources: `src_yahoo_finance`
- Observations: `obs_qqq_daily_change_pct_2026_09_02t04_00_00z`, `obs_spy_daily_change_pct_2026_09_02t04_00_00z`
- Events: none
- Evidence: `evd_qqq_market_move_2026_09_02t04_00_00z`, `evd_spy_market_move_2026_09_02t04_00_00z`
- Signals: `sig_equity_index_divergence_v1_c206ac641826`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### Equity indexes and VIX inverse daily movement

- Signal ID: `sig_equity_volatility_inverse_move_v1_61ace3e32c42`
- Rule ID: `equity_volatility_inverse_move_v1`
- Relationship: `inverse_movement`
- State: `not_observed`
- Condition met: `false`
- Data quality: `available`
- Confidence: `medium` (0.75)

Data-quality details:

- conflicting_inputs: []
- issues: []
- missing_inputs: []
- stale_observation_ids: []
- status: available

Observed values:

- `QQQ` daily_change_pct=0.2261 percent; as_of=2026-09-02T04:00:00Z; observation=`obs_qqq_daily_change_pct_2026_09_02t04_00_00z`; source=`src_yahoo_finance`
- `SPY` daily_change_pct=0.4437 percent; as_of=2026-09-02T04:00:00Z; observation=`obs_spy_daily_change_pct_2026_09_02t04_00_00z`; source=`src_yahoo_finance`
- `VIX` daily_change_pct=0.1316 percent; as_of=2026-09-03T05:00:00Z; observation=`obs_vix_daily_change_pct_2026_09_03t05_00_00z`; source=`src_yahoo_finance_vix`

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_fbc9024ac3f5aead`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- Source generated at: 2026-09-03T09:49:41.980662Z
- Validation status: `validated`
- Data status: `not_observed`
- observed_at: ["2026-09-02T04:00:00Z","2026-09-03T05:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260903T094941Z_consolidated_b6515be033a2b0c9`, `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- Evidence bundles: `ebd_6dbbb75ebc1538cda8b4`, `ebd_a8e7955e1620946e1294`, `ebd_f88af88c3ffe6dbbd6a6`
- Sources: `src_yahoo_finance`, `src_yahoo_finance_vix`
- Observations: `obs_qqq_daily_change_pct_2026_09_02t04_00_00z`, `obs_spy_daily_change_pct_2026_09_02t04_00_00z`, `obs_vix_daily_change_pct_2026_09_03t05_00_00z`
- Events: none
- Evidence: `evd_qqq_market_move_2026_09_02t04_00_00z`, `evd_spy_market_move_2026_09_02t04_00_00z`, `evd_vix_market_move_2026_09_03t05_00_00z`
- Signals: `sig_equity_volatility_inverse_move_v1_61ace3e32c42`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

### Gold and DXY inverse daily movement

- Signal ID: `sig_gold_dollar_inverse_move_v1_b788f58b52f2`
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

- `DXY` daily_change_pct=-0.3224 percent; as_of=2026-09-03T04:00:00Z; observation=`obs_dxy_daily_change_pct_2026_09_03t04_00_00z`; source=`src_yahoo_finance_dxy`
- `GOLD` daily_change_pct=2.5445 percent; as_of=2026-09-03T04:00:00Z; observation=`obs_gold_daily_change_pct_2026_09_03t04_00_00z`; source=`src_yahoo_finance`

Limitations:

- This relationship describes same-window observations and does not establish causality, persistence, or a future outcome.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_signal_291cfe7a314451e0`
- Object type: `cross_asset_signal`
- Source artifact: `market_signals.json`
- Source run: `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- Source generated at: 2026-09-03T09:49:41.980662Z
- Validation status: `validated`
- Data status: `observed`
- observed_at: ["2026-09-03T04:00:00Z"]
- scheduled_at: []
- detected_at: []

Evidence references:

- Artifact runs: `run_20260903T094941Z_consolidated_b6515be033a2b0c9`, `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- Evidence bundles: `ebd_8c7e99b1acb0ae62a341`, `ebd_cb82f4dc2e067c02f2b1`
- Sources: `src_yahoo_finance`, `src_yahoo_finance_dxy`
- Observations: `obs_dxy_daily_change_pct_2026_09_03t04_00_00z`, `obs_gold_daily_change_pct_2026_09_03t04_00_00z`
- Events: none
- Evidence: `evd_dxy_market_move_2026_09_03t04_00_00z`, `evd_gold_market_move_2026_09_03t04_00_00z`
- Signals: `sig_gold_dollar_inverse_move_v1_b788f58b52f2`
- Regime dimensions: none
- Risks: none
- Coverage inputs: none

</details>

## Upcoming Event Risks

### Scheduled official event: U.S. International Trade in Goods and Services, July 2026

- Risk ID: `rsk_upcoming_official_event_v1_33fae68465aa5c86`
- Rule ID: `upcoming_official_event_v1`
- Category: `upcoming_event`
- Status: `scheduled`
- Attention level: `low`
- Description: An official calendar event is scheduled within the next 48 hours.
- Related assets: ["DXY","QQQ","SPY","US10Y"]

Observed facts:

- country: US
- event_id: evt_20260903_u_s_international_trade_in_goods_and_5ed967ecb2
- impact: low
- name: U.S. International Trade in Goods and Services, July 2026
- scheduled_at: 2026-09-03T12:30:00Z
- topics: ["us_economy"]

Time window:

- scheduled_at: 2026-09-03T12:30:00Z
- window_end: 2026-09-05T09:49:42.034513Z
- window_start: 2026-09-03T09:49:42.034513Z

Limitations:

- The scheduled event does not imply a specific market response.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_risk_fbd741747aadee00`
- Object type: `upcoming_event_risk`
- Source artifact: `risk_monitor.json`
- Source run: `run_20260903T094942Z_risk_7db934988052ef5e`
- Source generated at: 2026-09-03T09:49:42.034513Z
- Validation status: `validated`
- Data status: `scheduled`
- observed_at: []
- scheduled_at: ["2026-09-03T12:30:00Z"]
- detected_at: []

Evidence references:

- Artifact runs: `run_20260903T094941Z_consolidated_b6515be033a2b0c9`, `run_20260903T094941Z_relationships_ec87c2fc99bc03db`, `run_20260903T094942Z_regime_104101e92401b5e8`, `run_20260903T094942Z_risk_7db934988052ef5e`
- Evidence bundles: `ebd_70eb06a1cf9a20519c76`
- Sources: `src_calendar_4a850d66272d3d7b`
- Observations: none
- Events: `evt_20260903_u_s_international_trade_in_goods_and_5ed967ecb2`
- Evidence: none
- Signals: none
- Regime dimensions: none
- Risks: `rsk_upcoming_official_event_v1_33fae68465aa5c86`
- Coverage inputs: none

</details>

## Data Quality Risks

### Degraded input coverage: economic_calendar

- Risk ID: `rsk_input_coverage_degraded_v1_de12ff42675c3d4b`
- Rule ID: `input_coverage_degraded_v1`
- Category: `data_quality`
- Status: `detected`
- Attention level: `medium`
- Description: The consolidated Evidence input reports incomplete or stale coverage.
- Related assets: ["DXY","QQQ","SPY","US10Y"]

Observed facts:

- artifact: economic_calendar.json
- coverage_status: partial
- input_type: economic_calendar
- record_count: 1
- stale_record_count: 0

Time window:

- detected_at: 2026-09-03T09:49:42.034513Z

Limitations:

- This item concerns data reliability, not market prices.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_risk_d2e35c23b32a7606`
- Object type: `data_quality_risk`
- Source artifact: `risk_monitor.json`
- Source run: `run_20260903T094942Z_risk_7db934988052ef5e`
- Source generated at: 2026-09-03T09:49:42.034513Z
- Validation status: `validated`
- Data status: `detected`
- observed_at: []
- scheduled_at: []
- detected_at: ["2026-09-03T09:49:42.034513Z"]

Evidence references:

- Artifact runs: `run_20260903T094941Z_consolidated_b6515be033a2b0c9`, `run_20260903T094941Z_relationships_ec87c2fc99bc03db`, `run_20260903T094942Z_regime_104101e92401b5e8`, `run_20260903T094942Z_risk_7db934988052ef5e`
- Evidence bundles: `ebd_70eb06a1cf9a20519c76`
- Sources: `src_calendar_4a850d66272d3d7b`
- Observations: none
- Events: `evt_20260903_u_s_international_trade_in_goods_and_5ed967ecb2`
- Evidence: none
- Signals: none
- Regime dimensions: none
- Risks: `rsk_input_coverage_degraded_v1_de12ff42675c3d4b`
- Coverage inputs: `economic_calendar`

</details>

### Cross-asset relationship coverage degraded

- Risk ID: `rsk_market_signal_coverage_degraded_v1_d0f8d7f4dcaca1ae`
- Rule ID: `market_signal_coverage_degraded_v1`
- Category: `data_quality`
- Status: `detected`
- Attention level: `medium`
- Description: One or more cross-asset relationship evaluations are stale or incomplete.
- Related assets: []

Observed facts:

- artifact_status: partial
- state_counts: {"insufficient_data":0,"not_observed":3,"observed":5,"stale_data":0}

Time window:

- detected_at: 2026-09-03T09:49:42.034513Z

Limitations:

- This item concerns analytical coverage only.

<details><summary>Traceability</summary>

Object metadata:

- Object ID: `int_risk_113c859d2eae9679`
- Object type: `data_quality_risk`
- Source artifact: `risk_monitor.json`
- Source run: `run_20260903T094942Z_risk_7db934988052ef5e`
- Source generated at: 2026-09-03T09:49:42.034513Z
- Validation status: `validated`
- Data status: `detected`
- observed_at: []
- scheduled_at: []
- detected_at: ["2026-09-03T09:49:42.034513Z"]

Evidence references:

- Artifact runs: `run_20260903T094941Z_consolidated_b6515be033a2b0c9`, `run_20260903T094941Z_relationships_ec87c2fc99bc03db`, `run_20260903T094942Z_regime_104101e92401b5e8`, `run_20260903T094942Z_risk_7db934988052ef5e`
- Evidence bundles: none
- Sources: none
- Observations: none
- Events: none
- Evidence: none
- Signals: none
- Regime dimensions: none
- Risks: `rsk_market_signal_coverage_degraded_v1_d0f8d7f4dcaca1ae`
- Coverage inputs: none

</details>

## Observed Market Stress

- None in validated input.

## Sources and Provenance

### Input Runs

- evidence_bundle_run_id: `run_20260903T094941Z_consolidated_b6515be033a2b0c9`
- market_signals_run_id: `run_20260903T094941Z_relationships_ec87c2fc99bc03db`
- market_regime_run_id: `run_20260903T094942Z_regime_104101e92401b5e8`
- risk_monitor_run_id: `run_20260903T094942Z_risk_7db934988052ef5e`

### Source Registry

- `src_calendar_4a850d66272d3d7b` — U.S. Bureau of Economic Analysis: U.S. International Trade in Goods and Services, July 2026
  - URL: https://www.bea.gov/news/schedule/full
  - Published at: unknown
  - Retrieved at: 2026-09-03T09:49:39.034222Z
  - Quality tier: 1
- `src_yahoo_finance` — Yahoo Finance: Yahoo Finance market snapshot
  - URL: https://finance.yahoo.com/
  - Published at: unknown
  - Retrieved at: 2026-09-03T09:49:36.956680Z
  - Quality tier: 3
- `src_yahoo_finance_dxy` — Yahoo Finance: U.S. Dollar Index macro proxy
  - URL: https://finance.yahoo.com/quote/DX-Y.NYB/
  - Published at: unknown
  - Retrieved at: 2026-09-03T09:49:38.576001Z
  - Quality tier: 3
- `src_yahoo_finance_us10y` — Yahoo Finance: U.S. 10-Year Treasury Yield macro proxy
  - URL: https://finance.yahoo.com/quote/%5ETNX/
  - Published at: unknown
  - Retrieved at: 2026-09-03T09:49:38.576001Z
  - Quality tier: 3
- `src_yahoo_finance_vix` — Yahoo Finance: Cboe Volatility Index macro proxy
  - URL: https://finance.yahoo.com/quote/%5EVIX/
  - Published at: unknown
  - Retrieved at: 2026-09-03T09:49:38.576001Z
  - Quality tier: 3

### Provenance Catalog IDs

- Evidence bundles: `ebd_4546fec4d63b69066be0`, `ebd_4cb1e81b79936ae9b10b`, `ebd_6416c8e31707f297c728`, `ebd_6dbbb75ebc1538cda8b4`, `ebd_70eb06a1cf9a20519c76`, `ebd_7159cab27e384dda620c`, `ebd_8c7e99b1acb0ae62a341`, `ebd_a8e7955e1620946e1294`, `ebd_c307bdcf93780136ea41`, `ebd_cb82f4dc2e067c02f2b1`, `ebd_f88af88c3ffe6dbbd6a6`
- Sources: `src_calendar_4a850d66272d3d7b`, `src_yahoo_finance`, `src_yahoo_finance_dxy`, `src_yahoo_finance_us10y`, `src_yahoo_finance_vix`
- Observations: `obs_btc_usd_daily_change_pct_2026_09_03t00_00_00z`, `obs_dxy_daily_change_pct_2026_09_03t04_00_00z`, `obs_eth_usd_daily_change_pct_2026_09_03t00_00_00z`, `obs_eurusd_daily_change_pct_2026_09_02t23_00_00z`, `obs_gold_daily_change_pct_2026_09_03t04_00_00z`, `obs_qqq_daily_change_pct_2026_09_02t04_00_00z`, `obs_spy_daily_change_pct_2026_09_02t04_00_00z`, `obs_us10y_daily_change_bps_2026_09_02t05_00_00z`, `obs_usdjpy_daily_change_pct_2026_09_02t23_00_00z`, `obs_vix_daily_change_pct_2026_09_03t05_00_00z`
- Events: `evt_20260903_u_s_international_trade_in_goods_and_5ed967ecb2`
- Evidence records: `evd_btc_usd_market_move_2026_09_03t00_00_00z`, `evd_dxy_market_move_2026_09_03t04_00_00z`, `evd_eth_usd_market_move_2026_09_03t00_00_00z`, `evd_eurusd_market_move_2026_09_02t23_00_00z`, `evd_gold_market_move_2026_09_03t04_00_00z`, `evd_qqq_market_move_2026_09_02t04_00_00z`, `evd_spy_market_move_2026_09_02t04_00_00z`, `evd_us10y_market_move_2026_09_02t05_00_00z`, `evd_usdjpy_market_move_2026_09_02t23_00_00z`, `evd_vix_market_move_2026_09_03t05_00_00z`

## Scope Limitations

- structured_assembly_only
- no_new_interpretation
- no_market_outlook_or_trade_action
