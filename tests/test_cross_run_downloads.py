from pathlib import Path


def test_cross_run_downloads_bind_source_run():
    for filename, steps in [('daily_market_brief.yml', ('previous', 'shadow')),
                            ('derivatives_shadow.yml', ('prior',))]:
        text = (Path('.github/workflows') / filename).read_text()
        for step in steps:
            assert 'artifact-ids: ${{ steps.' + step + '.outputs.id }}' in text
            assert 'run-id: ${{ steps.' + step + '.outputs.run_id }}' in text
        assert "core.setOutput('run_id'" in text
