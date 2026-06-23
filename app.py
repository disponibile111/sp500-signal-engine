import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="S&P500 Signal Engine", layout="wide")

# -----------------------------
# S&P500 LIST (semplificata per stabilità demo)
# (poi la estendiamo automaticamente)
# -----------------------------
TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META",
    "TSLA", "GOOGL", "GOOG", "JPM",
    "UNH", "XOM", "LLY", "V", "MA",
    "AVGO", "HD", "COST", "MRK", "ABBV"
]

# -----------------------------
# INDICATORI
# -----------------------------
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_data(ticker):

    try:

        df = yf.download(
            ticker,
            period="6mo",
            interval="1d",
            auto_adjust=True,
            progress=False
        )

        if df.empty:
            return None

        # elimina eventuale MultiIndex
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)

        df = df.rename(columns=str)

        close = pd.Series(df["Close"]).astype(float)
        open_ = pd.Series(df["Open"]).astype(float)
        high = pd.Series(df["High"]).astype(float)
        low = pd.Series(df["Low"]).astype(float)
        volume = pd.Series(df["Volume"]).astype(float)

        df["SMA20"] = close.rolling(20).mean()
        df["SMA50"] = close.rolling(50).mean()

        df["RSI14"] = compute_rsi(close)

        vol_sma20 = volume.rolling(20).mean()

        df["RV20"] = volume.div(vol_sma20)

        df["gap"] = open_.div(close.shift(1)).sub(1)

        df["oc_ret"] = close.sub(open_).div(open_)

        df["range"] = high.sub(low).div(open_)

        df["close_pos"] = close.sub(low).div(high.sub(low))

        return df

    except Exception as e:
        st.error(f"{ticker}: {e}")
        return None

# -----------------------------
# SCORE SEMPLICE VERSION 1
# -----------------------------
def score(df):
    last = df.iloc[-1]

    score = 0

    # trend
    if last["Close"] > last["SMA20"]:
        score += 1
    if last["SMA20"] > last["SMA50"]:
        score += 1

    # momentum
    if last["RSI14"] > 55:
        score += 1

    # volume
    if last["RV20"] > 1.2:
        score += 1

    # strength candle
    if last["oc_ret"] > 0:
        score += 1

    return score / 5  # 0-1

# -----------------------------
# APP
# -----------------------------
st.title("📊 S&P500 Hedge Fund Signal Engine (v1)")

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

# -----------------------------
# OUTPUT
# -----------------------------
res_df = pd.DataFrame(results)
res_df = res_df.sort_values("prediction", ascending=False)

st.subheader("🏆 Top Signals")
st.dataframe(res_df, use_container_width=True)

st.subheader("📈 Buy Signals Only")
st.dataframe(res_df[res_df["buy_signal"] == 1], use_container_width=True)