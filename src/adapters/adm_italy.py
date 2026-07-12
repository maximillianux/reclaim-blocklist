from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urljoin, urlparse

from ._http import default_http_get
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
        self._http_get = http_get or default_http_get

    def fetch(self) -> SourceResult:
        index_html = self._http_get(self._index_url)
        match = _LIST_LINK_RE.search(index_html)
        if not match:
            raise RuntimeError(
                f"could not find elenco_siti_inibiti_giochi.txt link on {self._index_url}"
            )
        list_url = urljoin(self._index_url, match.group(1))
        if urlparse(list_url).netloc != urlparse(BASE_URL).netloc:
            raise RuntimeError(
                f"refusing to fetch list from unexpected host: {list_url!r}"
            )

        raw_text = self._http_get(list_url)
        domains = {line.strip() for line in raw_text.splitlines() if line.strip()}

        return SourceResult(
            source_id=self.id,
            fetched_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            domains=domains,
        )
