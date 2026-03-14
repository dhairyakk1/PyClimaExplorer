# 🌍 PyClimaExplorer
**Developed by: The Pointless Pointers**

PyClimaExplorer is a high-performance climate analytics dashboard designed to visualize global environmental trends. Using ERA5-Land reanalysis data, the platform provides interactive mapping and regional time-series analysis for key climate indicators.

## 🚀 Key Features
* **Multi-Parameter Analysis:** Toggle between Temperature (°C), Wind Speed (m/s), and Total Precipitation (mm).
* **Vector Math Integration:** Real-time calculation of wind magnitude from U and V components.
* **Regional Zoom:** Point-specific 6-month trend analysis based on Latitude/Longitude coordinates.
* **Optimized Performance:** Spatial downsampling and zlib compression for a low-latency web experience.

## 🛠️ Tech Stack
* **Language:** Python
* **Data Processing:** Xarray, NumPy, Pandas
* **Visualization:** Plotly, Streamlit
* **Data Source:** Copernicus ERA5-Land Monthly Averaged (June - Nov 2025)

## Website Run
1. Open https://thepointlesspointers.streamlit.app

## 📦 Installation & Local Run
1. Clone the repo: `git clone https://github.com/dhairyakk1/PyClimaExplorer.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the app: `streamlit run app.py`