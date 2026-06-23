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
    "TSLA", "GOOGL", "GOOG", "BRK-B", "JPM",
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
    df = yf.download(ticker, period="6mo", interval="1d", progress=False)
    if df.empty:
        return None

    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["RSI14"] = compute_rsi(df["Close"], 14)

    df["vol_sma20"] = df["Volume"].rolling(20).mean()
    df["RV20"] = df["Volume"] / df["vol_sma20"]

    df["gap"] = df["Open"] / df["Close"].shift(1) - 1
    df["oc_ret"] = (df["Close"] - df["Open"]) / df["Open"]

    df["range"] = (df["High"] - df["Low"]) / df["Open"]

    df["close_pos"] = (df["Close"] - df["Low"]) / (df["High"] - df["Low"])

    return df

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