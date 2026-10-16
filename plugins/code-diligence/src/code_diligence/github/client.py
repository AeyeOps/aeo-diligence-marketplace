"""Minimal GitHub REST client: auth, pagination, rate-limit handling."""
import re
import time
from collections.abc import Iterator
from typing import Self
from urllib.parse import urlsplit

import httpx

_NEXT_LINK_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


_BASE_URL = "https://api.github.com"


class GitHubClient:
    def __init__(self, token: str, *, base_url: str = _BASE_URL) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "code-diligence/0.1.0",
        }
        self._client = httpx.Client(headers=self._headers, timeout=30.0)
        self._next_reset_at: int | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._client.close()

    def get(self, path_or_url: str, **params) -> httpx.Response:

        if self._next_reset_at is not None:
            now = int(time.time())
            if now < self._next_reset_at:
                time.sleep(self._next_reset_at - now + 1)
            self._next_reset_at = None


        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            url = path_or_url
        else:
            url = self._base_url + path_or_url

        if urlsplit(url)[:2] != urlsplit(self._base_url)[:2]:
            raise ValueError("GitHub request URL must use the configured API origin")
        response = self._client.get(url, params=params if params else None)


        if response.status_code in (403, 429):
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                time.sleep(int(retry_after) + 1)
                response = self._client.get(url, params=params if params else None)


        if response.headers.get("X-RateLimit-Remaining") == "0":
            self._next_reset_at = int(response.headers["X-RateLimit-Reset"])

        response.raise_for_status()
        return response


def paginate(client: GitHubClient, path: str, *, items_key: str | None = None, **params) -> Iterator[dict]:
    """Yield every result across paginated GitHub responses."""
    params = {"per_page": 100, "page": 1, **params}
    url = path
    while True:
        response = client.get(url, **params)
        payload = response.json()
        items = payload if items_key is None else payload[items_key]
        for item in items:
            yield item
        link = response.headers.get("Link", "")
        m = _NEXT_LINK_RE.search(link)
        if not m:
            break
        url = m.group(1)
        params = {}
