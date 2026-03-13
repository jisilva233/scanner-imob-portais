"""
scrapers/zap_scraper.py — Scraper do Zap Imóveis usando Playwright.
"""
import asyncio
from datetime import datetime
from typing import Optional

from playwright.async_api import async_playwright

from db.models import PropertyListing
from scrapers.base import BaseScraper

BASE_DOMAIN = "https://www.zapimoveis.com.br"
BASE_URL = f"{BASE_DOMAIN}/venda/imoveis/{{city}}/"

# Seletores CSS — centralizar aqui para facilitar manutenção
SELECTORS = {
    "listing_cards": "[data-testid='result-card']",
    "title": "[data-testid='listing-title']",
    "price": "[data-testid='listing-price']",
    "neighborhood": "[data-testid='listing-address']",
    "area": "[data-testid='listing-area']",
    "bedrooms": "[data-testid='listing-bedrooms']",
    "photos_count": "[data-testid='photos-count']",
    "link": "a[data-testid='listing-card-anchor']",
    "date": "[data-testid='listing-date']",
    "next_page": "[data-testid='next-page']",
}

MAX_RETRIES = 3


class ZapScraper(BaseScraper):
    def __init__(self) -> None:
        super().__init__(rate_limit=1.5)

    async def scrape(self, city: str, max_pages: int = 10) -> list[PropertyListing]:
        """Coleta anúncios do Zap Imóveis para a cidade informada."""
        listings: list[PropertyListing] = []
        city_slug = self.city_to_slug(city)
        url = BASE_URL.format(city=city_slug)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()

            for page_num in range(1, max_pages + 1):
                paginated_url = f"{url}?pagina={page_num}"
                loaded = False

                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        await page.goto(
                            paginated_url,
                            wait_until="networkidle",
                            timeout=30000,
                        )
                        await page.wait_for_selector(
                            SELECTORS["listing_cards"], timeout=10000
                        )
                        loaded = True
                        break
                    except Exception as e:
                        wait = 2 ** attempt
                        print(
                            f"[ZAP] Tentativa {attempt}/{MAX_RETRIES} "
                            f"falhou na página {page_num}: {e}. "
                            f"Aguardando {wait}s..."
                        )
                        await asyncio.sleep(wait)

                if not loaded:
                    print(f"[ZAP] Abandonando página {page_num} após {MAX_RETRIES} tentativas.")
                    break

                cards = await page.query_selector_all(SELECTORS["listing_cards"])
                if not cards:
                    break

                for card in cards:
                    listing = await self._extract_card(card, city)
                    if listing:
                        listings.append(listing)

                next_btn = await page.query_selector(SELECTORS["next_page"])
                if not next_btn:
                    break

                await self._sleep()

            await browser.close()

        print(f"[ZAP] Coletados {len(listings)} anúncios de {city}")
        return listings

    async def _extract_card(self, card, city: str) -> Optional[PropertyListing]:
        """Extrai dados de um card; erros são logados sem interromper o scan."""
        try:
            title = await self._safe_text(card, SELECTORS["title"])
            price_text = await self._safe_text(card, SELECTORS["price"])
            neighborhood = await self._safe_text(card, SELECTORS["neighborhood"])
            area_text = await self._safe_text(card, SELECTORS["area"])
            bedrooms_text = await self._safe_text(card, SELECTORS["bedrooms"])
            photos_text = await self._safe_text(card, SELECTORS["photos_count"])
            date_text = await self._safe_text(card, SELECTORS["date"])

            link_el = await card.query_selector(SELECTORS["link"])
            raw_link = await link_el.get_attribute("href") if link_el else None
            link = self._to_absolute_url(raw_link or "", BASE_DOMAIN)

            if not link or not title:
                return None

            price = self._parse_price(price_text)
            area = self._parse_number(area_text)
            bedrooms = self._parse_number(bedrooms_text)
            photos_count = self._parse_number(photos_text)
            listing_date = self._parse_date(date_text)
            fingerprint = self._make_fingerprint(link, price, title)

            return PropertyListing(
                fingerprint=fingerprint,
                title=title,
                price=price,
                neighborhood=neighborhood or None,
                area_sqm=float(area) if area else None,
                bedrooms=bedrooms,
                photos_count=photos_count,
                listing_url=link,
                listing_date=listing_date,
                source="zap",
                city=city,
            )
        except Exception as e:
            print(f"[ZAP] Erro ao extrair card: {e}")
            return None

    async def _safe_text(self, element, selector: str) -> str:
        try:
            el = await element.query_selector(selector)
            return (await el.text_content() or "").strip() if el else ""
        except Exception:
            return ""


async def scrape_zap(city: str, max_pages: int = 10) -> list[PropertyListing]:
    """Função de conveniência para uso externo."""
    return await ZapScraper().scrape(city, max_pages)
