"""
scan_listings.py — Entry point do scanner imobiliário.

Uso:
    python scan_listings.py --city "São Paulo"
    python scan_listings.py --city "Curitiba" --max-pages 5
"""
import argparse
import asyncio

from db.models import store_listings
from scrapers.olx_scraper import scrape_olx
from scrapers.vivareal_scraper import scrape_vivareal
from scrapers.zap_scraper import scrape_zap


async def run_scan(city: str, max_pages: int) -> None:
    print(f"\n🏠 Iniciando scan para: {city} (max {max_pages} páginas por portal)\n")

    zap, vivareal, olx = await asyncio.gather(
        scrape_zap(city, max_pages),
        scrape_vivareal(city, max_pages),
        scrape_olx(city, max_pages),
        return_exceptions=True,
    )

    # Tratar exceções retornadas pelo gather
    zap = zap if isinstance(zap, list) else []
    vivareal = vivareal if isinstance(vivareal, list) else []
    olx = olx if isinstance(olx, list) else []

    all_listings = zap + vivareal + olx
    stats = store_listings(all_listings)

    print(
        f"\n{'='*50}\n"
        f"  Zap Imóveis : {len(zap):>4} anúncios\n"
        f"  VivaReal    : {len(vivareal):>4} anúncios\n"
        f"  OLX         : {len(olx):>4} anúncios\n"
        f"  {'─'*30}\n"
        f"  Total coletado : {len(all_listings):>4}\n"
        f"  Inseridos      : {stats['inserted']:>4}\n"
        f"  Duplicados     : {stats['duplicates']:>4}\n"
        f"  Erros          : {stats['errors']:>4}\n"
        f"{'='*50}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scanner de anúncios imobiliários (Zap, VivaReal, OLX)"
    )
    parser.add_argument(
        "--city",
        required=True,
        help="Cidade alvo (ex: 'São Paulo')",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        dest="max_pages",
        help="Máximo de páginas por portal (default: 10)",
    )
    args = parser.parse_args()
    asyncio.run(run_scan(args.city, args.max_pages))


if __name__ == "__main__":
    main()
