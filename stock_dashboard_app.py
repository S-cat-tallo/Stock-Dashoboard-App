# stock_dashboard_app.py

import streamlit as st
import pandas as pd
import requests
import yfinance as yf
from finvizfinance.screener.overview import Overview

# ------------------------- CONFIG -------------------------
st.set_page_config(page_title="Stock Terminal", layout="wide", initial_sidebar_state="expanded")
st.title("📈 Custom Stock Watchlist Terminal")

st.markdown("""
<style>
    .stApp { background-color: #0c0f11; color: #d1d1d1; }
    .css-1d391kg, .css-1v0mbdj p { color: #33ff33; font-family: monospace; font-size: 16px; }
    .stDataFrame { background-color: #1e1e1e; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ------------------------- USER FILTERS -------------------------
sector_map = {
    "All": None,
    "Basic Materials": "Basic Materials",
    "Communication Services": "Communication Services",
    "Consumer Cyclical": "Consumer Cyclical",
    "Consumer Defensive": "Consumer Defensive",
    "Energy": "Energy",
    "Financial": "Financial",
    "Healthcare": "Healthcare",
    "Industrials": "Industrials",
    "Real Estate": "Real Estate",
    "Technology": "Technology",
    "Utilities": "Utilities"
}
selected_sector_label = st.selectbox("Select Sector", list(sector_map.keys()))
selected_sector_key = sector_map[selected_sector_label]

adr_threshold = st.slider("Min ADR % (Average Daily Range % over 20 days)", 0.0, 30.0, 5.0, step=0.5)

# ------------------------- FETCH DATA -------------------------
@st.cache_data(show_spinner=True)
def get_finviz_data(sector_filter):
    try:
        screener = Overview()
        filters = {}
        if sector_filter:
            filters['Sector'] = sector_filter
        screener.set_filter(filters_dict=filters)
        df = screener.screener_view()
        return df
    except Exception as e:
        st.error(f"Failed to fetch Finviz data: {e}")
        return pd.DataFrame()

raw_data = get_finviz_data(selected_sector_key)

# Exit early if Finviz fetch fails
if raw_data.empty:
    st.stop()

# ------------------------- FETCH HISTORICAL METRICS -------------------------
def calculate_atr_adr_dollarvol(symbol):
    try:
        data = yf.download(symbol, period="1mo", interval="1d")
        if len(data) < 20:
            return None, None, None
        data['High-Low'] = data['High'] - data['Low']
        atr = data['High-Low'].rolling(window=20).mean().iloc[-1]
        adr_pct = ((data['High-Low'] / data['Close']).rolling(window=20).mean() * 100).iloc[-1]
        avg_dollar_vol = (data['Close'] * data['Volume']).rolling(window=20).mean().iloc[-1]
        return round(adr_pct, 2), round(atr, 2), round(avg_dollar_vol, 2)
    except Exception:
        return None, None, None

# ------------------------- PROCESS DATA -------------------------
def clean_data(df):
    df = df.rename(columns={
        'Ticker': 'Symbol',
        'Price': 'Price',
        'Market Cap': 'MarketCap',
        'Float': 'Float',
        'Industry': 'Industry'
    })
    df['Finviz Link'] = df['Symbol'].apply(lambda x: f"https://finviz.com/quote.ashx?t={x}")
    adr_list, atr_list, adv_list = [], [], []
    for sym in df['Symbol']:
        adr, atr, adv = calculate_atr_adr_dollarvol(sym)
        adr_list.append(adr)
        atr_list.append(atr)
        adv_list.append(adv)
    df['ADR%'] = adr_list
    df['ATR'] = atr_list
    df['AvgDollarVolume'] = adv_list
    df = df.dropna(subset=['ADR%', 'ATR', 'AvgDollarVolume'])
    df = df[df['ADR%'] >= adr_threshold]
    display_cols = ['Symbol', 'Price', 'AvgDollarVolume', 'ADR%', 'ATR', 'MarketCap', 'Float', 'Industry', 'Finviz Link']
    return df[display_cols]

clean_df = clean_data(raw_data)

# ------------------------- DISPLAY TABLE -------------------------
st.markdown("### Filtered Stock Table")
st.dataframe(clean_df, use_container_width=True)

# ------------------------- TICKER CHART POPUP -------------------------
st.markdown("---")
st.markdown("### 🔍 View Chart For a Ticker")
ticker_input = st.text_input("Enter a symbol (e.g. RGTI)", "RGTI")
if ticker_input:
    try:
        chart_url = f"https://finviz.com/chart.ashx?t={ticker_input}&ty=c&ta=1&p=d&s=l"
        st.image(chart_url, caption=f"FinViz chart for {ticker_input.upper()}", use_column_width=True)
        st.markdown(f"[View full FinViz page →](https://finviz.com/quote.ashx?t={ticker_input})")
    except:
        st.warning("Invalid ticker or chart not available.")

