"""Tests for the product URL rewriting layer.

The product catalog mixes three sources: Depop (C2C marketplace, ~58 %),
Vestiaire Collective (~28 %), and Zara (~14 %). Depop listings are
ephemeral -- sellers sell or delist items, and the direct-listing URLs
404 at high rate by the time the dataset is used. We mitigate by
rewriting marketplace URLs to point at the same site's *search* page
for the product name, so the tap always lands on a valid page even if
the original item is gone.

Retailer URLs (Zara) are left alone since their SKU pages are stable.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from vibecheck.rec.products import Product, _resolve_product_url


def _product(name: str, url: str) -> Product:
    return Product(
        id="1",
        name=name,
        description="",
        category="",
        brand="",
        gender="",
        price="",
        product_link=url,
        image_link="",
    )


def test_depop_url_is_rewritten_to_a_search_query() -> None:
    direct = "https://www.depop.com/products/seller-rare-vintage-tee/"
    safe = _resolve_product_url(direct, "Rare Vintage Tee")
    assert safe.startswith("https://www.depop.com/search/")
    parsed = urlparse(safe)
    assert parse_qs(parsed.query)["q"] == ["Rare Vintage Tee"]


def test_vestiaire_url_is_rewritten_to_a_search_fragment() -> None:
    direct = (
        "https://us.vestiairecollective.com/men-clothing/trousers/"
        "gucci/grey-wool-gucci-trousers-54625196.shtml"
    )
    safe = _resolve_product_url(direct, "Grey Wool Gucci Trousers")
    assert safe.startswith("https://us.vestiairecollective.com/search/")
    assert "Grey+Wool+Gucci+Trousers" in safe


def test_zara_url_is_unchanged() -> None:
    direct = "https://www.zara.com/us/en/textured-knit-polo-p03332405.html"
    assert _resolve_product_url(direct, "Textured Knit Polo") == direct


def test_unknown_host_is_unchanged() -> None:
    direct = "https://example.com/clothing/blue-jeans"
    assert _resolve_product_url(direct, "Blue Jeans") == direct


def test_empty_url_returns_empty() -> None:
    assert _resolve_product_url("", "Whatever") == ""


def test_empty_name_falls_back_to_original_marketplace_url() -> None:
    direct = "https://www.depop.com/products/seller-thing/"
    # No name to query with -> better to keep the original than to send the
    # user to an empty search page.
    assert _resolve_product_url(direct, "") == direct


def test_product_to_dict_exposes_safe_url_and_keeps_raw() -> None:
    product = _product(
        name="Vintage Levis 501",
        url="https://www.depop.com/products/seller-vintage-levis-501/",
    )
    payload = product.to_dict(score=0.42)
    assert payload["product_url_raw"] == product.product_link
    assert payload["product_url"].startswith("https://www.depop.com/search/")
    assert "Vintage+Levis+501" in payload["product_url"]
    assert payload["score"] == 0.42


def test_product_to_dict_keeps_zara_url_intact() -> None:
    product = _product(
        name="Textured Knit Polo",
        url="https://www.zara.com/us/en/textured-knit-polo-p03332405.html",
    )
    payload = product.to_dict()
    assert payload["product_url"] == product.product_link
    assert payload["product_url_raw"] == product.product_link
