# Phase 13.2.2 — Morning Report production validation

## Architecture and schedule

The canonical date checkpoint is the public-safe `YYYY/YYYY-MM-DD/morning_report_public.json` file on the separate `morning-reports` branch. The existing daily workflow resolves the Asia/Taipei local date, first validates/reuses that date file, and builds only if it is absent. A create-only GitHub Contents API call has no update SHA; a write race reads and validates the winner. A 30-day public-only Actions artifact is a secondary backup, not the lock. Pages receives the validated public projection after the existing intelligence pipeline's `docs/data` cleanup. Generated date files are never committed to `main`.

The workflow cron is `30 0 * * *` UTC, equivalent to 08:30 Asia/Taipei year-round. GitHub may start scheduled runs late; the fixed baseline timestamp remains the local 08:30 slot. Very-late/ambiguous scheduled starts are rejected rather than assigned a guessed report date. A manual same-day rerun reuses the date file even if market data has changed.

## Permissions and archive policy

The generate job has `contents: write` only because it must append to `morning-reports`; `actions: read` supports prior-run/artifact discovery. The deploy job retains only its Pages permissions. `GITHUB_TOKEN` is injected at runtime into the checkpoint step, not saved in a file. The archive branch was created from the existing `main` HEAD and protected with admin enforcement, linear history, no force-push and no deletion. The expected automated writer is the Daily Market Brief workflow on `main`; repository administrators retain recovery authority. Archive date files are append-only and retained in Git history; 7-/30-day retrieval is possible without an archive UI.

If the branch or an existing date file is unavailable/corrupt, the Morning Report step fails closed and does not publish a substitute baseline. The existing daily intelligence flow can still run. A first failed creation leaves the date free for same-day recovery. A successfully created date file is never replaced on a retry. An unavailable source report is not locked as the successful baseline.

## Live validation evidence

Pending first and second production runs. Record actual run IDs, commit identity, report ID, public projection SHA-256, baseline timestamp, artifact ID, Pages result, and security scan after execution. Do not infer success from local tests.

## Concurrency and next-day validation

Offline tests cover two candidate creators racing: only the first create succeeds; a conflict loads the validated existing file. The production workflow also uses a single `daily-market-brief` concurrency group with `cancel-in-progress: false`. Next-day path and timezone rollover are covered by deterministic tests; no future-dated live file is created merely to test rollover.

## Rollback and recovery

If live validation fails, stop further manual dispatches and revert the `main` workflow integration in a new reviewed commit. Do **not** delete or overwrite an already created archive date file; preserve it for audit and investigate its creating run and hash. If a branch protection or permission issue prevents first creation, fix that configuration and retry within the same Asia/Taipei date. If an existing date file is corrupt, fail closed and require an explicit administrator recovery review; never silently replace the file or treat it as absent. Pages can omit the optional Morning Report projection while the existing intelligence page remains available.
