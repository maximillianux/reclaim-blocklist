# reclaim-blocklist

Generates and publishes the gambling-domain blocklist consumed by the
**Reclaim** iOS app's Safari Content Blocker. This repo only produces and
hosts the data; the app itself lives elsewhere.

A GitHub Actions workflow runs daily, pulls domains from one or more
upstream sources, normalizes/dedupes/sorts them, and publishes two static
JSON files via GitHub Pages.

## Public URLs

The app polls these two paths (locked in — do not change without updating
the app):

- Manifest (poll this frequently, it's small):
  `https://maximillianux.github.io/reclaim-blocklist/blocklist/v1/manifest.json`
- Rules (fetch only when `manifest.rulesSha256` changes):
  `https://maximillianux.github.io/reclaim-blocklist/blocklist/v1/blockerList.json`

The URL is fixed — it does not change per release. The app detects a new
release by comparing `manifest.rulesSha256` against the last SHA it saw,
not by relying on HTTP caching.

## How it works

```
adapters (raw domain strings) -> normalize.py -> merge/dedupe/sort -> two JSON files
```

- Each **source adapter** (`src/adapters/`) fetches from one upstream and
  returns a `SourceResult` with raw, unnormalized domain strings.
- `src/normalize.py` is the single place that validates and canonicalizes
  a raw string into a domain (lowercase, strip scheme/path/port, IDNA/UTS46
  encode, reject IPs/localhost/embedded wildcards/malformed labels). Every
  source is held to the same rules.
- `src/generate.py` merges all sources into one deduped, sorted set,
  enforces the 50,000-entry WebKit `if-domain` cap, and builds the manifest
  + blocker list bytes.
- `src/cli.py` orchestrates a run: compares the new rules SHA against the
  currently published one, and skips the commit entirely if nothing
  changed (no version bump, no write).

### Current sources

- **`adm-italy-inhibited`** (`src/adapters/adm_italy.py`) — Italy's Agenzia
  delle Dogane e dei Monopoli (ADM) publishes an authoritative,
  government-maintained plain-text list of domains ordered blocked for
  illegal online gambling (~12k+ domains). We originally planned to start
  with the UK Gambling Commission's unlicensed-operator list, but the UKGC
  does not publish operator/domain-level data — it's explicitly withheld
  under a law-enforcement FOIA exemption. ADM's list is real, scraping-free
  (it's a plain `.txt` file, one domain per line), and updated regularly,
  so it's the first adapter instead.

  The index page links to a CMS-hosted document whose URL (including a
  UUID) changes on every republish, so the adapter resolves the current
  link from the index page each run rather than hardcoding the document
  URL.

- **`nj-dge-igaming-sites`** (`src/adapters/nj_dge.py`) — New Jersey's
  Division of Gaming Enforcement publishes the authoritative list of
  internet gaming and sports wagering sites licensed in NJ, as actual
  domains (not just operator/brand names) — covers both mainstream
  national sportsbooks (`casino.draftkings.com`, `casino.fanduel.com`,
  `nj.betmgm.com`, ...) and the long tail of NJ-specific casino/poker
  skins. It's a hand-authored HTML table with no semantic markup, so the
  adapter walks the table structure (any row with exactly 3 cells —
  number, checkmark icon, domain text — is a data row) rather than
  regexing the page directly.

- **`known-us-operators`** (`src/adapters/known_operators.py`) — a
  hand-curated seed list (`src/adapters/data/known_us_operators.txt`) of
  major legal US gambling brands, verified against official sites/press
  as of the date noted in the file. This exists because government and
  state-licensee sources are structurally incapable of covering "every
  legal gambling brand": an illegal-operator blocklist by definition
  excludes legal operators, and any single state's registry misses
  brands not licensed in that state (e.g. DraftKings/FanDuel don't
  appear in ADM Italy's list because they're legal, and wouldn't appear
  in, say, a Michigan-only registry if they're not licensed there).
  Unlike the other adapters, this one reads a local file instead of
  fetching over the network — it changes only when someone edits it.
  **This list needs periodic manual re-verification**: operators
  rebrand (ESPN Bet → theScore Bet, Dec 2025), get acquired (PointsBet's
  US business folded into Fanatics in 2024), or exit markets (WynnBET
  scaled back to Nevada-resort-only) — don't assume a brand name maps to
  the "obvious" domain without checking.

## Adding a new source adapter

1. Create `src/adapters/<name>.py` implementing the `SourceAdapter`
   protocol from `src/adapters/base.py`:
   ```python
   class MyAdapter:
       id = "my-source-id"

       def fetch(self) -> SourceResult:
           ...  # return raw, unnormalized domain strings
   ```
   Accept an injectable `http_get` callable (see `adm_italy.py`) so the
   adapter is testable without network access.
2. Register an instance in the `ADAPTERS` list in `src/cli.py`.
3. Add unit tests under `tests/` with a fixture for the adapter's raw
   response format, plus normalizer edge cases specific to that source if
   it has a distinctive raw format.

Domain validation/normalization is centralized — adapters should not
normalize or filter domains themselves; just return what the source gave
you.

## Running locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

# Run tests
.venv/bin/pytest -q

# See what would change without writing/committing anything
.venv/bin/python -m src.cli --dry-run

# Actually generate docs/blocklist/v1/{manifest,blockerList}.json
.venv/bin/python -m src.cli
```

`cli.py` skips writing entirely if the domain set is unchanged since the
last published manifest (same `rulesSha256`), so running it twice in a row
with no upstream change is a no-op.

## One-time repo setup

1. **Enable GitHub Pages**: repo Settings → Pages → Source: "Deploy from a
   branch" → branch `main`, folder `/docs`.
2. **Allow the workflow to push**: repo Settings → Actions → General →
   Workflow permissions → "Read and write permissions". Required because
   `update-blocklist.yml` commits the regenerated files back to `main`.

The workflow (`.github/workflows/update-blocklist.yml`) runs daily at
04:00 UTC and can also be triggered manually via `workflow_dispatch`.

## Known limitation: caching headers

GitHub Pages does not support custom response headers (no way to set
`Cache-Control` per the spec's 5-min/immutable targets) — it serves
everything through its own CDN with GitHub-controlled caching. This is
fine for MVP: the app's actual change-detection is the SHA comparison in
the manifest, not HTTP cache semantics, so stale intermediate caching only
delays how soon a client sees a new manifest, it doesn't cause incorrect
behavior. If tighter cache control becomes necessary later, put a CDN
(e.g. Cloudflare) in front of the Pages site rather than switching hosts.

## Out of scope (this pass)

- Delta/patch files — the full list is small enough (~270KB at ~12.5k
  domains) that the app just re-downloads it whole.
- Per-user allowlists/customization — handled app-side.
- Auth, rate limiting, analytics.
- More state licensee registries (PA, MI, CO, etc.) — NJ is the first
  because its list conveniently ships actual domains in HTML; other
  states' registries may be PDF-only or company-name-only and need their
  own investigation before an adapter is worth writing.
