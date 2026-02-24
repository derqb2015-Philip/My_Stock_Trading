import streamlit as st
import pandas as pd
import numpy as np
from vnstock import Vnstock
from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="VN STOCK MAX ENGINE", layout="wide")
st.title("🚀 VN STOCK MAX ENGINE (400 HOSE - MULTITHREAD)")

# ===============================
# REFRESH 3 PHÚT + CLEAR CACHE
# ===============================
REFRESH_INTERVAL = 180
refresh_count = st_autorefresh(interval=REFRESH_INTERVAL * 1000, key="refresh")

if refresh_count > 0:
    st.cache_data.clear()

# ===============================
# LẤY DANH SÁCH TOÀN HOSE
# ===============================
@st.cache_data(ttl=3600)
def get_all_hose_symbols():

    vn = Vnstock().stock(symbol="VCB", source="VCI")
    listing = vn.listing.symbols_by_exchange()

    hose = listing[listing["exchange"] == "HOSE"]
    return hose["symbol"].tolist()

ALL_STOCKS = get_all_hose_symbols()

st.success(f"Tổng số mã HOSE: {len(ALL_STOCKS)}")

# ===============================
# TÍNH TOÁN CHỈ BÁO
# ===============================
def calculate_rsi(data, period=14):
    delta = data.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(data):
    ema12 = data.ewm(span=12, adjust=False).mean()
    ema26 = data.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

# ===============================
# HÀM BACKTEST
# ===============================
def backtest_strategy(df):

    close = df["close"]
    rsi = calculate_rsi(close)
    macd, signal = calculate_macd(close)

    position = 0
    entry_price = 0
    trades = []
    equity = 1
    equity_curve = []

    for i in range(len(df)):

        if i < 30:
            equity_curve.append(equity)
            continue

        # Điều kiện MUA
        if position == 0:
            if rsi.iloc[i] < 30 and macd.iloc[i] > signal.iloc[i]:
                position = 1
                entry_price = close.iloc[i]

        # Điều kiện BÁN
        elif position == 1:
            if rsi.iloc[i] > 70 and macd.iloc[i] < signal.iloc[i]:
                exit_price = close.iloc[i]
                profit = (exit_price - entry_price) / entry_price
                trades.append(profit)
                equity *= (1 + profit)
                position = 0

        equity_curve.append(equity)

    total_return = (equity - 1) * 100
    winrate = (len([t for t in trades if t > 0]) / len(trades) * 100) if trades else 0

    # Max drawdown
    peak = pd.Series(equity_curve).cummax()
    drawdown = (pd.Series(equity_curve) - peak) / peak
    max_dd = drawdown.min() * 100

    return {
        "Total Return (%)": round(total_return,2),
        "Win Rate (%)": round(winrate,2),
        "Max Drawdown (%)": round(max_dd,2),
        "Number of Trades": len(trades),
        "Equity Curve": equity_curve
    }

# ===============================
# HÀM XỬ LÝ MỘT MÃ (CHẠY SONG SONG)
# ===============================
def process_symbol(symbol):
    try:
        df = stock_historical_data(
            symbol=symbol,
            start_date="2024-01-01",
            end_date="2026-12-31",
            resolution="1D",
            type="stock"
        )

        if df.empty:
            return None

        close = df["close"]
        rsi = calculate_rsi(close).iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        macd, signal = calculate_macd(close)

        macd_value = macd.iloc[-1]
        signal_value = signal.iloc[-1]

        price = close.iloc[-1]
        volume = df["volume"].iloc[-1]

        signal_text = "GIỮ"

        if rsi < 30 and macd_value > signal_value:
            signal_text = "MUA"
        elif rsi > 70 and macd_value < signal_value:
            signal_text = "BÁN"
        elif macd_value > signal_value:
            signal_text = "MUA"
        elif macd_value < signal_value:
            signal_text = "BÁN"

        return [
            symbol, price, volume,
            round(rsi,2),
            round(ma20,2),
            round(macd_value,2),
            round(signal_value,2),
            signal_text
        ]

    except:
        return None

# ===============================
# QUÉT ĐA LUỒNG
# ===============================
@st.cache_data(ttl=180)
def scan_all_symbols(symbols):

    results = []

    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(process_symbol, s) for s in symbols]

        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    return results


with st.spinner("Đang quét toàn bộ HOSE (đa luồng)..."):
    data = scan_all_symbols(ALL_STOCKS)

df = pd.DataFrame(
    data,
    columns=["MÃ","GIÁ","KHỐI LƯỢNG","RSI","MA20","MACD","SIGNAL","TÍN HIỆU"]
)

# ===============================
# BỘ LỌC
# ===============================
filter_signal = st.selectbox(
    "Lọc tín hiệu:",
    ["TẤT CẢ", "MUA", "BÁN"]
)

if filter_signal != "TẤT CẢ":
    df = df[df["TÍN HIỆU"] == filter_signal]

st.dataframe(df, use_container_width=True)

st.success("⚡ Đa luồng | ~30-40 giây | Refresh 3 phút | Clear cache trước refresh")

# ===============================
# THÊM GIAO DIỆN BACKTEST
# ===============================

st.subheader("📊 Backtest chiến lược")

symbol_bt = st.selectbox("Chọn mã để backtest:", ALL_STOCKS)

if st.button("Chạy Backtest"):

    df_bt = stock_historical_data(
        symbol=symbol_bt,
        start_date="2022-01-01",
        end_date="2026-12-31",
        resolution="1D",
        type="stock"
    )

    result = backtest_strategy(df_bt)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Tổng lợi nhuận (%)", result["Total Return (%)"])
    col2.metric("Winrate (%)", result["Win Rate (%)"])
    col3.metric("Max Drawdown (%)", result["Max Drawdown (%)"])
    col4.metric("Số lệnh", result["Number of Trades"])

    st.line_chart(result["Equity Curve"])

