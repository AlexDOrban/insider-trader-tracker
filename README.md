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
