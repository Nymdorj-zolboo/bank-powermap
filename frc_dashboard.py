from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="ББСБ бүртгэл — FRC",
    page_icon="F",
    layout="wide",
    initial_sidebar_state="expanded",
)

BRAND_BLUE = "#4895fc"
BRAND_NAVY = "#1c3c65"
BRAND_DEEP_BLUE = "#004095"
BRAND_SLATE = "#2e3b44"
BRAND_TEAL = "#0a7ea4"
BRAND_AMBER = "#ffb703"

DATA_PATH = Path(__file__).resolve().parent / "frc" / "outputs" / "frc_api_records_guess.jsonl"


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: radial-gradient(circle at top right, rgba(72,149,252,.18), transparent 26%),
                        linear-gradient(180deg, #070b0e 0%, #162b42 100%);
            color: #edf5ff;
        }
        .stApp, .stApp p, .stApp li, .stApp label, .stApp span, .stApp div,
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5 { color: #edf5ff; }
        .block-container { padding-top: 1.1rem; max-width: 1380px; }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(10,16,23,.98), rgba(28,60,101,.92));
            border-right: 1px solid rgba(72,149,252,.18);
        }
        section[data-testid="stSidebar"] * { color: #edf5ff !important; }
        div[data-testid="stMetric"] {
            background: rgba(17,29,43,.92);
            border: 1px solid rgba(72,149,252,.18);
            border-radius: 14px;
            padding: .8rem 1rem;
            box-shadow: 0 12px 26px rgba(0,0,0,.28);
        }
        div[data-testid="stMetric"] [data-testid="stMetricLabel"] { color: #bfd4ec !important; }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #4895fc !important; }
        .hero {
            background: linear-gradient(135deg, rgba(72,149,252,.78), rgba(28,60,101,.96) 58%, rgba(7,11,14,.98));
            color: #f2f8ff;
            border-radius: 18px;
            padding: 1.1rem 1.35rem;
            margin-bottom: .95rem;
            box-shadow: 0 20px 36px rgba(0,0,0,.40);
        }
        .hero h1 { margin: 0 0 .2rem 0; font-size: 1.75rem; color: #f2f8ff !important; }
        .hero p { margin: .1rem 0; color: #eaf2ff !important; font-size: .96rem; }
        div[data-baseweb="select"] > div,
        div[data-testid="stTextInputRootElement"] > div {
            background: rgba(15,24,34,.98) !important;
            color: #edf5ff !important;
            border-color: rgba(72,149,252,.22) !important;
        }
        div[data-baseweb="select"] input,
        div[data-baseweb="select"] span,
        div[data-baseweb="popover"] * { color: #edf5ff !important; }
        div[data-baseweb="popover"] [role="option"]:hover { background: rgba(72,149,252,.12) !important; }
        .stExpander { border: 1px solid rgba(72,149,252,.18) !important; border-radius: 10px !important; }
        div[data-testid="stDataFrame"] { border: 1px solid rgba(72,149,252,.18); border-radius: 10px; }
        hr { border-color: rgba(72,149,252,.18) !important; }
        .section-title { font-size: 1.1rem; font-weight: 800; color: #8fc1ff; margin-bottom: .2rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def style_plot(fig: go.Figure, height: int | None = None) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="#0d1b2a",
        plot_bgcolor="#111d2e",
        font=dict(color="#c8dff8", size=12),
        title_font=dict(color="#edf5ff", size=16),
        legend=dict(
            bgcolor="rgba(11,18,32,.88)",
            bordercolor="rgba(72,149,252,.22)",
            borderwidth=1,
            font=dict(color="#c8dff8"),
        ),
        hoverlabel=dict(bgcolor="#111d2b", font=dict(color="#eaf2ff")),
        margin=dict(l=20, r=20, t=45, b=20),
    )
    fig.update_xaxes(
        gridcolor="rgba(143,193,255,.10)",
        linecolor="rgba(72,149,252,.20)",
        showline=True,
        tickfont=dict(color="#c8dff8"),
        title_font=dict(color="#c8dff8"),
    )
    fig.update_yaxes(
        gridcolor="rgba(143,193,255,.10)",
        linecolor="rgba(72,149,252,.20)",
        showline=True,
        tickfont=dict(color="#c8dff8"),
        title_font=dict(color="#c8dff8"),
    )
    if height is not None:
        fig.update_layout(height=height)
    return fig


@st.cache_data(show_spinner=False)
def load_data(path: Path) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if "financial_activities_name" not in d:
                continue
            rows.append(d)
    df = pd.DataFrame(rows)

    # Clean entity names
    df["entity_name"] = df["entity_name"].str.replace(r"&quot;", "", regex=False).str.strip()

    # Parse license_date
    df["license_date"] = pd.to_datetime(df["license_date"], errors="coerce")
    df["license_year"] = df["license_date"].dt.year
    df["license_month"] = df["license_date"].dt.to_period("M").astype(str)

    # Extract location from address (first token)
    def extract_location(addr: str) -> str:
        if not addr or not str(addr).strip():
            return "Тодорхойгүй"
        tokens = str(addr).strip().split()
        return tokens[0] if tokens else "Тодорхойгүй"

    df["location"] = df["address"].fillna("").apply(extract_location)

    # Normalize location: merge rare ones
    known = {
        "Улаанбаатар", "Дорноговь", "Сэлэнгэ", "Төв", "Дорнод", "Дархан-Уул",
        "Орхон", "Завхан", "Архангай", "Баян-Өлгий", "Баянхонгор", "Булган",
        "Говь-Алтай", "Говьсүмбэр", "Дундговь", "Өвөрхангай", "Өмнөговь",
        "Сүхбаатар", "Увс", "Ховд", "Хөвсгөл", "Хэнтий",
    }
    df["location"] = df["location"].apply(lambda x: x if x in known else "Бусад")

    # CEO flag
    df["has_ceo"] = df["ceo"].fillna("").str.strip().ne("")

    # Industry list
    df["industry_list"] = df["industry_names"].fillna("").apply(
        lambda x: [i.strip() for i in x.split(",") if i.strip()]
    )
    df["industry_count"] = df["industry_list"].apply(len)

    return df


def build_exploded(df: pd.DataFrame) -> pd.DataFrame:
    """One row per entity-industry combination."""
    rows = []
    for _, row in df.iterrows():
        for ind in row["industry_list"]:
            rows.append({"entity_name": row["entity_name"], "industry": ind,
                         "location": row["location"], "license_year": row["license_year"],
                         "has_ceo": row["has_ceo"]})
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["entity_name", "industry", "location", "license_year", "has_ceo"])


def main() -> None:
    inject_styles()

    st.markdown(
        """
        <div class="hero">
            <h1>ББСБ бүртгэл — FRC</h1>
            <p>Санхүүгийн зохицуулах хорооны банк бус санхүүгийн байгуулллагын бүртгэлийн мэдээлэл.</p>
            <p>Эх сурвалж: <code>frc.mn API</code></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not DATA_PATH.exists():
        st.error(f"Файл олдсонгүй: {DATA_PATH}")
        return

    df = load_data(DATA_PATH)
    exploded = build_exploded(df)

    all_industries = sorted(exploded["industry"].dropna().unique().tolist())
    all_locations = sorted(df["location"].dropna().unique().tolist())

    # ── Sidebar filters ─────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Шүүлтүүр")
        sel_industries = st.multiselect("Үйл ажиллагааны төрөл", all_industries)
        sel_locations = st.multiselect("Байршил (аймаг/хот)", all_locations)
        year_min = int(df["license_year"].min()) if df["license_year"].notna().any() else 2010
        year_max = int(df["license_year"].max()) if df["license_year"].notna().any() else 2030
        sel_years = st.slider("Лиценз олгосон он", year_min, year_max, (year_min, year_max))
        only_ceo = st.checkbox("Зөвхөн CEO бүртгэлтэй", value=False)

    # ── Apply filters ───────────────────────────────────────────────────────────
    scope = df.copy()
    if sel_industries:
        scope = scope[scope["industry_list"].apply(lambda lst: any(i in lst for i in sel_industries))]
    if sel_locations:
        scope = scope[scope["location"].isin(sel_locations)]
    scope = scope[scope["license_year"].between(sel_years[0], sel_years[1], inclusive="both") | scope["license_year"].isna()]
    if only_ceo:
        scope = scope[scope["has_ceo"]]

    scope_exploded = build_exploded(scope)

    if scope.empty:
        st.warning("Шүүлтүүрт тохирох байгуулллага алга.")
        return

    # ── Metrics ─────────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Нийт ББСБ", f"{len(scope):,}")
    c2.metric("Байршлын тоо", f"{scope['location'].nunique():,}")
    c3.metric("CEO бүртгэлтэй", f"{scope['has_ceo'].sum():,}")
    c4.metric("Үйл ажиллагааны төрөл", f"{scope_exploded['industry'].nunique():,}")

    st.divider()

    # ── Industry distribution ────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Үйл ажиллагааны төрлөөр</div>', unsafe_allow_html=True)
    ind_counts = (
        scope_exploded.groupby("industry")["entity_name"]
        .nunique()
        .reset_index(name="count")
        .sort_values("count")
    )
    fig_ind = px.bar(
        ind_counts,
        x="count",
        y="industry",
        orientation="h",
        color="count",
        color_continuous_scale=["#1c3c65", "#4895fc", "#8fc1ff"],
        labels={"count": "ББСБ тоо", "industry": "Үйл ажиллагаа"},
        title="ББСБ үйл ажиллагааны төрөл",
    )
    fig_ind.update_layout(coloraxis_showscale=False, yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(style_plot(fig_ind, height=420), use_container_width=True)

    st.divider()

    # ── Geography + License timeline ─────────────────────────────────────────────
    col_geo, col_time = st.columns(2, gap="large")

    with col_geo:
        st.markdown('<div class="section-title">Байршлаар</div>', unsafe_allow_html=True)
        loc_counts = (
            scope.groupby("location")["entity_name"]
            .nunique()
            .reset_index(name="count")
            .sort_values("count")
        )
        fig_loc = px.bar(
            loc_counts,
            x="count",
            y="location",
            orientation="h",
            color="count",
            color_continuous_scale=["#004095", "#4895fc"],
            labels={"count": "ББСБ тоо", "location": "Байршил"},
            title="Байршлаар",
        )
        fig_loc.update_layout(coloraxis_showscale=False, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(style_plot(fig_loc, height=400), use_container_width=True)

    with col_time:
        st.markdown('<div class="section-title">Лиценз олгосон он</div>', unsafe_allow_html=True)
        year_counts = (
            scope[scope["license_year"].notna()]
            .groupby("license_year")["entity_name"]
            .nunique()
            .reset_index(name="count")
            .sort_values("license_year")
        )
        fig_year = px.bar(
            year_counts,
            x="license_year",
            y="count",
            color="count",
            color_continuous_scale=["#1c3c65", BRAND_AMBER],
            labels={"license_year": "Он", "count": "ББСБ тоо"},
            title="Лиценз олгосон он",
        )
        fig_year.update_layout(coloraxis_showscale=False, bargap=0.15)
        st.plotly_chart(style_plot(fig_year, height=400), use_container_width=True)

    st.divider()

    # ── Multi-activity analysis ──────────────────────────────────────────────────
    st.markdown('<div class="section-title">Олон үйл ажиллагаатай байгуулллагууд</div>', unsafe_allow_html=True)
    col_multi1, col_multi2 = st.columns([1, 1.4], gap="large")

    with col_multi1:
        multi_dist = (
            scope.groupby("industry_count")["entity_name"]
            .nunique()
            .reset_index(name="count")
            .rename(columns={"industry_count": "Үйл ажиллагааны тоо"})
        )
        fig_multi = px.pie(
            multi_dist,
            names="Үйл ажиллагааны тоо",
            values="count",
            hole=0.54,
            color_discrete_sequence=[BRAND_DEEP_BLUE, BRAND_BLUE, BRAND_TEAL, BRAND_AMBER, BRAND_SLATE],
            title="Нэг байгуулллагын үйл ажиллагааны тоо",
        )
        fig_multi.update_traces(textinfo="percent+label")
        st.plotly_chart(style_plot(fig_multi, height=360), use_container_width=True)

    with col_multi2:
        multi_top = (
            scope[scope["industry_count"] >= 2][["entity_name", "industry_names", "location", "license_date", "ceo"]]
            .sort_values("industry_names")
            .reset_index(drop=True)
        )
        multi_top["license_date"] = multi_top["license_date"].dt.strftime("%Y-%m-%d")
        multi_top.columns = ["Байгуулллага", "Үйл ажиллагаа", "Байршил", "Лиценз олгосон огноо", "CEO"]
        st.caption(f"2+ үйл ажиллагаатай: {len(multi_top)} байгуулллага")
        st.dataframe(multi_top, use_container_width=True, hide_index=True, height=340)

    st.divider()

    # ── Entity search table ──────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Байгуулллагын хайлт</div>', unsafe_allow_html=True)
    search = st.text_input("Нэрээр хайх", placeholder="ББСБ нэр эсвэл registration дугаар...")
    table = scope[["entity_name", "industry_names", "location", "license_number",
                   "license_date", "registration_number", "ceo", "address"]].copy()
    table["license_date"] = table["license_date"].dt.strftime("%Y-%m-%d")
    if search:
        mask = (
            table["entity_name"].str.contains(search, case=False, na=False)
            | table["registration_number"].astype(str).str.contains(search, na=False)
        )
        table = table[mask]
    table.columns = ["Байгуулллага", "Үйл ажиллагаа", "Байршил", "Лицензийн №",
                     "Лиценз олгосон огноо", "Бүртгэлийн №", "CEO", "Хаяг"]
    st.caption(f"{len(table)} байгуулллага")
    st.dataframe(table, use_container_width=True, hide_index=True, height=460)


if __name__ == "__main__":
    main()
