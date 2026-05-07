from __future__ import annotations
import os
import re

import requests
from lxml import etree

from sources.filing import Filing

ATOM_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&output=atom"
ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}

CODE_TO_ACTION = {
    "P": "BUY", "S": "SELL", "A": "BUY", "M": "OPTION_BUY",
    "F": "EXCHANGE", "X": "OPTION_BUY", "D": "SELL", "G": "EXCHANGE",
}


def parse_atom(atom_bytes: bytes) -> list[dict]:
    root = etree.fromstring(atom_bytes)
    out: list[dict] = []
    for entry in root.findall("a:entry", ATOM_NS):
        eid = entry.findtext("a:id", default="", namespaces=ATOM_NS)
        m = re.search(r"accession-number=([\d-]+)", eid)
        if not m:
            continue
        accession = m.group(1)
        index_url = ""
        for link in entry.findall("a:link", ATOM_NS):
            href = link.get("href", "")
            if href.endswith("-index.htm"):
                index_url = href
                break
        if not index_url:
            continue
        out.append({
            "accession": accession,
            "filing_index_url": index_url,
            "updated": entry.findtext("a:updated", default="", namespaces=ATOM_NS),
        })
    return out


def _normalize_role(officer_title: str, is_director: bool, is_ten_percent: bool) -> str:
    t = (officer_title or "").strip()
    upper = t.upper()
    if "CEO" in upper or "CHIEF EXECUTIVE" in upper:
        return "CEO"
    if "CFO" in upper or "CHIEF FINANCIAL" in upper:
        return "CFO"
    if "COO" in upper or "CHIEF OPERATING" in upper:
        return "COO"
    if "PRESIDENT" in upper:
        return "President"
    if is_director:
        return "Director"
    if is_ten_percent:
        return "10% owner"
    return t or "Insider"


def parse_form4(xml_bytes: bytes, accession: str, filed_at: str, filing_index_url: str = "") -> Filing | None:
    root = etree.fromstring(xml_bytes)
    issuer_name = (root.findtext(".//issuer/issuerName") or "").strip()
    ticker = (root.findtext(".//issuer/issuerTradingSymbol") or "").strip() or None
    owner_name = (root.findtext(".//reportingOwner/reportingOwnerId/rptOwnerName") or "").strip()
    is_director = root.findtext(".//reportingOwnerRelationship/isDirector") in ("1", "true")
    is_ten_percent = root.findtext(".//reportingOwnerRelationship/isTenPercentOwner") in ("1", "true")
    is_officer = root.findtext(".//reportingOwnerRelationship/isOfficer") in ("1", "true")
    officer_title = root.findtext(".//reportingOwnerRelationship/officerTitle") or ""
    role = _normalize_role(officer_title if is_officer else "", is_director, is_ten_percent)

    tx = root.find(".//nonDerivativeTransaction")
    if tx is None:
        tx = root.find(".//derivativeTransaction")
    if tx is None:
        return None
    code = (tx.findtext(".//transactionCode") or "").strip().upper()
    action = CODE_TO_ACTION.get(code, "BUY")
    shares_txt = tx.findtext(".//transactionShares/value") or "0"
    price_txt = tx.findtext(".//transactionPricePerShare/value") or "0"
    try:
        shares = float(shares_txt)
        price = float(price_txt)
    except ValueError:
        shares, price = 0.0, 0.0
    value_exact = shares * price if shares and price else None

    return Filing(
        id=f"form4:{accession}:0",
        source="form4",
        filed_at=filed_at,
        person=owner_name,
        person_role=role,
        ticker=ticker,
        company=issuer_name,
        action=action,
        shares=shares or None,
        price_per_share=price or None,
        value_low=None,
        value_high=None,
        value_exact=value_exact,
        raw_url=filing_index_url,
    )


def _ua_headers() -> dict:
    ua = os.environ.get("SEC_USER_AGENT")
    if not ua:
        raise RuntimeError(
            "SEC_USER_AGENT environment variable is not set. "
            "Set it to '<Your Name> <your@email.com>' as required by EDGAR."
        )
    return {"User-Agent": ua, "Accept": "application/atom+xml,application/xml,text/xml"}


def _find_primary_xml_url(index_url: str, http_get=requests.get) -> str | None:
    resp = http_get(index_url, headers=_ua_headers(), timeout=30)
    resp.raise_for_status()
    for m in re.finditer(r'href="([^"]+\.xml)"', resp.text):
        href = m.group(1)
        if "FilingSummary" in href:
            continue
        if href.startswith("/"):
            return f"https://www.sec.gov{href}"
        return href
    return None


def fetch(http_get=requests.get) -> list[Filing]:
    atom_resp = http_get(ATOM_URL, headers=_ua_headers(), timeout=30)
    atom_resp.raise_for_status()
    entries = parse_atom(atom_resp.content)
    out: list[Filing] = []
    for e in entries:
        xml_url = _find_primary_xml_url(e["filing_index_url"], http_get=http_get)
        if not xml_url:
            continue
        try:
            r = http_get(xml_url, headers=_ua_headers(), timeout=30)
            r.raise_for_status()
            f = parse_form4(r.content, accession=e["accession"], filed_at=e["updated"], filing_index_url=e["filing_index_url"])
        except Exception:
            continue
        if f is not None:
            out.append(f)
    return out
