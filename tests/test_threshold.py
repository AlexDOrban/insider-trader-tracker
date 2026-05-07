from sources.filing import Filing
from tracker.threshold import classify, ThresholdConfig


def _congress(value_low: float, value_high: float, role: str = "Representative") -> Filing:
    return Filing(
        id="x", source="house", filed_at="2026-05-07T00:00:00+00:00",
        person="x", person_role=role, ticker="X", company="X",
        action="BUY", shares=None, price_per_share=None,
        value_low=value_low, value_high=value_high, value_exact=None, raw_url="",
    )


def _form4(value_exact: float, role: str = "CEO") -> Filing:
    return Filing(
        id="x", source="form4", filed_at="2026-05-07T00:00:00+00:00",
        person="x", person_role=role, ticker="X", company="X",
        action="SELL", shares=1.0, price_per_share=value_exact, value_low=None,
        value_high=None, value_exact=value_exact, raw_url="",
    )


def test_congress_below_threshold_is_small():
    cfg = ThresholdConfig(min_congress=50_000, min_form4=500_000, include_lower_insiders=False)
    assert classify(_congress(15_000, 50_000), cfg) == "small"


def test_congress_at_or_above_threshold_is_big():
    cfg = ThresholdConfig(min_congress=50_000, min_form4=500_000, include_lower_insiders=False)
    assert classify(_congress(50_000, 100_000), cfg) == "big"


def test_form4_below_threshold_is_small():
    cfg = ThresholdConfig(min_congress=50_000, min_form4=500_000, include_lower_insiders=False)
    assert classify(_form4(499_999), cfg) == "small"


def test_form4_above_threshold_csuite_is_big():
    cfg = ThresholdConfig(min_congress=50_000, min_form4=500_000, include_lower_insiders=False)
    assert classify(_form4(1_000_000, role="CFO"), cfg) == "big"


def test_form4_lower_insider_default_excluded_even_above_threshold():
    cfg = ThresholdConfig(min_congress=50_000, min_form4=500_000, include_lower_insiders=False)
    assert classify(_form4(2_000_000, role="VP Engineering"), cfg) == "small"


def test_form4_lower_insider_included_when_flag_on():
    cfg = ThresholdConfig(min_congress=50_000, min_form4=500_000, include_lower_insiders=True)
    assert classify(_form4(2_000_000, role="VP Engineering"), cfg) == "big"
