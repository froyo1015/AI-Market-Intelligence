import json
import subprocess
from pathlib import Path

import pytest

from src.pages.intelligence_generator import generate_intelligence_page


def js(code):
    script = Path('src/pages/static/intelligence.js').resolve()
    return subprocess.check_output(['node', '-e', "const v=require(process.argv[1]);" + code, str(script)], text=True)


def test_research_shell():
    page = generate_intelligence_page()
    for name in ('research-status', 'research-updated', 'top-intelligence-content', 'derivatives-content', 'audit-content'):
        assert f'id="{name}"' in page
    assert '分數用於選取重點，不是發生機率' in page
    assert '尚未用於 AI 決策' in page
    assert '尚未用於正式分析' in page


@pytest.mark.parametrize('state', ['partial', 'unavailable', 'complete'])
def test_status_header(state):
    out = js(f"console.log(JSON.stringify(v.researchHeader({{dataStatus:'{state}',freshnessStatus:'unknown',generatedAt:'unavailable'}},Date.now())));")
    result = json.loads(out)
    assert state in result['status']
    assert result['updated'] == 'Last update unavailable'


def test_old_artifact_age_does_not_rewrite_source_freshness():
    result = json.loads(js("console.log(JSON.stringify(v.researchHeader({dataStatus:'partial',freshnessStatus:'current',generatedAt:'2026-09-01T00:00:00Z'},Date.parse('2026-09-10T00:00:00Z'))));"))
    assert 'Older snapshot' in result['updated']
    assert 'Recorded source freshness: current' in result['status']
    assert 'artifact age' in result['updated']


def test_future_time_is_not_current():
    result = json.loads(js("console.log(JSON.stringify(v.researchHeader({generatedAt:'2026-10-01T00:00:00Z'},Date.parse('2026-09-10T00:00:00Z'))));"))
    assert 'future' in result['updated']


DOM = """
function node(tag){return {tag,children:[],textContent:'',appendChild(x){this.children.push(x)}};}
const doc={createElement:node};
function flatten(n){return [n,...n.children.flatMap(flatten)]}
"""


def test_individual_evidence_ids_preserved_as_text():
    result = json.loads(js(DOM + """
const r=v.renderReferences(doc,{source_ids:['source:1'],observation_ids:['obs:1','<script>test</script>']});
console.log(JSON.stringify(flatten(r).filter(x=>x.tag==='code').map(x=>x.textContent)));
"""))
    assert result == ['source:1', 'obs:1', '<script>test</script>']


def test_missing_references_visible():
    out = js(DOM + "console.log(flatten(v.renderReferences(doc,{})).map(x=>x.textContent).join(' '));")
    assert '暫無引用資料' in out


def test_shadow_badges_and_unavailable():
    out = js(DOM + """
const box=node('div'); doc.getElementById=()=>box;
v.renderDerivatives(doc,null);
console.log(flatten(box).map(x=>x.textContent).join(' '));
""")
    assert '衍生品暫無資料' in out
    script = Path('src/pages/static/intelligence.js').read_text()
    assert 'badge stale' in script and 'badge current' in script
    assert 'innerHTML' not in script
