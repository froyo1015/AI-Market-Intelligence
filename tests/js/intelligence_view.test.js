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

function groundedManifest(mode, freshness) {
  const selectedMode = mode || "grounded_ai";
  const isFallback = selectedMode === "deterministic_fallback";
  return {
    artifact_type: "run_manifest",
    modules: [{
      name: "grounded_ai_brief",
      status: "success",
      freshness_status: freshness || "current",
      generated_at: "2026-08-28T00:01:00Z",
      generation_metadata: {
        generation_mode: selectedMode,
        generation_status: isFallback ? "fallback" : "success",
        generated_at: "2026-08-28T00:00:59Z",
        freshness_status: freshness || "current",
        validation_status: "validated",
        provider: isFallback ? null : "static_test_writer",
        fallback_reason: isFallback ? "no_provider_configured" : null
      },
      artifacts: [{
        path: "ai_market_brief.md",
        generated_at: "2026-08-28T00:00:59Z",
        approved_for_publication: true
      }]
    }]
  };
}

const missing = view.buildViewModel({}, ["dailyIntelligence unavailable: HTTP 404"]);
assert.equal(missing.dataStatus, "unavailable");
assert.equal(missing.regime.classification, "unavailable");
assert.match(missing.regime.message, /insufficient fresh evidence/);
assert.equal(missing.signals.length, 0);
assert.equal(missing.topIntelligence.items.length, 0);
assert.equal(missing.topIntelligence.message, "No current validated Top 3 intelligence is available.");
assert.equal(missing.aiBrief.available, false);
assert.equal(missing.aiBrief.mode, "unavailable");

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

const canonicalFreshnessInput = daily("partial", "mixed");
canonicalFreshnessInput.freshness_status = "unknown";
canonicalFreshnessInput.coverage.forEach(function (item) {
  item.freshness_status = "stale";
  item.artifact_freshness_status = "stale";
});
const canonicalFreshness = view.buildViewModel(
  { dailyIntelligence: canonicalFreshnessInput },
  []
);
assert.equal(canonicalFreshness.freshnessStatus, "unknown");

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
  topIntelligence: {
    artifact_type: "top_intelligence",
    status: "partial",
    freshness_status: "current",
    items: [{
      rank: 1,
      item_id: "top_1",
      type: "market_regime",
      story_key: "market_state:risk_on",
      headline: "Current market regime: risk_on",
      why: "Validated current dimensions.",
      monitor: "Monitor current dimensions.",
      total_score: 81,
      related_assets: ["SPY", "QQQ"],
      freshness_status: "current",
      validation_status: "validated",
      evidence_refs: { source_ids: ["src_market"], regime_dimension_ids: ["equity"] },
      source_refs: ["src_market"]
    }]
  },
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
  aiBrief: "# Daily Market Intelligence Brief\n\nGrounded narrative.\n\n[refs: obs_spy]",
  runManifest: groundedManifest(),
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
assert.equal(valid.deterministicBriefAvailable, true);
assert.equal(valid.aiBrief.available, true);
assert.equal(valid.aiBrief.mode, "grounded_ai");
assert.equal(valid.aiBrief.modeLabel, "Grounded AI");
assert.equal(valid.aiBrief.generatedAt, "2026-08-28T00:00:59Z");
assert.equal(valid.aiBrief.freshnessStatus, "current");
assert.equal(valid.aiBrief.validationStatus, "validated");
assert.equal(valid.aiBrief.provider, "static_test_writer");
assert.equal(valid.aiBrief.metadataSource, "explicit");
assert.equal(valid.topIntelligence.items.length, 1);
assert.equal(valid.topIntelligence.items[0].score, 81);
assert.equal(valid.topIntelligence.items[0].storyKey, "market_state:risk_on");
assert.deepEqual(valid.audit.observationIds, ["obs_spy"]);

const fallbackText = "# Daily Market Intelligence Brief\n\nValidated fallback.\n\n[refs: risk_quality]";
const fallback = view.buildViewModel({
  dailyIntelligence: validInput,
  topIntelligence: {
    artifact_type: "top_intelligence",
    status: "available",
    freshness_status: "current",
    items: [{
      rank: 1,
      item_id: "top_preserved",
      type: "risk",
      story_key: "data_quality:coverage",
      headline: "Coverage status",
      why: "Validated source coverage.",
      monitor: "Monitor source recovery.",
      total_score: 70,
      related_assets: [],
      freshness_status: "current",
      validation_status: "validated",
      evidence_refs: { risk_ids: ["risk_quality"] },
      source_refs: []
    }]
  },
  aiBrief: fallbackText,
  deterministicBrief: fallbackText,
  runManifest: groundedManifest("deterministic_fallback", "current")
}, []);
assert.equal(fallback.aiBrief.mode, "deterministic_fallback");
assert.equal(fallback.aiBrief.modeLabel, "Deterministic fallback");
assert.equal(
  fallback.aiBrief.fallbackNote,
  "AI generation was unavailable; the validated deterministic brief is shown instead."
);
assert.equal(fallback.aiBrief.validationStatus, "validated");
assert.equal(fallback.aiBrief.fallbackReason, "no_provider_configured");
assert.equal(fallback.aiBrief.metadataSource, "explicit");
assert.equal(fallback.topIntelligence.items[0].id, "top_preserved");

const explicitWins = view.normalizeAIBrief(
  fallbackText,
  fallbackText,
  groundedManifest("grounded_ai", "current")
);
assert.equal(explicitWins.mode, "grounded_ai");
assert.equal(explicitWins.metadataSource, "explicit");
assert.equal(explicitWins.fallbackNote, "");

const missingBrief = view.buildViewModel({
  dailyIntelligence: validInput,
  topIntelligence: {
    artifact_type: "top_intelligence",
    status: "available",
    freshness_status: "current",
    items: [{
      rank: 1,
      item_id: "top_preserved",
      type: "risk",
      story_key: "data_quality:coverage",
      headline: "Coverage status",
      why: "Validated source coverage.",
      monitor: "Monitor source recovery.",
      total_score: 70,
      related_assets: [],
      freshness_status: "current",
      validation_status: "validated",
      evidence_refs: { risk_ids: ["risk_quality"] },
      source_refs: []
    }]
  }
}, ["aiBrief unavailable: HTTP 404"]);
assert.equal(missingBrief.aiBrief.available, false);
assert.equal(missingBrief.aiBrief.mode, "unavailable");
assert.equal(missingBrief.topIntelligence.items.length, 1);

const safeBlocks = view.parseSafeMarkdown(
  "# Safe heading\n\n<script>alert('x')</script>\n\n- item\n\n[refs: obs_spy, evd_market]"
);
assert.deepEqual(safeBlocks.map(function (block) { return block.kind; }), [
  "heading", "paragraph", "list", "reference"
]);
assert.equal(safeBlocks[1].text, "<script>alert('x')</script>");
assert.equal(safeBlocks[3].text, "[refs: obs_spy, evd_market]");
assert.equal(safeBlocks.some(function (block) { return block.kind === "html"; }), false);

const unknownMetadata = view.normalizeAIBrief("Brief", null, null);
assert.equal(unknownMetadata.mode, "grounded_ai");
assert.equal(unknownMetadata.generatedAt, "unknown");
assert.equal(unknownMetadata.freshnessStatus, "unknown");
assert.equal(unknownMetadata.validationStatus, "unknown");
assert.equal(unknownMetadata.metadataSource, "legacy_file_comparison");

const legacyFallback = view.normalizeAIBrief("Same", "Same", {
  modules: [{
    name: "grounded_ai_brief",
    status: "success",
    freshness_status: "current",
    generated_at: "2026-08-28T00:01:00Z",
    artifacts: [{
      path: "ai_market_brief.md",
      generated_at: "2026-08-28T00:00:59Z",
      approved_for_publication: true
    }]
  }]
});
assert.equal(legacyFallback.mode, "deterministic_fallback");
assert.equal(legacyFallback.metadataSource, "legacy_file_comparison");

console.log("intelligence-view tests passed");
