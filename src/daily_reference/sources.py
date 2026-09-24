"""Two independent official daily reference readers; no vendor quote fallback."""
from __future__ import annotations

import hashlib
import html
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import requests

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
H15_URL = "https://www.federalreserve.gov/releases/h15/"
MAX_BYTES = 600_000


class SourceError(ValueError):
    pass


def fetch(url: str) -> bytes:
    with requests.get(url, headers={"User-Agent": "AI-Market-Intelligence-Daily-Reference/1.0",
                                    "Accept": "text/html, application/xml, text/xml"},
                      timeout=15, stream=True) as response:
        response.raise_for_status()
        chunks = []
        size = 0
        for chunk in response.iter_content(chunk_size=64_000):
            size += len(chunk)
            if size > MAX_BYTES:
                raise SourceError("source_size_invalid")
            chunks.append(chunk)
    body = b"".join(chunks)
    if not body:
        raise SourceError("source_size_invalid")
    return body


def _positive(text: str) -> Decimal:
    try:
        value = Decimal(text)
    except (InvalidOperation, TypeError):
        raise SourceError("source_value_invalid") from None
    if not value.is_finite() or value <= 0:
        raise SourceError("source_value_invalid")
    return value


def _date(text: str, now: datetime, zone: str) -> str:
    try:
        value = date.fromisoformat(text)
    except (ValueError, TypeError):
        raise SourceError("source_date_invalid") from None
    if value.isoformat() != text or value > now.astimezone(ZoneInfo(zone)).date():
        raise SourceError("source_date_invalid")
    return text


def parse_ecb(body: bytes, now: datetime) -> dict:
    if b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise SourceError("source_xml_invalid")
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError:
        raise SourceError("source_xml_invalid") from None
    dated = [node for node in root.iter() if node.tag.endswith("Cube") and "time" in node.attrib]
    if len(dated) != 1:
        raise SourceError("source_period_ambiguous")
    period = _date(dated[0].attrib["time"], now, "Europe/Berlin")
    rates = {}
    for node in dated[0]:
        if not node.tag.endswith("Cube"):
            raise SourceError("source_xml_invalid")
        currency = node.attrib.get("currency")
        if currency in rates:
            raise SourceError("duplicate_currency")
        if currency:
            rates[currency] = _positive(node.attrib.get("rate"))
    if not all(currency in rates for currency in ("USD", "JPY", "GBP")):
        raise SourceError("missing_required_currency")
    return {"period": period, "rates": rates, "sha256": hashlib.sha256(body).hexdigest()}


class _H15Table(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_table = False
        self.table_count = 0
        self.in_cell = None
        self.cell_text = []
        self.row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if tag == "table" and props.get("id") == "h15table":
            self.in_table = True
            self.table_count += 1
        elif self.in_table and tag in {"th", "td"}:
            self.in_cell = tag
            self.cell_text = []
        elif self.in_table and self.in_cell and tag == "br":
            self.cell_text.append(" ")

    def handle_data(self, data):
        if self.in_table and self.in_cell:
            self.cell_text.append(data)

    def handle_endtag(self, tag):
        if not self.in_table:
            return
        if tag in {"th", "td"} and self.in_cell == tag:
            self.row.append((tag, " ".join("".join(self.cell_text).split())))
            self.in_cell = None
        elif tag == "tr":
            if self.row:
                self.rows.append(self.row)
            self.row = []
        elif tag == "table":
            self.in_table = False


def parse_h15(body: bytes, now: datetime) -> dict:
    try:
        page = body.decode("utf-8")
    except UnicodeDecodeError:
        raise SourceError("source_html_invalid") from None
    release = re.findall(r"Release date:\s*([A-Z][a-z]+\s+\d{1,2},\s+\d{4})", page)
    if len(release) != 1:
        raise SourceError("release_date_ambiguous")
    try:
        released = datetime.strptime(release[0], "%B %d, %Y").date().isoformat()
    except ValueError:
        raise SourceError("release_date_invalid") from None
    _date(released, now, "America/New_York")
    parser = _H15Table()
    parser.feed(page)
    if parser.table_count != 1 or not parser.rows:
        raise SourceError("h15_table_missing")
    header = parser.rows[0]
    dates = []
    for _, text in header[1:]:
        try:
            parsed = datetime.strptime(text, "%Y %b %d").date().isoformat()
        except ValueError:
            raise SourceError("h15_header_invalid") from None
        dates.append(_date(parsed, now, "America/New_York"))
    if not dates or len(dates) != len(set(dates)) or dates != sorted(dates):
        raise SourceError("h15_dates_invalid")
    section = None
    subsection = None
    matches = []
    for row in parser.rows[1:]:
        if not row or row[0][0] != "th":
            continue
        label = row[0][1]
        if label == "Treasury constant maturities":
            section = label
            subsection = None
        elif label.startswith("Nominal") and section:
            subsection = "nominal"
        elif label.startswith("Inflation indexed") or label.startswith("Inflation-indexed"):
            subsection = "real"
        elif label == "10-year" and section and subsection == "nominal":
            matches.append(row)
    if len(matches) != 1 or len(matches[0]) != len(dates) + 1:
        raise SourceError("h15_nominal_10y_ambiguous")
    candidates = []
    for period, (tag, text) in zip(dates, matches[0][1:]):
        if tag != "td":
            raise SourceError("h15_value_invalid")
        if text and text.lower() not in {"n.a.", "n.a", "na"}:
            candidates.append((period, _positive(html.unescape(text))))
    if not candidates or candidates[-1][0] > released:
        raise SourceError("h15_observation_unavailable")
    period, value = candidates[-1]
    return {"period": period, "release_date": released, "value": value,
            "sha256": hashlib.sha256(body).hexdigest()}
