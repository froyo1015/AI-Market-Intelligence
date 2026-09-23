# Phase 13.2.1 — Morning Report persistent checkpoint review

## Decision

Use a **date-keyed public projection on a dedicated `morning-reports` Git branch** as the cross-run authority. Keep a 30-day Actions artifact as a supplementary checkpoint. Do not commit generated files to `main`, add a database, or deploy this candidate yet.

The existing `daily-market-brief-*` artifact pattern proves that this repository can retrieve earlier workflow artifacts. But an Actions artifact has a finite retention period and can be deleted; by itself it cannot reliably prove that a date had *never* been generated. A single Pages path is mutable on every deployment. The branch path `YYYY/YYYY-MM-DD/morning_report_public.json` is therefore the durable date lock. The create request omits `sha`; a conflict reads and validates the existing winner rather than updating it. Only the approved public projection is stored there. The archive branch must be created and protected before activation.

GitHub documentation: [Actions artifact API](https://docs.github.com/en/rest/actions/artifacts), [artifact retention](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts), [Contents API create/update semantics](https://docs.github.com/en/rest/repos/contents).

## Persistence flow

```text
scheduled 08:30 Asia/Taipei (or explicit manual recovery slot)
  -> derive local report_date; reject ambiguous very-late scheduled start
  -> check dedicated archive branch exists
  -> read exact dated public file
       present: validate schema, date, one-commit history, content hash,
                creating workflow run/repository/branch/SHA; reuse unchanged
       absent:  inspect same-date Actions artifacts for an orphan/expired
                checkpoint; fail closed if any or if discovery fails
                -> find a validated prior source run completed by cutoff
                -> build fixed Morning Report from its validated inputs
                -> create-only dated public file (no update SHA)
                -> read back and verify winner
  -> copy validated public projection into docs/data for Pages
  -> optionally upload 30-day public-only Actions artifact
```

`source_run_id` inside the report identifies the intelligence source run. The date-file commit message separately records the **Actions creating run ID**, source branch, workflow path, repository, head SHA, and SHA-256 of the exact public file bytes. On discovery these are checked against GitHub's run API. A file with more than one path-specific commit is rejected as modified. An API error, wrong provenance, corrupt file, missing archive branch, or orphan Actions artifact is not treated as an absent baseline.

A locally generated report whose `data_status` is `unavailable` is not persisted as the day's successful checkpoint. A later attempt may recover if eligible pre-cutoff evidence becomes available. Partial reports remain eligible, with their limitations and freshness visible. Neither case upgrades stale data to current.

This protects ordinary reruns and create races. It does **not** defend against an administrator force-pushing or deleting the archive branch or deleting both the branch record and every artifact. Branch protection and restricted write access are release prerequisites. GitHub itself cannot make an admin-level deletion mathematically impossible.

## Retention and public data

The archive branch retains dated public projections indefinitely, supporting current/previous day and later 7-/30-day replay without an archive UI. The candidate Actions artifact uses `retention-days: 30`, subject to repository/organization limits. Its ZIP contains only `morning_report_public.json`; never the private baseline, source inputs, response headers, raw provider payloads, or credentials. Pages receives only the validated public projection. No user-specific generation occurs.

## Workflow candidate — review only

`docs/workflow-candidates/morning-report-checkpoint.yml` is an **illustrative patch fragment**, not an active workflow. It resolves/downloads a prior source before the mutable daily pipeline, then discovers/creates the checkpoint **after** that pipeline finishes and before Pages upload. This order is necessary because current orchestration removes extra `docs/data` files during its public-data cleanup; writing the projection earlier would silently lose it. Existing daily generation, Pages upload, Telegram, and cadence are otherwise unchanged. The existing workflow has one concurrency group with `cancel-in-progress: false`; this serializes ordinary workflow reruns. The dedicated branch still provides the create-only lock if execution is concurrent elsewhere.

To activate later: create/protect `morning-reports`, grant the generate job `contents: write` and `actions: read`, review branch protection and repository artifact retention, integrate the fragment into `.github/workflows/daily_market_brief.yml`, then test a live first creation plus same-day rerun. `GITHUB_TOKEN` is runtime-only. The current production workflow has **not** been edited by this phase.

The workflow candidate intentionally does not use today's freshly generated intelligence for an 08:30 baseline: that output did not exist at the 08:30 cutoff. A previous eligible run is selected by completion time; the Python builder additionally enforces its own timestamp, date, manifest SHA, freshness, and validation rules. If no eligible source exists, Morning Report publication fails closed while the existing daily pipeline can continue. The date artifact is not created from stale or post-cutoff data.

## Review evidence and limitations

Offline tests simulate first creation, cross-run restore with missing local inputs, same-day reuse, failed first attempt/retry, conflict, next-day key, expired/orphan artifact, corrupt file, modified history, wrong branch/workflow/repository, public-only payload and API failure. No GitHub write was performed. A live guarantee requires the later protected-branch setup, workflow activation, and a real rerun test; **Phase 13.2.1 is a candidate, not a deployed persistence guarantee**.

`samples/morning_checkpoint_reuse.json` records the offline first-run/reuse scenario. Its run IDs are test fixtures, not GitHub production runs. An expired backup artifact does not invalidate a valid branch checkpoint; if the branch date file is absent and an expired/orphan artifact is still discoverable, generation fails closed instead of guessing that the date was never created.
