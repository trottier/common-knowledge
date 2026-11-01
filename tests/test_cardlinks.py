from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from pypdf import PdfReader

from ck.cardlinks import PAGES, card_links, site_urls
from ck.config import Build, load_config
from ck.publication import build_site
from ck.render import render_pdf

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "url",
    [
        "http://example.invalid/",
        "javascript:alert(1)",
        "//example.invalid/",
        "https://user:secret@example.invalid/",
        "https://example.invalid/?",
        "https://example.invalid/#",
        "https://example.invalid/a b",
        "https://example.invalid:0/",
        "https://example.invalid:abc/",
        "https://example.invalid\\other/",
    ],
)
def test_card_destination_configuration_rejects_unsafe_or_ambiguous_bases(url):
    values = load_config(ROOT).build.model_dump()
    with pytest.raises(ValueError):
        Build.model_validate({**values, "site_base_url": url})


def test_unconfirmed_site_does_not_generate_a_scannable_placeholder():
    marker = "[[VERIFY: publisher site URL]]"
    links = card_links(marker, ["Videos", "Agencies", "Verify"])
    assert len(links) == 3
    assert all(link["url"] is None and link["image"] is None for link in links)
    assert all(link["unconfirmed"] == marker for link in links)


def test_every_card_destination_is_built_without_remote_resources(tmp_path):
    build_site(ROOT, [], tmp_path / "site", "trottier/common-knowledge")
    for page in PAGES:
        soup = BeautifulSoup((tmp_path / "site" / page).read_text(), "html.parser")
        assert not soup.select("script, iframe, img, link, audio, video")
        assert soup.select_one('meta[http-equiv="Content-Security-Policy"]')
        for link in soup.select("nav a"):
            assert (tmp_path / "site" / link["href"]).is_file()
    assert (
        "https://www.usa.gov/state-emergency-management"
        in (tmp_path / "site" / PAGES[1]).read_text()
    )


@pytest.mark.parametrize("code", ["en", "es"])
def test_real_card_codes_keep_two_pages_and_match_clickable_destinations(code, tmp_path):
    config = load_config(ROOT)
    config.build.site_base_url = "https://example.invalid/common-knowledge/"
    language = next(item for item in config.languages if item.code == code)
    output = tmp_path / f"{code}.pdf"
    render_pdf(
        ROOT,
        config,
        ROOT / f"content/{code}/card.md",
        language,
        "print",
        output,
        946684800,
        template="card.html.j2",
    )
    reader = PdfReader(output)
    assert len(reader.pages) == 2
    document = output.with_suffix(".html").read_text()
    soup = BeautifulSoup(document, "html.parser")
    codes = soup.select(".front .qr a")
    assert [link["href"] for link in codes] == site_urls(config.build.site_base_url)
    assert len(soup.select(".back .picture svg")) == 4
    assert all(link.img["src"].startswith("data:image/svg+xml") for link in codes)
    assert not soup.select(".qr .unconfirmed")
    destinations = {
        ref.get_object().get("/A", {}).get("/URI") for ref in reader.pages[0].get("/Annots", [])
    }
    assert set(site_urls(config.build.site_base_url)) <= destinations
    if code == "es":
        assert all(
            "Traducción automática sin revisar." in page.extract_text().replace(" .", ".")
            for page in reader.pages
        )
