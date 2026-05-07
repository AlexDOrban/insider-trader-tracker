from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def load_seen(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_seen(path: Path, seen: dict[str, str]) -> None:
    path.write_text(json.dumps(seen, indent=2, sort_keys=True))


def partition_new(ids: list[str], seen: dict[str, str]) -> tuple[list[str], list[str]]:
    new_ids = [i for i in ids if i not in seen]
    already = [i for i in ids if i in seen]
    return new_ids, already


def prune_old(
    seen: dict[str, str],
    now: datetime | None = None,
    max_age_days: int = 90,
) -> dict[str, str]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=max_age_days)
    keep: dict[str, str] = {}
    for fid, ts in seen.items():
        try:
            t = datetime.fromisoformat(ts)
        except ValueError:
            continue
        if t >= cutoff:
            keep[fid] = ts
    return keep
