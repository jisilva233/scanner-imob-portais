"""
scan_apify.py — Coleta anúncios imobiliários via Apify Actors.

Uso:
    python scan_apify.py --city "São Paulo" --max-results 50
"""
import argparse
import os

from apify_client import ApifyClient
from dotenv import load_dotenv

from db.models import PropertyListing, make_fingerprint, store_listings

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
if not APIFY_TOKEN:
    raise RuntimeError("APIFY_API_TOKEN não encontrado no .env")

client = ApifyClient(APIFY_TOKEN)

# Actors disponíveis
ACTORS = {
    "zap": "avorio/zap-imoveis-scraper",
    "olx": "viralanalyzer/brazil-real-estate-scraper",
}


def collect_zap(city: str, max_results: int) -> list[PropertyListing]:
    """Coleta do Zap Imóveis via Apify."""
    print(f"\n[ZAP] Iniciando coleta para {city}...")

    city_slug = city.lower().replace(" ", "-")
    # Remove acentos simples
    for old, new in [("ã", "a"), ("á", "a"), ("é", "e"), ("ê", "e"), ("í", "i"), ("ó", "o"), ("ô", "o"), ("ú", "u"), ("ç", "c")]:
        city_slug = city_slug.replace(old, new)

    run_input = {
        "location": f"sp+{city_slug}",
        "listingType": "sale",
        "maxItems": max_results,
    }

    try:
        run = client.actor(ACTORS["zap"]).call(run_input=run_input)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    except Exception as e:
        print(f"[ZAP] Erro ao executar Actor: {e}")
        return []

    listings = []
    for item in items:
        try:
            title = item.get("title", "")
            price = item.get("price") or item.get("salePrice")
            url = item.get("url", "") or item.get("link", "")
            if not title or not url:
                continue

            price_float = None
            if price:
                try:
                    price_float = float(str(price).replace("R$", "").replace(".", "").replace(",", ".").strip())
                except ValueError:
                    pass

            area = item.get("area") or item.get("totalArea")
            area_float = None
            if area:
                try:
                    area_float = float(str(area).replace("m²", "").replace(".", "").replace(",", ".").strip())
                except ValueError:
                    pass

            bedrooms = item.get("bedrooms") or item.get("rooms")
            bedrooms_int = None
            if bedrooms:
                try:
                    bedrooms_int = int(str(bedrooms).split()[0])
                except (ValueError, IndexError):
                    pass

            fp = make_fingerprint(url, price_float, title)
            listings.append(PropertyListing(
                fingerprint=fp,
                title=title[:500],
                price=price_float,
                neighborhood=item.get("neighborhood") or item.get("address", ""),
                area_sqm=area_float,
                bedrooms=bedrooms_int,
                photos_count=item.get("photos") or len(item.get("images", [])) or None,
                listing_url=url,
                source="zap",
                city=city,
            ))
        except Exception as e:
            print(f"[ZAP] Erro ao processar item: {e}")
            continue

    print(f"[ZAP] Coletados {len(listings)} anúncios")
    return listings


def collect_olx(city: str, max_results: int) -> list[PropertyListing]:
    """Coleta da OLX via Apify (Brazil Real Estate Scraper)."""
    print(f"\n[OLX] Iniciando coleta para {city}...")

    run_input = {
        "platform": "olx",
        "state": "sp",
        "city": city,
        "propertyType": "all",
        "listingType": "sale",
        "maxItems": max_results,
    }

    try:
        run = client.actor(ACTORS["olx"]).call(run_input=run_input)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    except Exception as e:
        print(f"[OLX] Erro ao executar Actor: {e}")
        return []

    listings = []
    for item in items:
        try:
            title = item.get("title", "")
            url = item.get("url", "") or item.get("link", "")
            if not title or not url:
                continue

            price_float = None
            price = item.get("price") or item.get("salePrice")
            if price:
                try:
                    price_float = float(str(price).replace("R$", "").replace(".", "").replace(",", ".").strip())
                except ValueError:
                    pass

            area = item.get("area") or item.get("size")
            area_float = None
            if area:
                try:
                    area_float = float(str(area).replace("m²", "").replace(".", "").replace(",", ".").strip())
                except ValueError:
                    pass

            bedrooms = item.get("bedrooms") or item.get("rooms")
            bedrooms_int = None
            if bedrooms:
                try:
                    bedrooms_int = int(str(bedrooms).split()[0])
                except (ValueError, IndexError):
                    pass

            fp = make_fingerprint(url, price_float, title)
            listings.append(PropertyListing(
                fingerprint=fp,
                title=title[:500],
                price=price_float,
                neighborhood=item.get("neighborhood") or item.get("location", ""),
                area_sqm=area_float,
                bedrooms=bedrooms_int,
                photos_count=item.get("photos") or len(item.get("images", [])) or None,
                listing_url=url,
                source="olx",
                city=city,
            ))
        except Exception as e:
            print(f"[OLX] Erro ao processar item: {e}")
            continue

    print(f"[OLX] Coletados {len(listings)} anúncios")
    return listings


def main():
    parser = argparse.ArgumentParser(description="Scanner imobiliário via Apify")
    parser.add_argument("--city", required=True, help="Cidade (ex: 'São Paulo')")
    parser.add_argument("--max-results", type=int, default=50, help="Máximo de resultados por portal (default: 50)")
    args = parser.parse_args()

    print(f"\n🏠 Coletando anúncios via Apify para: {args.city}\n")

    zap = collect_zap(args.city, args.max_results)
    olx = collect_olx(args.city, args.max_results)

    all_listings = zap + olx
    if all_listings:
        stats = store_listings(all_listings)
        print(
            f"\n{'='*50}\n"
            f"  Zap Imóveis : {len(zap):>4} anúncios\n"
            f"  OLX         : {len(olx):>4} anúncios\n"
            f"  {'─'*30}\n"
            f"  Total coletado : {len(all_listings):>4}\n"
            f"  Inseridos      : {stats['inserted']:>4}\n"
            f"  Duplicados     : {stats['duplicates']:>4}\n"
            f"  Erros          : {stats['errors']:>4}\n"
            f"{'='*50}\n"
        )
    else:
        print("\n⚠️  Nenhum anúncio coletado. Verifique os Actors no Apify.")


if __name__ == "__main__":
    main()
