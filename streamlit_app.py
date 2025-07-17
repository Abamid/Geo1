import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import zipfile
import os
import tempfile

st.set_page_config(page_title="GeoData Fetcher", layout="wide")

st.title("🗺️ Agent 1: GeoData Fetcher")
st.markdown("Upload a shapefile (`.zip`) to visualize and inspect geologic data.")

uploaded_file = st.file_uploader(
    "Upload a zipped shapefile (.zip)", 
    type="zip", 
    help="Upload a .zip file containing .shp, .shx, .dbf, etc."
)

if uploaded_file:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, uploaded_file.name)
        
        # Save uploaded zip
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.read())

        # Extract
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(tmpdir)

        # Find the shapefile
        shp_files = [f for f in os.listdir(tmpdir) if f.endswith(".shp")]
        if not shp_files:
            st.error("No .shp file found in the uploaded zip.")
        else:
            shp_path = os.path.join(tmpdir, shp_files[0])
            try:
                gdf = gpd.read_file(shp_path)

                # Validate CRS
                if gdf.crs is None:
                    gdf.set_crs("EPSG:4326", inplace=True)  # default to WGS84

                st.success(f"Shapefile loaded: {shp_files[0]}")
                st.write(f"CRS: {gdf.crs}")
                st.write(f"Records: {len(gdf)}")
                st.dataframe(gdf.head())

                # Create map
                centroid = gdf.geometry.unary_union.centroid
                m = folium.Map(location=[centroid.y, centroid.x], zoom_start=8)

                folium.GeoJson(gdf).add_to(m)
                st_folium(m, width=1000, height=600)

            except Exception as e:
                st.error(f"Failed to read shapefile: {e}")
