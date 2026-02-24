import streamlit as st
import pandas as pd
from tradingview_ta import TA_Handler, Interval
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="VN STOCK PRO SCANNER", layout="wide")

# ===== AUTO REFRESH 60 GIÂY =====
st_autorefresh(interval=60 * 1000, key="refresh")

st.title("🔥 VN STOCK PRO SCANNER (TradingView)")

# ===== LẤY DANH SÁCH TOÀN BỘ HOSE =====
@st.cache_data(ttl=3600)
def get_hose_symbols():
    # Danh sách phổ biến HOSE (có thể mở rộng)
    hose = [
        "VCB","BID","CTG","TCB","MBB","VPB",
        "HPG","HSG","NKG",
        "FPT","MWG","PNJ",
        "VNM","SAB","MSN",
        "SSI","VND","HCM",
        "GAS","PLX","POW",
        "BVH","VIC","VHM","VRE"
    ]
    return hose

stocks = get_hose_symbols()
stocks.append("VNINDEX")

# ===== CHỌN KHUNG THỜI GIAN =====
interval_option = st.selectbox(
    "Khung thời gian:",
    {
        "5 phút": Interval.INTERVAL_5_MINUTES,
        "15 phút": Interval.INTERVAL_15_MINUTES,
        "1 giờ": Interval.INTERVAL_1_HOUR,
        "1 ngày": Interval.INTERVAL_1_DAY,
    }
)

# ===== BỘ LỌC TÍN HIỆU =====
filter_signal = st.selectbox(
    "Lọc tín hiệu:",
    ["TẤT CẢ", "MUA", "BÁN"]
)

results = []
progress = st.progress(0)

for i, stock in enumerate(stocks):
    try:
        exchange = "HOSE"
        screener = "vietnam"

        if stock == "VNINDEX":
            exchange = "HOSE"
            screener = "vietnam"

        handler = TA_Handler(
            symbol=stock,
            screener=screener,
            exchange=exchange,
            interval=interval_option
        )

        analysis = handler.get_analysis()
        indicators = analysis.indicators

        price = indicators.get("close", None)
        volume = indicators.get("volume", None)
        rsi = indicators.get("RSI", None)
        ma20 = indicators.get("SMA20", None)
        macd = indicators.get("MACD.macd", None)
        signal = indicators.get("MACD.signal", None)

        # ===== LOGIC TÍN HIỆU =====
        signal_text = "GIỮ"

        if rsi and macd and signal:
            if rsi < 30 and macd > signal:
                signal_text = "MUA"
            elif rsi > 70 and macd < signal:
                signal_text = "BÁN"
            elif macd > signal:
                signal_text = "MUA"
            elif macd < signal:
                signal_text = "BÁN"

        results.append([
            stock, price, volume, rsi, ma20, macd, signal, signal_text
        ])

    except:
        results.append([stock, "-", "-", "-", "-", "-", "-", "-"])

    progress.progress((i + 1) / len(stocks))

df = pd.DataFrame(
    results,
    columns=["MÃ","GIÁ","KHỐI LƯỢNG","RSI","MA20","MACD","SIGNAL","TÍN HIỆU"]
)

# ===== ÁP DỤNG BỘ LỌC =====
if filter_signal != "TẤT CẢ":
    df = df[df["TÍN HIỆU"] == filter_signal]

st.dataframe(df, use_container_width=True)

st.success("🔄 Tự động cập nhật mỗi 60 giây")
