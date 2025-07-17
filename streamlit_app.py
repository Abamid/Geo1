import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import matplotlib
import os
import tempfile
from zipfile import ZipFile

st.set_page_config(layout="wide")
st.title("🛰️ Agent 1: GeoData Fetcher")

st.markdown("""
Upload a shapefile (as `.zip`) to visualize and inspect geologic data.
This map will serve as the base layer for future analysis.
""")

uploaded_file = st.file_uploader("Upload a zipped shapefile (.zip)", type="zip")

if uploaded_file:
    with st.spinner("⏳ Unzipping and loading shapefile..."):
        try:
            # Use a temporary directory for safe extraction
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "shapefile.zip")

                # Save zip file to temp path
                with open(zip_path, "wb") as f:
                    f.write(uploaded_file.read())

                # Extract
                with ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)

                # Find .shp file
                shp_path = None
                for root, dirs, files in os.walk(tmpdir):
                    for file in files:
                        if file.endswith(".shp"):
                            shp_path = os.path.join(root, file)
                            break

                if not shp_path:
                    st.error("❌ Shapefile (.shp) not found in archive!")
                else:
                    # Load into GeoDataFrame
                    gdf = gpd.read_file(shp_path)

                    # Reproject to WGS84
                    gdf = gdf.to_crs(epsg=4326)

                    # Simplify geometry if complex
                    gdf["geometry"] = gdf["geometry"].simplify(0.0001, preserve_topology=True)

                    # Use "GLG" or first column
                    label_col = "GLG" if "GLG" in gdf.columns else gdf.columns[0]

                    unique_units = gdf[label_col].unique()
                    cmap = matplotlib.colormaps.get_cmap('tab20')
                    colors = [matplotlib.colors.rgb2hex(cmap(i / len(unique_units))) for i in range(len(unique_units))]
                    unit_color_dict = dict(zip(unique_units, colors))

                    # Map center
                    bounds = gdf.total_bounds
                    center_lat = (bounds[1] + bounds[3]) / 2
                    center_lon = (bounds[0] + bounds[2]) / 2

                    # Create map
                    m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles=None)
                    folium.TileLayer("OpenStreetMap", name="Street Map").add_to(m)
                    folium.TileLayer("Stamen Terrain", name="Terrain", attr="Map tiles by Stamen Design").add_to(m)
                    folium.TileLayer(
                        tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
                        attr="Map data © Google",
                        name="Satellite"
                    ).add_to(m)

                    # Add polygons
                    for unit in unique_units:
                        sub_gdf = gdf[gdf[label_col] == unit]
                        color = unit_color_dict[unit]
                        gj = folium.GeoJson(
                            sub_gdf,
                            style_function=lambda feature, color=color: {
                                'fillColor': color,
                                'color': 'black',
                                'weight': 0.5,
                                'fillOpacity': 0.6
                            },
                            tooltip=folium.GeoJsonTooltip(fields=[label_col], aliases=["Unit:"]),
                            popup=folium.GeoJsonPopup(fields=[label_col]),
                            name=unit
                        )
                        gj.add_to(m)

                    folium.LayerControl(collapsed=False).add_to(m)

                    st.markdown("### 🌍 Interactive Geological Map")
                    st_data = st_folium(m, width=1000, height=600)

                    # Export HTML for download
                    html_path = os.path.join(tmpdir, "map.html")
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(m.get_root().render())

                    with open(html_path, "rb") as f:
                        st.download_button(
                            label="💾 Download Map as HTML",
                            data=f,
                            file_name="geology_map.html",
                            mime="text/html"
                        )
        except Exception as e:
            st.error(f"⚠️ Error loading shapefile: {e}")
