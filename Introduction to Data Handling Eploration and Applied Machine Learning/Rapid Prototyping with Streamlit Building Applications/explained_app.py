# ------------------------------------------------------------
# 1) Import the libraries we need
# ------------------------------------------------------------
# import time
#   Gives us access to time-related functions.
#   We use it to simulate a slow data source in the built-in dataset mode.
#
# import pandas as pd
#   pandas gives us tables, filtering, grouping, and date handling.
#   We use it for the stock data, filtering, rebase calculation, and export.
#
# import plotly.express as px
#   Plotly Express creates charts quickly and cleanly.
#   We use it to draw the stock comparison line chart.
#
# import requests
#   requests lets Python contact a web API.
#   We use it to fetch live prices from Alpha Vantage when an API key is present.
#
# import streamlit as st
#   streamlit is the framework that builds the web app UI.
#   It creates the title, widgets, metrics, chart, and buttons.
import time

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

# ------------------------------------------------------------
# 2) App setup
# ------------------------------------------------------------
# This sets the browser tab title and makes the layout wider.
st.set_page_config(page_title="Watchlist Explorer", layout="wide")

# These lines create the title and subtitle text at the top of the page.
st.title("Watchlist Explorer")
st.caption("Six tech stocks, weekly, 2018-2019. Indexed to 1.00 on 2018-01-01.")

# Read the optional API key without crashing when secrets.toml does not exist.
def get_api_key():
    try:
        return st.secrets["ALPHAVANTAGE_API_KEY"]
    except (KeyError, StreamlitSecretNotFoundError):
        return None

# ------------------------------------------------------------
# 3) Load the data once, not on every click
# ------------------------------------------------------------
# Streamlit reruns the script whenever a widget changes.
# The @st.cache_data decorator stops us from reloading data every rerun.

# Built-in dataset version.
@st.cache_data
def load_builtin_data():
    # time.sleep(2) is only here to show why caching matters.
    time.sleep(2)

    # px.data.stocks() gives us Plotly's sample stock dataset.
    wide = px.data.stocks()

    # Convert the date column into a real datetime value.
    wide["date"] = pd.to_datetime(wide["date"])

    # Convert the table from wide format to long format.
    # Each row becomes one ticker/date/price observation.
    long = wide.melt(id_vars="date", var_name="ticker", value_name="price")

    # Return the data sorted by ticker and date.
    return long.sort_values(["ticker", "date"])


# Live-data version from Alpha Vantage.
@st.cache_data(ttl=3600)
def load_prices(symbol):
    # requests.get fetches the stock data from the API.
    r = requests.get(
        "https://www.alphavantage.co/query",
        params={
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": get_api_key(),
            "outputsize": "compact",
        },
        timeout=10,
    )
    payload = r.json()
    series = payload.get("Time Series (Daily)")

    # If the API response is missing or blocked, raise a clear error.
    if series is None:
        raise RuntimeError(
            payload.get("Information") or payload.get("Note") or "Unexpected response"
        )

    # The API response is nested JSON, so we reshape it into a table.
    out = (
        pd.DataFrame(series)
        .T.rename(columns={"4. close": "price"})[["price"]]
        .astype(float)
        .rename_axis("date")
        .reset_index()
    )
    out["date"] = pd.to_datetime(out["date"])
    out["ticker"] = symbol
    return out.sort_values("date")


# Wrapper that picks either the built-in data or live API data.
@st.cache_data(ttl=3600)
def load_data(symbols=("AAPL", "MSFT", "IBM")):
    # If the API key is not configured, use the built-in dataset instead.
    if get_api_key() is None:
        return load_builtin_data()

    # Otherwise, fetch and combine the selected stock symbols.
    return pd.concat([load_prices(s) for s in symbols], ignore_index=True)


# This runs once at the start and stores the data in memory.
df = load_data(symbols=("AAPL", "MSFT", "IBM"))

# ------------------------------------------------------------
# 4) Sidebar controls
# ------------------------------------------------------------
with st.sidebar:
    st.header("Controls")

    # st.multiselect lets the user choose one or more tickers.
    tickers = st.multiselect(
        "Tickers",
        options=sorted(df["ticker"].unique()),
        default=["AAPL", "MSFT", "AMZN"] if "AMZN" in df["ticker"].unique() else list(df["ticker"].unique())[:3],
    )

    # st.slider creates a date range selector.
    start, end = st.slider(
        "Date range",
        min_value=df["date"].min().date(),
        max_value=df["date"].max().date(),
        value=(df["date"].min().date(), df["date"].max().date()),
    )

    # st.checkbox toggles whether the chart is rebased to 100.
    rebase = st.checkbox("Rebase to 100 at window start", value=True)

# ------------------------------------------------------------
# 5) Filter the data based on the controls
# ------------------------------------------------------------
# Keep only rows that are in the selected ticker list and date range.
view = df[df["ticker"].isin(tickers) & df["date"].dt.date.between(start, end)].copy()

# If there are no tickers selected, stop early and show a helpful message.
if view.empty:
    st.info("Pick at least one ticker in the sidebar.")
    st.stop()

# ------------------------------------------------------------
# 6) Rebase the prices if needed
# ------------------------------------------------------------
# This makes each ticker start at 100 at the beginning of the visible window.
# It helps compare performance even if the starting prices were different.
if rebase:
    view["price"] = view.groupby("ticker")["price"].transform(
        lambda s: s / s.iloc[0] * 100
    )

# ------------------------------------------------------------
# 7) Compute performance metrics
# ------------------------------------------------------------
# Group by ticker and find the first and last price in the filtered window.
perf = view.groupby("ticker")["price"].agg(["first", "last"])

# Calculate percentage return for each ticker.
perf["return_%"] = (perf["last"] / perf["first"] - 1) * 100

# Best ticker is the one with the highest return.
best = perf["return_%"].idxmax()

# Show metric cards across 3 columns.
c1, c2, c3 = st.columns(3)
c1.metric("Tickers", len(tickers))
c2.metric("Weeks in window", view["date"].nunique())
c3.metric(f"Best: {best}", f"{perf.loc[best, 'return_%']:+.1f}%")

# ------------------------------------------------------------
# 8) Draw the chart
# ------------------------------------------------------------
# Create the stock comparison chart using Plotly Express.
fig = px.line(
    view,
    x="date",
    y="price",
    color="ticker",
    labels={
        "price": "Rebased (start = 100)" if rebase else "Index (2018-01-01 = 1.00)",
        "date": "",
    },
)
fig.update_layout(height=420, margin=dict(t=10, b=0), legend_title_text="")
st.plotly_chart(fig)

# ------------------------------------------------------------
# 9) Pinning views
# ------------------------------------------------------------
# st.session_state keeps values between reruns.
# This lets the user pin a selected view and keep it visible.
if "pinned" not in st.session_state:
    st.session_state.pinned = []

left, right, _ = st.columns([1, 1, 4])
if left.button("Pin this view"):
    st.session_state.pinned.append(
        {
            "tickers": ", ".join(tickers),
            "from": start,
            "to": end,
            "best": best,
            "return_%": round(float(perf.loc[best, "return_%"]), 1),
        }
    )
if right.button("Clear pins"):
    st.session_state.pinned = []

if st.session_state.pinned:
    st.subheader("Pinned views")
    st.dataframe(pd.DataFrame(st.session_state.pinned), hide_index=True)

# ------------------------------------------------------------
# 10) Download the filtered data
# ------------------------------------------------------------
# This gives the user a CSV export of the visible filtered data.
st.download_button(
    "Download filtered data (CSV)",
    data=view.to_csv(index=False).encode("utf-8"),
    file_name="watchlist.csv",
    mime="text/csv",
)
