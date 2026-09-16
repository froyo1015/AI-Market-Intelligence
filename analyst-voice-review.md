# Phase 12.2.2 — Analyst Voice Reality Check

## Review scope

This review evaluates only the user-facing Traditional Chinese language layer. It does not change intelligence selection, ranking, regime classification, scoring, freshness, evidence contracts, or source data.

The target voice is a concise morning note written by a market research analyst:

- state what is observable;
- explain why the observation is useful;
- identify what to monitor next without forecasting an outcome;
- keep implementation details in the expandable technical layer.

## Review result

| Scenario | Natural Chinese | Market terminology | No internal leakage | No prediction / advice | Observation vs interpretation | Concise | Result |
|---|---|---|---|---|---|---|---|
| Risk-Off | Pass | Pass | Pass | Pass | Pass | Pass | **PASS** |
| Risk-On | Pass | Pass | Pass | Pass | Pass | Pass | **PASS** |
| Insufficient data | Pass after wording adjustment | Pass | Pass | Pass | Pass | Pass | **PASS** |

## Scenario 1 — Risk-Off environment

### Before

> Observed current risk-off regime

> 市場環境偏向 Risk-Off。已驗證的跨資產條件整體偏向防守。

Problems:

- English and classifier-style wording lead the sentence.
- 「已驗證的跨資產條件」describes implementation rather than the market.
- The reader is not told clearly what the observation means or what to monitor.

### After

**Headline**

> 目前市場偏向避險（Risk-Off）

**發生什麼事**

> 目前主要市場走勢整體較偏防守。

**為什麼重要**

> 這是理解其他市場變化的重要背景，但不代表下一步走向。

**接下來留意**

> 下一輪更新要看跨市場方向是否仍然一致。

Assessment: the Chinese conclusion comes first, `Risk-Off` remains as useful market terminology, and the text does not claim that the condition will persist.

## Scenario 2 — Risk-On environment

### Before

> Current market regime: risk_on

> 市場環境偏向 Risk-On。已驗證的跨資產條件整體偏向承擔風險。

Problems:

- The wording reads like a serialized classification result.
- 「承擔風險」without context is stiff and system-oriented.
- It does not separate the observed state from its significance.

### After

**Headline**

> 目前市場偏向風險資產（Risk-On）

**發生什麼事**

> 目前主要市場走勢整體較偏積極。

**為什麼重要**

> 這是理解其他市場變化的重要背景，但不代表下一步走向。

**接下來留意**

> 下一輪更新要看跨市場方向是否仍然一致。

Assessment: 「偏向風險資產」is market-language rather than a literal translation of an enum. It describes the current environment without predicting continuation.

## Scenario 3 — Insufficient-data environment

### Before

> Market regime unavailable due to insufficient fresh evidence.

> 目前沒有足夠的已驗證重點可供概括。

Problems:

- The English sentence exposes system output directly.
- 「可供概括」sounds translated and bureaucratic.
- A valid regime followed by 「未能整理可靠主線」could contradict itself when regime was the only available item.

### After

**No valid regime**

> 目前市場環境暫時無法判定。現有資料不足，今日暫未能整理出可靠的市場主線。

> 現有資料不足，暫時不宜為市場定調；待下一輪更新再作判斷。

**Valid regime but no additional current story**

> 除市場環境外，現有資料暫未支持更多可靠主線。

Assessment: the output says plainly what cannot be concluded. It neither fills the gap with a prediction nor treats missing information as a market signal.

## Language and safety findings

### Market terminology

- Traditional Chinese leads every headline.
- `Risk-On`, `Risk-Off`, `CPI`, `FOMC`, tickers, and source names remain where they improve recognition.
- Common calendar names receive a Chinese market description before the original English name.
- The copy avoids using 「市場情緒」when the input only proves observed price relationships.

### Observation and interpretation boundary

- 「發生什麼事」is assembled only from validated current fields.
- 「為什麼重要」explains reading context without adding a cause.
- 「接下來留意」names a future observation to check; it does not state the future outcome.
- Phrases such as 「不能證明因果」and 「不是走勢預測」remain where the distinction matters.

### Technical language containment

The primary reading layer does not display:

- deterministic classifier;
- story key;
- internal type or rule ID;
- scoring or confidence mechanics;
- coverage terminology.

Those fields remain available only in the expandable evidence and technical section.

### Concision contract

Automated checks enforce:

- summary: at most 100 characters;
- headline: at most 40 characters;
- each observation, significance, and watch sentence: at most 70 characters;
- no buy/sell, position-sizing, target-price, certainty, or directional-prediction language.

## Tests

`tests/js/reading_brief.test.js` now covers:

- Risk-Off analyst voice;
- Risk-On analyst voice;
- insufficient-data wording;
- regime-only summary consistency;
- Chinese-first headlines;
- observation / significance / watch separation;
- internal terminology leakage;
- prediction and trading-advice language;
- maximum copy length;
- existing stale, invalid, unsupported, order, evidence-grounding, crypto, equity, gold/dollar, FX, and calendar-event cases.

## Conclusion

All three scenarios pass the analyst-voice review. The presentation now reads as a concise Traditional Chinese market brief while preserving the original evidence trail and the boundary between observed facts and interpretation.
