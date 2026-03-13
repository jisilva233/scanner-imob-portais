"""
db/models.py — ORM SQLAlchemy e modelo Pydantic para anúncios imobiliários.

Tabela: property_listings
Deduplicação: fingerprint MD5(link + price + title) com UNIQUE constraint
"""
import hashlib
import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, field_validator
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import DeclarativeBase, Session

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@localhost:5432/imob_scraper"
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


class Base(DeclarativeBase):
    pass


class PropertyListingDB(Base):
    """ORM da tabela property_listings."""

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
    source = Column(String(50), nullable=False)
    city = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_city_neighborhood_price", "city", "neighborhood", "price"),
        Index("ix_source", "source"),
    )


class PropertyListing(BaseModel):
    """Modelo Pydantic para validação antes da inserção."""

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

    @field_validator("fingerprint")
    @classmethod
    def fingerprint_length(cls, v: str) -> str:
        if len(v) != 32:
            raise ValueError("fingerprint deve ter exatamente 32 caracteres (MD5)")
        return v

    @field_validator("source")
    @classmethod
    def source_valid(cls, v: str) -> str:
        allowed = {"zap", "vivareal", "olx"}
        if v not in allowed:
            raise ValueError(f"source deve ser um de {allowed}")
        return v


def make_fingerprint(listing_url: str, price: Optional[float], title: str) -> str:
    """Gera fingerprint MD5 para deduplicação."""
    raw = f"{listing_url}{price}{title}"
    return hashlib.md5(raw.encode()).hexdigest()


def store_listings(listings: list[PropertyListing]) -> dict:
    """
    Armazena listings no PostgreSQL com deduplicação via fingerprint.

    Usa INSERT ... ON CONFLICT (fingerprint) DO NOTHING para evitar duplicatas.

    Returns:
        dict: {inserted: int, duplicates: int, errors: int}
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
                print(f"[DB] Erro ao inserir {listing.fingerprint[:8]}...: {e}")
                stats["errors"] += 1
                session.rollback()

        session.commit()

    print(
        f"[DB] Inseridos: {stats['inserted']} | "
        f"Duplicados: {stats['duplicates']} | "
        f"Erros: {stats['errors']}"
    )
    return stats
