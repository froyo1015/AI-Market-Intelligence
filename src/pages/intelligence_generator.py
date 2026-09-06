"""Build the static shell and package artifacts for Intelligence View."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from string import Template
from typing import Dict, Mapping, Optional, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIRECTORY = PROJECT_ROOT / "src" / "output"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "docs" / "intelligence.html"
DEFAULT_DATA_DIRECTORY = PROJECT_ROOT / "docs" / "data"
DEFAULT_SCRIPT_SOURCE = PROJECT_ROOT / "src" / "pages" / "static" / "intelligence.js"
DEFAULT_SCRIPT_TARGET = PROJECT_ROOT / "docs" / "assets" / "intelligence.js"
ARTIFACT_FILENAMES = (
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
    "run_manifest.json",
)


class IntelligencePageGenerationError(ValueError):
    """Raised when the static Intelligence View shell cannot be built."""


def default_artifact_paths() -> Dict[str, Path]:
    return {name: OUTPUT_DIRECTORY / name for name in ARTIFACT_FILENAMES}


def generate_intelligence_page() -> str:
    return PAGE_TEMPLATE.substitute(script_path="assets/intelligence.js")


def package_artifacts(
    artifact_paths: Mapping[str, Path],
    data_directory: Path,
) -> Dict[str, str]:
    data_directory.mkdir(parents=True, exist_ok=True)
    statuses: Dict[str, str] = {}
    for filename in ARTIFACT_FILENAMES:
        source = artifact_paths.get(filename)
        target = data_directory / filename
        if source is None or not source.is_file():
            if target.exists():
                target.unlink()
            statuses[filename] = "missing"
            continue
        content = source.read_text(encoding="utf-8")
        if filename.endswith(".json"):
            try:
                payload = json.loads(content)
            except json.JSONDecodeError:
                if target.exists():
                    target.unlink()
                statuses[filename] = "invalid"
                continue
            if not isinstance(payload, dict):
                if target.exists():
                    target.unlink()
                statuses[filename] = "invalid"
                continue
            content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        _atomic_write(target, content)
        statuses[filename] = "packaged"
    return statuses


def run_intelligence_page_generator(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    data_directory: Path = DEFAULT_DATA_DIRECTORY,
    script_source: Path = DEFAULT_SCRIPT_SOURCE,
    script_target: Path = DEFAULT_SCRIPT_TARGET,
    artifact_paths: Optional[Mapping[str, Path]] = None,
) -> Dict[str, str]:
    if not script_source.is_file():
        raise IntelligencePageGenerationError(
            f"Intelligence View script not found: {script_source}"
        )
    page = generate_intelligence_page()
    _atomic_write(output_path, page)
    _atomic_write(script_target, script_source.read_text(encoding="utf-8"))
    return package_artifacts(
        artifact_paths if artifact_paths is not None else default_artifact_paths(),
        data_directory,
    )


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(content, encoding="utf-8")
    temporary_path.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the static GitHub Pages Intelligence View."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIRECTORY)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    statuses = run_intelligence_page_generator(
        output_path=args.output,
        data_directory=args.data_dir,
    )
    packaged = sum(value == "packaged" for value in statuses.values())
    print(
        f"Wrote Intelligence View to {args.output}; "
        f"packaged={packaged}, unavailable={len(statuses) - packaged}"
    )
    return 0


def cli() -> None:
    raise SystemExit(main())


PAGE_TEMPLATE = Template(
    """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <meta
    http-equiv="Content-Security-Policy"
    content="default-src 'none'; script-src 'self'; connect-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
  >
  <meta
    name="description"
    content="Evidence-linked market regime, cross-asset observations and risk monitoring."
  >
  <title>Market Intelligence View</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #071019;
      --surface: rgba(15, 28, 40, 0.92);
      --surface-2: rgba(20, 40, 55, 0.82);
      --line: rgba(153, 190, 216, 0.16);
      --text: #eef7fb;
      --muted: #9eb3c2;
      --cyan: #5ee2d0;
      --blue: #70a7ff;
      --amber: #f3c969;
      --red: #ff8b92;
      --green: #7de4b4;
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      background:
        radial-gradient(circle at 12% 0%, rgba(22, 117, 129, 0.24), transparent 32rem),
        radial-gradient(circle at 88% 12%, rgba(67, 79, 151, 0.22), transparent 34rem),
        var(--bg);
      font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
        "Segoe UI", "PingFang TC", "Noto Sans TC", sans-serif;
      line-height: 1.55;
    }
    a { color: var(--cyan); }
    code { color: #cbe7f5; overflow-wrap: anywhere; }
    .shell { width: min(1180px, calc(100% - 32px)); margin: auto; padding: 32px 0 72px; }
    .topbar { display: flex; justify-content: space-between; gap: 16px; align-items: center; margin-bottom: 18px; }
    .brand { color: var(--cyan); font-size: .78rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }
    .topnav { display: flex; flex-wrap: wrap; gap: 8px; }
    .topnav a { padding: 8px 12px; border: 1px solid var(--line); border-radius: 999px; color: var(--muted); text-decoration: none; }
    .topnav a[aria-current="page"] { color: var(--text); border-color: rgba(94,226,208,.5); }
    .hero, .panel, .card { border: 1px solid var(--line); background: var(--surface); box-shadow: 0 20px 60px rgba(0,0,0,.2); }
    .hero { padding: clamp(24px, 5vw, 52px); border-radius: 24px; }
    h1 { margin: 6px 0 10px; font-size: clamp(2.2rem, 6vw, 4.8rem); line-height: 1; letter-spacing: -.055em; }
    .lede { max-width: 760px; margin: 0; color: #c7d9e4; }
    .status-grid, .market-grid, .card-grid { display: grid; gap: 12px; }
    .status-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top: 26px; }
    .status-box { padding: 13px 14px; border: 1px solid rgba(94,226,208,.16); border-radius: 12px; background: rgba(5,14,22,.38); min-width: 0; }
    .status-box span { display: block; color: var(--muted); font-size: .7rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
    .status-box strong { display: block; margin-top: 5px; overflow-wrap: anywhere; }
    .section { margin-top: 18px; }
    .panel { padding: 24px; border-radius: 18px; }
    .section-head { display: flex; justify-content: space-between; gap: 16px; align-items: end; margin-bottom: 15px; }
    .section-head h2 { margin: 0; font-size: 1.22rem; }
    .section-head p { margin: 0; color: var(--muted); font-size: .86rem; }
    .card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .market-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .card { min-width: 0; padding: 17px; border-radius: 14px; background: var(--surface-2); box-shadow: none; }
    .card h3 { margin: 0 0 9px; font-size: 1rem; }
    .card p { margin: 7px 0; color: #d6e5ed; }
    .meta { color: var(--muted) !important; font-size: .8rem; overflow-wrap: anywhere; }
    .metric { font-variant-numeric: tabular-nums; font-size: 1.3rem; font-weight: 750; }
    .badge { display: inline-flex; align-items: center; padding: 4px 9px; border: 1px solid var(--line); border-radius: 999px; font-family: ui-monospace, monospace; font-size: .72rem; }
    .badge.available, .badge.current, .badge.validated { color: var(--green); border-color: rgba(125,228,180,.32); }
    .badge.partial, .badge.stale, .badge.medium { color: var(--amber); border-color: rgba(243,201,105,.34); }
    .badge.unavailable, .badge.failed, .badge.high { color: var(--red); border-color: rgba(255,139,146,.34); }
    .notice { padding: 14px 16px; border: 1px solid rgba(243,201,105,.25); border-radius: 12px; color: #f7dfa3; background: rgba(121,87,21,.14); }
    .brief-meta { grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 0 0 18px; }
    .brief-body { max-width: 860px; color: #d6e5ed; }
    .brief-body h3, .brief-body h4, .brief-body h5, .brief-body h6 { margin: 1.35em 0 .45em; color: var(--text); line-height: 1.25; }
    .brief-body h3:first-child { margin-top: 0; }
    .brief-body p { margin: .7em 0; }
    .brief-body ul { margin: .65em 0; padding-left: 1.35em; }
    .brief-reference { color: var(--muted); font-family: ui-monospace, monospace; font-size: .78rem; overflow-wrap: anywhere; }
    .fallback-note { margin: 0 0 18px; padding: 11px 13px; border-left: 3px solid var(--amber); color: #f7dfa3; background: rgba(121,87,21,.12); }
    .empty { margin: 0; color: var(--muted); }
    .refs { margin: 11px 0 0; padding: 0; list-style: none; color: var(--muted); font-family: ui-monospace, monospace; font-size: .72rem; }
    .refs li { margin-top: 4px; overflow-wrap: anywhere; }
    details { border: 1px solid var(--line); border-radius: 14px; background: rgba(5,14,22,.34); }
    summary { cursor: pointer; padding: 16px; font-weight: 750; }
    .audit-body { padding: 0 16px 16px; }
    .audit-group { margin-top: 16px; }
    .audit-group h3 { margin: 0 0 8px; font-size: .9rem; }
    .audit-list { margin: 0; padding-left: 18px; color: var(--muted); font-size: .78rem; overflow-wrap: anywhere; }
    .loading { animation: pulse 1.4s ease-in-out infinite; }
    @keyframes pulse { 50% { opacity: .5; } }
    @media (max-width: 860px) {
      .status-grid, .market-grid, .brief-meta { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .card-grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 560px) {
      .shell { width: min(100% - 20px, 1180px); padding-top: 14px; }
      .topbar { align-items: flex-start; flex-direction: column; }
      .hero, .panel { border-radius: 16px; }
      .status-grid, .market-grid, .brief-meta { grid-template-columns: 1fr; }
    }
    @media (prefers-reduced-motion: reduce) {
      html { scroll-behavior: auto; }
      .loading { animation: none; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <div class="topbar">
      <div class="brand">AI Market Intelligence · Evidence View</div>
      <nav class="topnav" aria-label="Primary">
        <a href="index.html">Market Brief</a>
        <a href="intelligence.html" aria-current="page">Intelligence</a>
      </nav>
    </div>

    <header class="hero">
      <p class="brand">Daily Intelligence Overview</p>
      <h1>Market Intelligence</h1>
      <p class="lede">Validated market relationships, current-condition regime and observable risks with a complete evidence trail.</p>
      <div class="status-grid" aria-label="Intelligence status">
        <div class="status-box"><span>Generated</span><strong id="generated-at" class="loading">Loading…</strong></div>
        <div class="status-box"><span>Data status</span><strong id="data-status" class="loading">Loading…</strong></div>
        <div class="status-box"><span>Freshness</span><strong id="freshness-status" class="loading">Loading…</strong></div>
        <div class="status-box"><span>Validation</span><strong id="validation-status" class="loading">Loading…</strong></div>
      </div>
    </header>

    <div id="load-notices" class="section" aria-live="polite"></div>

    <section class="section panel" id="ai-brief">
      <div class="section-head"><div><p class="brand">AI MARKET BRIEF</p><h2>AI Market Brief</h2><p>Validated narrative presentation of canonical intelligence artifacts</p></div></div>
      <div class="status-grid brief-meta" aria-label="AI brief publication metadata">
        <div class="status-box"><span>Generation Mode</span><strong id="ai-brief-mode" class="loading">Loading…</strong></div>
        <div class="status-box"><span>Generated At</span><strong id="ai-brief-generated-at" class="loading">Loading…</strong></div>
        <div class="status-box"><span>Freshness</span><strong id="ai-brief-freshness" class="loading">Loading…</strong></div>
        <div class="status-box"><span>Validation</span><strong id="ai-brief-validation" class="loading">Loading…</strong></div>
      </div>
      <p id="ai-brief-note" class="fallback-note" hidden></p>
      <div id="ai-brief-content" class="brief-body" aria-live="polite"><p class="empty loading">Loading validated brief…</p></div>
    </section>

    <section class="section panel" id="top-intelligence">
      <div class="section-head"><div><h2>Today's Top Market Intelligence</h2><p>Current, validated and evidence-linked priorities</p></div></div>
      <div id="top-intelligence-content" class="card-grid"><p class="empty loading">Loading current priorities…</p></div>
    </section>

    <section class="section panel" id="regime">
      <div class="section-head"><div><h2>Market Regime</h2><p>Current observed conditions only</p></div></div>
      <div id="regime-content"><p class="empty loading">Loading validated regime…</p></div>
    </section>

    <section class="section panel" id="signals">
      <div class="section-head"><div><h2>Cross Asset Signals</h2><p>Observed deterministic relationships only</p></div></div>
      <div id="signals-content" class="card-grid"><p class="empty loading">Loading observed relationships…</p></div>
    </section>

    <section class="section panel" id="risks">
      <div class="section-head"><div><h2>Risk Monitor</h2><p>Scheduled, data-quality and observed stress conditions</p></div></div>
      <div id="risks-content"><p class="empty loading">Loading observable risks…</p></div>
    </section>

    <section class="section panel" id="markets">
      <div class="section-head"><div><h2>Market Overview</h2><p>Existing market and macro snapshots</p></div></div>
      <div id="markets-content" class="market-grid"><p class="empty loading">Loading market observations…</p></div>
    </section>

    <section class="section" id="audit">
      <details>
        <summary>Evidence / Audit</summary>
        <div id="audit-content" class="audit-body"><p class="empty loading">Loading provenance…</p></div>
      </details>
    </section>
  </main>
  <script src="$script_path" defer></script>
</body>
</html>
"""
)


if __name__ == "__main__":
    cli()
