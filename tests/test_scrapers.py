"""
tests/test_scrapers.py — Testes unitários dos scrapers (sem acesso real à rede).
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scrapers.base import BaseScraper
from scrapers.zap_scraper import ZapScraper


# ── Instância concreta para testar BaseScraper ────────────────────────────────

class ConcreteScraper(BaseScraper):
    async def scrape(self, city, max_pages=10):
        return []


scraper = ConcreteScraper()


# ── city_to_slug ──────────────────────────────────────────────────────────────

def test_city_to_slug_sao_paulo():
    assert scraper.city_to_slug("São Paulo") == "sao-paulo"


def test_city_to_slug_rio():
    assert scraper.city_to_slug("Rio de Janeiro") == "rio-de-janeiro"


def test_city_to_slug_lowercase():
    assert scraper.city_to_slug("CURITIBA") == "curitiba"


# ── _parse_price ──────────────────────────────────────────────────────────────

def test_parse_price_standard():
    assert scraper._parse_price("R$ 1.200.000") == 1200000.0


def test_parse_price_with_comma():
    assert scraper._parse_price("R$ 450.500,00") == 450500.0


def test_parse_price_empty():
    assert scraper._parse_price("") is None


def test_parse_price_invalid():
    assert scraper._parse_price("Consulte") is None


# ── _parse_number ─────────────────────────────────────────────────────────────

def test_parse_number_area():
    assert scraper._parse_number("80 m²") == 80


def test_parse_number_bedrooms():
    assert scraper._parse_number("3 quartos") == 3


def test_parse_number_empty():
    assert scraper._parse_number("") is None


# ── _to_absolute_url ──────────────────────────────────────────────────────────

def test_to_absolute_url_relative():
    url = scraper._to_absolute_url("/imovel/123", "https://www.zapimoveis.com.br")
    assert url == "https://www.zapimoveis.com.br/imovel/123"


def test_to_absolute_url_already_absolute():
    url = scraper._to_absolute_url("https://example.com/imovel/123", "https://base.com")
    assert url == "https://example.com/imovel/123"


def test_to_absolute_url_empty():
    url = scraper._to_absolute_url("", "https://base.com")
    assert url == ""


# ── _make_fingerprint ─────────────────────────────────────────────────────────

def test_fingerprint_is_32_chars():
    fp = scraper._make_fingerprint("https://example.com", 500000.0, "Casa")
    assert len(fp) == 32


def test_fingerprint_deterministic():
    fp1 = scraper._make_fingerprint("https://example.com", 500000.0, "Casa")
    fp2 = scraper._make_fingerprint("https://example.com", 500000.0, "Casa")
    assert fp1 == fp2


def test_fingerprint_different_for_different_input():
    fp1 = scraper._make_fingerprint("https://example.com/1", 500000.0, "Casa")
    fp2 = scraper._make_fingerprint("https://example.com/2", 500000.0, "Casa")
    assert fp1 != fp2


# ── ZapScraper._extract_card (mock Playwright) ────────────────────────────────

def make_mock_card(
    title="Apto 3 quartos",
    price="R$ 800.000",
    neighborhood="Pinheiros",
    area="90 m²",
    bedrooms="3",
    photos="15",
    date="",
    href="/imovel/abc123",
):
    """Cria um mock de card Playwright com os seletores do Zap."""

    async def safe_text_side_effect(selector):
        mapping = {
            "[data-testid='listing-title']": title,
            "[data-testid='listing-price']": price,
            "[data-testid='listing-address']": neighborhood,
            "[data-testid='listing-area']": area,
            "[data-testid='listing-bedrooms']": bedrooms,
            "[data-testid='photos-count']": photos,
            "[data-testid='listing-date']": date,
        }
        el = MagicMock()
        el.text_content = AsyncMock(return_value=mapping.get(selector, ""))
        return el

    card = MagicMock()
    card.query_selector = AsyncMock(side_effect=safe_text_side_effect)

    link_el = MagicMock()
    link_el.get_attribute = AsyncMock(return_value=href)
    card.query_selector = AsyncMock(side_effect=safe_text_side_effect)

    # Override para retornar link_el quando selector for o de link
    original = card.query_selector.side_effect

    async def combined_side_effect(selector):
        if selector == "a[data-testid='listing-card-anchor']":
            return link_el
        return await original(selector)

    card.query_selector.side_effect = combined_side_effect
    return card


@pytest.mark.asyncio
async def test_extract_card_valid():
    zap = ZapScraper()
    card = make_mock_card()
    listing = await zap._extract_card(card, "São Paulo")

    assert listing is not None
    assert listing.title == "Apto 3 quartos"
    assert listing.price == 800000.0
    assert listing.source == "zap"
    assert listing.city == "São Paulo"
    assert listing.listing_url == "https://www.zapimoveis.com.br/imovel/abc123"
    assert len(listing.fingerprint) == 32


@pytest.mark.asyncio
async def test_extract_card_no_link_returns_none():
    zap = ZapScraper()
    card = make_mock_card(href=None)

    # Forçar link_el.get_attribute retornar None
    link_el = MagicMock()
    link_el.get_attribute = AsyncMock(return_value=None)

    async def side_effect(selector):
        if selector == "a[data-testid='listing-card-anchor']":
            return link_el
        el = MagicMock()
        el.text_content = AsyncMock(return_value="")
        return el

    card.query_selector = AsyncMock(side_effect=side_effect)
    listing = await zap._extract_card(card, "São Paulo")
    assert listing is None


@pytest.mark.asyncio
async def test_extract_card_exception_returns_none():
    """Erro durante extração não deve propagar — deve retornar None."""
    zap = ZapScraper()
    card = MagicMock()
    card.query_selector = AsyncMock(side_effect=Exception("DOM error"))
    listing = await zap._extract_card(card, "São Paulo")
    assert listing is None
