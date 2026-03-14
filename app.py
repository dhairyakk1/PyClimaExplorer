import streamlit as st
import xarray as xr
import plotly.express as px
import pandas as pd
import numpy as np

# --- 1. UI CONFIGURATION ---
st.set_page_config(layout="wide", page_title="The Pointless Pointers | Climate Suite")

# Professional Dark Mode CSS (No-Scroll logic)
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #FFFFFF; }
    .stApp { height: 100vh; overflow: hidden; } 
    [data-testid="stMetricValue"] { font-size: 1.6rem; color: #00d4ff; }
    .stPlotlyChart { margin-bottom: -20px; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    ds = xr.open_dataset('dataset_final.nc')
    
    # 1. Map variables to friendly names
    rename_map = {'t2m': 'Temp', 'u10': 'U', 'v10': 'V', 'tp': 'Precip'}
    ds = ds.rename({k: v for k, v in rename_map.items() if k in ds})
    
    # 2. Conversions
    if 'Temp' in ds:
        if ds['Temp'].max() > 100: ds['Temp'] = ds['Temp'] - 273.15
    if 'U' in ds and 'V' in ds:
        ds['Wind Speed'] = np.sqrt(ds.U**2 + ds.V**2)
    if 'Precip' in ds:
        # Convert to mm if it's in meters
        if ds['Precip'].max() < 1: ds['Precip'] = ds['Precip'] * 1000
        
    return ds

try:
    ds = load_data()

    # --- 2. SIDEBAR (The "Cockpit") ---
    st.sidebar.header("🛠️ Analysis Controls")
    param = st.sidebar.selectbox("Select Parameter", ["Temp", "Wind Speed", "Precip"])
    
    time_coords = pd.to_datetime(ds.time.values)
    selected_time = st.sidebar.select_slider("Select Month", 
                                             options=time_coords, 
                                             format_func=lambda x: x.strftime('%b %Y'))

    st.sidebar.divider()
    st.sidebar.subheader("📍 Regional Focus")
    # Defaulting to India coordinates
    lat_in = st.sidebar.number_input("Latitude", value=20.5, step=0.5)
    lon_in = st.sidebar.number_input("Longitude", value=78.9, step=0.5)

    # --- 3. TOP SECTION: THE MAP (80% Area) ---
    data_slice = ds[param].sel(time=selected_time, method='nearest')
    
    cmaps = {"Temp": "RdYlBu_r", "Wind Speed": "Viridis", "Precip": "Blues"}
    units = {"Temp": "°C", "Wind Speed": "m/s", "Precip": "mm"}

    fig = px.imshow(
        data_slice,
        color_continuous_scale=cmaps[param],
        origin='lower',
        title=f"Global {param} Map ({units[param]})",
        aspect='auto'
    )
    
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=10, r=10, b=0, t=40),
        height=520 
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 4. BOTTOM SECTION: ANALYTICS (20% Area) ---
    st.divider()
    c1, c2, c3, c4 = st.columns([1, 1, 1, 4])
    
    # Fetch data for the specific point
    point_data = ds[param].sel(latitude=lat_in, longitude=lon_in, method='nearest')
    current_val = float(point_data.sel(time=selected_time))

    c1.metric(f"Current {param}", f"{current_val:.2f} {units[param]}")
    c2.metric("6-Mo High", f"{float(point_data.max()):.2f}")
    c3.metric("6-Mo Low", f"{float(point_data.min()):.2f}")

    # Trend Line Chart
    trend_df = point_data.to_dataframe().reset_index()
    trend_fig = px.line(trend_df, x='time', y=param, markers=True, 
                        title=f"6-Month Trend at Lat: {lat_in}, Lon: {lon_in}")
    trend_fig.update_layout(height=180, template="plotly_dark", margin=dict(l=0, r=0, b=0, t=30))
    c4.plotly_chart(trend_fig, use_container_width=True)

except Exception as e:
    st.error(f"Waiting for dataset... Error: {e}")