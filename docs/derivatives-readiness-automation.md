# Phase 8.3 — Readiness automation

Existing daily shadow collection now exports both archive-linked readiness and
a closed-schema public projection. Readiness policy/thresholds are unchanged.
Tracking is for the seven UTC dates ending at evaluation time:

- collected_days: distinct dates with a supplied nonduplicate sample (an
  unavailable-provider attempt counts as collected, not successful).
- missing_days: required dates with no sample; never filled synthetically.
- freshness_pass_rate: samples passing the all-facts-current check / samples.
- provenance_completeness: samples with complete verified provenance / samples.
- validation_failures: samples with failed consistency validation, including
  malformed samples. Empty sample denominator gives null, not 100%.

Duplicate snapshots do not inflate denominators. Rates are sample-level checks,
not continuous uptime or ratios of individual source records. Corrupted archive
replay still fails closed before aggregation; these failures surface as workflow
failures rather than silently fabricated readiness rows.

Scheduler produces derivatives_readiness.json and derivatives-shadow.json at the
same evaluation cutoff. Only the latter is uploaded unencrypted as the named
`derivatives-shadow-public` artifact, after closed-schema validation. Raw inputs
remain in encrypted checkpoint only. A failing checkpoint step prevents public
publication. No secret is exposed to the Pages workflow.

The existing daily Pages workflow downloads the latest projection from the shadow
workflow on the repository default branch, validates again, and installs only
docs/derivatives-shadow.json. Missing/expired projection removes any checked-in
snapshot so the view shows unavailable. API/download/invalid-projection failures
fail the workflow; no arbitrary files from downloaded artifacts enter Pages.
This update is publication-only, after canonical orchestration. It does not rerun
or modify canonical intelligence/AI inputs. Cadences remain unchanged, so the
Pages run displays the latest available shadow snapshot (possibly the prior day);
browser freshness re-aging and snapshot timestamps remain visible.

production_enabled=false is mandatory even after readiness reaches passing.
No AI, ranking, signals or regime integration. Deployment requires reviewed code
to be committed/pushed and the existing archive secret/bootstrap configuration;
this phase does not trigger remote runs. GnuPG real encryption tests remain
skipped locally if GnuPG is absent, and required on the Actions runner.
