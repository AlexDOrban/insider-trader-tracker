from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from sources.filing import Filing, filing_to_dict, filing_from_dict
from sources import house_ptr, senate_ptr, sec_form4
from tracker.dedupe import load_seen, save_seen, prune_old, partition_new
from tracker.threshold import classify, ThresholdConfig
from tracker.telegram_format import format_alert, format_digest
from tracker.errors import load_state as load_err, save_state as save_err, record_result, should_alert
from telegram_notify import send_message
from build_dashboard import render_dashboard

FETCHERS: dict[str, Callable[[], list[Filing]]] = {
    "house": house_ptr.fetch,
    "senate": senate_ptr.fetch,
    "form4": sec_form4.fetch,
}


def _load_filings_history(path: Path) -> list[Filing]:
    if not path.exists():
        return []
    return [filing_from_dict(d) for d in json.loads(path.read_text())]


def _save_filings_history(path: Path, filings: list[Filing]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([filing_to_dict(f) for f in filings], indent=2))


def _trim_history(filings: list[Filing], days: int = 90, now: datetime | None = None) -> list[Filing]:
    now = now or datetime.now(timezone.utc)
    keep: list[Filing] = []
    for f in filings:
        try:
            t = datetime.fromisoformat(f.filed_at)
        except ValueError:
            continue
        if (now - t).days <= days:
            keep.append(f)
    return keep


def run(
    *,
    seen_path: Path,
    data_path: Path,
    errors_path: Path,
    template_dir: Path,
    out_html: Path,
    out_data: Path,
    dashboard_url: str,
    min_congress: float,
    min_form4: float,
    include_lower_insiders: bool,
) -> None:
    now = datetime.now(timezone.utc)
    cfg = ThresholdConfig(
        min_congress=min_congress,
        min_form4=min_form4,
        include_lower_insiders=include_lower_insiders,
    )
    seen = prune_old(load_seen(seen_path), now=now, max_age_days=90)
    err_state = load_err(errors_path)

    all_new: list[Filing] = []
    for source_name, fetcher in FETCHERS.items():
        try:
            filings = fetcher()
            err_state = record_result(err_state, source_name, ok=True)
        except Exception as e:
            err_state = record_result(err_state, source_name, ok=False)
            if should_alert(err_state, source_name, threshold=3):
                try:
                    send_message(f"Source <b>{source_name}</b> failed 3 polls in a row: {e}")
                except Exception:
                    pass
            continue
        ids = [f.id for f in filings]
        new_ids, _ = partition_new(ids, seen)
        new_set = set(new_ids)
        all_new.extend(f for f in filings if f.id in new_set)

    for f in all_new:
        seen[f.id] = now.isoformat()
    save_seen(seen_path, seen)
    save_err(errors_path, err_state)

    bigs = [f for f in all_new if classify(f, cfg) == "big"]
    if bigs:
        try:
            if len(bigs) <= 5:
                for f in bigs:
                    send_message(format_alert(f, dashboard_url))
            else:
                send_message(format_digest(bigs, dashboard_url))
        except Exception as e:
            print(f"telegram error: {e}", file=sys.stderr)

    history = _load_filings_history(data_path)
    history.extend(all_new)
    history = _trim_history(history, days=90, now=now)
    _save_filings_history(data_path, history)
    render_dashboard(
        filings=history,
        last_poll=now.isoformat(),
        template_dir=template_dir,
        out_html=out_html,
        out_data=out_data,
        min_congress=min_congress,
        min_form4=min_form4,
        include_lower_insiders=include_lower_insiders,
    )


def main() -> int:
    repo = Path(__file__).parent
    dashboard_url = os.environ.get("DASHBOARD_URL", "")
    run(
        seen_path=repo / "seen.json",
        data_path=repo / "data" / "filings.json",
        errors_path=repo / "errors.json",
        template_dir=repo / "templates",
        out_html=repo / "docs" / "index.html",
        out_data=repo / "docs" / "data.json",
        dashboard_url=dashboard_url,
        min_congress=float(os.environ.get("MIN_CONGRESS", "50000")),
        min_form4=float(os.environ.get("MIN_FORM4", "500000")),
        include_lower_insiders=os.environ.get("INCLUDE_LOWER_INSIDERS", "0") == "1",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
