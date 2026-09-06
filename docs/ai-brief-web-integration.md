# AI Brief Web Integration Contract

## Scope

Phase 7.2-C is a presentation-only integration. The Intelligence Web View displays the already-produced and validated `ai_market_brief.md`; it does not generate, rank, interpret, validate, or rewrite market intelligence.

The browser must not contain an LLM client, prompt, provider configuration, or an alternative brief-generation path.

## Presentation hierarchy

The Intelligence page presents content in this order:

1. Grounded AI Brief
2. Today's Top Market Intelligence
3. Market Regime
4. Cross-Asset Signals
5. Risk Monitor
6. Market Overview
7. Evidence / Audit

The AI Brief is the narrative layer. Top Intelligence remains the structured, inspectable layer and is not removed or replaced. The existing market and audit sections remain available.

## Published inputs

The view reads only these relevant published artifacts:

- `data/ai_market_brief.md`: canonical narrative to display.
- `data/daily_market_brief.md`: deterministic fallback artifact, used only to identify an exact fallback result; it is not independently rendered as an AI brief.
- `data/run_manifest.json`: generation time, freshness, validation context, and publication provenance.

The existing structured JSON artifacts continue to supply all other page sections.

## Generation mode semantics

`generation_mode` is one of:

- `grounded_ai`: explicit backend metadata records successful validated provider output.
- `deterministic_fallback`: explicit backend metadata records use of the validated deterministic brief.
- `unavailable`: `ai_market_brief.md` is missing, empty, or cannot be loaded.

The `grounded_ai_brief.generation_metadata` record in `run_manifest.json` is the primary source of truth. For older manifests without valid generation metadata only, the browser retains the legacy byte-for-byte comparison: equal artifacts mean deterministic fallback; different artifacts mean grounded AI. The browser does not infer whether prose is good or grounded.

`generated_at`, `freshness_status`, and `validation_status` come from the explicit generation metadata. Legacy manifests use the grounded module/artifact metadata where available. Missing values are shown as `unknown`; they are never invented from the current clock.

## Fallback rendering

When `generation_mode` is `deterministic_fallback`, the brief remains visible and the page displays:

> AI generation was unavailable; the validated deterministic brief is shown instead.

When the AI brief artifact is unavailable, the brief section displays:

> AI Market Brief unavailable.

Failure of this section never prevents Top Intelligence or any later section from rendering.

## Markdown safety

The renderer implements a deliberately small allowlist:

- headings;
- paragraphs;
- unordered lists;
- reference lines.

Markdown is parsed into plain data blocks and rendered with DOM `textContent`. Raw HTML is never interpreted, `innerHTML` is never used, links and images are not expanded, and scripts cannot execute. HTML-looking input is displayed as literal text. The existing Content Security Policy remains in force as a second control.

The renderer limits accepted artifact size and rejects invalid input types. It does not fetch URLs embedded in Markdown.

## Traceability

Reference lines, including `[refs: ...]`, are preserved verbatim. They may use subdued styling, but remain visible and copyable.

The browser does not add, remove, resolve, or rewrite evidence identifiers. Structured evidence remains available in Top Intelligence and Evidence / Audit.

## Failure boundaries

- Missing AI brief: show the unavailable message; continue the page.
- Missing deterministic brief: display the AI brief as `grounded_ai`; do not synthesize a fallback comparison.
- Missing or malformed manifest: display the brief with `unknown` metadata; do not expose internal details.
- Unsafe-looking Markdown: render it as literal text using the allowlist.
- Missing structured artifacts: retain the existing section-level unavailable behavior.

No API keys, prompts, provider secrets, validator internals, or unpublished filesystem paths are exposed.
