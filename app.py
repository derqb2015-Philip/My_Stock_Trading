import streamlit as st
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from vnstock import Vnstock
import datetime

st.set_page_config(page_title="VN STOCK MAX ENGINE 2026", layout="wide")

st.title("🚀 VN STOCK MAX ENGINE 2026 (HOSE - MULTITHREAD)")

# =========================
# AUTO REFRESH 3 PHÚT
# =========================
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.datetime.now()

if (datetime.datetime.now() - st.session_state.last_refresh).seconds > 180:
    st.cache_data.clear()
    st.session_state.last_refresh = datetime.datetime.now()
    st.rerun()

# =========================
# CLEAR CACHE BUTTON
# =========================
if st.button("🔄 Refresh Now"):
    st.cache_data.clear()
    st.session_state.last_refresh = datetime.datetime.now()
    st.rerun()

# =========================
# LẤY DANH SÁCH HOSE
# =========================
@st.cache_data(ttl=3600)
def get_all_hose_symbols():
    vn = Vnstock().stock(symbol="VCB", source="VCI")
    listing = vn.listing.symbols_by_exchange()
    hose = listing[listing["exchange"] == "HOSE"]
    return hose["symbol"].tolist()

# =========================
# LẤY GIÁ
# =========================
@st.cache_data(ttl=600)
def get_price(symbol):
    try:
        vn = Vnstock().stock(symbol=symbol, source="VCI")
        df = vn.quote.history(start="2024-01-01", interval="1D")
        return df
    except:
        return pd.DataFrame()

# =========================
# RSI
# =========================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# =========================
# MACD
# =========================
def calculate_macd(series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

# =========================
# PROCESS SYMBOL (ALL-IN-ONE)
# =========================
def process_symbol(symbol):

    df = get_price(symbol)

    if df.empty or len(df) < 50:
        return None

    close = df["close"]
    
    if symbol == "VNINDEX":
    avg_volume = 0
    avg_value = 0
else:
    volume = df["volume"]
    avg_volume = volume.tail(30).mean()
    avg_value = avg_volume * price
    
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
        round(price,2),
        int(avg_volume),
        int(avg_value),
        round(rsi,2),
        round(ma20,2),
        round(macd_value,2),
        round(signal_value,2),
        signal_text
    ]

# =========================
# MULTITHREAD SCAN
# =========================
def scan_market(symbols, max_workers=20):

    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_symbol, s): s for s in symbols}

        for future in as_completed(futures):
            res = future.result()
            if res:
                results.append(res)

    return results

# =========================
# MAIN EXECUTION
# =========================
ALL_STOCKS = [
    "VCB","BID","CTG","TCB","MBB","VPB","ACB","STB","SHB",
    "HPG","HSG","NKG","FPT","MWG","PNJ","REE","GMD","VHC",
    "VNM","SAB","MSN","SSI","VND","HCM","GAS","PLX","POW",
    "BVH","VIC","VHM","VRE","DXG","DIG","KBC","PDR","NVL",
    "DPM","DCM","ANV","PVS","PVD","KDH","HDG","HDC","CSV",
    "CMG","BWE","SZC","TCH","IDC","VPI","BCM","CTR","CII",
    "HAG","HNG","NLG","KSB","GEX","VGC","MSB","OCB","TPB"
]

ALL_STOCKS.append("VNINDEX")

st.info(f"Số mã đang quét: {len(ALL_STOCKS)}")

if st.button("🚀 QUÉT TOÀN BỘ HOSE"):

    with st.spinner("Đang quét thị trường..."):

        data = scan_market(ALL_STOCKS, max_workers=20)

        df = pd.DataFrame(
            data,
            columns=[
                "MÃ","GIÁ",
                "VOL_TB_30","GIÁ_TRỊ_TB_30",
                "RSI","MA20","MACD","SIGNAL","TÍN HIỆU"
            ]
        )

        # =========================
        # BỘ LỌC NÂNG CAO
        # =========================
        st.subheader("🔎 Bộ lọc nâng cao")

        min_volume = st.number_input("Thanh khoản TB tối thiểu:", value=1000000)
        min_value = st.number_input("Giá trị giao dịch TB tối thiểu:", value=0)
        top_n = st.number_input("Top N thanh khoản:", value=200)

        df = df[df["VOL_TB_30"] >= min_volume]
        df = df[df["GIÁ_TRỊ_TB_30"] >= min_value]

        df = df.sort_values("VOL_TB_30", ascending=False).head(top_n)

        filter_signal = st.selectbox("Chỉ hiển thị tín hiệu:", ["TẤT CẢ","MUA","BÁN"])

        if filter_signal != "TẤT CẢ":
            df = df[df["TÍN HIỆU"] == filter_signal]

        st.success(f"Số mã sau lọc: {len(df)}")

        st.dataframe(df, use_container_width=True)

