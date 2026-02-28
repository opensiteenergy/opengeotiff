import os
import sys
import yaml
import requests
import rasterio
import zipfile
import glob
from urllib.parse import urlparse, unquote, urldefrag
import re
import geopandas as gpd
from rasterio.mask import mask as riomask
from rasterio.features import shapes
from rasterio.enums import Resampling
from shapely.geometry import mapping

class OpenGeoTIFF:
    def __init__(self, config_path):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Defragment the URL to separate the link from the #target-file
        self.raw_source = self.config['source']
        self.source, self.target_internal_file = urldefrag(self.raw_source)
        
        self.cache_dir = self.config['cache_dir']
        self.clipping_path = self.config['clipping']
        self.output_name = self.config['output']
        self.val_min = self.config['mask']['min']
        self.val_max = self.config['mask']['max']
        
        os.makedirs(self.cache_dir, exist_ok=True)

    def run(self):
        # 1. Sanitize filename for local storage
        # Strips query params so we don't get 'file?url=...' as a filename
        parsed_url = urlparse(self.source)
        clean_name = os.path.basename(unquote(parsed_url.path))
        
        # Specific fix for Solargis/Atlas redirect links
        if 'url=' in self.source:
            match = re.search(r'([^/&?]+\.zip)', self.source)
            if match:
                clean_name = match.group(1)

        local_path = os.path.join(self.cache_dir, clean_name)

        # 2. Download
        if not os.path.exists(local_path):
            print(f"[*] Downloading: {clean_name}")
            r = requests.get(self.source, stream=True)
            r.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        # 3. Handle ZIP Extraction
        final_tif = local_path
        if zipfile.is_zipfile(local_path):
            extract_folder = local_path.replace('.zip', '_extracted')
            if not os.path.exists(extract_folder):
                with zipfile.ZipFile(local_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_folder)
            
            # Find the TIF
            tifs = glob.glob(os.path.join(extract_folder, "**/*.tif"), recursive=True)
            
            if self.target_internal_file:
                # Look for the specific file mentioned after the #
                matches = [f for f in tifs if self.target_internal_file.lower() in f.lower()]
                if matches:
                    final_tif = matches[0]
                    print(f"[*] Found target file: {os.path.basename(final_tif)}")
                else:
                    print(f"[!] Warning: {self.target_internal_file} not found. Falling back to largest TIF.")
                    final_tif = max(tifs, key=os.path.getsize)
            else:
                # Default to largest if no fragment provided
                final_tif = max(tifs, key=os.path.getsize)

        # 4. Raster Processing (Clipping & Masking)
        print(f"[*] Filtering values ({self.val_min}-{self.val_max})...")
        with rasterio.open(final_tif) as src:
            clip_gdf = gpd.read_file(self.clipping_path).to_crs(src.crs)
            geoms = [mapping(g) for g in clip_gdf.geometry]

            # Use nodata=0 or another safe value to avoid leakage
            out_image, out_transform = riomask(src, geoms, crop=True, nodata=0)
            data = out_image[0] 

            # 2. MASKING (Second step)
            # Now we apply the 0-1000 threshold to the ALREADY clipped data
            # We specifically ignore the 0 (NoData) from the clip step
            mask_condition = (data >= self.val_min) & (data <= self.val_max) & (data != 0)
            binary_mask = mask_condition.astype('int16')

            # 3. VECTORIZING
            # Converting the clean binary mask to GeoPackage shapes
            results = (
                {'properties': {'value': v}, 'geometry': s}
                for i, (s, v) in enumerate(shapes(binary_mask, mask=(binary_mask == 1), transform=out_transform))
            )

            gdf = gpd.GeoDataFrame.from_features(list(results), crs=src.crs)
            # Apply slight simplification to fix 'coarseness'
            gdf['geometry'] = gdf['geometry'].simplify(0.005, preserve_topology=True)
            gdf.to_file(self.output_name, driver="GPKG")
            print(f"[+] Done: {self.output_name}")

def main():
    # Check if a config file was provided
    if len(sys.argv) < 2:
        print("Usage: opengeotiff <config.yml>")
        sys.exit(1)

    config_path = sys.argv[1]
    
    # Check if the file actually exists
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)

    # Initialize and run
    app = OpenGeoTIFF(config_path)
    app.run()

if __name__ == "__main__":
    main()