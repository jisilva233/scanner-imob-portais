---
task: Executar Dashboard Streamlit
responsavel: "@dashboard-agent"
elicit: false
atomic_layer: task
Entrada:
  - PostgreSQL rodando com tabela property_listings populada
Saida:
  - Painel web em http://localhost:8501
---

# Task: Run Dashboard

## Propósito
Executar o painel Streamlit com filtros por preço, bairro e metragem.

## Execução

```bash
streamlit run dashboard/app.py
```

## Implementação: `dashboard/app.py`

```python
import streamlit as st
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session
from db.models import PropertyListingDB, engine

st.set_page_config(
    page_title="Imob Scanner",
    page_icon="🏠",
    layout="wide",
)

st.title("🏠 Imob Scanner — Anúncios Imobiliários")


@st.cache_data(ttl=300)  # Cache de 5 minutos
def load_data() -> pd.DataFrame:
    """Carrega listings ativos do PostgreSQL."""
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
            "Portal": r.source.upper(),
            "Cidade": r.city,
            "Link": r.listing_url,
            "Data": r.listing_date,
        }
        for r in rows
    ])


df = load_data()

if df.empty:
    st.warning("Nenhum anúncio encontrado. Execute `python scan_listings.py` primeiro.")
    st.stop()

# ── Métricas de resumo ─────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de Anúncios", len(df))
col2.metric("Preço Médio", f"R$ {df['Preço (R$)'].mean():,.0f}" if df["Preço (R$)"].notna().any() else "—")
col3.metric("Portais", df["Portal"].nunique())
col4.metric("Bairros", df["Bairro"].nunique())

st.divider()

# ── Filtros ────────────────────────────────────────────────────────────────────
st.sidebar.header("🔍 Filtros")

# Filtro de preço
price_min = float(df["Preço (R$)"].min() or 0)
price_max = float(df["Preço (R$)"].max() or 10_000_000)
price_range = st.sidebar.slider(
    "Preço (R$)",
    min_value=price_min,
    max_value=price_max,
    value=(price_min, price_max),
    format="R$ %,.0f",
)

# Filtro de bairro
bairros = sorted(df["Bairro"].dropna().unique().tolist())
bairros_sel = st.sidebar.multiselect("Bairro", bairros, default=[])

# Filtro de metragem
area_min = float(df["Metragem (m²)"].min() or 0)
area_max = float(df["Metragem (m²)"].max() or 1000)
area_range = st.sidebar.slider(
    "Metragem (m²)",
    min_value=area_min,
    max_value=area_max,
    value=(area_min, area_max),
)

# Filtro de portal
portais = sorted(df["Portal"].unique().tolist())
portais_sel = st.sidebar.multiselect("Portal", portais, default=portais)

# ── Aplicar filtros ────────────────────────────────────────────────────────────
mask = (
    df["Preço (R$)"].between(price_range[0], price_range[1])
    & df["Metragem (m²)"].between(area_range[0], area_range[1])
    & df["Portal"].isin(portais_sel if portais_sel else portais)
)
if bairros_sel:
    mask &= df["Bairro"].isin(bairros_sel)

filtered = df[mask].reset_index(drop=True)

st.subheader(f"📋 {len(filtered)} anúncios encontrados")

# Tabela com link clicável
st.dataframe(
    filtered.drop(columns=["Link"]).assign(
        Link=filtered["Link"].apply(lambda x: f"[Ver anúncio]({x})" if x else "—")
    ),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Link": st.column_config.LinkColumn("Link", display_text="Ver anúncio"),
        "Preço (R$)": st.column_config.NumberColumn("Preço (R$)", format="R$ %,.0f"),
        "Metragem (m²)": st.column_config.NumberColumn("Metragem (m²)", format="%.0f m²"),
    },
)
```
