from sources.filing import Filing
from tracker.telegram_format import format_alert, format_digest


def _form4() -> Filing:
    return Filing(
        id="form4:abc:0", source="form4",
        filed_at="2026-05-07T11:48:00+00:00",
        person="Jensen Huang", person_role="CEO",
        ticker="NVDA", company="NVIDIA Corp",
        action="SELL", shares=100_000.0, price_per_share=124.0,
        value_low=None, value_high=None, value_exact=12_400_000.0,
        raw_url="https://sec.gov/x",
    )


def _congress() -> Filing:
    return Filing(
        id="house:xyz:0", source="house",
        filed_at="2026-05-07T12:31:00+00:00",
        person="Nancy Pelosi", person_role="Representative",
        ticker="NVDA", company="NVIDIA Corp",
        action="OPTION_BUY", shares=None, price_per_share=None,
        value_low=1_000_000.0, value_high=5_000_000.0, value_exact=None,
        raw_url="https://disclosures-clerk.house.gov/x",
    )


def test_format_alert_form4_includes_shares_and_price():
    msg = format_alert(_form4(), dashboard_url="https://example.com")
    assert "Jensen Huang" in msg
    assert "CEO" in msg
    assert "NVDA" in msg
    assert "SELL" in msg
    assert "100,000" in msg
    assert "$124.00" in msg
    assert "$12,400,000" in msg
    assert "https://sec.gov/x" in msg
    assert "https://example.com" in msg


def test_format_alert_congress_shows_range_not_shares():
    msg = format_alert(_congress(), dashboard_url="https://example.com")
    assert "Pelosi" in msg
    assert "NVDA" in msg
    assert "OPTION_BUY" in msg
    assert "$1,000,000" in msg
    assert "shares" not in msg.lower()


def test_format_digest_lists_each_filing_one_per_line():
    msg = format_digest([_form4(), _congress()], dashboard_url="https://example.com")
    lines = [l for l in msg.splitlines() if l.strip()]
    assert any("Huang" in l for l in lines)
    assert any("Pelosi" in l for l in lines)
    assert "https://example.com" in msg
