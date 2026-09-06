# Phase 7.1-A Legacy Pipeline Consolidation

## Purpose

Phase 7.1-A removes duplicate production presentation execution without deleting
the legacy modules that existing local users may still call. The canonical daily
production presentation is now owned by the Phase 6.4-D orchestrator.

This phase does not change market data, Evidence, Signal, Regime, Risk, or
Intelligence rules. It does not add AI generation, an LLM, a data source, a new
interface, or a notification channel.

## Current execution graph before consolidation

The production workflow previously executed this graph:

```text
GitHub Actions scheduler
        |
        +-- tests
        |
        +-- orchestration
        |      |
        |      +-- market/macro/calendar/news inputs
        |      +-- Evidence and Intelligence modules
        |      +-- daily_intelligence.json
        |      +-- daily_market_brief.md
        |      +-- Intelligence Web View
        |
        +-- legacy deterministic brief generator
        |      +-- market_snapshot.json -> daily_brief.md
        |
        +-- Mock Analyst generator
        |      +-- market_snapshot.json + market_context.json
        |          -> ai_market_brief.md
        |
        +-- legacy Pages generator
        |      +-- ai_market_brief.md -> docs/index.html
        |
        +-- Telegram sender
        |      +-- ai_market_brief.md
        |
        +-- artifact upload and Pages deployment
```

The three legacy generation steps ran after the canonical renderer and Web View.
They did not feed the Intelligence View, but they created a second production
presentation branch with a different input contract and different output files.

## Active production steps

The following remain active:

- dependency installation and the complete test suite;
- `src.orchestration.pipeline` as the single daily execution owner;
- the structured composer invoked by orchestration;
- the deterministic intelligence brief renderer invoked by orchestration;
- the Intelligence Web View packager invoked by orchestration;
- canonical artifact verification and audit artifact upload;
- GitHub Pages packaging and deployment;
- the existing optional Telegram delivery step, explicitly reading the canonical
  `daily_market_brief.md` artifact.

Telegram remains outside the presentation-generation graph. Delivery failure is
still isolated from the main workflow.

## Duplicated and legacy paths

| Legacy path | Previous production use | Phase 7.1-A state |
| --- | --- | --- |
| `src.brief.generator` | Built `daily_brief.md` directly from price data | Deprecated for production; CLI retained |
| `src.ai.analyst` with `MockLLMAdapter` | Built `ai_market_brief.md` | Deprecated for production; CLI retained |
| `src.pages.generator` | Rebuilt `docs/index.html` from Mock Analyst Markdown | Deprecated for production; CLI retained |
| `market_context.json` | Input to Mock Analyst | No longer a production presentation input |
| `daily_brief.md` | Uploaded legacy brief | Removed from production verification/upload |
| Legacy Mock Analyst ownership of `ai_market_brief.md` | Old Pages and Telegram input | Producer deprecated; filename reactivated in Phase 7.2-B exclusively for validated grounded output or deterministic fallback |

These modules are not deleted because their public Python functions, console
scripts, and tests provide backward compatibility for manual users. They must not
be invoked by the scheduled production workflow.

## Target architecture

```text
GitHub Actions scheduler
        |
        +-- tests
        |
        +-- orchestration
        |      |
        |      +-- validated upstream data and Evidence
        |      +-- daily_intelligence.json       (single source of truth)
        |      +-- top_intelligence.json         (frozen priority order)
        |      +-- daily_market_brief.md         (canonical Markdown)
        |      +-- ai_market_brief.md            (validated grounded rewrite or byte-identical fallback)
        |      +-- docs/intelligence.html        (canonical Web View)
        |      +-- docs/data/* approved files    (same-run publication)
        |      +-- run_manifest.json             (audit contract)
        |
        +-- canonical output verification
        +-- optional Telegram delivery from daily_market_brief.md
        +-- artifact upload
        +-- Pages deployment
```

The only sources of presentation facts are `daily_intelligence.json` and the
derived `top_intelligence.json`. The brief renderer, grounded writer, and Web
View do not independently select, infer, or regenerate intelligence. Reuse of
the historical `ai_market_brief.md` filename does not reactivate the legacy Mock
Analyst: orchestration is its only production owner, and grounded validation or
deterministic fallback is mandatory.

## Existing market page compatibility

`docs/index.html` remains available at the existing site root, including its
market and Crypto anchors. It is treated as a backward-compatible static page
and is not rebuilt by the scheduled workflow. Its navigation continues to link
to the canonical Intelligence View.

The canonical daily page is `docs/intelligence.html`. New integrations should
link to it and consume only the approved `docs/data/` artifacts.

## Telegram compatibility

The Telegram module and its CLI remain unchanged. Its historical default input
continues to support manual callers using `ai_market_brief.md`.

Production must pass the canonical input explicitly:

```bash
python -m src.telegram.bot \
  --input src/output/daily_market_brief.md \
  --skip-if-unconfigured
```

This redirects production delivery without changing Telegram formatting,
transport, retry, secret, or failure-isolation behavior.

## Migration plan

1. Remove direct legacy generator invocations from GitHub Actions.
2. Remove legacy presentation files from workflow verification and artifact
   upload.
3. Keep all existing legacy CLI entry points and unit tests.
4. Mark the legacy commands and artifacts deprecated in user documentation.
5. Route the existing optional Telegram step to the canonical brief explicitly.
6. Verify that orchestration remains the only command generating production
   presentation artifacts.
7. Preserve the existing root market page as a static compatibility surface.

## Validation contract

The consolidation is valid only when:

- the workflow invokes exactly one production presentation owner:
  `src.orchestration.pipeline`;
- the workflow does not invoke the legacy brief, Mock Analyst, old Pages, direct
  intelligence renderer, or direct Intelligence Pages commands;
- canonical intelligence artifacts are not mutated by page packaging;
- both the root compatibility page and Intelligence View remain buildable;
- Telegram production input is `daily_market_brief.md`;
- the publication set remains a subset of the orchestration allowlist;
- the full existing test suite passes.
