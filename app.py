import os
import streamlit as st
import xarray as xr
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# --- 1. UI CONFIGURATION ---
st.set_page_config(layout="wide", page_title="The Pointless Pointers | Climate Suite")

st.markdown("""
    <style>
    .main { background-color: #070B14; color: #FFFFFF; }
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-thumb { background: #00d4ff; border-radius: 4px; }
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #00d4ff; font-weight: bold; }
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "lat" not in st.session_state: st.session_state.lat = 28.6
if "lon" not in st.session_state: st.session_state.lon = 77.2

def sync_sidebar():
    st.session_state.lat = st.session_state.sidebar_lat
    st.session_state.lon = st.session_state.sidebar_lon

# --- 2. DATA ENGINE ---
@st.cache_resource(show_spinner="Syncing Climate Data Engine...")
def load_climate_data():
    possible_paths = ["dataset_final.nc", "data/dataset_final.nc"]
    file_path = next((p for p in possible_paths if os.path.exists(p)), None)
    
    if not file_path:
        st.error("🚨 CRITICAL: 'dataset_final.nc' not found. Ensure it is uploaded to your GitHub root.")
        st.stop()
        
    ds = xr.open_dataset(file_path, engine="netcdf4", chunks={'time': 1})
    
    # 1. Dynamic Time Coord Fix
    time_name = next((c for c in ds.coords if 'time' in c.lower()), None)
    if time_name: ds = ds.rename({time_name: 'time'})
        
    # 2. Expver Dimension Fix
    if 'expver' in ds.dims or 'expver' in ds.coords:
        ds = ds.sel(expver=ds.expver.values[0], drop=True)

    # 3. Standardize Lat/Lon
    if 'longitude' in ds.coords: ds = ds.rename({'longitude': 'lon', 'latitude': 'lat'})
    
    # 4. Standardize Variables
    rename_map = {"t2m": "Temp", "u10": "U", "v10": "V", "tp": "Precip"}
    ds = ds.rename({k: v for k, v in rename_map.items() if k in ds})
    
    # 5. Wind Speed Vector Fix
    if "U" in ds and "V" in ds:
        ds["Wind Speed"] = np.sqrt(ds.U**2 + ds.V**2)
        ds = ds.drop_vars(["U", "V"]) 
        
    return ds

try:
    ds = load_climate_data()

    # --- 3. SIDEBAR CONTROLS ---
    st.sidebar.title("🛠️ Analysis Suite")
    param = st.sidebar.selectbox("Select Parameter", ["Temp", "Wind Speed", "Precip"])
    
    time_coords = pd.to_datetime(ds.time.values)
    selected_time = st.sidebar.select_slider("Global Timeline", options=time_coords, format_func=lambda x: x.strftime("%b %Y"))

    st.sidebar.divider()
    st.sidebar.subheader("📍 Location Targeting")
    
    GLOBAL_CITIES = {
        "Amazon Rainforest": (-3.0, -60.0),
        "Beijing, China": (39.9, 116.4),
        "Buenos Aires, Argentina": (-34.6, -58.4),
        "Cape Town, South Africa": (-33.9, 18.4),
        "Delhi, India": (28.6, 77.2),
        "Dubai, UAE": (25.2, 55.3),
        "London, UK": (51.5, -0.1),
        "Los Angeles, USA": (34.0, -118.2),
        "Moscow, Russia": (55.7, 37.6),
        "Mumbai, India": (19.0, 72.8),
        "Nairobi, Kenya": (-1.3, 36.8),
        "New York, USA": (40.7, -74.0),
        "Paris, France": (48.8, 2.3),
        "Rio de Janeiro, Brazil": (-22.9, -43.2),
        "Sahara Desert": (23.5, 12.0),
        "Singapore": (1.3, 103.8),
        "Sydney, Australia": (-33.8, 151.2),
        "Tokyo, Japan": (35.6, 139.6),
        "Toronto, Canada": (43.7, -79.4)
    }
    
    city_choice = st.sidebar.selectbox("Quick Jump Directory", ["-- Select City --"] + list(GLOBAL_CITIES.keys()))
    if city_choice != "-- Select City --":
        st.session_state.lat, st.session_state.lon = GLOBAL_CITIES[city_choice]

    st.sidebar.number_input("Latitude", value=st.session_state.lat, step=0.1, key="sidebar_lat", on_change=sync_sidebar)
    st.sidebar.number_input("Longitude", value=st.session_state.lon, step=0.1, key="sidebar_lon", on_change=sync_sidebar)

    # --- CUSTOM COLOR SCALES ---
    temp_scale = [[0.0, "#011959"], [0.33, "#105a96"], [0.55, "#a3d977"], [0.77, "#f09a39"], [1.0, "#5b0b1e"]]
    precip_scale = [[0.0, "#FFFFFF"], [0.15, "#80DEEA"], [0.50, "#00ACC1"], [1.00, "#01579B"]]
    cmaps = {"Temp": temp_scale, "Wind Speed": "Viridis", "Precip": precip_scale}
    units = {"Temp": "°C", "Wind Speed": "m/s", "Precip": "mm"}

    # --- 4. TOP SECTION: MAP ---
    with st.spinner("Rendering Visual Slice..."):
        data_slice = ds[param].sel(time=selected_time, method="nearest").compute()
        if param == "Temp" and data_slice.max() > 100: data_slice = data_slice - 273.15
        if param == "Precip" and data_slice.max() < 0.1: data_slice = data_slice * 1000

    fig = px.imshow(
        data_slice,
        color_continuous_scale=cmaps.get(param, "Viridis"),
        origin="lower",
        title=f"Global {param} Dynamics - {selected_time.strftime('%B %Y')}",
        aspect="auto"
    )
    
    # --- NEW TARGET-LOCK CROSSHAIR ---
    # Central dot
    fig.add_trace(go.Scatter(x=[st.session_state.lon], y=[st.session_state.lat], 
                             mode="markers", marker=dict(color="#ff0055", size=8), showlegend=False, hoverinfo="skip"))
    
    # The 4 non-intersecting arms
    gap, length = 2.0, 8.0  # Gap creates the hole in the middle, Length extends the lines
    l_style = dict(color="#00ffff", width=2)
    
    fig.add_shape(type="line", x0=st.session_state.lon, x1=st.session_state.lon, y0=st.session_state.lat + gap, y1=st.session_state.lat + length, line=l_style) # Top
    fig.add_shape(type="line", x0=st.session_state.lon, x1=st.session_state.lon, y0=st.session_state.lat - gap, y1=st.session_state.lat - length, line=l_style) # Bottom
    fig.add_shape(type="line", x0=st.session_state.lon + gap, x1=st.session_state.lon + length, y0=st.session_state.lat, y1=st.session_state.lat, line=l_style) # Right
    fig.add_shape(type="line", x0=st.session_state.lon - gap, x1=st.session_state.lon - length, y0=st.session_state.lat, y1=st.session_state.lat, line=l_style) # Left
    # ---------------------------------
    
    fig.update_layout(template="plotly_dark", margin={"l": 10, "r": 10, "b": 0, "t": 50}, height=540, xaxis_visible=False, yaxis_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # --- 5. BOTTOM SECTION: STATS & TREND ---
    st.divider()
    c1, c2 = st.columns([1, 2])
    
    point_series = ds[param].sel(lat=st.session_state.lat, lon=st.session_state.lon, method="nearest").compute()
    if param == "Temp" and point_series.max() > 100: point_series = point_series - 273.15
    
    current_val = float(point_series.sel(time=selected_time, method="nearest"))
    c1.metric(f"Current {param}", f"{current_val:.2f} {units.get(param, '')}")
    c1.metric("Timeline Peak", f"{float(point_series.max()):.2f} {units.get(param, '')}")
    
    trend_df = point_series.to_dataframe().reset_index()
    trend_fig = px.line(trend_df, x="time", y=param, markers=True, title="Historical Trend Profile")
    trend_fig.update_traces(line=dict(color="#00ffff", width=3), marker=dict(size=6, color="#ff0055"))
    trend_fig.update_layout(height=250, template="plotly_dark", margin={"l": 0, "r": 0, "b": 0, "t": 30})
    c2.plotly_chart(trend_fig, use_container_width=True)

except Exception as e:
    st.error(f"Engine Failure: {e}")
