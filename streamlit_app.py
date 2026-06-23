import streamlit as st

st.title("🎈 Giới thiệu tuyến điểm du lịch Mice")
import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium

# ============ CONFIG ============
st.set_page_config(
    page_title="Tuyến điểm MICE",
    layout="wide",
    initial_sidebar_state="collapsed",  # Ẩn sidebar mặc định
)

# Ẩn hoàn toàn sidebar và nút mở sidebar
st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="collapsedControl"] {display: none;}
    </style>
    """,
    unsafe_allow_html=True
)

DATA_PATH = "Data/tours_detail.csv"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"

TOUR_INFO = {
    "Tour 1": {
        "color": "#2E6F9E",
        "banner": "#DCE9F5",
    },
    "Tour 2": {
        "color": "#2E7D4F",
        "banner": "#E2EFE3",
    },
    "Tour 3": {
        "color": "#C2620E",
        "banner": "#F6E6D6",
    },
}

BUOI_ICON = {
    "Sáng": "🌅",
    "Trưa": "🍽️",
    "Chiều": "🌇",
    "Tối": "🌙",
}


@st.cache_data
def load_data():
    return pd.read_csv(DATA_PATH)


@st.cache_data(show_spinner=False)
def get_road_route(coords_list):
    """Gọi OSRM lấy tuyến đường bộ thực tế nối các điểm theo thứ tự."""
    if len(coords_list) < 2:
        return None
    coord_str = ";".join([f"{lon},{lat}" for lat, lon in coords_list])
    url = OSRM_URL.format(coords=coord_str)
    try:
        resp = requests.get(url, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "Ok" and data.get("routes"):
                geom = data["routes"][0]["geometry"]["coordinates"]
                return [(lat, lon) for lon, lat in geom]
    except requests.exceptions.RequestException:
        pass
    return None


df_all = load_data()

# ============ SESSION STATE ============
if "selected_tour" not in st.session_state:
    st.session_state.selected_tour = "Tour 1"

# ============ VÙNG TRÊN: THANH CHỌN TOUR ============
st.markdown("## 🗺️ Tuyến điểm du lịch MICE")

tours = ["Tour 1", "Tour 2", "Tour 3"]
sel_cols = st.columns(3)
for i, tour in enumerate(tours):
    with sel_cols[i]:
        is_selected = st.session_state.selected_tour == tour
        btn_type = "primary" if is_selected else "secondary"
        if st.button(tour, key=f"btn_{tour}", use_container_width=True, type=btn_type):
            st.session_state.selected_tour = tour

selected_tour = st.session_state.selected_tour
tinfo = TOUR_INFO[selected_tour]
color = tinfo["color"]

df_tour = df_all[df_all["TOUR"] == selected_tour].sort_values("THU_TU").reset_index(drop=True)
title = df_tour["TITLE"].iloc[0]
subtitle = df_tour["SUBTITLE"].iloc[0]

# ============ BANNER THÔNG TIN ============
st.markdown(
    f"""
    <div style="
        background-color:{tinfo['banner']};
        border-radius:8px;
        padding:18px 24px;
        margin-top:6px;
        margin-bottom:18px;
    ">
        <div style="font-size:19px; font-weight:800; color:{color};">
            {selected_tour.upper()} — "{title}"
        </div>
        <div style="margin-top:6px; font-size:14.5px; color:#3a3a3a;">
            {subtitle}
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ============ VÙNG TRÁI: BẢN ĐỒ + VÙNG PHẢI: CHI TIẾT HÀNH TRÌNH ============
col_map, col_info = st.columns([2, 1])

with col_map:
    center_lat = df_tour["LAT"].mean()
    center_lon = df_tour["LON"].mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=9, tiles="OpenStreetMap")

    # --- Lấy danh sách điểm DUY NHẤT theo thứ tự xuất hiện (gộp các mốc cùng địa điểm) ---
    unique_points = df_tour.drop_duplicates(subset=["TEN"], keep="first").reset_index(drop=True)
    coords_list = list(zip(unique_points["LAT"], unique_points["LON"]))

    # --- Vẽ tuyến đường bộ thực tế ---
    if len(coords_list) >= 2:
        road_geom = get_road_route(coords_list)
        if road_geom:
            folium.PolyLine(road_geom, color=color, weight=4, opacity=0.85).add_to(m)
        else:
            folium.PolyLine(coords_list, color=color, weight=3, opacity=0.6, dash_array="6,6").add_to(m)
            st.caption("⚠️ Không lấy được tuyến đường bộ thực tế (OSRM) — đang hiển thị đường nối thẳng tạm thời.")

    # --- Marker cho từng điểm duy nhất, đánh số theo thứ tự xuất hiện đầu tiên ---
    for idx, row in unique_points.iterrows():
        # Lấy toàn bộ các mốc giờ tại điểm này để hiện trong popup
        stops_here = df_tour[df_tour["TEN"] == row["TEN"]]
        stop_lines = "<br>".join(
            f"🕐 {r['GIO']} – {r['HOAT_DONG']}" for _, r in stops_here.iterrows()
        )
        popup_html = f"<b>{idx+1}. {row['TEN']}</b><br>{stop_lines}"

        folium.Marker(
            location=[row["LAT"], row["LON"]],
            tooltip=f"{idx+1}. {row['TEN']}",
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.DivIcon(html=f"""
                <div style="
                    background-color:{color};
                    color:white;
                    border-radius:50%;
                    width:30px;height:30px;
                    display:flex;align-items:center;justify-content:center;
                    font-weight:bold;font-size:14px;
                    border:2px solid white;
                    box-shadow:0 1px 3px rgba(0,0,0,0.4);
                ">{idx+1}</div>
            """)
        ).add_to(m)

    st_folium(m, width=None, height=620, key=f"map_{selected_tour}")

with col_info:
    st.markdown(
        f"""<div style="font-size:18px; font-weight:800; color:{color}; margin-bottom:10px;">
        CHI TIẾT HÀNH TRÌNH
        </div>""",
        unsafe_allow_html=True
    )

    # Map tên điểm -> số thứ tự (theo thứ tự xuất hiện đầu tiên, dùng để đánh số đồng bộ với bản đồ)
    point_order = {name: i + 1 for i, name in enumerate(unique_points["TEN"])}

    with st.container(height=600):
        for idx, row in df_tour.iterrows():
            buoi_icon = BUOI_ICON.get(row["BUOI"], "🕐")
            stop_no = point_order[row["TEN"]]
            st.markdown(
                f"""
                <div style="display:flex; align-items:flex-start; margin-bottom:16px;">
                    <div style="
                        flex-shrink:0;
                        background-color:{color};
                        color:white;
                        border-radius:50%;
                        width:26px;height:26px;
                        display:flex;align-items:center;justify-content:center;
                        font-weight:bold;font-size:13px;
                        margin-right:10px;
                        margin-top:2px;
                    ">{stop_no}</div>
                    <div>
                        <div style="font-size:12.5px; color:#888; font-weight:600;">
                            {buoi_icon} {row['BUOI']} ({row['GIO']})
                        </div>
                        <div style="font-weight:700; color:{color}; font-size:15px; margin-top:2px;">
                            {row['TEN']}
                        </div>
                        <div style="font-size:13.5px; color:#444; margin-top:2px;">
                            {row['HOAT_DONG']}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
