# Phase 12.0.1 — Visual Product QA

Status: **PASS — ready for product review before commit or deployment.**

The BEFORE screenshots use the exact Phase 11.7 deployed Pages artifact. The AFTER screenshots use the Phase 12.0 candidate with the same Phase 11.7 live data artifacts, so this comparison isolates presentation and information hierarchy.

## Viewport results

| Viewport | Result | First screen | Text and number density | Readability / runtime |
|---|---|---|---|---|
| 1440px | PASS | Market direction appears in the upper half; all three story headlines and their concise explanations are visible in the first viewport. The top navigation links directly to monitoring and evidence. | Three-sentence summary; no score, price grid, freshness age, coverage count or evidence ID in the primary flow. The sole numeric token is the structural “3” in the section heading. | No overflow, failed requests or JavaScript errors. CLS 0.0012. |
| 390px | PASS | Summary begins at 366px; current direction and the first story appear without a scroll. Remaining stories follow in one natural text column. | Short paragraphs, no cards or badges in the primary flow, no technical metadata above the disclosure. | No overflow in closed or fully expanded states. Headings wrap naturally. CLS 0.0109. |
| 375px | PASS | Same hierarchy as 390px; the three-sentence summary and first current story remain visible within the initial viewport. | The summary wraps cleanly and the story copy remains readable. No dense metrics or technical IDs appear. | No overflow in closed or fully expanded states. No JavaScript errors. CLS 0.0109. |

## Product review

### First 10 seconds

PASS. The first useful text states: `市場環境：Risk-Off。美元指數上升、EURUSD下降。BTC／ETH 同步上升。` It contains three grounded observations and no causal or predictive language. The next heading explicitly introduces the three selected stories. “接下來要留意” is available through the header link and follows the stories in reading order.

### Text density

PASS. The summary contains three short sentences. Each story contains one headline, one explanation and a quiet evidence link. Beta metadata, pipeline status, the full deterministic/AI brief, market cards and diagnostics no longer occupy the primary reading experience.

### Number density

PASS. The primary flow contains no scores, prices, confidence values, ages, counts or identifiers. The number `3` labels the number of selected stories. Existing scores and market values remain in the technical report.

### Mobile readability

PASS. Content is a single text column. There are no primary cards or badge clusters. At 390px and 375px the document width equals the viewport width, and expanding every technical disclosure produces no horizontal overflow.

### Product hierarchy

PASS. Browser geometry confirms this order:

1. 今日市場一句話
2. 今日最重要 3 件事
3. 接下來要留意
4. 市場環境
5. 已知限制
6. 查看證據、完整報告與技術資訊

### Audit layer

PASS. The technical layer starts collapsed. It contains the original evidence IDs, timestamps, source names and warnings. Each primary story’s “查看此項證據” link opens the disclosure and targets its corresponding existing Top Intelligence card. The disclosure can be closed again and remains readable when all nested sections are expanded.

## Runtime and state checks

- No `pageerror` events or HTTP failures in the final controlled comparison.
- No loading copy remains in the primary flow after initialization.
- Current, validated items retain their selected order.
- Stale, invalid, unsupported and unmatched records cannot be presented as current facts.
- Positive, negative and flat BTC/ETH observations produce the matching Chinese direction.
- An unavailable regime uses a generic insufficient-evidence explanation; it does not invent a timestamp mismatch.
- Missing calendar evidence produces a limitation, not a claim that no future event risk exists.
- Initial technical disclosure is closed; open, anchor navigation and close behavior pass.

## Presentation issues found and fixed

1. The first summary repeated Risk-Off because the regime and its matching Top story both entered the summary. The summary now suppresses a duplicate `market_state` story while retaining the story in Top 3.
2. Initial mobile CLS was approximately 0.33 because one-line loading placeholders expanded into three stories. Presentation-only loading space now reserves the expected reading area; final mobile CLS is approximately 0.011.
3. Monitoring points were alphabetically sorted by a shared helper. The reading layer now preserves Top Intelligence order while deterministically removing duplicates.

## Screenshot inventory

- `review/phase-12.0/before-1440.png`
- `review/phase-12.0/after-1440.png`
- `review/phase-12.0/before-390.png`
- `review/phase-12.0/after-390.png`
- `review/phase-12.0/before-375.png`
- `review/phase-12.0/after-375.png`

Machine-readable browser results are in `review/phase-12.0/visual-qa-results.json`.

## Conclusion

All six product-review questions pass. The candidate reads as a concise market brief before exposing system diagnostics, remains useful without raw prices, and keeps the complete audit trail accessible. No intelligence, ranking, scoring, regime, freshness, evidence, prompt, source, derivatives or Minimum Useful Gate behavior changed.
