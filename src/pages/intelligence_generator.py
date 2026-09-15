"""Build the static shell and package artifacts for Intelligence View."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from string import Template
from typing import Dict, Mapping, Optional, Sequence
from src.pages.zh_hant import localize_shell


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
    "minimum_useful_status.json",
    "run_manifest.json",
)


class IntelligencePageGenerationError(ValueError):
    """Raised when the static Intelligence View shell cannot be built."""


def default_artifact_paths() -> Dict[str, Path]:
    return {name: OUTPUT_DIRECTORY / name for name in ARTIFACT_FILENAMES}


def generate_intelligence_page() -> str:
    page = localize_shell(PAGE_TEMPLATE.substitute(script_path="assets/intelligence.js"))
    # Keep the complete existing report and its stable anchors accessible.
    start = page.index('    <header class="hero">')
    end = page.index('  </main>', start)
    archive = page[start:end]
    archive = archive.replace('<h1>市場情報</h1>', '<h2>完整報告與資料狀態</h2>')
    page = page[:start] + READING_SHELL + '<details id="technical-report" class="section technical-report"><summary>查看證據、完整報告與技術資訊</summary><div class="technical-content">' + archive + '</div></details>\n' + page[end:]
    return page.replace('  </style>', READING_STYLES + '\n</style>')


READING_SHELL = '''
    <header class="reading-header">
      <p class="edition">DAILY RESEARCH · Beta</p>
      <h1>今日市場，一眼看懂。</h1>
      <p class="reading-intro">發生甚麼、為何重要、接下來留意甚麼。</p>
      <nav class="reading-nav" aria-label="簡報導覽"><a href="#reading-stories">市場重點</a><a href="#reading-watch">接下來要留意</a><a href="#technical-report">查看證據</a></nav>
    </header>
    <section class="reading-summary" aria-labelledby="reading-summary-title">
      <h2 id="reading-summary-title">今日市場一句話</h2>
      <div id="reading-summary" aria-live="polite" aria-busy="true"><p>正在讀取今日市場重點。</p></div>
    </section>
    <section class="reading-section" id="reading-stories"><h2 id="reading-stories-title">今日最重要的事</h2><div id="reading-stories-content" aria-busy="true"><p>正在讀取已驗證重點。</p></div></section>
    <section class="reading-section" id="reading-watch"><h2>接下來要留意</h2><ul id="reading-watch-content" aria-busy="true"><li>正在讀取觀察重點。</li></ul></section>
    <section class="reading-section" id="reading-regime"><h2>市場環境</h2><div id="reading-regime-content" aria-busy="true"><p>暫時無法判定。</p></div></section>
    <section class="reading-section reading-limitations" id="reading-limitations"><h2>已知限制</h2><ul id="reading-limitations-content" aria-busy="true"><li>正在確認資料涵蓋範圍。</li></ul><p class="reading-footnote">Beta 期間資料可能暫缺。內容供市場研究參考，不提供買賣建議。</p></section>
'''

READING_STYLES = '''
    .shell { width: min(860px, calc(100% - 40px)); }
    .reading-header { padding: 34px 0 20px; }
    .edition { color: var(--cyan); font-size: .72rem; letter-spacing: .16em; }
    .reading-header h1 { font-size: clamp(1.85rem, 5vw, 3rem); line-height: 1.3; letter-spacing: -.025em; }
    .reading-intro, .reading-footnote { color: var(--muted); }
    .reading-nav { display: flex; flex-wrap: wrap; gap: 8px 22px; font-size: .85rem; margin-top: 18px; }
    .reading-nav a { text-decoration: none; min-height: 44px; display: inline-flex; align-items: center; }
    .reading-summary { border-left: 3px solid var(--cyan); padding: 4px 0 4px 24px; margin: 18px 0 42px; }
    .reading-summary h2 { font-size: .85rem; color: var(--cyan); font-weight: 500; }
    #reading-summary p { font-size: clamp(1.12rem, 3vw, 1.45rem); line-height: 1.8; margin: 12px 0; }
    .reading-section { border-top: 1px solid var(--line); padding: 26px 0; }
    .reading-section h2 { font-size: 1.15rem; margin: 0 0 22px; }
    .reading-story { padding: 2px 0 24px; max-width: 720px; }
    .reading-story h3 { font-size: 1.1rem; margin: 0 0 8px; color: var(--text); }
    .reading-story p, #reading-watch-content li, #reading-regime-content p { line-height: 1.9; color: #d6e5ed; margin: 8px 0; }
    .reading-story a { font-size: .78rem; text-decoration: none; color: var(--muted); }
    #reading-summary[aria-busy="true"] { min-height: 48px; }
    #reading-stories-content[aria-busy="true"] { min-height: 405px; }
    #reading-watch-content[aria-busy="true"] { min-height: 150px; }
    #reading-regime-content[aria-busy="true"] { min-height: 92px; }
    #reading-limitations-content[aria-busy="true"] { min-height: 180px; }
    #reading-watch-content, #reading-limitations-content { padding-left: 22px; }
    #reading-limitations-content li { margin: 8px 0; color: var(--muted); }
    .reading-footnote { font-size: .8rem; }
    .technical-content { padding: 0 12px 20px; }
    .technical-report .hero { padding: 20px; }
    .technical-report h2 { line-height: 1.45; }
    @media (max-width: 560px) {
      .shell { width: calc(100% - 36px); }
      .topbar { margin-bottom: 0; }
      .brand { font-size: .66rem; letter-spacing: .05em; }
      .reading-header { padding-top: 18px; }
      .reading-summary { margin-top: 8px; padding-left: 16px; margin-bottom: 28px; }
      #reading-summary[aria-busy="true"] { min-height: 100px; }
      #reading-stories-content[aria-busy="true"] { min-height: 500px; }
      #reading-watch-content[aria-busy="true"] { min-height: 220px; }
      .reading-section { padding: 22px 0; }
      .technical-content { padding-left: 4px; padding-right: 4px; }
    }
'''


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
    content="以可追溯證據整理市場環境、跨資產觀察及風險，提供每日市場情報。"
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
    .research-banner { margin-top: 20px; padding: 16px; border-left: 3px solid var(--cyan); background: var(--surface-2); border-radius: 8px; }
    .research-banner p { margin: 4px 0; }
    .research-nav { display: flex; flex-wrap: wrap; gap: 8px 20px; margin-top: 18px; font-size: .85rem; }
    .research-nav a:focus-visible, summary:focus-visible { outline: 2px solid var(--cyan); outline-offset: 4px; }
    .trace-entry { margin: 10px 0; }
    .trace-entry code { display: block; padding: 5px 8px; margin-top: 4px; background: rgba(0,0,0,.15); border-radius: 4px; white-space: pre-wrap; }
    .explanation-label { font-size: .76rem; text-transform: uppercase; letter-spacing: .06em; color: var(--cyan); margin-top: 18px; }
    #derivatives-content .card p { font-size: .83rem; overflow-wrap: anywhere; }
    .shell > *, .card, .panel, .status-box, .section-head > * { min-width: 0; }
    .card, .panel, .hero, .badge, summary, .research-nav a { overflow-wrap: anywhere; }
    .badge { max-width: 100%; white-space: normal; }
    .section-head { flex-wrap: wrap; }
    .onboarding { margin-top: 18px; }
    .onboarding dt { color: var(--cyan); font-weight: 700; margin-top: 12px; }
    .onboarding dd { margin: 4px 0 0; color: var(--muted); }
    .product-flow { display: flex; flex-wrap: wrap; gap: 10px; padding: 0; list-style: none; }
    .product-flow li { border: 1px solid var(--line); border-radius: 8px; padding: 8px 12px; }
    .research-nav a { display: inline-flex; align-items: center; min-height: 44px; }
    .skip-link { position: absolute; left: -9999px; }
    .skip-link:focus { position: static; display: block; padding: 12px; }
    @media (max-width: 560px) {
      .card-grid, .market-grid, .status-grid, .brief-meta { grid-template-columns: minmax(0, 1fr); }
      .panel { padding: 18px; }
      .research-nav { gap: 4px 14px; }
      h1 { overflow-wrap: anywhere; }
      .trace-entry code { max-width: 100%; }
    }
  </style>
</head>
<body>
  <a class="skip-link" href="#executive-summary">Skip to daily research</a>
  <main class="shell">
    <div class="topbar">
      <div class="brand">AI Market Intelligence · Evidence View</div>
      <nav class="topnav" aria-label="Primary">
        <a href="index.html">Market Brief</a>
        <a href="intelligence.html" aria-current="page">Intelligence</a>
      </nav>
    </div>

    <header class="hero">
      <aside id="beta-status" class="onboarding" aria-label="Limited beta status">
        <h2>Limited Beta · 10.2 candidate</h2>
        <p>Readiness: conditional · Last validation: 2026-09-12 05:46 UTC</p>
        <details><summary>Beta release metadata</summary><p class="meta">Last validated deployed commit: <code>df01ee67902f521ced9d0e703a45a0a760032f87</code>. This identifies the validated baseline, not an assertion that this candidate has been deployed.</p></details>
        <div id="beta-live-status" aria-live="polite"><p>Current status unavailable; awaiting artifacts.</p></div>
        <p>Data availability may vary. Unavailable and partial data are shown explicitly. This system provides evidence-backed market intelligence, not trading recommendations or a promise of prediction.</p>
        <a href="https://github.com/froyo1015/AI-Market-Intelligence/issues/new" rel="noopener noreferrer">Send beta feedback on GitHub</a>
        <p class="meta">GitHub sign-in may be required. Feedback is public: do not include credentials, private account details or raw provider responses.</p>
      </aside>
      <p class="brand">Daily Intelligence Overview</p>
      <h1>Market Intelligence</h1>
      <p class="lede">Validated market relationships, current-condition regime and observable risks with a complete evidence trail.</p>
      <div id="product-overview" class="onboarding">
        <h2>Market research you can trace</h2>
        <p>AI Market Intelligence brings market observations, events and their supporting evidence into a daily research report.</p>
        <ol class="product-flow" aria-label="Evidence-first architecture">
          <li>1. Data — recorded observations</li><li>2. Evidence — validated, traceable records</li><li>3. Intelligence — structured context</li>
        </ol>
        <p class="meta">AI writes from validated intelligence when available; deterministic fallback is labeled. It does not choose the ranked stories, discover new facts, forecast prices or provide investment advice.</p>
      </div>
      <div class="research-banner" aria-live="polite">
        <strong id="research-status">Daily research status unavailable</strong>
        <p id="research-updated" class="muted">Last update unavailable</p>
        <p class="meta">Research context only. Source freshness and report generation time are different checks.</p>
        <div id="minimum-useful-status" class="meta" aria-label="產品可用性狀態">
          <p>系統狀態：暫無資料</p><p>今日情報：暫無資料</p><p>已知限制：暫無資料</p>
        </div>
      </div>
      <div class="status-grid" aria-label="Intelligence status">
        <div class="status-box"><span>Generated</span><strong id="generated-at" class="loading">Loading…</strong></div>
        <div class="status-box"><span>Data status</span><strong id="data-status" class="loading">Loading…</strong></div>
        <div class="status-box"><span>Freshness</span><strong id="freshness-status" class="loading">Loading…</strong></div>
        <div class="status-box"><span>Validation</span><strong id="validation-status" class="loading">Loading…</strong></div>
      </div>
      <nav class="research-nav" aria-label="Research sections">
        <a href="#executive-summary">Daily Intelligence</a><a href="#markets">Market Overview</a>
        <a href="#regime">Macro &amp; Risk</a><a href="#risks">Risks Ahead</a>
        <a href="#derivatives-shadow">Crypto / Derivatives Shadow</a><a href="#methodology">Evidence &amp; Methodology</a>
      </nav>
    </header>

    <section class="section panel" id="methodology">
      <details class="onboarding">
        <summary>New here? How to read this report</summary>
        <p>Start with status and Executive Summary. Read What Changed, then Why It Matters. Review risks and open Evidence Trail to inspect references.</p>
        <dl>
          <dt>Freshness</dt><dd>Current meets the recorded freshness policy; stale is outside that window. Unknown means timing cannot be established. Unavailable means usable data is absent. A new report timestamp does not make old observations current.</dd>
          <dt>Validation</dt><dd>Validated means the record passed the applicable input and reference checks. It is not a guarantee of market truth or future outcomes.</dd>
          <dt>Shadow Validated</dt><dd>Derivatives records passed shadow checks but are not used for AI decisions. Passing readiness does not enable production.</dd>
          <dt>Missing modules</dt><dd>Optional history or shadow data may be unavailable while other sections remain usable. No missing evidence is replaced with invented content.</dd>
        </dl>
        <a href="#audit">Open Evidence Trail below</a>
      </details>
      <div id="onboarding-state" aria-live="polite"></div>
    </section>

    <div id="load-notices" class="section" aria-live="polite"></div>

    <section class="section panel" id="executive-summary">
      <h2>1. Executive Summary</h2>
      <div id="executive-content"><p class="empty">Validated stories unavailable.</p></div>
    </section>
    <section class="section panel" id="what-changed">
      <h2>2. What Changed</h2>
      <p class="meta">Observed market snapshot differences only. No causal interpretation. Recorded status does not imply live data.</p>
      <div id="changes-content"><p class="empty">Previous available run unavailable.</p></div>
    </section>

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
      <p class="meta">來源與報告中的原始敘述可能保留英文，方便核對；介面不會重新撰寫或補充市場事實。引用 ID 與時間維持原樣。</p>
    </section>

    <section class="section panel" id="top-intelligence">
      <div class="section-head"><div><h2>3. Why It Matters</h2><p>Today's Top Market Intelligence · Existing validated explanations and evidence</p></div></div>
      <p class="meta">Read the observation, why it matters, then what to monitor. Order and explanations come from validated artifacts; the page does not re-rank them. Scores are selection scores, not probabilities.</p>
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

    <section class="section panel" id="markets">
      <div class="section-head"><div><h2>4. Market Structure</h2><p>Equity · Macro · Crypto · Existing market snapshots</p></div></div>
      <div id="markets-content" class="market-grid"><p class="empty loading">Loading market observations…</p></div>
    </section>

    <section class="section panel" id="derivatives-shadow">
      <div class="section-head"><div><h2>Derivatives Shadow</h2><p>Shadow Validated · Not used for AI decisions</p></div></div>
      <p class="notice">Research preview only · Production disabled. Stale measurements are historical observations, not current evidence for decisions.</p>
      <div id="derivatives-content" class="card-grid"><p class="empty">Derivatives unavailable.</p></div>
    </section>

    <section class="section panel" id="risks">
      <div class="section-head"><div><h2>5. Risks Ahead</h2><p>Existing risk monitor: upcoming events, observed stress and data quality warnings</p></div></div>
      <div id="risks-content"><p class="empty loading">Loading observable risks…</p></div>
      <div id="report-quality-content"></div>
    </section>
    <section class="section" id="audit">
      <h2>6. Evidence Trail</h2>
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
