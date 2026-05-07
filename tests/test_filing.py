import json
import pytest
from sources.filing import Filing, filing_to_dict, filing_from_dict


def test_filing_roundtrip_form4():
    f = Filing(
        id="form4:0001234567-26-000123:0",
        source="form4",
        filed_at="2026-05-07T11:48:00+00:00",
        person="Jensen Huang",
        person_role="CEO",
        ticker="NVDA",
        company="NVIDIA Corp",
        action="SELL",
        shares=100000.0,
        price_per_share=124.0,
        value_low=None,
        value_high=None,
        value_exact=12_400_000.0,
        raw_url="https://www.sec.gov/Archives/edgar/data/1045810/...",
    )
    d = filing_to_dict(f)
    f2 = filing_from_dict(d)
    assert f == f2
    json.dumps(d)


def test_filing_roundtrip_congress_uses_value_range():
    f = Filing(
        id="house:20260507-PEL-1:0",
        source="house",
        filed_at="2026-05-07T12:31:00+00:00",
        person="Nancy Pelosi",
        person_role="Representative",
        ticker="NVDA",
        company="NVIDIA Corp",
        action="OPTION_BUY",
        shares=None,
        price_per_share=None,
        value_low=1_000_000.0,
        value_high=5_000_000.0,
        value_exact=None,
        raw_url="https://disclosures-clerk.house.gov/...",
    )
    d = filing_to_dict(f)
    assert d["value_exact"] is None
    assert d["value_low"] == 1_000_000.0
    assert filing_from_dict(d) == f


def test_filing_rejects_both_exact_and_range():
    with pytest.raises(ValueError, match="exactly one of value_exact"):
        Filing(
            id="x", source="form4", filed_at="2026-05-07T00:00:00+00:00",
            person="x", person_role="x", ticker="X", company="X",
            action="BUY", shares=None, price_per_share=None,
            value_low=1.0, value_high=2.0, value_exact=3.0, raw_url="",
        )
