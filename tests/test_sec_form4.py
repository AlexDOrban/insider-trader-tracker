import pytest
from pathlib import Path
from sources.sec_form4 import parse_atom, parse_form4, _ua_headers


ATOM = (Path(__file__).parent / "fixtures" / "form4_atom.xml").read_bytes()
FILING = (Path(__file__).parent / "fixtures" / "form4_filing.xml").read_bytes()


def test_parse_atom_extracts_filing_index_url_and_accession():
    entries = parse_atom(ATOM)
    # 2 Form 4 entries (one "4 - ...", one "4/A - ...") — 424B2 entry filtered out
    assert len(entries) == 2
    e = entries[0]
    assert e["accession"] == "0001045810-26-000123"
    assert e["filing_index_url"].endswith("0001045810-26-000123-index.htm")
    assert e["updated"].startswith("2026-05-07T")


def test_parse_atom_filters_non_form4_titles():
    entries = parse_atom(ATOM)
    accessions = {e["accession"] for e in entries}
    # 424B2 prospectus must be excluded
    assert "0001918704-26-012458" not in accessions
    # 4/A amendment must be included
    assert "0001111111-26-999999" in accessions


EXPECTED_INDEX_URL = "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000123/0001045810-26-000123-index.htm"


def test_parse_form4_returns_filing_with_csuite_role():
    f = parse_form4(FILING, accession="0001045810-26-000123",
                    filed_at="2026-05-07T11:48:00-04:00",
                    filing_index_url=EXPECTED_INDEX_URL)
    assert f is not None
    assert f.source == "form4"
    assert f.person == "Huang Jensen"
    assert f.person_role == "CEO"
    assert f.ticker == "NVDA"
    assert f.company == "NVIDIA CORP"
    assert f.action == "SELL"
    assert f.shares == 100000.0
    assert f.price_per_share == 124.0
    assert f.value_exact == 100000.0 * 124.0
    assert f.id == "form4:0001045810-26-000123:0"
    assert f.raw_url == EXPECTED_INDEX_URL


def test_parse_form4_p_code_is_buy():
    bytes_in = FILING.replace(b"<transactionCode>S</transactionCode>",
                              b"<transactionCode>P</transactionCode>")
    f = parse_form4(bytes_in, accession="x", filed_at="2026-05-07T00:00:00+00:00",
                    filing_index_url=EXPECTED_INDEX_URL)
    assert f.action == "BUY"
    assert f.raw_url == EXPECTED_INDEX_URL


def test_ua_headers_raises_when_env_var_missing(monkeypatch):
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    with pytest.raises(RuntimeError, match="SEC_USER_AGENT"):
        _ua_headers()
