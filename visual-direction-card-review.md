# Phase 12.4-B — Visual Direction Card Review

## Review scope

This review covers only the presentation candidate for `今日市場方向` and the
presentation-only `Crypto 資金情緒` placeholder. It does not approve or change
intelligence, ranking, scoring, regime, freshness, evidence, source, AI prompt,
or derivatives logic.

Review date: 2026-09-16 (Asia/Taipei)

## Result

**PASS — ready for commit review.** No presentation correction was required.

The first reading layer now follows this order:

1. 今日市場一句話
2. 今日市場方向
3. 今日最重要 3 件事
4. 接下來要留意
5. 市場環境與已知限制
6. 可展開的證據／完整報告／技術資訊

## Viewport results

| Viewport | Result | Horizontal overflow | First-screen observation |
|---|---|---:|---|
| 1440 × 1000 | PASS | No (`scrollWidth=clientWidth=1440`) | One-line summary and all five direction groups are visible before the detailed stories. |
| 390 × 844 | PASS | No (`scrollWidth=clientWidth=390`) | Summary and the direction grid appear immediately; Top 3 begins after one short scroll. |
| 375 × 812 | PASS | No (`scrollWidth=clientWidth=375`) | Two-column cards remain readable at approximately 14.7px state text; no clipped labels or cramped arrows. |

The 375px layout deliberately keeps two columns rather than compressing five
categories into tiny dashboard tiles. This means the final commodity card sits
just below the initial viewport, while the summary and the main Macro, FX,
Equity, BTC and ETH directions remain immediately visible.

## First-five-seconds review

Using the fixed local candidate data, a non-professional reader can identify:

- stronger / rising: EUR/USD, SPY, BTC, ETH and Gold;
- weaker: the U.S. dollar;
- context requiring attention: the one-line Risk-On summary, followed by the
  clearly linked `市場重點` and `接下來要留意` sections.

The cards are a visual reading aid, not a recommendation surface. They contain
no price targets, scores, buy/sell language, entry wording, or predictive claim.

## Direction card review

- Arrows are visually prominent and paired with words, so meaning does not rely
  on colour alone.
- Chinese wording is short and natural: `偏弱`, `走高`, `回落`, `持平`,
  `需要留意`.
- Up and down states use two restrained accent colours on the same neutral card
  surface. The page does not resemble a red/green trading terminal.
- Prices, raw changes, IDs and scores are absent from this layer.
- Category labels keep the grouping understandable without showing every asset.

## Crypto funding placeholder

The placeholder passed the unavailable-state review:

- heading: `Crypto 資金情緒`;
- explicit state: `資料尚未接入`;
- lists only future concepts: Funding Rate, OI and leverage changes;
- explicitly states that no live or simulated values are displayed;
- explicitly states that it is not used for intelligence decisions.

It reads as a planned product area rather than a broken data card and does not
imply that any live derivatives value exists.

## Audit layer

The `查看證據、完整報告與技術資訊` disclosure expands correctly. Existing
warnings, status metadata, timestamps, source names, observation IDs and evidence
references remain accessible and are visually secondary to the morning-brief
layer.

Browser console review at 375px returned no warning or error entries.

## Before / after

| Before | After |
|---|---|
| Summary paragraph led directly into detailed Top Intelligence prose. | Summary is followed by a six-asset direction scan grouped into five market categories. |
| Users had to read paragraphs to find relative strength and weakness. | Arrows plus concise Chinese states expose direction without displaying extra scores or raw numbers. |
| No reserved presentation state for future crypto positioning context. | A clearly unavailable, non-live Crypto funding placeholder explains future scope without fake data. |
| Evidence remained available but the path from summary to detail was text-heavy. | Evidence remains unchanged and expandable after the concise reading layer. |

## Presentation changes made during Phase 12.4-B

None. Phase 12.4-A candidate passed visual review as implemented.
