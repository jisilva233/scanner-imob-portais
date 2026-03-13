# imob-scraper

Squad AIOS para coleta de anúncios imobiliários do Zap Imóveis, VivaReal e OLX.

## Início Rápido

```bash
# 1. Instalar dependências
pip install -r requirements.txt
playwright install chromium

# 2. Configurar banco
cp .env.example .env
# Editar .env com sua DATABASE_URL

# 3. Criar tabela
python db/migrations.py

# 4. Executar scan
python scan_listings.py --city "São Paulo"

# 5. Abrir painel
streamlit run dashboard/app.py
```

## Agentes

| Agente | Responsabilidade |
|--------|-----------------|
| `@imobScraper:scraper-agent` | Scraping com Playwright |
| `@imobScraper:data-agent` | Armazenamento e deduplicação |
| `@imobScraper:dashboard-agent` | Painel Streamlit |

## Dados Coletados

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `title` | string | Título do anúncio |
| `price` | float | Preço em reais |
| `neighborhood` | string | Bairro |
| `area_sqm` | float | Metragem em m² |
| `bedrooms` | int | Número de quartos |
| `photos_count` | int | Número de fotos |
| `listing_url` | string | Link do anúncio |
| `listing_date` | datetime | Data do anúncio |
| `source` | string | Portal (zap/vivareal/olx) |
| `fingerprint` | string | Hash MD5 para deduplicação |

## Variáveis de Ambiente

```env
DATABASE_URL=postgresql://user:password@localhost:5432/imob_scraper
```

## Estrutura

```
scrapers/          # Módulos de scraping por portal
db/                # Modelos e migrations
dashboard/         # Painel Streamlit
scan_listings.py   # Entry point principal
```
