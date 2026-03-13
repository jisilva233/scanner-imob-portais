# Tech Stack — imob-scraper

## Linguagem
- Python 3.11+

## Scraping
- **Playwright** — Browser automation para sites dinâmicos (JS-rendered)
- Modo headless por padrão, headed para debug

## Banco de Dados
- **PostgreSQL** — Armazenamento principal
- **SQLAlchemy** — ORM e migrations
- **psycopg2-binary** — Driver PostgreSQL

## Dashboard
- **Streamlit** — Painel web simples com filtros

## Utilitários
- **python-dotenv** — Variáveis de ambiente
- **pydantic** — Validação de modelos de dados
- **hashlib** — Geração de fingerprint para deduplicação

## Ambiente
- `.env` para credenciais de banco
- `requirements.txt` para dependências Python
