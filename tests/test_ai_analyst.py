import json

from src.ai.analyst import REQUIRED_HEADINGS, run_analyst
from src.ai.llm_adapter import MockLLMAdapter
from src.ai.prompt_builder import (
    INPUT_END_MARKER,
    INPUT_START_MARKER,
    build_analyst_prompt,
)


def _snapshot() -> dict:
    return {
        "generated_at": "2026-07-29T12:00:00Z",
        "source": "test_market_source",
        "records": [
            {
                "symbol": "SPY",
                "asset_type": "equity",
                "price": 123.45,
                "daily_change": 1.25,
                "weekly_change": 2.5,
                "sma20": 120.0,
                "volatility_20d": 10.0,
                "trend": "above_sma20",
                "timestamp": "2026-07-29T04:00:00Z",
                "source": "test_market_source",
                "status": "success",
            },
            {
                "symbol": "BTC-USD",
                "asset_type": "crypto",
                "price": None,
                "daily_change": None,
                "weekly_change": None,
                "sma20": None,
                "volatility_20d": None,
                "trend": "unavailable",
                "timestamp": "2026-07-29T00:00:00Z",
                "source": "test_market_source",
                "status": "failed",
            },
        ],
    }


def _context() -> dict:
    return {
        "generated_at": "2026-07-29T11:00:00Z",
        "source": "test_context_source",
        "status": "unavailable",
        "items": [],
        "risks": [],
    }


def test_prompt_contains_grounding_rules_and_input_metadata() -> None:
    prompt = build_analyst_prompt(_snapshot(), _context())

    assert "不可以自行創造" in prompt
    assert "price 完全一致" in prompt
    assert "宏觀／新聞背景未知" in prompt
    assert INPUT_START_MARKER in prompt
    assert INPUT_END_MARKER in prompt
    assert '"price": 123.45' in prompt
    assert "test_market_source" in prompt
    assert "2026-07-29T04:00:00Z" in prompt
    assert '"data_quality": {' in prompt
    assert "美股核心交易時段 09:30–16:00 ET" in prompt


def test_mock_adapter_generates_required_chinese_sections_and_citations() -> None:
    prompt = build_analyst_prompt(_snapshot(), _context())
    response = MockLLMAdapter().generate(prompt)

    for heading in REQUIRED_HEADINGS:
        assert heading in response
    assert "SPY：價格 123.45" in response
    assert "[來源: test_market_source; timestamp: 2026-07-29T04:00:00Z]" in response
    assert "BTC-USD：價格未知" in response
    assert "宏觀／新聞背景未知" in response
    assert "報告生成時間：2026-07-29T12:00:00Z" in response
    assert "資料時間範圍：" in response
    assert "新鮮度 🟢 current" in response
    assert "市場時段 美股核心交易時段 09:30–16:00 ET" in response
    assert "provider symbol SPY" in response
    assert "Yahoo Finance 調整後日線價格（非即時報價）" in response


def test_analyst_pipeline_reads_two_inputs_and_writes_markdown(tmp_path) -> None:
    snapshot_path = tmp_path / "market_snapshot.json"
    context_path = tmp_path / "market_context.json"
    output_path = tmp_path / "ai_market_brief.md"
    snapshot_path.write_text(json.dumps(_snapshot()), encoding="utf-8")
    context_path.write_text(json.dumps(_context()), encoding="utf-8")

    response = run_analyst(snapshot_path, context_path, output_path)

    assert output_path.read_text(encoding="utf-8") == response
    assert response.startswith("# 今日市場焦點")
