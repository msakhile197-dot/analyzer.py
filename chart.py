import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from analyzer import fetch, find_poi


@st.cache_data(ttl=300)
def load_h1(symbol):
    return fetch(symbol, "1h", "60d")


def liquidity_level(h1, direction, lookback=20):
    """Recent swing that price must sweep before the setup can progress."""
    prior = h1.iloc[-lookback - 1:-1]
    if direction == "long":
        return float(prior["low"].min())
    return float(prior["high"].max())


def scenario_steps(cl, direction):
    """Build the step tracker and find the current stage (0 to 4)."""
    long_ = direction == "long"
    trig = cl["Price action trigger on 15M"]
    checks = [
        ("1H liquidity sweep", cl["Liquidity sweep on 1H"],
         "Wait for price to wick past the recent {} and close back inside.".format(
             "low" if long_ else "high")),
        ("15M structure break", cl["Structure break on 15M"],
         "Wait for a 15M candle to close beyond the latest swing {}.".format(
             "high" if long_ else "low")),
        ("Price inside POI", cl["Price inside POI"],
         "Wait for price to pull back into the highlighted zone."),
        ("Price action trigger", trig != "None",
         "Wait for an engulfing candle or pin bar in the trade direction, inside the zone."),
    ]
    steps = [("Daily bias", True, "Trade only {} setups".format("buy" if long_ else "sell"))]
    stage = 4
    for i, (name, done, text) in enumerate(checks):
        steps.append((name, done, text))
        if not done and stage == 4:
            stage = i
    return steps, stage


EXPECT = {
    0: "Do not enter yet. Expect price to {} the recent {} first (a liquidity sweep). "
       "Once it wicks through and closes back inside, the setup can progress.",
    1: "The sweep is done. Expect a 15M close that breaks the latest swing in the trade "
       "direction. Still no entry.",
    2: "Structure has shifted. Expect price to pull back into the highlighted POI zone. "
       "Do not chase price away from the zone.",
    3: "Price is inside the zone. Expect a confirmation candle. Enter only after it closes.",
    4: "All conditions are aligned. Review the signal, then place the order using the "
       "calculated position size.",
}


def build_chart(h1, poi, liq, price, entry=None, sl=None, tp=None):
    df = h1.iloc[-80:]
    fig = go.Figure(go.Candlestick(
        x
