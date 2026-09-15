from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from src.pages.intelligence_generator import (
    ARTIFACT_FILENAMES,
    generate_intelligence_page,
    run_intelligence_page_generator,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_static_shell_has_dynamic_artifact_contract_and_safe_csp() -> None:
    page = generate_intelligence_page()

    assert "<!doctype html>" in page
    assert 'id="ai-brief-content"' in page
    assert 'id="ai-brief-mode"' in page
    assert 'id="ai-brief-generated-at"' in page
    assert 'id="ai-brief-freshness"' in page
    assert 'id="ai-brief-validation"' in page
    assert 'id="top-intelligence-content"' in page
    assert 'id="regime-content"' in page
    assert 'id="signals-content"' in page
    assert 'id="risks-content"' in page
    assert 'id="markets-content"' in page
    assert 'id="audit-content"' in page
    assert 'id="minimum-useful-status"' in page
    assert 'src="assets/intelligence.js"' in page
    assert "script-src 'self'" in page
    assert "connect-src 'self'" in page
    assert "unpkg" not in page
    assert "react" not in page.lower()
    assert page.index('id="ai-brief"') < page.index('id="top-intelligence"')
    assert page.index('id="top-intelligence"') < page.index('id="regime"')
    assert page.index('id="regime"') < page.index('id="signals"')
    assert page.index('id="signals"') < page.index('id="markets"')
    assert page.index('id="markets"') < page.index('id="risks"')
    assert page.index('id="markets"') < page.index('id="audit"')


def test_frontend_has_no_llm_execution_or_html_injection_path() -> None:
    script = (
        PROJECT_ROOT / "src" / "pages" / "static" / "intelligence.js"
    ).read_text(encoding="utf-8")

    assert "innerHTML" not in script
    assert "insertAdjacentHTML" not in script
    assert "eval(" not in script
    assert "Function(" not in script
    assert "llm_adapter" not in script
    assert "grounded_brief" not in script
    assert "api.openai.com" not in script
    assert 'aiBrief: ["data/ai_market_brief.md", "text"]' in script
    assert 'runManifest: ["data/run_manifest.json", "json"]' in script
    assert 'minimumUseful: ["data/minimum_useful_status.json", "json"]' in script


def test_ai_brief_web_integration_contract_is_documented() -> None:
    contract = PROJECT_ROOT / "docs" / "ai-brief-web-integration.md"
    text = contract.read_text(encoding="utf-8")

    assert "deterministic_fallback" in text
    assert "AI Market Brief unavailable." in text
    assert "textContent" in text
    assert "[refs: ...]" in text


def test_generator_packages_valid_artifacts_and_handles_missing_inputs(
    tmp_path: Path,
) -> None:
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    intelligence = source_directory / "daily_intelligence.json"
    intelligence.write_text(
        json.dumps({"artifact_type": "daily_intelligence"}),
        encoding="utf-8",
    )
    data_directory = tmp_path / "docs" / "data"
    stale_target = data_directory / "market_regime.json"
    stale_target.parent.mkdir(parents=True)
    stale_target.write_text('{"old": true}', encoding="utf-8")
    output_path = tmp_path / "docs" / "intelligence.html"
    script_target = tmp_path / "docs" / "assets" / "intelligence.js"

    statuses = run_intelligence_page_generator(
        output_path=output_path,
        data_directory=data_directory,
        script_target=script_target,
        artifact_paths={"daily_intelligence.json": intelligence},
    )

    assert output_path.is_file()
    assert script_target.is_file()
    assert statuses["daily_intelligence.json"] == "packaged"
    assert json.loads(
        (data_directory / "daily_intelligence.json").read_text(encoding="utf-8")
    ) == {"artifact_type": "daily_intelligence"}
    assert statuses["market_regime.json"] == "missing"
    assert not stale_target.exists()
    assert set(statuses) == set(ARTIFACT_FILENAMES)


def test_generator_rejects_invalid_json_from_public_data_directory(
    tmp_path: Path,
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("not-json", encoding="utf-8")
    data_directory = tmp_path / "docs" / "data"

    statuses = run_intelligence_page_generator(
        output_path=tmp_path / "docs" / "intelligence.html",
        data_directory=data_directory,
        script_target=tmp_path / "docs" / "assets" / "intelligence.js",
        artifact_paths={"market_regime.json": bad},
    )

    assert statuses["market_regime.json"] == "invalid"
    assert not (data_directory / "market_regime.json").exists()


def test_javascript_view_model_missing_partial_unavailable_and_valid_states() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not available for static JavaScript checks")
    script = PROJECT_ROOT / "tests" / "js" / "intelligence_view.test.js"

    result = subprocess.run(
        [node, str(script)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "intelligence-view tests passed" in result.stdout
