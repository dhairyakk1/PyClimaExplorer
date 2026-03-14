import streamlit as st
import xarray as xr
import plotly.express as px
import pandas as pd
import numpy as np

# --- 1. UI CONFIGURATION ---
st.set_page_config(layout="wide", page_title="The Pointless Pointers | Climate Suite")

# Professional Dark Mode CSS (Forces everything into one screen)
st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #FFFFFF; }
    .stApp { height: 100vh; overflow: hidden; } 
    [data-testid="stMetricValue"] { font-size: 1.6rem; color: #00d4ff; }
    .stPlotlyChart { margin-bottom: -15px; }
    /* Hide Streamlit header/footer for a cleaner look */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    # Ensure this matches your filename on GitHub
    ds = xr.open_dataset('dataset_final.nc')
    
    # 1. UNIVERSAL TIME FINDER (Fixes the 'AttributeError')
    time_name = None
    for coord in ds.coords:
        if 'time' in coord.lower():
            time_name = coord
            break
    
    if time_name and time_name != 'time':
        ds = ds.rename({time_name: 'time'})

    # 2. Map variables to friendly names (ERA5 standard names)
    rename_map = {'t2m': 'Temp', 'u10': 'U', 'v10': 'V', 'tp': 'Precip'}
    ds = ds.rename({k: v for k, v in rename_map.items() if k in ds})
    
    # 3. Handle Conversions
    if 'Temp' in ds:
        # If in Kelvin, convert to Celsius
        if ds['Temp'].max() > 100: 
            ds['Temp'] = ds['Temp'] - 273.15
            
    if 'U' in ds and 'V' in ds:
        # Calculate Wind Magnitude (Vector Math)
        ds['Wind Speed'] = np.sqrt(ds.U**2 + ds.V**2)
        
    if 'Precip' in ds:
        # Convert meters to millimeters if necessary
        if ds['Precip'].max() < 1: 
            ds['Precip'] = ds['Precip'] * 1000
        
    return ds

try:
    ds = load_data()

    # --- 2. SIDEBAR CONTROLS ---
    st.sidebar.title("🛠️ Pointless Pointers")
    param = st.sidebar.selectbox("Select Parameter", ["Temp", "Wind Speed", "Precip"])
    
    # Timeline Logic
    time_coords = pd.to_datetime(ds.time.values)
    selected_time = st.sidebar.select_slider("Select Month", 
                                             options=time_coords, 
                                             format_func=lambda x: x.strftime('%b %Y'))

    st.sidebar.divider()
    st.sidebar.subheader("📍 Regional Analytics")
    # Default to India center
    lat_in = st.sidebar.number_input("Latitude", value=20.5, step=0.5)
    lon_in = st.sidebar.number_input("Longitude", value=78.9, step=0.5)

    # --- 3. TOP SECTION: MAP (80% Height) ---
    data_slice = ds[param].sel(time=selected_time, method='nearest')
    
    cmaps = {"Temp": "RdYlBu_r", "Wind Speed": "Viridis", "Precip": "Blues"}
    units = {"Temp": "°C", "Wind Speed": "m/s", "Precip": "mm"}

    fig = px.imshow(
        data_slice,
        color_continuous_scale=cmaps[param],
