from __future__ import annotations
from datetime import datetime, timezone

import requests
from lxml import html

from sources.filing import Filing

BASE = "https://efdsearch.senate.gov"
HOME = f"{BASE}/search/home/"
SEARCH = f"{BASE}/search/report/data/"


def _parse_date(s: str) -> str:
    dt = datetime.strptime(s.strip(), "%m/%d/%Y").replace(tzinfo=timezone.utc)
    return dt.isoformat()


def parse_results(html_text: str) -> list[Filing]:
    tree = html.fromstring(html_text)
    rows = tree.xpath("//table[@id='filedReports']/tbody/tr")
    out: list[Filing] = []
    for row in rows:
        tds = row.xpath("./td")
        if len(tds) < 5:
            continue
        first = (tds[0].text_content() or "").strip()
        last = (tds[1].text_content() or "").strip()
        filing_type = (tds[2].text_content() or "").strip()
        date = (tds[3].text_content() or "").strip()
        link = tds[4].xpath(".//a/@href")
        if "Periodic Transaction Report" not in filing_type:
            continue
        if not link:
            continue
        href = link[0]
        slug = href.strip("/").split("/")[-1]
        out.append(
            Filing(
                id=f"senate:{slug}:0",
                source="senate",
                filed_at=_parse_date(date),
                person=f"{first} {last}",
                person_role="Senator",
                ticker=None,
                company="",
                action="BUY",
                shares=None,
                price_per_share=None,
                value_low=None,
                value_high=None,
                value_exact=None,
                raw_url=f"{BASE}{href}",
            )
        )
    return out


def fetch(session: requests.Session | None = None) -> list[Filing]:
    s = session or requests.Session()
    s.get(HOME, timeout=30)
    s.post(
        HOME,
        data={"prohibition_agreement": "1"},
        headers={"Referer": HOME},
        timeout=30,
    )
    resp = s.post(
        SEARCH,
        data={
            "report_types": "[11]",
            "filer_types": "[]",
            "submitted_start_date": "",
            "submitted_end_date": "",
            "candidate_ddl": "",
            "senator_first_name": "",
            "senator_last_name": "",
            "office_id": "",
            "first_name": "",
            "last_name": "",
        },
        headers={"Referer": HOME, "X-Requested-With": "XMLHttpRequest"},
        timeout=60,
    )
    resp.raise_for_status()
    return parse_results(resp.text)
