"""Convert the generated analyst Markdown into a safe static HTML page."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from src.data.data_quality import build_data_quality_context, format_quality_counts


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BRIEF_PATH = PROJECT_ROOT / "src" / "output" / "ai_market_brief.md"
DEFAULT_SNAPSHOT_PATH = PROJECT_ROOT / "src" / "output" / "market_snapshot.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "docs" / "index.html"

SECTION_CONFIGURATION: Sequence[Tuple[str, str, str]] = (
    ("美股", "equities", "blue"),
    ("Crypto", "crypto", "violet"),
    ("黃金", "gold", "gold"),
    ("外匯", "forex", "teal"),
    ("今日風險", "risk", "red"),
)

CITATION_PATTERN = re.compile(
    r"\[來源:\s*(?P<source>.*?);\s*timestamp:\s*(?P<timestamp>.*?)\]"
)


class PageGenerationError(ValueError):
    """Raised when generated inputs cannot produce the required page."""


def load_snapshot(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PageGenerationError(f"snapshot not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PageGenerationError(f"snapshot is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PageGenerationError("snapshot root must be a JSON object")
    return payload


def generate_page(markdown: str, snapshot: Mapping[str, Any]) -> str:
    """Render the known analyst report structure without executing HTML input."""
    summary_lines, parsed_sections = _parse_markdown(markdown)
    missing_sections = [
        heading
        for heading, _, _ in SECTION_CONFIGURATION
        if heading not in parsed_sections
    ]
    if missing_sections:
        raise PageGenerationError(
            f"analyst brief is missing sections: {', '.join(missing_sections)}"
        )

    generated_at = _text(snapshot.get("generated_at"))
    report_date = generated_at[:10] if len(generated_at) >= 10 else "未知"
    quality_context = build_data_quality_context(snapshot)
    quality_summary = quality_context["summary"]
    data_time_range = (
        f"{quality_summary['earliest_data_time']} → "
        f"{quality_summary['latest_data_time']}"
    )
    sources = _collect_sources(markdown, snapshot)
    source_html = "".join(
        f"<li><span class=\"source-dot\" aria-hidden=\"true\"></span>"
        f"{html.escape(source)}</li>"
        for source in sources
    )
    sections_html = "".join(
        _render_section(
            heading,
            section_id,
            accent,
            parsed_sections[heading],
        )
        for heading, section_id, accent in SECTION_CONFIGURATION
    )

    return PAGE_TEMPLATE.substitute(
        report_date=html.escape(report_date),
        generated_at=html.escape(generated_at),
        data_time_range=html.escape(data_time_range),
        freshness_summary=html.escape(
            format_quality_counts(quality_summary["counts"])
        ),
        summary_html=_render_lines(summary_lines),
        sections_html=sections_html,
        source_html=source_html,
    )


def run_generator(
    brief_path: Path = DEFAULT_BRIEF_PATH,
    snapshot_path: Path = DEFAULT_SNAPSHOT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> str:
    try:
        markdown = brief_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PageGenerationError(f"analyst brief not found: {brief_path}") from exc
    snapshot = load_snapshot(snapshot_path)
    page = generate_page(markdown, snapshot)
    _write_page(page, output_path)
    return page


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the static GitHub Pages market brief."
    )
    parser.add_argument(
        "--brief",
        type=Path,
        default=DEFAULT_BRIEF_PATH,
        help=f"Analyst Markdown path (default: {DEFAULT_BRIEF_PATH})",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT_PATH,
        help=f"Market snapshot path (default: {DEFAULT_SNAPSHOT_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"HTML output path (default: {DEFAULT_OUTPUT_PATH})",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    page = run_generator(args.brief, args.snapshot, args.output)
    print(f"Wrote static page ({len(page)} bytes) to {args.output}")
    return 0


def cli() -> None:
    raise SystemExit(main())


def _parse_markdown(
    markdown: str,
) -> Tuple[List[str], Dict[str, List[str]]]:
    summary: List[str] = []
    sections: Dict[str, List[str]] = {}
    current_section: Optional[str] = None

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            current_section = line[3:].strip()
            sections.setdefault(current_section, [])
            continue
        target = summary if current_section is None else sections[current_section]
        target.append(line)

    return summary, sections


def _render_section(
    heading: str,
    section_id: str,
    accent: str,
    lines: Sequence[str],
) -> str:
    return (
        f"<section class=\"market-card accent-{accent}\" id=\"{section_id}\">"
        f"<div class=\"section-heading\">"
        f"<span class=\"accent-bar\" aria-hidden=\"true\"></span>"
        f"<h2>{html.escape(heading)}</h2>"
        f"</div>"
        f"{_render_lines(lines)}"
        f"</section>"
    )


def _render_lines(lines: Sequence[str]) -> str:
    fragments: List[str] = []
    list_open = False

    for line in lines:
        if line.startswith("- "):
            if not list_open:
                fragments.append("<ul class=\"brief-list\">")
                list_open = True
            fragments.append(f"<li>{_render_inline(line[2:])}</li>")
            continue

        if list_open:
            fragments.append("</ul>")
            list_open = False
        fragments.append(f"<p>{_render_inline(line)}</p>")

    if list_open:
        fragments.append("</ul>")
    if not fragments:
        return "<p class=\"unknown\">資料未知。</p>"
    return "".join(fragments)


def _render_inline(value: str) -> str:
    fragments: List[str] = []
    position = 0
    for match in CITATION_PATTERN.finditer(value):
        fragments.append(html.escape(value[position : match.start()]))
        source = html.escape(match.group("source"))
        timestamp = html.escape(match.group("timestamp"))
        fragments.append(
            "<span class=\"citation\">"
            f"<span>{source}</span>"
            "<span aria-hidden=\"true\">·</span>"
            f"<time datetime=\"{timestamp}\">{timestamp}</time>"
            "</span>"
        )
        position = match.end()
    fragments.append(html.escape(value[position:]))
    return "".join(fragments)


def _collect_sources(
    markdown: str,
    snapshot: Mapping[str, Any],
) -> Sequence[str]:
    sources = {
        match.group("source").strip()
        for match in CITATION_PATTERN.finditer(markdown)
        if match.group("source").strip()
    }
    root_source = snapshot.get("source")
    if isinstance(root_source, str) and root_source:
        sources.add(root_source)
    records = snapshot.get("records")
    if isinstance(records, list):
        for record in records:
            if not isinstance(record, dict):
                continue
            source = record.get("source")
            if isinstance(source, str) and source:
                sources.add(source)
    return tuple(sorted(sources)) or ("未知",)


def _write_page(page: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.write_text(page, encoding="utf-8")
    temporary_path.replace(output_path)


def _text(value: Any) -> str:
    if value is None or value == "":
        return "未知"
    return str(value)


PAGE_TEMPLATE = Template(
    """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <meta
    http-equiv="Content-Security-Policy"
    content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'"
  >
  <meta
    name="description"
    content="每日跨資產 AI Market Brief，涵蓋美股、Crypto、黃金與外匯。"
  >
  <title>AI Market Brief · $report_date</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #071019;
      --surface: rgba(15, 28, 40, 0.88);
      --surface-strong: #122536;
      --line: rgba(153, 190, 216, 0.15);
      --text: #eef7fb;
      --muted: #9eb3c2;
      --cyan: #5ee2d0;
      --blue: #70a7ff;
      --violet: #ab8cff;
      --gold: #f3c969;
      --teal: #55d6be;
      --red: #ff7e86;
    }

    * { box-sizing: border-box; }

    html { scroll-behavior: smooth; }

    body {
      margin: 0;
      min-height: 100vh;
      font-family:
        Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI",
        "PingFang TC", "Noto Sans TC", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 15% 0%, rgba(28, 116, 132, 0.25), transparent 30rem),
        radial-gradient(circle at 90% 15%, rgba(58, 77, 137, 0.23), transparent 34rem),
        var(--bg);
      line-height: 1.65;
    }

    a { color: inherit; }

    .shell {
      width: min(1100px, calc(100% - 32px));
      margin: 0 auto;
      padding: 56px 0 72px;
    }

    .masthead {
      padding: clamp(26px, 5vw, 54px);
      border: 1px solid var(--line);
      border-radius: 24px;
      background:
        linear-gradient(130deg, rgba(20, 47, 62, 0.96), rgba(12, 24, 37, 0.92));
      box-shadow: 0 28px 80px rgba(0, 0, 0, 0.28);
    }

    .eyebrow {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      color: var(--cyan);
      font-size: 0.78rem;
      font-weight: 750;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }

    .date-pill {
      padding: 6px 11px;
      border: 1px solid rgba(94, 226, 208, 0.3);
      border-radius: 999px;
      color: var(--text);
      background: rgba(94, 226, 208, 0.08);
      letter-spacing: 0.04em;
    }

    h1 {
      max-width: 720px;
      margin: 22px 0 12px;
      font-size: clamp(2.15rem, 6vw, 4.35rem);
      line-height: 1.02;
      letter-spacing: -0.055em;
    }

    .summary {
      max-width: 820px;
      color: #c7d9e4;
      font-size: clamp(1rem, 2vw, 1.14rem);
    }

    .summary p { margin: 8px 0 0; }

    .quality-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 24px;
    }

    .quality-item {
      min-width: 0;
      padding: 12px 14px;
      border: 1px solid rgba(94, 226, 208, 0.17);
      border-radius: 12px;
      background: rgba(5, 14, 22, 0.32);
    }

    .quality-item span {
      display: block;
      margin-bottom: 4px;
      color: var(--muted);
      font-size: 0.7rem;
      font-weight: 750;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .quality-item strong {
      display: block;
      color: #dff7f2;
      font-size: 0.82rem;
      overflow-wrap: anywhere;
    }

    .nav {
      display: flex;
      gap: 8px;
      margin: 22px 0;
      overflow-x: auto;
      padding-bottom: 3px;
      scrollbar-width: thin;
    }

    .nav a {
      flex: 0 0 auto;
      padding: 8px 13px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      background: rgba(9, 20, 30, 0.75);
      text-decoration: none;
      font-size: 0.88rem;
    }

    .nav a:hover,
    .nav a:focus-visible {
      color: var(--text);
      border-color: rgba(94, 226, 208, 0.45);
      outline: none;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }

    .market-card {
      min-width: 0;
      padding: 24px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: var(--surface);
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.16);
    }

    .market-card:last-child { grid-column: 1 / -1; }

    .section-heading {
      display: flex;
      align-items: center;
      gap: 11px;
      margin-bottom: 14px;
    }

    .accent-bar {
      width: 4px;
      height: 24px;
      border-radius: 4px;
      background: var(--blue);
    }

    .accent-violet .accent-bar { background: var(--violet); }
    .accent-gold .accent-bar { background: var(--gold); }
    .accent-teal .accent-bar { background: var(--teal); }
    .accent-red .accent-bar { background: var(--red); }

    h2 {
      margin: 0;
      font-size: 1.18rem;
      letter-spacing: -0.02em;
    }

    .brief-list {
      display: grid;
      gap: 12px;
      margin: 0;
      padding: 0;
      list-style: none;
    }

    .brief-list li {
      padding: 13px 14px;
      border: 1px solid rgba(153, 190, 216, 0.1);
      border-radius: 12px;
      color: #d7e6ee;
      background: rgba(5, 14, 22, 0.38);
      overflow-wrap: anywhere;
    }

    .citation {
      display: flex;
      flex-wrap: wrap;
      gap: 4px 8px;
      margin-top: 8px;
      color: var(--muted);
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.72rem;
    }

    .unknown { color: var(--muted); }

    .footer {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 24px;
      align-items: end;
      margin-top: 20px;
      padding: 20px 4px 0;
      color: var(--muted);
      font-size: 0.82rem;
    }

    .footer strong {
      display: block;
      margin-bottom: 5px;
      color: #cfe0e9;
      font-size: 0.74rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .sources {
      display: flex;
      flex-wrap: wrap;
      gap: 7px 14px;
      margin: 0;
      padding: 0;
      list-style: none;
    }

    .sources li {
      display: inline-flex;
      align-items: center;
      gap: 7px;
    }

    .source-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--cyan);
    }

    @media (max-width: 720px) {
      .shell {
        width: min(100% - 20px, 1100px);
        padding-top: 18px;
      }

      .masthead, .market-card { border-radius: 16px; }
      .grid { grid-template-columns: 1fr; }
      .market-card:last-child { grid-column: auto; }
      .footer { grid-template-columns: 1fr; }
      .eyebrow { align-items: flex-start; flex-direction: column; }
      .quality-grid { grid-template-columns: 1fr; }
    }

    @media (prefers-reduced-motion: reduce) {
      html { scroll-behavior: auto; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header class="masthead">
      <div class="eyebrow">
        <span>AI Market Brief · Daily Research Snapshot</span>
        <time class="date-pill" datetime="$report_date">$report_date</time>
      </div>
      <h1>今日市場焦點</h1>
      <div class="summary">$summary_html</div>
      <div class="quality-grid" aria-label="資料品質">
        <div class="quality-item">
          <span>報告生成時間</span>
          <strong>$generated_at</strong>
        </div>
        <div class="quality-item">
          <span>資料時間範圍</span>
          <strong>$data_time_range</strong>
        </div>
        <div class="quality-item">
          <span>資料新鮮度</span>
          <strong>$freshness_summary</strong>
        </div>
      </div>
    </header>

    <nav class="nav" aria-label="市場分類">
      <a href="#equities">美股</a>
      <a href="#crypto">Crypto</a>
      <a href="#gold">黃金</a>
      <a href="#forex">外匯</a>
      <a href="#risk">風險提示</a>
    </nav>

    <div class="grid">$sections_html</div>

    <footer class="footer">
      <div>
        <strong>資料來源</strong>
        <ul class="sources">$source_html</ul>
      </div>
      <div>
        <strong>生成時間</strong>
        <time datetime="$generated_at">$generated_at</time>
      </div>
    </footer>
  </main>
</body>
</html>
"""
)


if __name__ == "__main__":
    cli()
