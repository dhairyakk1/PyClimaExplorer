import os
import base64
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
    
    /* Hide Streamlit Clutter BUT keep the sidebar toggle */
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    header {background-color: transparent !important;}
    
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
    
    /* BRAND LOGO CSS - SCALED DOWN */
    .brand-logo { 
        font-size: 1.6rem; 
        font-weight: 900; 
        text-align: center; 
        background: linear-gradient(45deg, #00d4ff, #ffffff); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        margin-top: 10px;
        margin-bottom: 5px; 
        letter-spacing: 1.5px; 
        text-shadow: 0px 4px 15px rgba(0, 212, 255, 0.3);
    }
    
    .sidebar-title { font-size: 1.1rem; font-weight: bold; color: #00d4ff; text-align: center; margin-bottom: 20px; letter-spacing: 2px;}
    .team-credit { text-align: center; font-size: 0.8rem; color: #555; margin-top: 50px; }
    
    hr { border-color: rgba(0, 212, 255, 0.1); }
    </style>
    """, unsafe_allow_html=True)

# 🎯 FLOATING RIGHT TEAM LOGO (Position Adjusted)
try:
    with open("logo.png", "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    st.markdown(
        f'''
        <div style="position: fixed; top: 45px; right: 45px; z-index: 9999;">
            <img src="data:image/png;base64,{data}" width="70" style="border-radius: 50%; box-shadow: 0 4px 15px rgba(0,212,255,0.4); border: 2px solid rgba(0,212,255,0.2);">
        </div>
        ''',
        unsafe_allow_html=True
    )
except FileNotFoundError:
    st.markdown(
        '''
        <div style="position: fixed; top: 45px; right: 45px; z-index: 9999; color: #00d4ff; font-weight: 800; font-size: 1rem; text-shadow: 0 0 10px rgba(0,212,255,0.5); letter-spacing: 1.5px;">
            THE POINTLESS POINTERS
        </div>
        ''',
        unsafe_allow_html=True
    )

# --- SESSION STATE INITIALIZATION ---
if "lat" not in st.session_state: st.session_state.lat = 25.3  # Varanasi
if "lon" not in st.session_state: st.session_state.lon = 83.0
if "sidebar_lat" not in st.session_state: st.session_state.sidebar_lat = 25.3
if "sidebar_lon" not in st.session_state: st.session_state.sidebar_lon = 83.0
if "city_selector" not in st.session_state: st.session_state.city_selector = "-- Select City --"

# --- 2. DATA ENGINE ---
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
    
    rename_map = {"t2m": "Temperature", "u10": "U", "v10": "V", "tp": "Precipitation"}
    ds = ds.rename({k: v for k, v in rename_map.items() if k in ds})
    
    if "U" in ds and "V" in ds:
        ds["Wind Speed"] = np.sqrt(ds.U**2 + ds.V**2)
        ds = ds.drop_vars(["U", "V"]) 
        
    return ds

try:
    ds = load_climate_data()

    # --- 3. SIDEBAR: COMMAND CENTER ---
    st.sidebar.markdown("<div class='brand-logo'>PyClimaExplorer</div>", unsafe_allow_html=True)
    st.sidebar.markdown("<div class='sidebar-title'>⚙️ COMMAND CENTER</div>", unsafe_allow_html=True)
    
    st.sidebar.markdown("**1. Data Layer**")
    param = st.sidebar.selectbox("Select Parameter", ["Temperature", "Wind Speed", "Precipitation"], label_visibility="collapsed")
    
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
    
    def handle_city_change():
        city = st.session_state.city_selector
        if city != "-- Select City --":
            st.session_state.lat, st.session_state.lon = GLOBAL_CITIES[city]
            st.session_state.sidebar_lat = st.session_state.lat
            st.session_state.sidebar_lon = st.session_state.lon

    def load_custom_coords():
        st.session_state.lat = st.session_state.sidebar_lat
        st.session_state.lon = st.session_state.sidebar_lon
        st.session_state.city_selector = "-- Select City --"
    
    st.sidebar.selectbox("Quick Jump", ["-- Select City --"] + list(GLOBAL_CITIES.keys()), key="city_selector", on_change=handle_city_change, label_visibility="collapsed")

    colA, colB = st.sidebar.columns(2)
    colA.number_input("Lat", step=0.5, key="sidebar_lat")
    colB.number_input("Lon", step=0.5, key="sidebar_lon")
    st.sidebar.button("Load", on_click=load_custom_coords, use_container_width=True)

    st.sidebar.markdown("<div class='team-credit'>Built by <b>The Pointless Pointers</b></div>", unsafe_allow_html=True)

    # --- UI & COLOR SCALES ---
    temp_scale = [[0.0, "#011959"], [0.33, "#105a96"], [0.55, "#3ba3a1"], [0.77, "#f09a39"], [1.0, "#5b0b1e"]]
    precip_scale = [[0.000, "#FFFFFF"], [0.025, "#BBDEFB"], [0.100, "#1E88E5"], [0.500, "#0D47A1"], [1.000, "#6A1B9A"]]
    cmaps = {"Temperature": temp_scale, "Wind Speed": "Viridis", "Precipitation": precip_scale}
    units = {"Temperature": "Temperature (C)", "Wind Speed": "Wind Speed (m/s)", "Precipitation": "Precipitation (mm)"}

    # Extract data slice
    data_slice = ds[param].sel(time=selected_time, method="nearest").compute()
    if param == "Temperature" and data_slice.max() > 100: data_slice = data_slice - 273.15
    if param == "Precipitation" and data_slice.max() < 0.1: data_slice = data_slice * 1000
    data_slice.name = units[param]
    
    z_min, z_max = None, None
    if param == "Temperature":
        z_min, z_max = -40, 45 
    elif param == "Precipitation":
        z_min, z_max = 0, 50  

    # --- 4. TOP SECTION: 2D MAP ---
    st.markdown(f"<h2 style='text-align: center; color: #FFFFFF; font-weight: 300; letter-spacing: 2px;'>GLOBAL <span style='color: #00d4ff; font-weight: bold;'>{param.upper()}</span> DYNAMICS</h2>", unsafe_allow_html=True)
    
    with st.container():
        fig = px.imshow(
            data_slice, x=data_slice.lon, y=data_slice.lat, 
            color_continuous_scale=cmaps.get(param, "Viridis"), origin="lower", aspect="auto",
            zmin=z_min, zmax=z_max 
        )
        
        fig.add_trace(go.Scatter(x=[st.session_state.lon], y=[st.session_state.lat], mode="markers", marker=dict(symbol="circle-open", size=8, line=dict(color="#FF0000", width=2.5)), showlegend=False, hoverinfo="skip"))
        gap, length = 1.2, 10.0 
        l_style = dict(color="#FF0000", width=1.5)
        fig.add_shape(type="line", x0=st.session_state.lon, x1=st.session_state.lon, y0=st.session_state.lat + gap, y1=st.session_state.lat + length, line=l_style)
        fig.add_shape(type="line", x0=st.session_state.lon, x1=st.session_state.lon, y0=st.session_state.lat - gap, y1=st.session_state.lat - length, line=l_style)
        fig.add_shape(type="line", x0=st.session_state.lon + gap, x1=st.session_state.lon + length, y0=st.session_state.lat, y1=st.session_state.lat, line=l_style)
        fig.add_shape(type="line", x0=st.session_state.lon - gap, x1=st.session_state.lon - length, y0=st.session_state.lat, y1=st.session_state.lat, line=l_style)
        
        cbar_settings = dict(title=dict(text=f"<b>{units[param]}</b>", font=dict(color="#00d4ff", size=14)), tickfont=dict(color="#FFF"))
        if param == "Temperature":
            cbar_settings.update({"tickmode": "linear", "tick0": 0, "dtick": 10})

        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin={"l": 0, "r": 0, "b": 0, "t": 10}, height=550, xaxis_visible=False, yaxis_visible=False, coloraxis_colorbar=cbar_settings)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 5. MIDDLE SECTION: METRICS & TREND GRAPH ---
    point_series = ds[param].sel(lat=st.session_state.lat, lon=st.session_state.lon, method="nearest").compute()
    if param == "Temperature" and point_series.max() > 100: point_series = point_series - 273.15
    if param == "Precipitation" and point_series.max() < 0.1: point_series = point_series * 1000
    
    current_val = float(point_series.sel(time=selected_time, method="nearest"))
    metric_unit = "°C" if param == "Temperature" else ("m/s" if param == "Wind Speed" else "mm")

    c_metrics, c_graph = st.columns([1, 2.5])
    with c_metrics:
        st.metric(f"TARGET {param.upper()}", f"{current_val:.1f} {metric_unit}")
        st.markdown("<br>", unsafe_allow_html=True)
        st.metric("TIMELINE PEAK", f"{float(point_series.max()):.1f} {metric_unit}")
        
    with c_graph:
        trend_df = point_series.to_dataframe().reset_index()
        trend_fig = px.line(trend_df, x="time", y=param)
        trend_fig.update_traces(line=dict(color="#00ffff", width=2), fill='tozeroy', fillcolor="rgba(0, 212, 255, 0.1)", marker=dict(size=4, color="#ff0055"))
        trend_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=260, margin={"l": 0, "r": 0, "b": 0, "t": 10}, xaxis=dict(title="", showgrid=False, tickfont=dict(color="#888")), yaxis=dict(title=units[param], showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color="#888")))
        st.plotly_chart(trend_fig, use_container_width=True)

    # --- 6. BOTTOM SECTION: 3D GLOBE PROJECTION ---
    st.markdown("<br><hr><br>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center; color: #FFFFFF; font-weight: 300; letter-spacing: 2px;'>3D PLANETARY <span style='color: #00d4ff; font-weight: bold;'>PROJECTION</span></h3>", unsafe_allow_html=True)
    
    with st.container():
        globe_fig = go.Figure()

        if param == "Precipitation":
            df = data_slice.to_dataframe().reset_index()
            val_col = units[param]
            df_rain = df[df[val_col] > 0.1] 
            
            globe_fig.add_trace(go.Scattergeo(
                lon=df_rain['lon'],
                lat=df_rain['lat'],
                marker=dict(
                    size=4,
                    color=df_rain[val_col],
                    colorscale=cmaps.get(param, "Viridis"),
                    cmin=z_min, cmax=z_max,
                    opacity=0.85
                ),
                showlegend=False, hoverinfo="skip"
            ))
            
            globe_fig.update_geos(
                projection_type="orthographic",
                projection_rotation=dict(lon=st.session_state.lon, lat=st.session_state.lat, roll=0),
                showocean=True, oceancolor="#0A1930",
                showland=True, landcolor="#FFFFFF",
                showcoastlines=True, coastlinecolor="rgba(0,0,0,0.2)",
                showlakes=False,
                bgcolor="rgba(0,0,0,0)",
                framecolor="rgba(0,0,0,0)"
            )
            
            globe_fig.add_trace(go.Scattergeo(
                lon=[st.session_state.lon],
                lat=[st.session_state.lat],
                mode="markers",
                marker=dict(size=10, color="#FF0000", line=dict(color="#FFFFFF", width=1.5)),
                showlegend=False,
                hoverinfo="skip"
            ))
            
        else:
            lon_grid, lat_grid = np.meshgrid(data_slice.lon.values, data_slice.lat.values)
            lon_rad, lat_rad = np.radians(lon_grid), np.radians(lat_grid)
            
            x_sphere = np.cos(lat_rad) * np.cos(lon_rad)
            y_sphere = np.cos(lat_rad) * np.sin(lon_rad)
            z_sphere = np.sin(lat_rad)
            
            surface_kwargs = dict(
                x=x_sphere, y=y_sphere, z=z_sphere,
                surfacecolor=data_slice.values,
                colorscale=cmaps.get(param, "Viridis"),
                showscale=False, 
                lighting=dict(ambient=0.7, diffuse=0.8, roughness=0.5, specular=0.1, fresnel=0.2)
            )
            if z_min is not None and z_max is not None:
                surface_kwargs.update({"cmin": z_min, "cmax": z_max})
                
            globe_fig.add_trace(go.Surface(**surface_kwargs))
            
            cam_x = 1.5 * np.cos(np.radians(st.session_state.lat)) * np.cos(np.radians(st.session_state.lon))
            cam_y = 1.5 * np.cos(np.radians(st.session_state.lat)) * np.sin(np.radians(st.session_state.lon))
            cam_z = 1.5 * np.sin(np.radians(st.session_state.lat))
            
            globe_fig.update_layout(
                scene=dict(
                    xaxis=dict(showbackground=False, visible=False),
                    yaxis=dict(showbackground=False, visible=False),
                    zaxis=dict(showbackground=False, visible=False),
                    bgcolor="rgba(0,0,0,0)",
                    camera=dict(eye=dict(x=cam_x, y=cam_y, z=cam_z))
                )
            )

            mx = 1.02 * np.cos(np.radians(st.session_state.lat)) * np.cos(np.radians(st.session_state.lon))
            my = 1.02 * np.cos(np.radians(st.session_state.lat)) * np.sin(np.radians(st.session_state.lon))
            mz = 1.02 * np.sin(np.radians(st.session_state.lat))
            
            globe_fig.add_trace(go.Scatter3d(
                x=[mx], y=[my], z=[mz],
                mode="markers",
                marker=dict(size=6, color="#FF0000", symbol="circle", line=dict(color="#FFFFFF", width=1)),
                showlegend=False,
                hoverinfo="skip"
            ))

        globe_fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, b=0, t=0), height=650)
        st.plotly_chart(globe_fig, use_container_width=True)

except Exception as e:
    st.error(f"System Offline: {e}")
