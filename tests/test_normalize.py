from __future__ import annotations

import idna
import pytest

from src.normalize import InvalidDomainError, normalize_domain


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("bet365.com", "bet365.com"),
        ("BET365.COM", "bet365.com"),
        ("Bet365.Com", "bet365.com"),
        ("example.com.", "example.com"),
        ("http://example.com", "example.com"),
        ("https://example.com", "example.com"),
        ("https://example.com/some/path", "example.com"),
        ("https://example.com/path?query=1", "example.com"),
        ("https://example.com/path#frag", "example.com"),
        ("https://example.com:8080", "example.com"),
        ("user:pass@example.com", "example.com"),
        ("  example.com  ", "example.com"),
        ("*.example.com", "example.com"),
        ("sub.example.com", "sub.example.com"),
    ],
)
def test_normalize_valid_inputs(raw: str, expected: str) -> None:
    assert normalize_domain(raw) == expected


def test_normalize_idn_domain() -> None:
    raw = "münchen-wetten.de"
    expected = idna.encode(raw.lower(), uts46=True).decode("ascii")
    assert normalize_domain(raw) == expected
    assert normalize_domain(raw).startswith("xn--")


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "192.168.1.1",
        "8.8.8.8",
        "::1",
        "[::1]",
        "[::1]:8080",
        "localhost",
        "localhost.localdomain",
        "sub.*.evil.com",
        "evil*.com",
        "no-dot-at-all",
        "-example.com",
        "example-.com",
        "exa..mple.com",
        None,
    ],
)
def test_normalize_rejects_invalid_inputs(raw) -> None:
    with pytest.raises(InvalidDomainError):
        normalize_domain(raw)


def test_normalize_is_idempotent() -> None:
    once = normalize_domain("HTTP://Example.COM/path")
    twice = normalize_domain(once)
    assert once == twice == "example.com"
