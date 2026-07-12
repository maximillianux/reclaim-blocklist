from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date

from .adapters.base import SourceAdapter
from .normalize import InvalidDomainError, normalize_domain

MAX_DOMAINS = 50_000
WARN_DOMAINS = int(MAX_DOMAINS * 0.9)
SCHEMA_VERSION = 1


@dataclass
class SourceSummary:
    id: str
    fetched_at: str
    domain_count: int


@dataclass
class PipelineResult:
    domains: list[str]  # final "*domain" entries, deduped and sorted
    sources: list[SourceSummary] = field(default_factory=list)
    rejected: list[tuple[str, str, str]] = field(default_factory=list)  # (source_id, raw, reason)


def run_pipeline(adapters: list[SourceAdapter]) -> PipelineResult:
    merged: set[str] = set()
    sources: list[SourceSummary] = []
    rejected: list[tuple[str, str, str]] = []

    for adapter in adapters:
        result = adapter.fetch()
        valid_count = 0
        for raw in result.domains:
            try:
                normalized = normalize_domain(raw)
            except InvalidDomainError as exc:
                rejected.append((result.source_id, raw, str(exc)))
                continue
            merged.add(normalized)
            valid_count += 1
        sources.append(SourceSummary(result.source_id, result.fetched_at, valid_count))

    if len(merged) > MAX_DOMAINS:
        raise RuntimeError(
            f"domain set has {len(merged)} entries, exceeding the WebKit "
            f"if-domain cap of {MAX_DOMAINS}"
        )
    if len(merged) > WARN_DOMAINS:
        print(
            f"WARNING: domain set has {len(merged)} entries, approaching "
            f"the WebKit cap of {MAX_DOMAINS}"
        )

    prefixed = sorted(f"*{d}" for d in merged)
    return PipelineResult(domains=prefixed, sources=sources, rejected=rejected)


def build_blocker_list_bytes(domains: list[str]) -> bytes:
    doc = [
        {
            "action": {"type": "block"},
            "trigger": {"url-filter": ".*", "if-domain": domains},
        }
    ]
    return json.dumps(doc, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def build_manifest(
    *,
    version: str,
    generated_at: str,
    rules_url: str,
    rules_bytes: bytes,
    domain_count: int,
    sources: list[SourceSummary],
    min_app_version: str,
) -> dict:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "version": version,
        "generatedAt": generated_at,
        "rulesUrl": rules_url,
        "rulesSha256": hashlib.sha256(rules_bytes).hexdigest(),
        "rulesByteSize": len(rules_bytes),
        "domainCount": domain_count,
        "sources": [
            {"id": s.id, "fetchedAt": s.fetched_at, "domainCount": s.domain_count}
            for s in sources
        ],
        "minAppVersion": min_app_version,
    }


def next_version(previous_version: str | None, today: date) -> str:
    prefix = today.strftime("%Y.%m.%d")
    if previous_version and previous_version.startswith(prefix + "-"):
        try:
            n = int(previous_version.rsplit("-", 1)[1])
        except ValueError:
            n = 0
        return f"{prefix}-{n + 1}"
    return f"{prefix}-1"
