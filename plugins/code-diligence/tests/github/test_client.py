"""Mock-based tests for the GitHub client. No real API calls."""
import pytest
import httpx
from code_diligence.github.client import GitHubClient, paginate


def test_paginate_handles_link_header(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://api.github.com/repos/x/y/pulls?per_page=100&page=1",
        json=[{"number": 1}, {"number": 2}],
        headers={"Link": '<https://api.github.com/repos/x/y/pulls?per_page=100&page=2>; rel="next"'},
    )
    httpx_mock.add_response(
        url="https://api.github.com/repos/x/y/pulls?per_page=100&page=2",
        json=[{"number": 3}],
        headers={},
    )
    client = GitHubClient(token="test")
    results = list(paginate(client, "/repos/x/y/pulls"))
    assert [r["number"] for r in results] == [1, 2, 3]


def test_rate_limit_waits(httpx_mock, monkeypatch) -> None:
    """When response says X-RateLimit-Remaining: 0, client sleeps until reset."""
    sleep_calls = []
    monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))
    import time as _time
    httpx_mock.add_response(
        url="https://api.github.com/test",
        status_code=200, json={"ok": True},
        headers={
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(_time.time()) + 5),
        },
    )
    httpx_mock.add_response(url="https://api.github.com/test", json={"ok": True})
    client = GitHubClient(token="test")
    client.get("/test")
    client.get("/test")  # second call should trigger sleep on the prior reset
    assert any(0 < s <= 10 for s in sleep_calls)
