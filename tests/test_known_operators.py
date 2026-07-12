from __future__ import annotations

from pathlib import Path

from src.adapters.known_operators import DATA_PATH, KnownOperatorsAdapter
from src.normalize import InvalidDomainError, normalize_domain


def test_reads_real_data_file_and_ignores_comments_and_blanks(tmp_path: Path) -> None:
    fixture = tmp_path / "operators.txt"
    fixture.write_text(
        "# comment\n"
        "\n"
        "draftkings.com\n"
        "   \n"
        "# another comment\n"
        "fanduel.com\n"
    )

    result = KnownOperatorsAdapter(data_path=fixture).fetch()

    assert result.source_id == "known-us-operators"
    assert result.domains == {"draftkings.com", "fanduel.com"}


def test_real_shipped_data_file_is_nonempty_and_all_entries_normalize() -> None:
    adapter = KnownOperatorsAdapter()
    result = adapter.fetch()

    assert len(result.domains) >= 15

    for raw in result.domains:
        try:
            normalize_domain(raw)
        except InvalidDomainError as exc:
            raise AssertionError(f"curated entry {raw!r} fails normalization: {exc}")


def test_default_data_path_points_at_real_file() -> None:
    assert DATA_PATH.exists()
