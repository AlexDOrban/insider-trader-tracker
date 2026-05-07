from __future__ import annotations
from sources.filing import Filing

SOURCE_ICON = {"house": "🏛 House", "senate": "🏛 Senate", "form4": "📄 Form 4"}


def _fmt_money(n: float) -> str:
    return f"${n:,.0f}"


def _fmt_filed(iso: str) -> str:
    date, time = iso.split("T")
    hhmm = time[:5]
    return f"Filed {hhmm} UTC · {date}"


def format_alert(f: Filing, dashboard_url: str) -> str:
    src = SOURCE_ICON[f.source]
    role = f" ({f.person_role})" if f.source == "form4" else ""
    header = f"{src} — {f.person}{role}"

    if f.source == "form4":
        shares = f"{int(f.shares):,}" if f.shares is not None else "?"
        price = f"${f.price_per_share:.2f}" if f.price_per_share is not None else "?"
        total = _fmt_money(f.value_exact) if f.value_exact is not None else "?"
        body = f"{f.action}  {f.ticker}  {shares} sh @ {price} = {total}"
    else:
        lo = _fmt_money(f.value_low) if f.value_low is not None else "?"
        hi = _fmt_money(f.value_high) if f.value_high is not None else "?"
        body = f"{f.action}  {f.ticker}  {lo}–{hi}"

    filed = _fmt_filed(f.filed_at)
    links = f"<a href=\"{f.raw_url}\">View filing</a> · <a href=\"{dashboard_url}\">Dashboard</a>"
    return f"{header}\n{body}\n{filed}\n{links}"


def format_digest(filings: list[Filing], dashboard_url: str) -> str:
    lines = [f"📈 {len(filings)} new big trades"]
    for f in filings:
        src = SOURCE_ICON[f.source]
        ticker = f.ticker or "?"
        if f.source == "form4":
            amt = _fmt_money(f.value_exact) if f.value_exact is not None else "?"
        else:
            amt = (
                f"{_fmt_money(f.value_low)}–{_fmt_money(f.value_high)}"
                if f.value_low is not None and f.value_high is not None
                else "?"
            )
        lines.append(f"• {src} · {f.person} · {f.action} {ticker} · {amt}")
    lines.append(f"<a href=\"{dashboard_url}\">Dashboard</a>")
    return "\n".join(lines)
