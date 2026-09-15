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

  // Presentation translations only. Contract values and source prose stay intact.
  const ZH = {
    "No current validated Top 3 intelligence is available.": "目前暫無符合新鮮度與驗證要求的市場重點。",
    "Market regime unavailable due to insufficient fresh evidence.": "目前有效證據不足，暫時無法判定市場環境。",
    "Observable risk condition": "可觀察的風險狀況",
    "Current observed regime classification from validated evidence.": "依據已驗證證據，描述目前的市場環境。",
    current: "目前有效", stale: "資料已過期", unavailable: "暫無資料", unknown: "時間不明",
    partial: "部分資料可用", complete: "資料完整", available: "資料可用", success: "成功",
    failed: "未能取得資料", validated: "已驗證", invalid: "未通過驗證",
    risk_on: "風險偏好較強（risk_on）", risk_off: "避險傾向較強（risk_off）", mixed: "走勢分歧（mixed）",
    "Unavailable": "暫無資料", "Deterministic fallback": "規則式備援模式", "Grounded AI": "依據證據撰寫的 AI 模式",
    "AI generation was unavailable; the validated deterministic brief is shown instead.": "AI 暫時無法產生簡報，目前顯示已驗證的規則式備援簡報。",
    "AI Market Brief unavailable.": "AI 市場簡報暫無資料。",
    "Why this matters": "為何重要", "Monitor next": "接下來留意甚麼",
    "Data availability notices": "資料取得狀況", "Regime unavailable": "市場環境暫無資料",
    "No current observed cross-asset relationships are available.": "目前沒有可用的跨資產觀察。",
    "No validated observable risk items are available.": "暫無通過驗證的風險觀察。",
    "Market snapshots unavailable.": "行情暫無資料。", "Daily change unavailable": "暫無單日變化資料",
    "Equity": "美股", "Crypto": "加密資產", "Macro": "宏觀",
    "Source references": "來源參考", "Source catalog unavailable.": "暫無來源目錄。",
    "Timestamps": "時間紀錄", "Observation IDs": "觀察 ID", "Event IDs": "事件 ID",
    "Grounded AI report artifact": "AI 簡報原始檔", "Deterministic report artifact": "規則式簡報原始檔",
    "Open ai_market_brief.md": "開啟 ai_market_brief.md", "Open daily_market_brief.md": "開啟 daily_market_brief.md",
    "References unavailable": "暫無引用資料", "None in validated input.": "已驗證資料中沒有此項記錄。",
    "Upcoming Events": "即將發生的事件", "Data Quality Risks": "資料品質風險", "Observed Market Stress": "已觀察到的市場壓力",
    "Derivatives unavailable.": "衍生品暫無資料。", "BTC Perpetual": "BTC 永續合約", "ETH Perpetual": "ETH 永續合約",
    "production_enabled: false": "尚未用於正式分析", "Readiness snapshot stale; awaiting refresh.": "準備度記錄已過期，等待更新。",
    "Daily report unavailable. This may be a first run or a missing artifact; consult available source sections and return after the next published run.": "暫無每日報告，可能是首次執行或檔案缺漏。可先查看其他有資料的章節，稍後再試。",
    "Partial pipeline: some inputs are missing or unusable. Read the data quality warnings before using this report.": "部分資料缺漏或無法使用，閱讀報告前請先留意資料品質警告。",
    "Stale data: use the displayed observation timestamps as historical context, not a live market view.": "資料已過期，請按顯示的觀察時間作歷史參考，不要當成即時行情。",
    "Previous run unavailable: What Changed cannot provide a comparison yet.": "暫無上次報告，因此未能比較市場變化。",
    "Optional derivatives shadow data unavailable. This does not enable or disable other research sections.": "衍生品測試資料暫缺，不影響其他研究章節的啟用狀態。",
    "Current market snapshot unavailable.": "目前行情暫無資料。",
    "Previous available run unavailable; comparison omitted.": "暫無上次行情，未進行比較。",
    "Previous available run unavailable.": "暫無上次報告。",
    "Previous run timestamp is not earlier; comparison omitted.": "前次報告時間不早於本次，因此不作比較。",
    "No comparable changed observations in the supplied snapshots.": "兩次記錄之間沒有可比較的觀察變化。",
    "No current validated stories available.": "目前暫無已驗證的市場重點。",
    "No additional data quality warnings in supplied artifacts.": "提供的資料中沒有其他品質警告。",
    "Last update unavailable": "上次更新：暫無資料",
    "Last update timestamp is in the future; check the source clock": "更新時間晚於目前時間，來源時鐘有待確認。"
  };
  const ZH_PREFIXES = {
    "Current data status: ": "目前資料狀態：", "AI generation mode: ": "AI 簡報模式：",
    "Derivatives shadow: ": "衍生品測試狀態：", "Last successful report update: ": "上次成功產生報告：",
    "Recorded freshness: ": "記錄的資料新鮮度：", "Daily research status: ": "今日報告狀態：",
    "Last report update: ": "上次報告更新：", "Priority ": "重點 ",
    "Monitor next: ": "後續觀察：", "Type: ": "類型：", "Story: ": "主題代碼：",
    "Assets: ": "相關資產：", "Confidence: ": "判定可靠程度：", "Relationship: ": "觀察關係：",
    "Severity: ": "程度：", "Daily change: ": "單日變化：", "Observed: ": "觀察時間：", "Source: ": "來源：",
    "Validation: ": "驗證狀態：", "Snapshot: ": "記錄時間：", "Funding rate: ": "資金費率（Funding Rate）：",
    "Open interest: ": "未平倉量（OI）：", "Observation timestamp: ": "觀察時間：", "Freshness: ": "資料新鮮度：",
    "Evidence quality: ": "證據品質：", "Provenance: ": "來源追溯：", "Readiness history: ": "準備度觀察天數：",
    "Missing days: ": "缺漏日期：", "Freshness pass rate: ": "新鮮度合格比例：", "Provenance completeness: ": "來源完整比例：",
    "Validation failures: ": "驗證未通過次數：", "Blocking reasons: ": "尚未通過的項目：", "Snapshot comparison: ": "行情記錄比較：",
    "Evidence references (": "證據引用 ("
  };
  function uiText(value) {
    const text = String(value);
    if (Object.prototype.hasOwnProperty.call(ZH, text)) return ZH[text];
    const prefix = Object.keys(ZH_PREFIXES).find(x => text.startsWith(x));
    if (!prefix) return text; // Never guess translations of source facts or IDs.
    let tail = text.slice(prefix.length);
    if (Object.prototype.hasOwnProperty.call(ZH, tail)) tail = ZH[tail];
    tail = tail.replace(" · Not used for AI decisions", " · 尚未用於 AI 決策")
      .replace(" (validated report timestamp; not proof of full pipeline success)", "（已驗證報告的時間，不代表所有資料均取得成功）")
      .replace(" · Recorded source freshness: ", " · 來源資料新鮮度：")
      .replace(" · Older snapshot — awaiting refresh", " · 舊記錄，等待更新")
      .replace("h ago (artifact age)", " 小時前（報告檔案時間）")
      .replace(" (at snapshot)", "（記錄當時）").replace(" days", " 天")
      .replace(" (fraction)", "（小數比例）");
    // Only translate standalone status tokens in known UI-generated lines.
    if (!["Source: ", "Story: ", "Assets: ", "Observed: ", "Snapshot comparison: ", "Observation timestamp: ", "Snapshot: "].includes(prefix)) {
      tail = tail.replace(/\b(current|stale|unavailable|unknown|partial|complete|available|success|failed|validated|invalid)\b/g, x => ZH[x]);
    }
    return ZH_PREFIXES[prefix] + tail;
  }

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
    minimumUseful: ["data/minimum_useful_status.json", "json"],
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
    const minimumUseful = normalizeMinimumUsefulStatus(resources.minimumUseful);
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
      deterministicBriefAvailable: typeof resources.deterministicBrief === "string",
      minimumUseful: minimumUseful
    };
  }

  function normalizeMinimumUsefulStatus(input) {
    const item = asObject(input);
    const system = item && asObject(item.system_health);
    const product = item && asObject(item.product_usefulness);
    const limitations = item && Array.isArray(item.explicit_limitations)
      ? item.explicit_limitations.filter(function (value) { return typeof value === "string"; }) : [];
    if (!item || item.artifact_type !== "minimum_useful_status" || item.schema_version !== "1.0" ||
        !system || !product || !["healthy", "degraded", "unusable"].includes(system.state) ||
        !["useful", "degraded", "unusable"].includes(product.state) ||
        !["healthy", "degraded", "unusable"].includes(item.overall_status) ||
        typeof item.minimum_useful !== "boolean") {
      return {available: false, system: "unavailable", product: "unavailable",
        overall: "unavailable", minimumUseful: false, limitations: ["gate_artifact_unavailable"]};
    }
    return {available: true, system: system.state, product: product.state,
      overall: item.overall_status, minimumUseful: item.minimum_useful,
      limitations: uniqueStrings(limitations)};
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

  function scopedFreshness(artifact, id, now) {
    const extension = asObject(artifact && artifact.freshness_items);
    if (!extension) return null; // Conservative compatibility for old artifacts.
    const record = extension.version === "reference_scoped_v1" && asObject(extension.items) && asObject(extension.items[id]);
    if (!record || !["current", "stale"].includes(record.freshness_status)) return "unavailable";
    const eventReceiptBasis = record.freshness_basis === "retrieved_at" && Array.isArray(record.event_ids) && record.event_ids.length > 0 && Array.isArray(record.observation_ids) && record.observation_ids.length === 0;
    const source = Date.parse(eventReceiptBasis ? record.retrieved_at : record.source_timestamp);
    const generated = Date.parse(record.generated_at);
    const age = record.age_seconds;
    const limit = record.stale_after_seconds;
    if (!Number.isFinite(source) || !Number.isFinite(generated) || !Number.isFinite(now) ||
        record.generated_at !== artifact.generated_at || (record.freshness_basis !== "source_timestamp" && !eventReceiptBasis) ||
        !Number.isFinite(age) || !Number.isInteger(limit) || limit <= 0 ||
        Math.abs(Math.max(0, (generated - source) / 1000) - age) > 0.002 ||
        source > generated + 300000 || generated > now + 300000 ||
        (record.freshness_status === "current" && age > limit)) return "unavailable";
    return record.freshness_status === "stale" || now - source > limit * 1000 ? "stale" : "current";
  }

  function normalizeTopIntelligence(input, now) {
    now = now === undefined ? Date.now() : now;
    const artifact = asObject(input);
    if (!artifact || artifact.status === "unavailable" || (!artifact.freshness_items && artifact.freshness_status !== "current")) {
      return {
        status: "unavailable",
        items: [],
        message: "No current validated Top 3 intelligence is available."
      };
    }
    const items = Array.isArray(artifact.items) ? artifact.items.map(function (raw) {
      const item = asObject(raw);
      const freshness = item && (scopedFreshness(artifact, item.item_id, now) || item.freshness_status);
      if (!item || !["current", "stale"].includes(freshness) || item.validation_status !== "validated") {
        return null;
      }
      return {
        rank: item.rank,
        freshnessStatus: freshness,
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
        freshnessStatus: scopedFreshness(wrapped ? daily : fallback, wrapper ? wrapper.object_id : payload.signal_id, Date.now()),
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
            freshnessStatus: scopedFreshness(snapshot, item.symbol, Date.now()),
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
            freshnessStatus: scopedFreshness(macro, item.symbol, Date.now()),
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
    const beta = documentRef.getElementById("beta-live-status");
    if (beta) {
      beta.textContent = "";
      betaStatusLines(model, Date.now()).forEach(function (line) {
        beta.appendChild(element(documentRef, "p", "meta", line));
      });
    }
    const onboarding = documentRef.getElementById("onboarding-state");
    if (onboarding) {
      onboarding.textContent = "";
      onboardingHints(model).forEach(function (hint) { onboarding.appendChild(element(documentRef, "p", "meta", hint)); });
    }
    renderReport(documentRef, model);
    const header = researchHeader(model, Date.now());
    const statusNode = documentRef.getElementById("research-status");
    const updatedNode = documentRef.getElementById("research-updated");
    if (statusNode) statusNode.textContent = uiText(header.status);
    if (updatedNode) updatedNode.textContent = uiText(header.updated);
    renderMinimumUsefulStatus(documentRef, model.minimumUseful);
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

  function renderMinimumUsefulStatus(documentRef, gate) {
    const target = documentRef.getElementById("minimum-useful-status");
    if (!target) return;
    clear(target);
    const system = gate && gate.available ? ({healthy:"正常", degraded:"降級", unusable:"不可用"}[gate.system]) : "暫無資料";
    let report = "暫無資料";
    if (gate && gate.available) {
      report = gate.minimumUseful ? "可用" : gate.product === "degraded" ? "有限度可用，未達最低標準" : "不可用";
      if (gate.overall === "degraded" && gate.minimumUseful) report += "，但資料不完整";
    }
    const labels = {
      equity_core_unavailable:"美股目前沒有 current 資料", regime_unavailable:"Market Regime 暫不可判定",
      report_partial:"報告只有部分資料", report_stale:"報告包含過期資料",
      ai_generation_deterministic_fallback:"AI 使用規則式備援模式",
      provenance_validation_failed:"來源追溯驗證失敗", freshness_validation_failed:"資料新鮮度驗證失敗"
    };
    const limits = gate && gate.available && gate.limitations.length
      ? gate.limitations.map(function (value) { return labels[value] || value; }).join("；") : "沒有已發布的限制資料";
    target.appendChild(element(documentRef, "p", "meta", "系統狀態：" + system));
    target.appendChild(element(documentRef, "p", "meta", "今日情報：" + report));
    target.appendChild(element(documentRef, "p", "meta", "已知限制：" + limits));
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
    note.textContent = uiText(brief.fallbackNote);
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
      card.appendChild(badge(documentRef, item.freshnessStatus || "unknown"));
      if (item.freshnessStatus === "stale") card.appendChild(element(documentRef, "p", "meta", "資料已過期：僅供歷史參考，不代表目前市場狀況。"));
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
      target.textContent = uiText(value);
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
      if (signal.freshnessStatus) card.appendChild(badge(documentRef, signal.freshnessStatus));
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
      if (market.freshnessStatus) card.appendChild(badge(documentRef, market.freshnessStatus));
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
      const labels = {source_ids: "來源", observation_ids: "觀察", event_ids: "事件",
        evidence_ids: "證據", evidence_bundle_ids: "證據組合", signal_ids: "跨資產觀察",
        risk_ids: "風險", regime_dimension_ids: "市場環境構面", coverage_inputs: "資料涵蓋範圍"};
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
      node.textContent = tag === "code" || tag === "a" ? String(text) : uiText(text);
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
      model.topIntelligence.items.length ? model.topIntelligence.items.map(function (s) { return s.rank + ". " + (s.freshnessStatus === "stale" ? "[資料已過期／歷史參考] " : "") + s.headline; }) : ["No current validated stories available."]));
    lines("changes-content", model.changes || ["Previous available run unavailable."]);
    lines("report-quality-content", model.warnings.length ? model.warnings : ["No additional data quality warnings in supplied artifacts."]);
  }

  function betaStatusLines(model, now) {
    const lines = derivativesLines(model.derivatives, now);
    const available = lines[0] === "Validation: validated";
    const derivativeStatus = !available ? "unavailable" :
      lines.some(x => /stale/.test(x)) ? "stale" :
      lines.some(x => /: unavailable/.test(x)) ? "partial" : "available";
    const validReport = model.reportAvailable && model.validationStatus === "validated";
    return [
      "Current data status: " + (model.dataStatus || "unavailable"),
      "AI generation mode: " + (model.aiBrief ? model.aiBrief.modeLabel : "unavailable"),
      "Derivatives shadow: " + derivativeStatus + " · Not used for AI decisions",
      "Last successful report update: " + (validReport ? formatTimestamp(model.generatedAt) : "unavailable") +
        " (validated report timestamp; not proof of full pipeline success)",
      "Recorded freshness: " + (model.freshnessStatus || "unknown")
    ];
  }

  return {
    scopedFreshness: scopedFreshness,
    uiText: uiText,
    betaStatusLines: betaStatusLines,
    ENDPOINTS: ENDPOINTS,
    researchHeader: researchHeader,
    onboardingHints: onboardingHints,
    observedChanges: observedChanges,
    renderReferences: renderReferences,
    derivativesLines: derivativesLines,
    renderDerivatives: renderDerivatives,
    normalizeMinimumUsefulStatus: normalizeMinimumUsefulStatus,
    renderMinimumUsefulStatus: renderMinimumUsefulStatus,
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
