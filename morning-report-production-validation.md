# Phase 13.2.2 — Morning Report production validation

## Architecture and schedule

The canonical date checkpoint is the public-safe `YYYY/YYYY-MM-DD/morning_report_public.json` file on the separate `morning-reports` branch. The existing daily workflow resolves the Asia/Taipei local date, first validates/reuses that date file, and builds only if it is absent. A create-only GitHub Contents API call has no update SHA; a write race reads and validates the winner. A 30-day public-only Actions artifact is a secondary backup, not the lock. Pages receives the validated public projection after the existing intelligence pipeline's `docs/data` cleanup. Generated date files are never committed to `main`.

The workflow cron is `30 0 * * *` UTC, equivalent to 08:30 Asia/Taipei year-round. GitHub may start scheduled runs late; the fixed baseline timestamp remains the local 08:30 slot. Very-late/ambiguous scheduled starts are rejected rather than assigned a guessed report date. A manual same-day rerun reuses the date file even if market data has changed.

## Permissions and archive policy

The generate job has `contents: write` only because it must append to `morning-reports`; `actions: read` supports prior-run/artifact discovery. The deploy job retains only its Pages permissions. `GITHUB_TOKEN` is injected at runtime into the checkpoint step, not saved in a file. The archive branch was created from the existing `main` HEAD and protected with admin enforcement, linear history, no force-push and no deletion. The expected automated writer is the Daily Market Brief workflow on `main`; repository administrators retain recovery authority. Archive date files are append-only and retained in Git history; 7-/30-day retrieval is possible without an archive UI.

If the branch or an existing date file is unavailable/corrupt, the Morning Report step fails closed and does not publish a substitute baseline. The existing daily intelligence flow can still run. A first failed creation leaves the date free for same-day recovery. A successfully created date file is never replaced on a retry. An unavailable source report is not locked as the successful baseline.

## Live validation evidence

Production activation commit: `0d73f8dbce2712e13f8264b7d32dc50ba86190d0` on `main`. The archive branch was created from the prior `main` HEAD and remains separate from generated files on `main`.

| Check | Live Run A — first creation | Live Run B — same-day retry |
|---|---|---|
| Actions run | [35832666621](https://github.com/froyo1015/AI-Market-Intelligence/actions/runs/35832666621) | [35832903568](https://github.com/froyo1015/AI-Market-Intelligence/actions/runs/35832903568) |
| Generate / Pages jobs | success / success | success / success |
| Checkpoint CLI | `created:true`, `creator_run_id:35832666621` | `created:false`, `creator_run_id:35832666621` |
| Report ID | `morning_2026-09-23_5ad868ac444dc324bf83` | unchanged |
| Baseline date / time | `2026-09-23`, `2026-09-23T00:30:00Z` (08:30 Taiwan) | unchanged |
| Actual generation time | `2026-09-23T07:38:21.698999Z` | unchanged in reused file |
| Report / source state | `partial`, source freshness `current`; source run `run_20260922T051308Z_orchestration_199bdf533cb3` | unchanged |
| Dated branch file | `2026/2026-09-23/morning_report_public.json` | same file, no second path commit |
| Public JSON SHA-256 | `b226ac3918c9ac5528da5b8812a4583c452b0235b692bbfeea822270dfb0ad95` | identical |
| Branch path history | one commit, `de4094f91613da69541ef35864ca5944745a574c` | still one commit |
| Git blob SHA / size | `016395236e995fb3fb365d7f95630b964776b32d` / 11,127 bytes | unchanged |
| Secondary artifact | ID `10737454561`, 30-day expiry `2026-10-23T07:38:25Z` | creation-only upload skipped; no second date artifact |
| Pages deployment | `6608848069` success | `6608888341` success |

The date-file commit message records Run A, the source branch/workflow/repository, deployment commit and the exact file hash. Run B's log explicitly states `created:false`. The public [Morning Report JSON](https://froyo1015.github.io/AI-Market-Intelligence/data/morning_report_public.json) after Run B has the same report ID, baseline timestamp and byte SHA-256 as the protected archive file. It exposes `report_type:"morning"` and `baseline_for_date:"2026-09-23"`; no Market Pulse was introduced. The live public JSON passed the approved projection validator and a scan for credentials, raw responses, internal filesystem paths and private-key markers with zero findings. Artifact upload logs confirm exactly one file; the backup artifact is not the canonical lock.

Both runs were **manual on September 23 Taiwan afternoon**. They validate real cross-run immutability and Pages publication, not punctuality of the next automatic 08:30 scheduled fire. `generated_at` is therefore later than the 08:30 baseline cutoff by design; the source run was selected from before that cutoff. The first scheduled morning execution remains an operational follow-up, not a condition claimed to have passed here.

## Concurrency and next-day validation

Offline tests cover two candidate creators racing: only the first create succeeds; a conflict loads the validated existing file. The production workflow also uses a single `daily-market-brief` concurrency group with `cancel-in-progress: false`. Next-day path and timezone rollover are covered by deterministic tests; no future-dated live file is created merely to test rollover.

Local validation before activation: 652 tests collected, 651 passed and 1 skipped; relevant Morning Report tests passed; production YAML parsed; staged diff check passed; no staged secret/private-path markers. The live archive branch protection was confirmed as admin-enforced, linear-history-only, force-push disabled and deletion disabled. No deliberately corrupt production artifact, permission denial, or failed live run was injected; those failure cases are covered by offline tests and fail-closed code paths.

## Rollback and recovery

If live validation fails, stop further manual dispatches and revert the `main` workflow integration in a new reviewed commit. Do **not** delete or overwrite an already created archive date file; preserve it for audit and investigate its creating run and hash. If a branch protection or permission issue prevents first creation, fix that configuration and retry within the same Asia/Taipei date. If an existing date file is corrupt, fail closed and require an explicit administrator recovery review; never silently replace the file or treat it as absent. Pages can omit the optional Morning Report projection while the existing intelligence page remains available.
