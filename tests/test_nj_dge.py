from __future__ import annotations

from pathlib import Path

from src.adapters.nj_dge import INDEX_URL, NjDgeAdapter

FIXTURES = Path(__file__).parent / "fixtures"


def test_nj_dge_extracts_domains_and_skips_headers() -> None:
    html = (FIXTURES / "nj_dge_sample.html").read_text()
    adapter = NjDgeAdapter(http_get=lambda url: html)

    result = adapter.fetch()

    assert result.source_id == "nj-dge-igaming-sites"
    assert result.domains == {
        "play.ballybet.com",
        "casino.fanatics.com",
        "borgataonline.com/en/casino",
        "borgataonline.com/en/poker",
        "nj.betmgm.com/en/casino",
        "nj.betmgm.com/en/poker",
    }


def test_nj_dge_fetches_configured_url() -> None:
    seen_urls = []

    def fake_get(url: str) -> str:
        seen_urls.append(url)
        return "<table></table>"

    NjDgeAdapter(http_get=fake_get).fetch()
    assert seen_urls == [INDEX_URL]
