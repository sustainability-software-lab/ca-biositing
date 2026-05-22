"""
ETL Extract for Land IQ Data.


This module provides functionality for extracting Land IQ geospatial data from shapefiles.
Supports loading from a local path (Docker Compose / dev) or downloading from an HTTP URL
at runtime (Cloud Run) when LANDIQ_SHAPEFILE_URL is set.
"""

import os
import tempfile
import zipfile
from typing import Optional
import geopandas as gpd
from prefect import task, get_run_logger

# --- CONFIGURATION ---
# Default path within the repository
# Note: Users must download the Land IQ shapefile from https://www.landiq.com/land-use-mapping
# and place it in the data/landiq/ directory.
DEFAULT_SHAPEFILE_PATH = "data/landiq/i15_Crop_Mapping_2024_Provisional.shp"

# HTTP URL for downloading the shapefile in Cloud Run.
# Set to empty string or unset to disable URL download and fall back to local path.
LANDIQ_SHAPEFILE_URL = os.getenv("LANDIQ_SHAPEFILE_URL", "")


def download_shapefile(url: str, logger) -> Optional[tuple[str, str]]:
    """Download a shapefile (or zip archive containing one) from a URL.

    Returns a tuple of (shp_path, tmp_dir) on success, or None on failure.
    The caller is responsible for cleanup of tmp_dir.
    """
    import requests

    logger.info(f"Downloading LandIQ shapefile from: {url}")
    tmp_dir = tempfile.mkdtemp()

    try:
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        filename = url.split("?")[0].split("/")[-1] or "landiq_download"
        local_path = os.path.join(tmp_dir, filename)

        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Downloaded to: {local_path}")

        # If it's a zip archive, extract and find the .shp file
        if local_path.endswith(".zip") or zipfile.is_zipfile(local_path):
            logger.info("Extracting zip archive...")
            extract_dir = os.path.join(tmp_dir, "extracted")
            with zipfile.ZipFile(local_path, "r") as zf:
                zf.extractall(extract_dir)

            # Find the .shp file in the extracted contents
            shp_files = []
            for root, _, files in os.walk(extract_dir):
                for fname in files:
                    if fname.endswith(".shp"):
                        shp_files.append(os.path.join(root, fname))

            if not shp_files:
                logger.error("No .shp file found in the downloaded zip archive")
                return None

            if len(shp_files) > 1:
                logger.warning(f"Multiple .shp files found, using first: {shp_files}")

            shp_path = shp_files[0]
            logger.info(f"Found shapefile: {shp_path}")
            return shp_path, tmp_dir

        # Direct .shp download (requires companion .dbf/.shx/.prj files — unlikely via URL)
        if local_path.endswith(".shp"):
            logger.warning(
                "Downloaded a single .shp file — companion files (.dbf, .shx, .prj) "
                "may be missing. Provide a URL to a zip archive for reliable results."
            )
            return local_path, tmp_dir

        logger.error(f"Downloaded file is not a zip or shp: {local_path}")
        return None

    except Exception as e:
        logger.error(f"Failed to download shapefile from {url}: {e}", exc_info=True)
        return None


@task
def extract(shapefile_path: Optional[str] = None) -> Optional[gpd.GeoDataFrame]:
    """
    Extracts raw data from a Land IQ shapefile.

    Resolution order:
    1. `shapefile_path` argument (if provided and exists locally)
    2. `DEFAULT_SHAPEFILE_PATH` (falls back to volume-mounted file for Docker Compose)

    URL download is handled by the flow before calling this task.

    Args:
        shapefile_path: Path to the Land IQ shapefile. If None, uses default path.

    Returns:
        A geopandas GeoDataFrame containing the raw data, or None if an error occurs.
    """
    logger = get_run_logger()

    # Resolution 1: explicit path argument
    if shapefile_path and os.path.exists(shapefile_path):
        path = shapefile_path
        logger.info(f"Using provided shapefile path: {path}")
        return _read_shapefile(path, logger)

    # Resolution 2: local default path
    path = shapefile_path or DEFAULT_SHAPEFILE_PATH
    logger.info(f"Extracting Land IQ data from: {path}")

    if not os.path.exists(path):
        logger.error(f"Shapefile path does not exist: {path}")
        return None

    return _read_shapefile(path, logger)


def _read_shapefile(path: str, logger) -> Optional[gpd.GeoDataFrame]:
    """Read a shapefile with geopandas and return a GeoDataFrame."""
    try:
        gdf = gpd.read_file(path)

        if gdf is None or gdf.empty:
            logger.error(f"Extracted GeoDataFrame is empty or None from {path}")
            return None

        logger.info(f"Successfully extracted {len(gdf)} records from Land IQ shapefile.")
        logger.info(f"CRS: {gdf.crs}")
        return gdf

    except Exception as e:
        logger.error(f"Failed to extract Land IQ data: {e}", exc_info=True)
        return None
