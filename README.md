# 🏠 Scanner Imob Portais

Scanner automatizado de anúncios imobiliários dos portais **Zap Imóveis**, **VivaReal** e **OLX**, com armazenamento em PostgreSQL e painel de análise via Streamlit.

---

## Funcionalidades

- Coleta automatizada de anúncios de 3 portais simultaneamente (via Playwright)
- Armazenamento em PostgreSQL com deduplicação por fingerprint MD5
- Script CLI simples: `python scan_listings.py --city "São Paulo"`
- Painel web interativo com filtros de preço, bairro e metragem

---

## Pré-requisitos

- Python 3.10+
- PostgreSQL 13+
- [Playwright](https://playwright.dev/python/) com Chromium

---

## Instalação

```bash
# 1. Clonar o repositório
git clone https://github.com/jisilva233/scanner-imob-portais.git
cd scanner-imob-portais

# 2. Criar e ativar ambiente virtual
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Instalar navegador Playwright
playwright install chromium

# 5. Configurar variável de ambiente
cp .env.example .env
# Edite o .env com sua DATABASE_URL
```

---

## Configuração

Edite o arquivo `.env`:

```env
DATABASE_URL=postgresql://usuario:senha@localhost:5432/imob_scraper
```

Para criar o banco e as tabelas:

```bash
python -c "from db.migrations import run_migrations; run_migrations()"
```

---

## Uso

### Coletar anúncios

```bash
# Cidade padrão — máximo 10 páginas por portal
python scan_listings.py --city "São Paulo"

# Limitar páginas (mais rápido para testes)
python scan_listings.py --city "Curitiba" --max-pages 3
```

Saída esperada:

```
🏠 Iniciando scan para: São Paulo (max 10 páginas por portal)

==================================================
  Zap Imóveis :  124 anúncios
  VivaReal    :   98 anúncios
  OLX         :   67 anúncios
  ──────────────────────────────
  Total coletado :  289
  Inseridos      :  274
  Duplicados     :   15
  Erros          :    0
==================================================
```

### Abrir o painel

```bash
streamlit run dashboard/app.py
```

Acesse: [http://localhost:8501](http://localhost:8501)

**Filtros disponíveis:**
- Preço (R$) — slider de intervalo
- Bairro — multiselect
- Metragem (m²) — slider de intervalo
- Portal — ZAP / VIVAREAL / OLX

---

## Estrutura do Projeto

```
scanner-imob-portais/
├── scrapers/
│   ├── base.py              # Classe abstrata BaseScraper
│   ├── zap_scraper.py       # Scraper do Zap Imóveis
│   ├── vivareal_scraper.py  # Scraper do VivaReal
│   └── olx_scraper.py       # Scraper da OLX
├── db/
│   ├── models.py            # Modelo SQLAlchemy + store_listings()
│   └── migrations.py        # Criação de tabelas
├── dashboard/
│   └── app.py               # Painel Streamlit
├── tests/
│   ├── test_models.py       # Testes da camada de dados
│   └── test_scrapers.py     # Testes dos scrapers (mock Playwright)
├── scan_listings.py         # Entry point CLI
├── requirements.txt
└── .env.example
```

---

## Testes

```bash
python -m pytest tests/ -v
```

31 testes unitários cobrindo:
- Parsing de preço, metragem e quartos
- Geração de fingerprint MD5
- Conversão de URLs relativas → absolutas
- Extração de cards (mock Playwright)
- store_listings() com deduplicação

---

## Stack Técnica

| Camada | Tecnologia |
|--------|-----------|
| Scraping | Playwright (async) |
| ORM | SQLAlchemy 2.0 |
| Banco | PostgreSQL |
| Validação | Pydantic v2 |
| Dashboard | Streamlit |
| Testes | pytest + pytest-asyncio |

---

## Licença

MIT
