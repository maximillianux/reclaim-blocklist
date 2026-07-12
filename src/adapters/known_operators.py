from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .base import SourceResult

DATA_PATH = Path(__file__).parent / "data" / "known_us_operators.txt"


class KnownOperatorsAdapter:
    """Hand-curated seed list of major legal US gambling operators.

    Unlike the other adapters, this one reads a local, manually
    maintained file rather than fetching from a network source -- see
    `data/known_us_operators.txt` for why this list needs to exist
    alongside the regulator-sourced adapters.
    """

    id = "known-us-operators"

    def __init__(self, data_path: Path = DATA_PATH):
        self._data_path = data_path

    def fetch(self) -> SourceResult:
        lines = self._data_path.read_text().splitlines()
        domains = {
            line.strip()
            for line in lines
            if line.strip() and not line.strip().startswith("#")
        }
        return SourceResult(
            source_id=self.id,
            fetched_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            domains=domains,
        )
