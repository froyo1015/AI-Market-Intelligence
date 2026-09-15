import copy
import json
import re
from pathlib import Path

from src.brief.intelligence_renderer import render_daily_market_brief
from src.brief.renderer_validator import validate_rendered_brief
from tests.test_intelligence_brief_renderer import _intelligence, _top


def test_reading_order_and_reference_preservation():
    daily = _intelligence(calendar=True)
    top = _top(daily)
    original = copy.deepcopy((daily, top))
    text = render_daily_market_brief(daily, top).markdown
    headings = ['## 今日市場重點', '## 市場環境', '## 未來 24–48 小時風險',
                '## 資料狀態', '## 證據與引用']
    assert [text.index(h) for h in headings] == sorted(text.index(h) for h in headings)
    assert text.index('## Data Quality and Coverage') > text.index(headings[-1])
    for item in top['items']:
        assert text.index(item['headline']) < text.index(headings[1])
        assert item['item_id'] in text
        for refs in item['evidence_refs'].values():
            assert all(ref in text for ref in refs)
    assert (daily, top) == original
    validate_rendered_brief(text, daily, top)


def test_unavailable_does_not_invent_story_or_safe_future():
    daily = _intelligence(stale_hours=25)
    text = render_daily_market_brief(daily).markdown
    assert '不補造市場結論' in text
    assert '不代表未來沒有風險' in text
    assert all(w in text for w in daily['warnings'])
    assert render_daily_market_brief(daily).markdown == text


def test_live_review_preserves_identifiers_and_gate_failure():
    root = Path(__file__).resolve().parents[1]
    before = (root / 'review/phase-11.2/before-brief.md').read_text()
    after = (root / 'review/phase-11.2/after-brief.md').read_text()
    identifiers = re.findall(r'`([^`\n]+)`', before)
    assert all(value in after for value in identifiers)
    gate = json.loads((root / 'minimum-useful-intelligence-gate.json').read_text())
    assert gate['gate_passed'] == all(c['passed'] for c in gate['criteria'])
    assert not gate['gate_passed']
    assert gate['criteria'][0]['actual'] == 5
    assert gate['criteria'][0]['required'] == 6
