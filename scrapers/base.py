"""
scrapers/base.py — Classe base abstrata para todos os scrapers imobiliários.
"""
import asyncio
import re
import unicodedata
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from db.models import PropertyListing, make_fingerprint


class BaseScraper(ABC):
    """Scraper base com utilitários comuns de extração e normalização."""

    def __init__(self, rate_limit: float = 1.5):
        self.rate_limit = rate_limit

    @abstractmethod
    async def scrape(self, city: str, max_pages: int = 10) -> list[PropertyListing]:
        """Coleta anúncios do portal para a cidade informada."""
        ...

    def city_to_slug(self, city: str) -> str:
        """Converte 'São Paulo' → 'sao-paulo'."""
        nfkd = unicodedata.normalize("NFKD", city)
        ascii_str = nfkd.encode("ASCII", "ignore").decode()
        return ascii_str.lower().replace(" ", "-")

    def _parse_price(self, text: str) -> Optional[float]:
        """Converte 'R$ 1.200.000' → 1200000.0."""
        try:
            cleaned = (
                text.replace("R$", "")
                .replace(".", "")
                .replace(",", ".")
                .strip()
            )
            # Remover sufixos como '/mês', '/m²'
            cleaned = re.sub(r"[^\d.]", "", cleaned)
            return float(cleaned) if cleaned else None
        except (ValueError, AttributeError):
            return None

    def _parse_number(self, text: str) -> Optional[int]:
        """Extrai o primeiro número inteiro de um texto."""
        match = re.search(r"\d+", text or "")
        return int(match.group()) if match else None

    def _parse_date(self, text: str) -> Optional[datetime]:
        """Tenta parsear data do anúncio; retorna None se falhar."""
        try:
            from dateutil import parser as dateparser
            return dateparser.parse(text, dayfirst=True)
        except Exception:
            return None

    def _to_absolute_url(self, url: str, base_domain: str) -> str:
        """Converte URL relativa para absoluta."""
        if not url:
            return url
        if url.startswith("http"):
            return url
        return f"{base_domain.rstrip('/')}{url}"

    def _make_fingerprint(
        self, listing_url: str, price: Optional[float], title: str
    ) -> str:
        """Delega para make_fingerprint do módulo db.models."""
        return make_fingerprint(listing_url, price, title)

    async def _sleep(self) -> None:
        """Rate limiting entre requests."""
        await asyncio.sleep(self.rate_limit)
