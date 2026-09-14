import copy
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_derivatives_readiness import sample
from src.intelligence import evidence_boundary
from src.shadow.derivatives.archive import append
from src.shadow.derivatives.dashboard import project
from src.pages.derivatives_schema import validate_public
from src.orchestration.pipeline import _published_files, APPROVED_PUBLIC_FILES


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence_boundary, "SHADOW_ROOT", tmp_path)
    return tmp_path / "archive"


def render(payload, now="2026-09-10T00:03:00.123Z"):
    script = Path("src/pages/static/intelligence.js").resolve()
    code = "const v=require(process.argv[1]); console.log(v.derivativesLines(JSON.parse(process.argv[2]),Date.parse(process.argv[3])).join('\\n'));"
    return subprocess.check_output(["node", "-e", code, str(script), json.dumps(payload), now], text=True)


def test_available_rendering_and_safe_projection(root):
    append(root, sample(10, archive_request=True))
    p = project(root, "2026-09-10T00:03:00.123Z")
    assert validate_public(p)
    text = render(p)
    assert "BTC Perpetual" in text and "ETH Perpetual" in text
    assert "Funding rate: 0.0001" in text and "Open interest: 123.45" in text
    assert "Freshness: current" in text and "Provenance: complete" in text
    assert "production_enabled: false" in text
    assert all(word not in json.dumps(p).lower() for word in ("body_base64", "receipt", "transport", "secret", "bullish", "bearish", "prediction"))


def test_stale_rendering_and_browser_reaging(root):
    append(root, sample(10, archive_request=True))
    p = project(root, "2026-09-11T00:03:00.123Z")
    assert all(x["freshness_status"] == "stale" for x in p["measurements"])
    assert "Freshness: stale" in render(p, "2026-09-11T00:03:00.123Z")
    p = project(root, "2026-09-10T00:03:00.123Z")
    assert "Freshness: current" not in render(p, "2026-09-12T00:03:00.123Z")


def test_unavailable_rendering(root):
    p = project(root, "2026-09-10T00:03:00.123Z")
    assert validate_public(p)
    assert "Funding rate: unavailable" in render(p)
    assert "Derivatives unavailable" in render(None)


@pytest.mark.parametrize("field", ["receipts", "raw_response", "api_key", "transport", "bullish"])
def test_artifact_allowlist_rejects_extras(root, tmp_path, field):
    append(root, sample(10, archive_request=True))
    p = project(root, "2026-09-10T00:03:00.123Z")
    p["measurements"][0][field] = "forbidden"
    assert not validate_public(p)
    target = tmp_path / "docs/derivatives-shadow.json"
    target.parent.mkdir()
    target.write_text(json.dumps(p))
    _published_files(SimpleNamespace(docs_directory=target.parent))
    assert not target.exists()


def test_publication_preserves_only_valid_projection(root, tmp_path):
    append(root, sample(10, archive_request=True))
    p = project(root, "2026-09-10T00:03:00.123Z")
    target = tmp_path / "docs/derivatives-shadow.json"
    target.parent.mkdir()
    target.write_text(json.dumps(p))
    published, _ = _published_files(SimpleNamespace(docs_directory=target.parent))
    assert "derivatives-shadow.json" in published
    assert not any("receipt" in x or "archive" in x for x in APPROVED_PUBLIC_FILES)
    bad = copy.deepcopy(p)
    bad["readiness"]["production_enabled"] = True
    assert not validate_public(bad)


def test_render_dom_and_no_directional_language(root):
    append(root, sample(10, archive_request=True))
    p = project(root, "2026-09-10T00:03:00.123Z")
    code = '''const v=require(process.argv[1]);
    const box={textContent:'', children:[], appendChild(x){this.children.push(x)}};
    const doc={getElementById(id){return id==='derivatives-content'?box:null},
      createElement(tag){return {tag,textContent:'',className:'',children:[],appendChild(x){this.children.push(x)}}}};
    v.renderDerivatives(doc,JSON.parse(process.argv[2]));
    const nodes=box.children.flatMap(x=>x.children);
    if(!nodes.some(x=>x.textContent==='BTC 永續合約'))process.exit(1);
    console.log(nodes.map(x=>x.textContent).join('\\n'));'''
    text = subprocess.check_output(["node", "-e", code, str(Path("src/pages/static/intelligence.js").resolve()), json.dumps(p)], text=True)
    assert all(x not in text.lower() for x in ("bullish", "bearish", "buy", "sell", "predict"))
