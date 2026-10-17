import streamlit as st
from analyzer import analyze

st.set_page_config(
    page_title="SMC Analyzer",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Mobile-focused styling: tighter padding, larger tap targets, readable text
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
        padding-bottom: 2rem;
    }
    h1 {font-size: 1.6rem !important;}
    h2, h3 {font-size: 1.2rem !important;}
    div[data-testid="stMetricValue"] {font-size: 1.3rem;}
    div[data-testid="stMetricLabel"] {font-size: 0.85rem;}
    .stButton > button {
        width: 100%;
        min-height: 3rem;
        font-size: 1.05rem;
        border-radius: 10px;
    }
    .stTextInput input, .stNumberInput input {
        min-height: 2.8rem;
        font-size: 1rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("SMC Market Analyzer")
st.caption("Top-down analysis, price action, and smart money concepts.")

# ---------- Inputs (on the main screen, not a sidebar) ----------
symbol = st.text_input("Symbol", value="EURUSD=X",
                       help="Examples: EURUSD=X, GC=F, BTC-USD, AAPL")

col1, col2 = st.columns(2)
with col1:
    account = st.number_input("Account size", min_value=100.0,
                              value=10000.0, step=100.0)
with col2:
    risk_pct = st.number_input("Risk %", min_value=0.1, max_value=10.0,
                               value=1.0, step=0.1)

min_rr = st.number_input("Minimum risk-reward", min_value=1.0,
                         max_value=10.0, value=2.0, step=0.5)

run = st.button("Analyze Market", type="primary")

# ---------- Results ----------
if run:
    if not symbol.strip():
        st.error("Please enter a symbol.")
    else:
        with st.spinner("Analyzing multiple timeframes..."):
            try:
                res = analyze(symbol.strip().upper(),
                              account=account,
                              risk_pct=risk_pct,
                              min_rr=min_rr)
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                st.stop()

        st.subheader(f"{res['symbol']}")

        signal = res.get("signal", "NO TRADE")
        if signal == "NO TRADE":
            st.warning(f"Signal: NO TRADE")
        else:
            st.success(f"Signal: {signal}")

        st.write(f"**Daily bias:** {res.get('htf_bias', 'n/a').title()}")
        if "price" in res:
            st.write(f"**Current price:** {res['price']}")
        st.info(res.get("reason", ""))

        if "checklist" in res and res["checklist"]:
            st.markdown("### Confirmation Checklist")
            for item, value in res["checklist"].items():
                if isinstance(value, bool):
                    icon = "Yes" if value else "No"
                else:
                    icon = value
                st.write(f"- **{item}:** {icon}")

        if signal != "NO TRADE":
            st.markdown("### Trade Plan")
            m1, m2 = st.columns(2)
            m1.metric("Entry", res["entry"])
            m2.metric("Stop Loss", res["stop_loss"])
            m3, m4 = st.columns(2)
            m3.metric("Take Profit", res["take_profit"])
            m4.metric("Risk:Reward", f"1:{res['rr']}")
            m5, m6 = st.columns(2)
            m5.metric("Risk Amount", f"{res['risk_amount']}")
            m6.metric("Position Size (units)", res["units"])

st.divider()
st.caption("For education only. This is not financial advice. "
           "Always backtest and never risk money you cannot afford to lose.")
