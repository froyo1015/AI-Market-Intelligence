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
    previousMarket: ["previous-market-snapshot.json", "json"],
    derivatives: ["derivatives-shadow.json", "json"],
    topIntelligence: ["data/top_intelligence.json", "json"],
    dailyIntelligence: ["data/daily_intelligence.json", "json"],
    marketSignals: ["data/market_signals.json", "json"],
    marketRegime: ["data/market_regime.json", "json"],
    riskMonitor: ["data/risk_monitor.json", "json"],
    marketSnapshot: ["data/market_snapshot.json", "json"],
    macroSnapshot: ["data/macro_snapshot.json", "json"],
    aiBrief: ["data/ai_market_brief.md", "text"],
    runManifest: ["data/run_manifest.json", "json"],
    deterministicBrief: ["data/daily_market_brief.md", "text"]
  };
  const MAX_BRIEF_CHARACTERS = 100000;
  const GENERATION_FALLBACK_REASONS = [
    "no_provider_configured", "provider_timeout", "provider_rate_limit",
    "invalid_llm_output", "malformed_provider_response", "provider_error",
    "pipeline_failure", "missing_generation_metadata"
  ];
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
    const topIntelligence = normalizeTopIntelligence(resources.topIntelligence);
    const aiBrief = normalizeAIBrief(
      resources.aiBrief,
      resources.deterministicBrief,
      resources.runManifest
    );
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
      reportAvailable: Boolean(daily),
      previousAvailable: Boolean(resources.previousMarket),
      freshnessStatus: freshness,
      validationStatus: validation,
      warnings: uniqueStrings(warnings),
      aiBrief: aiBrief,
      derivatives: resources.derivatives,
      changes: observedChanges(resources.marketSnapshot, resources.previousMarket),
      topIntelligence: topIntelligence,
      regime: regime,
      signals: signals,
      risks: risks,
      markets: markets,
      audit: buildAudit(daily, resources),
      deterministicBriefAvailable: typeof resources.deterministicBrief === "string"
    };
  }

  function normalizeAIBrief(aiBriefInput, deterministicInput, manifestInput) {
    const available = typeof aiBriefInput === "string"
      && aiBriefInput.trim().length > 0
      && aiBriefInput.length <= MAX_BRIEF_CHARACTERS;
    if (!available) {
      return {
        available: false,
        mode: "unavailable",
        modeLabel: "Unavailable",
        generatedAt: "unknown",
        freshnessStatus: "unknown",
        validationStatus: "unknown",
        provider: null,
        fallbackReason: null,
        metadataSource: "none",
        fallbackNote: "",
        blocks: []
      };
    }

    const manifest = asObject(manifestInput);
    const modules = manifest && Array.isArray(manifest.modules) ? manifest.modules : [];
    const moduleRecord = modules.map(asObject).find(function (item) {
      return item && item.name === "grounded_ai_brief";
    }) || null;
    const artifacts = moduleRecord && Array.isArray(moduleRecord.artifacts)
      ? moduleRecord.artifacts.map(asObject).filter(Boolean)
      : [];
    const artifactRecord = artifacts.find(function (item) {
      return item.path === "ai_market_brief.md";
    }) || null;
    const explicit = normalizeGenerationMetadata(
      moduleRecord && moduleRecord.generation_metadata
    );
    if (explicit) {
      if (explicit.generationMode === "unavailable") {
        return {
          available: false,
          mode: "unavailable",
          modeLabel: "Unavailable",
          generatedAt: explicit.generatedAt,
          freshnessStatus: explicit.freshnessStatus,
          validationStatus: explicit.validationStatus,
          provider: explicit.provider,
          fallbackReason: explicit.fallbackReason,
          metadataSource: "explicit",
          fallbackNote: "",
          blocks: []
        };
      }
      const explicitFallback = explicit.generationMode === "deterministic_fallback";
      return {
        available: true,
        mode: explicit.generationMode,
        modeLabel: explicitFallback ? "Deterministic fallback" : "Grounded AI",
        generatedAt: explicit.generatedAt,
        freshnessStatus: explicit.freshnessStatus,
        validationStatus: explicit.validationStatus,
        provider: explicit.provider,
        fallbackReason: explicit.fallbackReason,
        metadataSource: "explicit",
        fallbackNote: explicitFallback
          ? "AI generation was unavailable; the validated deterministic brief is shown instead."
          : "",
        blocks: parseSafeMarkdown(aiBriefInput)
      };
    }

    const isFallback = typeof deterministicInput === "string"
      && aiBriefInput === deterministicInput;
    const validated = Boolean(
      moduleRecord
      && ["success", "partial"].includes(moduleRecord.status)
      && artifactRecord
      && artifactRecord.approved_for_publication === true
    );
    const freshness = moduleRecord
      && ["current", "stale", "unavailable", "unknown"].includes(moduleRecord.freshness_status)
      ? moduleRecord.freshness_status
      : "unknown";
    return {
      available: true,
      mode: isFallback ? "deterministic_fallback" : "grounded_ai",
      modeLabel: isFallback ? "Deterministic fallback" : "Grounded AI",
      generatedAt: (artifactRecord && artifactRecord.generated_at)
        || (moduleRecord && moduleRecord.generated_at)
        || "unknown",
      freshnessStatus: freshness,
      validationStatus: validated ? "validated" : "unknown",
      provider: null,
      fallbackReason: isFallback ? "missing_generation_metadata" : null,
      metadataSource: "legacy_file_comparison",
      fallbackNote: isFallback
        ? "AI generation was unavailable; the validated deterministic brief is shown instead."
        : "",
      blocks: parseSafeMarkdown(aiBriefInput)
    };
  }

  function normalizeGenerationMetadata(input) {
    const metadata = asObject(input);
    if (!metadata) {
      return null;
    }
    const mode = metadata.generation_mode;
    const status = metadata.generation_status;
    const freshness = metadata.freshness_status;
    const validation = metadata.validation_status;
    const provider = metadata.provider;
    const reason = metadata.fallback_reason;
    if (!["grounded_ai", "deterministic_fallback", "unavailable"].includes(mode)) {
      return null;
    }
    if (!["success", "fallback", "failed"].includes(status)) {
      return null;
    }
    if (!["current", "stale", "unavailable", "unknown"].includes(freshness)) {
      return null;
    }
    if (!["validated", "unavailable", "unknown"].includes(validation)) {
      return null;
    }
    if (typeof metadata.generated_at !== "string" || !metadata.generated_at) {
      return null;
    }
    if (provider !== null && (typeof provider !== "string" || !provider)) {
      return null;
    }
    if (reason !== null && !GENERATION_FALLBACK_REASONS.includes(reason)) {
      return null;
    }
    if (mode === "grounded_ai"
      && (status !== "success" || validation !== "validated" || !provider || reason !== null)) {
      return null;
    }
    if (mode === "deterministic_fallback"
      && (status !== "fallback" || validation !== "validated" || !reason)) {
      return null;
    }
    if (mode === "unavailable"
      && (status !== "failed" || validation === "validated" || !reason)) {
      return null;
    }
    return {
      generationMode: mode,
      generationStatus: status,
      generatedAt: metadata.generated_at,
      freshnessStatus: freshness,
      validationStatus: validation,
      provider: provider,
      fallbackReason: reason
    };
  }

  function parseSafeMarkdown(markdown) {
    if (typeof markdown !== "string" || markdown.length > MAX_BRIEF_CHARACTERS) {
      return [];
    }
    const blocks = [];
    const paragraph = [];
    let listItems = [];

    function flushParagraph() {
      if (paragraph.length) {
        blocks.push({ kind: "paragraph", text: paragraph.join(" ") });
        paragraph.length = 0;
      }
    }

    function flushList() {
      if (listItems.length) {
        blocks.push({ kind: "list", items: listItems });
        listItems = [];
      }
    }

    markdown.replace(/\r\n?/g, "\n").split("\n").forEach(function (line) {
      const heading = /^(#{1,6})\s+(.+)$/.exec(line);
      const listItem = /^\s*[-*+]\s+(.+)$/.exec(line);
      const isReference = /\[refs:\s*[^\]]+\]/i.test(line)
        || /^\s*(Source\s*\/\s*Evidence|Evidence|References?)\s*:/i.test(line);

      if (!line.trim()) {
        flushParagraph();
        flushList();
      } else if (heading) {
        flushParagraph();
        flushList();
        blocks.push({
          kind: "heading",
          level: Math.min(6, heading[1].length + 2),
          text: heading[2].trim()
        });
      } else if (listItem) {
        flushParagraph();
        listItems.push(listItem[1].trim());
      } else if (isReference) {
        flushParagraph();
        flushList();
        blocks.push({ kind: "reference", text: line.trim() });
      } else {
        flushList();
        paragraph.push(line.trim());
      }
    });
    flushParagraph();
    flushList();
    return blocks;
  }

  function normalizeTopIntelligence(input) {
    const artifact = asObject(input);
    if (!artifact || artifact.status === "unavailable" || artifact.freshness_status !== "current") {
      return {
        status: "unavailable",
        items: [],
        message: "No current validated Top 3 intelligence is available."
      };
    }
    const items = Array.isArray(artifact.items) ? artifact.items.map(function (raw) {
      const item = asObject(raw);
      if (!item || item.freshness_status !== "current" || item.validation_status !== "validated") {
        return null;
      }
      return {
        rank: item.rank,
        id: item.item_id,
        type: item.type,
        storyKey: item.story_key,
        headline: item.headline,
        why: item.why,
        monitor: item.monitor,
        score: numberOrNull(item.total_score),
        assets: Array.isArray(item.related_assets) ? item.related_assets.slice() : [],
        references: normalizeReferences(item.evidence_refs),
        sourceRefs: uniqueStrings(Array.isArray(item.source_refs) ? item.source_refs : [])
      };
    }).filter(Boolean) : [];
    return {
      status: items.length ? safeStatus(artifact.status) : "unavailable",
      items: items,
      message: items.length ? "" : "No current validated Top 3 intelligence is available."
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
    if (["current", "stale", "unavailable", "unknown"].indexOf(daily.freshness_status) !== -1) {
      return daily.freshness_status;
    }
    if (coverage.some(function (item) {
      return item.artifact_freshness_status === "stale" || item.freshness_status === "stale";
    })) {
      return "stale";
    }
    return coverage.length === 4 ? "current" : "unknown";
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
    const onboarding = documentRef.getElementById("onboarding-state");
    if (onboarding) {
      onboarding.textContent = "";
      onboardingHints(model).forEach(function (hint) { onboarding.appendChild(element(documentRef, "p", "meta", hint)); });
    }
    renderReport(documentRef, model);
    const header = researchHeader(model, Date.now());
    const statusNode = documentRef.getElementById("research-status");
    const updatedNode = documentRef.getElementById("research-updated");
    if (statusNode) statusNode.textContent = header.status;
    if (updatedNode) updatedNode.textContent = header.updated;
    renderDerivatives(documentRef, model.derivatives);
    setStatus(documentRef, "generated-at", formatTimestamp(model.generatedAt), "");
    setStatus(documentRef, "data-status", model.dataStatus, model.dataStatus);
    setStatus(documentRef, "freshness-status", model.freshnessStatus, model.freshnessStatus);
    setStatus(documentRef, "validation-status", model.validationStatus, model.validationStatus);
    renderNotices(documentRef, model.warnings);
    renderAIBrief(documentRef, model.aiBrief);
    renderTopIntelligence(documentRef, model.topIntelligence);
    renderRegime(documentRef, model.regime);
    renderSignals(documentRef, model.signals);
    renderRisks(documentRef, model.risks);
    renderMarkets(documentRef, model.markets);
    renderAudit(
      documentRef,
      model.audit,
      model.aiBrief.available,
      model.deterministicBriefAvailable
    );
  }

  function renderAIBrief(documentRef, brief) {
    setStatus(documentRef, "ai-brief-mode", brief.modeLabel, brief.mode);
    setStatus(
      documentRef,
      "ai-brief-generated-at",
      formatTimestamp(brief.generatedAt),
      ""
    );
    setStatus(
      documentRef,
      "ai-brief-freshness",
      brief.freshnessStatus,
      brief.freshnessStatus
    );
    setStatus(
      documentRef,
      "ai-brief-validation",
      brief.validationStatus,
      brief.validationStatus
    );
    const note = documentRef.getElementById("ai-brief-note");
    note.hidden = !brief.fallbackNote;
    note.textContent = brief.fallbackNote;
    const rootNode = documentRef.getElementById("ai-brief-content");
    clear(rootNode);
    if (!brief.available) {
      rootNode.appendChild(element(
        documentRef,
        "p",
        "empty",
        "AI Market Brief unavailable."
      ));
      return;
    }
    renderSafeMarkdown(documentRef, rootNode, brief.blocks);
  }

  function renderSafeMarkdown(documentRef, rootNode, blocks) {
    blocks.forEach(function (block) {
      if (block.kind === "heading") {
        rootNode.appendChild(element(documentRef, "h" + block.level, "", block.text));
      } else if (block.kind === "list") {
        const list = element(documentRef, "ul");
        block.items.forEach(function (item) {
          list.appendChild(element(documentRef, "li", "", item));
        });
        rootNode.appendChild(list);
      } else if (block.kind === "reference") {
        rootNode.appendChild(element(documentRef, "p", "brief-reference", block.text));
      } else if (block.kind === "paragraph") {
        rootNode.appendChild(element(documentRef, "p", "", block.text));
      }
    });
  }

  function renderTopIntelligence(documentRef, topIntelligence) {
    const rootNode = documentRef.getElementById("top-intelligence-content");
    clear(rootNode);
    if (!topIntelligence.items.length) {
      rootNode.appendChild(element(documentRef, "p", "empty", topIntelligence.message));
      return;
    }
    topIntelligence.items.forEach(function (item) {
      const card = element(documentRef, "article", "card");
      card.appendChild(element(documentRef, "p", "brand", "Priority " + item.rank));
      card.appendChild(element(documentRef, "h3", "", item.headline));
      card.appendChild(element(documentRef, "h4", "explanation-label", "Why this matters"));
      card.appendChild(element(documentRef, "p", "", item.why));
      card.appendChild(element(documentRef, "h4", "explanation-label", "Monitor next"));
      card.appendChild(element(documentRef, "p", "meta", "Monitor next: " + item.monitor));
      card.appendChild(element(documentRef, "p", "meta", "Type: " + item.type + " · Score: " + formatNumber(item.score)));
      card.appendChild(element(documentRef, "p", "meta", "Story: " + item.storyKey));
      if (item.assets.length) {
        card.appendChild(element(documentRef, "p", "meta", "Assets: " + item.assets.join(", ")));
      }
      card.appendChild(renderReferences(documentRef, item.references));
      rootNode.appendChild(card);
    });
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
      card.appendChild(element(documentRef, "p", "brand", ["SPY", "QQQ", "NVDA", "AAPL", "TSLA"].includes(market.symbol) ? "Equity" : ["BTC-USD", "ETH-USD"].includes(market.symbol) ? "Crypto" : "Macro"));
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

  function renderAudit(documentRef, audit, aiBriefAvailable, deterministicBriefAvailable) {
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
    if (aiBriefAvailable) {
      const group = auditGroup(documentRef, "Grounded AI report artifact");
      const link = element(documentRef, "a", "", "Open ai_market_brief.md");
      link.href = "data/ai_market_brief.md";
      group.appendChild(link);
      rootNode.appendChild(group);
    }
    if (deterministicBriefAvailable) {
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
      const labels = {source_ids: "Sources", observation_ids: "Observations", event_ids: "Events",
        evidence_ids: "Evidence", evidence_bundle_ids: "Evidence bundles", signal_ids: "Signals",
        risk_ids: "Risks", regime_dimension_ids: "Regime dimensions", coverage_inputs: "Coverage inputs"};
      const entry = element(documentRef, "li", "trace-entry");
      entry.appendChild(element(documentRef, "strong", "", (labels[key] || key) + " · " + values.length));
      values.forEach(function (value) { entry.appendChild(element(documentRef, "code", "", value)); });
      list.appendChild(entry);
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

  function derivativesLines(payload, now) {
    if (!payload || payload.schema_contract !== "derivatives_public_v1" ||
        !Array.isArray(payload.measurements) || payload.measurements.length !== 4 ||
        !payload.readiness || payload.readiness.production_enabled !== false) {
      return ["Derivatives unavailable."];
    }
    const lines = ["Validation: " + (payload.validation_status === "validated" ? "validated" : "unavailable"),
      "Snapshot: " + formatTimestamp(payload.generated_at)];
    ["BTC", "ETH"].forEach(function (asset) {
      lines.push(asset + " Perpetual");
      ["funding_rate", "open_interest"].forEach(function (metric) {
        const r = payload.measurements.find(function (x) { return x.asset === asset && x.metric === metric; });
        const title = metric === "funding_rate" ? "Funding rate" : "Open interest";
        if (!r || r.value === null || !/^-?\d+(\.\d+)?$/.test(String(r.value))) {
          lines.push(title + ": unavailable"); return;
        }
        const age = now - Date.parse(r.source_timestamp);
        const freshness = r.freshness_status === "current" && age >= 0 && age <= r.ttl_seconds * 1000 ? "current" : "stale";
        lines.push(title + ": " + r.value + (metric === "funding_rate" ? " (fraction)" : " " + asset));
        lines.push("Observation timestamp: " + formatTimestamp(r.source_timestamp));
        lines.push("Freshness: " + freshness);
        lines.push("Evidence quality: " + (typeof r.evidence_quality === "number" ? String(r.evidence_quality) : "unknown") + " (at snapshot)");
        lines.push("Provenance: " + (r.provenance_status === "complete" ? "complete" : "unavailable"));
      });
    });
    const r = payload.readiness;
    lines.push("Readiness history: " + r.current_history_days + " / " + r.required_history_days + " days (at snapshot)");
    lines.push("production_enabled: false");
    if (r.tracking) {
      const t = r.tracking;
      lines.push("Missing days: " + (Array.isArray(t.missing_days) ? t.missing_days.join(", ") || "none" : "unknown"));
      lines.push("Freshness pass rate: " + (typeof t.freshness_pass_rate === "number" ? (t.freshness_pass_rate * 100).toFixed(1) + "%" : "unknown"));
      lines.push("Provenance completeness: " + (typeof t.provenance_completeness === "number" ? (t.provenance_completeness * 100).toFixed(1) + "%" : "unknown"));
      lines.push("Validation failures: " + (Number.isInteger(t.validation_failures) ? t.validation_failures : "unknown"));
    }
    const allowed = ["history", "availability", "freshness", "provenance", "coverage", "safety", "input_integrity", "invalid_archive", "unavailable"];
    const reasons = Array.isArray(r.blocking_reasons) ? r.blocking_reasons.filter(function (x) { return allowed.includes(x); }) : ["unavailable"];
    lines.push("Blocking reasons: " + (reasons.join(", ") || "none at snapshot"));
    if (now - Date.parse(payload.generated_at) > 86400000) lines.push("Readiness snapshot stale; awaiting refresh.");
    return lines;
  }

  function renderDerivatives(documentRef, payload) {
    const container = documentRef.getElementById("derivatives-content");
    if (!container) return;
    container.textContent = "";
    let group = element(documentRef, "div", "card");
    container.appendChild(group);
    derivativesLines(payload, Date.now()).forEach(function (line) {
      if (line === "BTC Perpetual" || line === "ETH Perpetual" || line.startsWith("Readiness history:")) {
        group = element(documentRef, "article", "card");
        container.appendChild(group);
      }
      const freshnessBadge = line === "Freshness: current" ? "badge current" : line === "Freshness: stale" ? "badge stale" : "muted";
      group.appendChild(element(documentRef, line.endsWith("Perpetual") ? "h3" : "p", freshnessBadge, line));
    });
  }

  function researchHeader(model, now) {
    const statuses = ["available", "complete", "partial", "unavailable", "failed"];
    const state = statuses.includes(model.dataStatus) ? model.dataStatus : "unavailable";
    const freshness = ["current", "stale", "unknown", "unavailable"].includes(model.freshnessStatus) ? model.freshnessStatus : "unknown";
    const generated = Date.parse(model.generatedAt);
    const age = now - generated;
    let updated = "Last update unavailable";
    if (Number.isFinite(generated) && age >= 0) {
      updated = "Last report update: " + formatTimestamp(model.generatedAt) + " · " + Math.floor(age / 3600000) + "h ago (artifact age)";
      if (age > 86400000) updated += " · Older snapshot — awaiting refresh";
    } else if (Number.isFinite(generated)) {
      updated = "Last update timestamp is in the future; check the source clock";
    }
    return {status: "Daily research status: " + state + " · Recorded source freshness: " + freshness, updated: updated};
  }

  function onboardingHints(model) {
    const hints = [];
    if (!model.reportAvailable) hints.push("Daily report unavailable. This may be a first run or a missing artifact; consult available source sections and return after the next published run.");
    if (model.dataStatus === "partial") hints.push("Partial pipeline: some inputs are missing or unusable. Read the data quality warnings before using this report.");
    if (model.freshnessStatus === "stale") hints.push("Stale data: use the displayed observation timestamps as historical context, not a live market view.");
    if (!model.previousAvailable) hints.push("Previous run unavailable: What Changed cannot provide a comparison yet.");
    if (!model.derivatives || model.derivatives.validation_status !== "validated") hints.push("Optional derivatives shadow data unavailable. This does not enable or disable other research sections.");
    return hints;
  }

  function observedChanges(current, previous) {
    if (!current || !Array.isArray(current.records)) return ["Current market snapshot unavailable."];
    if (!previous || !Array.isArray(previous.records)) return ["Previous available run unavailable; comparison omitted."];
    const a = Date.parse(previous.generated_at), b = Date.parse(current.generated_at);
    if (!Number.isFinite(a) || !Number.isFinite(b) || a >= b) return ["Previous run timestamp is not earlier; comparison omitted."];
    const lines = ["Snapshot comparison: " + formatTimestamp(previous.generated_at) + " → " + formatTimestamp(current.generated_at)];
    current.records.forEach(function (r) {
      const matches = previous.records.filter(function (p) { return p.symbol === r.symbol; });
      if (matches.length !== 1) return;
      const p = matches[0];
      if (![p,r].every(function (x) { return ["success","stale"].includes(x.status) && typeof x.price === "number" && Number.isFinite(x.price) && typeof x.source === "string"; }) || p.source !== r.source) return;
      const oldTime = Date.parse(p.timestamp), newTime = Date.parse(r.timestamp);
      if (!Number.isFinite(oldTime) || !Number.isFinite(newTime) || newTime < oldTime || newTime > b || oldTime > a) return;
      if (p.price !== r.price || p.status !== r.status) {
        lines.push(r.symbol + ": " + p.price + " → " + r.price + "; recorded status " + p.status + " → " + r.status + "; source " + r.source + "; observations " + p.timestamp + " → " + r.timestamp);
      }
    });
    if (lines.length === 1) lines.push("No comparable changed observations in the supplied snapshots.");
    return lines;
  }

  function renderReport(doc, model) {
    function lines(id, values) {
      const box = doc.getElementById(id); if (!box) return;
      box.textContent = "";
      values.forEach(function (v) { box.appendChild(element(doc,"p","meta",v)); });
    }
    lines("executive-content", [researchHeader(model, Date.now()).status].concat(
      model.topIntelligence.items.length ? model.topIntelligence.items.map(function (s) { return s.rank + ". " + s.headline; }) : ["No current validated stories available."]));
    lines("changes-content", model.changes || ["Previous available run unavailable."]);
    lines("report-quality-content", model.warnings.length ? model.warnings : ["No additional data quality warnings in supplied artifacts."]);
  }

  return {
    ENDPOINTS: ENDPOINTS,
    researchHeader: researchHeader,
    onboardingHints: onboardingHints,
    observedChanges: observedChanges,
    renderReferences: renderReferences,
    derivativesLines: derivativesLines,
    renderDerivatives: renderDerivatives,
    MARKET_ORDER: MARKET_ORDER,
    buildViewModel: buildViewModel,
    initialize: initialize,
    loadResources: loadResources,
    normalizeMarkets: normalizeMarkets,
    normalizeAIBrief: normalizeAIBrief,
    normalizeGenerationMetadata: normalizeGenerationMetadata,
    normalizeTopIntelligence: normalizeTopIntelligence,
    parseSafeMarkdown: parseSafeMarkdown,
    render: render
  };
});
