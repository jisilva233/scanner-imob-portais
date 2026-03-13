---
task: Store Listings no PostgreSQL
responsavel: "@data-agent"
elicit: false
atomic_layer: task
Entrada:
  - listings: Lista de PropertyListing coletados
Saida:
  - stats: {inserted, duplicates, errors}
Checklist:
  - "[ ] Modelo PropertyListing definido no SQLAlchemy"
  - "[ ] Tabela property_listings criada no PostgreSQL"
  - "[ ] Inserção usa ON CONFLICT (fingerprint) DO NOTHING"
  - "[ ] Retorna estatísticas de inserção"
---

# Task: Store Listings

## Propósito
Armazenar anúncios coletados no PostgreSQL com deduplicação via fingerprint.

## Implementação: `db/models.py`

```python
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Boolean,
    Index, create_engine, text
)
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.dialects.postgresql import insert
import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/imob_scraper")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


class Base(DeclarativeBase):
    pass


class PropertyListingDB(Base):
    """Modelo ORM da tabela property_listings."""

    __tablename__ = "property_listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fingerprint = Column(String(32), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    price = Column(Float, nullable=True)
    neighborhood = Column(String(200), nullable=True)
    area_sqm = Column(Float, nullable=True)
    bedrooms = Column(Integer, nullable=True)
    photos_count = Column(Integer, nullable=True)
    listing_url = Column(String(1000), nullable=False)
    listing_date = Column(DateTime, nullable=True)
    source = Column(String(50), nullable=False)   # zap | vivareal | olx
    city = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_city_neighborhood_price", "city", "neighborhood", "price"),
        Index("ix_source", "source"),
    )


class PropertyListing(BaseModel):
    """Modelo Pydantic para validação de dados coletados."""
    fingerprint: str
    title: str
    price: Optional[float] = None
    neighborhood: Optional[str] = None
    area_sqm: Optional[float] = None
    bedrooms: Optional[int] = None
    photos_count: Optional[int] = None
    listing_url: str
    listing_date: Optional[datetime] = None
    source: str
    city: str


def store_listings(listings: list[PropertyListing]) -> dict:
    """
    Armazena listings no PostgreSQL com deduplicação.

    Usa INSERT ... ON CONFLICT (fingerprint) DO NOTHING para evitar duplicatas.

    Returns:
        dict com chaves: inserted, duplicates, errors
    """
    stats = {"inserted": 0, "duplicates": 0, "errors": 0}

    with Session(engine) as session:
        for listing in listings:
            try:
                stmt = (
                    insert(PropertyListingDB)
                    .values(**listing.model_dump())
                    .on_conflict_do_nothing(index_elements=["fingerprint"])
                )
                result = session.execute(stmt)
                if result.rowcount > 0:
                    stats["inserted"] += 1
                else:
                    stats["duplicates"] += 1
            except Exception as e:
                print(f"[DB] Erro ao inserir listing {listing.fingerprint[:8]}...: {e}")
                stats["errors"] += 1
                session.rollback()

        session.commit()

    print(
        f"[DB] Inseridos: {stats['inserted']} | "
        f"Duplicados: {stats['duplicates']} | "
        f"Erros: {stats['errors']}"
    )
    return stats
```
