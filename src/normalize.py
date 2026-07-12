from __future__ import annotations

import ipaddress
import re

import idna

_LABEL_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")


class InvalidDomainError(ValueError):
    """Raised when a raw source entry cannot be normalized to a valid,
    blockable domain."""


def _strip_wrapper(raw: str) -> str:
    s = raw.strip()
    s = _SCHEME_RE.sub("", s)
    s = s.split("/", 1)[0]
    s = s.split("?", 1)[0]
    s = s.split("#", 1)[0]
    s = s.split("@", 1)[-1]  # drop userinfo, e.g. user:pass@host
    if s.startswith("*."):
        # A leading "*." from a source is equivalent to the bare domain --
        # we add our own "*" prefix later for the Safari content blocker.
        s = s[2:]
    if not s.startswith("[") and s.count(":") == 1:
        s = s.split(":", 1)[0]  # drop :port
    s = s.rstrip(".")  # trailing root dot
    return s


def normalize_domain(raw: str) -> str:
    """Normalize a raw domain/URL string to a canonical ASCII domain.

    Raises InvalidDomainError if the input can't be normalized to a valid,
    blockable domain (IP address, localhost, embedded wildcard, malformed
    label, etc).
    """
    if raw is None:
        raise InvalidDomainError("empty input")

    s = _strip_wrapper(raw)
    if not s:
        raise InvalidDomainError(f"empty after stripping: {raw!r}")

    if s.startswith("["):
        raise InvalidDomainError(f"IPv6 literal: {raw!r}")

    if "*" in s:
        raise InvalidDomainError(f"embedded wildcard: {raw!r}")

    s = s.lower()

    is_ip_address = True
    try:
        ipaddress.ip_address(s)
    except ValueError:
        is_ip_address = False
    if is_ip_address:
        raise InvalidDomainError(f"IP address: {raw!r}")

    if s in ("localhost", "localhost.localdomain"):
        raise InvalidDomainError(f"localhost: {raw!r}")

    try:
        ascii_domain = idna.encode(s, uts46=True).decode("ascii")
    except idna.IDNAError as exc:
        raise InvalidDomainError(f"IDNA encode failed for {raw!r}: {exc}") from exc
    except UnicodeError as exc:
        raise InvalidDomainError(f"encode failed for {raw!r}: {exc}") from exc

    labels = ascii_domain.split(".")
    if len(labels) < 2:
        raise InvalidDomainError(f"single-label host: {raw!r}")

    for label in labels:
        if not _LABEL_RE.match(label):
            raise InvalidDomainError(f"invalid label {label!r} in {raw!r}")

    return ascii_domain
