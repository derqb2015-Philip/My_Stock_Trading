import streamlit as st
import subprocess
import threading
import time
from datetime import datetime

# ===== FILE VBS =====
VBS_FILE = r"C:\Users\manhpc\Downloads\New data FireAnt\Auto_download_data_vbs\auto_ami_cp68_last.vbs"

# ===== BIẾN ĐIỀU KHIỂN =====
if "running" not in st.session_state:
    st.session_state.running = False

if "logs" not in st.session_state:
    st.session_state.logs = []

# ===== HÀM CHẠY VBS =====
def run_vbs_loop():
    while st.session_state.running:
        try:
            subprocess.run(
                ["cscript", "//nologo", VBS_FILE],
                shell=True
            )

            log = f"✅ Chạy VBS: {datetime.now().strftime('%H:%M:%S')}"
            st.session_state.logs.insert(0, log)

        except Exception as e:
            st.session_state.logs.insert(0, f"❌ Lỗi: {e}")

        time.sleep(120)   # 2 phút

# ===== GIAO DIỆN =====
st.title("🚀 Auto Run VBS Every 2 Minutes")

col1, col2 = st.columns(2)

with col1:
    if st.button("▶ START"):
        if not st.session_state.running:
            st.session_state.running = True
            threading.Thread(target=run_vbs_loop, daemon=True).start()

with col2:
    if st.button("⛔ STOP"):
        st.session_state.running = False

# ===== HIỂN THỊ TRẠNG THÁI =====
status = "🟢 RUNNING" if st.session_state.running else "🔴 STOPPED"
st.subheader(status)

# ===== LOG =====
st.write("### Logs")

for log in st.session_state.logs[:20]:
    st.write(log)