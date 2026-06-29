"""Combined Streamlit dashboard — Банк & Банк бус (ББСБ).

Tab 1: bank powermap (from bank_powermap_simple.py)
Tab 2: FRC / ББСБ dashboard (from frc_dashboard.py) + radial powermap
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page config — MUST be the very first Streamlit call (module level).
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Банк & ББСБ powermap",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
_BASE_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = _BASE_DIR / "gold_datamart"
DATA_PATH: Path = _BASE_DIR / "frc" / "outputs" / "frc_api_records_guess.jsonl"
INS_DATA_PATH: Path = _BASE_DIR / "frc-insurance" / "outputs" / "frc_insurance_api_records_guess.jsonl"

# ---------------------------------------------------------------------------
# Brand colours (shared)
# ---------------------------------------------------------------------------
BRAND_BLUE: str = "#4895fc"
BRAND_NAVY: str = "#1c3c65"
BRAND_DEEP_BLUE: str = "#004095"
BRAND_SLATE: str = "#2e3b44"
BRAND_ICE: str = "#f2f8ff"
BRAND_TEAL: str = "#0a7ea4"
BRAND_AMBER: str = "#ffb703"


# ---------------------------------------------------------------------------
# Shared style helpers
# ---------------------------------------------------------------------------


def inject_styles() -> None:
    """Inject global dark-theme CSS."""
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
            padding: 1.1rem 1.25rem;
            margin-bottom: .95rem;
            box-shadow: 0 20px 36px rgba(0,0,0,.40);
        }
        .hero h1 { margin: 0 0 .2rem 0; font-size: 1.75rem; color: #f2f8ff !important; }
        .hero p  { margin: .1rem 0; color: #f2f8ff !important; font-size: .96rem; }
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        div[data-testid="stTextInputRootElement"] > div {
            background: rgba(15,24,34,.98) !important;
            color: #edf5ff !important;
            border-color: rgba(72,149,252,.22) !important;
        }
        div[data-baseweb="select"] input,
        div[data-baseweb="select"] span,
        div[data-baseweb="popover"] * { color: #edf5ff !important; }
        div[data-baseweb="popover"] [role="option"]:hover { background: rgba(72,149,252,.12) !important; }
        div[data-baseweb="slider"] * { color: #4895fc !important; }
        .stExpander { border: 1px solid rgba(72,149,252,.18) !important; border-radius: 10px !important; }
        div[data-testid="stDataFrame"] { border: 1px solid rgba(72,149,252,.18); border-radius: 10px; }
        hr { border-color: rgba(72,149,252,.18) !important; }
        .section-title { font-size: 1.1rem; font-weight: 800; color: #8fc1ff; margin-bottom: .2rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def style_plot(fig: go.Figure, height: int | None = None) -> go.Figure:
    """Apply dark theme to a standard Plotly figure."""
    fig.update_layout(
        paper_bgcolor="#0d1b2a",
        plot_bgcolor="#111d2e",
        font=dict(color="#c8dff8", size=12),
        title_font=dict(color="#edf5ff", size=17),
        legend=dict(
            orientation="h",
            bgcolor="rgba(11,18,32,.88)",
            bordercolor="rgba(72,149,252,.22)",
            borderwidth=1,
            font=dict(color="#c8dff8"),
        ),
        hoverlabel=dict(bgcolor="#111d2b", font=dict(color="#eaf2ff")),
        margin=dict(l=20, r=20, t=50, b=20),
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


def style_powermap_dark(fig: go.Figure, height: int = 720) -> go.Figure:
    """Apply dark radial-network theme to a Plotly figure."""
    fig.update_layout(
        height=height,
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0b1220",
        font=dict(color="#eaf2ff", size=12),
        title_font=dict(color="#f2f8ff", size=17),
        legend=dict(
            orientation="h",
            bgcolor="rgba(11,18,32,.88)",
            bordercolor="rgba(143,193,255,.22)",
            borderwidth=1,
            font=dict(color="#eaf2ff"),
        ),
        hoverlabel=dict(bgcolor="#111d2b", font=dict(color="#f2f8ff")),
        margin=dict(l=0, r=0, t=55, b=0),
    )
    fig.update_xaxes(visible=False, range=[-0.10, 1.10], showgrid=False, zeroline=False)
    fig.update_yaxes(visible=False, range=[-0.10, 1.10], showgrid=False, zeroline=False)
    return fig


def _short_label(value: object, max_len: int = 22) -> str:
    """Truncate a string to *max_len* characters, appending '…' if needed."""
    text = str(value)
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


# ===========================================================================
# ── BANK SIDE ──────────────────────────────────────────────────────────────
# ===========================================================================


@st.cache_data(show_spinner=False)
def load_csv_outputs(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Load all bank CSV datamart files."""
    files = {
        "dim_bank": "dim_bank_official.csv",
        "by_bank": "bank_branch_units_latest.csv",
        "fact_map": "bank_branch_units_fact_map_latest.csv",
        "clean_market": "clean_bank_market.csv",
        "matching_report": "bank_matching_report.csv",
    }
    missing = [f for f in files.values() if not (data_dir / f).exists()]
    if missing:
        raise FileNotFoundError(
            "Эхлээд pipeline ажиллуулна уу: python build_clean_bank_market.py"
        )
    data: dict[str, pd.DataFrame] = {
        key: pd.read_csv(data_dir / fname, low_memory=False)
        for key, fname in files.items()
    }
    for key in ("dim_bank", "by_bank", "fact_map", "matching_report"):
        if "register" in data[key].columns:
            data[key]["register"] = data[key]["register"].astype(str)
    return data


@st.cache_data(show_spinner=False)
def load_edges(data_dir: Path) -> pd.DataFrame:
    """Load powermap edge list for banks."""
    cols = [
        "source_company_register",
        "target_party_key",
        "target_party_name",
        "country",
        "relation_type",
        "relation_detail",
        "registered_at",
        "is_foreign",
    ]
    edges = pd.read_csv(data_dir / "powermap_edges.csv", usecols=cols, low_memory=False)
    edges["source_company_register"] = edges["source_company_register"].astype(str)
    return edges


@st.cache_data(show_spinner=False)
def load_company_master(data_dir: Path) -> pd.DataFrame:
    """Load company master table for bank powermap."""
    cols = [
        "register",
        "company_name",
        "company_name_market",
        "company_name_main",
        "aimag",
        "network_intensity_score",
    ]
    company = pd.read_csv(
        data_dir / "powermap_company_master.csv", usecols=cols, low_memory=False
    )
    company["register"] = company["register"].astype(str)
    company["company_label"] = (
        company["company_name"]
        .fillna(company["company_name_market"])
        .fillna(company["company_name_main"])
        .fillna(company["register"])
    )
    return company


def render_map(fact_map: pd.DataFrame) -> None:
    """Render a scatter mapbox of bank branch locations."""
    view = fact_map.copy()
    view["known_unit_count_for_map"] = pd.to_numeric(
        view["known_unit_count_for_map"], errors="coerce"
    ).fillna(0)
    fig = px.scatter_mapbox(
        view,
        lat="latitude",
        lon="longitude",
        size="known_unit_count_for_map",
        color="bank_name_mn",
        hover_name="bank_name_mn",
        hover_data={
            "aimag_city": True,
            "region": True,
            "branch_count": ":,",
            "settlement_center_count": ":,",
            "fx_unit_count": ":,",
            "known_unit_count_for_map": ":,",
            "latitude": False,
            "longitude": False,
        },
        zoom=4.05,
        center={"lat": 46.9, "lon": 103.8},
        height=610,
        size_max=42,
        labels={
            "bank_name_mn": "Банк",
            "aimag_city": "Аймаг/хот",
            "region": "Бүс",
            "branch_count": "Салбар",
            "settlement_center_count": "Тооцооны төв",
            "fx_unit_count": "Валютын нэгж",
            "known_unit_count_for_map": "Map дээрх нэгж",
        },
    )
    fig.update_layout(
        mapbox_style="carto-positron",
        margin=dict(l=0, r=0, t=0, b=0),
        legend_title_text="Банк",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_bank_units(by_bank: pd.DataFrame) -> None:
    """Render a stacked horizontal bar chart of bank unit types."""
    view = by_bank.copy()
    unit_long = view.melt(
        id_vars=["bank_name_mn"],
        value_vars=[
            "branch_count",
            "settlement_center_count",
            "fx_unit_count",
            "representative_office_count",
            "other_unit_count",
        ],
        var_name="unit_type",
        value_name="unit_count",
    )
    unit_labels: dict[str, str] = {
        "branch_count": "Салбар",
        "settlement_center_count": "Тооцооны төв",
        "fx_unit_count": "Валютын нэгж",
        "representative_office_count": "Төлөөлөгчийн газар",
        "other_unit_count": "Бусад",
    }
    unit_long["unit_type"] = unit_long["unit_type"].map(unit_labels)
    merged = unit_long.merge(
        view[["bank_name_mn", "total_unit_count"]], on="bank_name_mn", how="left"
    ).sort_values("total_unit_count")
    merged["label"] = merged["unit_count"].apply(lambda v: str(int(v)) if v > 0 else "")
    fig = px.bar(
        merged,
        x="unit_count",
        y="bank_name_mn",
        color="unit_type",
        text="label",
        orientation="h",
        height=560,
        labels={
            "unit_count": "Нэгжийн тоо",
            "bank_name_mn": "Банк",
            "unit_type": "Нэгжийн төрөл",
        },
        color_discrete_map={
            "Салбар": BRAND_DEEP_BLUE,
            "Тооцооны төв": BRAND_BLUE,
            "Валютын нэгж": BRAND_NAVY,
            "Төлөөлөгчийн газар": "#7a8da0",
            "Бусад": BRAND_SLATE,
        },
    )
    fig.update_traces(textposition="inside", insidetextanchor="middle",
                      textfont=dict(color="#f2f8ff", size=11))
    fig.update_layout(margin=dict(l=0, r=0, t=20, b=0), barmode="stack")
    style_plot(fig, height=560)
    st.plotly_chart(fig, use_container_width=True)


def build_bank_people_company_network(
    matching_report: pd.DataFrame,
    edges: pd.DataFrame,
    company: pd.DataFrame,
    max_people: int,
    max_companies_per_person: int,
    selected_banks: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build the three dataframes needed for render_powermap_graph."""
    matched = matching_report[matching_report["bank_id"].notna()].copy()
    if selected_banks:
        matched = matched[matched["bank_name_mn"].isin(selected_banks)].copy()
    matched["register"] = matched["register"].astype(str)
    edges = edges.copy()
    edges["source_company_register"] = edges["source_company_register"].astype(str)
    company = company.copy()
    company["register"] = company["register"].astype(str)

    bank_edges = edges[
        edges["source_company_register"].isin(set(matched["register"]))
    ].copy()
    bank_edges = bank_edges.merge(
        matched[["register", "bank_name_mn", "short_name"]].rename(
            columns={"register": "source_company_register"}
        ),
        on="source_company_register",
        how="left",
    )
    bank_edges = bank_edges[
        bank_edges["relation_type"].isin(
            ["representative", "shareholder", "ultimate_owner"]
        )
    ].copy()
    aggregate_party = (
        bank_edges["target_party_name"].fillna("").str.upper().str.contains("НИЙТ|ОЛОН НИЙТ")
    )
    aggregate_key = (
        bank_edges["target_party_key"]
        .fillna("")
        .str.upper()
        .str.contains("PARTY::::НИЙТ|TOTAL")
    )
    bank_edges = bank_edges[~aggregate_party & ~aggregate_key].copy()

    people_rank = (
        bank_edges.groupby(["target_party_key", "target_party_name"], as_index=False)
        .agg(
            bank_links=("source_company_register", "nunique"),
            relation_rows=("target_party_key", "size"),
        )
        .sort_values(["bank_links", "relation_rows"], ascending=False)
        .head(max_people)
    )
    selected_people = set(people_rank["target_party_key"])
    bank_people_edges = bank_edges[
        bank_edges["target_party_key"].isin(selected_people)
    ].copy()

    other_edges = edges[
        edges["target_party_key"].isin(selected_people)
        & ~edges["source_company_register"].isin(set(matched["register"]))
    ].copy()
    other_edges = other_edges.merge(
        company[
            ["register", "company_label", "aimag", "network_intensity_score"]
        ].rename(columns={"register": "source_company_register"}),
        on="source_company_register",
        how="left",
    )
    other_edges["company_rank"] = other_edges.groupby("target_party_key")[
        "network_intensity_score"
    ].rank(method="first", ascending=False)
    other_edges = other_edges[
        other_edges["company_rank"].le(max_companies_per_person)
    ].copy()
    return bank_people_edges, other_edges, people_rank


def render_powermap_graph(
    selected_bank_name: str,
    bank_people_edges: pd.DataFrame,
    other_edges: pd.DataFrame,
) -> None:
    """Render the radial powermap for a single bank."""
    if bank_people_edges.empty:
        st.info("Холбоос олдсонгүй.")
        return

    center_x, center_y = 0.5, 0.5
    fig = go.Figure()

    people = (
        bank_people_edges.groupby(
            ["target_party_key", "target_party_name"], as_index=False
        )
        .agg(
            link_rows=("target_party_key", "size"),
            relation_types=(
                "relation_type",
                lambda s: ", ".join(sorted(set(s.astype(str)))),
            ),
        )
        .sort_values(["link_rows", "target_party_name"], ascending=[False, True])
        .reset_index(drop=True)
    )
    companies = (
        other_edges.groupby(
            ["source_company_register", "company_label"], as_index=False
        )
        .agg(
            link_rows=("target_party_key", "size"),
            people_count=("target_party_key", "nunique"),
        )
        .sort_values(
            ["people_count", "link_rows", "company_label"], ascending=[False, False, True]
        )
        .reset_index(drop=True)
    )

    def _circle_positions(
        ids: list[str], radius: float, start_angle: float = -math.pi / 2
    ) -> dict[str, tuple[float, float]]:
        total = max(len(ids), 1)
        return {
            node_id: (
                center_x + radius * math.cos(start_angle + 2 * math.pi * idx / total),
                center_y + radius * math.sin(start_angle + 2 * math.pi * idx / total),
            )
            for idx, node_id in enumerate(ids)
        }

    people_ids = people["target_party_key"].astype(str).tolist()
    company_ids = companies["source_company_register"].astype(str).tolist()
    people_pos = _circle_positions(people_ids, 0.30)
    company_pos = _circle_positions(company_ids, 0.52)

    relation_colors: dict[str, str] = {
        "representative": "rgba(72,149,252,.75)",
        "shareholder": "rgba(143,193,255,.65)",
        "ultimate_owner": "rgba(242,248,255,.50)",
    }
    for relation_type, rel_df in bank_people_edges.groupby("relation_type"):
        xs: list[float | None] = []
        ys: list[float | None] = []
        for row in rel_df.itertuples(index=False):
            person_id = str(row.target_party_key)
            if person_id not in people_pos:
                continue
            xs.extend([center_x, people_pos[person_id][0], None])
            ys.extend([center_y, people_pos[person_id][1], None])
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line=dict(
                    color=relation_colors.get(
                        str(relation_type), "rgba(180,190,205,.45)"
                    ),
                    width=1.6,
                ),
                opacity=0.85,
                name=str(relation_type),
                hoverinfo="skip",
            )
        )

    xs_other: list[float | None] = []
    ys_other: list[float | None] = []
    for row in other_edges.itertuples(index=False):
        person_id = str(row.target_party_key)
        company_id = str(row.source_company_register)
        if person_id not in people_pos or company_id not in company_pos:
            continue
        xs_other.extend([people_pos[person_id][0], company_pos[company_id][0], None])
        ys_other.extend([people_pos[person_id][1], company_pos[company_id][1], None])
    fig.add_trace(
        go.Scatter(
            x=xs_other,
            y=ys_other,
            mode="lines",
            line=dict(color="rgba(143,193,255,.25)", width=0.9),
            name="хүн → бусад компани",
            hoverinfo="skip",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[center_x],
            y=[center_y],
            mode="markers+text",
            text=[_short_label(selected_bank_name, 18)],
            textposition="bottom center",
            textfont=dict(size=12, color="#f2f8ff"),
            marker=dict(
                size=48, color="#004095", line=dict(color="#8fc1ff", width=3)
            ),
            name="Сонгосон банк",
            hovertemplate=f"<b>{selected_bank_name}</b><extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[people_pos[str(r.target_party_key)][0] for r in people.itertuples(index=False)],
            y=[people_pos[str(r.target_party_key)][1] for r in people.itertuples(index=False)],
            mode="markers+text",
            text=[_short_label(r.target_party_name) for r in people.itertuples(index=False)],
            textposition="middle center",
            textfont=dict(size=10, color="#f2f8ff"),
            marker=dict(size=22, color="#4895fc", line=dict(color="#f2f8ff", width=2)),
            name="Хүн/этгээд",
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Холбооны төрөл: %{customdata[1]}<br>"
                "Link rows: %{customdata[2]}<extra></extra>"
            ),
            customdata=[
                [r.target_party_name, r.relation_types, int(r.link_rows)]
                for r in people.itertuples(index=False)
            ],
        )
    )

    if not companies.empty:
        fig.add_trace(
            go.Scatter(
                x=[
                    company_pos[str(r.source_company_register)][0]
                    for r in companies.itertuples(index=False)
                ],
                y=[
                    company_pos[str(r.source_company_register)][1]
                    for r in companies.itertuples(index=False)
                ],
                mode="markers+text",
                text=[
                    _short_label(r.company_label)
                    for r in companies.itertuples(index=False)
                ],
                textposition="middle center",
                textfont=dict(size=9, color="#c8dff8"),
                marker=dict(
                    size=14, color="#2e3b44", line=dict(color="#8fc1ff", width=1.5)
                ),
                name="Бусад компани",
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Холбогдсон хүн/этгээд: %{customdata[1]}<br>"
                    "Link rows: %{customdata[2]}<extra></extra>"
                ),
                customdata=[
                    [r.company_label, int(r.people_count), int(r.link_rows)]
                    for r in companies.itertuples(index=False)
                ],
            )
        )

    fig.update_layout(
        title=f"Radial powermap — {selected_bank_name}",
        showlegend=True,
        legend=dict(orientation="h"),
    )
    style_powermap_dark(fig, height=740)
    st.plotly_chart(fig, use_container_width=True)


def render_network(
    matching_report: pd.DataFrame,
    edges: pd.DataFrame,
    company: pd.DataFrame,
    selected_banks: list[str],
) -> None:
    """Bank powermap: selectbox + metrics + radial graph."""
    available = sorted(
        matching_report.loc[
            matching_report["bank_id"].notna(), "bank_name_mn"
        ]
        .dropna()
        .unique()
        .tolist()
    )
    powermap_options = [b for b in available if b in selected_banks] or available
    selected_bank = st.selectbox(
        "Powermap-д харуулах банк",
        powermap_options,
        key="app_powermap_bank_select",
    )

    bank_people_edges, other_edges, people_rank = build_bank_people_company_network(
        matching_report,
        edges,
        company,
        max_people=18,
        max_companies_per_person=8,
        selected_banks=[selected_bank],
    )

    c1, c2 = st.columns(2)
    c1.metric("Хүн/этгээд", f"{people_rank['target_party_key'].nunique():,}")
    c2.metric(
        "Холбогдсон бусад компани",
        f"{other_edges['source_company_register'].nunique():,}",
    )

    render_powermap_graph(selected_bank, bank_people_edges, other_edges)


# ===========================================================================
# ── FRC / ББСБ SIDE ────────────────────────────────────────────────────────
# ===========================================================================


@st.cache_data(show_spinner=False)
def load_frc_data(path: Path) -> pd.DataFrame:
    """Load and parse the FRC JSONL records file."""
    rows: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if "financial_activities_name" not in d:
                continue
            rows.append(d)
    df = pd.DataFrame(rows)

    df["entity_name"] = (
        df["entity_name"].str.replace("&quot;", "", regex=False).str.strip()
    )
    df["license_date"] = pd.to_datetime(df["license_date"], errors="coerce")
    df["license_year"] = df["license_date"].dt.year
    df["license_month"] = df["license_date"].dt.to_period("M").astype(str)

    def _extract_location(addr: str) -> str:
        if not addr or not str(addr).strip():
            return "Тодорхойгүй"
        tokens = str(addr).strip().split()
        return tokens[0] if tokens else "Тодорхойгүй"

    df["location"] = df["address"].fillna("").apply(_extract_location)

    known_locations = {
        "Улаанбаатар", "Дорноговь", "Сэлэнгэ", "Төв", "Дорнод", "Дархан-Уул",
        "Орхон", "Завхан", "Архангай", "Баян-Өлгий", "Баянхонгор", "Булган",
        "Говь-Алтай", "Говьсүмбэр", "Дундговь", "Өвөрхангай", "Өмнөговь",
        "Сүхбаатар", "Увс", "Ховд", "Хөвсгөл", "Хэнтий",
    }
    df["location"] = df["location"].apply(
        lambda x: x if x in known_locations else "Бусад"
    )

    df["has_ceo"] = df["ceo"].fillna("").str.strip().ne("")
    df["industry_list"] = df["industry_names"].fillna("").apply(
        lambda x: [i.strip() for i in x.split(",") if i.strip()]
    )
    df["industry_count"] = df["industry_list"].apply(len)
    return df


def build_exploded(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per entity-industry combination."""
    rows: list[dict] = []
    for _, row in df.iterrows():
        for ind in row["industry_list"]:
            rows.append(
                {
                    "entity_name": row["entity_name"],
                    "industry": ind,
                    "location": row["location"],
                    "license_year": row["license_year"],
                    "has_ceo": row["has_ceo"],
                }
            )
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(
        columns=["entity_name", "industry", "location", "license_year", "has_ceo"]
    )


def render_frc_powermap(
    df: pd.DataFrame,
    edges: pd.DataFrame,
    company: pd.DataFrame,
) -> None:
    """Radial powermap for FRC/ББСБ data.

    Center : selected ББСБ
    Ring 1 (radius=0.30): people/entities connected via powermap_edges
    Ring 2 (radius=0.52): other companies those people are connected to
    """
    entity_names = sorted(df["entity_name"].dropna().unique().tolist())
    if not entity_names:
        st.info("ББСБ олдсонгүй.")
        return

    selected_entity = st.selectbox(
        "Powermap-д харуулах ББСБ",
        entity_names,
        key="frc_powermap_entity_select",
    )

    row_mask = df["entity_name"] == selected_entity
    if not row_mask.any():
        st.info("Сонгосон ББСБ-ийн мэдээлэл олдсонгүй.")
        return

    entity_row = df[row_mask].iloc[0]
    reg_num = str(entity_row["registration_number"])

    # Edges for the selected ББСБ
    bbsb_edges = edges[edges["source_company_register"] == reg_num].copy()

    if bbsb_edges.empty:
        st.info("Энэ ББСБ-д powermap edges дата олдсонгүй.")
        return

    # Ring 1: top parties (people / entities)
    parties = (
        bbsb_edges.groupby(["target_party_key", "target_party_name"], as_index=False)
        .agg(
            link_rows=("target_party_name", "size"),
            relation_types=("relation_type", lambda s: ", ".join(sorted(set(s.astype(str))))),
        )
        .sort_values("link_rows", ascending=False)
        .head(12)
        .reset_index(drop=True)
    )

    # Ring 2: other companies connected to those parties
    party_keys = set(parties["target_party_key"])
    other_edges = edges[
        edges["target_party_key"].isin(party_keys)
        & (edges["source_company_register"] != reg_num)
    ].copy()
    other_companies = (
        other_edges.groupby("source_company_register", as_index=False)
        .agg(
            people_count=("target_party_key", "nunique"),
            link_rows=("target_party_key", "size"),
        )
        .merge(
            company[["register", "company_label"]],
            left_on="source_company_register",
            right_on="register",
            how="left",
        )
        .sort_values(["people_count", "link_rows"], ascending=[False, False])
        .head(12)
        .reset_index(drop=True)
    )

    # Metrics
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Холбогдсон этгээд", len(parties))
    mc2.metric("Холбоосын тоо", len(bbsb_edges))
    mc3.metric("Бусад холбоотой компани", len(other_companies))

    # ── Build figure ─────────────────────────────────────────────────────────
    center_x, center_y = 0.5, 0.5
    fig = go.Figure()

    def _ring_pos(ids: list[str], radius: float) -> dict[str, tuple[float, float]]:
        total = max(len(ids), 1)
        return {
            node_id: (
                center_x + radius * math.cos(-math.pi / 2 + 2 * math.pi * i / total),
                center_y + radius * math.sin(-math.pi / 2 + 2 * math.pi * i / total),
            )
            for i, node_id in enumerate(ids)
        }

    party_ids = parties["target_party_key"].astype(str).tolist()
    party_names = parties["target_party_name"].tolist()
    company_ids = other_companies["source_company_register"].astype(str).tolist()
    company_labels = other_companies["company_label"].fillna(other_companies["source_company_register"]).tolist()

    party_pos = _ring_pos(party_ids, 0.30)
    company_pos = _ring_pos(company_ids, 0.52)

    # Edges: center → party ring
    xs: list[float | None] = []
    ys: list[float | None] = []
    for row in parties.itertuples(index=False):
        pid = str(row.target_party_key)
        px_, py_ = party_pos[pid]
        xs.extend([center_x, px_, None])
        ys.extend([center_y, py_, None])
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines",
        line=dict(color="rgba(72,149,252,.65)", width=1.6),
        hoverinfo="skip", name="ББСБ → этгээд"))

    # Edges: party ring → company ring
    xs2: list[float | None] = []
    ys2: list[float | None] = []
    for row in other_edges[other_edges["source_company_register"].isin(company_ids)].itertuples(index=False):
        pid = str(row.target_party_key)
        cid = str(row.source_company_register)
        if pid in party_pos and cid in company_pos:
            px_, py_ = party_pos[pid]
            cx_, cy_ = company_pos[cid]
            xs2.extend([px_, cx_, None])
            ys2.extend([py_, cy_, None])
    fig.add_trace(go.Scatter(x=xs2, y=ys2, mode="lines",
        line=dict(color="rgba(143,193,255,.22)", width=0.9),
        hoverinfo="skip", name="Этгээд → бусад компани"))

    # Center node
    fig.add_trace(go.Scatter(
        x=[center_x], y=[center_y],
        mode="markers+text",
        text=[_short_label(selected_entity, 20)],
        textposition="bottom center",
        textfont=dict(size=12, color="#f2f8ff"),
        marker=dict(size=44, color="#004095", line=dict(color="#8fc1ff", width=3)),
        name="Сонгосон ББСБ",
        hovertemplate=f"<b>{selected_entity}</b><br>Бүртгэл: {reg_num}<extra></extra>",
    ))

    # Ring 1: people / entities
    fig.add_trace(go.Scatter(
        x=[party_pos[pid][0] for pid in party_ids],
        y=[party_pos[pid][1] for pid in party_ids],
        mode="markers+text",
        text=[_short_label(n, 18) for n in party_names],
        textposition="middle center",
        textfont=dict(size=10, color="#f2f8ff"),
        marker=dict(size=22, color="#4895fc", line=dict(color="#f2f8ff", width=2)),
        name="Хүн / этгээд",
        hovertemplate="<b>%{customdata[0]}</b><br>Холбоосын төрөл: %{customdata[1]}<br>Link rows: %{customdata[2]}<extra></extra>",
        customdata=[
            [row.target_party_name, row.relation_types, int(row.link_rows)]
            for row in parties.itertuples(index=False)
        ],
    ))

    # Ring 2: other companies
    if company_ids:
        fig.add_trace(go.Scatter(
            x=[company_pos[cid][0] for cid in company_ids],
            y=[company_pos[cid][1] for cid in company_ids],
            mode="markers+text",
            text=[_short_label(lbl, 16) for lbl in company_labels],
            textposition="middle center",
            textfont=dict(size=9, color="#c8dff8"),
            marker=dict(size=14, color="#2e3b44", line=dict(color="#8fc1ff", width=1.5)),
            name="Бусад компани",
            hovertemplate="<b>%{customdata[0]}</b><br>Холбогдсон этгээд: %{customdata[1]}<extra></extra>",
            customdata=[
                [lbl, int(row.people_count)]
                for lbl, row in zip(company_labels, other_companies.itertuples(index=False))
            ],
        ))

    fig.update_layout(
        title=f"ББСБ Powermap — {_short_label(selected_entity, 40)}",
        showlegend=True,
        legend=dict(orientation="h"),
    )
    style_powermap_dark(fig, height=740)
    st.plotly_chart(fig, use_container_width=True)


# ===========================================================================
# ── MAIN ───────────────────────────────────────────────────────────────────
# ===========================================================================


def main() -> None:  # noqa: C901  (intentionally one large orchestrator)
    inject_styles()

    # ── Hero banner ──────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="hero">
            <h1>Банк &amp; ББСБ powermap</h1>
            <p>Монголбанк болон Санхүүгийн зохицуулах хорооны мэдээлэлд үндэслэсэн харьцуулсан dashboard.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Load bank data (may fail gracefully) ─────────────────────────────────
    bank_load_error: str | None = None
    bank_data: dict[str, pd.DataFrame] = {}
    bank_edges_df: pd.DataFrame = pd.DataFrame()
    bank_company_df: pd.DataFrame = pd.DataFrame()
    try:
        bank_data = load_csv_outputs(DATA_DIR)
        bank_edges_df = load_edges(DATA_DIR)
        bank_company_df = load_company_master(DATA_DIR)
    except FileNotFoundError as exc:
        bank_load_error = str(exc)

    # ── Load FRC data (may fail gracefully) ──────────────────────────────────
    frc_load_error: str | None = None
    frc_df: pd.DataFrame = pd.DataFrame()
    if DATA_PATH.exists():
        frc_df = load_frc_data(DATA_PATH)
    else:
        frc_load_error = f"FRC файл олдсонгүй: {DATA_PATH}"

    ins_load_error: str | None = None
    ins_df: pd.DataFrame = pd.DataFrame()
    if INS_DATA_PATH.exists():
        ins_df = load_frc_data(INS_DATA_PATH)
    else:
        ins_load_error = f"Даатгалын файл олдсонгүй: {INS_DATA_PATH}"

    # ── Sidebar ──────────────────────────────────────────────────────────────
    # Bank sidebar filters
    selected_banks: list[str] = []
    selected_regions: list[str] = []
    with st.sidebar.expander("🏦 Банк шүүлтүүр", expanded=True):
        if bank_load_error:
            st.warning("Банкны өгөгдөл ачаалагдаагүй.")
        else:
            fact_map = bank_data["fact_map"]
            banks_all = sorted(fact_map["bank_name_mn"].dropna().unique())
            regions_all = sorted(fact_map["region"].dropna().unique())
            selected_banks = st.multiselect(
                "Банк сонгох",
                banks_all,
                default=banks_all,
                help="Нэг эсвэл хэд хэдэн банк сонгоод газрын зураг, нэгж, powermap-ийг шүүнэ.",
            )
            selected_regions = st.multiselect(
                "Бүс", regions_all, default=regions_all
            )
            if not selected_banks:
                selected_banks = banks_all
                st.info("Банк сонгоогүй тул бүх банк харуулж байна.")
            if not selected_regions:
                selected_regions = regions_all
                st.info("Бүс сонгоогүй тул бүх бүс харуулж байна.")
            st.caption(f"Сонгосон банк: {len(selected_banks)} / {len(banks_all)}")

    # FRC sidebar filters
    sel_industries: list[str] = []
    sel_locations: list[str] = []
    sel_years: tuple[int, int] = (2010, 2030)
    only_ceo: bool = False
    with st.sidebar.expander("🏢 ББСБ шүүлтүүр", expanded=False):
        if frc_load_error:
            st.warning("FRC өгөгдөл ачаалагдаагүй.")
        else:
            frc_exploded_all = build_exploded(frc_df)
            all_industries = sorted(
                frc_exploded_all["industry"].dropna().unique().tolist()
            )
            all_locations = sorted(frc_df["location"].dropna().unique().tolist())
            sel_industries = st.multiselect("Үйл ажиллагааны төрөл", all_industries)
            sel_locations = st.multiselect("Байршил (аймаг/хот)", all_locations)
            year_min = (
                int(frc_df["license_year"].min())
                if frc_df["license_year"].notna().any()
                else 2010
            )
            year_max = (
                int(frc_df["license_year"].max())
                if frc_df["license_year"].notna().any()
                else 2030
            )
            sel_years = st.slider(
                "Лиценз олгосон он",
                year_min,
                year_max,
                (year_min, year_max),
            )
            only_ceo = st.checkbox("Зөвхөн CEO бүртгэлтэй", value=False)

    # Insurance sidebar filters
    sel_ins_industries: list[str] = []
    sel_ins_locations: list[str] = []
    sel_ins_years: tuple[int, int] = (2000, 2030)
    only_ins_ceo: bool = False
    with st.sidebar.expander("🛡️ Даатгал шүүлтүүр", expanded=False):
        if ins_load_error:
            st.warning("Даатгалын өгөгдөл ачаалагдаагүй.")
        else:
            ins_exploded_all = build_exploded(ins_df)
            ins_all_industries = sorted(ins_exploded_all["industry"].dropna().unique().tolist())
            ins_all_locations = sorted(ins_df["location"].dropna().unique().tolist())
            sel_ins_industries = st.multiselect("Үйл ажиллагааны төрөл", ins_all_industries, key="ins_ind")
            sel_ins_locations = st.multiselect("Байршил (аймаг/хот)", ins_all_locations, key="ins_loc")
            ins_year_min = int(ins_df["license_year"].min()) if ins_df["license_year"].notna().any() else 2000
            ins_year_max = int(ins_df["license_year"].max()) if ins_df["license_year"].notna().any() else 2030
            sel_ins_years = st.slider("Лиценз олгосон он", ins_year_min, ins_year_max, (ins_year_min, ins_year_max), key="ins_yr")
            only_ins_ceo = st.checkbox("Зөвхөн CEO бүртгэлтэй", value=False, key="ins_ceo")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_bank, tab_frc, tab_ins = st.tabs(["🏦 Банк", "🏢 Банк бус (ББСБ)", "🛡️ Даатгал"])

    # ════════════════════════════════════════════════════════════════════════
    with tab_bank:
        if bank_load_error:
            st.error(bank_load_error)
        else:
            dim_bank = bank_data["dim_bank"]
            by_bank = bank_data["by_bank"]
            fact_map = bank_data["fact_map"]
            matching_report = bank_data["matching_report"]

            fact_filtered = fact_map[
                fact_map["bank_name_mn"].isin(selected_banks)
                & fact_map["region"].isin(selected_regions)
            ].copy()
            bank_filtered = by_bank[
                by_bank["bank_name_mn"].isin(selected_banks)
            ].copy()

            # Metrics
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Банк", f"{dim_bank['bank_id'].nunique():,}")
            c2.metric("Салбар", f"{bank_filtered['branch_count'].sum():,.0f}")
            c3.metric(
                "Тооцооны төв",
                f"{bank_filtered['settlement_center_count'].sum():,.0f}",
            )
            c4.metric(
                "Валютын нэгж",
                f"{bank_filtered['fx_unit_count'].sum():,.0f}",
            )
            c5.metric(
                "Нийт нэгж",
                f"{bank_filtered['total_unit_count'].sum():,.0f}",
            )

            st.divider()

            st.subheader("Газрын зураг")
            render_map(fact_filtered)

            st.divider()

            st.subheader("Банкны нэгж")
            render_bank_units(bank_filtered)

            st.divider()

            st.subheader("Удирдлага / эзэмшигч")
            st.caption(
                "Зүүн талд банк, дунд талд тухайн банктай холбогдсон хүн/эзэмшигч, "
                "баруун талд тэр хүний бусад холбоотой компани харагдана."
            )
            render_network(
                matching_report, bank_edges_df, bank_company_df, selected_banks
            )

    # ════════════════════════════════════════════════════════════════════════
    with tab_frc:
        if frc_load_error:
            st.error(frc_load_error)
        else:
            # Apply sidebar filters
            scope = frc_df.copy()
            if sel_industries:
                scope = scope[
                    scope["industry_list"].apply(
                        lambda lst: any(i in lst for i in sel_industries)
                    )
                ]
            if sel_locations:
                scope = scope[scope["location"].isin(sel_locations)]
            scope = scope[
                scope["license_year"].between(
                    sel_years[0], sel_years[1], inclusive="both"
                )
                | scope["license_year"].isna()
            ]
            if only_ceo:
                scope = scope[scope["has_ceo"]]

            if scope.empty:
                st.warning("Шүүлтүүрт тохирох байгуулллага алга.")
            else:
                scope_exploded = build_exploded(scope)

                # Metrics
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Нийт ББСБ", f"{len(scope):,}")
                c2.metric("Байршлын тоо", f"{scope['location'].nunique():,}")
                c3.metric("CEO бүртгэлтэй", f"{scope['has_ceo'].sum():,}")
                c4.metric(
                    "Үйл ажиллагааны төрөл",
                    f"{scope_exploded['industry'].nunique():,}",
                )

                st.divider()

                # Industry distribution chart
                st.markdown(
                    '<div class="section-title">Үйл ажиллагааны төрлөөр</div>',
                    unsafe_allow_html=True,
                )
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
                    text="count",
                    color_continuous_scale=["#1c3c65", "#4895fc", "#8fc1ff"],
                    labels={"count": "ББСБ тоо", "industry": "Үйл ажиллагаа"},
                    title="ББСБ үйл ажиллагааны төрөл",
                )
                fig_ind.update_traces(textposition="outside", textfont_color="#edf5ff")
                fig_ind.update_layout(
                    coloraxis_showscale=False,
                    yaxis={"categoryorder": "total ascending"},
                    xaxis={"range": [0, ind_counts["count"].max() * 1.15]},
                )
                st.plotly_chart(
                    style_plot(fig_ind, height=420), use_container_width=True
                )

                st.divider()

                # Geography + License timeline
                col_geo, col_time = st.columns(2, gap="large")

                with col_geo:
                    st.markdown(
                        '<div class="section-title">Байршлаар</div>',
                        unsafe_allow_html=True,
                    )
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
                        text="count",
                        color_continuous_scale=["#004095", "#4895fc"],
                        labels={"count": "ББСБ тоо", "location": "Байршил"},
                        title="Байршлаар",
                    )
                    fig_loc.update_traces(textposition="outside", textfont_color="#edf5ff")
                    fig_loc.update_layout(
                        coloraxis_showscale=False,
                        yaxis={"categoryorder": "total ascending"},
                        xaxis={"range": [0, loc_counts["count"].max() * 1.18]},
                    )
                    st.plotly_chart(
                        style_plot(fig_loc, height=400), use_container_width=True
                    )

                with col_time:
                    st.markdown(
                        '<div class="section-title">Лиценз олгосон он</div>',
                        unsafe_allow_html=True,
                    )
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
                        text="count",
                        color_continuous_scale=["#1c3c65", BRAND_AMBER],
                        labels={"license_year": "Он", "count": "ББСБ тоо"},
                        title="Лиценз олгосон он",
                    )
                    fig_year.update_traces(textposition="outside", textfont_color="#edf5ff")
                    fig_year.update_layout(
                        coloraxis_showscale=False, bargap=0.15,
                        yaxis={"range": [0, year_counts["count"].max() * 1.18]},
                    )
                    st.plotly_chart(
                        style_plot(fig_year, height=400), use_container_width=True
                    )

                st.divider()

                # Multi-activity analysis
                st.markdown(
                    '<div class="section-title">Олон үйл ажиллагаатай байгуулллагууд</div>',
                    unsafe_allow_html=True,
                )
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
                        color_discrete_sequence=[
                            BRAND_DEEP_BLUE,
                            BRAND_BLUE,
                            BRAND_TEAL,
                            BRAND_AMBER,
                            BRAND_SLATE,
                        ],
                        title="Нэг байгуулллагын үйл ажиллагааны тоо",
                    )
                    fig_multi.update_traces(textinfo="percent+label")
                    st.plotly_chart(
                        style_plot(fig_multi, height=360), use_container_width=True
                    )

                with col_multi2:
                    multi_top = (
                        scope[scope["industry_count"] >= 2][
                            [
                                "entity_name",
                                "industry_names",
                                "location",
                                "license_date",
                                "ceo",
                            ]
                        ]
                        .sort_values("industry_names")
                        .reset_index(drop=True)
                    )
                    multi_top["license_date"] = multi_top[
                        "license_date"
                    ].dt.strftime("%Y-%m-%d")
                    multi_top.columns = [
                        "Байгуулллага",
                        "Үйл ажиллагаа",
                        "Байршил",
                        "Лиценз олгосон огноо",
                        "CEO",
                    ]
                    st.caption(
                        f"2+ үйл ажиллагаатай: {len(multi_top)} байгуулллага"
                    )
                    st.dataframe(
                        multi_top,
                        use_container_width=True,
                        hide_index=True,
                        height=340,
                    )

                st.divider()

                # FRC Powermap
                st.subheader("ББСБ Radial Powermap")
                st.caption(
                    "Сонгосон ББСБ (төв), тухайн байгуулллагатай холбогдсон хүн/этгээд (1-р тойрог), "
                    "тэдгээр этгээдтэй холбоотой бусад компаниуд (2-р тойрог)."
                )
                render_frc_powermap(scope, bank_edges_df, bank_company_df)

                st.divider()

                # Searchable entity table
                st.markdown(
                    '<div class="section-title">Байгуулллагын хайлт</div>',
                    unsafe_allow_html=True,
                )
                search = st.text_input(
                    "Нэрээр хайх",
                    placeholder="ББСБ нэр эсвэл registration дугаар...",
                    key="frc_entity_search",
                )
                table = scope[
                    [
                        "entity_name",
                        "industry_names",
                        "location",
                        "license_number",
                        "license_date",
                        "registration_number",
                        "ceo",
                        "address",
                    ]
                ].copy()
                table["license_date"] = table["license_date"].dt.strftime("%Y-%m-%d")
                if search:
                    mask = table["entity_name"].str.contains(
                        search, case=False, na=False
                    ) | table["registration_number"].astype(str).str.contains(
                        search, na=False
                    )
                    table = table[mask]
                table.columns = [
                    "Байгуулллага",
                    "Үйл ажиллагаа",
                    "Байршил",
                    "Лицензийн №",
                    "Лиценз олгосон огноо",
                    "Бүртгэлийн №",
                    "CEO",
                    "Хаяг",
                ]
                st.caption(f"{len(table)} байгуулллага")
                st.dataframe(
                    table, use_container_width=True, hide_index=True, height=460
                )


    # ── Insurance tab ─────────────────────────────────────────────────────────
    with tab_ins:
        if ins_load_error:
            st.error(ins_load_error)
        else:
            ins_scope = ins_df.copy()
            if sel_ins_industries:
                ins_scope = ins_scope[ins_scope["industry_list"].apply(
                    lambda lst: any(i in lst for i in sel_ins_industries))]
            if sel_ins_locations:
                ins_scope = ins_scope[ins_scope["location"].isin(sel_ins_locations)]
            ins_scope = ins_scope[
                ins_scope["license_year"].between(sel_ins_years[0], sel_ins_years[1], inclusive="both")
                | ins_scope["license_year"].isna()
            ]
            if only_ins_ceo:
                ins_scope = ins_scope[ins_scope["has_ceo"]]

            if ins_scope.empty:
                st.warning("Шүүлтүүрт тохирох байгуулллага алга.")
            else:
                ins_scope_ex = build_exploded(ins_scope)

                # Metrics
                ic1, ic2, ic3, ic4 = st.columns(4)
                ic1.metric("Нийт байгуулллага", f"{len(ins_scope):,}")
                ic2.metric("Байршлын тоо", f"{ins_scope['location'].nunique():,}")
                ic3.metric("CEO бүртгэлтэй", f"{ins_scope['has_ceo'].sum():,}")
                ic4.metric("Үйл ажиллагааны төрөл", f"{ins_scope_ex['industry'].nunique():,}")

                st.divider()

                # Industry distribution
                st.markdown('<div class="section-title">Үйл ажиллагааны төрлөөр</div>', unsafe_allow_html=True)
                ins_ind_counts = (
                    ins_scope_ex.groupby("industry")["entity_name"]
                    .nunique().reset_index(name="count").sort_values("count")
                )
                fig_ii = px.bar(ins_ind_counts, x="count", y="industry", orientation="h",
                    color="count", text="count",
                    color_continuous_scale=["#1c3c65", "#4895fc", "#8fc1ff"],
                    labels={"count": "Байгуулллага тоо", "industry": "Үйл ажиллагаа"},
                    title="Даатгалын байгуулллагын үйл ажиллагааны төрөл")
                fig_ii.update_traces(textposition="outside", textfont_color="#edf5ff")
                fig_ii.update_layout(coloraxis_showscale=False,
                    yaxis={"categoryorder": "total ascending"},
                    xaxis={"range": [0, ins_ind_counts["count"].max() * 1.15]})
                st.plotly_chart(style_plot(fig_ii, height=420), use_container_width=True)

                st.divider()

                col_ig, col_it = st.columns(2, gap="large")
                with col_ig:
                    st.markdown('<div class="section-title">Байршлаар</div>', unsafe_allow_html=True)
                    ins_loc_counts = (
                        ins_scope.groupby("location")["entity_name"]
                        .nunique().reset_index(name="count").sort_values("count")
                    )
                    fig_il = px.bar(ins_loc_counts, x="count", y="location", orientation="h",
                        color="count", text="count",
                        color_continuous_scale=["#004095", "#4895fc"],
                        labels={"count": "Байгуулллага тоо", "location": "Байршил"},
                        title="Байршлаар")
                    fig_il.update_traces(textposition="outside", textfont_color="#edf5ff")
                    fig_il.update_layout(coloraxis_showscale=False,
                        yaxis={"categoryorder": "total ascending"},
                        xaxis={"range": [0, ins_loc_counts["count"].max() * 1.18]})
                    st.plotly_chart(style_plot(fig_il, height=400), use_container_width=True)

                with col_it:
                    st.markdown('<div class="section-title">Лиценз олгосон он</div>', unsafe_allow_html=True)
                    ins_year_counts = (
                        ins_scope[ins_scope["license_year"].notna()]
                        .groupby("license_year")["entity_name"]
                        .nunique().reset_index(name="count").sort_values("license_year")
                    )
                    fig_iy = px.bar(ins_year_counts, x="license_year", y="count",
                        color="count", text="count",
                        color_continuous_scale=["#1c3c65", BRAND_AMBER],
                        labels={"license_year": "Он", "count": "Байгуулллага тоо"},
                        title="Лиценз олгосон он")
                    fig_iy.update_traces(textposition="outside", textfont_color="#edf5ff")
                    fig_iy.update_layout(coloraxis_showscale=False, bargap=0.15,
                        yaxis={"range": [0, ins_year_counts["count"].max() * 1.18]})
                    st.plotly_chart(style_plot(fig_iy, height=400), use_container_width=True)

                st.divider()

                # Powermap
                st.subheader("Даатгал Powermap")
                st.caption("Сонгосон байгуулллага (төв), холбогдсон хүн/этгээд (1-р тойрог), тэдгээрээр холбогдох бусад компаниуд (2-р тойрог).")
                render_frc_powermap(ins_scope, bank_edges_df, bank_company_df)

                st.divider()

                # Search table
                st.markdown('<div class="section-title">Байгуулллагын хайлт</div>', unsafe_allow_html=True)
                ins_search = st.text_input("Нэрээр хайх",
                    placeholder="Байгуулллагын нэр эсвэл бүртгэлийн дугаар...",
                    key="ins_entity_search")
                ins_table = ins_scope[["entity_name", "industry_names", "location",
                    "license_number", "license_date", "registration_number", "ceo", "address"]].copy()
                ins_table["license_date"] = ins_table["license_date"].dt.strftime("%Y-%m-%d")
                if ins_search:
                    ins_mask = (
                        ins_table["entity_name"].str.contains(ins_search, case=False, na=False)
                        | ins_table["registration_number"].astype(str).str.contains(ins_search, na=False)
                    )
                    ins_table = ins_table[ins_mask]
                ins_table.columns = ["Байгуулллага", "Үйл ажиллагаа", "Байршил",
                    "Лицензийн №", "Лиценз олгосон огноо", "Бүртгэлийн №", "CEO", "Хаяг"]
                st.caption(f"{len(ins_table)} байгуулллага")
                st.dataframe(ins_table, use_container_width=True, hide_index=True, height=460)


if __name__ == "__main__":
    main()
