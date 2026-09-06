"""Deterministic orchestration of the existing market intelligence pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple

from src.brief.renderer_pipeline import run_renderer_pipeline
from src.calendar_pipeline import run_calendar_pipeline
from src.consolidation.pipeline import run_consolidation_pipeline
from src.data.freshness import aggregate_freshness_fields, aggregate_freshness_status
from src.evidence.pipeline import run_evidence_pipeline
from src.evaluation.pipeline import run_ai_brief_evaluation_pipeline
from src.events.pipeline import run_events_pipeline
from src.grounded_brief.pipeline import run_grounded_brief_pipeline
from src.intelligence.pipeline import run_daily_intelligence_pipeline
from src.top_intelligence.pipeline import run_top_intelligence_pipeline
from src.macro_pipeline import run_macro_pipeline
from src.models.run_manifest_schema import (
    ArtifactRunRecord,
    ModuleRunRecord,
    RunManifest,
)
from src.news_pipeline import run_news_pipeline
from src.pages.intelligence_generator import run_intelligence_page_generator
from src.pipeline import run_pipeline
from src.regime.pipeline import run_market_regime_pipeline
from src.risk.pipeline import run_risk_monitor_pipeline
from src.signals.pipeline import run_market_signals_pipeline
from src.orchestration.validator import validate_run_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIRECTORY = PROJECT_ROOT / "src" / "output"
DEFAULT_DOCS_DIRECTORY = PROJECT_ROOT / "docs"
MANIFEST_FILENAME = "run_manifest.json"
GENERATION_METADATA_FILENAME = "generation_metadata.json"

APPROVED_DYNAMIC_FILES = (
    "top_intelligence.json",
    "daily_intelligence.json",
    "ai_market_brief.md",
    "ai_brief_evaluation.json",
    "market_signals.json",
    "market_regime.json",
    "risk_monitor.json",
    "daily_market_brief.md",
    "market_snapshot.json",
    "macro_snapshot.json",
    MANIFEST_FILENAME,
)
APPROVED_STATIC_FILES = (
    "intelligence.html",
    "assets/intelligence.js",
)
APPROVED_PUBLIC_FILES = tuple(
    [f"data/{name}" for name in APPROVED_DYNAMIC_FILES]
    + list(APPROVED_STATIC_FILES)
)


@dataclass(frozen=True)
class RunPaths:
    work_directory: Path
    output_directory: Path
    docs_directory: Path

    def artifact(self, filename: str) -> Path:
        return self.work_directory / filename

    @property
    def data_directory(self) -> Path:
        return self.docs_directory / "data"


@dataclass(frozen=True)
class ModuleSpec:
    name: str
    outputs: Tuple[str, ...]
    hard_dependencies: Tuple[str, ...] = ()
    soft_dependencies: Tuple[str, ...] = ()


MODULE_SPECS = (
    ModuleSpec("market_data", ("market_snapshot.json",)),
    ModuleSpec("macro", ("macro_snapshot.json",)),
    ModuleSpec("calendar", ("economic_calendar.json",)),
    ModuleSpec("news_ingestion", ("news_items.json",)),
    ModuleSpec("event_normalization", ("events.json",), ("news_ingestion",)),
    ModuleSpec(
        "evidence_foundation",
        ("observations.json", "evidence.json"),
        ("market_data",),
        ("macro",),
    ),
    ModuleSpec(
        "evidence_consolidation",
        ("evidence_bundle.json",),
        ("evidence_foundation",),
        ("calendar", "event_normalization"),
    ),
    ModuleSpec("cross_asset_signals", ("market_signals.json",), ("evidence_consolidation",)),
    ModuleSpec(
        "market_regime",
        ("market_regime.json",),
        ("evidence_consolidation", "cross_asset_signals"),
    ),
    ModuleSpec(
        "risk_monitor",
        ("risk_monitor.json",),
        ("evidence_consolidation", "cross_asset_signals", "market_regime"),
    ),
    ModuleSpec(
        "daily_intelligence",
        ("daily_intelligence.json",),
        ("evidence_consolidation", "cross_asset_signals", "market_regime", "risk_monitor"),
    ),
    ModuleSpec("top_intelligence", ("top_intelligence.json",), ("daily_intelligence",)),
    ModuleSpec(
        "brief_renderer",
        ("daily_market_brief.md",),
        ("daily_intelligence", "top_intelligence"),
    ),
    ModuleSpec(
        "grounded_ai_brief",
        ("ai_market_brief.md",),
        ("top_intelligence", "daily_intelligence", "brief_renderer"),
    ),
    ModuleSpec(
        "ai_brief_evaluation",
        ("ai_brief_evaluation.json",),
        (
            "grounded_ai_brief",
            "top_intelligence",
            "daily_intelligence",
            "brief_renderer",
        ),
    ),
    ModuleSpec(
        "intelligence_web_view",
        ("docs/intelligence.html", "docs/assets/intelligence.js"),
        (),
        (
            "grounded_ai_brief",
            "top_intelligence",
            "daily_intelligence",
            "cross_asset_signals",
            "market_regime",
            "risk_monitor",
        ),
    ),
)
EXECUTION_ORDER = tuple(spec.name for spec in MODULE_SPECS)
Runner = Callable[[RunPaths], Any]


def _default_runners() -> Dict[str, Runner]:
    return {
        "market_data": lambda p: run_pipeline(p.artifact("market_snapshot.json")),
        "macro": lambda p: run_macro_pipeline(p.artifact("macro_snapshot.json")),
        "calendar": lambda p: run_calendar_pipeline(p.artifact("economic_calendar.json")),
        "news_ingestion": lambda p: run_news_pipeline(p.artifact("news_items.json")),
        "event_normalization": lambda p: run_events_pipeline(
            p.artifact("news_items.json"), p.artifact("events.json")
        ),
        "evidence_foundation": lambda p: run_evidence_pipeline(
            p.artifact("market_snapshot.json"),
            p.artifact("observations.json"),
            p.artifact("evidence.json"),
            p.artifact("macro_snapshot.json")
            if p.artifact("macro_snapshot.json").is_file()
            else None,
        ),
        "evidence_consolidation": lambda p: run_consolidation_pipeline(
            p.artifact("observations.json"),
            p.artifact("evidence.json"),
            p.artifact("economic_calendar.json"),
            p.artifact("events.json"),
            p.artifact("evidence_bundle.json"),
        ),
        "cross_asset_signals": lambda p: run_market_signals_pipeline(
            p.artifact("evidence_bundle.json"), p.artifact("market_signals.json")
        ),
        "market_regime": lambda p: run_market_regime_pipeline(
            p.artifact("evidence_bundle.json"),
            p.artifact("market_signals.json"),
            p.artifact("market_regime.json"),
        ),
        "risk_monitor": lambda p: run_risk_monitor_pipeline(
            p.artifact("evidence_bundle.json"),
            p.artifact("market_signals.json"),
            p.artifact("market_regime.json"),
            p.artifact("risk_monitor.json"),
        ),
        "daily_intelligence": lambda p: run_daily_intelligence_pipeline(
            p.artifact("evidence_bundle.json"),
            p.artifact("market_signals.json"),
            p.artifact("market_regime.json"),
            p.artifact("risk_monitor.json"),
            p.artifact("daily_intelligence.json"),
        ),
        "top_intelligence": lambda p: run_top_intelligence_pipeline(
            p.artifact("daily_intelligence.json"),
            p.artifact("top_intelligence.json"),
        ),
        "brief_renderer": lambda p: run_renderer_pipeline(
            p.artifact("daily_intelligence.json"),
            p.artifact("daily_market_brief.md"),
            p.artifact("top_intelligence.json"),
        ),
        "grounded_ai_brief": lambda p: run_grounded_brief_pipeline(
            p.artifact("top_intelligence.json"),
            p.artifact("daily_intelligence.json"),
            p.artifact("daily_market_brief.md"),
            p.artifact("ai_market_brief.md"),
        ),
        "ai_brief_evaluation": lambda p: run_ai_brief_evaluation_pipeline(
            p.artifact("top_intelligence.json"),
            p.artifact("daily_intelligence.json"),
            p.artifact("ai_market_brief.md"),
            p.artifact("daily_market_brief.md"),
            p.artifact(GENERATION_METADATA_FILENAME),
            p.artifact("ai_brief_evaluation.json"),
        ),
        "intelligence_web_view": _run_web_view,
    }


def run_daily_orchestration(
    output_directory: Path = DEFAULT_OUTPUT_DIRECTORY,
    docs_directory: Path = DEFAULT_DOCS_DIRECTORY,
    runners: Optional[Mapping[str, Runner]] = None,
    clock: Optional[Callable[[], datetime]] = None,
) -> Dict[str, Any]:
    """Run all existing modules in order and return the validated manifest."""
    output_directory = Path(output_directory)
    docs_directory = Path(docs_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    docs_directory.mkdir(parents=True, exist_ok=True)
    now = clock or (lambda: datetime.now(timezone.utc))
    started_at = _as_utc(now())
    active_runners = _default_runners()
    if runners:
        unknown = sorted(set(runners) - set(EXECUTION_ORDER))
        if unknown:
            raise ValueError(f"unknown orchestration runner(s): {unknown}")
        active_runners.update(runners)

    module_records = []
    failures = []
    with tempfile.TemporaryDirectory(prefix="market-intelligence-run-") as temporary:
        paths = RunPaths(Path(temporary), output_directory, docs_directory)
        module_outputs: Dict[str, bool] = {}

        for sequence, spec in enumerate(MODULE_SPECS, start=1):
            module_started = _iso(now())
            missing_hard = [
                dependency
                for dependency in spec.hard_dependencies
                if not module_outputs.get(dependency, False)
            ]
            if missing_hard:
                module_completed = _iso(now())
                failure = {
                    "module": spec.name,
                    "failure_type": "missing_hard_dependency",
                    "retryable": False,
                    "message": "Missing current-run artifact(s) from: "
                    + ", ".join(missing_hard),
                }
                failures.append(failure)
                module_records.append(
                    ModuleRunRecord(
                        sequence=sequence,
                        name=spec.name,
                        hard_dependencies=list(spec.hard_dependencies),
                        soft_dependencies=list(spec.soft_dependencies),
                        started_at=module_started,
                        completed_at=module_completed,
                        status="blocked",
                        source_timestamp=None,
                        retrieved_at=None,
                        generated_at=module_completed,
                        age_seconds=None,
                        freshness_status="unavailable",
                        declared_artifacts=list(spec.outputs),
                        failure=failure,
                        generation_metadata=_unavailable_generation_metadata(
                            module_completed,
                            "pipeline_failure",
                        ) if spec.name == "grounded_ai_brief" else None,
                    )
                )
                module_outputs[spec.name] = False
                continue

            warnings = [
                f"Soft dependency {dependency} did not produce a current-run artifact."
                for dependency in spec.soft_dependencies
                if not module_outputs.get(dependency, False)
            ]
            failure = None
            runner_result = None
            try:
                runner_result = active_runners[spec.name](paths)
            except Exception as exc:  # isolation boundary is intentional
                failure = {
                    "module": spec.name,
                    "failure_type": "module_execution_error",
                    "retryable": True,
                    "message": _safe_error(exc),
                }
                failures.append(failure)

            artifact_records = _inspect_outputs(spec, paths)
            module_outputs[spec.name] = len(artifact_records) == len(spec.outputs)
            if failure is not None:
                status = "failed"
            elif not module_outputs[spec.name]:
                status = "failed"
                failure = {
                    "module": spec.name,
                    "failure_type": "missing_declared_artifact",
                    "retryable": True,
                    "message": "Module completed without all declared artifacts.",
                }
                failures.append(failure)
            else:
                status = _module_status(artifact_records)
                if status == "unavailable":
                    failure = {
                        "module": spec.name,
                        "failure_type": "source_or_data_unavailable",
                        "retryable": True,
                        "message": "Module produced a valid unavailable artifact.",
                    }
                    failures.append(failure)
            warnings.extend(_artifact_warnings(spec, paths))
            module_completed = _iso(now())
            module_freshness = _module_freshness_fields(
                spec,
                artifact_records,
                module_records,
                module_completed,
            )
            generation_metadata = _module_generation_metadata(
                spec,
                runner_result,
                module_completed,
                failure,
            )
            if spec.name == "grounded_ai_brief" and generation_metadata is not None:
                _write_json(
                    generation_metadata,
                    paths.artifact(GENERATION_METADATA_FILENAME),
                )
            module_records.append(
                ModuleRunRecord(
                    sequence=sequence,
                    name=spec.name,
                    hard_dependencies=list(spec.hard_dependencies),
                    soft_dependencies=list(spec.soft_dependencies),
                    started_at=module_started,
                    completed_at=module_completed,
                    status=status,
                    source_timestamp=module_freshness["source_timestamp"],
                    retrieved_at=module_freshness["retrieved_at"],
                    generated_at=module_freshness["generated_at"],
                    age_seconds=module_freshness["age_seconds"],
                    freshness_status=module_freshness["freshness_status"],
                    declared_artifacts=list(spec.outputs),
                    artifacts=artifact_records,
                    warnings=sorted(set(warnings)),
                    failure=failure,
                    generation_metadata=generation_metadata,
                )
            )

        _promote_current_run_artifacts(paths)
        published, omitted = _published_files(paths)
        final_published = sorted(
            set(published) | {f"data/{MANIFEST_FILENAME}"}
        )
        execution_completed = _iso(now())
        manifest_freshness = aggregate_freshness_fields(
            [record.to_dict() for record in module_records],
            execution_completed,
        )
        manifest = RunManifest(
            run_id=_run_id(started_at),
            execution_started_at=_iso(started_at),
            execution_completed_at=execution_completed,
            status=_run_status(module_records),
            source_timestamp=manifest_freshness["source_timestamp"],
            retrieved_at=manifest_freshness["retrieved_at"],
            generated_at=manifest_freshness["generated_at"],
            age_seconds=manifest_freshness["age_seconds"],
            freshness_status=manifest_freshness["freshness_status"],
            execution_order=list(EXECUTION_ORDER),
            modules=module_records,
            artifact_versions=_artifact_versions(module_records),
            failures=failures,
            publication={
                "approved_files": list(APPROVED_PUBLIC_FILES),
                "published_files": final_published,
                "omitted_files": [
                    name for name in omitted if name != f"data/{MANIFEST_FILENAME}"
                ],
            },
        ).to_dict()
        validate_run_manifest(manifest, EXECUTION_ORDER, APPROVED_PUBLIC_FILES)
        manifest_path = output_directory / MANIFEST_FILENAME
        _write_json(manifest, manifest_path)
        _write_json(manifest, docs_directory / "data" / MANIFEST_FILENAME)
        return manifest


def _run_web_view(paths: RunPaths) -> Dict[str, str]:
    _remove_unapproved_public_data(paths.data_directory)
    artifact_paths = {
        name: paths.artifact(name)
        for name in APPROVED_DYNAMIC_FILES
        if name != MANIFEST_FILENAME and paths.artifact(name).is_file()
    }
    return run_intelligence_page_generator(
        output_path=paths.docs_directory / "intelligence.html",
        data_directory=paths.data_directory,
        script_target=paths.docs_directory / "assets" / "intelligence.js",
        artifact_paths=artifact_paths,
    )


def _inspect_outputs(spec: ModuleSpec, paths: RunPaths) -> list[ArtifactRunRecord]:
    records = []
    for declared in spec.outputs:
        path = _declared_path(declared, paths)
        if not path.is_file():
            continue
        payload = _read_json(path) if path.suffix == ".json" else None
        versions = _versions(payload)
        records.append(
            ArtifactRunRecord(
                path=declared,
                artifact_type=(
                    str(payload.get("artifact_type", path.stem))
                    if payload is not None
                    else path.stem
                ),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                versions=versions,
                source_timestamp=(
                    str(payload.get("source_timestamp"))
                    if payload is not None and payload.get("source_timestamp")
                    else None
                ),
                retrieved_at=(
                    str(payload.get("retrieved_at"))
                    if payload is not None and payload.get("retrieved_at")
                    else None
                ),
                generated_at=(
                    str(payload.get("generated_at"))
                    if payload is not None and payload.get("generated_at")
                    else datetime.fromtimestamp(
                        path.stat().st_mtime, tz=timezone.utc
                    ).isoformat().replace("+00:00", "Z")
                ),
                age_seconds=(
                    float(payload["age_seconds"])
                    if payload is not None
                    and isinstance(payload.get("age_seconds"), (int, float))
                    and not isinstance(payload.get("age_seconds"), bool)
                    else None
                ),
                data_status=(
                    _artifact_data_status(payload)
                    if path.suffix == ".json"
                    else "success"
                ),
                freshness_status=_artifact_freshness(payload),
                source_health=(
                    [_manifest_source_health(item) for item in payload.get("sources", []) if isinstance(item, dict)]
                    if payload is not None and isinstance(payload.get("sources"), list)
                    else []
                ),
                approved_for_publication=_is_approved_path(declared),
            )
        )
    return records


def _manifest_source_health(source: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalize provider-specific states to the manifest health vocabulary."""
    item = dict(source)
    raw_status = str(item.get("status", "invalid"))
    if raw_status in {"available", "unavailable", "invalid"}:
        normalized = raw_status
    elif raw_status in {"success", "complete", "current", "partial", "stale", "failed"}:
        normalized = (
            "available"
            if raw_status in {"success", "complete", "current", "partial"}
            else "unavailable"
        )
    else:
        normalized = "invalid"
    item["status"] = normalized
    if raw_status != normalized:
        item["raw_status"] = raw_status
    item["source"] = str(
        item.get("source")
        or item.get("source_id")
        or item.get("provider")
        or "unknown"
    )
    return item


def _declared_path(declared: str, paths: RunPaths) -> Path:
    if declared.startswith("docs/"):
        return paths.docs_directory / declared.removeprefix("docs/")
    return paths.artifact(declared)


def _read_json(path: Path) -> Optional[Mapping[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _module_status(records: Sequence[ArtifactRunRecord]) -> str:
    statuses = [record.data_status for record in records]
    if "unavailable" in statuses:
        return "unavailable"
    if "partial" in statuses:
        return "partial"
    return "success"


def _artifact_data_status(payload: Optional[Mapping[str, Any]]) -> str:
    if payload is None:
        return "unavailable"
    status = payload.get("status")
    if status is None and isinstance(payload.get("records"), list):
        record_statuses = {item.get("status") for item in payload["records"] if isinstance(item, dict)}
        if record_statuses and record_statuses <= {"failed"}:
            return "unavailable"
        if record_statuses & {"failed", "stale"}:
            return "partial"
        return "success"
    if status in {"complete", "available", "success", "validated"}:
        return "success"
    if status in {"partial", "stale"}:
        return "partial"
    if status in {"failed", "unavailable", "invalid"}:
        return "unavailable"
    return "success"


def _artifact_freshness(payload: Optional[Mapping[str, Any]]) -> str:
    if payload is None:
        return "unknown"
    direct = payload.get("freshness_status")
    if direct in {"current", "stale", "unavailable", "unknown"}:
        return str(direct)
    if _artifact_data_status(payload) == "unavailable":
        return "unavailable"
    candidates = [payload.get("freshness_status")]
    input_freshness = payload.get("input_freshness")
    if isinstance(input_freshness, dict):
        candidates.append(input_freshness.get("status"))
    coverage = payload.get("coverage")
    if isinstance(coverage, list):
        if any(
            isinstance(item, dict)
            and (item.get("stale_record_count", 0) or item.get("status") == "stale")
            for item in coverage
        ):
            candidates.append("stale")
    records = payload.get("records")
    if isinstance(records, list) and any(
        isinstance(item, dict) and item.get("status") == "stale" for item in records
    ):
        candidates.append("stale")
    normalized = [
        value
        for value in candidates
        if value in {"current", "stale", "unavailable", "unknown"}
    ]
    if "stale" in normalized:
        return "stale"
    if "current" in normalized:
        return "current"
    if "unavailable" in normalized:
        return "unavailable"
    return "unknown"


def _aggregate_freshness(statuses: Sequence[str]) -> str:
    return aggregate_freshness_status(statuses)


def _module_freshness_fields(
    spec: ModuleSpec,
    artifacts: Sequence[ArtifactRunRecord],
    prior_modules: Sequence[ModuleRunRecord],
    generated_at: str,
) -> Dict[str, Any]:
    records = [artifact.to_dict() for artifact in artifacts]
    if not records or all(record["freshness_status"] == "unknown" for record in records):
        dependencies = set(spec.hard_dependencies) | set(spec.soft_dependencies)
        records = [
            module.to_dict() for module in prior_modules if module.name in dependencies
        ]
    if not records:
        return {
            "source_timestamp": None,
            "retrieved_at": None,
            "generated_at": generated_at,
            "age_seconds": None,
            "freshness_status": "unknown",
        }
    return aggregate_freshness_fields(records, generated_at)


def _artifact_warnings(spec: ModuleSpec, paths: RunPaths) -> list[str]:
    warnings = []
    for declared in spec.outputs:
        payload = _read_json(_declared_path(declared, paths))
        if payload is not None and isinstance(payload.get("warnings"), list):
            warnings.extend(str(value) for value in payload["warnings"])
    return warnings


def _module_generation_metadata(
    spec: ModuleSpec,
    runner_result: Any,
    generated_at: str,
    failure: Optional[Mapping[str, Any]],
) -> Optional[Dict[str, Any]]:
    if spec.name != "grounded_ai_brief":
        return None
    if failure is not None:
        return _unavailable_generation_metadata(generated_at, "pipeline_failure")
    metadata_builder = getattr(runner_result, "generation_metadata", None)
    if callable(metadata_builder):
        metadata = metadata_builder()
        if isinstance(metadata, dict):
            return metadata
    if isinstance(runner_result, Mapping):
        metadata = runner_result.get("generation_metadata")
        if isinstance(metadata, dict):
            return dict(metadata)
    return _unavailable_generation_metadata(
        generated_at,
        "missing_generation_metadata",
    )


def _unavailable_generation_metadata(
    generated_at: str,
    fallback_reason: str,
) -> Dict[str, Any]:
    return {
        "generation_mode": "unavailable",
        "generation_status": "failed",
        "generated_at": generated_at,
        "freshness_status": "unavailable",
        "validation_status": "unavailable",
        "provider": None,
        "fallback_reason": fallback_reason,
    }


def _versions(payload: Optional[Mapping[str, Any]]) -> Dict[str, str]:
    if payload is None:
        return {}
    keys = ("schema_version", "schema_contract", "rule_set_version")
    return {key: str(payload[key]) for key in keys if payload.get(key) is not None}


def _artifact_versions(records: Sequence[ModuleRunRecord]) -> Dict[str, Dict[str, str]]:
    versions = {}
    for module in records:
        for artifact in module.artifacts:
            versions[artifact.path] = artifact.versions
    versions[MANIFEST_FILENAME] = {"schema_version": "1.0"}
    return dict(sorted(versions.items()))


def _run_status(records: Sequence[ModuleRunRecord]) -> str:
    statuses = {record.status for record in records}
    web_ok = next(
        (record.status in {"success", "partial"} for record in records if record.name == "intelligence_web_view"),
        False,
    )
    intelligence_ok = next(
        (record.status in {"success", "partial", "unavailable"} for record in records if record.name == "daily_intelligence"),
        False,
    )
    if not web_ok and not intelligence_ok:
        return "failed"
    return "complete" if statuses == {"success"} else "partial"


def _promote_current_run_artifacts(paths: RunPaths) -> None:
    expected = {
        filename
        for spec in MODULE_SPECS
        for filename in spec.outputs
        if not filename.startswith("docs/")
    }
    for filename in sorted(expected):
        source = paths.artifact(filename)
        target = paths.output_directory / filename
        if source.is_file():
            _atomic_copy(source, target)
        elif target.is_file():
            target.unlink()


def _remove_unapproved_public_data(data_directory: Path) -> None:
    data_directory.mkdir(parents=True, exist_ok=True)
    approved = set(APPROVED_DYNAMIC_FILES)
    for path in data_directory.iterdir():
        if path.is_file() and path.name not in approved:
            path.unlink()


def _published_files(paths: RunPaths) -> Tuple[list[str], list[str]]:
    published = []
    for relative in APPROVED_PUBLIC_FILES:
        path = paths.docs_directory / relative
        if path.is_file():
            published.append(relative)
    omitted = sorted(set(APPROVED_PUBLIC_FILES) - set(published))
    return sorted(published), omitted


def _is_approved_path(declared: str) -> bool:
    if declared.startswith("docs/"):
        return declared.removeprefix("docs/") in APPROVED_STATIC_FILES
    return declared in APPROVED_DYNAMIC_FILES


def _run_id(started_at: datetime) -> str:
    order_hash = hashlib.sha256("|".join(EXECUTION_ORDER).encode("utf-8")).hexdigest()[:12]
    return f"run_{started_at:%Y%m%dT%H%M%SZ}_orchestration_{order_hash}"


def _safe_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {' '.join(str(exc).split())}"[:500]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(f"{target.suffix}.tmp")
    shutil.copyfile(source, temporary)
    temporary.replace(target)


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Regenerate the deterministic daily market intelligence pipeline."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIRECTORY)
    parser.add_argument("--docs-dir", type=Path, default=DEFAULT_DOCS_DIRECTORY)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = run_daily_orchestration(args.output_dir, args.docs_dir)
    print(
        f"Completed orchestration {manifest['run_id']}; "
        f"status={manifest['status']}, failures={len(manifest['failures'])}"
    )
    return 1 if manifest["status"] == "failed" else 0


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
