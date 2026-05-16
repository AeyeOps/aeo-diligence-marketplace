"""Minimal GitHub REST client: auth, pagination, rate-limit handling."""
import re
import time
from typing import Iterator

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

    def get(self, path_or_url: str, **params) -> httpx.Response:
        # If we previously saw remaining=0, sleep until reset
        if self._next_reset_at is not None:
            now = int(time.time())
            if now < self._next_reset_at:
                time.sleep(self._next_reset_at - now + 1)
            self._next_reset_at = None

        # Build absolute URL from path if not already absolute
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            url = path_or_url
        else:
            url = self._base_url + path_or_url

        response = self._client.get(url, params=params if params else None)

        # Handle secondary rate limit
        if response.status_code in (403, 429):
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                time.sleep(int(retry_after) + 1)
                response = self._client.get(url, params=params if params else None)

        # Track primary rate limit
        if response.headers.get("X-RateLimit-Remaining") == "0":
            self._next_reset_at = int(response.headers["X-RateLimit-Reset"])

        response.raise_for_status()
        return response


def paginate(client: GitHubClient, path: str, **params) -> Iterator[dict]:
    """Yield every result across paginated GitHub responses."""
    params = {"per_page": 100, "page": 1, **params}
    url = path
    while True:
        response = client.get(url, **params)
        for item in response.json():
            yield item
        link = response.headers.get("Link", "")
        m = _NEXT_LINK_RE.search(link)
        if not m:
            break
        url = m.group(1)
        params = {}  # next-link URL has its own query
