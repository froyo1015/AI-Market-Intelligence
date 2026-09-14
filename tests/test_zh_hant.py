import json
import subprocess
from pathlib import Path
from src.pages.intelligence_generator import generate_intelligence_page


def translate(values):
    return json.loads(subprocess.check_output(['node', '-e',
        'const v=require(process.argv[1]); console.log(JSON.stringify(JSON.parse(process.argv[2]).map(v.uiText)));',
        str(Path('src/pages/static/intelligence.js').resolve()), json.dumps(values)], text=True))


def test_status_presentation_only():
    values = ['stale', 'partial', 'Deterministic fallback', 'unavailable']
    assert translate(values) == ['資料已過期', '部分資料可用', '規則式備援模式', '暫無資料']
    assert values == ['stale', 'partial', 'Deterministic fallback', 'unavailable']


def test_identifiers_and_source_text_preserved():
    values = ['obs_BTC_stale_20260914', '[refs: evidence_123]', 'Yahoo Finance',
              'BTC-USD', '2026-09-14T07:05:08.123Z', 'Source: Current Research',
              'Story: market_state:risk_off']
    assert translate(values) == values[:5] + ['來源：Current Research', '主題代碼：market_state:risk_off']


def test_chinese_shell_and_safety():
    html = generate_intelligence_page()
    for text in ['今日市場摘要', '市場有何變化', '為何重要', '市場結構', '未來風險',
                 '證據與來源', '市場環境（Market Regime）', '不應自行補充不存在的事實']:
        assert text in html
    assert 'lang="zh-Hant"' in html
    assert "script-src 'self'" in html
    assert 'https://github.com/froyo1015/AI-Market-Intelligence/issues/new' in html
    assert not any(x in html for x in ['/Users/', '/home/runner/', 'body_base64'])
