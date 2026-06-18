import streamlit as st

st.title("🎈 Ứng dụng giới thiệu tuyến điểm du lịch Mice")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)
"""
Bảng điều khiển giới thiệu tuyến điểm du lịch Mice
---------------------------------------------------
Đọc dữ liệu từ shapefile (Data/Mice.shp) và hiển thị dưới dạng:
- Bản đồ tương tác (Folium) với marker/đường, popup thông tin
- Bộ lọc theo các cột phân loại có trong dữ liệu
- Ô tìm kiếm theo tên
- Thẻ chi tiết khi chọn 1 tuyến/điểm
- Bảng dữ liệu đầy đủ + nút tải CSV

Code được viết để TỰ NHẬN DIỆN cấu trúc cột, nên chạy được ngay
cả khi bạn chưa chỉnh tên cột cho khớp 100% với dữ liệu thật.
"""

import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium

# ------------------------------------------------------------------
# Cấu hình trang
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Tuyến điểm du lịch Mice",
    page_icon="🗺️",
    layout="wide",
)

DATA_PATH = "Data/Mice.shp"


# ------------------------------------------------------------------
# Đọc & chuẩn hoá dữ liệu
# ------------------------------------------------------------------
@st.cache_data
def load_data(path: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    # Folium cần hệ toạ độ WGS84 (EPSG:4326)
    if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    return gdf


def guess_name_column(gdf: gpd.GeoDataFrame) -> str:
    """Đoán cột nào là 'tên' (ưu tiên các tên cột thường gặp)."""
    candidates = ["ten", "name", "tentuyen", "diadiem", "tendiem", "tieude"]
    for col in gdf.columns:
        if col.lower().replace("_", "") in candidates:
            return col
    text_cols = [c for c in gdf.columns if gdf[c].dtype == "object" and c != "geometry"]
    return text_cols[0] if text_cols else gdf.columns[0]


try:
    gdf = load_data(DATA_PATH)
except Exception as e:
    st.error(
        f"Không đọc được dữ liệu tại `{DATA_PATH}`.\n\n"
        f"Hãy kiểm tra: file Mice.shp/.dbf/.shx/.prj đã nằm cùng thư mục `Data/` chưa.\n\n"
        f"Lỗi chi tiết: {e}"
    )
    st.stop()

attr_cols = [c for c in gdf.columns if c != "geometry"]
name_col = guess_name_column(gdf)
geom_type = gdf.geometry.geom_type.iloc[0] if len(gdf) else "Unknown"

# Các cột phân loại phù hợp để làm bộ lọc (kiểu chữ, số lượng giá trị ít)
filter_cols = [
    c for c in attr_cols
    if gdf[c].dtype == "object" and gdf[c].nunique() <= 30 and c != name_col
]

# ------------------------------------------------------------------
# Sidebar - bộ lọc & cấu hình
# ------------------------------------------------------------------
st.sidebar.header("⚙️ Tuỳ chọn hiển thị")

name_col = st.sidebar.selectbox(
    "Cột dùng làm 'Tên tuyến/điểm'", attr_cols,
    index=attr_cols.index(name_col) if name_col in attr_cols else 0,
)

search_text = st.sidebar.text_input("🔎 Tìm theo tên", "")

filtered = gdf.copy()
if search_text:
    filtered = filtered[
        filtered[name_col].astype(str).str.contains(search_text, case=False, na=False)
    ]

active_filters = {}
for col in filter_cols:
    options = sorted(gdf[col].dropna().unique().tolist())
    chosen = st.sidebar.multiselect(f"Lọc theo: {col}", options)
    if chosen:
        active_filters[col] = chosen
        filtered = filtered[filtered[col].isin(chosen)]

st.sidebar.markdown("---")
st.sidebar.caption(f"Tổng số bản ghi: {len(gdf)} | Đang hiển thị: {len(filtered)}")
st.sidebar.caption(f"Loại hình học: {geom_type}")

# ------------------------------------------------------------------
# Tiêu đề
# ------------------------------------------------------------------
st.title("🗺️ Tuyến điểm du lịch Mice")
st.write(
    "Khám phá các tuyến/điểm du lịch Mice trên bản đồ tương tác. "
    "Dùng thanh bên để tìm kiếm, lọc theo nhóm, hoặc chọn một tuyến để xem chi tiết."
)

if filtered.empty:
    st.warning("Không có dữ liệu phù hợp với bộ lọc hiện tại.")
    st.stop()

col_map, col_detail = st.columns([2, 1])

# ------------------------------------------------------------------
# Bản đồ tương tác
# ------------------------------------------------------------------
with col_map:
    st.subheader("Bản đồ")

    bounds = filtered.total_bounds  # minx, miny, maxx, maxy
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="CartoDB positron")

    for _, row in filtered.iterrows():
        label = str(row[name_col])
        popup_html = f"<b>{label}</b><br>" + "<br>".join(
            f"{c}: {row[c]}" for c in attr_cols if c != name_col and pd.notna(row[c])
        )

        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        if geom.geom_type == "Point":
            folium.Marker(
                location=[geom.y, geom.x],
                tooltip=label,
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color="blue", icon="info-sign"),
            ).add_to(m)
        elif geom.geom_type in ("LineString", "MultiLineString"):
            folium.GeoJson(
                geom,
                tooltip=label,
                style_function=lambda f: {"color": "#d62728", "weight": 4},
            ).add_to(m)
        else:  # Polygon / MultiPolygon hoặc loại khác
            folium.GeoJson(geom, tooltip=label).add_to(m)

    try:
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    except Exception:
        pass

    map_state = st_folium(m, width=None, height=560, returned_objects=["last_object_clicked_tooltip"])

# ------------------------------------------------------------------
# Chi tiết tuyến/điểm
# ------------------------------------------------------------------
with col_detail:
    st.subheader("Chi tiết")

    names_list = filtered[name_col].astype(str).tolist()
    default_index = 0
    clicked = map_state.get("last_object_clicked_tooltip") if map_state else None
    if clicked and clicked in names_list:
        default_index = names_list.index(clicked)

    selected_name = st.selectbox("Chọn tuyến/điểm để xem chi tiết", names_list, index=default_index)
    selected_row = filtered[filtered[name_col].astype(str) == selected_name].iloc[0]

    st.markdown(f"### {selected_name}")
    for c in attr_cols:
        if c == name_col or pd.isna(selected_row[c]):
            continue
        st.markdown(f"**{c}:** {selected_row[c]}")

# ------------------------------------------------------------------
# Bảng dữ liệu đầy đủ
# ------------------------------------------------------------------
st.subheader("📋 Danh sách đầy đủ")
display_df = pd.DataFrame(filtered.drop(columns="geometry"))
st.dataframe(display_df, use_container_width=True, hide_index=True)

csv_data = display_df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "⬇️ Tải dữ liệu (CSV)",
    data=csv_data,
    file_name="tuyen_diem_mice.csv",
    mime="text/csv",
)