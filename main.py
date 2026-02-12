from flask import Flask, jsonify
import requests
import pandas as pd
import ta
import time
import os
import threading
from datetime import datetime

app = Flask(__name__)

API_KEY = os.getenv("API_KEY")

PAIRS = {
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "AUDUSD": "AUDUSD"
}

signals = []  # stored signals


# -----------------------
# GET MARKET DATA
# -----------------------
def get_data(pair):
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "FX_INTRADAY",
        "from_symbol": pair[:3],
        "to_symbol": pair[3:],
        "interval": "1min",
        "apikey": API_KEY,
        "outputsize": "compact"
    }

    r = requests.get(url, params=params).json()
    key = "Time Series FX (1min)"
    if key not in r:
        print("AlphaVantage error:", r)
        return None

    df = pd.DataFrame.from_dict(r[key], orient="index").astype(float)
    df.columns = ["open", "high", "low", "close"]
    df = df.sort_index()
    return df


# -----------------------
# ANALYZE DATA
# -----------------------
def analyze(df):
    df["ema9"] = ta.trend.EMAIndicator(df["close"], 9).ema_indicator()
    df["ema21"] = ta.trend.EMAIndicator(df["close"], 21).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], 14).rsi()
    df["adx"] = ta.trend.ADXIndicator(
        df["high"], df["low"], df["close"], 14
    ).adx()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if (
        prev["ema9"] < prev["ema21"] and
        last["ema9"] > last["ema21"] and
        50 <= last["rsi"] <= 70 and
        last["adx"] > 20
    ):
        return "BUY"

    if (
        prev["ema9"] > prev["ema21"] and
        last["ema9"] < last["ema21"] and
        30 <= last["rsi"] <= 50 and
        last["adx"] > 20
    ):
        return "SELL"

    return None


# -----------------------
# BACKGROUND SIGNAL LOOP
# -----------------------
def generate_signal_loop():
    global signals

    while True:
        new_signals = []

        print("Checking market...")

        for name, pair in PAIRS.items():
            df = get_data(pair)
            if df is None or len(df) < 30:
                continue

            signal = analyze(df)
            if signal:
                new_signals.append({
                    "pair": name,
                    "signal": signal,
                    "expiry": "1 Minute",
                    "time": datetime.utcnow().strftime("%H:%M:%S")
                })

        signals = new_signals  # update stored signals
        print("Generated signals:", signals)

        time.sleep(60)


# Start background thread
threading.Thread(target=generate_signal_loop, daemon=True).start()


# -----------------------
# ROUTES
# -----------------------
@app.route("/signals")
def get_signals():
    return jsonify(signals)


@app.route("/")
def home():
    return "Pocket Option Signal Backend Running"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
