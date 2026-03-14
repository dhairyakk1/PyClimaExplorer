import os
import streamlit as st
import xarray as xr
import plotly.express as px
import pandas as pd
import numpy as np

# --- 1. UI CONFIGURATION ---
st.set_page_config(layout="wide", page_title="The Pointless Pointers | Climate Suite")

# Professional Dark Mode CSS (Responsive & Clean)
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #FFFFFF; }
    /* Soften the scrollbar instead of completely hiding overflow for better compatibility */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #00d4ff; font-weight: bold; }
    .stPlotlyChart { margin-bottom: -15px; }
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def load_data():
    file_path = 'dataset_final.nc'
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Missing core data file: {file_path}")
        
    ds = xr.open_dataset(file_path)
    
    # 1. UNIVERSAL TIME FINDER
    time_name = None
    for coord in ds.coords:
        if 'time' in coord.lower():
            time_name = coord
            break
    
    if time_name and time_name != 'time':
        ds = ds.rename({time_name: 'time'})

    # 2. Map variables to friendly names
    rename_map = {'t2m': 'Temp', 'u10': 'U', 'v10': 'V', 'tp': 'Precip'}
    ds = ds.rename({k: v for k, v in rename_map.items() if k in ds})
    
    # 3. Handle Conversions & Memory Optimization
    if 'Temp' in ds and ds['Temp'].max() > 100: 
        ds['Temp'] = ds['Temp'] - 273.15
            
    if 'U' in ds and 'V' in ds:
        ds['Wind Speed'] = np.sqrt(ds.U**2 + ds.V**2)
        ds = ds.drop_vars(['U', 'V']) # Free up RAM
        
    if 'Precip' in ds and ds['Precip'].max() < 1: 
        ds['Precip'] = ds['Precip'] * 1000
        
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
                                             format_func=lambda x: x.strftime('%b %Y'))

    st.sidebar.divider()
    st.sidebar.subheader("📍 Regional Focus")
    lat_in = st.sidebar.number_input("Latitude", value=20.5, step=0.5)
    lon_in = st.sidebar.number_input("Longitude", value=78.9, step=0.5)

    # --- 3. TOP SECTION: MAP (80% Height) ---
    # Ensure param exists in dataset before plotting
    if param not in ds:
        st.error(f"Parameter '{param}' not found in the dataset.")
        st.stop()
        
    data_slice = ds[param].sel(time=selected_time, method='nearest')
    
    cmaps = {"Temp": "RdYlBu_r", "Wind Speed": "Viridis", "Precip": "Blues"}
    units = {"Temp": "°C", "Wind Speed": "m/s", "Precip": "mm"}

    fig = px.imshow(
        data_slice,
        color_continuous_scale=cmaps[param],
        origin='lower',
        title=f"Global {param} Map ({units[param]}) - {selected_time.strftime('%B %Y')}",
        aspect='auto'
    )
    
    # Clean map aesthetics (removing gridlines)
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=10, r=10, b=0, t=50),
        height=
