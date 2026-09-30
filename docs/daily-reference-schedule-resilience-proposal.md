# Daily Reference staggered schedule proposal

Status: review approved for a local implementation checkpoint; push and deployment
await separate approval. Production validation remains pending.

## Proposed schedule

Replace `10 0 * * *` with `3,13,23 0 * * *` in
`.github/workflows/daily_reference_capture.yml`.

| Asia/Taipei | UTC | Nominal time remaining before cutoff |
| --- | --- | --- |
| 08:03 | 00:03 | 27 minutes |
| 08:13 | 00:13 | 17 minutes |
| 08:23 | 00:23 | 7 minutes |

All opportunities fall inside the existing 08:00–08:30 capture window.
The buffers start at the nominal trigger time, not the actual CLI start;
queueing, runner setup and source collection consume them. The last slot
does not guarantee completion before cutoff, even with the eight-minute job timeout.

## Existing safeguards

`run_capture` discovers and validates the dated checkpoint before fetching sources
or applying the new-capture time window. A valid checkpoint is reused unchanged,
including by a delayed same-day run. That path does not fetch sources or write a
new canonical checkpoint. An absent checkpoint after 08:30 fails closed.

The unchanged workflow concurrency group `daily-reference-capture`, with
`cancel-in-progress: false`, serializes these scheduled/manual capture runs and
does not cancel the active capture. Default concurrency permits one pending run;
another pending run can replace it, and ordering is not guaranteed. The three
slots are opportunities, not a promise that every queued run executes.

The checkpoint store supplies an independent create-only boundary: the dated
Contents API PUT omits an existing-file SHA. A competing writer returns a
409/422 conflict; the loser re-discovers and validates the winner. It cannot
overwrite the winner. Concurrency does not govern every other workflow on the
archive branch; unrelated-path conflicts may still fail safely. Outside the
shared group, simultaneous collectors could fetch twice before either persists,
but only one canonical same-date capture can win.

## Proposed diff and validation

- Workflow: schedule expression and explanatory comments only; permissions,
  concurrency, timeout and commands unchanged.
- CLI: retain the reviewed four-field safe failure logging proposal.
- Tests: each of the three slots can establish the first valid capture;
  subsequent and delayed runs reuse its bytes/creator without fetching;
  all late runs fail without fetching/writing; competing 409/422 writers preserve
  the winner; existing capture, Morning binding and log-security checks remain.

No capture-window, cutoff, source, schema, reuse or Morning-binding contract changes.

Local validation: **23 Daily Reference tests passed**, workflow YAML parsed and
schedule/concurrency/timeout assertions passed, and `git diff --check` passed.
No live workflow was dispatched and no production checkpoint was written.

## Operational limit and next decision

GitHub schedules are not hard real-time and can share the same delay or be dropped.
Staggering supplies extra opportunities; no measured success-rate improvement or
100% SLA is claimed. If future live evidence shows the entire 08:00–08:30 window
missed, evaluate a Cloudflare Cron or another external scheduler dispatching this
existing workflow early enough to complete within the same contract. Do not keep
expanding GitHub cron tuning or relax cutoff. External dispatch would still depend
on GitHub runner availability and requires a separately reviewed design.

References: [GitHub concurrency](https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency),
[scheduled workflow events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
