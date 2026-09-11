import json
import subprocess
from pathlib import Path
from html.parser import HTMLParser

from src.pages.intelligence_generator import generate_intelligence_page


def hints(model):
    script = Path('src/pages/static/intelligence.js').resolve()
    return json.loads(subprocess.check_output(['node','-e',
        'const v=require(process.argv[1]); console.log(JSON.stringify(v.onboardingHints(JSON.parse(process.argv[2]))));',
        str(script),json.dumps(model)],text=True))


def test_product_navigation_targets_and_onboarding():
    class Inventory(HTMLParser):
        def __init__(self):
            super().__init__(); self.ids=set(); self.links=[]
        def handle_starttag(self, tag, attrs):
            a=dict(attrs)
            if 'id' in a: self.ids.add(a['id'])
            if tag=='a' and a.get('href','').startswith('#'): self.links.append(a['href'][1:])
    page=generate_intelligence_page()
    inventory=Inventory(); inventory.feed(page)
    assert all(x in inventory.ids for x in inventory.links)
    for label in ('Daily Intelligence','Market Overview','Macro &amp; Risk','Crypto / Derivatives Shadow','Evidence &amp; Methodology'):
        assert label in page
    assert 'Data — recorded observations' in page
    assert 'It is not a guarantee of market truth' in page
    assert 'does not choose the ranked stories' in page


def test_unknown_first_run_is_not_asserted_as_fact():
    text=' '.join(hints({}))
    assert 'may be a first run or a missing artifact' in text
    assert 'Previous run unavailable' in text
    assert 'Optional derivatives' in text


def test_partial_stale_and_optional_states():
    text=' '.join(hints({'reportAvailable':True,'dataStatus':'partial','freshnessStatus':'stale','previousAvailable':True}))
    assert 'Partial pipeline' in text and 'Stale data' in text
    assert 'Daily report unavailable' not in text
    assert hints({'reportAvailable':True,'previousAvailable':True,'dataStatus':'complete','freshnessStatus':'current','derivatives':{'validation_status':'validated'}})==[]


def test_mobile_and_security_rules():
    page=generate_intelligence_page()
    assert 'grid-template-columns: minmax(0, 1fr)' in page
    assert 'min-width: 0' in page and 'white-space: normal' in page
    assert 'min-height: 44px' in page and 'Skip to daily research' in page
    assert "script-src 'self'" in page
    script=Path('src/pages/static/intelligence.js').read_text()
    assert 'innerHTML' not in script and 'insertAdjacentHTML' not in script
