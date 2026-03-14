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
    .main { background-color: #0E1117; color: #FFFFFF; }
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-thumb { background: #00d4ff; border-radius: 4px; }
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #00d4ff; font-weight: bold; }
    .stPlotlyChart { margin-bottom: -15px; }
    header {visibility: hidden;}
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
    
    # Universal Time Finder
    time_name = next((c for c in ds.coords if "time" in str(c).lower()), None)
    if time_name and time_name != "time":
        ds = ds.rename({time_name: "time"})

    # Map variables to friendly names
    rename_map = {"t2m": "Temp", "u10": "U", "v10": "V", "tp": "Precip"}
    ds = ds.rename({k: v for k, v in rename_map.items() if k in ds})
    
    # Conversions
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
    st.sidebar.subheader("📍 Regional Focus")
    st.sidebar.markdown("<span style='color:#a8b2c1; font-size:0.9em;'><i>Click map or adjust sliders:</i></span>", unsafe_allow_html=True)
    
    lat_in = st.sidebar.number_input("Latitude", value=st.session_state.lat, step=0.5, key="sidebar_lat", on_change=sync_sidebar)
    lon_in = st.sidebar.number_input("Longitude", value=st.session_state.lon, step=0.5, key="sidebar_lon", on_change=sync_sidebar)

    # --- 3. CUSTOM COLOR SCALES (TEAMMATE'S UPGRADE) ---
    temp_custom_scale = [
        [0.0, "#00008B"],   # -40C: Dark Blue
        [0.28, "#87CEEB"],  # -15C: Sky Blue (transition)
        [0.44, "#FFFFFF"],  # 0C: Pure White
        [0.61, "#FFFF00"],  # 15C: Yellow
        [0.83, "#FFA500"],  # 35C: Orange
        [1.0, "#FF0000"]    # 50C: Total Red
    ]

    cmaps = {"Temp": temp_custom_scale, "Wind Speed": "Viridis", "Precip": "Blues"}
    units = {"Temp": "°C", "Wind Speed": "m/s", "Precip": "mm"}

    # --- 4. TOP SECTION: MAP (80% Height) ---
    if param not in ds:
        st.error(f"Parameter '{param}' not found in the dataset.")
        st.stop()
        
    data_slice = ds[param].sel(time=selected_time, method="nearest")
    
    # Range Locks for Consistency
    z_min, z_max = (-40, 50) if param == "Temp" else (None, None)

    fig = px.imshow(
        data_slice,
        color_continuous_scale=cmaps.get(param, "Viridis"),
        origin="lower",
        title=f"Global {param} Map ({units.get(param, '')}) - {selected_time.strftime('%B %Y')}",
        aspect="auto",
        zmin=z_min,
        zmax=z_max
    )
    
    # 🎯 HIGH-TECH TARGET RETICLE (RESTORED)
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
        margin={"l": 10, "r": 10, "b": 0, "t": 50},
        height=540,
        xaxis={"showgrid": False, "zeroline": False, "visible": False}, 
        yaxis={"showgrid": False, "zeroline": False, "visible": False}, 
        coloraxis_colorbar=dict(title=units.get(param, "")),
        hovermode="closest"
    )
    
    # 🖱️ CAPTURING THE CLICK EVENT (RESTORED)
    map_event = st.plotly_chart(
        fig, 
        use_container_width=True, 
        on_select="rerun",       
        selection_mode="points"  
    )

    if map_event and map_event.selection and map_event.selection.points:
        clicked_lon = float(map_event.selection.points[0]["x"])
        clicked_lat = float(map_event.selection.points[0]["y"])
        
        if clicked_lon != st.session_state.lon or clicked_lat != st.session_state.lat:
            st.session_state.lon = clicked_lon
            st.session_state.lat = clicked_lat
            st.toast(f"Target Acquired: Lat {clicked_lat:.1f}, Lon {clicked_lon:.1f}", icon="🎯")
            st.rerun()

    # --- 5. BOTTOM SECTION: STATS & TREND (20% Height) ---
    st.divider()
    c1, c2, c3, c4 = st.columns([1, 1, 1, 3])
    
    # Teammate's robust coordinate checker
    lat_key = 'lat' if 'lat' in ds.coords else 'latitude'
    lon_key = 'lon' if 'lon' in ds.coords else 'longitude'
    
    # Fetching data using the session state variables
    point_data = ds[param].sel({lat_key: st.session_state.lat, lon_key: st.session_state.lon}, method="nearest")
    current_val = float(point_data.sel(time=selected_time, method="nearest"))

    c1.metric(f"Local {param}", f"{current_val:.2f} {units.get(param, '')}")
    c2.metric("6-Mo Peak", f"{float(point_data.max()):.2f}")
    c3.metric("6-Mo Floor", f"{float(point_data.min()):.2f}")
    
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
