from pathlib import Path
from sources.house_ptr import parse_xml


FIXTURE = Path(__file__).parent / "fixtures" / "house_sample.xml"


def test_parse_xml_returns_only_ptr_filings():
    filings = parse_xml(FIXTURE.read_bytes())
    assert len(filings) == 2
    assert {f.person for f in filings} == {"Nancy Pelosi", "Daniel Crenshaw"}


def test_parse_xml_sets_source_and_role():
    filings = parse_xml(FIXTURE.read_bytes())
    for f in filings:
        assert f.source == "house"
        assert f.person_role == "Representative"


def test_parse_xml_filing_id_is_stable_and_unique():
    filings = parse_xml(FIXTURE.read_bytes())
    ids = [f.id for f in filings]
    assert len(ids) == len(set(ids))
    again = parse_xml(FIXTURE.read_bytes())
    assert [f.id for f in again] == ids


def test_parse_xml_links_to_clerk_pdf():
    filings = parse_xml(FIXTURE.read_bytes())
    for f in filings:
        assert "disclosures-clerk.house.gov" in f.raw_url
