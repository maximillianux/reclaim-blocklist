from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from .adapters.adm_italy import AdmItalyAdapter
from .adapters.base import SourceAdapter
from .generate import build_blocker_list_bytes, build_manifest, next_version, run_pipeline

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs" / "blocklist" / "v1"
MANIFEST_PATH = DOCS_DIR / "manifest.json"
BLOCKER_PATH = DOCS_DIR / "blockerList.json"

RULES_URL = "https://maxostrander3.github.io/reclaim-blocklist/blocklist/v1/blockerList.json"
MIN_APP_VERSION = "1.0.0"

ADAPTERS: list[SourceAdapter] = [AdmItalyAdapter()]


def _load_previous() -> tuple[dict | None, set[str]]:
    manifest = json.loads(MANIFEST_PATH.read_text()) if MANIFEST_PATH.exists() else None
    domains: set[str] = set()
    if BLOCKER_PATH.exists():
        blocker = json.loads(BLOCKER_PATH.read_text())
        domains = {d.lstrip("*") for d in blocker[0]["trigger"]["if-domain"]}
    return manifest, domains


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the Reclaim gambling blocklist")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the added/removed domain diff without writing or committing files",
    )
    args = parser.parse_args(argv)

    result = run_pipeline(ADAPTERS)
    new_domains = {d.lstrip("*") for d in result.domains}
    blocker_bytes = build_blocker_list_bytes(result.domains)
    new_sha = hashlib.sha256(blocker_bytes).hexdigest()

    previous_manifest, previous_domains = _load_previous()

    if result.rejected:
        print(f"WARN: rejected {len(result.rejected)} invalid entries:", file=sys.stderr)
        for source_id, raw, reason in result.rejected[:20]:
            print(f"  [{source_id}] {raw!r}: {reason}", file=sys.stderr)
        if len(result.rejected) > 20:
            print(f"  ... and {len(result.rejected) - 20} more", file=sys.stderr)

    if args.dry_run:
        added = sorted(new_domains - previous_domains)
        removed = sorted(previous_domains - new_domains)
        print(f"Total domains: {len(new_domains)} (previously published: {len(previous_domains)})")
        print(f"Added ({len(added)}):")
        for d in added:
            print(f"  + {d}")
        print(f"Removed ({len(removed)}):")
        for d in removed:
            print(f"  - {d}")
        if not added and not removed:
            print("No changes -- would skip regeneration.")
        return 0

    if previous_manifest and previous_manifest.get("rulesSha256") == new_sha:
        print("No change in domain set; skipping regeneration.")
        return 0

    today = date.today()
    version = next_version(
        previous_manifest.get("version") if previous_manifest else None, today
    )
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    manifest = build_manifest(
        version=version,
        generated_at=generated_at,
        rules_url=RULES_URL,
        rules_bytes=blocker_bytes,
        domain_count=len(new_domains),
        sources=result.sources,
        min_app_version=MIN_APP_VERSION,
    )

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    BLOCKER_PATH.write_bytes(blocker_bytes)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"Wrote version {version}: {len(new_domains)} domains ({len(blocker_bytes)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
