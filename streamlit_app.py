import streamlit as st

st.title("🎈 Ứng dụng giới thiệu tuyến điểm du lịch Mice")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ============ CONFIG ============
st.set_page_config(page_title="Tuyến điểm MICE", layout="wide")

DATA_PATH = "Data/mice_tours.csv"

# Màu riêng cho từng tuyến
TOUR_COLORS = {
    "Tuyến 1": "#4285F4",   # xanh dương
    "Tuyến 2": "#34A853",   # xanh lá
    "Tuyến 3": "#FB8C00",   # cam
}

TOUR_TITLES = {
    "Day 1": "Tuyến 1 – MICE Nội thành TP.HCM",
    "Day 2": "Tuyến 2 – MICE mở rộng Bình Dương",
    "Day 3": "Tuyến 3 – MICE nghỉ dưỡng Vũng Tàu – Hồ Tràm",
}


@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)
    return df


df_all = load_data()

# ============ HEADER ============
st.title("🗺️ Tuyến điểm du lịch MICE")
st.caption("Chọn ngày để xem chi tiết tuyến tham quan tương ứng")

# ============ SESSION STATE: ngày đang chọn ============
if "selected_day" not in st.session_state:
    st.session_state.selected_day = "Day 1"

# ============ THANH CHỌN DAY 1 / DAY 2 / DAY 3 (dạng nút bấm) ============
days = ["Day 1", "Day 2", "Day 3"]
cols = st.columns(len(days))

for i, day in enumerate(days):
    with cols[i]:
        is_selected = st.session_state.selected_day == day
        btn_type = "primary" if is_selected else "secondary"
        if st.button(day, key=f"btn_{day}", use_container_width=True, type=btn_type):
            st.session_state.selected_day = day

selected_day = st.session_state.selected_day
df_day = df_all[df_all["DAY"] == selected_day].sort_values("THU_TU").reset_index(drop=True)

st.markdown("---")

# ============ LAYOUT: BẢN ĐỒ (trái) + DANH SÁCH ĐIỂM (phải) ============
col_map, col_list = st.columns([1.4, 1])

with col_map:
    if len(df_day) > 0:
        center_lat = df_day["LAT"].mean()
        center_lon = df_day["LON"].mean()
    else:
        center_lat, center_lon = 10.78, 106.70

    m = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="OpenStreetMap")

    color = TOUR_COLORS.get(df_day["TUYEN"].iloc[0], "#4285F4") if len(df_day) > 0 else "#4285F4"

    # Vẽ các điểm + đường nối theo thứ tự THU_TU
    coords = []
    for idx, row in df_day.iterrows():
        coords.append([row["LAT"], row["LON"]])

        popup_html = f"""
        <b>{row['THU_TU']}. {row['TEN']}</b><br>
        🕐 {row['THOI_GIAN']}<br>
        {row['MO_TA']}
        """
        folium.Marker(
            location=[row["LAT"], row["LON"]],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=row["TEN"],
            icon=folium.DivIcon(html=f"""
                <div style="
                    background-color:{color};
                    color:white;
                    border-radius:50%;
                    width:28px;height:28px;
                    display:flex;align-items:center;justify-content:center;
                    font-weight:bold;font-size:13px;
                    border:2px solid white;
                    box-shadow:0 1px 3px rgba(0,0,0,0.4);
                ">{row['THU_TU']}</div>
            """)
        ).add_to(m)

    # Vẽ tuyến đường nối các điểm theo thứ tự
    if len(coords) > 1:
        folium.PolyLine(coords, color=color, weight=4, opacity=0.7, dash_array="8,6").add_to(m)

    st_folium(m, width=None, height=600, key=f"map_{selected_day}")

with col_list:
    title = TOUR_TITLES.get(selected_day, selected_day)
    st.subheader(title)

    for idx, row in df_day.iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([0.15, 0.85])
            with c1:
                st.markdown(
                    f"""<div style="
                        background-color:{color};
                        color:white;
                        border-radius:50%;
                        width:32px;height:32px;
                        display:flex;align-items:center;justify-content:center;
                        font-weight:bold;
                        margin-top:4px;
                    ">{row['THU_TU']}</div>""",
                    unsafe_allow_html=True
                )
            with c2:
                st.markdown(f"**🕐 {row['THOI_GIAN']}**")
                st.markdown(f"### {row['TEN']}")
                st.caption(row["MO_TA"])

# ============ BẢNG DỮ LIỆU CHI TIẾT (tuỳ chọn xem thêm) ============
with st.expander("📋 Xem dữ liệu dạng bảng"):
    st.dataframe(
        df_day[["THU_TU", "TEN", "THOI_GIAN", "MO_TA", "LAT", "LON"]],
        use_container_width=True,
        hide_index=True
    )

# ============ TẢI TOÀN BỘ DỮ LIỆU ============
with st.sidebar:
    st.header("⚙️ Tùy chọn")
    st.markdown("**Toàn bộ 3 tuyến MICE**")
    st.dataframe(df_all[["TUYEN", "DAY", "TEN"]], use_container_width=True, hide_index=True)

    csv = df_all.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Tải dữ liệu CSV",
        data=csv,
        file_name="mice_tours.csv",
        mime="text/csv"
    )
