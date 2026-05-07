# Insider Trader Tracker — Design Spec

**Date:** 2026-05-07
**Owner:** Alex Orban
**Status:** Draft for review

## 1. Purpose

Track high-conviction insider trading activity from three public sources and surface it in two channels:

1. **Push:** Telegram alert the moment a trade above threshold is published.
2. **Pull:** Static GitHub Pages dashboard with full data, filters, and a toggle to reveal smaller trades / lower-rank insiders.

Goal is signal over noise — default view shows only big trades, but full data is one click away.

## 2. Scope

**In scope:**

- US House Periodic Transaction Reports (PTR)
- US Senate Periodic Transaction Reports (PTR)
- SEC Form 4 (officer/director/10% holder transactions)
- Telegram push notifications above thresholds
- GitHub Pages dashboard with filtering UI
- Deduplication so a filing is alerted only once

**Out of scope (v1):**

- Form 13F (quarterly fund holdings)
- Form 13D/13G (5%+ activist filings)
- Options-flow / unusual options activity
- Historical backfill beyond current calendar year
- Authentication / multi-user
- Real-time streaming (cron polling is enough — filings are not millisecond-sensitive)
- Trade execution / brokerage integration

## 3. Sources

| Source | Endpoint | Format | Update cadence |
|---|---|---|---|
| House PTR | `https://disclosures-clerk.house.gov/public_disc/financial-pdfs/<YEAR>FD.zip` (XML inside) | XML in ZIP | Updated multiple times daily |
| Senate PTR | `https://efdsearch.senate.gov/search/` | HTML form (POST), HTML results | Updated as filings arrive |
| SEC Form 4 | `https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&output=atom` | Atom feed | Near real-time |

**Notes:**

- House PTR ZIP must be re-downloaded on each poll — small file (<5 MB), cheap.
- Senate EFD requires accepting a terms-of-use form first (one POST), then search. Session cookie required per run.
- SEC EDGAR requires a `User-Agent` header with contact email or returns 403.

## 4. Architecture

**Runtime:** GitHub Actions cron, 15-minute interval.

```
┌──────────────────────── GitHub Actions runner (every 15 min) ─────────────────────┐
│                                                                                   │
│   main.py orchestrator                                                            │
│      │                                                                            │
│      ├─→ sources/house_ptr.py    ─┐                                               │
│      ├─→ sources/senate_ptr.py   ─┼─→ list of normalized Filing dicts             │
│      └─→ sources/sec_form4.py    ─┘                                               │
│                       │                                                           │
│                       ▼                                                           │
│              dedupe vs seen.json                                                  │
│                       │                                                           │
│         ┌─────────────┴─────────────┐                                             │
│         ▼                           ▼                                             │
│   above threshold?              all new filings                                   │
│         │                           │                                             │
│         ▼                           ▼                                             │
│   telegram_notify.send()     append to data/filings.json                          │
│                                     │                                             │
│                                     ▼                                             │
│                          docs/index.html (built from JSON)                        │
│                                     │                                             │
│                                     ▼                                             │
│                      git commit + push (seen.json, data/, docs/)                  │
└───────────────────────────────────────────────────────────────────────────────────┘

GitHub Pages → serves docs/ → user opens dashboard via Telegram link
```

### 4.1 Components

Each source module exposes a single function that returns a list of normalized filings — no shared state, easy to test in isolation.

**`sources/house_ptr.py`**

- `fetch() -> list[Filing]`
- Downloads ZIP, extracts XML, parses each `<Member>` block, follows links to filing PDFs only when needed (PDFs are not parsed in v1 — filing metadata in XML is enough for ticker, type, date, value range).
- Pure function aside from HTTP.

**`sources/senate_ptr.py`**

- `fetch() -> list[Filing]`
- Submits ToS form, scrapes search results table.
- Same return shape as House.

**`sources/sec_form4.py`**

- `fetch() -> list[Filing]`
- Pulls Atom feed, follows each entry to the Form 4 XML to get exact share count and price/share.
- Includes officer/director title from the XML.

**`telegram_notify.py`**

- `send_message(text: str, parse_mode: str = "HTML") -> None`
- Reads `TELEGRAM_BOT_TOKEN` and `CHAT_ID` from env. No state.

**`main.py`**

- Calls each source, dedupes against `seen.json`, classifies (big vs small), pushes alerts, appends to `data/filings.json`, regenerates `docs/index.html`.
- Commits and pushes results back to repo via `actions/checkout` + `git-auto-commit-action`.

**`build_dashboard.py`** (new — not in original tree)

- Reads `data/filings.json`, renders `docs/index.html` from a Jinja template.
- Static HTML + small vanilla-JS for client-side filtering. No build step.

### 4.2 Data shape

Normalized filing dict (every source produces this shape):

```python
{
  "id": str,            # stable hash: f"{source}:{filing_id}:{transaction_idx}"
  "source": "house" | "senate" | "form4",
  "filed_at": str,      # ISO 8601 UTC
  "person": str,        # e.g. "Nancy Pelosi" or "Jensen Huang"
  "person_role": str,   # "Representative", "Senator", "CEO", "CFO", "Director", "10% owner", ...
  "ticker": str | None,
  "company": str,
  "action": "BUY" | "SELL" | "EXCHANGE" | "OPTION_BUY" | "OPTION_SELL",
  "shares": float | None,           # Form 4 only — None for Congress
  "price_per_share": float | None,  # Form 4 only — None for Congress
  "value_low": float | None,        # Congress range bucket low
  "value_high": float | None,       # Congress range bucket high
  "value_exact": float | None,      # Form 4 — shares * price
  "raw_url": str,                   # link to source filing
}
```

Either `value_exact` (Form 4) or `value_low/value_high` (Congress) is populated, never both.

## 5. Threshold logic

Defaults (overridable via env vars):

- `MIN_CONGRESS=50000` — alert if `value_low >= 50000`
- `MIN_FORM4=500000` — alert if `value_exact >= 500000`

**Lower-rank Form 4 filter (default off, env opt-in):**

By default, alerts only on C-suite + directors (`person_role` in `{CEO, CFO, COO, President, Director, 10% owner}`). Set `INCLUDE_LOWER_INSIDERS=1` to also alert VPs and other officers above threshold.

The dashboard always shows everything (filtered client-side); thresholds only affect the Telegram push.

## 6. Deduplication

`seen.json` is a flat dict: `{filing_id: iso_timestamp_first_seen}`.

- Read at start of run, written at end.
- Pruned to last 90 days each run to keep file small.
- Lives in repo root, committed every run.
- Race condition non-issue — only one cron job runs at a time on Actions.

## 7. Dashboard

**Stack:** Jinja-rendered static HTML + Tailwind via CDN + ~80 lines of vanilla JS for filtering. No bundler.

**Layout** (matches approved mockup):

- Top bar: title, last poll timestamp, threshold badge, "Show smaller →" toggle.
- Stats strip: count of big trades today, total $ volume, top ticker, top buyer.
- Left sidebar: source checkboxes, min-size dropdown, ticker text filter, person text filter.
- Main table: filed time · source · person · ticker · action · size. Color-coded BUY (green) / SELL (red).
- Bottom drawer: "+N smaller trades hidden" with "Show all" button.

**Data:** Dashboard loads `data/filings.json` (last 90 days) on page load. All filtering is client-side. No server needed.

## 8. Error handling

- Each source wrapped in try/except. One source failing must not block the others.
- Failures logged to stdout (Actions captures), and a single Telegram alert sent if any source fails N=3 polls in a row (suppresses transient errors).
- HTTP requests use a 30s timeout and one retry with backoff.
- Hard fail (exit 1) only if Telegram itself is unreachable AND there are alerts to send — Actions UI flags failed runs.

## 9. Testing

- `tests/test_dedupe.py` — seen.json round-trip + pruning.
- `tests/test_sources.py` — each source has a `fixtures/` snapshot of one real response, parser asserted against expected normalized output. No live HTTP in tests.
- `tests/test_threshold.py` — classify big vs small for Congress and Form 4 cases.
- `tests/test_dashboard.py` — render template against fixture data, assert key elements present.
- CI: `pytest` runs on every push (separate workflow from cron).

## 10. Repository layout

```
insider-trader-tracker/
├── .github/workflows/
│   ├── poll.yml          # cron every 15 min
│   └── test.yml          # pytest on push
├── .env.example          # documents required env vars (no real .env in repo)
├── requirements.txt
├── seen.json             # committed
├── data/
│   └── filings.json      # rolling 90-day data, committed
├── docs/                 # GitHub Pages root
│   ├── index.html        # generated
│   └── assets/           # icons, favicon
├── sources/
│   ├── __init__.py
│   ├── house_ptr.py
│   ├── senate_ptr.py
│   └── sec_form4.py
├── tests/
│   ├── fixtures/
│   ├── test_dedupe.py
│   ├── test_sources.py
│   ├── test_threshold.py
│   └── test_dashboard.py
├── templates/
│   └── dashboard.html.j2
├── build_dashboard.py
├── telegram_notify.py
├── main.py
└── README.md
```

## 11. Secrets and config

GitHub Actions repo secrets:

- `TELEGRAM_BOT_TOKEN` — required
- `TELEGRAM_CHAT_ID` — required
- `SEC_USER_AGENT` — required, e.g. `"Insider Tracker contact@example.com"`

Optional env vars (defaults shown):

- `MIN_CONGRESS=50000`
- `MIN_FORM4=500000`
- `INCLUDE_LOWER_INSIDERS=0`

## 12. Telegram alert format

One message per filing, HTML-formatted:

```
🏛 House — Nancy Pelosi
BUY  NVDA  $1M–$5M
Filed 12:31 UTC · 2026-05-07
[View filing](raw_url) · [Dashboard](pages_url)
```

```
📄 Form 4 — Jensen Huang (CEO)
SELL  NVDA  100,000 sh @ $124.00 = $12.4M
Filed 11:48 UTC · 2026-05-07
[View filing](raw_url) · [Dashboard](pages_url)
```

If more than 5 alerts queue in one poll, batch into a single digest message to avoid Telegram rate limits.

## 13. Open questions

- **GitHub Pages publish source:** publish from `/docs` on `main` branch (simpler, no separate `gh-pages` branch). Confirm OK.
- **Repo visibility:** public for GitHub Pages free tier — does that conflict with anything? (Code only, no secrets in repo.)
- **Domain:** default `<user>.github.io/<repo>/` URL or custom domain? Default is fine for v1.

## 14. Success criteria

1. Big trade by a Congress member or C-suite officer triggers a Telegram alert within 30 minutes of the filing being public.
2. No filing is ever alerted twice.
3. Dashboard renders < 1s for 90 days of data on a typical phone.
4. Operating cost: $0/month (GitHub free tier limits).
5. Code is split such that adding a fourth source (e.g. SEC Form 13F) requires only a new `sources/foo.py` and registering it in `main.py`.
