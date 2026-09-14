import json
import subprocess
from pathlib import Path

from src.pages.intelligence_generator import generate_intelligence_page


def status(model):
    return json.loads(subprocess.check_output(['node', '-e',
        'const v=require(process.argv[1]); console.log(JSON.stringify(v.betaStatusLines(JSON.parse(process.argv[2]),Date.now())));',
        str(Path('src/pages/static/intelligence.js').resolve()), json.dumps(model)], text=True))


def test_beta_missing_is_truthful():
    text = ' '.join(status({}))
    assert 'Derivatives shadow: unavailable' in text
    assert 'Last successful report update: unavailable' in text


def test_beta_partial_fallback():
    text = ' '.join(status({'reportAvailable': True, 'validationStatus': 'validated',
        'generatedAt': '2026-09-12T04:48:39Z', 'dataStatus': 'partial',
        'freshnessStatus': 'stale', 'aiBrief': {'modeLabel': 'Deterministic fallback'}}))
    assert 'partial' in text and 'Deterministic fallback' in text
    assert 'Recorded freshness: stale' in text
    assert 'not proof of full pipeline success' in text


def test_beta_notice_and_safe_feedback():
    page = generate_intelligence_page()
    assert '測試狀態：有條件開放' in page
    assert '上次通過部署驗證的版本：' in page
    assert 'https://github.com/froyo1015/AI-Market-Intelligence/issues/new' in page
    assert '不提供買賣建議，也不承諾預測市場走勢' in page
    assert '意見會公開顯示' in page
    assert not any(x in page for x in ['/Users/', '/home/runner/', 'body_base64', 'raw_response', 'sk-proj-'])
