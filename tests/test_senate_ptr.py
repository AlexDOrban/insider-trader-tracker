from pathlib import Path
from sources.senate_ptr import parse_results


FIXTURE = Path(__file__).parent / "fixtures" / "senate_results.html"


def test_parse_results_keeps_only_ptr_rows():
    filings = parse_results(FIXTURE.read_text())
    assert len(filings) == 2
    assert {f.person for f in filings} == {"Tommy Tuberville", "Bernie Sanders"}


def test_parse_results_sets_source_role_and_url():
    filings = parse_results(FIXTURE.read_text())
    for f in filings:
        assert f.source == "senate"
        assert f.person_role == "Senator"
        assert "efdsearch.senate.gov" in f.raw_url


def test_parse_results_ids_unique_and_stable():
    f1 = parse_results(FIXTURE.read_text())
    f2 = parse_results(FIXTURE.read_text())
    assert [f.id for f in f1] == [f.id for f in f2]
    assert len({f.id for f in f1}) == len(f1)
