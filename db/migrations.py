"""
db/migrations.py — Cria o schema no PostgreSQL.

Uso:
    python db/migrations.py
"""
from db.models import Base, engine


def run_migrations() -> None:
    """Cria todas as tabelas definidas nos modelos (idempotente)."""
    print("[MIGRATION] Criando tabelas...")
    Base.metadata.create_all(engine)
    print("[MIGRATION] ✅ Tabela 'property_listings' criada (ou já existia).")
    print("[MIGRATION] Índices: ix_city_neighborhood_price, ix_source, ix_fingerprint")


if __name__ == "__main__":
    run_migrations()
