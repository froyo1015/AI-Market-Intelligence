(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.IntelligenceView = api;
  if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", function () {
      api.initialize(document, root.fetch.bind(root));
    });
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const ENDPOINTS = {
    dailyIntelligence: ["data/daily_intelligence.json", "json"],
    marketSignals: ["data/market_signals.json", "json"],
    marketRegime: ["data/market_regime.json", "json"],
    riskMonitor: ["data/risk_monitor.json", "json"],
    marketSnapshot: ["data/market_snapshot.json", "json"],
    macroSnapshot: ["data/macro_snapshot.json", "json"],
    deterministicBrief: ["data/daily_market_brief.md", "text"]
  };
  const MARKET_ORDER = [
    "BTC-USD", "ETH-USD", "SPY", "QQQ", "GOLD", "DXY", "US10Y", "VIX"
  ];
  const RISK_CATEGORIES = [
    ["upcoming_event", "Upcoming Events"],
    ["data_quality", "Data Quality Risks"],
    ["market_stress", "Observed Market Stress"]
  ];
  const REFERENCE_KEYS = [
    "evidence_bundle_ids", "source_ids", "observation_ids", "event_ids",
    "evidence_ids", "signal_ids", "regime_dimension_ids", "risk_ids",
    "coverage_inputs"
  ];

  async function loadResources(fetchImpl) {
    const resources = {};
    const errors = [];
    await Promise.all(Object.entries(ENDPOINTS).map(async function (entry) {
      const name = entry[0];
      const url = entry[1][0];
      const kind = entry[1][1];
      try {
        const response = await fetchImpl(url, { cache: "no-store" });
        if (!response.ok) {
          throw new Error("HTTP " + response.status);
        }
        resources[name] = kind === "json" ? await response.json() : await response.text();
      } catch (error) {
        resources[name] = null;
        errors.push(name + " unavailable: " + error.message);
      }
    }));
    return { resources: resources, errors: errors.sort() };
  }

  function buildViewModel(resources, loadErrors) {
    const daily = asObject(resources.dailyIntelligence);
    const regime = normalizeRegime(daily, resources.marketRegime);
    const signals = normalizeSignals(daily, resources.marketSignals);
    const risks = normalizeRisks(daily, resources.riskMonitor);
    const markets = normalizeMarkets(resources.marketSnapshot, resources.macroSnapshot);
    const coverage = daily && Array.isArray(daily.coverage) ? daily.coverage : [];
    const intelligenceStatus = daily ? safeStatus(daily.status) : "unavailable";
    const freshness = overallFreshness(coverage, daily);
    const validation = overallValidation(daily, coverage);
    const generatedAt = daily && daily.generated_at ? daily.generated_at : latestTimestamp([
      resources.marketRegime,
      resources.marketSignals,
      resources.riskMonitor,
      resources.marketSnapshot,
      resources.macroSnapshot
    ]);
    const warnings = uniqueStrings(
      (daily && Array.isArray(daily.warnings) ? daily.warnings : []).concat(loadErrors || [])
    );
    if (!daily) {
      warnings.unshift("daily_intelligence.json unavailable; showing validated source artifacts where present.");
    }
    return {
      generatedAt: generatedAt || "unavailable",
      dataStatus: intelligenceStatus,
      freshnessStatus: freshness,
      validationStatus: validation,
      warnings: uniqueStrings(warnings),
      regime: regime,
      signals: signals,
      risks: risks,
      markets: markets,
      audit: buildAudit(daily, resources),
      briefAvailable: typeof resources.deterministicBrief === "string"
    };
  }

  function normalizeRegime(daily, fallback) {
    let wrapper = daily && asObject(daily.market_regime);
    let payload = wrapper && asObject(wrapper.payload);
    if (!payload) {
      payload = asObject(fallback);
      wrapper = null;
    }
    if (!payload) {
      return {
        classification: "unavailable",
        confidenceLabel: "unavailable",
        confidenceScore: null,
        status: "unavailable",
        references: emptyReferences(),
        message: "Market regime unavailable due to insufficient fresh evidence."
      };
    }
    const classification = ["risk_on", "risk_off", "mixed"].includes(payload.classification)
      ? payload.classification
      : "unavailable";
    const confidence = asObject(payload.confidence) || {};
    return {
      classification: classification,
      confidenceLabel: confidence.label || "unavailable",
      confidenceScore: numberOrNull(confidence.score),
      status: safeStatus(payload.status),
      references: wrapper ? normalizeReferences(wrapper.evidence_refs) : normalizeReferences(payload.evidence_refs),
      message: classification === "unavailable"
        ? "Market regime unavailable due to insufficient fresh evidence."
        : "Current observed regime classification from validated evidence."
    };
  }

  function normalizeSignals(daily, fallback) {
    let entries = daily && Array.isArray(daily.cross_asset_signals)
      ? daily.cross_asset_signals
      : null;
    const wrapped = Boolean(entries);
    if (!entries) {
      const source = asObject(fallback);
      entries = source && Array.isArray(source.signals) ? source.signals : [];
    }
    return entries.map(function (entry) {
      const wrapper = wrapped ? asObject(entry) : null;
      const payload = wrapper ? asObject(wrapper.payload) : asObject(entry);
      if (!payload || payload.state !== "observed") {
        return null;
      }
      return {
        id: payload.signal_id || (wrapper && wrapper.object_id) || "unknown",
        name: payload.label || payload.rule_id || "Observed relationship",
        assets: Array.isArray(payload.required_assets) ? payload.required_assets.slice() : [],
        status: payload.state,
        relationship: payload.relationship_kind || "observed",
        references: normalizeReferences(
          wrapper ? wrapper.evidence_refs : payload.evidence_refs
        )
      };
    }).filter(Boolean);
  }

  function normalizeRisks(daily, fallback) {
    const result = [];
    if (daily) {
      ["upcoming_events", "data_quality_risks", "observed_market_stress"].forEach(function (section) {
        const entries = Array.isArray(daily[section]) ? daily[section] : [];
        entries.forEach(function (wrapper) {
          const item = normalizeRisk(asObject(wrapper.payload), wrapper.evidence_refs);
          if (item) {
            result.push(item);
          }
        });
      });
      return result;
    }
    const source = asObject(fallback);
    const entries = source && Array.isArray(source.risks) ? source.risks : [];
    entries.forEach(function (payload) {
      const raw = asObject(payload);
      const item = normalizeRisk(raw, raw && raw.evidence_refs);
      if (item) {
        result.push(item);
      }
    });
    return result;
  }

  function normalizeRisk(payload, refs) {
    if (!payload) {
      return null;
    }
    return {
      id: payload.risk_id || "unknown",
      category: payload.category || "data_quality",
      title: payload.title || "Observable risk condition",
      description: payload.description || "Description unavailable.",
      severity: payload.attention_level || "unavailable",
      status: payload.status || "unavailable",
      references: normalizeReferences(refs || payload.evidence_refs)
    };
  }

  function normalizeMarkets(snapshotInput, macroInput) {
    const snapshot = asObject(snapshotInput);
    const macro = asObject(macroInput);
    const records = [];
    if (snapshot && Array.isArray(snapshot.records)) {
      snapshot.records.forEach(function (record) {
        const item = asObject(record);
        if (item) {
          records.push({
            symbol: item.symbol,
            value: numberOrNull(item.price),
            unit: "price",
            dailyChange: numberOrNull(item.daily_change),
            changeUnit: "percent",
            status: item.status || "unavailable",
            timestamp: item.timestamp || "unavailable",
            source: item.source || "unavailable"
          });
        }
      });
    }
    if (macro && Array.isArray(macro.records)) {
      macro.records.forEach(function (record) {
        const item = asObject(record);
        if (item) {
          records.push({
            symbol: item.symbol,
            value: numberOrNull(item.value),
            unit: item.value_unit || "value",
            dailyChange: numberOrNull(item.daily_change),
            changeUnit: item.change_unit || "change",
            status: item.status || "unavailable",
            timestamp: item.timestamp || "unavailable",
            source: item.source || "unavailable"
          });
        }
      });
    }
    const index = new Map(records.map(function (item) { return [item.symbol, item]; }));
    return MARKET_ORDER.map(function (symbol) { return index.get(symbol); }).filter(Boolean);
  }

  function buildAudit(daily, resources) {
    const catalog = daily && asObject(daily.provenance_catalog);
    const sources = catalog && Array.isArray(catalog.source_records)
      ? catalog.source_records.map(function (item) {
        return {
          id: item.source_id || "unknown",
          title: item.title || item.publisher || "Source",
          url: /^https?:\/\//.test(item.url || "") ? item.url : null,
          publishedAt: item.published_at || null,
          retrievedAt: item.retrieved_at || null
        };
      })
      : [];
    const observations = catalog && Array.isArray(catalog.observation_records)
      ? catalog.observation_records.map(function (item) { return item.observation_id; }).filter(Boolean)
      : [];
    const events = catalog && Array.isArray(catalog.event_records)
      ? catalog.event_records.map(function (item) { return item.event_id; }).filter(Boolean)
      : [];
    const timestamps = [];
    if (daily && asObject(daily.data_window)) {
      Object.values(daily.data_window).forEach(function (window) {
        if (asObject(window) && Array.isArray(window.values)) {
          timestamps.push.apply(timestamps, window.values);
        }
      });
    }
    Object.values(resources).forEach(function (artifact) {
      if (asObject(artifact) && artifact.generated_at) {
        timestamps.push(artifact.generated_at);
      }
    });
    return {
      sources: sources,
      timestamps: uniqueStrings(timestamps),
      observationIds: uniqueStrings(observations),
      eventIds: uniqueStrings(events)
    };
  }

  function overallFreshness(coverage, daily) {
    if (!daily) {
      return "unavailable";
    }
    if (coverage.some(function (item) {
      return item.artifact_freshness_status === "stale" || item.freshness_status === "stale";
    })) {
      return "stale";
    }
    return coverage.length === 4 ? "current" : "partial";
  }

  function overallValidation(daily, coverage) {
    if (!daily || coverage.length !== 4) {
      return "unavailable";
    }
    const objects = [daily.market_regime]
      .concat(daily.cross_asset_signals || [])
      .concat(daily.upcoming_events || [])
      .concat(daily.data_quality_risks || [])
      .concat(daily.observed_market_stress || []);
    const validCoverage = coverage.every(function (item) {
      return item.validation_status === "validated";
    });
    const validObjects = objects.every(function (item) {
      return asObject(item) && item.validation_status === "validated";
    });
    return validCoverage && validObjects ? "validated" : "unavailable";
  }

  function render(documentRef, model) {
    setStatus(documentRef, "generated-at", formatTimestamp(model.generatedAt), "");
    setStatus(documentRef, "data-status", model.dataStatus, model.dataStatus);
    setStatus(documentRef, "freshness-status", model.freshnessStatus, model.freshnessStatus);
    setStatus(documentRef, "validation-status", model.validationStatus, model.validationStatus);
    renderNotices(documentRef, model.warnings);
    renderRegime(documentRef, model.regime);
    renderSignals(documentRef, model.signals);
    renderRisks(documentRef, model.risks);
    renderMarkets(documentRef, model.markets);
    renderAudit(documentRef, model.audit, model.briefAvailable);
  }

  function setStatus(documentRef, id, value, badgeClass) {
    const target = documentRef.getElementById(id);
    target.classList.remove("loading");
    clear(target);
    if (badgeClass) {
      const badge = element(documentRef, "span", "badge " + badgeClass, value);
      target.appendChild(badge);
    } else {
      target.textContent = value;
    }
  }

  function renderNotices(documentRef, warnings) {
    const rootNode = documentRef.getElementById("load-notices");
    clear(rootNode);
    if (!warnings.length) {
      return;
    }
    const notice = element(documentRef, "div", "notice");
    const title = element(documentRef, "strong", "", "Data availability notices");
    notice.appendChild(title);
    const list = element(documentRef, "ul", "audit-list");
    warnings.forEach(function (warning) {
      list.appendChild(element(documentRef, "li", "", warning));
    });
    notice.appendChild(list);
    rootNode.appendChild(notice);
  }

  function renderRegime(documentRef, regime) {
    const rootNode = documentRef.getElementById("regime-content");
    clear(rootNode);
    const card = element(documentRef, "article", "card");
    const title = regime.classification === "unavailable"
      ? "Regime unavailable"
      : regime.classification;
    card.appendChild(element(documentRef, "h3", "", title));
    card.appendChild(element(documentRef, "p", "", regime.message));
    card.appendChild(element(
      documentRef,
      "p",
      "meta",
      "Confidence: " + regime.confidenceLabel + formatScore(regime.confidenceScore)
    ));
    card.appendChild(badge(documentRef, regime.status));
    card.appendChild(renderReferences(documentRef, regime.references));
    rootNode.appendChild(card);
  }

  function renderSignals(documentRef, signals) {
    const rootNode = documentRef.getElementById("signals-content");
    clear(rootNode);
    if (!signals.length) {
      rootNode.appendChild(element(
        documentRef,
        "p",
        "empty",
        "No current observed cross-asset relationships are available."
      ));
      return;
    }
    signals.forEach(function (signal) {
      const card = element(documentRef, "article", "card");
      card.appendChild(element(documentRef, "h3", "", signal.name));
      card.appendChild(element(
        documentRef,
        "p",
        "meta",
        "Assets: " + (signal.assets.length ? signal.assets.join(", ") : "unavailable")
      ));
      card.appendChild(element(documentRef, "p", "meta", "Relationship: " + signal.relationship));
      card.appendChild(badge(documentRef, signal.status));
      card.appendChild(renderReferences(documentRef, signal.references));
      rootNode.appendChild(card);
    });
  }

  function renderRisks(documentRef, risks) {
    const rootNode = documentRef.getElementById("risks-content");
    clear(rootNode);
    let rendered = 0;
    RISK_CATEGORIES.forEach(function (configuration) {
      const category = configuration[0];
      const title = configuration[1];
      const items = risks.filter(function (item) { return item.category === category; });
      if (!items.length) {
        return;
      }
      rendered += items.length;
      const group = element(documentRef, "div", "audit-group");
      group.appendChild(element(documentRef, "h3", "", title));
      const grid = element(documentRef, "div", "card-grid");
      items.forEach(function (risk) {
        const card = element(documentRef, "article", "card");
        card.appendChild(element(documentRef, "h3", "", risk.title));
        card.appendChild(element(documentRef, "p", "", risk.description));
        card.appendChild(element(documentRef, "p", "meta", "Severity: " + risk.severity));
        card.appendChild(badge(documentRef, risk.status));
        card.appendChild(renderReferences(documentRef, risk.references));
        grid.appendChild(card);
      });
      group.appendChild(grid);
      rootNode.appendChild(group);
    });
    if (!rendered) {
      rootNode.appendChild(element(
        documentRef,
        "p",
        "empty",
        "No validated observable risk items are available."
      ));
    }
  }

  function renderMarkets(documentRef, markets) {
    const rootNode = documentRef.getElementById("markets-content");
    clear(rootNode);
    if (!markets.length) {
      rootNode.appendChild(element(documentRef, "p", "empty", "Market snapshots unavailable."));
      return;
    }
    markets.forEach(function (market) {
      const card = element(documentRef, "article", "card");
      card.appendChild(element(documentRef, "h3", "", market.symbol));
      card.appendChild(element(
        documentRef,
        "p",
        "metric",
        market.value === null ? "unavailable" : formatNumber(market.value) + " " + market.unit
      ));
      const change = market.dailyChange === null
        ? "Daily change unavailable"
        : "Daily change: " + formatNumber(market.dailyChange) + " " + market.changeUnit;
      card.appendChild(element(documentRef, "p", "meta", change));
      card.appendChild(element(documentRef, "p", "meta", "Observed: " + market.timestamp));
      card.appendChild(element(documentRef, "p", "meta", "Source: " + market.source));
      card.appendChild(badge(documentRef, market.status));
      rootNode.appendChild(card);
    });
  }

  function renderAudit(documentRef, audit, briefAvailable) {
    const rootNode = documentRef.getElementById("audit-content");
    clear(rootNode);
    const sourceGroup = auditGroup(documentRef, "Source references");
    if (!audit.sources.length) {
      sourceGroup.appendChild(element(documentRef, "p", "empty", "Source catalog unavailable."));
    } else {
      const list = element(documentRef, "ul", "audit-list");
      audit.sources.forEach(function (source) {
        const item = element(documentRef, "li");
        item.appendChild(documentRef.createTextNode(source.id + " — "));
        if (source.url) {
          const link = element(documentRef, "a", "", source.title);
          link.href = source.url;
          link.rel = "noopener noreferrer";
          item.appendChild(link);
        } else {
          item.appendChild(documentRef.createTextNode(source.title));
        }
        item.appendChild(documentRef.createTextNode(
          " | published=" + (source.publishedAt || "unavailable")
          + " | retrieved=" + (source.retrievedAt || "unavailable")
        ));
        list.appendChild(item);
      });
      sourceGroup.appendChild(list);
    }
    rootNode.appendChild(sourceGroup);
    rootNode.appendChild(auditListGroup(documentRef, "Timestamps", audit.timestamps));
    rootNode.appendChild(auditListGroup(documentRef, "Observation IDs", audit.observationIds));
    rootNode.appendChild(auditListGroup(documentRef, "Event IDs", audit.eventIds));
    if (briefAvailable) {
      const group = auditGroup(documentRef, "Deterministic report artifact");
      const link = element(documentRef, "a", "", "Open daily_market_brief.md");
      link.href = "data/daily_market_brief.md";
      group.appendChild(link);
      rootNode.appendChild(group);
    }
  }

  function renderReferences(documentRef, references) {
    const details = element(documentRef, "details", "");
    const list = element(documentRef, "ul", "refs audit-body");
    let count = 0;
    REFERENCE_KEYS.forEach(function (key) {
      const values = references[key] || [];
      if (!values.length) {
        return;
      }
      count += values.length;
      list.appendChild(element(documentRef, "li", "", key + ": " + values.join(", ")));
    });
    const summary = element(
      documentRef,
      "summary",
      "",
      count ? "Evidence references (" + count + ")" : "References unavailable"
    );
    details.appendChild(summary);
    if (!count) {
      return details;
    }
    details.appendChild(list);
    return details;
  }

  function auditGroup(documentRef, title) {
    const group = element(documentRef, "div", "audit-group");
    group.appendChild(element(documentRef, "h3", "", title));
    return group;
  }

  function auditListGroup(documentRef, title, values) {
    const group = auditGroup(documentRef, title);
    if (!values.length) {
      group.appendChild(element(documentRef, "p", "empty", "None in validated input."));
      return group;
    }
    const list = element(documentRef, "ul", "audit-list");
    values.forEach(function (value) {
      list.appendChild(element(documentRef, "li", "", value));
    });
    group.appendChild(list);
    return group;
  }

  function badge(documentRef, value) {
    return element(documentRef, "span", "badge " + cssToken(value), value || "unavailable");
  }

  function element(documentRef, tag, className, text) {
    const node = documentRef.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text !== undefined) {
      node.textContent = String(text);
    }
    return node;
  }

  function clear(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  function normalizeReferences(value) {
    const refs = asObject(value) || {};
    const result = emptyReferences();
    REFERENCE_KEYS.forEach(function (key) {
      result[key] = uniqueStrings(Array.isArray(refs[key]) ? refs[key] : []);
    });
    return result;
  }

  function emptyReferences() {
    return {
      evidence_bundle_ids: [],
      source_ids: [],
      observation_ids: [],
      event_ids: [],
      evidence_ids: [],
      signal_ids: [],
      regime_dimension_ids: [],
      risk_ids: [],
      coverage_inputs: []
    };
  }

  function uniqueStrings(values) {
    return Array.from(new Set(values.filter(function (value) {
      return typeof value === "string" && value.length > 0;
    }))).sort();
  }

  function latestTimestamp(values) {
    return values.map(asObject).filter(Boolean).map(function (value) {
      return value.generated_at;
    }).filter(Boolean).sort().pop() || null;
  }

  function safeStatus(value) {
    return typeof value === "string" && value ? value : "unavailable";
  }

  function numberOrNull(value) {
    return typeof value === "number" && Number.isFinite(value) ? value : null;
  }

  function formatNumber(value) {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 6 }).format(value);
  }

  function formatScore(value) {
    return value === null ? "" : " (" + formatNumber(value) + ")";
  }

  function formatTimestamp(value) {
    if (typeof value !== "string" || !value.includes("T")) {
      return value || "unavailable";
    }
    return value.replace("T", " ").replace(/(\.\d+)?Z$/, " UTC");
  }

  function cssToken(value) {
    return String(value || "unavailable").toLowerCase().replace(/[^a-z0-9_-]/g, "-");
  }

  function asObject(value) {
    return value && typeof value === "object" && !Array.isArray(value) ? value : null;
  }

  async function initialize(documentRef, fetchImpl) {
    const loaded = await loadResources(fetchImpl);
    const model = buildViewModel(loaded.resources, loaded.errors);
    render(documentRef, model);
    return model;
  }

  return {
    ENDPOINTS: ENDPOINTS,
    MARKET_ORDER: MARKET_ORDER,
    buildViewModel: buildViewModel,
    initialize: initialize,
    loadResources: loadResources,
    normalizeMarkets: normalizeMarkets,
    render: render
  };
});
