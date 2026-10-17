import pandas as pd
import numpy as np
import yfinance as yf


# ---------- Data ----------
def fetch(symbol, interval, period):
    df = yf.download(symbol, interval=interval, period=period,
                     auto_adjust=True, progress=False)
    df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower()
                  for c in df.columns]
    return df[["open", "high", "low", "close"]].dropna()


def atr(df, n=14):
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - df["close"].shift()).abs(),
                    (df["low"] - df["close"].shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


# ---------- Market structure ----------
def swing_points(df, left=3, right=3):
    """Fractal swing highs and lows. Confirmed only after 'right' bars."""
    sh = pd.Series(False, index=df.index)
    sl = pd.Series(False, index=df.index)
    for i in range(left, len(df) - right):
        if df["high"].iloc[i] == df["high"].iloc[i - left:i + right + 1].max():
            sh.iloc[i] = True
        if df["low"].iloc[i] == df["low"].iloc[i - left:i + right + 1].min():
            sl.iloc[i] = True
    return sh, sl


def htf_bias(df):
    sh, sl = swing_points(df)
    highs = df["high"][sh].values[-2:]
    lows = df["low"][sl].values[-2:]
    if len(highs) < 2 or len(lows) < 2:
        return "neutral"
    if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
        return "bullish"
    if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
        return "bearish"
    return "neutral"


# ---------- SMC elements ----------
def liquidity_sweep(df, direction, lookback=20):
    """Last candle wicks beyond a recent swing and closes back inside."""
    last = df.iloc[-1]
    prior = df.iloc[-lookback - 1:-1]
    if direction == "long":
        return last["low"] < prior["low"].min() and last["close"] > prior["low"].min()
    return last["high"] > prior["high"].max() and last["close"] < prior["high"].max()

def structure_break(df, direction):
    """Close beyond the most recent swing in the trade direction (BOS or CHoCH)."""
    d = df.iloc[:-1]
    sh, sl = swing_points(d)
    if direction == "long":
        level = d["high"][sh].iloc[-1] if sh.any() else None
        return level is not None and df["close"].iloc[-1] > level
    level = d["low"][sl].iloc[-1] if sl.any() else None
    return level is not None and df["close"].iloc[-1] < level


def find_poi(df, direction, lookback=50):
    """Most recent order block or FVG in the trade direction."""
    a = atr(df)
    zones = []
    for i in range(2, len(df)):
        o, h, l, c = df.iloc[i][["open", "high", "low", "close"]]
        body = abs(c - o)
        atr_val = a.iloc[i]
        impulsive = (not np.isnan(atr_val)) and body > 1.5 * atr_val
        if direction == "long":
            if l > df["high"].iloc[i - 2]:  # bullish FVG
                zones.append(("FVG", df["high"].iloc[i - 2], l, i))
            if impulsive and c > o and df["close"].iloc[i - 1] < df["open"].iloc[i - 1]:
                zones.append(("OB", df["low"].iloc[i - 1], df["high"].iloc[i - 1], i))
        else:
            if h < df["low"].iloc[i - 2]:  # bearish FVG
                zones.append(("FVG", h, df["low"].iloc[i - 2], i))
            if impulsive and c < o and df["close"].iloc[i - 1] > df["open"].iloc[i - 1]:
                zones.append(("OB", df["low"].iloc[i - 1], df["high"].iloc[i - 1], i))
    recent = [z for z in zones if z[3] >= len(df) - lookback]
    return recent[-1] if recent else None


def price_action_trigger(df, direction):
    """Engulfing or pin bar on the latest closed candle."""
    p, c = df.iloc[-2], df.iloc[-1]
    rng = c["high"] - c["low"]
    if rng == 0:
        return None
    body = abs(c["close"] - c["open"])
    lower_wick = min(c["open"], c["close"]) - c["low"]
    upper_wick = c["high"] - max(c["open"], c["close"])
    if direction == "long":
        if (c["close"] > c["open"] and p["close"] < p["open"]
                and c["close"] > p["open"] and c["open"] < p["close"]):
            return "Bullish engulfing"
        if lower_wick > 2 * body and lower_wick > 0.6 * rng:
            return "Bullish pin bar"
    else:
        if (c["close"] < c["open"] and p["close"] > p["open"]
                and c["close"] < p["open"] and c["open"] > p["close"]):
            return "Bearish engulfing"
        if upper_wick > 2 * body and upper_wick > 0.6 * rng:
            return "Bearish pin bar"
    return None


# ---------- Full analysis ----------
def analyze(symbol, account=10000.0, risk_pct=1.0, min_rr=2.0):
    d1 = fetch(symbol, "1d", "2y")
    h1 = fetch(symbol, "1h", "60d")
    m15 = fetch(symbol, "15m", "30d")

    bias = htf_bias(d1)
    result = {"symbol": symbol, "htf_bias": bias, "signal": "NO TRADE",
              "checklist": {}, "reason": ""}
    if bias == "neutral":
        result["reason"] = "Daily structure is unclear. Stand aside."
        return result

    direction = "long" if bias == "bullish" else "short"
    sweep = liquidity_sweep(h1, direction)
    bos = structure_break(m15, direction)
    poi = find_poi(h1, direction)
    trigger = price_action_trigger(m15, direction)
    price = m15["close"].iloc[-1]

    result["price"] = round(float(price), 5)
    result["checklist"] = {
        "Liquidity sweep on 1H": bool(sweep),
        "Structure break on 15M": bool(bos),
        "POI found (OB or FVG)": poi is not None,
        "Price inside POI": False,
        "Price action trigger on 15M": trigger or "None",
    }
    if poi is None:
        result["reason"] = "No valid POI. Wait."
        return result

    _, low, high, _ = poi
    in_zone = low <= price <= high
    result["checklist"]["Price inside POI"] = bool(in_zone)

    if not (sweep and bos and in_zone and trigger):
        result["reason"] = "Setup incomplete. Wait for all confirmations."
        return result

    buffer = atr(m15).iloc[-1] * 0.2
    if direction == "long":
        entry, sl = high, low - buffer
        tp = h1["high"].iloc[-50:].max()
    else:
        entry, sl = low, high + buffer
        tp = h1["low"].iloc[-50:].min()

    risk_per_unit = abs(entry - sl)
    reward = abs(tp - entry)
    rr = reward / risk_per_unit if risk_per_unit else 0
    if rr < min_rr:
        result["reason"] = f"Risk-reward {rr:.2f} is below the minimum of {min_rr}. Skip."
        return result

    risk_amount = account * risk_pct / 100
    units = risk_amount / risk_per_unit

    result.update({
        "signal": "LONG" if direction == "long" else "SHORT",
        "entry": round(float(entry), 5),
        "stop_loss": round(float(sl), 5),
        "take_profit": round(float(tp), 5),
        "rr": round(float(rr), 2),
        "risk_amount": round(risk_amount, 2),
        "units": round(float(units), 4),
        "trigger": trigger,
        "poi_type": poi[0],
        "reason": "All confirmations aligned.",
    })
    return result
