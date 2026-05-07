from tracker.errors import record_result, should_alert, load_state, save_state


def test_first_failure_does_not_alert(tmp_path):
    p = tmp_path / "errors.json"
    state = load_state(p)
    state = record_result(state, "house", ok=False)
    assert should_alert(state, "house", threshold=3) is False
    save_state(p, state)


def test_three_consecutive_failures_alerts_once(tmp_path):
    p = tmp_path / "errors.json"
    state = load_state(p)
    for _ in range(3):
        state = record_result(state, "house", ok=False)
    assert should_alert(state, "house", threshold=3) is True
    state = record_result(state, "house", ok=False)
    assert should_alert(state, "house", threshold=3) is False


def test_success_resets_streak(tmp_path):
    p = tmp_path / "errors.json"
    state = load_state(p)
    for _ in range(3):
        state = record_result(state, "form4", ok=False)
    assert should_alert(state, "form4", threshold=3) is True
    state = record_result(state, "form4", ok=True)
    state = record_result(state, "form4", ok=False)
    assert should_alert(state, "form4", threshold=3) is False


def test_state_isolated_per_source(tmp_path):
    p = tmp_path / "errors.json"
    state = load_state(p)
    state = record_result(state, "house", ok=False)
    state = record_result(state, "senate", ok=True)
    assert state["house"]["consecutive_failures"] == 1
    assert state["senate"]["consecutive_failures"] == 0
