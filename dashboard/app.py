"""
dashboard/app.py — Painel Streamlit para visualização de anúncios imobiliários.

Uso:
    streamlit run dashboard/app.py
"""
import pandas as pd
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import PropertyListingDB, engine

st.set_page_config(
    page_title="Imob Scanner",
    page_icon="🏠",
    layout="wide",
)


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    """Carrega anúncios ativos do PostgreSQL (cache de 5 min)."""
    with Session(engine) as session:
        rows = session.execute(
            select(PropertyListingDB).where(PropertyListingDB.is_active == True)
        ).scalars().all()

    return pd.DataFrame([
        {
            "Título": r.title,
            "Preço (R$)": r.price,
            "Bairro": r.neighborhood,
            "Metragem (m²)": r.area_sqm,
            "Quartos": r.bedrooms,
            "Fotos": r.photos_count,
            "Portal": (r.source or "").upper(),
            "Cidade": r.city,
            "Link": r.listing_url,
            "Data": r.listing_date,
        }
        for r in rows
    ])


# ── Carregar dados ─────────────────────────────────────────────────────────────
st.title("🏠 Imob Scanner — Anúncios Imobiliários")

df = load_data()

if df.empty:
    st.warning(
        "Nenhum anúncio encontrado. "
        "Execute `python scan_listings.py --city 'São Paulo'` primeiro."
    )
    st.stop()

# ── Métricas de resumo ─────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

price_mean = df["Preço (R$)"].dropna().mean()
col1.metric("Total de Anúncios", f"{len(df):,}")
col2.metric(
    "Preço Médio",
    f"R$ {price_mean:,.0f}" if pd.notna(price_mean) else "—",
)
col3.metric("Portais", df["Portal"].nunique())
col4.metric("Bairros", df["Bairro"].dropna().nunique())

st.divider()

# ── Filtros sidebar ────────────────────────────────────────────────────────────
st.sidebar.header("🔍 Filtros")

price_min = float(df["Preço (R$)"].dropna().min() or 0)
price_max = float(df["Preço (R$)"].dropna().max() or 10_000_000)
if price_min == price_max:
    price_max = price_min + 1

price_range = st.sidebar.slider(
    "Preço (R$)",
    min_value=price_min,
    max_value=price_max,
    value=(price_min, price_max),
    format="R$ %,.0f",
)

bairros = sorted(df["Bairro"].dropna().unique().tolist())
bairros_sel = st.sidebar.multiselect("Bairro", bairros, default=[])

area_min = float(df["Metragem (m²)"].dropna().min() or 0)
area_max = float(df["Metragem (m²)"].dropna().max() or 1000)
if area_min == area_max:
    area_max = area_min + 1

area_range = st.sidebar.slider(
    "Metragem (m²)",
    min_value=area_min,
    max_value=area_max,
    value=(area_min, area_max),
    format="%.0f m²",
)

portais = sorted(df["Portal"].unique().tolist())
portais_sel = st.sidebar.multiselect("Portal", portais, default=portais)

# ── Aplicar filtros ────────────────────────────────────────────────────────────
mask = (
    df["Preço (R$)"].fillna(price_min).between(price_range[0], price_range[1])
    & df["Metragem (m²)"].fillna(area_min).between(area_range[0], area_range[1])
    & df["Portal"].isin(portais_sel if portais_sel else portais)
)
if bairros_sel:
    mask &= df["Bairro"].isin(bairros_sel)

filtered = df[mask].reset_index(drop=True)

st.subheader(f"📋 {len(filtered):,} anúncios encontrados")

# ── Tabela com link clicável ───────────────────────────────────────────────────
st.dataframe(
    filtered,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Link": st.column_config.LinkColumn("Link", display_text="Ver anúncio"),
        "Preço (R$)": st.column_config.NumberColumn(
            "Preço (R$)", format="R$ %,.0f"
        ),
        "Metragem (m²)": st.column_config.NumberColumn(
            "Metragem (m²)", format="%.0f m²"
        ),
        "Data": st.column_config.DatetimeColumn("Data", format="DD/MM/YYYY"),
    },
)
