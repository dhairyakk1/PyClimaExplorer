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
    .stPlotlyChart { margin-bottom: -15px; }
    /* FIX: Hide the right-side toolbar (deploy/menu) but keep the sidebar toggle visible */
    [data-testid="stToolbar"] {visibility: hidden;}
    header {background: transparent !important;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "lat" not in st.session_state:
    st.session_state.lat = 20.5
if "lon" not in st.session_state:
    st.session_state.lon = 78.9

def sync_sidebar():
    st.session_state.lat = st.session_state.sidebar_lat
    st.session_state.lon = st.session_state.sidebar_lon

@st.cache_data(show_spinner=False)
def load_data():
    file_path = "dataset_final.nc"
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Missing core data file: {file_path}")
        
    ds = xr.open_dataset(file_path)
    
    time_name = next((c for c in ds.coords if "time" in str(c).lower()), None)
    if time_name and time_name != "time":
        ds = ds.rename({time_name: "time"})

    # 🌍 LONGITUDE WRAP FIX (-180 TO +180)
    lon_name = 'lon' if 'lon' in ds.coords else 'longitude'
    if lon_name in ds.coords and float(ds[lon_name].max()) > 180:
        ds.coords[lon_name] = (ds.coords[lon_name] + 180) % 360 - 180
        ds = ds.sortby(ds[lon_name])

    rename_map = {"t2m": "Temp", "u10": "U", "v10": "V", "tp": "Precip"}
    ds = ds.rename({k: v for k, v in rename_map.items() if k in ds})
    
    if "Temp" in ds and ds["Temp"].max() > 100: 
        ds["Temp"] = ds["Temp"] - 273.15
            
    if "U" in ds and "V" in ds:
        ds["Wind Speed"] = np.sqrt(ds.U**2 + ds.V**2)
        ds = ds.drop_vars(["U", "V"]) 
        
    if "Precip" in ds and ds["Precip"].max() < 1: 
        ds["Precip"] = ds["Precip"] * 1000 
        
    return ds

try:
    with st.spinner("Initializing Climate Engine..."):
        ds = load_data()

    # --- 2. SIDEBAR CONTROLS ---
    st.sidebar.title("🛠️ Analysis Suite")
    param = st.sidebar.selectbox("Select Parameter", ["Temp", "Wind Speed", "Precip"])
    
    time_coords = pd.to_datetime(ds.time.values)
    selected_time = st.sidebar.select_slider("Select Timeline", 
                                             options=time_coords, 
                                             format_func=lambda x: x.strftime("%b %Y"))

    st.sidebar.divider()
    
    # 🌍 UPGRADED FEATURE: CONTINENT-WISE QUICK-JUMP
    st.sidebar.subheader("📍 Location Targeting")
    
    nav_mode = st.sidebar.radio("Navigation Method", ["Quick Jump Directory", "Custom Coordinates"])
    
    if nav_mode == "Quick Jump Directory":
        REGION_PRESETS = {
            "🌎 North America": {
                "New York, USA": (40.7, -74.0),
                "Los Angeles, USA": (34.0, -118.2),
                "Toronto, Canada": (43.7, -79.4),
                "Mexico City, Mexico": (19.4, -99.1)
            },
            "🌍 South America": {
                "Amazon Rainforest": (-3.0, -60.0),
                "São Paulo, Brazil": (-23.5, -46.6),
                "Buenos Aires, Argentina": (-34.6, -58.4),
                "Santiago, Chile": (-33.4, -70.6)
            },
            "🌍 Europe": {
                "London, UK": (51.5, -0.1),
                "Paris, France": (48.8, 2.3),
                "Berlin, Germany": (52.5, 13.4),
                "Rome, Italy": (41.9, 12.5)
            },
            "🌍 Africa": {
                "Sahara Desert": (23.5, 12.0),
                "Cairo, Egypt": (30.0, 31.2),
                "Lagos, Nigeria": (6.5, 3.4),
                "Cape Town, South Africa": (-33.9, 18.4)
            },
            "🌏 Asia": {
                "Mumbai, India": (19.0, 72.8),
                "Delhi, India": (28.6, 77.2),
                "Tokyo, Japan": (35.6, 139.6),
                "Beijing, China": (39.9, 116.4),
                "Dubai, UAE": (25.2, 55.2)
            },
            "🌏 Oceania": {
                "Sydney, Australia": (-33.8, 151.2),
                "Melbourne, Australia": (-37.8, 144.9),
                "Auckland, New Zealand": (-36.8, 174.7)
            }
        }
        
        region = st.sidebar.selectbox("Select Continent:", list(REGION_PRESETS.keys()))
        city = st.sidebar.selectbox("Select Location:", list(REGION_PRESETS[region].keys()))
        
        st.session_state.lat = REGION_PRESETS[region][city][0]
        st.session_state.lon = REGION_PRESETS[region][city][1]

    # Manual coordinate entry perfectly synced
    lat_in = st.sidebar.number_input("Latitude", value=st.session_state.lat, step=0.5, key="sidebar_lat", on_change=sync_sidebar)
    lon_in = st.sidebar.number_input("Longitude", value=st.session_state.lon, step=0.5, key="sidebar_lon", on_change=sync_sidebar)

    # --- 3. CUSTOM COLOR SCALES ---
    temp_custom_scale = [
        [0.000, "#011959"], [0.333, "#105a96"], [0.444, "#3ba3a1"], 
        [0.556, "#a3d977"], [0.667, "#f5d448"], [0.778, "#f09a39"], 
        [0.889, "#c12128"], [1.000, "#5b0b1e"]   
    ]

    precip_custom_scale = [
        [0.00, "#FFFFFF"], [0.05, "#E0F7FA"], [0.15, "#80DEEA"], 
        [0.30, "#26C6DA"], [0.50, "#00ACC1"], [0.75, "#00838F"], [1.00, "#01579B"]
    ]

    cmaps = {"Temp": temp_custom_scale, "Wind Speed": "Viridis", "Precip": precip_custom_scale}
    units = {"Temp": "°C", "Wind Speed": "m/s", "Precip": "mm"}

    # --- 4. TOP SECTION: MAP ---
    if param not in ds:
        st.error(f"Parameter '{param}' not found in the dataset.")
        st.stop()
        
    data_slice = ds[param].sel(time=selected_time, method="nearest")
    
    if param == "Temp":
        z_min, z_max = (-40, 50)
    elif param == "Precip":
        z_min = 0
        current_max = float(data_slice.max())
        z_max = current_max * 0.6 if current_max > 0 else 10 
    else:
        z_min, z_max = (None, None)

    fig = px.imshow(
        data_slice,
        color_continuous_scale=cmaps.get(param, "Viridis"),
        origin="lower",
        title=f"Global {param} Map ({units.get(param, '')}) - {selected_time.strftime('%B %Y')}",
        aspect="auto",
        zmin=z_min,
        zmax=z_max
    )
    
    fig.add_trace(go.Scatter(
        x=[st.session_state.lon], y=[st.session_state.lat],
        mode="markers",
        marker=dict(color="rgba(0,0,0,0)", size=22, line=dict(color="#00ffff", width=3)),
        showlegend=False, hoverinfo="skip"
    ))
    fig.add_trace(go.Scatter(
        x=[st.session_state.lon], y=[st.session_state.lat],
        mode="markers",
        marker=dict(color="#ff0055", size=8),
        showlegend=False, hoverinfo="skip"
    ))
    
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)", 
        paper_bgcolor="rgba(0,0,0,0)",
        margin={"l": 10, "r": 10, "b": 0, "t": 50},
        height=540,
        xaxis={"showgrid": False, "zeroline": False, "visible": False}, 
        yaxis={"showgrid": False, "zeroline": False, "visible": False}, 
        coloraxis_colorbar=dict(title=units.get(param, "")),
        hovermode="closest"
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # --- 5. BOTTOM SECTION: STATS & TREND ---
    st.divider()
    c1, c2, c3, c4 = st.columns([1, 1, 1, 3])
    
    lat_key = 'lat' if 'lat' in ds.coords else 'latitude'
    lon_key = 'lon' if 'lon' in ds.coords else 'longitude'
    
    point_data = ds[param].sel({lat_key: st.session_state.lat, lon_key: st.session_state.lon}, method="nearest")
    current_val = float(point_data.sel(time=selected_time, method="nearest"))

    c1.metric(f"Local {param}", f"{current_val:.2f} {units.get(param, '')}")
    c2.metric("6-Mo Peak", f"{float(point_data.max()):.2f} {units.get(param, '')}")
    c3.metric("6-Mo Floor", f"{float(point_data.min()):.2f} {units.get(param, '')}")
    
    trend_df = point_data.to_dataframe().reset_index()
    csv_data = trend_df[["time", param]].to_csv(index=False).encode("utf-8")
    
    c1.download_button(
        label="📥 Export Location Data",
        data=csv_data,
        file_name=f"{param}_Lat{st.session_state.lat}_Lon{st.session_state.lon}.csv",
        mime="text/csv",
        use_container_width=True
    )

    trend_fig = px.line(
        trend_df, 
        x="time", 
        y=param, 
        markers=True, 
        title=f"Trend Profile for Lat: {st.session_state.lat:.1f}, Lon: {st.session_state.lon:.1f}"
    )
    
    trend_fig.update_traces(line=dict(color="#00ffff", width=3), marker=dict(size=8, color="#ff0055"))
    
    trend_fig.update_layout(
        height=200, 
        template="plotly_dark", 
        margin={"l": 0, "r": 0, "b": 0, "t": 30},
        xaxis_title=None,
        yaxis_title=units.get(param, ""),
        xaxis={"showgrid": False},
        yaxis={"showgrid": True, "gridcolor": "#333333"}
    )
    c4.plotly_chart(trend_fig, use_container_width=True)

except FileNotFoundError as fnf_error:
    st.error(f"⚠️ Initialization Failed: {fnf_error}")
    st.info("Please ensure 'dataset_final.nc' is pushed to the repository.")
except Exception as e:
    st.error(f"⚠️ Critical Sync Error: {e}")
