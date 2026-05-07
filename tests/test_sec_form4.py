from pathlib import Path
from sources.sec_form4 import parse_atom, parse_form4


ATOM = (Path(__file__).parent / "fixtures" / "form4_atom.xml").read_bytes()
FILING = (Path(__file__).parent / "fixtures" / "form4_filing.xml").read_bytes()


def test_parse_atom_extracts_filing_index_url_and_accession():
    entries = parse_atom(ATOM)
    assert len(entries) == 1
    e = entries[0]
    assert e["accession"] == "0001045810-26-000123"
    assert e["filing_index_url"].endswith("0001045810-26-000123-index.htm")
    assert e["updated"].startswith("2026-05-07T")


def test_parse_form4_returns_filing_with_csuite_role():
    f = parse_form4(FILING, accession="0001045810-26-000123",
                    filed_at="2026-05-07T11:48:00-04:00")
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


def test_parse_form4_p_code_is_buy():
    bytes_in = FILING.replace(b"<transactionCode>S</transactionCode>",
                              b"<transactionCode>P</transactionCode>")
    f = parse_form4(bytes_in, accession="x", filed_at="2026-05-07T00:00:00+00:00")
    assert f.action == "BUY"
