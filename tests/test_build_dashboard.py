import json
from pathlib import Path

from sources.filing import Filing
from build_dashboard import compute_stats, render_dashboard


def _f(source, value_low=None, value_high=None, value_exact=None,
       ticker="NVDA", person="A", action="BUY"):
    return Filing(
        id=f"{source}:{ticker}:{person}", source=source,
        filed_at="2026-05-07T11:48:00+00:00",
        person=person, person_role="CEO" if source == "form4" else "Representative",
        ticker=ticker, company="X",
        action=action, shares=None, price_per_share=None,
        value_low=value_low, value_high=value_high, value_exact=value_exact,
        raw_url="",
    )


def test_compute_stats_counts_only_big_today():
    today = "2026-05-07"
    filings = [
        _f("form4", value_exact=12_400_000.0),
        _f("house", value_low=1_000_000.0, value_high=5_000_000.0),
        _f("house", value_low=15_000.0, value_high=50_000.0),
    ]
    stats = compute_stats(filings, today=today, min_congress=50_000, min_form4=500_000)
    assert stats["big_today"] == 2
    assert stats["volume"].startswith("$")
    assert "NVDA" in stats["top_ticker"]


def test_compute_stats_handles_empty():
    stats = compute_stats([], today="2026-05-07", min_congress=50_000, min_form4=500_000)
    assert stats["big_today"] == 0
    assert stats["top_ticker"] == "-"
    assert stats["top_buyer"] == "-"


def test_render_dashboard_writes_html_and_data(tmp_path: Path):
    template_dir = Path(__file__).parent.parent / "templates"
    out_html = tmp_path / "index.html"
    out_data = tmp_path / "data.json"
    render_dashboard(
        filings=[_f("form4", value_exact=12_400_000.0)],
        last_poll="2026-05-07T11:50:00+00:00",
        template_dir=template_dir,
        out_html=out_html,
        out_data=out_data,
        min_congress=50_000,
        min_form4=500_000,
    )
    html = out_html.read_text()
    assert "Insider Tracker" in html
    assert "NVDA" in html
    data = json.loads(out_data.read_text())
    assert data[0]["ticker"] == "NVDA"
