from __future__ import annotations

import re
import urllib.request
from datetime import datetime, timezone
from typing import Callable

from .base import SourceResult

INDEX_URL = "https://www.adm.gov.it/portale/en/siti-web-inibiti-giochi"
BASE_URL = "https://www.adm.gov.it"

# The index page links to a CMS-hosted document whose URL (including a
# document UUID) changes every time ADM republishes the list, so we resolve
# the current link from the index page on every run rather than hardcoding
# the document URL.
_LIST_LINK_RE = re.compile(
    r'href="([^"]*elenco_siti_inibiti_giochi\.txt[^"]*)"', re.IGNORECASE
)

_USER_AGENT = "reclaim-blocklist/1.0 (+https://github.com/maxostrander3/reclaim-blocklist)"


def _default_http_get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


class AdmItalyAdapter:
    """Italy's Agenzia delle Dogane e dei Monopoli (ADM) publishes an
    authoritative, government-maintained list of domains ordered blocked
    for illegal online gambling -- a plain-text file, one domain per line,
    with no scraping/parsing ambiguity beyond resolving the current link.
    """

    id = "adm-italy-inhibited"

    def __init__(
        self,
        index_url: str = INDEX_URL,
        http_get: Callable[[str], str] | None = None,
    ):
        self._index_url = index_url
        self._http_get = http_get or _default_http_get

    def fetch(self) -> SourceResult:
        index_html = self._http_get(self._index_url)
        match = _LIST_LINK_RE.search(index_html)
        if not match:
            raise RuntimeError(
                f"could not find elenco_siti_inibiti_giochi.txt link on {self._index_url}"
            )
        list_url = match.group(1)
        if list_url.startswith("/"):
            list_url = BASE_URL + list_url

        raw_text = self._http_get(list_url)
        domains = {line.strip() for line in raw_text.splitlines() if line.strip()}

        return SourceResult(
            source_id=self.id,
            fetched_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            domains=domains,
        )
