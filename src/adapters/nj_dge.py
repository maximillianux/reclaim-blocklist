from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Callable

from ._http import default_http_get
from .base import SourceResult

INDEX_URL = (
    "https://www.njoag.gov/about/divisions-and-offices/"
    "division-of-gaming-enforcement-home/internet-gaming-sites/"
)


class _TableCellExtractor(HTMLParser):
    """Collects the flattened text of every <td> cell, grouped by row.

    The NJ DGE page is a hand-authored HTML table with no semantic
    markup (no classes/ids distinguishing a "domain" column) and stray
    inline anchors/spans inside cells. Rather than regex against that
    directly, we walk the table structure and treat any row with exactly
    3 cells -- number, checkmark icon, domain text -- as a data row; the
    two-column operator-name header rows (colspan across a single <td>)
    naturally have only 1 cell and are skipped.
    """

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "tr":
            self._row = []
        elif tag == "td" and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._cell is not None:
            self._row.append("".join(self._cell).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


class NjDgeAdapter:
    """New Jersey's Division of Gaming Enforcement publishes the
    authoritative list of internet gaming and sports wagering sites
    licensed to operate in NJ -- actual domains, not just operator/brand
    names, covering both the mainstream national sportsbooks and the
    long tail of NJ-specific casino/poker skins.
    """

    id = "nj-dge-igaming-sites"

    def __init__(
        self,
        index_url: str = INDEX_URL,
        http_get: Callable[[str], str] | None = None,
    ):
        self._index_url = index_url
        self._http_get = http_get or default_http_get

    def fetch(self) -> SourceResult:
        html = self._http_get(self._index_url)

        parser = _TableCellExtractor()
        parser.feed(html)

        domains: set[str] = set()
        for row in parser.rows:
            if len(row) != 3:
                continue
            text = row[2]
            if not text:
                continue
            for chunk in text.split(","):
                chunk = chunk.strip()
                if chunk:
                    domains.add(chunk)

        return SourceResult(
            source_id=self.id,
            fetched_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            domains=domains,
        )
