import streamlit as st

st.title("🎈 Ứng dụng giới thiệu tuyến điểm du lịch Mice")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)
import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium

# ============ CONFIG ============
st.set_page_config(page_title="Tuyến điểm MICE", layout="wide")

DATA_PATH = "Data/mice_full.csv"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"

DAY_INFO = {
    "Day 1": {
        "vung": "TP. Hồ Chí Minh",
        "cuc": "Cực Tài chính – Dịch vụ – Quản trị",
        "color": "#2E6F9E",
        "banner": "#F3E4D0",
    },
    "Day 2": {
        "vung": "Bình Dương",
        "cuc": "Cực Công nghiệp – Logistics",
        "color": "#2E7D4F",
        "banner": "#E2EFE3",
    },
    "Day 3": {
        "vung": "Bà Rịa – Vũng Tàu",
        "cuc": "Cực Sinh thái – Du lịch biển – Di sản",
        "color": "#C2620E",
        "banner": "#F6E6D6",
    },
}

ICON_BY_TYPE = {
    "Hội nghị": "🏛️",
    "Khách sạn": "🏨",
    "Nhà hàng": "🍽️",
    "Triển lãm": "🖼️",
    "Vui chơi/Tham quan": "🌳",
}


@st.cache_data
def load_data():
    return pd.read_csv(DATA_PATH)


@st.cache_data(show_spinner=False)
def get_road_route(coords_list):
    """
    Gọi OSRM để lấy tuyến đường thực tế (đi theo đường bộ) nối các điểm theo thứ tự.
    coords_list: list các (lat, lon) theo đúng thứ tự hành trình.
    Trả về list [(lat, lon), ...] của toàn tuyến đường, hoặc None nếu lỗi.
    """
    if len(coords_list) < 2:
        return None
    # OSRM cần format lon,lat;lon,lat;...
    coord_str = ";".join([f"{lon},{lat}" for lat, lon in coords_list])
    url = OSRM_URL.format(coords=coord_str)
    try:
        resp = requests.get(url, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "Ok" and data.get("routes"):
                geom = data["routes"][0]["geometry"]["coordinates"]
                # geom là [lon, lat] -> đổi thành [lat, lon] cho folium
                return [(lat, lon) for lon, lat in geom]
    except requests.exceptions.RequestException:
        pass
    return None


df_all = load_data()

# ============ SESSION STATE ============
if "selected_day" not in st.session_state:
    st.session_state.selected_day = "Day 1"

# ============ VÙNG 1: THANH CHỌN (TRÊN CÙNG) ============
days = ["Day 1", "Day 2", "Day 3"]
sel_cols = st.columns(3)
for i, day in enumerate(days):
    info = DAY_INFO[day]
    with sel_cols[i]:
        is_selected = st.session_state.selected_day == day
        btn_type = "primary" if is_selected else "secondary"
        label = f"{day} · {info['vung']}"
        if st.button(label, key=f"btn_{day}", use_container_width=True, type=btn_type):
            st.session_state.selected_day = day

selected_day = st.session_state.selected_day
info = DAY_INFO[selected_day]
color = info["color"]

df_day = df_all[df_all["DAY"] == selected_day].reset_index(drop=True)
df_route = df_day[df_day["THU_TU"].notna()].sort_values("THU_TU").reset_index(drop=True)
n_points = len(df_route)
n_provinces = df_day["VUNG"].nunique()

# ============ BANNER THÔNG TIN (gộp vào vùng thanh chọn) ============
st.markdown(
    f"""
    <div style="
        background-color:{info['banner']};
        border-radius:8px;
        padding:18px 24px;
        margin-top:6px;
        margin-bottom:18px;
    ">
        <div style="font-size:20px; font-weight:800; color:{color}; letter-spacing:0.5px;">
            {selected_day.upper()} — {info['vung'].upper()}
        </div>
        <div style="margin-top:8px; font-size:15px; color:#3a3a3a;">
            <b>{info['cuc']}</b><br>
            Hành trình gồm <b>{n_points} điểm</b> tiêu biểu, kết hợp hội nghị / triển lãm,
            lưu trú &amp; ẩm thực, cùng các điểm tham quan – vui chơi tại khu vực.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ============ VÙNG 2 (TRÁI, BẢN ĐỒ) + VÙNG 3 (PHẢI, THÔNG TIN) ============
col_map, col_info = st.columns([2, 1])

with col_map:
    if len(df_day) > 0:
        center_lat = df_day["LAT"].mean()
        center_lon = df_day["LON"].mean()
    else:
        center_lat, center_lon = 10.78, 106.70

    m = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles="OpenStreetMap")

    # --- Vẽ tuyến đường bộ thực tế nối các điểm hành trình chính ---
    if n_points >= 2:
        coords_list = list(zip(df_route["LAT"], df_route["LON"]))
        road_geom = get_road_route(coords_list)

        if road_geom:
            folium.PolyLine(
                road_geom, color=color, weight=4, opacity=0.85
            ).add_to(m)
        else:
            # Fallback: nối thẳng nếu không gọi được OSRM (vd. mạng bị chặn)
            folium.PolyLine(
                coords_list, color=color, weight=3, opacity=0.6, dash_array="6,6"
            ).add_to(m)
            st.caption("⚠️ Không lấy được tuyến đường bộ thực tế (OSRM) — đang hiển thị đường nối thẳng tạm thời.")

    # --- Marker cho các điểm thuộc hành trình chính (có số thứ tự) ---
    for idx, row in df_route.iterrows():
        folium.Marker(
            location=[row["LAT"], row["LON"]],
            tooltip=f"{int(row['THU_TU'])}. {row['TEN']}",
            popup=folium.Popup(f"<b>{int(row['THU_TU'])}. {row['TEN']}</b><br>{row['LOAI_HINH']}", max_width=280),
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
                ">{int(row['THU_TU'])}</div>
            """)
        ).add_to(m)

    # --- Marker mờ cho các điểm còn lại (không thuộc hành trình chính) ---
    df_other = df_day[df_day["THU_TU"].isna()]
    for idx, row in df_other.iterrows():
        icon_char = ICON_BY_TYPE.get(row["LOAI_HINH"], "📍")
        folium.Marker(
            location=[row["LAT"], row["LON"]],
            tooltip=row["TEN"],
            popup=folium.Popup(f"{icon_char} {row['TEN']}<br>{row['LOAI_HINH']}", max_width=260),
            icon=folium.DivIcon(html=f"""
                <div style="
                    background-color:white;
                    color:{color};
                    border:2px solid {color};
                    border-radius:50%;
                    width:24px;height:24px;
                    display:flex;align-items:center;justify-content:center;
                    font-size:12px;
                    opacity:0.85;
                ">{icon_char}</div>
            """)
        ).add_to(m)

    st_folium(m, width=None, height=620, key=f"map_{selected_day}")

with col_info:
    st.markdown(
        f"""<div style="font-size:18px; font-weight:800; color:{color}; margin-bottom:10px;">
        CHI TIẾT HÀNH TRÌNH
        </div>""",
        unsafe_allow_html=True
    )

    with st.container(height=600):
        # --- Hành trình chính, có số thứ tự tròn giống ảnh mẫu ---
        for idx, row in df_route.iterrows():
            icon_char = ICON_BY_TYPE.get(row["LOAI_HINH"], "📍")
            st.markdown(
                f"""
                <div style="display:flex; align-items:flex-start; margin-bottom:14px;">
                    <div style="
                        flex-shrink:0;
                        background-color:{color};
                        color:white;
                        border-radius:50%;
                        width:26px;height:26px;
                        display:flex;align-items:center;justify-content:center;
                        font-weight:bold;font-size:13px;
                        margin-right:10px;
                    ">{int(row['THU_TU'])}</div>
                    <div>
                        <div style="font-weight:700; color:{color}; font-size:15px;">{row['TEN']}</div>
                        <div style="font-size:13px; color:#555;">{icon_char} {row['LOAI_HINH']}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # --- Các điểm tham khảo thêm (không nằm trong hành trình chính) ---
        if len(df_other) > 0:
            st.markdown("---")
            st.markdown(f"**Các điểm tham khảo thêm tại {info['vung']}**")
            order = ["Hội nghị", "Triển lãm", "Khách sạn", "Nhà hàng", "Vui chơi/Tham quan"]
            df_other_sorted = df_other.copy()
            df_other_sorted["LOAI_HINH"] = pd.Categorical(df_other_sorted["LOAI_HINH"], categories=order, ordered=True)
            df_other_sorted = df_other_sorted.sort_values("LOAI_HINH")

            current_type = None
            for idx, row in df_other_sorted.iterrows():
                if row["LOAI_HINH"] != current_type:
                    current_type = row["LOAI_HINH"]
                    icon_char = ICON_BY_TYPE.get(current_type, "📍")
                    st.markdown(f"*{icon_char} {current_type}*")
                st.markdown(f"&nbsp;&nbsp;• {row['TEN']}")

# ============ SIDEBAR ============
with st.sidebar:
    st.header("⚙️ Tùy chọn")
    st.markdown(f"**Tổng số điểm – {selected_day}:** {len(df_day)}")
    st.dataframe(
        df_day[["TEN", "LOAI_HINH"]],
        use_container_width=True,
        hide_index=True
    )

    csv_bytes = df_all.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Tải toàn bộ dữ liệu CSV",
        data=csv_bytes,
        file_name="mice_full.csv",
        mime="text/csv"
    )
