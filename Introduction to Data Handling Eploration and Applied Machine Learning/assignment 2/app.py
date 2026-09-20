from pathlib import Path
import time

import pandas as pd
import plotly.express as px
import streamlit as st


DATA_PATH = Path(__file__).parent / "PanelData_backend.xlsx"

st.set_page_config(page_title="Physical Accompainments", layout="wide")
st.title("Physical Accompainments: Social Sundhed")
st.caption("Physical accompainments at Social Sundhed from 2022 to the first half of 2026.")


@st.cache_data
def load_data():
    return pd.read_excel(DATA_PATH)


def smooth_metric(container, label, target, state_key):
    """Animate a cumulative accompainment total when the year changes."""
    placeholder = container.empty()
    previous = st.session_state.get(state_key, target)
    steps = 12
    for step in range(1, steps + 1):
        value = round(previous + (target - previous) * step / steps)
        placeholder.metric(label, f"{value:,}")
        time.sleep(0.025)
    st.session_state[state_key] = target


def make_chart(df, year, region, program):
    """Create a cumulative appointment chart for the selected controls."""
    selected = df[df["aar"].between(2022, year)].copy()
    if region != "Denmark Total":
        selected = selected[
            selected["Gruppe"]
            == {"Jutland": "Jylland", "Rest of Denmark": "Resten af Danmark"}[region]
        ]
    if program != "All program types":
        selected = selected[selected["Programtype"] == program]
    selected["Sektor"] = selected["Sektoransvar_udledt"].str.extract(
        r"^(Region|Kommune)", expand=False
    )
    counts = (
        selected.groupby("Sektor", as_index=False)
        .size()
        .rename(columns={"size": "appointments"})
    )
    counts["Sektor"] = counts["Sektor"].map(
        {"Region": "Health Sector", "Kommune": "Local government sector"}
    )
    counts["Sektor"] = pd.Categorical(
        counts["Sektor"],
        categories=["Health Sector", "Local government sector"],
        ordered=True,
    )
    counts = counts.sort_values("Sektor")
    figure = px.bar(
        counts,
        x="Sektor",
        y="appointments",
        text="appointments",
        color="Sektor",
        color_discrete_map={"Region": "#e8751a", "Kommune": "#163a5f"},
        title=(
            f"Confirmed physical accompainments, 2022-{year}"
            f" | {region} | {program}"
        ),
        labels={"Sektor": "Sector", "appointments": "Accompainments"},
    )
    figure.update_traces(texttemplate="%{text:,}", textposition="outside")
    figure.update_layout(
        height=430,
        showlegend=False,
        margin=dict(l=20, r=20, t=60, b=20),
        transition=dict(duration=500, easing="cubic-in-out"),
    )
    return figure, counts


df = load_data()
year = st.slider(
    "Accumulate accompainments through year",
    min_value=2022,
    max_value=2026,
    value=2022,
    step=1,
)

chart_column, control_column = st.columns([3, 1], gap="large")
with control_column:
    st.subheader("Select part of Denmark and type of program")
    region = st.radio(
        "Part of Denmark",
        options=["Jutland", "Rest of Denmark", "Denmark Total"],
        index=2,
    )
    program = st.radio(
        "Type of Program",
        options=["All program types", "SBB", "FBB", "SOB"],
        index=0,
    )

figure, counts = make_chart(df, year, region, program)

col1, col2, col3 = chart_column.columns(3)
col1.metric("Accumulated through", year)
total_appointments = int(counts["appointments"].sum())
selected_region_view = df[df["aar"].between(2022, year)]
if region != "Denmark Total":
    selected_region_view = selected_region_view[
        selected_region_view["Gruppe"] == {
            "Jutland": "Jylland",
            "Rest of Denmark": "Resten af Danmark",
        }[region]
    ]
if program != "All program types":
    selected_region_view = selected_region_view[
        selected_region_view["Programtype"] == program
    ]
selected_region_appointments = len(selected_region_view)
smooth_metric(col2, "Accompainments", total_appointments, "total_accompainments")
smooth_metric(
    col3,
    "Accompainments in selected area",
    selected_region_appointments,
    "selected_region_appointments",
)

with chart_column:
    st.plotly_chart(figure, use_container_width=True)
