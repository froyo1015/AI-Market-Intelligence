"use strict";

const assert = require("node:assert/strict");
const path = require("node:path");
const view = require(path.resolve(
  __dirname,
  "../../src/pages/static/intelligence.js"
));

function coverage(status) {
  return ["evidence", "signals", "regime", "risk"].map(function (name) {
    return {
      artifact: name,
      validation_status: "validated",
      data_status: status,
      freshness_status: "current",
      artifact_freshness_status: "current"
    };
  });
}

function wrapper(type, payload, refs) {
  return {
    object_id: "obj_" + type + "_" + (payload.signal_id || payload.risk_id || "regime"),
    object_type: type,
    validation_status: "validated",
    data_status: payload.state || payload.status,
    payload: payload,
    evidence_refs: refs || {
      source_ids: [],
      evidence_ids: [],
      observation_ids: [],
      event_ids: []
    }
  };
}

function daily(status, classification) {
  const regimePayload = {
    run_id: "run_regime",
    status: classification ? status : "unavailable",
    classification: classification,
    confidence: { label: classification ? "high" : "insufficient", score: classification ? 0.8 : 0 },
    dimensions: [],
    evidence_refs: {}
  };
  return {
    artifact_type: "daily_intelligence",
    generated_at: "2026-08-28T00:00:00Z",
    status: status,
    coverage: coverage(status),
    warnings: status === "partial" ? ["upstream_partial:risk_monitor.json"] : [],
    market_regime: wrapper("market_regime", regimePayload),
    cross_asset_signals: [],
    upcoming_events: [],
    data_quality_risks: [],
    observed_market_stress: [],
    provenance_catalog: {
      source_records: [],
      observation_records: [],
      event_records: []
    },
    data_window: {}
  };
}

const missing = view.buildViewModel({}, ["dailyIntelligence unavailable: HTTP 404"]);
assert.equal(missing.dataStatus, "unavailable");
assert.equal(missing.regime.classification, "unavailable");
assert.match(missing.regime.message, /insufficient fresh evidence/);
assert.equal(missing.signals.length, 0);

const unavailableInput = daily("unavailable", null);
unavailableInput.coverage.forEach(function (item) {
  item.freshness_status = "stale";
  item.artifact_freshness_status = "stale";
});
const unavailable = view.buildViewModel({ dailyIntelligence: unavailableInput }, []);
assert.equal(unavailable.dataStatus, "unavailable");
assert.equal(unavailable.freshnessStatus, "stale");
assert.equal(unavailable.regime.classification, "unavailable");
assert.equal(unavailable.validationStatus, "validated");

const partialInput = daily("partial", "mixed");
const partial = view.buildViewModel({ dailyIntelligence: partialInput }, []);
assert.equal(partial.dataStatus, "partial");
assert.equal(partial.freshnessStatus, "current");
assert.equal(partial.regime.classification, "mixed");
assert.deepEqual(partial.warnings, ["upstream_partial:risk_monitor.json"]);

const validInput = daily("available", "risk_on");
validInput.cross_asset_signals = [
  wrapper("cross_asset_signal", {
    signal_id: "sig_observed",
    label: "Observed relationship",
    state: "observed",
    relationship_kind: "co_movement",
    required_assets: ["SPY", "QQQ"]
  }, {
    source_ids: ["src_market"],
    evidence_ids: ["evd_market"],
    observation_ids: ["obs_spy"],
    event_ids: []
  }),
  wrapper("cross_asset_signal", {
    signal_id: "sig_not_observed",
    label: "Not observed relationship",
    state: "not_observed",
    relationship_kind: "co_movement",
    required_assets: ["BTC-USD", "ETH-USD"]
  })
];
validInput.data_quality_risks = [wrapper("data_quality_risk", {
  risk_id: "risk_quality",
  category: "data_quality",
  title: "Coverage degraded",
  description: "One source is unavailable.",
  attention_level: "medium",
  status: "detected"
})];
validInput.provenance_catalog.source_records = [{
  source_id: "src_market",
  title: "Market source",
  url: "https://example.com/source",
  published_at: null,
  retrieved_at: "2026-08-28T00:00:00Z"
}];
validInput.provenance_catalog.observation_records = [{ observation_id: "obs_spy" }];
const valid = view.buildViewModel({
  dailyIntelligence: validInput,
  marketSnapshot: {
    generated_at: "2026-08-28T00:00:00Z",
    records: [
      { symbol: "SPY", price: 100, daily_change: 1, status: "success", timestamp: "2026-08-28T00:00:00Z", source: "test" },
      { symbol: "BTC-USD", price: 60000, daily_change: 0.5, status: "success", timestamp: "2026-08-28T00:00:00Z", source: "test" }
    ]
  },
  macroSnapshot: {
    generated_at: "2026-08-28T00:00:00Z",
    records: [
      { symbol: "DXY", value: 100, daily_change: -0.2, value_unit: "index_points", change_unit: "percent", status: "success", timestamp: "2026-08-28T00:00:00Z", source: "test" }
    ]
  },
  deterministicBrief: "# Brief"
}, []);
assert.equal(valid.dataStatus, "available");
assert.equal(valid.validationStatus, "validated");
assert.equal(valid.regime.classification, "risk_on");
assert.equal(valid.signals.length, 1);
assert.equal(valid.signals[0].id, "sig_observed");
assert.deepEqual(valid.signals[0].assets, ["SPY", "QQQ"]);
assert.equal(valid.risks.length, 1);
assert.deepEqual(valid.markets.map(function (item) { return item.symbol; }), [
  "BTC-USD", "SPY", "DXY"
]);
assert.equal(valid.briefAvailable, true);
assert.deepEqual(valid.audit.observationIds, ["obs_spy"]);

console.log("intelligence-view tests passed");
