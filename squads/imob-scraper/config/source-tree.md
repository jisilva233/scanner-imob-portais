# Source Tree — imob-scraper

```
scanner-imob-portais/
├── squads/imob-scraper/          # Definição do squad AIOS
│   ├── squad.yaml
│   ├── agents/
│   ├── tasks/
│   └── workflows/
├── scrapers/                     # Módulos de scraping por portal
│   ├── __init__.py
│   ├── base.py                   # Classe base abstrata
│   ├── zap_scraper.py
│   ├── vivareal_scraper.py
│   └── olx_scraper.py
├── db/                           # Camada de banco de dados
│   ├── __init__.py
│   ├── models.py                 # Tabela property_listings
│   └── migrations.py             # Setup inicial do schema
├── dashboard/                    # Painel Streamlit
│   ├── __init__.py
│   └── app.py
├── scan_listings.py              # Entry point principal
├── requirements.txt
├── .env.example
└── README.md
```
