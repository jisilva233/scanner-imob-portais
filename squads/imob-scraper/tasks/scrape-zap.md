---
task: Scrape Zap Imóveis
responsavel: "@scraper-agent"
elicit: false
atomic_layer: task
Entrada:
  - city: Cidade alvo (ex: "São Paulo")
  - max_pages: Limite de páginas (default: 10)
Saida:
  - listings: Lista de dicts com os campos coletados
Checklist:
  - "[ ] Playwright lança browser headless"
  - "[ ] Navega para URL de busca do Zap com city"
  - "[ ] Extrai listagens da página de resultados"
  - "[ ] Pagina até max_pages ou fim dos resultados"
  - "[ ] Retorna lista de PropertyListing validados"
---

# Task: Scrape Zap Imóveis

## Propósito
Coletar anúncios imobiliários do Zap Imóveis usando Playwright.

## Implementação: `scrapers/zap_scraper.py`

```python
import asyncio
import hashlib
from datetime import datetime
from typing import Optional
from playwright.async_api import async_playwright, Page
from db.models import PropertyListing

# Seletores CSS do Zap Imóveis (atualizar se o site mudar)
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

BASE_URL = "https://www.zapimoveis.com.br/venda/imoveis/{city}/"


async def scrape_zap(city: str, max_pages: int = 10) -> list[PropertyListing]:
    """
    Coleta anúncios do Zap Imóveis para a cidade informada.

    Args:
        city: Cidade no formato slug (ex: 'sp+sao-paulo')
        max_pages: Máximo de páginas a coletar

    Returns:
        Lista de PropertyListing validados
    """
    listings = []
    city_slug = city.lower().replace(" ", "-")
    url = BASE_URL.format(city=city_slug)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        for page_num in range(1, max_pages + 1):
            try:
                paginated_url = f"{url}?pagina={page_num}"
                await page.goto(paginated_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_selector(SELECTORS["listing_cards"], timeout=10000)

                cards = await page.query_selector_all(SELECTORS["listing_cards"])
                if not cards:
                    break

                for card in cards:
                    listing = await _extract_listing(card, page, "zap")
                    if listing:
                        listings.append(listing)

                # Verificar se há próxima página
                next_btn = await page.query_selector(SELECTORS["next_page"])
                if not next_btn:
                    break

                await asyncio.sleep(1.5)  # Rate limiting

            except Exception as e:
                print(f"[ZAP] Erro na página {page_num}: {e}")
                break

        await browser.close()

    print(f"[ZAP] Coletados {len(listings)} anúncios de {city}")
    return listings


async def _extract_listing(card, page: Page, source: str) -> Optional[PropertyListing]:
    """Extrai dados de um card de anúncio."""
    try:
        title = await _safe_text(card, SELECTORS["title"])
        price_text = await _safe_text(card, SELECTORS["price"])
        neighborhood = await _safe_text(card, SELECTORS["neighborhood"])
        area_text = await _safe_text(card, SELECTORS["area"])
        bedrooms_text = await _safe_text(card, SELECTORS["bedrooms"])
        photos_text = await _safe_text(card, SELECTORS["photos_count"])
        link_el = await card.query_selector(SELECTORS["link"])
        link = await link_el.get_attribute("href") if link_el else None
        date_text = await _safe_text(card, SELECTORS["date"])

        # Normalizar valores
        price = _parse_price(price_text)
        area = _parse_number(area_text)
        bedrooms = _parse_number(bedrooms_text)
        photos_count = _parse_number(photos_text)

        if not link:
            return None

        # Garantir URL absoluta
        if link.startswith("/"):
            link = f"https://www.zapimoveis.com.br{link}"

        # Gerar fingerprint para deduplicação
        fingerprint = hashlib.md5(
            f"{link}{price}{title}".encode()
        ).hexdigest()

        return PropertyListing(
            title=title,
            price=price,
            neighborhood=neighborhood,
            area_sqm=area,
            bedrooms=bedrooms,
            photos_count=photos_count,
            listing_url=link,
            listing_date=_parse_date(date_text),
            source=source,
            city="São Paulo",
            fingerprint=fingerprint,
        )
    except Exception as e:
        print(f"[ZAP] Erro ao extrair card: {e}")
        return None


async def _safe_text(element, selector: str) -> str:
    """Extrai texto de um seletor com fallback vazio."""
    try:
        el = await element.query_selector(selector)
        return (await el.text_content() or "").strip() if el else ""
    except Exception:
        return ""


def _parse_price(text: str) -> Optional[float]:
    """Converte 'R$ 1.200.000' → 1200000.0"""
    try:
        cleaned = text.replace("R$", "").replace(".", "").replace(",", ".").strip()
        return float(cleaned)
    except (ValueError, AttributeError):
        return None


def _parse_number(text: str) -> Optional[int]:
    """Extrai primeiro número inteiro de um texto."""
    import re
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


def _parse_date(text: str) -> Optional[datetime]:
    """Tenta parsear data do anúncio."""
    from dateutil import parser as dateparser
    try:
        return dateparser.parse(text, dayfirst=True)
    except Exception:
        return datetime.now()
```

## Notas de Implementação

- Os seletores CSS do `SELECTORS` podem mudar se o Zap Imóveis atualizar o frontend
- Usar `wait_until="networkidle"` garante que o JS carregou os cards
- Rate limiting de 1.5s entre páginas é suficiente para evitar bloqueio
- VivaReal e OLX seguem o mesmo padrão com seletores próprios
