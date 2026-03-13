"""
dashboard/app.py — Painel Streamlit para visualização de anúncios imobiliários.

Uso:
    streamlit run dashboard/app.py
"""
import time

import pandas as pd
import pydeck as pdk
import requests
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


# ── Cache e rate limiting de geocodificação (dict de módulo, persiste na sessão) ─
_geo_cache: dict[str, tuple[float, float] | None] = {}
_last_request_time: float = 0.0


def geocode_bairro(bairro: str, cidade: str = "Brasil") -> tuple[float, float] | None:
    """Geocodifica um bairro usando Nominatim (OpenStreetMap). Retorna (lat, lon) ou None."""
    global _last_request_time

    if not bairro:
        return None

    cache_key = f"{bairro},{cidade}".lower()
    if cache_key in _geo_cache:
        return _geo_cache[cache_key]

    # Rate limiting: mínimo 1s entre requisições (ToS Nominatim)
    elapsed = time.time() - _last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{bairro}, {cidade}, Brasil", "format": "json", "limit": 1},
            headers={"User-Agent": "imob-scanner/1.0"},
            timeout=5,
        )
        _last_request_time = time.time()
        data = resp.json()
        if data:
            result = (float(data[0]["lat"]), float(data[0]["lon"]))
            _geo_cache[cache_key] = result
            return result
    except Exception:
        pass

    _geo_cache[cache_key] = None
    return None


# ── Mapeamento de cores por portal ─────────────────────────────────────────────
PORTAL_COLORS = {
    "ZAP":      [0, 100, 255, 180],
    "VIVAREAL": [0, 200, 100, 180],
    "OLX":      [255, 140, 0, 180],
}


def get_color(portal: str) -> list[int]:
    """Retorna cor RGBA para o marcador de acordo com o portal."""
    return PORTAL_COLORS.get(portal.upper(), [180, 180, 180, 180])


def build_map_data(df: pd.DataFrame) -> pd.DataFrame:
    """Geocodifica bairros e monta DataFrame para renderização pydeck."""
    rows = []
    for _, row in df.iterrows():
        bairro = row.get("Bairro") or ""
        cidade = row.get("Cidade") or "Brasil"
        if not bairro:
            continue
        coords = geocode_bairro(str(bairro), str(cidade))
        if coords is None:
            continue
        lat, lon = coords
        price_val = row.get("Preço (R$)") or 0
        rows.append({
            "lat": lat,
            "lon": lon,
            "titulo": row.get("Título", ""),
            "price": price_val,
            "price_fmt": f"R$ {price_val:,.0f}" if price_val else "—",
            "bairro": bairro,
            "portal": row.get("Portal", ""),
            "link": row.get("Link", ""),
            "color": get_color(str(row.get("Portal", ""))),
            "radius": max(50, min(int(price_val / 5000), 500)),
        })
    return pd.DataFrame(rows)


def render_map(filtered: pd.DataFrame) -> None:
    """Renderiza mapa interativo pydeck com ScatterplotLayer."""
    map_df = build_map_data(filtered)

    if map_df.empty:
        st.info("Nenhum imóvel com coordenadas disponível para os filtros selecionados.")
        return

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position=["lon", "lat"],
        get_color="color",
        get_radius="radius",
        pickable=True,
        opacity=0.8,
        stroked=True,
        filled=True,
        radius_min_pixels=6,
        radius_max_pixels=40,
    )

    view_state = pdk.ViewState(
        latitude=map_df["lat"].mean(),
        longitude=map_df["lon"].mean(),
        zoom=11,
        pitch=0,
    )

    tooltip = {
        "html": (
            "<b>{titulo}</b><br/>"
            "Preço: {price_fmt}<br/>"
            "Bairro: {bairro}<br/>"
            "Portal: {portal}<br/>"
            "<a href='{link}' target='_blank'>Ver anúncio</a>"
        ),
        "style": {"backgroundColor": "white", "color": "black", "padding": "8px"},
    }

    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip))
    st.caption(f"✅ {len(map_df)} imóveis mapeados de {len(filtered)} anúncios filtrados.")

    # Legenda de cores
    col1, col2, col3 = st.columns(3)
    col1.markdown("🔵 **ZAP Imóveis**")
    col2.markdown("🟢 **VivaReal**")
    col3.markdown("🟠 **OLX**")


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

# ── Abas: Lista e Mapa ─────────────────────────────────────────────────────────
tab_lista, tab_mapa = st.tabs(["📋 Lista", "🗺️ Mapa"])

with tab_lista:
    st.subheader(f"📋 {len(filtered):,} anúncios encontrados")
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

with tab_mapa:
    st.subheader(f"🗺️ {len(filtered):,} anúncios — geocodificando bairros...")
    with st.spinner("Obtendo coordenadas via Nominatim (OpenStreetMap)..."):
        render_map(filtered)
