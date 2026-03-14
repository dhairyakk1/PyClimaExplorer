import os
import streamlit as st
import xarray as xr
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# --- 1. PRO UI CONFIGURATION & CSS ---
st.set_page_config(layout="wide", page_title="Climate Engine | The Pointless Pointers", page_icon="🌍")

st.markdown("""
    <style>
    /* Global Background and Typography */
    .stApp {
        background: radial-gradient(circle at top left, #0A1128, #04070D);
        color: #E0E6ED;
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    
    /* Hide Streamlit Clutter */
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Scrollbar Polish */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-thumb { background: rgba(0, 212, 255, 0.4); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0, 212, 255, 0.8); }
    
    /* Glassmorphism Metric Cards */
    [data-testid="stMetric"] {
        background: rgba(10, 17, 40, 0.6);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid rgba(0, 212, 255, 0.15);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(4px);
    }
    [data-testid="stMetricLabel"] { font-size: 1rem; color: #80DEEA; font-weight: 500; }
    [data-testid="stMetricValue"] { font-size: 2.2rem; color: #FFFFFF; font-weight: 700; text-shadow: 0 0 10px rgba(0,212,255,0.3); }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #04070D !important;
        border-right: 1px solid rgba(0, 212, 255, 0.1);
    }
    .sidebar-title { font-size: 1.5rem; font-weight: bold; color: #00d4ff; text-align: center; margin-bottom: 20px;}
    .team-credit { text-align: center; font-size: 0.8rem; color: #555; margin-top: 50px; }
    
    /* Divider Polish */
    hr { border-color: rgba(0, 212, 255, 0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "lat" not in st.session_state: st.session_state.lat = 25.3  # Varanasi
if "lon" not in st.session_state: st.session_state.lon = 83.0

def sync_sidebar():
    st.session_state.lat = st.session_state.sidebar_lat
    st.session_state.lon = st.session_state.sidebar_lon

# --- 2. DATA ENGINE (Untouched) ---
@st.cache_resource(show_spinner="Booting Climate Engine...")
def load_climate_data():
    file_path = "dataset_lite.nc"
    if not os.path.exists(file_path):
        st.error(f"🚨 CRITICAL: '{file_path}' not found.")
        st.stop()
        
    ds = xr.open_dataset(file_path, engine="netcdf4", chunks={'time': 1})
    
    time_name = next((c for c in ds.coords if 'time' in c.lower()), None)
    if time_name: ds = ds.rename({time_name: 'time'})
    if 'expver' in ds.dims or 'expver' in ds.coords:
        ds = ds.sel(expver=ds.expver.values[0], drop=True)

    if 'longitude' in ds.coords: ds = ds.rename({'longitude': 'lon', 'latitude': 'lat'})
    
    if float(ds.lon.max()) > 180:
        ds.coords['lon'] = (ds.coords['lon'] + 180) % 360 - 180
        ds = ds.sortby(ds.lon) 
    
    rename_map = {"t2m": "Temp", "u10": "U", "v10": "V", "tp": "Precip"}
    ds = ds.rename({k: v for k, v in rename_map.items() if k in ds})
    
    if "U" in ds and "V" in ds:
        ds["Wind Speed"] = np.sqrt(ds.U**2 + ds.V**2)
        ds = ds.drop_vars(["U", "V"]) 
        
    return ds

try:
    ds = load_climate_data()

    # --- 3. SIDEBAR: COMMAND CENTER ---
    st.sidebar.markdown("<div class='sidebar-title'>⚙️ COMMAND CENTER</div>", unsafe_allow_html=True)
    
    st.sidebar.markdown("**1. Data Layer**")
    param = st.sidebar.selectbox("Select Parameter", ["Temp", "Wind Speed", "Precip"], label_visibility="collapsed")
    
    time_coords = pd.to_datetime(ds.time.values)
    st.sidebar.markdown("<br>**2. Temporal Timeline**", unsafe_allow_html=True)
    selected_time = st.sidebar.select_slider("Timeline", options=time_coords, format_func=lambda x: x.strftime("%b %Y"), label_visibility="collapsed")

    st.sidebar.divider()
    
    st.sidebar.markdown("**3. Spatial Targeting**")
    GLOBAL_CITIES = {
        "Amazon Rainforest": (-3.0, -60.0), "Antarctica (South Pole)": (-90.0, 0.0),
        "Beijing, China": (39.9, 116.4), "Buenos Aires, Argentina": (-34.6, -58.4), 
        "Cape Town, South Africa": (-33.9, 18.4), "Delhi, India": (28.6, 77.2), 
        "Dubai, UAE": (25.2, 55.3), "London, UK": (51.5, -0.1), 
        "Los Angeles, USA": (34.0, -118.2), "Moscow, Russia": (55.7, 37.6), 
        "Mumbai, India": (19.0, 72.8), "Nairobi, Kenya": (-1.3, 36.8), 
        "New York, USA": (40.7, -74.0), "Paris, France": (48.8, 2.3), 
        "Rio de Janeiro, Brazil": (-22.9, -43.2), "Sahara Desert": (23.5, 12.0), 
        "Singapore": (1.3, 103.8), "Sydney, Australia": (-33.8, 151.2), 
        "Tokyo, Japan": (35.6, 139.6), "Varanasi, India": (25.3, 83.0)
    }
    
    city_choice = st.sidebar.selectbox("Quick Jump", ["-- Select City --"] + list(GLOBAL_CITIES.keys()), label_visibility="collapsed")
    if city_choice != "-- Select City --":
        st.session_state.lat, st.session_state.lon = GLOBAL_CITIES[city_choice]

    colA, colB = st.sidebar.columns(2)
    colA.number_input("Lat", value=st.session_state.lat, step=0.5, key="sidebar_lat", on_change=sync_sidebar)
    colB.number_input("Lon", value=st.session_state.lon, step=0.5, key="sidebar_lon", on_change=sync_sidebar)

    st.sidebar.markdown("<div class='team-credit'>Built by <b>The Pointless Pointers</b></div>", unsafe_allow_html=True)

    # --- UI & COLOR SCALES ---
    temp_scale = [[0.0, "#011959"], [0.33, "#105a96"], [0.55, "#3ba3a1"], [0.77, "#f09a39"], [1.0, "#5b0b1e"]]
    precip_scale = [[0.0, "rgba(0,0,0,0)"], [0.15, "#80DEEA"], [0.50, "#00ACC1"], [1.00, "#01579B"]]
    cmaps = {"Temp": temp_scale, "Wind Speed": "Viridis", "Precip": precip_scale}
    units = {"Temp": "Temperature (C)", "Wind Speed": "Wind Speed (m/s)", "Precip": "Precipitation (mm)"}

    # --- 4. MAIN DASHBOARD AREA ---
    st.markdown(f"<h2 style='text-align: center; color: #FFFFFF; font-weight: 300; letter-spacing: 2px;'>GLOBAL <span style='color: #00d4ff; font-weight: bold;'>{param.upper()}</span> DYNAMICS</h2>", unsafe_allow_html=True)
    
    # 4A. THE MAP CONTAINER
    with st.container():
        data_slice = ds[param].sel(time=selected_time, method="nearest").compute()
        if param == "Temp" and data_slice.max() > 100: data_slice = data_slice - 273.15
        if param == "Precip" and data_slice.max() < 0.1: data_slice = data_slice * 1000
        data_slice.name = units[param]

        fig = px.imshow(
            data_slice, x=data_slice.lon, y=data_slice.lat, 
            color_continuous_scale=cmaps.get(param, "Viridis"), origin="lower", aspect="auto"
        )
        
        fig.add_trace(go.Scatter(x=[st.session_state.lon], y=[st.session_state.lat], mode="markers", marker=dict(color="#ff0055", size=8), showlegend=False, hoverinfo="skip"))
        
        gap, length = 3.0, 10.0
        l_style = dict(color="#00ffff", width=2)
        fig.add_shape(type="line", x0=st.session_state.lon, x1=st.session_state.lon, y0=st.session_state.lat + gap, y1=st.session_state.lat + length, line=l_style)
        fig.add_shape(type="line", x0=st.session_state.lon, x1=st.session_state.lon, y0=st.session_state.lat - gap, y1=st.session_state.lat - length, line=l_style)
        fig.add_shape(type="line", x0=st.session_state.lon + gap, x1=st.session_state.lon + length, y0=st.session_state.lat, y1=st.session_state.lat, line=l_style)
        fig.add_shape(type="line", x0=st.session_state.lon - gap, x1=st.session_state.lon - length, y0=st.session_state.lat, y1=st.session_state.lat, line=l_style)
        
        # Pro Plotly Styling (Transparent backgrounds)
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin={"l": 0, "r": 0, "b": 0, "t": 10}, height=550, 
            xaxis_visible=False, yaxis_visible=False,
            coloraxis_colorbar=dict(title="", tickfont=dict(color="#FFF"))
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True) # Spacing

    # 4B. METRICS & TREND CONTAINER
    point_series = ds[param].sel(lat=st.session_state.lat, lon=st.session_state.lon, method="nearest").compute()
    if param == "Temp" and point_series.max() > 100: point_series = point_series - 273.15
    if param == "Precip" and point_series.max() < 0.1: point_series = point_series * 1000
    
    current_val = float(point_series.sel(time=selected_time, method="nearest"))
    metric_unit = "°C" if param == "Temp" else ("m/s" if param == "Wind Speed" else "mm")

    c_metrics, c_graph = st.columns([1, 2.5])
    
    with c_metrics:
        st.metric(f"TARGET {param.upper()}", f"{current_val:.1f} {metric_unit}")
        st.markdown("<br>", unsafe_allow_html=True) # Spacing between cards
        st.metric("TIMELINE PEAK", f"{float(point_series.max()):.1f} {metric_unit}")
        
    with c_graph:
        trend_df = point_series.to_dataframe().reset_index()
        trend_fig = px.line(trend_df, x="time", y=param)
        
        # Pro Graph Styling
        trend_fig.update_traces(
            line=dict(color="#00ffff", width=2), 
            fill='tozeroy', fillcolor="rgba(0, 212, 255, 0.1)", # Adds a cool glowing fill under the line
            marker=dict(size=4, color="#ff0055")
        )
        trend_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=260, margin={"l": 0, "r": 0, "b": 0, "t": 10},
            xaxis=dict(title="", showgrid=False, tickfont=dict(color="#888")),
            yaxis=dict(title=units[param], showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="#888"))
        )
        st.plotly_chart(trend_fig, use_container_width=True)

except Exception as e:
    st.error(f"System Offline: {e}")