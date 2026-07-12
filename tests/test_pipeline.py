from __future__ import annotations

import hashlib
import json
from datetime import date

from src.adapters.base import SourceResult
from src.generate import (
    build_blocker_list_bytes,
    build_manifest,
    next_version,
    run_pipeline,
)


class FakeAdapter:
    def __init__(self, source_id: str, domains: set[str]):
        self.id = source_id
        self._domains = domains

    def fetch(self) -> SourceResult:
        return SourceResult(
            source_id=self.id, fetched_at="2026-07-11T03:58:12Z", domains=self._domains
        )


def test_pipeline_merges_dedupes_and_sorts_across_sources() -> None:
    a = FakeAdapter("source-a", {"Bet365.com", "http://foo.com", "dup.com"})
    b = FakeAdapter("source-b", {"DUP.COM", "bar.com", "192.168.1.1", "localhost"})

    result = run_pipeline([a, b])

    assert result.domains == sorted(
        {"*bet365.com", "*foo.com", "*dup.com", "*bar.com"}
    )
    assert len(result.rejected) == 2  # the IP and localhost from source-b

    counts = {s.id: s.domain_count for s in result.sources}
    assert counts == {"source-a": 3, "source-b": 2}


def test_pipeline_output_is_deterministic() -> None:
    a = FakeAdapter("source-a", {"Foo.com", "bar.com", "baz.com"})

    result1 = run_pipeline([a])
    result2 = run_pipeline([a])

    bytes1 = build_blocker_list_bytes(result1.domains)
    bytes2 = build_blocker_list_bytes(result2.domains)

    assert bytes1 == bytes2
    assert hashlib.sha256(bytes1).hexdigest() == hashlib.sha256(bytes2).hexdigest()

    doc = json.loads(bytes1)
    assert doc == [
        {
            "action": {"type": "block"},
            "trigger": {
                "url-filter": ".*",
                "if-domain": ["*bar.com", "*baz.com", "*foo.com"],
            },
        }
    ]


def test_pipeline_raises_over_cap(monkeypatch) -> None:
    import src.generate as generate_module

    monkeypatch.setattr(generate_module, "MAX_DOMAINS", 2)
    a = FakeAdapter("source-a", {"foo.com", "bar.com", "baz.com"})

    try:
        run_pipeline([a])
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "exceeding" in str(exc)


def test_manifest_fields_and_sha_match_bytes() -> None:
    domains = ["*bar.com", "*foo.com"]
    rules_bytes = build_blocker_list_bytes(domains)

    manifest = build_manifest(
        version="2026.07.11-1",
        generated_at="2026-07-11T04:00:00Z",
        rules_url="https://example.github.io/repo/blocklist/v1/blockerList.json",
        rules_bytes=rules_bytes,
        domain_count=len(domains),
        sources=[],
        min_app_version="1.0.0",
    )

    assert manifest["rulesSha256"] == hashlib.sha256(rules_bytes).hexdigest()
    assert manifest["rulesByteSize"] == len(rules_bytes)
    assert manifest["domainCount"] == 2
    assert manifest["schemaVersion"] == 1


def test_next_version_increments_same_day() -> None:
    today = date(2026, 7, 11)
    assert next_version(None, today) == "2026.07.11-1"
    assert next_version("2026.07.11-1", today) == "2026.07.11-2"
    assert next_version("2026.07.10-3", today) == "2026.07.11-1"
