from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SourceResult:
    """Raw output of a single source adapter, before normalization."""

    source_id: str
    fetched_at: str  # ISO8601 UTC, e.g. "2026-07-11T03:58:12Z"
    domains: set[str]  # raw strings exactly as the source returned them


class SourceAdapter(Protocol):
    """Contract every source adapter must satisfy.

    To add a new source: implement this protocol in a new module under
    `src/adapters/`, then register an instance in the `ADAPTERS` list in
    `src/cli.py`. Adapters should return raw, unnormalized strings —
    normalization/validation happens once, centrally, in `src/normalize.py`,
    so every source is held to the same rules.
    """

    id: str

    def fetch(self) -> SourceResult: ...
