import os
import streamlit as st
import xarray as xr
import plotly.express as px
import pandas as pd
import numpy as np

# --- 1. UI CONFIGURATION ---
st.set_page_config(layout="wide", page_title="The Pointless Pointers | Climate Suite")

st.markdown("""
    <style>
    .main { background-color: #0E1117; color: #FFFFFF; }
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
    file_path = "dataset_final.nc"
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Missing core data file: {file_path}")
        
    ds = xr.open_dataset(file_path)
    
    # 1. UNIVERSAL TIME FINDER
    time_name = None
    for coord in ds.coords:
        if "time" in str(coord).lower():
            time_name = coord
            break
    
    if time_name and time_name != "time":
        ds = ds.rename({time_name: "time"})

    # 2. Map variables to friendly names
    rename_map = {"t2m": "Temp", "u10": "U", "v10": "V", "tp": "Precip"}
    ds = ds.rename({k: v for k, v in rename_map.items() if k in ds})
    
    # 3. Handle Conversions & Memory Optimization
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
    lat_in = st.sidebar.number_input("Latitude", value=20.5, step=0.5)
    lon_in = st.sidebar.number_input("Longitude", value=78.9, step=0.5)

    # --- 3. TOP SECTION: MAP (80% Height) ---
    if param not in ds:
        st.error(f"Parameter '{param}' not found in the dataset.")
        st.stop()
        
    data_slice = ds[param].sel(time=selected_time, method="nearest")
    
    cmaps = {"Temp": "RdYlBu_r", "Wind Speed": "Viridis", "Precip": "Blues"}
    units = {"Temp": "°C", "Wind Speed": "m/s", "Precip": "mm"}

    fig = px.imshow(
        data_slice,
        color_continuous_scale=cmaps.get(param, "Viridis"),
        origin="lower",
        title=f"Global {param} Map ({units.get(param, '')}) - {selected_time.strftime('%B %Y')}",
        aspect="auto"
    )
    
    fig.update_layout(
        template="plotly_dark",
        margin={"l": 10, "r": 10, "b": 0, "t": 50},
        height=540,
        xaxis={"showgrid": False, "zeroline": False},
        yaxis={"showgrid": False, "zeroline": False}
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 4. BOTTOM SECTION: STATS & TREND (20% Height) ---
    st.divider()
    c1, c2, c3, c4 = st.columns([1, 1, 1, 3])
    
    point_data = ds[param].sel(latitude=lat_in, longitude=lon_in, method="nearest")
    current_val = float(point_data.sel(time=selected_time, method="nearest"))

    c1.metric(f"Local {param}", f"{current_val:.2f} {units.get(param, '')}")
    c2.metric("6-Mo Peak", f"{float(point_data.max()):.2f}")
    c3.metric("6-Mo Floor", f"{float(point_data.min()):.2f}")
    
    trend_df = point_data.to_dataframe().reset_index()
    csv_data = trend_df[["time", param]].to_csv(index=False).encode("utf-8")
    
    c1.download_button(
        label="📥 Export CSV",
        data=csv_data,
        file_name=f"{param}_Lat{lat_in}_Lon{lon_in}.csv",
        mime="text/csv",
        use_container_width=True
    )

    trend_fig = px.line(
        trend_df, 
        x="time", 
        y=param, 
        markers=True, 
        title=f"Regional Trend Profile: ({lat_in}, {lon_in})"
    )
    
    trend_fig.update_layout(
        height=200, 
        template="plotly_dark", 
        margin={"l": 0, "r": 0, "b": 0, "t": 30},
        xaxis_title=None,
        yaxis_title=units.get(param, ""),
        xaxis={"showgrid": False}
    )
    c4.plotly_chart(trend_fig, use_container_width=True)

except FileNotFoundError as fnf_error:
    st.error(f"⚠️ Initialization Failed: {fnf_error}")
    st.info("Please ensure 'dataset_final.nc' is pushed to the repository.")
except Exception as e:
    st.error(f"⚠️ Critical Sync Error: {e}")
