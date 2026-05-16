from code_diligence.heuristics.fte import (
    AuthorActivity,
    classify,
    classify_all,
    _signal_bot,
    _signal_domain,
    _signal_cadence,
    _signal_tenure,
    _signal_breadth,
)


def _activity(**kw) -> AuthorActivity:
    defaults = dict(
        email="user@acme.com",
        name="User",
        target_domain="acme.com",
        tenure_days=400,
        total_commits=200,
        repos_touched=10,
        weekday_commit_pct=0.9,
        burstiness=0.1,
    )
    defaults.update(kw)
    return AuthorActivity(**defaults)


def test_signal_bot_detects_dependabot() -> None:
    a = _activity(email="dependabot[bot]@users.noreply.github.com", name="dependabot[bot]")
    assert _signal_bot(a) == 1.0


def test_signal_bot_zero_for_human() -> None:
    a = _activity(email="alice@acme.com", name="Alice")
    assert _signal_bot(a) == 0.0


def test_signal_domain_exact_match() -> None:
    a = _activity(email="alice@acme.com", target_domain="acme.com")
    assert _signal_domain(a) == 1.0


def test_signal_domain_free_provider_low() -> None:
    a = _activity(email="alice@gmail.com", target_domain="acme.com")
    assert _signal_domain(a) == 0.1


def test_signal_domain_unknown_corporate_mid() -> None:
    a = _activity(email="alice@vendor.com", target_domain="acme.com")
    assert _signal_domain(a) == 0.4


def test_signal_cadence_high_for_steady_weekday() -> None:
    a = _activity(weekday_commit_pct=0.9, burstiness=0.1)
    # 0.6 * 0.9 + 0.4 * 0.9 = 0.9
    assert _signal_cadence(a) >= 0.85


def test_signal_cadence_low_for_burst_weekend() -> None:
    a = _activity(weekday_commit_pct=0.3, burstiness=0.9)
    # 0.6 * 0.3 + 0.4 * 0.1 = 0.22
    assert _signal_cadence(a) < 0.3


def test_signal_tenure_long() -> None:
    assert _signal_tenure(_activity(tenure_days=400)) == 1.0


def test_signal_tenure_short() -> None:
    assert _signal_tenure(_activity(tenure_days=20)) == 0.1


def test_signal_breadth_many_repos() -> None:
    assert _signal_breadth(_activity(repos_touched=12)) == 1.0


def test_signal_breadth_single_repo() -> None:
    assert _signal_breadth(_activity(repos_touched=1)) == 0.1


def test_classify_fte_high_confidence() -> None:
    a = _activity(
        email="alice@acme.com", target_domain="acme.com",
        tenure_days=540, total_commits=200, repos_touched=12,
        weekday_commit_pct=0.9, burstiness=0.1,
    )
    result = classify(a)
    assert result.label == "fte"
    assert result.confidence >= 0.85


def test_classify_contractor() -> None:
    a = _activity(
        email="contractor@vendor.com", target_domain="acme.com",
        tenure_days=45, total_commits=15, repos_touched=1,
        weekday_commit_pct=0.4, burstiness=0.9,
    )
    result = classify(a)
    assert result.label == "contractor"
    assert result.confidence >= 0.7


def test_classify_bot_short_circuits() -> None:
    a = _activity(
        email="dependabot[bot]@users.noreply.github.com",
        name="dependabot[bot]",
        target_domain="acme.com",
        # Even with FTE-like signals, bot detection wins
        tenure_days=400, total_commits=200, repos_touched=10,
    )
    result = classify(a)
    assert result.label == "bot"
    assert result.confidence >= 0.95
    assert "bot" in result.signals


def test_classify_unknown_for_mixed_signals() -> None:
    # FTE domain but contractor cadence/tenure/breadth
    a = _activity(
        email="alice@acme.com", target_domain="acme.com",
        tenure_days=45, total_commits=15, repos_touched=1,
        weekday_commit_pct=0.4, burstiness=0.9,
    )
    result = classify(a)
    assert result.label == "unknown"
    # Signals dict exposed for transparency
    assert set(result.signals.keys()) == {"domain", "cadence", "tenure", "breadth"}


def test_classify_all_processes_iterable() -> None:
    activities = [
        _activity(email="alice@acme.com"),
        _activity(email="bob@acme.com"),
    ]
    results = classify_all(activities)
    assert len(results) == 2
    assert all(r.label in {"fte", "contractor", "bot", "unknown"} for r in results)
