"""Shared card destinations and deterministic, locally generated QR images."""

import re
from urllib.parse import urlsplit

import segno

PAGES = ("videos.html", "state-emergency-agencies.html", "index.html")


def site_urls(base: str) -> list[str | None]:
    if re.fullmatch(r"\[\[VERIFY(?::[^\n]+)?\]\]", base):
        return [None] * len(PAGES)
    parsed = urlsplit(base)
    port = parsed.port
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or "?" in base
        or "#" in base
        or "\\" in base
        or port == 0
        or any(character.isspace() or ord(character) < 32 for character in base)
    ):
        raise ValueError("Use an HTTPS site directory URL without credentials, query or fragment")
    return [base.rstrip("/") + "/" + path for path in PAGES]


def card_links(base: str, labels: list[str]) -> list[dict]:
    if len(labels) != len(PAGES):
        raise ValueError("The card needs one label for each of its three destinations")
    return [
        {
            "label": label,
            "url": url,
            "image": segno.make(url, error="m", micro=False, boost_error=False).svg_data_uri(
                scale=1, border=4
            )
            if url
            else None,
            "unconfirmed": base if url is None else None,
        }
        for label, url in zip(labels, site_urls(base), strict=True)
    ]
