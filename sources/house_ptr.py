from __future__ import annotations
import io
import zipfile
from datetime import datetime, timezone

import requests
from lxml import etree

from sources.filing import Filing

ZIP_URL_TEMPLATE = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip"
PDF_URL_TEMPLATE = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{doc_id}.pdf"


def _parse_filing_date(s: str) -> str:
    dt = datetime.strptime(s.strip(), "%m/%d/%Y").replace(tzinfo=timezone.utc)
    return dt.isoformat()


def parse_xml(xml_bytes: bytes) -> list[Filing]:
    root = etree.fromstring(xml_bytes)
    out: list[Filing] = []
    for member in root.findall(".//Member"):
        if (member.findtext("FilingType") or "").strip() != "P":
            continue
        last = (member.findtext("Last") or "").strip()
        first = (member.findtext("First") or "").strip()
        doc_id = (member.findtext("DocID") or "").strip()
        year = (member.findtext("Year") or "").strip()
        filing_date = (member.findtext("FilingDate") or "").strip()
        if not (last and first and doc_id and year and filing_date):
            continue
        person = f"{first} {last}"
        raw_url = PDF_URL_TEMPLATE.format(year=year, doc_id=doc_id)
        out.append(
            Filing(
                id=f"house:{doc_id}:0",
                source="house",
                filed_at=_parse_filing_date(filing_date),
                person=person,
                person_role="Representative",
                ticker=None,
                company="",
                action="BUY",
                shares=None,
                price_per_share=None,
                value_low=None,
                value_high=None,
                value_exact=None,
                raw_url=raw_url,
            )
        )
    return out


def fetch(year: int | None = None, http_get=requests.get) -> list[Filing]:
    year = year or datetime.now(timezone.utc).year
    url = ZIP_URL_TEMPLATE.format(year=year)
    resp = http_get(url, timeout=60)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        xml_name = next(n for n in z.namelist() if n.lower().endswith(".xml"))
        xml_bytes = z.read(xml_name)
    return parse_xml(xml_bytes)
