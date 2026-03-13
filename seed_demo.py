"""Insere dados de demonstração para testar o dashboard."""
from db.models import PropertyListing, make_fingerprint, store_listings

DEMO = [
    ("Apartamento 3 quartos - Pinheiros", 850000, "Pinheiros", 90, 3, 12, "zap", "São Paulo", "https://www.zapimoveis.com.br/imovel/1"),
    ("Cobertura duplex com terraço", 1200000, "Vila Madalena", 150, 4, 20, "zap", "São Paulo", "https://www.zapimoveis.com.br/imovel/2"),
    ("Studio moderno próximo ao metrô", 380000, "Consolação", 35, 1, 8, "zap", "São Paulo", "https://www.zapimoveis.com.br/imovel/3"),
    ("Casa térrea com quintal", 950000, "Butantã", 120, 3, 15, "vivareal", "São Paulo", "https://www.vivareal.com.br/imovel/4"),
    ("Apartamento reformado", 520000, "Moema", 65, 2, 10, "vivareal", "São Paulo", "https://www.vivareal.com.br/imovel/5"),
    ("Flat mobiliado - Itaim Bibi", 680000, "Itaim Bibi", 45, 1, 6, "vivareal", "São Paulo", "https://www.vivareal.com.br/imovel/6"),
    ("Sobrado 4 quartos", 1100000, "Perdizes", 180, 4, 18, "olx", "São Paulo", "https://www.olx.com.br/imovel/7"),
    ("Apto 2 quartos com varanda", 450000, "Lapa", 70, 2, 9, "olx", "São Paulo", "https://www.olx.com.br/imovel/8"),
    ("Kitnet centro", 250000, "República", 28, 1, 4, "olx", "São Paulo", "https://www.olx.com.br/imovel/9"),
    ("Penthouse com piscina", 2500000, "Jardins", 250, 5, 25, "zap", "São Paulo", "https://www.zapimoveis.com.br/imovel/10"),
    ("Apartamento garden", 720000, "Vila Mariana", 85, 2, 11, "vivareal", "São Paulo", "https://www.vivareal.com.br/imovel/11"),
    ("Loft industrial", 490000, "Barra Funda", 55, 1, 7, "olx", "São Paulo", "https://www.olx.com.br/imovel/12"),
    ("Casa em condomínio fechado", 1800000, "Morumbi", 200, 4, 22, "zap", "São Paulo", "https://www.zapimoveis.com.br/imovel/13"),
    ("Apto novo nunca habitado", 600000, "Tatuapé", 75, 3, 13, "vivareal", "São Paulo", "https://www.vivareal.com.br/imovel/14"),
    ("Studio compacto Paulista", 320000, "Bela Vista", 30, 1, 5, "olx", "São Paulo", "https://www.olx.com.br/imovel/15"),
]

listings = []
for title, price, bairro, area, quartos, fotos, portal, cidade, url in DEMO:
    fp = make_fingerprint(url, price, title)
    listings.append(PropertyListing(
        fingerprint=fp, title=title, price=price, neighborhood=bairro,
        area_sqm=area, bedrooms=quartos, photos_count=fotos,
        listing_url=url, source=portal, city=cidade,
    ))

stats = store_listings(listings)
print(f"\n✅ {stats['inserted']} anúncios de demonstração inseridos!")
