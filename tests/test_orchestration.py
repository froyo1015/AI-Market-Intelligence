from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Optional

from src.orchestration.pipeline import (
    APPROVED_PUBLIC_FILES,
    EXECUTION_ORDER,
    MODULE_SPECS,
    RunPaths,
    run_daily_orchestration,
)


FIXED_NOW = datetime(2026, 8, 28, 1, 2, 3, tzinfo=timezone.utc)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _artifact_payload(filename: str, status: str = "complete") -> dict:
    return {
        "schema_version": "1.0",
        "artifact_type": Path(filename).stem,
        "freshness_contract_version": "1.0",
        "source_timestamp": "2026-08-28T01:02:03Z",
        "retrieved_at": "2026-08-28T01:02:03Z",
        "generated_at": "2026-08-28T01:02:03Z",
        "age_seconds": 0.0,
        "freshness_status": "current",
        "freshness_basis": "source_timestamp",
        "stale_after_seconds": 172800,
        "status": status,
        "warnings": [],
    }


def _successful_runners(
    order: Optional[list[str]] = None,
    overrides: Optional[Dict[str, Callable[[RunPaths], object]]] = None,
) -> Dict[str, Callable[[RunPaths], object]]:
    runners: Dict[str, Callable[[RunPaths], object]] = {}
    for spec in MODULE_SPECS:
        if spec.name == "intelligence_web_view":
            continue

        def runner(paths: RunPaths, current=spec) -> object:
            if order is not None:
                order.append(current.name)
            if current.name == "minimum_useful_gate":
                payload = {
                    "schema_version": "1.0", "artifact_type": "minimum_useful_status",
                    "policy_id": "evidence_backed_daily_intelligence_v1",
                    "evaluated_at": "2026-08-28T01:02:03Z", "status": "available",
                    "system_health": {"state": "healthy", "reasons": []},
                    "product_usefulness": {"state": "useful", "reasons": []},
                    "overall_status": "healthy", "minimum_useful": True,
                    "criteria": {"fixture": {"passed": True}},
                    "asset_class_coverage": {"passed": True},
                    "explicit_limitations": [], "provenance_integrity": True,
                    "freshness_integrity": True,
                    "source_artifact_references": [{"artifact": "fixture.json", "run_id": "fixture", "generated_at": "2026-08-28T01:02:03Z"}],
                    "verified_latest_session_assets_counted": 0,
                }
                _write_json(paths.artifact("minimum_useful_status.json"), payload)
                _write_json(paths.data_directory / "minimum_useful_status.json", payload)
                return payload
            for filename in current.outputs:
                target = paths.artifact(filename)
                if filename.endswith(".md"):
                    target.write_text("# Daily Market Intelligence\n", encoding="utf-8")
                else:
                    _write_json(target, _artifact_payload(filename))
            if current.name == "grounded_ai_brief":
                return {
                    "generation_metadata": {
                        "generation_mode": "deterministic_fallback",
                        "generation_status": "fallback",
                        "generated_at": "2026-08-28T01:02:03Z",
                        "freshness_status": "current",
                        "validation_status": "validated",
                        "provider": None,
                        "fallback_reason": "no_provider_configured",
                    }
                }
            return None

        runners[spec.name] = runner
    if overrides:
        runners.update(overrides)
    return runners


def _run(tmp_path: Path, runners) -> tuple[dict, Path, Path]:
    output = tmp_path / "output"
    docs = tmp_path / "docs"
    manifest = run_daily_orchestration(
        output_directory=output,
        docs_directory=docs,
        runners=runners,
        clock=lambda: FIXED_NOW,
    )
    return manifest, output, docs


def test_full_successful_run_generates_manifest_and_approved_artifacts(
    tmp_path: Path,
) -> None:
    manifest, output, docs = _run(tmp_path, _successful_runners())

    assert manifest["status"] == "complete"
    assert manifest["run_id"].startswith("run_20260828T010203Z_orchestration_")
    assert manifest["execution_timestamp"] == "2026-08-28T01:02:03Z"
    assert manifest["freshness_status"] == "current"
    assert manifest["age_seconds"] == 0.0
    assert manifest["execution_order"] == list(EXECUTION_ORDER)
    assert all(module["status"] == "success" for module in manifest["modules"])
    assert not manifest["failures"]
    assert manifest["schema_version"] == "1.1"
    assert manifest["product_usefulness"]["minimum_useful"] is True
    assert (output / "run_manifest.json").is_file()
    assert (docs / "data" / "run_manifest.json").is_file()
    assert set(manifest["publication"]["published_files"]).issubset(
        set(APPROVED_PUBLIC_FILES)
    )
    assert (docs / "intelligence.html").is_file()
    grounded = next(
        module for module in manifest["modules"]
        if module["name"] == "grounded_ai_brief"
    )
    assert grounded["generation_metadata"] == {
        "generation_mode": "deterministic_fallback",
        "generation_status": "fallback",
        "generated_at": "2026-08-28T01:02:03Z",
        "freshness_status": "current",
        "validation_status": "validated",
        "provider": None,
        "fallback_reason": "no_provider_configured",
    }


def test_partial_failure_isolated_and_soft_consumer_continues(tmp_path: Path) -> None:
    def fail_calendar(paths: RunPaths) -> None:
        del paths
        raise RuntimeError("calendar endpoint timeout")

    manifest, output, _ = _run(
        tmp_path,
        _successful_runners(overrides={"calendar": fail_calendar}),
    )
    modules = {item["name"]: item for item in manifest["modules"]}

    assert manifest["status"] == "partial"
    assert modules["calendar"]["status"] == "failed"
    assert modules["evidence_consolidation"]["status"] == "success"
    assert any(
        "Soft dependency calendar" in warning
        for warning in modules["evidence_consolidation"]["warnings"]
    )
    assert (output / "daily_intelligence.json").is_file()
    assert any(item["module"] == "calendar" for item in manifest["failures"])


def test_grounded_brief_failure_records_explicit_unavailable_metadata(
    tmp_path: Path,
) -> None:
    def fail_grounded_brief(paths: RunPaths) -> None:
        del paths
        raise RuntimeError("provider response must not enter public metadata")

    manifest, _, _ = _run(
        tmp_path,
        _successful_runners(
            overrides={"grounded_ai_brief": fail_grounded_brief}
        ),
    )
    grounded = next(
        module for module in manifest["modules"]
        if module["name"] == "grounded_ai_brief"
    )

    assert grounded["status"] == "failed"
    assert grounded["generation_metadata"] == {
        "generation_mode": "unavailable",
        "generation_status": "failed",
        "generated_at": "2026-08-28T01:02:03Z",
        "freshness_status": "unavailable",
        "validation_status": "unavailable",
        "provider": None,
        "fallback_reason": "pipeline_failure",
    }
    assert "provider response" not in json.dumps(grounded["generation_metadata"])


def test_unavailable_source_artifact_does_not_block_pipeline(tmp_path: Path) -> None:
    def unavailable_calendar(paths: RunPaths) -> None:
        payload = _artifact_payload("economic_calendar.json", status="failed")
        payload.update(
            {
                "failure_type": "source_access_error",
                "retryable": True,
                "warnings": ["Economic calendar unavailable: HTTP 403"],
                "events": [],
                "source_timestamp": None,
                "retrieved_at": None,
                "age_seconds": None,
                "freshness_status": "unavailable",
                "freshness_basis": "unavailable",
            }
        )
        _write_json(paths.artifact("economic_calendar.json"), payload)

    manifest, _, _ = _run(
        tmp_path,
        _successful_runners(overrides={"calendar": unavailable_calendar}),
    )
    modules = {item["name"]: item for item in manifest["modules"]}

    assert modules["calendar"]["status"] == "unavailable"
    assert modules["evidence_consolidation"]["status"] == "success"
    assert modules["daily_intelligence"]["status"] == "success"
    assert manifest["status"] == "partial"
    assert manifest["freshness_status"] == "unavailable"
    assert "Economic calendar unavailable: HTTP 403" in modules["calendar"]["warnings"]
    for module in manifest["modules"]:
        assert {
            "source_timestamp",
            "retrieved_at",
            "generated_at",
            "age_seconds",
            "freshness_status",
        }.issubset(module)


def test_calendar_fallback_health_is_preserved_in_manifest(tmp_path: Path) -> None:
    def fallback_calendar(paths: RunPaths) -> None:
        payload = _artifact_payload("economic_calendar.json", status="partial")
        payload.update(
            {
                "failure_type": "primary_source_access_error",
                "retryable": True,
                "warnings": ["Primary unavailable; official fallback used."],
                "events": [],
                "sources": [
                    {
                        "source": "bls_release_calendar",
                        "status": "unavailable",
                        "failure_type": "primary_source_access_error",
                    },
                    {
                        "source": "bea_release_schedule",
                        "status": "available",
                        "failure_type": None,
                    },
                ],
            }
        )
        _write_json(paths.artifact("economic_calendar.json"), payload)

    manifest, _, _ = _run(
        tmp_path,
        _successful_runners(overrides={"calendar": fallback_calendar}),
    )
    calendar = next(
        module for module in manifest["modules"] if module["name"] == "calendar"
    )

    assert calendar["status"] == "partial"
    assert calendar["artifacts"][0]["source_health"] == [
        {
            "source": "bls_release_calendar",
            "status": "unavailable",
            "failure_type": "primary_source_access_error",
        },
        {
            "source": "bea_release_schedule",
            "status": "available",
            "failure_type": None,
        },
    ]


def test_provider_specific_failed_source_status_is_normalized_for_manifest(
    tmp_path: Path,
) -> None:
    def unavailable_market(paths: RunPaths) -> None:
        payload = _artifact_payload("market_snapshot.json", status="failed")
        payload.update(
            {
                "freshness_status": "unavailable",
                "freshness_basis": "unavailable",
                "source_timestamp": None,
                "age_seconds": None,
                "sources": [
                    {
                        "source_id": "src_market_spy",
                        "provider": "yahoo_finance",
                        "status": "failed",
                    }
                ],
            }
        )
        _write_json(paths.artifact("market_snapshot.json"), payload)

    manifest, _, _ = _run(
        tmp_path,
        _successful_runners(overrides={"market_data": unavailable_market}),
    )
    market = next(item for item in manifest["modules"] if item["name"] == "market_data")
    source = market["artifacts"][0]["source_health"][0]

    assert source["source"] == "src_market_spy"
    assert source["status"] == "unavailable"
    assert source["raw_status"] == "failed"


def test_artifact_generation_order_is_fixed(tmp_path: Path) -> None:
    observed: list[str] = []
    runners = _successful_runners(order=observed)

    def web_runner(paths: RunPaths) -> None:
        observed.append("intelligence_web_view")
        page = paths.docs_directory / "intelligence.html"
        script = paths.docs_directory / "assets" / "intelligence.js"
        page.parent.mkdir(parents=True, exist_ok=True)
        script.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("<!doctype html>", encoding="utf-8")
        script.write_text("'use strict';", encoding="utf-8")

    runners["intelligence_web_view"] = web_runner
    manifest, _, _ = _run(tmp_path, runners)

    assert observed == list(EXECUTION_ORDER)
    assert manifest["execution_order"] == observed
    assert [item["sequence"] for item in manifest["modules"]] == list(
        range(1, len(EXECUTION_ORDER) + 1)
    )


def test_publication_removes_unapproved_dynamic_files(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    data = docs / "data"
    data.mkdir(parents=True)
    (data / "raw_news_items.json").write_text("{}", encoding="utf-8")

    manifest = run_daily_orchestration(
        output_directory=tmp_path / "output",
        docs_directory=docs,
        runners=_successful_runners(),
        clock=lambda: FIXED_NOW,
    )

    assert not (data / "raw_news_items.json").exists()
    assert set(manifest["publication"]["published_files"]).issubset(
        set(APPROVED_PUBLIC_FILES)
    )
