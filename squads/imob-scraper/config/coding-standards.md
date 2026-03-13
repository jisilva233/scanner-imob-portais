# Coding Standards — imob-scraper

## Python
- Seguir PEP 8
- Type hints obrigatórios em funções públicas
- Docstrings em classes e funções públicas
- Máximo 120 caracteres por linha

## Estrutura de Funções
- Uma responsabilidade por função
- Retornar objetos Pydantic validados
- Tratar exceções específicas, nunca `except Exception` genérico

## Scraping
- Sempre usar `async with` para gerenciar contextos Playwright
- Logar URLs acessadas e erros de extração
- Nunca hardcodar seletores CSS — centralizar em constantes

## Banco de Dados
- Usar sessions SQLAlchemy com context manager
- Nunca escrever SQL raw — usar ORM
- Toda inserção deve verificar deduplicação antes

## Variáveis de Ambiente
- Nunca commitar credenciais
- Usar `.env` + `python-dotenv`
- Documentar todas as variáveis em `.env.example`
