import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="S&P500 Signal Engine", layout="wide")

TICKERS = [
    "AAPL", "MSFT"
]

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=3600)
def get_data(ticker):
    try:
        df = yf.download(
            ticker,
            period="6mo",
            interval="1d",
            auto_adjust=True,
            progress=False
        )

        if df is None or df.empty:
            return None

        # Se yfinance restituisce MultiIndex, lo appiattiamo
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)

        df.columns = [str(c) for c in df.columns]

        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"{ticker}: colonne mancanti nei dati scaricati")
            return None

        close = df["Close"].astype(float)
        open_ = df["Open"].astype(float)
        high = df["High"].astype(float)
        low = df["Low"].astype(float)
        volume = df["Volume"].astype(float)

        df["SMA20"] = close.rolling(20).mean()
        df["SMA50"] = close.rolling(50).mean()
        df["RSI14"] = compute_rsi(close)

        vol_sma20 = volume.rolling(20).mean()
        df["RV20"] = volume / vol_sma20

        prev_close = close.shift(1)
        df["gap"] = (open_ / prev_close) - 1
        df["oc_ret"] = (close - open_) / open_
        df["range"] = (high - low) / open_

        hl_diff = (high - low).replace(0, np.nan)
        df["close_pos"] = (close - low) / hl_diff

        # pulizia finale minima
        df = df.replace([np.inf, -np.inf], np.nan)

        return df

    except Exception as e:
        st.error(f"{ticker}: {e}")
        return None

def score(df):
    last = df.iloc[-1]
    s = 0

    if last["Close"] > last["SMA20"]:
        s += 1
    if last["SMA20"] > last["SMA50"]:
        s += 1
    if last["RSI14"] > 55:
        s += 1
    if last["RV20"] > 1.2:
        s += 1
    if last["oc_ret"] > 0:
        s += 1

    return s / 5

st.title("📊 S&P500 Hedge Fund Signal Engine (v1)")
st.write("App started")

results = []

for t in TICKERS:
    df = get_data(t)
    if df is None or len(df) < 60:
        continue

    s = score(df)
    prediction = int(s * 100)

    results.append({
        "ticker": t,
        "prediction": prediction,
        "buy_signal": 1 if prediction >= 55 else 0
    })

if results:
    res_df = pd.DataFrame(results).sort_values("prediction", ascending=False)

    st.subheader("🏆 Top Signals")
    st.dataframe(res_df, use_container_width=True)

    st.subheader("📈 Buy Signals Only")
    st.dataframe(res_df[res_df["buy_signal"] == 1], use_container_width=True)
else:
    st.warning("Nessun dato disponibile o insufficiente per i ticker selezionati.")