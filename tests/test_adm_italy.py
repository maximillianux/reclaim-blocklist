from __future__ import annotations

from pathlib import Path

from src.adapters.adm_italy import BASE_URL, INDEX_URL, AdmItalyAdapter

FIXTURES = Path(__file__).parent / "fixtures"


def _fake_http_get(responses: dict[str, str]):
    def _get(url: str) -> str:
        return responses[url]

    return _get


def test_adm_adapter_resolves_link_and_parses_domains() -> None:
    index_html = (FIXTURES / "adm_index_sample.html").read_text()
    list_txt = (FIXTURES / "adm_list_sample.txt").read_text()
    list_url = (
        BASE_URL
        + "/portale/documents/20182/114059352/elenco_siti_inibiti_giochi.txt/"
        "06a494fd-d135-680b-7a24-de79d1048f23"
    )

    adapter = AdmItalyAdapter(
        http_get=_fake_http_get({INDEX_URL: index_html, list_url: list_txt})
    )
    result = adapter.fetch()

    assert result.source_id == "adm-italy-inhibited"
    assert result.domains == {
        "01.mycoolcasino.com",
        "0101b00merang-bet.com",
        "01winshark1.com",
        "1-xbet10.com",
    }
    assert result.fetched_at.endswith("Z")


def test_adm_adapter_raises_if_link_missing() -> None:
    adapter = AdmItalyAdapter(http_get=_fake_http_get({INDEX_URL: "<html>no link here</html>"}))
    try:
        adapter.fetch()
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "elenco_siti_inibiti_giochi.txt" in str(exc)
