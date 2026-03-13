# Checklist de Scraping — imob-scraper

## Pré-execução
- [ ] PostgreSQL rodando e acessível
- [ ] `.env` configurado com `DATABASE_URL`
- [ ] Playwright instalado: `playwright install chromium`
- [ ] Migrations executadas: `python db/migrations.py`

## Durante execução
- [ ] Cada portal retorna ao menos 1 anúncio
- [ ] Logs mostram progresso de paginação
- [ ] Rate limiting ativo (delay entre requests)
- [ ] Erros de extração logados sem interromper scan

## Pós-execução
- [ ] Stats de inserção exibidas (inserted/duplicates/errors)
- [ ] Deduplicação executada
- [ ] Painel Streamlit exibe os dados corretamente

## Qualidade dos dados
- [ ] Fingerprints únicos por anúncio
- [ ] Preços com valores numéricos (sem "R$")
- [ ] URLs absolutas (não relativas)
- [ ] Datas parseadas corretamente
