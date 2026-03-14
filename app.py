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
    
    time_name = next((c for c in ds.coords if "time" in str(c).lower()), None)
    if time_name and time_name != "time":
        ds = ds.rename({time_name: "time"})

    rename_map = {"t2m": "Temp", "u10": "U", "v10": "V", "tp": "Precip"}
    ds = ds.rename({k: v for k, v in rename_map.items() if k in ds})
    
    if "Temp" in ds and ds["Temp"].max() > 100: 
        ds["Temp"] = ds["Temp"] - 273.15
            
    if "U" in ds and "V" in ds:
        ds["Wind Speed"] = np.sqrt(ds.U**2 + ds.V**2)
        ds = ds.drop_vars(["U", "V"]) 
        
    if "Precip" in ds and ds["Precip"].max() < 1: 
        ds["Precip"] = ds["Precip"] * 1000 # Convert to mm
        
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

    # --- 3. CUSTOM COLOR SCALES & LOGIC ---
    # TEMPERATURE: ICON Weather Model Match (-40 to 50)
    temp_custom_scale = [
        [0.000, "#011959"],  # Deep Arctic Blue (-40°C)
        [0.333, "#105a96"],  # Ocean Blue (-10°C)
        [0.444, "#3ba3a1"],  # Teal/Cyan (0°C)
        [0.556, "#a3d977"],  # Pale Yellow-Green (10°C)
        [0.667, "#f5d448"],  # Golden Yellow (20°C)
        [0.778, "#f09a39"],  # Deep Orange (30°C)
        [0.889, "#c12128"],  # Crimson Red (40°C)
        [1.000, "#5b0b1e"]   # Dark Burgundy/Purple (50°C+)
    ]

    # PRECIPITATION: Teammate's Capped 0-120mm Scale
    precip_custom_scale = [
        [0.0, "#FFFFFF"],    # 0 mm (White)
        [0.083, "#E0F7FA"],  # 10 mm
        [0.166, "#B2EBF2"],  # 20 mm
        [0.25, "#80DEEA"],   # 30 mm
        [0.333, "#4DD0E1"],  # 40 mm
        [0.416, "#26C6DA"],  # 50 mm
        [0.5, "#00BCD4"],    # 60 mm
        [0.583, "#00ACC1"],  # 70 mm
        [0.666, "#0097A7"],  # 80 mm
        [0.75, "#00838F"],   # 90 mm
        [0.833, "#006064"],  # 100 mm 
        [0.916, "#01579B"],  # 110 mm
        [1.0, "#0D47A1"]     # 120 mm (Darkest Blue)
    ]

    cmaps = {"Temp": temp_custom_scale, "Wind Speed": "Viridis", "Precip": precip_custom_scale}
    units = {"Temp": "°C", "Wind Speed": "m/s", "Precip": "mm"}

    # --- 4. TOP SECTION: MAP ---
    if param not in ds:
        st.error(f"Parameter '{param}' not found in the dataset.")
        st.stop()
        
    data_slice = ds[param].sel(time=selected_time, method="nearest")
    
    # Scaling logic locks
    if param == "Temp":
        z_min, z_max = (-40, 50)
    elif param == "Precip":
        z_min, z_max = (0, 120) 
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
    
    # TARGET RETICLE
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
        plot_bgcolor="rgba(0,0,0,0)", # Transparent oceans!
        paper_bgcolor="rgba(0,0,0,0)",
        margin={"l": 10, "r": 10, "b": 0, "t": 50},
        height=540,
        xaxis={"showgrid": False, "zeroline": False, "visible": False}, 
        yaxis={"showgrid": False, "zeroline": False, "visible": False}, 
        coloraxis_colorbar=dict(
            title=units.get(param, ""),
            tickvals=list(range(0, 121, 10)) if param == "Precip" else None
        ),
        hovermode="closest"
    )
    
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
