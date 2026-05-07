from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from sources.filing import Filing, filing_to_dict
from tracker.threshold import CSUITE_ROLES


def _effective_value(f: Filing) -> float:
    return f.value_exact if f.value_exact is not None else (f.value_low or 0.0)


def _is_big(f: Filing, min_congress: float, min_form4: float, include_lower_insiders: bool = False) -> bool:
    if f.source == "form4":
        if (f.value_exact or 0.0) < min_form4:
            return False
        if not include_lower_insiders and f.person_role not in CSUITE_ROLES:
            return False
        return True
    return (f.value_low or 0.0) >= min_congress


def _fmt_money(n: float) -> str:
    if n >= 1_000_000:
        return f"${n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"${n/1_000:.0f}k"
    return f"${n:,.0f}"


def compute_stats(filings: list[Filing], today: str, min_congress: float, min_form4: float, include_lower_insiders: bool = False) -> dict:
    big_today = [
        f for f in filings
        if f.filed_at.startswith(today) and _is_big(f, min_congress, min_form4, include_lower_insiders)
    ]
    volume = sum(_effective_value(f) for f in big_today)
    top_ticker_counter = Counter(f.ticker for f in big_today if f.ticker)
    top_ticker = top_ticker_counter.most_common(1)[0][0] if top_ticker_counter else "-"
    top_buyer = "-"
    if big_today:
        biggest = max(big_today, key=_effective_value)
        amount = _fmt_money(_effective_value(biggest))
        top_buyer = f"{biggest.person} - {amount} {biggest.action}"
    return {
        "big_today": len(big_today),
        "volume": _fmt_money(volume) if volume else "$0",
        "top_ticker": top_ticker,
        "top_buyer": top_buyer,
    }


def render_dashboard(
    filings: list[Filing],
    last_poll: str,
    template_dir: Path,
    out_html: Path,
    out_data: Path,
    min_congress: float,
    min_form4: float,
    include_lower_insiders: bool = False,
) -> None:
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "j2"]),
    )
    tpl = env.get_template("dashboard.html.j2")
    today = last_poll[:10]
    stats = compute_stats(filings, today=today, min_congress=min_congress, min_form4=min_form4, include_lower_insiders=include_lower_insiders)
    data = [filing_to_dict(f) for f in filings]
    json_blob = json.dumps(data).replace("</script>", "<\\/script>")
    html = tpl.render(
        last_poll=last_poll,
        stats=stats,
        filings_json=json_blob,
    )
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html)
    out_data.write_text(json.dumps(data, indent=2))
