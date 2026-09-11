from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.orchestration.pipeline import (
    APPROVED_DYNAMIC_FILES,
    APPROVED_PUBLIC_FILES,
    APPROVED_STATIC_FILES,
    MANIFEST_FILENAME,
)
from src.pages.generator import generate_page
from src.pages.intelligence_generator import (
    ARTIFACT_FILENAMES,
    generate_intelligence_page,
    run_intelligence_page_generator,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "daily_market_brief.yml"


def test_production_workflow_has_one_presentation_owner() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert workflow.count("python -m src.orchestration.pipeline") == 1
    for obsolete_command in (
        "python -m src.brief.generator",
        "python -m src.ai.analyst",
        "python -m src.pages.generator",
        "python -m src.brief.renderer_pipeline",
        "python -m src.pages.intelligence_generator",
    ):
        assert obsolete_command not in workflow
    for obsolete_artifact in (
        "src/output/daily_brief.md",
        "src/output/market_context.json",
    ):
        assert obsolete_artifact not in workflow
    assert "src/output/ai_market_brief.md" in workflow
    assert "--input src/output/daily_market_brief.md" in workflow
    assert "python -m src.telegram.bot" in workflow


def test_legacy_clis_are_retained_and_documented_as_deprecated() -> None:
    project = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    consolidation = (
        PROJECT_ROOT / "docs" / "pipeline-consolidation.md"
    ).read_text(encoding="utf-8")

    for entrypoint in (
        'market-brief-generate = "src.brief.generator:cli"',
        'market-brief-analyst = "src.ai.analyst:cli"',
        'market-brief-pages = "src.pages.generator:cli"',
    ):
        assert entrypoint in project
    assert "deprecated as production presentation paths" in readme
    assert "Deprecated for production; CLI retained" in consolidation
    assert 'market-brief-grounded-ai = "src.grounded_brief.pipeline:cli"' in project


def test_page_packaging_does_not_mutate_intelligence_artifacts(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    artifact_paths = {}
    for filename in ARTIFACT_FILENAMES:
        path = source / filename
        if filename.endswith(".json"):
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "artifact_type": Path(filename).stem,
                        "status": "available",
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
        else:
            path.write_text("# Deterministic brief\n", encoding="utf-8")
        artifact_paths[filename] = path
    before = {
        filename: hashlib.sha256(path.read_bytes()).hexdigest()
        for filename, path in artifact_paths.items()
    }

    statuses = run_intelligence_page_generator(
        output_path=tmp_path / "docs" / "intelligence.html",
        data_directory=tmp_path / "docs" / "data",
        script_target=tmp_path / "docs" / "assets" / "intelligence.js",
        artifact_paths=artifact_paths,
    )

    after = {
        filename: hashlib.sha256(path.read_bytes()).hexdigest()
        for filename, path in artifact_paths.items()
    }
    assert after == before
    assert set(statuses.values()) == {"packaged"}


def test_existing_market_page_and_intelligence_page_still_build() -> None:
    legacy_markdown = """# 今日市場焦點

Summary

## 美股
SPY
## Crypto
BTC
## 黃金
GOLD
## 外匯
EURUSD
## 今日風險
Data delay
"""
    snapshot = {
        "generated_at": "2026-08-28T00:00:00Z",
        "source": "test_source",
        "records": [],
    }

    market_page = generate_page(legacy_markdown, snapshot)
    intelligence_page = generate_intelligence_page()

    assert "<!doctype html>" in market_page
    assert 'id="crypto"' in market_page
    assert 'href="intelligence.html"' in market_page
    assert "<!doctype html>" in intelligence_page
    assert 'id="markets-content"' in intelligence_page
    assert (PROJECT_ROOT / "docs" / "index.html").is_file()


def test_deployment_allowlist_matches_canonical_presentation_contract() -> None:
    assert set(APPROVED_DYNAMIC_FILES) == set(ARTIFACT_FILENAMES) | {
        MANIFEST_FILENAME
    }
    assert set(APPROVED_STATIC_FILES) == {
        "previous-market-snapshot.json",
        "derivatives-shadow.json",
        "intelligence.html",
        "assets/intelligence.js",
    }
    assert set(APPROVED_PUBLIC_FILES) == {
        *(f"data/{name}" for name in APPROVED_DYNAMIC_FILES),
        *APPROVED_STATIC_FILES,
    }
