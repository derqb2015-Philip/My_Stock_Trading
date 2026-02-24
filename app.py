import streamlit as st
import pandas as pd
import numpy as np
from vnstock import Vnstock
from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="VN STOCK MAX ENGINE", layout="wide")
st.title("🚀 VN STOCK MAX ENGINE 2026 (HOSE - MULTITHREAD)")

# ===============================
# REFRESH 3 PHÚT + CLEAR CACHE
# ===============================
REFRESH_INTERVAL = 180
refresh_count = st_autorefresh(interval=REFRESH_INTERVAL * 1000, key="refresh")

if refresh_count > 0:
    st.cache_data.clear()

# ===============================
# INIT VNSTOCK
# ===============================
vn = Vnstock()

# ===============================
# LẤY DANH SÁCH TOÀN HOSE
# ===============================
@st.cache_data(ttl=3600)
def get_all_hose_symbols():
    listing = vn.stock(symbol="VCB", source="VCI").listing.symbols_by_exchange()
    hose = listing[listing["exchange"] == "HOSE"]
    return hose["symbol"].tolist()

ALL_STOCKS = get_all_hose_symbols()
st.success(f"Tổng số mã HOSE: {len(ALL_STOCKS)}")

# ===============================
# LẤY DỮ LIỆU GIÁ
# ===============================
def get_price(symbol, start="2024-01-01", end="2026-12-31"):
    try:
        stock = vn.stock(symbol=symbol, source="VCI")
        df = stock.quote.history(start=start, end=end, interval="1D")
        return df
    except:
        return pd.DataFrame()

# ===============================
# CHỈ BÁO
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
# BACKTEST
# ===============================
def backtest_strategy(df):

    if df.empty:
        return None

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

        if position == 0:
            if rsi.iloc[i] < 30 and macd.iloc[i] > signal.iloc[i]:
                position = 1
                entry_price = close.iloc[i]

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
# XỬ LÝ MỘT MÃ (ĐA LUỒNG)
# ===============================
def process_symbol(symbol):

    df = get_price(symbol, start="2024-01-01")
    if df.empty or len(df) < 50:
        return None

    close = df["close"]
    volume = df["volume"]

    avg_volume = volume.tail(30).mean()
    price = close.iloc[-1]
    avg_value = avg_volume * price

    # Chỉ báo
    rsi_series = calculate_rsi(close)
    macd, signal = calculate_macd(close)

    rsi = rsi_series.iloc[-1]
    ma20 = close.rolling(20).mean().iloc[-1]
    macd_value = macd.iloc[-1]
    signal_value = signal.iloc[-1]

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
        symbol,
        price,
        avg_volume,
        avg_value,
        round(rsi,2),
        round(ma20,2),
        round(macd_value,2),
        round(signal_value,2),
        signal_text
    ]

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

with st.spinner("Đang quét toàn bộ HOSE..."):
    data = scan_all_symbols(ALL_STOCKS)


st.subheader("🔎 Bộ lọc nâng cao")

min_volume = st.number_input("Thanh khoản TB tối thiểu:", value=1000000)
min_value = st.number_input("Giá trị giao dịch TB tối thiểu:", value=500000000)
top_n = st.number_input("Giới hạn số mã (Top N thanh khoản):", value=200)

# Lọc thanh khoản
df = df[df["VOL_TB_30"] >= min_volume]

# Lọc giá trị giao dịch
df = df[df["GIÁ_TRỊ_TB_30"] >= min_value]

# Sắp xếp theo thanh khoản giảm dần
df = df.sort_values("VOL_TB_30", ascending=False)

# Giới hạn Top N
df = df.head(top_n)


df = pd.DataFrame(
    data,
    columns=[
        "MÃ","GIÁ",
        "VOL_TB_30","GIÁ_TRỊ_TB_30",
        "RSI","MA20","MACD","SIGNAL","TÍN HIỆU"
    ]
)

filter_signal = st.selectbox(
    "Lọc tín hiệu:",
    ["TẤT CẢ", "MUA", "BÁN"]
)

if filter_signal != "TẤT CẢ":
    df = df[df["TÍN HIỆU"] == filter_signal]

st.dataframe(df, use_container_width=True)

# ===============================
# BACKTEST UI
# ===============================
st.subheader("📊 Backtest chiến lược")

symbol_bt = st.selectbox("Chọn mã để backtest:", ALL_STOCKS)

if st.button("Chạy Backtest"):

    df_bt = get_price(symbol_bt, start="2022-01-01")

    result = backtest_strategy(df_bt)

    if result:

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Tổng lợi nhuận (%)", result["Total Return (%)"])
        col2.metric("Winrate (%)", result["Win Rate (%)"])
        col3.metric("Max Drawdown (%)", result["Max Drawdown (%)"])
        col4.metric("Số lệnh", result["Number of Trades"])

        st.line_chart(result["Equity Curve"])
