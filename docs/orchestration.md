# Daily Intelligence Pipeline Orchestration

## Purpose

Phase 6.4-D adds a deterministic orchestration layer around the existing market
intelligence modules. It coordinates execution, records run-level health, and
publishes only approved static artifacts. It does not change the business rules,
schemas, or command-line interfaces owned by the individual modules.

The orchestrator is responsible for four things only:

1. execute existing modules in a fixed dependency order;
2. isolate source and module failures;
3. write a traceable `run_manifest.json`;
4. publish an explicit allowlist of GitHub Pages artifacts.

It does not perform analysis, prediction, recommendation, notification, or
natural-language generation.

## Execution order

Every run uses the following stable order:

| Sequence | Module | Output |
| ---: | --- | --- |
| 1 | Market data pipeline | `market_snapshot.json` |
| 2 | Macro pipeline | `macro_snapshot.json` |
| 3 | Economic calendar pipeline | `economic_calendar.json` |
| 4 | News source ingestion | `news_items.json` |
| 5 | News event normalization | `events.json` |
| 6 | Evidence foundation | `observations.json`, `evidence.json` |
| 7 | Evidence consolidation | `evidence_bundle.json` |
| 8 | Cross-asset signal engine | `market_signals.json` |
| 9 | Market regime classifier | `market_regime.json` |
| 10 | Risk monitor | `risk_monitor.json` |
| 11 | Structured intelligence composer | `daily_intelligence.json` |
| 12 | Deterministic brief renderer | `daily_market_brief.md` |
| 13 | Intelligence Web View | `docs/intelligence.html` and approved data files |
| 14 | Run manifest finalization | `run_manifest.json` |

Execution order is fixed even where two source modules are independent. This
makes run history and test output reproducible and keeps module ordering visible
in the manifest.

## Artifact dependencies

Dependencies are classified by artifact availability, not by a market opinion or
the data value contained in an artifact.

| Module | Hard dependencies | Soft dependencies |
| --- | --- | --- |
| Market data | none | none |
| Macro | none | none |
| Calendar | none | none |
| News ingestion | none | none |
| Event normalization | `news_items.json` | none |
| Evidence foundation | `market_snapshot.json` | `macro_snapshot.json` |
| Evidence consolidation | `observations.json`, `evidence.json` | `economic_calendar.json`, `events.json` |
| Cross-asset signals | `evidence_bundle.json` | none |
| Market regime | `evidence_bundle.json`, `market_signals.json` | none |
| Risk monitor | `evidence_bundle.json`, `market_signals.json`, `market_regime.json` | none |
| Intelligence composer | evidence bundle, signals, regime, risk artifacts | none |
| Brief renderer | `daily_intelligence.json` | none |
| Web View | none | all display artifacts |

A valid failure artifact satisfies availability. For example, a calendar artifact
with `status: failed` proves that the source was attempted and unavailable; it is
not treated as a missing artifact. The consolidator may consume that fact and
continue with a partial evidence bundle.

## Failure handling

The orchestrator uses these module statuses:

- `success`: execution completed and its data contract is available;
- `partial`: execution completed with stale, incomplete, or degraded data;
- `unavailable`: execution completed and produced a valid unavailable/failure
  artifact;
- `blocked`: a required artifact was not produced, so execution was skipped;
- `failed`: the module raised an exception or failed to produce its declared
  artifact.

Rules:

1. A source-declared failure is recorded as `unavailable`, not converted into
   fake data.
2. A soft dependency failure produces a warning and does not block the consumer.
3. A missing hard dependency marks the consumer `blocked`; downstream modules
   requiring its output are also blocked.
4. One module exception is captured in the manifest and does not terminate the
   orchestration process.
5. The Web View is still generated when intelligence artifacts are missing so it
   can display an explicit unavailable state.
6. Artifacts from an earlier run must not satisfy the current run. Modules write
   into an isolated run directory and only current-run artifacts are promoted.

Examples:

- Calendar returns HTTP 403 and writes a valid failed artifact: calendar is
  `unavailable`; evidence consolidation continues and the run is `partial`.
- News ingestion raises before writing an artifact: news is `failed`, event
  normalization is `blocked`, and evidence consolidation continues without news.
- Evidence consolidation raises: signals, regime, risk, intelligence, and brief
  are `blocked`; the manifest and unavailable Web View are still generated.

## Run manifest contract

`run_manifest.json` is an audit artifact for one orchestration attempt. Its
top-level contract is:

```json
{
  "schema_version": "1.0",
  "artifact_type": "run_manifest",
  "run_id": "run_20260828T010203Z_...",
  "execution_timestamp": "2026-08-28T01:02:03Z",
  "execution_started_at": "2026-08-28T01:02:03Z",
  "execution_completed_at": "2026-08-28T01:02:10Z",
  "status": "complete",
  "freshness_status": "current",
  "execution_order": ["market_data", "macro"],
  "modules": [],
  "artifact_versions": {},
  "failures": [],
  "publication": {
    "approved_files": [],
    "published_files": [],
    "omitted_files": []
  }
}
```

Each module record contains:

- sequence and module name;
- dependencies;
- start and completion timestamps;
- module status;
- declared and produced artifacts;
- artifact schema/rule versions where present;
- freshness status;
- warnings and structured failure details.

The run-level status is:

- `complete` when all required processing completed without degraded inputs;
- `partial` when at least one module is partial, unavailable, blocked, or failed
  but the run still produced usable output or an unavailable Web View;
- `failed` when no current-run intelligence or presentation output can be
  produced.

`freshness_status` is `current`, `stale`, `mixed`, or `unknown`. It is derived
from explicit upstream freshness metadata and record statuses. It does not infer
freshness from the orchestration time alone.

## Provenance and artifact versions

The orchestrator never rewrites evidence references or source metadata. Artifact
hashes and discovered version fields are copied into manifest records. Supported
version fields include `schema_version`, `schema_contract`,
`rule_set_version`, and renderer/view contract versions.

The manifest records paths relative to the repository where possible and stores
a SHA-256 digest for every produced artifact. This permits a published report to
be tied to the exact files generated during its run.

## Publication allowlist

Only the following dynamic artifacts may be copied into `docs/data/` by the
orchestrator:

- `daily_intelligence.json`
- `market_signals.json`
- `market_regime.json`
- `risk_monitor.json`
- `daily_market_brief.md`
- `market_snapshot.json`
- `macro_snapshot.json`
- `run_manifest.json`

The approved static files are:

- `docs/intelligence.html`
- `docs/assets/intelligence.js`

Calendar raw events, raw news items, normalized news events, observations,
evidence objects, and the evidence bundle remain internal audit artifacts. They
are not deployed by this phase. Unknown files in the managed `docs/data/`
directory are never added to the publication set.

## Scheduler integration

The existing GitHub Actions schedule remains the scheduler. It invokes one
orchestration CLI command after dependency installation and tests. The
orchestrator replaces the repeated intelligence-generation commands, while each
existing module CLI remains independently callable for development and recovery.

The scheduler must:

1. run tests;
2. invoke the orchestration CLI;
3. validate `run_manifest.json` and approved Pages artifacts;
4. upload generated audit artifacts and the static Pages package.

Telegram delivery and any other notification step are outside this contract. No
notification is triggered by the orchestration layer.

## Validation requirements

Before a run is considered valid:

- the execution order must match the frozen module order;
- every executed module must have a terminal status;
- every produced artifact must exist and have a SHA-256 digest;
- artifact versions must agree with the versions in the files;
- failures must reference the affected module;
- a blocked module must name at least one missing hard dependency;
- published dynamic files must be a subset of the publication allowlist;
- the final manifest itself must pass schema validation.
