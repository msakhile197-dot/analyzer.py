import streamlit as st
from analyzer import analyze

st.set_page_config(page_title="SMC Analyzer", layout="centered",
                   initial_sidebar_state="collapsed")

# Mobile styling with bottom padding so the footer clears the Streamlit bar
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
        padding-bottom: 6rem;
    }
    h1 {font-size: 1.6rem !important;}
    h2, h3 {font-size: 1.2rem !important;}
    div[data-testid="stMetricValue"] {font-size: 1.3rem;}
    .stButton > button {
        width: 100%;
        min-height: 3rem;
        font-size: 1.05rem;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Readable names for Yahoo Finance tickers
SYMBOL_NAMES = {
    "EURUSD=X": "EUR/USD",
    "GBPUSD=X": "GBP/USD",
    "USDJPY=X": "USD/JPY",
    "AUDUSD=X": "AUD/USD",
    "USDCAD=X": "USD/CAD",
    "USDCHF=X": "USD/CHF",
    "NZDUSD=X": "NZD/USD",
    "XAUUSD=X": "XAU/USD (Gold)",
    "BTC-USD": "BTC/USD",
    "ETH-USD": "ETH/USD",
    "^GSPC": "S&P 500",
    "^NDX": "NASDAQ 100",
}

st.title("SMC Market Analyzer")
st.caption("Price action, top-down, and Smart Money Concepts")

symbol = st.text_input("Symbol (Yahoo Finance ticker)", value="EURUSD=X")
account = st.number_input("Account size ($)", min_value=100.0,
                          value=10000.0, step=100.0)
risk_pct = st.number_input("Risk per trade (%)", min_value=0.1,
                           max_value=5.0, value=1.0, step=0.1)
min_rr = st.number_input("Minimum risk-reward", min_value=1.0,
                         max_value=10.0, value=2.0, step=0.5)

if st.button("Analyze Market", type="primary"):
    with st.spinner("Reading the market..."):
        try:
            res = analyze(symbol, account, risk_pct, min_rr)
        except Exception as e:
            st.error(f"Could not analyze {symbol}: {e}")
            st.stop()

    name = SYMBOL_NAMES.get(res["symbol"], res["symbol"])
    st.subheader(name)

    signal = res["signal"]
    if signal == "NO TRADE":
        st.warning(f"Signal: {signal}")
    else:
        st.success(f"Signal: {signal}")

    st.metric("Daily bias", res["htf_bias"].capitalize())
    if "price" in res:
        st.metric("Current price", res["price"])

    st.markdown("#### Checklist")
    for item, value in res.get("checklist", {}).items():
        st.write(f"**{item}:** {value}")

    if res.get("reason"):
        st.info(res["reason"])

    if signal != "NO TRADE":
        st.markdown("#### Trade Plan")
        c1, c2 = st.columns(2)
        c1.metric("Entry", res["entry"])
        c2.metric("Stop loss", res["stop_loss"])
        c1.metric("Take profit", res["take_profit"])
        c2.metric("Risk-reward", res["rr"])
        st.metric("Risk amount ($)", res["risk_amount"])
        st.metric("Position size (units)", res["units"])

st.markdown("---")
st.caption("For education only. This is not financial advice. "
           "Always test on a demo account first.")
