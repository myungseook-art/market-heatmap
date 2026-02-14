import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🌍 개인용 멀티마켓 히트맵 – 풀옵션 버전")

# -------------------------
# 자동 새로고침
# -------------------------
st_autorefresh = st.sidebar.checkbox("자동 새로고침 (30초)", value=False)
if st_autorefresh:
    st.experimental_rerun()

# -------------------------
# 시장 선택
# -------------------------
market = st.sidebar.selectbox(
    "시장 선택",
    ["KOSPI", "KOSDAQ", "S&P500", "Nasdaq", "Dow", "ETF"]
)

period_option = st.sidebar.selectbox(
    "기간 선택",
    ["1d", "5d", "1mo"]
)

# -------------------------
# 시장별 종목 리스트
# -------------------------
markets = {
    "KOSPI": ["005930.KS","000660.KS","035420.KS","051910.KS"],
    "KOSDAQ": ["035720.KQ","086520.KQ"],
    "S&P500": ["AAPL","MSFT","NVDA","AMZN","GOOGL"],
    "Nasdaq": ["NVDA","AMD","META","TSLA"],
    "Dow": ["AAPL","MSFT","JPM","V"],
    "ETF": ["SPY","QQQ","DIA","ARKK","SOXL"]
}

symbols = markets[market]

# -------------------------
# ETF 구성 종목 자동 불러오기
# -------------------------
def get_etf_holdings(etf):
    try:
        data = yf.Ticker(etf).fund_holdings
        if data is not None and "Symbol" in data.columns:
            return data["Symbol"].head(20).tolist()
    except:
        pass
    return []

if market == "ETF":
    selected_etf = st.sidebar.selectbox("ETF 선택", symbols)
    symbols = get_etf_holdings(selected_etf)

# -------------------------
# 섹터 매핑
# -------------------------
sector_map = {
    "SPY": "ETF", "QQQ": "ETF", "DIA": "ETF",
    "ARKK": "ETF", "SOXL": "ETF"
}

# -------------------------
# 데이터 로딩
# -------------------------
@st.cache_data(ttl=300)
def load_data(symbols, period):
    result = []

    for symbol in symbols:
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period=period)

            # 데이터 없으면 스킵
            if hist is None or hist.empty or len(hist) < 2:
                continue

            price_now = hist["Close"].iloc[-1]
            price_old = hist["Close"].iloc[0]
            change_pct = (price_now - price_old) / price_old * 100

            info = stock.fast_info
            market_cap = info.get("market_cap", 1)

            sector = sector_map.get(symbol, "Unknown")

            result.append({
                "Symbol": symbol,
                "Price": round(price_now, 2),
                "Change (%)": round(change_pct, 2),
                "MarketCap": market_cap,
                "Sector": sector
            })
        except:
            pass

    return pd.DataFrame(result)

df = load_data(symbols, period_option)

if df.empty:
    st.warning("데이터를 불러오지 못했습니다.")
    st.stop()

# -------------------------
# 섹터 필터
# -------------------------
sector_filter = st.sidebar.multiselect(
    "섹터 필터",
    sorted(df["Sector"].unique()),
    default=sorted(df["Sector"].unique())
)

df = df[df["Sector"].isin(sector_filter)]

# -------------------------
# 정렬 옵션
# -------------------------
sort_option = st.sidebar.radio(
    "정렬 기준",
    ["변화율 높은 순", "변화율 낮은 순", "시가총액 큰 순"]
)

if sort_option == "변화율 높은 순":
    df = df.sort_values("Change (%)", ascending=False)
elif sort_option == "변화율 낮은 순":
    df = df.sort_values("Change (%)", ascending=True)
else:
    df = df.sort_values("MarketCap", ascending=False)

# -------------------------
# 히트맵
# -------------------------
fig = px.treemap(
    df,
    path=["Sector","Symbol"],
    values="MarketCap",
    color="Change (%)",
    hover_data=["Price","Change (%)"],
    color_continuous_scale=[
        [0.0, "#7f0000"],
        [0.25, "#ff4d4d"],
        [0.5, "#ffffff"],
        [0.75, "#66cc66"],
        [1.0, "#006400"]
    ],
    color_continuous_midpoint=0
)
fig.update_layout(margin=dict(t=30, l=5, r=5, b=5))
st.plotly_chart(fig, use_container_width=True)

# -------------------------
# 종목 검색
# -------------------------
search = st.text_input("🔍 종목 검색 (심볼 입력)")
if search:
    df = df[df["Symbol"].str.contains(search.upper())]

# -------------------------
# 종목 선택
# -------------------------
selected = st.selectbox("종목 선택", df["Symbol"])
st.dataframe(df[df["Symbol"] == selected], use_container_width=True)

# -------------------------
# 차트 (캔들 + 라인)
# -------------------------
st.subheader(f"📈 {selected} 차트")

stock = yf.Ticker(selected)
hist = stock.history(period="3mo")

tab1, tab2 = st.tabs(["캔들 차트", "라인 차트"])

with tab1:
    fig_candle = go.Figure(data=[
        go.Candlestick(
            x=hist.index,
            open=hist["Open"],
            high=hist["High"],
            low=hist["Low"],
            close=hist["Close"]
        )
    ])
    fig_candle.update_layout(height=500)
    st.plotly_chart(fig_candle, use_container_width=True)

with tab2:
    fig_line = px.line(hist, y="Close", title="종가 추세")
    st.plotly_chart(fig_line, use_container_width=True)