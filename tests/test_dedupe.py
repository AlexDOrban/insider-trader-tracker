from datetime import datetime, timezone, timedelta
from pathlib import Path

from tracker.dedupe import load_seen, save_seen, partition_new, prune_old


def test_load_seen_missing_returns_empty(tmp_path: Path):
    assert load_seen(tmp_path / "nope.json") == {}


def test_save_and_load_roundtrip(tmp_path: Path):
    p = tmp_path / "seen.json"
    save_seen(p, {"a:1": "2026-05-07T00:00:00+00:00"})
    assert load_seen(p) == {"a:1": "2026-05-07T00:00:00+00:00"}


def test_partition_new_separates_seen_from_unseen():
    seen = {"a:1": "2026-05-07T00:00:00+00:00"}
    ids = ["a:1", "a:2", "b:3"]
    new_ids, already = partition_new(ids, seen)
    assert new_ids == ["a:2", "b:3"]
    assert already == ["a:1"]


def test_prune_old_drops_entries_past_cutoff():
    now = datetime(2026, 5, 7, tzinfo=timezone.utc)
    cutoff = now - timedelta(days=90)
    seen = {
        "fresh": now.isoformat(),
        "old": (cutoff - timedelta(days=1)).isoformat(),
    }
    pruned = prune_old(seen, now=now, max_age_days=90)
    assert "fresh" in pruned
    assert "old" not in pruned
