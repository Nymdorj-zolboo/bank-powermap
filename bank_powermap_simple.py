from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(page_title="Банкны powermap", page_icon="B", layout="wide")

BASE_DIR = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
DATA_DIR = BASE_DIR / "gold_datamart"


BRAND_BLUE = "#4895fc"
BRAND_NAVY = "#1c3c65"
BRAND_DEEP_BLUE = "#004095"
BRAND_SLATE = "#2e3b44"
BRAND_ICE = "#f2f8ff"


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
            padding: 1.1rem 1.25rem;
            margin-bottom: .95rem;
            box-shadow: 0 20px 36px rgba(0,0,0,.40);
        }
        .hero h1 { margin: 0 0 .2rem 0; font-size: 1.75rem; color: #f2f8ff !important; }
        .hero p { margin: .1rem 0; color: #f2f8ff !important; }
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
        hr { border-color: rgba(72,149,252,.18) !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def style_plot(fig: go.Figure, height: int | None = None) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="#0d1b2a",
        plot_bgcolor="#111d2e",
        font=dict(color="#c8dff8", size=12),
        title_font=dict(color="#edf5ff", size=17),
        legend=dict(orientation="h", bgcolor="rgba(11,18,32,.88)", bordercolor="rgba(72,149,252,.22)", borderwidth=1, font=dict(color="#c8dff8")),
        hoverlabel=dict(bgcolor="#111d2b", font=dict(color="#eaf2ff")),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    fig.update_xaxes(gridcolor="rgba(143,193,255,.10)", linecolor="rgba(72,149,252,.20)", showline=True, tickfont=dict(color="#c8dff8"), title_font=dict(color="#c8dff8"))
    fig.update_yaxes(gridcolor="rgba(143,193,255,.10)", linecolor="rgba(72,149,252,.20)", showline=True, tickfont=dict(color="#c8dff8"), title_font=dict(color="#c8dff8"))
    if height is not None:
        fig.update_layout(height=height)
    return fig


def style_powermap_dark(fig: go.Figure, height: int = 720) -> go.Figure:
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


@st.cache_data(show_spinner=False)
def load_csv_outputs(data_dir: Path) -> dict[str, pd.DataFrame]:
    files = {
        "dim_bank": "dim_bank_official.csv",
        "by_bank": "bank_branch_units_latest.csv",
        "fact_map": "bank_branch_units_fact_map_latest.csv",
        "clean_market": "clean_bank_market.csv",
        "matching_report": "bank_matching_report.csv",
    }
    missing = [file for file in files.values() if not (data_dir / file).exists()]
    if missing:
        raise FileNotFoundError("Эхлээд pipeline ажиллуулна уу: python build_clean_bank_market.py")

    data = {key: pd.read_csv(data_dir / file, low_memory=False) for key, file in files.items()}
    for key in ("dim_bank", "by_bank", "fact_map", "matching_report"):
        if "register" in data[key].columns:
            data[key]["register"] = data[key]["register"].astype(str)
    return data


@st.cache_data(show_spinner=False)
def load_edges(data_dir: Path) -> pd.DataFrame:
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
    cols = [
        "register",
        "company_name",
        "company_name_market",
        "company_name_main",
        "aimag",
        "network_intensity_score",
    ]
    company = pd.read_csv(data_dir / "powermap_company_master.csv", usecols=cols, low_memory=False)
    company["register"] = company["register"].astype(str)
    company["company_label"] = (
        company["company_name"].fillna(company["company_name_market"]).fillna(company["company_name_main"]).fillna(company["register"])
    )
    return company


def render_map(fact_map: pd.DataFrame) -> None:
    view = fact_map.copy()
    view["known_unit_count_for_map"] = pd.to_numeric(view["known_unit_count_for_map"], errors="coerce").fillna(0)
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
    fig.update_layout(mapbox_style="carto-positron", margin=dict(l=0, r=0, t=0, b=0), legend_title_text="Банк")
    st.plotly_chart(fig, use_container_width=True)


def render_bank_units(by_bank: pd.DataFrame) -> None:
    view = by_bank.copy()
    unit_long = view.melt(
        id_vars=["bank_name_mn"],
        value_vars=["branch_count", "settlement_center_count", "fx_unit_count", "representative_office_count", "other_unit_count"],
        var_name="unit_type",
        value_name="unit_count",
    )
    unit_labels = {
        "branch_count": "Салбар",
        "settlement_center_count": "Тооцооны төв",
        "fx_unit_count": "Валютын нэгж",
        "representative_office_count": "Төлөөлөгчийн газар",
        "other_unit_count": "Бусад",
    }
    unit_long["unit_type"] = unit_long["unit_type"].map(unit_labels)
    display_cols = [
        "bank_name_mn",
        "bank_name_en",
        "short_name",
        "branch_count",
        "settlement_center_count",
        "fx_unit_count",
        "representative_office_count",
        "other_unit_count",
        "total_unit_count",
    ]
    fig = px.bar(
        unit_long.merge(view[["bank_name_mn", "total_unit_count"]], on="bank_name_mn", how="left").sort_values("total_unit_count"),
        x="unit_count",
        y="bank_name_mn",
        color="unit_type",
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
    matched = matching_report[matching_report["bank_id"].notna()].copy()
    if selected_banks:
        matched = matched[matched["bank_name_mn"].isin(selected_banks)].copy()
    matched["register"] = matched["register"].astype(str)
    edges = edges.copy()
    edges["source_company_register"] = edges["source_company_register"].astype(str)
    company = company.copy()
    company["register"] = company["register"].astype(str)

    bank_edges = edges[edges["source_company_register"].isin(set(matched["register"]))].copy()
    bank_edges = bank_edges.merge(
        matched[["register", "bank_name_mn", "short_name"]].rename(columns={"register": "source_company_register"}),
        on="source_company_register",
        how="left",
    )
    bank_edges = bank_edges[bank_edges["relation_type"].isin(["representative", "shareholder", "ultimate_owner"])].copy()
    aggregate_party = bank_edges["target_party_name"].fillna("").str.upper().str.contains("НИЙТ|ОЛОН НИЙТ")
    aggregate_key = bank_edges["target_party_key"].fillna("").str.upper().str.contains("PARTY::::НИЙТ|TOTAL")
    bank_edges = bank_edges[~aggregate_party & ~aggregate_key].copy()

    people_rank = (
        bank_edges.groupby(["target_party_key", "target_party_name"], as_index=False)
        .agg(bank_links=("source_company_register", "nunique"), relation_rows=("target_party_key", "size"))
        .sort_values(["bank_links", "relation_rows"], ascending=False)
        .head(max_people)
    )
    selected_people = set(people_rank["target_party_key"])
    bank_people_edges = bank_edges[bank_edges["target_party_key"].isin(selected_people)].copy()

    other_edges = edges[
        edges["target_party_key"].isin(selected_people)
        & ~edges["source_company_register"].isin(set(matched["register"]))
    ].copy()
    other_edges = other_edges.merge(
        company[["register", "company_label", "aimag", "network_intensity_score"]].rename(columns={"register": "source_company_register"}),
        on="source_company_register",
        how="left",
    )
    other_edges["company_rank"] = other_edges.groupby("target_party_key")["network_intensity_score"].rank(
        method="first", ascending=False
    )
    other_edges = other_edges[other_edges["company_rank"].le(max_companies_per_person)].copy()
    return bank_people_edges, other_edges, people_rank


def render_powermap_graph(selected_bank_name: str, bank_people_edges: pd.DataFrame, other_edges: pd.DataFrame) -> None:
    if bank_people_edges.empty:
        st.info("Холбоос олдсонгүй.")
        return

    def short_label(value: object, max_len: int = 22) -> str:
        text = str(value)
        return text if len(text) <= max_len else text[: max_len - 1] + "…"

    center_x, center_y = 0.5, 0.5
    fig = go.Figure()

    people = (
        bank_people_edges.groupby(["target_party_key", "target_party_name"], as_index=False)
        .agg(link_rows=("target_party_key", "size"), relation_types=("relation_type", lambda s: ", ".join(sorted(set(s.astype(str))))))
        .sort_values(["link_rows", "target_party_name"], ascending=[False, True])
        .reset_index(drop=True)
    )
    companies = (
        other_edges.groupby(["source_company_register", "company_label"], as_index=False)
        .agg(link_rows=("target_party_key", "size"), people_count=("target_party_key", "nunique"))
        .sort_values(["people_count", "link_rows", "company_label"], ascending=[False, False, True])
        .reset_index(drop=True)
    )

    def circle_positions(ids: list[str], radius: float, start_angle: float = -math.pi / 2) -> dict[str, tuple[float, float]]:
        total = max(len(ids), 1)
        return {
            node_id: (center_x + radius * math.cos(start_angle + 2 * math.pi * idx / total),
                      center_y + radius * math.sin(start_angle + 2 * math.pi * idx / total))
            for idx, node_id in enumerate(ids)
        }

    people_ids = people["target_party_key"].astype(str).tolist()
    company_ids = companies["source_company_register"].astype(str).tolist()
    people_pos = circle_positions(people_ids, 0.30)
    company_pos = circle_positions(company_ids, 0.52)

    # Edges: bank center → people (1st ring)
    relation_colors = {
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
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines",
            line=dict(color=relation_colors.get(relation_type, "rgba(180,190,205,.45)"), width=1.6),
            opacity=0.85, name=relation_type, hoverinfo="skip"))

    # Edges: people (1st ring) → other companies (2nd ring)
    xs, ys = [], []
    for row in other_edges.itertuples(index=False):
        person_id = str(row.target_party_key)
        company_id = str(row.source_company_register)
        if person_id not in people_pos or company_id not in company_pos:
            continue
        xs.extend([people_pos[person_id][0], company_pos[company_id][0], None])
        ys.extend([people_pos[person_id][1], company_pos[company_id][1], None])
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines",
        line=dict(color="rgba(143,193,255,.25)", width=0.9),
        name="хүн → бусад компани", hoverinfo="skip"))

    # Center node: selected bank
    fig.add_trace(go.Scatter(
        x=[center_x], y=[center_y],
        mode="markers+text",
        text=[short_label(selected_bank_name, 18)],
        textposition="bottom center",
        textfont=dict(size=12, color="#f2f8ff"),
        marker=dict(size=48, color="#004095", line=dict(color="#8fc1ff", width=3)),
        name="Сонгосон банк",
        hovertemplate=f"<b>{selected_bank_name}</b><extra></extra>",
    ))

    # 1st ring: people / entities
    fig.add_trace(go.Scatter(
        x=[people_pos[str(row.target_party_key)][0] for row in people.itertuples(index=False)],
        y=[people_pos[str(row.target_party_key)][1] for row in people.itertuples(index=False)],
        mode="markers+text",
        text=[short_label(row.target_party_name) for row in people.itertuples(index=False)],
        textposition="middle center",
        textfont=dict(size=10, color="#f2f8ff"),
        marker=dict(size=22, color="#4895fc", line=dict(color="#f2f8ff", width=2)),
        name="Хүн/этгээд",
        hovertemplate="<b>%{customdata[0]}</b><br>Холбооны төрөл: %{customdata[1]}<br>Link rows: %{customdata[2]}<extra></extra>",
        customdata=[[row.target_party_name, row.relation_types, int(row.link_rows)] for row in people.itertuples(index=False)],
    ))

    # 2nd ring: other companies
    if not companies.empty:
        fig.add_trace(go.Scatter(
            x=[company_pos[str(row.source_company_register)][0] for row in companies.itertuples(index=False)],
            y=[company_pos[str(row.source_company_register)][1] for row in companies.itertuples(index=False)],
            mode="markers+text",
            text=[short_label(row.company_label) for row in companies.itertuples(index=False)],
            textposition="middle center",
            textfont=dict(size=9, color="#c8dff8"),
            marker=dict(size=14, color="#2e3b44", line=dict(color="#8fc1ff", width=1.5)),
            name="Бусад компани",
            hovertemplate="<b>%{customdata[0]}</b><br>Холбогдсон хүн/этгээд: %{customdata[1]}<br>Link rows: %{customdata[2]}<extra></extra>",
            customdata=[[row.company_label, int(row.people_count), int(row.link_rows)] for row in companies.itertuples(index=False)],
        ))

    fig.update_xaxes(visible=False, range=[-0.08, 1.08], showgrid=False, zeroline=False)
    fig.update_yaxes(visible=False, range=[-0.08, 1.08], showgrid=False, zeroline=False)
    fig.update_layout(
        title=f"Radial powermap — {selected_bank_name}",
        height=740,
        margin=dict(l=0, r=0, t=55, b=0),
        showlegend=True,
        legend=dict(orientation="h"),
    )
    style_powermap_dark(fig, height=740)
    st.plotly_chart(fig, use_container_width=True)


def render_network(matching_report: pd.DataFrame, edges: pd.DataFrame, company: pd.DataFrame, selected_banks: list[str]) -> None:
    available = sorted(
        matching_report.loc[matching_report["bank_id"].notna(), "bank_name_mn"].dropna().unique().tolist()
    )
    powermap_options = [b for b in available if b in selected_banks] or available
    selected_bank = st.selectbox("Powermap-д харуулах банк", powermap_options, key="powermap_bank_select")

    bank_people_edges, other_edges, people_rank = build_bank_people_company_network(
        matching_report, edges, company, 18, 8, [selected_bank]
    )

    c1, c2 = st.columns(2)
    c1.metric("Хүн/этгээд", f"{people_rank['target_party_key'].nunique():,}")
    c2.metric("Холбогдсон бусад компани", f"{other_edges['source_company_register'].nunique():,}")

    render_powermap_graph(selected_bank, bank_people_edges, other_edges)


def main() -> None:
    inject_styles()
    st.markdown(
        """
        <div class="hero">
            <h1>Банкны powermap</h1>
            <p>Монголбанкны register-тэй салбар нэгжийн Excel болон компанийн холбоосын datamart дээр үндэслэв.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        data = load_csv_outputs(DATA_DIR)
    except FileNotFoundError as exc:
        st.error(str(exc))
        return

    dim_bank = data["dim_bank"]
    by_bank = data["by_bank"]
    fact_map = data["fact_map"]
    matching_report = data["matching_report"]
    edges = load_edges(DATA_DIR)
    company = load_company_master(DATA_DIR)

    with st.sidebar:
        st.header("Шүүлтүүр")
        banks = sorted(fact_map["bank_name_mn"].dropna().unique())
        regions = sorted(fact_map["region"].dropna().unique())
        selected_banks = st.multiselect(
            "Банк сонгох",
            banks,
            default=banks,
            help="Нэг эсвэл хэд хэдэн банк сонгоод газрын зураг, нэгж, powermap-ийг шүүнэ.",
        )
        selected_regions = st.multiselect("Бүс", regions, default=regions)
        if not selected_banks:
            selected_banks = banks
            st.info("Банк сонгоогүй тул бүх банк харуулж байна.")
        if not selected_regions:
            selected_regions = regions
            st.info("Бүс сонгоогүй тул бүх бүс харуулж байна.")
        st.caption(f"Сонгосон банк: {len(selected_banks)} / {len(banks)}")

    fact_filtered = fact_map[fact_map["bank_name_mn"].isin(selected_banks) & fact_map["region"].isin(selected_regions)].copy()
    bank_filtered = by_bank[by_bank["bank_name_mn"].isin(selected_banks)].copy()

    # ── Metric summary ──────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Банк", f"{dim_bank['bank_id'].nunique():,}")
    c2.metric("Салбар", f"{bank_filtered['branch_count'].sum():,.0f}")
    c3.metric("Тооцооны төв", f"{bank_filtered['settlement_center_count'].sum():,.0f}")
    c4.metric("Валютын нэгж", f"{bank_filtered['fx_unit_count'].sum():,.0f}")
    c5.metric("Нийт нэгж", f"{bank_filtered['total_unit_count'].sum():,.0f}")

    st.divider()

    # ── Газрын зураг ────────────────────────────────────────────────────────────
    st.subheader("Газрын зураг")
    render_map(fact_filtered)

    st.divider()

    # ── Банкны нэгж ─────────────────────────────────────────────────────────────
    st.subheader("Банкны нэгж")
    render_bank_units(bank_filtered)

    st.divider()

    # ── Удирдлага / эзэмшигч ────────────────────────────────────────────────────
    st.subheader("Удирдлага / эзэмшигч")
    st.caption("Зүүн талд банк, дунд талд тухайн банктай холбогдсон хүн/эзэмшигч, баруун талд тэр хүний бусад холбоотой компани харагдана.")
    render_network(matching_report, edges, company, selected_banks)



if __name__ == "__main__":
    main()
