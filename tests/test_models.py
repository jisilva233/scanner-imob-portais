"""
tests/test_models.py — Testes unitários para db/models.py

Execução:
    pytest tests/test_models.py -v
"""
import hashlib
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from db.models import PropertyListing, make_fingerprint, store_listings


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_listing(**overrides) -> PropertyListing:
    url = overrides.get("listing_url", "https://zapimoveis.com.br/imovel/123")
    price = overrides.get("price", 500000.0)
    title = overrides.get("title", "Apartamento 3 quartos")
    defaults = {
        "fingerprint": make_fingerprint(url, price, title),
        "title": title,
        "price": price,
        "neighborhood": "Pinheiros",
        "area_sqm": 80.0,
        "bedrooms": 3,
        "photos_count": 10,
        "listing_url": url,
        "listing_date": datetime(2026, 3, 13),
        "source": "zap",
        "city": "São Paulo",
    }
    defaults.update(overrides)
    # Recalcular fingerprint se url/price/title foram sobrescritos
    if any(k in overrides for k in ("listing_url", "price", "title")):
        defaults["fingerprint"] = make_fingerprint(
            defaults["listing_url"], defaults["price"], defaults["title"]
        )
    return PropertyListing(**defaults)


# ── Testes: make_fingerprint ───────────────────────────────────────────────────

def test_fingerprint_is_32_chars():
    fp = make_fingerprint("https://example.com", 100000.0, "Casa")
    assert len(fp) == 32


def test_fingerprint_same_input_same_output():
    fp1 = make_fingerprint("https://example.com", 100000.0, "Casa")
    fp2 = make_fingerprint("https://example.com", 100000.0, "Casa")
    assert fp1 == fp2


def test_fingerprint_different_input_different_output():
    fp1 = make_fingerprint("https://example.com/1", 100000.0, "Casa")
    fp2 = make_fingerprint("https://example.com/2", 100000.0, "Casa")
    assert fp1 != fp2


# ── Testes: PropertyListing (Pydantic) ────────────────────────────────────────

def test_property_listing_valid():
    listing = make_listing()
    assert listing.title == "Apartamento 3 quartos"
    assert listing.source == "zap"
    assert len(listing.fingerprint) == 32


def test_property_listing_optional_fields_can_be_none():
    listing = make_listing(
        price=None, neighborhood=None, area_sqm=None,
        bedrooms=None, photos_count=None, listing_date=None,
    )
    assert listing.price is None
    assert listing.neighborhood is None


def test_property_listing_invalid_source():
    with pytest.raises(ValidationError) as exc_info:
        make_listing(source="invalid_portal")
    assert "source deve ser um de" in str(exc_info.value)


def test_property_listing_invalid_fingerprint_length():
    with pytest.raises(ValidationError) as exc_info:
        listing = make_listing()
        PropertyListing(**{**listing.model_dump(), "fingerprint": "curto"})
    assert "32 caracteres" in str(exc_info.value)


def test_property_listing_missing_required_fields():
    with pytest.raises(ValidationError):
        PropertyListing(
            fingerprint="a" * 32,
            # title ausente — obrigatório
            listing_url="https://example.com",
            source="zap",
            city="São Paulo",
        )


# ── Testes: store_listings ────────────────────────────────────────────────────

@patch("db.models.Session")
def test_store_listings_inserts_new(mock_session_cls):
    """Novo registro deve incrementar inserted."""
    mock_session = MagicMock()
    mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_session.execute.return_value = mock_result

    listing = make_listing()
    stats = store_listings([listing])

    assert stats["inserted"] == 1
    assert stats["duplicates"] == 0
    assert stats["errors"] == 0


@patch("db.models.Session")
def test_store_listings_ignores_duplicate(mock_session_cls):
    """Registro duplicado (rowcount=0) deve incrementar duplicates."""
    mock_session = MagicMock()
    mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

    mock_result = MagicMock()
    mock_result.rowcount = 0  # ON CONFLICT DO NOTHING
    mock_session.execute.return_value = mock_result

    listing = make_listing()
    stats = store_listings([listing])

    assert stats["inserted"] == 0
    assert stats["duplicates"] == 1
    assert stats["errors"] == 0


@patch("db.models.Session")
def test_store_listings_handles_error(mock_session_cls):
    """Erro de DB deve incrementar errors sem lançar exceção."""
    mock_session = MagicMock()
    mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)
    mock_session.execute.side_effect = Exception("DB connection error")

    listing = make_listing()
    stats = store_listings([listing])

    assert stats["errors"] == 1
    assert stats["inserted"] == 0


@patch("db.models.Session")
def test_store_listings_returns_correct_stats(mock_session_cls):
    """Com 3 listings (1 novo, 1 dup, 1 erro) stats devem ser corretos."""
    mock_session = MagicMock()
    mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

    results = [
        MagicMock(rowcount=1),   # inserido
        MagicMock(rowcount=0),   # duplicado
    ]
    mock_session.execute.side_effect = [
        results[0],
        results[1],
        Exception("erro"),
    ]

    listings = [
        make_listing(listing_url=f"https://example.com/{i}", title=f"Casa {i}")
        for i in range(3)
    ]
    stats = store_listings(listings)

    assert stats["inserted"] == 1
    assert stats["duplicates"] == 1
    assert stats["errors"] == 1
