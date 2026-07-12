from __future__ import annotations

import urllib.request

USER_AGENT = "reclaim-blocklist/1.0 (+https://github.com/maximillianux/reclaim-blocklist)"


def default_http_get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")
