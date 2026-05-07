import json
from pathlib import Path
from unittest.mock import patch

from sources.filing import Filing
import main as orchestrator


def _f(fid="x", source="form4", value_exact=2_000_000.0):
    return Filing(
        id=fid, source=source, filed_at="2026-05-07T11:48:00+00:00",
        person="X", person_role="CEO", ticker="NVDA", company="X",
        action="SELL", shares=10000.0, price_per_share=200.0,
        value_low=None, value_high=None, value_exact=value_exact, raw_url="",
    )


def test_run_emits_alerts_only_for_new_big_filings(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "T")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "C")
    seen = tmp_path / "seen.json"
    data = tmp_path / "filings.json"
    errors = tmp_path / "errors.json"
    out_html = tmp_path / "index.html"
    out_data = tmp_path / "data.json"

    new = [_f(fid="form4:1"), _f(fid="form4:2", value_exact=10.0)]
    with patch.object(orchestrator, "FETCHERS", {"form4": lambda: new}), \
         patch("main.send_message") as send:
        orchestrator.run(
            seen_path=seen, data_path=data, errors_path=errors,
            template_dir=Path(__file__).parent.parent / "templates",
            out_html=out_html, out_data=out_data,
            dashboard_url="https://example.com",
            min_congress=50_000, min_form4=500_000, include_lower_insiders=False,
        )
        assert send.call_count == 1
    assert set(json.loads(seen.read_text()).keys()) == {"form4:1", "form4:2"}


def test_run_dedupes_already_seen(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "T")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "C")
    seen = tmp_path / "seen.json"
    seen.write_text(json.dumps({"form4:1": "2026-05-07T00:00:00+00:00"}))
    data = tmp_path / "filings.json"
    errors = tmp_path / "errors.json"
    out_html = tmp_path / "index.html"
    out_data = tmp_path / "data.json"

    with patch.object(orchestrator, "FETCHERS", {"form4": lambda: [_f(fid="form4:1")]}), \
         patch("main.send_message") as send:
        orchestrator.run(
            seen_path=seen, data_path=data, errors_path=errors,
            template_dir=Path(__file__).parent.parent / "templates",
            out_html=out_html, out_data=out_data,
            dashboard_url="https://example.com",
            min_congress=50_000, min_form4=500_000, include_lower_insiders=False,
        )
        send.assert_not_called()


def test_run_continues_when_one_source_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "T")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "C")
    seen = tmp_path / "seen.json"
    data = tmp_path / "filings.json"
    errors = tmp_path / "errors.json"
    out_html = tmp_path / "index.html"
    out_data = tmp_path / "data.json"

    def boom():
        raise RuntimeError("network down")

    fetchers = {"house": boom, "form4": lambda: [_f()]}
    with patch.object(orchestrator, "FETCHERS", fetchers), \
         patch("main.send_message"):
        orchestrator.run(
            seen_path=seen, data_path=data, errors_path=errors,
            template_dir=Path(__file__).parent.parent / "templates",
            out_html=out_html, out_data=out_data,
            dashboard_url="https://example.com",
            min_congress=50_000, min_form4=500_000, include_lower_insiders=False,
        )
    err_state = json.loads(errors.read_text())
    assert err_state["house"]["consecutive_failures"] == 1
    assert err_state["form4"]["consecutive_failures"] == 0
