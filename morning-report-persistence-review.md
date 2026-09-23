# Morning Report persistence review — Phase 13.2

## Existing hosting path

The current production workflow downloads a previous successful run artifact for market comparison, then regenerates current intelligence and deploys the `docs/` Pages tree. It uploads a `daily-market-brief-*` Actions artifact with a 30-day retention setting. `docs/data/` is replaced on each build. The workflow has `contents: read` and `actions: read`, and does not write a dated morning archive. Its `schedule` is already 08:30 Asia/Taipei; this phase does not alter it.

| Lifecycle step | Before Phase 13.2 | Phase 13.2 local foundation | Later production integration needed |
|---|---|---|---|
| First morning run | Regenerates mutable daily report and Pages data | Validates cutoff inputs and creates one dated baseline | Publish the dated baseline to durable repository archive |
| Same-day retry | May regenerate presentation from newer input | Reads the existing baseline without replacing its bytes | Read date key before build; handle remote create conflict |
| Next-day run | Previous Pages data replaced; Actions history expires | New local date path leaves prior file untouched | Persist date paths across ephemeral runners |
| Public retrieval | Latest Pages files only | Validated public-safe projection of stored baseline | Publish current and previous dated public projections |

| Candidate | Cross-run retrieval | Immutable per date | History / limitation | Decision |
|---|---|---|---|---|
| Workflow artifact checkpoint | Actions API can find/download prior runs | Artifact immutable within one run, but reruns create distinct artifacts | Current upload retains 30 days; listing/expiry and choosing a winner need extra logic | Useful backup, not sole date authority |
| Current `docs/data/` Pages artifact | Public fetch possible | New deployment replaces content | No reliable same-date lock or full historical archive | Public projection only |
| Date-keyed repository archive | Direct path lookup for date, Git history for replay | Create-only path and no overwrite policy, enforced with serialized workflow and conflict handling | Requires explicit `contents: write` approval when integrated | Preferred production persistence |
| Local Actions workspace | Easy within one run | Atomic file insertion locally | Fresh runner loses it after run | Implemented foundation and tests only |

Recommended later integration: dedicated `morning-reports` branch containing public-safe per-date JSON, `YYYY/YYYY-MM-DD/`. A scheduled job first reads that branch and validates the dated baseline. If present, it republishes the existing report and does not call the builder. If absent, it builds once from the completed source run and creates the dated file without an update SHA. A repository Contents API create request that finds an existing file must be treated as a conflict and followed by a read/validation of the winner; never retry with an update SHA. Serialize the morning job with a fixed concurrency group; keep `cancel-in-progress: false`. The branch must reject manual edits or overwrites by policy/review. No content token scope change, branch creation or remote write occurs in this phase.

Retain dated files indefinitely in Git by default; serve current and previous day from the archive once approved. That structure also supports 7- and 30-day replay without building archival UI. A single mutable `docs/data/morning_report_public.json` can point to today's immutable dated record in a later integration, but cannot be the archive authority. Public-only archive data avoids secrets at rest in a public repository. Private debug/input payloads remain in expiring Actions artifacts, not the branch.

Operational safeguards for a later workflow: verify manifest run linkage and SHA before insertion, derive target local date from the scheduled 08:30 slot, reject after-day backfills without an explicit approved recovery policy, and reconcile non-fast-forward/race conflicts by loading the existing dated record. If the archive read fails, do not create a second baseline from a later source. A failed first creation may be recovered during the same local day. Record source run and artifact hashes for replay.

Because this phase does not add the remote archive or workflow step, **cross-run GitHub immutability is designed but not yet operational**. The local archive code is ready for that integration; users should not interpret the `samples/` files as a live Morning Report.

Sources: [GitHub schedule syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax), [artifact retention](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts), [repository Contents API](https://docs.github.com/en/rest/repos/contents).
