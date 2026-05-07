# Insider Trader Tracker

Tracks high-conviction insider trading activity from US House PTR, US Senate PTR, and SEC Form 4. Pushes Telegram alerts above thresholds and publishes a static dashboard on GitHub Pages.

See [`docs/superpowers/specs/2026-05-07-insider-trader-tracker-design.md`](docs/superpowers/specs/2026-05-07-insider-trader-tracker-design.md) for the design.

## Setup

1. Copy `.env.example` to `.env` and fill in `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `SEC_USER_AGENT`.
2. `pip install -r requirements.txt`
3. `python main.py` for a one-shot run.

## Deployment

- Add the env vars as GitHub Actions repo secrets.
- Enable GitHub Pages from `/docs` on `main` branch.
- The `poll.yml` workflow runs every 15 minutes.

## Tests

`pytest`

## Known limitations (v1)

- **Senate PTR scraper is brittle.** The current parser expects an HTML results table at `efdsearch.senate.gov/search/report/data/`, but the live endpoint returns DataTables JSON and requires a CSRF token. The fixture-based tests pass, but the scraper may return zero results in production until v1.1 rewrites it against the real JSON API.
- **House and Senate filings have no per-line ticker / value / action data in v1.** The line-item PDFs are not parsed, so Congress rows show no ticker and no size on the dashboard, and Congress filings never trigger Telegram alerts (the threshold classifier requires a numeric `value_low`). Dashboard surfaces them with the "View filing" link to the PDF.
- **No EDGAR rate limiting.** Each poll fans out up to ~80 HTTP calls to SEC EDGAR with no delay. SEC's stated limit is 10 req/s; we stay under but bursty. v1.1 should add a 100ms inter-request sleep.
