#!/usr/bin/env python3
"""Build canonical California county geospatial assets in data/static/.

This script standardizes California's 58 county boundary geometries against
`data/static/ca_counties.csv` and enforces the project's Coordinate Reference
System (CRS / SRID) conventions:

1. **Storage & Interchange CRS (`EPSG:4326` / WGS 84, SRID 4326)**:
   - Used for `data/static/ca_counties.geojson` (RFC 7946 compliant),
     PostGIS `geometry(Geometry, 4326)` columns, and web mapping libraries
     (Plotly, MapLibre, Leaflet, Deck.gl).
   - Every GeoJSON Feature includes both a top-level `"id"` equal to its
     5-digit FIPS `geoid` (e.g., `"06099"`) and enriched `properties` matching
     `data/static/ca_counties.csv`.

2. **Planar Analysis & Cartographic Projection CRS (`EPSG:3310` / NAD83 California Albers, SRID 3310)**:
   - Equal-area conic projection tailored for California.
   - Used to compute accurate planar county areas (`area_sq_km`, `area_acres`),
     interior label placement points (`representative_point()`), and pre-projected
     SVG paths in `data/static/ca_counties_svg.json` (`viewBox="0 0 800 920"`).

Usage:
    pixi run python scripts/build_ca_counties_geo.py
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pyproj

# CRITICAL (macOS Apple Silicon): Set PROJ_LIB before importing geopandas/pyogrio
os.environ["PROJ_LIB"] = pyproj.datadir.get_data_dir()

import geopandas as gpd
import pandas as pd
from shapely.geometry import MultiPolygon, Polygon

CANONICAL_STORAGE_CRS = "EPSG:4326"
CANONICAL_STORAGE_SRID = 4326
CANONICAL_PLANAR_CRS = "EPSG:3310"
CANONICAL_PLANAR_SRID = 3310

DEFAULT_SOURCE_URL = (
    "https://raw.githubusercontent.com/codeforamerica/click_that_hood/"
    "master/public/data/california-counties.geojson"
)

SVG_WIDTH = 800.0
SVG_HEIGHT = 920.0
SVG_PADDING = 36.0

SQ_METERS_PER_SQ_KM = 1_000_000.0
SQ_METERS_PER_ACRE = 4_046.8564224


def _ring_to_svg_subpath(coords, transform_fn) -> str:
    """Convert a sequence of (x, y) planar coordinates to an SVG path command string."""
    pts = [transform_fn(x, y) for x, y in coords]
    if len(pts) < 3:
        return ""
    parts = [f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"]
    for px, py in pts[1:]:
        parts.append(f"L{px:.1f},{py:.1f}")
    parts.append("Z")
    return "".join(parts)


def geometry_to_svg_path(geom, transform_fn) -> str:
    """Convert a Shapely Polygon or MultiPolygon into an SVG path `d` attribute."""
    if geom.is_empty:
        return ""
    polygons = []
    if isinstance(geom, Polygon):
        polygons = [geom]
    elif isinstance(geom, MultiPolygon):
        polygons = list(geom.geoms)
    else:
        for sub in getattr(geom, "geoms", []):
            if isinstance(sub, (Polygon, MultiPolygon)):
                polygons.append(sub)

    subpaths = []
    for poly in polygons:
        ext = _ring_to_svg_subpath(poly.exterior.coords, transform_fn)
        if ext:
            subpaths.append(ext)
        for interior in poly.interiors:
            hole = _ring_to_svg_subpath(interior.coords, transform_fn)
            if hole:
                subpaths.append(hole)
    return " ".join(subpaths)


def build_ca_counties_assets(
    raw_geojson_path: Path,
    csv_path: Path,
    out_geojson_path: Path,
    out_svg_json_path: Path,
) -> None:
    """Build `ca_counties.geojson` (EPSG:4326) and `ca_counties_svg.json` (EPSG:3310)."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing county metadata CSV: {csv_path}")

    source_target = str(raw_geojson_path) if raw_geojson_path.exists() else DEFAULT_SOURCE_URL
    gdf = gpd.read_file(source_target)

    # 1. Repair geometries and enforce EPSG:4326 storage standard
    gdf["geometry"] = gdf["geometry"].make_valid()
    if gdf.crs is None:
        gdf = gdf.set_crs(CANONICAL_STORAGE_CRS)
    elif gdf.crs.to_string() != CANONICAL_STORAGE_CRS:
        gdf = gdf.to_crs(CANONICAL_STORAGE_CRS)

    # Normalize county_name key for joining against data/static/ca_counties.csv
    name_col = "county_name" if "county_name" in gdf.columns else "name"
    gdf["county_name_key"] = (
        gdf[name_col]
        .astype(str)
        .str.replace(" County", "", case=False, regex=False)
        .str.strip()
        .str.lower()
    )

    df_csv = pd.read_csv(csv_path, dtype=str)
    df_csv["county_name_key"] = df_csv["county_name"].str.strip().str.lower()

    merged = gdf[["county_name_key", "geometry"]].merge(
        df_csv,
        on="county_name_key",
        how="inner",
    )
    if len(merged) != 58:
        raise ValueError(f"Expected 58 California counties after join, got {len(merged)}")

    merged = gpd.GeoDataFrame(merged, geometry="geometry", crs=CANONICAL_STORAGE_CRS)
    merged = merged.sort_values("geoid").reset_index(drop=True)

    # 2. Project to EPSG:3310 (California Albers) for accurate planar area and interior points
    gdf_3310 = merged.to_crs(CANONICAL_PLANAR_CRS)
    area_m2 = gdf_3310.geometry.area
    merged["area_sq_km"] = (area_m2 / SQ_METERS_PER_SQ_KM).round(2)
    merged["area_acres"] = (area_m2 / SQ_METERS_PER_ACRE).round(1)

    rep_pts_3310 = gdf_3310.geometry.representative_point()
    rep_pts_4326 = gpd.GeoSeries(rep_pts_3310, crs=CANONICAL_PLANAR_CRS).to_crs(
        CANONICAL_STORAGE_CRS
    )
    merged["centroid_lon"] = rep_pts_4326.x.round(5)
    merged["centroid_lat"] = rep_pts_4326.y.round(5)

    merged["display_name"] = merged["county_name"].str.title()
    merged["full_name"] = merged["display_name"] + " County"
    merged["region_display"] = (
        merged["region_name"]
        .str.title()
        .str.replace("Of", "of", regex=False)
    )
    merged["srid"] = CANONICAL_STORAGE_SRID
    merged["crs"] = CANONICAL_STORAGE_CRS

    # 3. Build RFC 7946 GeoJSON with top-level feature `"id": geoid`
    property_cols = [
        "geoid",
        "county_name",
        "display_name",
        "full_name",
        "county_fips",
        "state_fips",
        "state_name",
        "agg_level_desc",
        "region_name",
        "region_display",
        "srid",
        "crs",
        "centroid_lon",
        "centroid_lat",
        "area_sq_km",
        "area_acres",
    ]
    raw_fc = json.loads(merged[property_cols + ["geometry"]].to_json())
    features = []
    for feat in raw_fc["features"]:
        geoid = feat["properties"]["geoid"]
        features.append(
            {
                "type": "Feature",
                "id": geoid,
                "properties": feat["properties"],
                "geometry": feat["geometry"],
            }
        )

    geojson_doc = {
        "type": "FeatureCollection",
        "metadata": {
            "name": "California County Boundaries (ca-biositing canonical)",
            "srid": CANONICAL_STORAGE_SRID,
            "crs": CANONICAL_STORAGE_CRS,
            "planar_measurement_srid": CANONICAL_PLANAR_SRID,
            "planar_measurement_crs": CANONICAL_PLANAR_CRS,
            "feature_count": len(features),
            "join_key": "geoid",
            "secondary_join_key": "county_name",
            "source_metadata": "data/static/ca_counties.csv",
        },
        "features": features,
    }

    out_geojson_path.parent.mkdir(parents=True, exist_ok=True)
    out_geojson_path.write_text(
        json.dumps(geojson_doc, separators=(",", ":")),
        encoding="utf-8",
    )

    # 4. Build pre-projected EPSG:3310 SVG paths & regional zoom bounding boxes
    minx, miny, maxx, maxy = gdf_3310.total_bounds
    span_x = maxx - minx
    span_y = maxy - miny
    avail_w = SVG_WIDTH - 2 * SVG_PADDING
    avail_h = SVG_HEIGHT - 2 * SVG_PADDING
    scale = min(avail_w / span_x, avail_h / span_y)
    offset_x = (SVG_WIDTH - span_x * scale) / 2.0
    offset_y = (SVG_HEIGHT - span_y * scale) / 2.0

    def to_svg_xy(x: float, y: float) -> tuple[float, float]:
        sx = offset_x + (x - minx) * scale
        sy = offset_y + (maxy - y) * scale  # Invert Y for SVG top-down coordinates
        return round(sx, 1), round(sy, 1)

    # Light topological simplification (250m in EPSG:3310) for crisp, compact SVG rendering
    gdf_3310_simp = gdf_3310.copy()
    gdf_3310_simp["geometry"] = gdf_3310_simp.geometry.simplify(
        tolerance=250.0, preserve_topology=True
    )

    counties_svg = []
    region_bounds_acc: dict[str, list[float]] = {}

    for idx, row in merged.iterrows():
        geom_3310 = gdf_3310_simp.loc[idx, "geometry"]
        rep_pt_3310 = rep_pts_3310.loc[idx]
        lx, ly = to_svg_xy(rep_pt_3310.x, rep_pt_3310.y)

        gminx, gminy, gmaxx, gmaxy = geom_3310.bounds
        bx1, by2 = to_svg_xy(gminx, gminy)
        bx2, by1 = to_svg_xy(gmaxx, gmaxy)
        bbox = [
            round(min(bx1, bx2), 1),
            round(min(by1, by2), 1),
            round(abs(bx2 - bx1), 1),
            round(abs(by2 - by1), 1),
        ]

        rname = row["region_name"]
        if rname not in region_bounds_acc:
            region_bounds_acc[rname] = [
                min(bx1, bx2),
                min(by1, by2),
                max(bx1, bx2),
                max(by1, by2),
            ]
        else:
            rb = region_bounds_acc[rname]
            rb[0] = min(rb[0], min(bx1, bx2))
            rb[1] = min(rb[1], min(by1, by2))
            rb[2] = max(rb[2], max(bx1, bx2))
            rb[3] = max(rb[3], max(by1, by2))

        svg_path = geometry_to_svg_path(geom_3310, to_svg_xy)
        counties_svg.append(
            {
                "geoid": row["geoid"],
                "county_name": row["county_name"],
                "display_name": row["display_name"],
                "full_name": row["full_name"],
                "county_fips": row["county_fips"],
                "region_name": rname,
                "region_display": row["region_display"],
                "centroid_lon": float(row["centroid_lon"]),
                "centroid_lat": float(row["centroid_lat"]),
                "area_sq_km": float(row["area_sq_km"]),
                "area_acres": float(row["area_acres"]),
                "label_x": lx,
                "label_y": ly,
                "bbox": bbox,
                "svg_path": svg_path,
            }
        )

    def _format_region_box(x1: float, y1: float, x2: float, y2: float, pad: float = 28.0) -> dict:
        vx = max(0.0, round(x1 - pad, 1))
        vy = max(0.0, round(y1 - pad, 1))
        vw = min(SVG_WIDTH - vx, round((x2 - x1) + 2 * pad, 1))
        vh = min(SVG_HEIGHT - vy, round((y2 - y1) + 2 * pad, 1))
        return {
            "bbox": [vx, vy, vw, vh],
            "viewBox": f"{vx:.1f} {vy:.1f} {vw:.1f} {vh:.1f}",
        }

    regions_meta = {
        "statewide": {
            "display_name": "California (Statewide)",
            "bbox": [0.0, 0.0, SVG_WIDTH, SVG_HEIGHT],
            "viewBox": f"0 0 {int(SVG_WIDTH)} {int(SVG_HEIGHT)}",
        }
    }
    for rname, (x1, y1, x2, y2) in sorted(region_bounds_acc.items()):
        rbox = _format_region_box(x1, y1, x2, y2, pad=32.0)
        regions_meta[rname] = {
            "display_name": rname.title(),
            **rbox,
        }

    # Add combined Central Valley bounding box
    cv_regions = [
        "sacramento valley",
        "north san joaquin valley",
        "south san joaquin valley",
    ]
    cv_coords = [region_bounds_acc[r] for r in cv_regions if r in region_bounds_acc]
    if cv_coords:
        cv_x1 = min(c[0] for c in cv_coords)
        cv_y1 = min(c[1] for c in cv_coords)
        cv_x2 = max(c[2] for c in cv_coords)
        cv_y2 = max(c[3] for c in cv_coords)
        regions_meta["central valley"] = {
            "display_name": "Central Valley (All)",
            **_format_region_box(cv_x1, cv_y1, cv_x2, cv_y2, pad=30.0),
        }

    svg_doc = {
        "metadata": {
            "name": "California Counties Pre-Projected SVG Paths (EPSG:3310 California Albers)",
            "storage_srid": CANONICAL_STORAGE_SRID,
            "storage_crs": CANONICAL_STORAGE_CRS,
            "projection_srid": CANONICAL_PLANAR_SRID,
            "projection_crs": CANONICAL_PLANAR_CRS,
            "viewBox": f"0 0 {int(SVG_WIDTH)} {int(SVG_HEIGHT)}",
            "width": SVG_WIDTH,
            "height": SVG_HEIGHT,
            "county_count": len(counties_svg),
        },
        "regions": regions_meta,
        "counties": counties_svg,
    }

    out_svg_json_path.write_text(
        json.dumps(svg_doc, separators=(",", ":")),
        encoding="utf-8",
    )
    print(
        f"Built {out_geojson_path} ({out_geojson_path.stat().st_size:,} bytes, {CANONICAL_STORAGE_CRS})"
    )
    print(
        f"Built {out_svg_json_path} ({out_svg_json_path.stat().st_size:,} bytes, projected via {CANONICAL_PLANAR_CRS})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-geojson",
        type=Path,
        default=Path("/tmp/ca_counties_raw.geojson"),
        help="Path to raw California counties GeoJSON (falls back to existing ca_counties.geojson or remote URL)",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("data/static/ca_counties.csv"),
        help="Path to canonical California counties CSV lookup",
    )
    parser.add_argument(
        "--out-geojson",
        type=Path,
        default=Path("data/static/ca_counties.geojson"),
        help="Output path for canonical EPSG:4326 GeoJSON",
    )
    parser.add_argument(
        "--out-svg-json",
        type=Path,
        default=Path("data/static/ca_counties_svg.json"),
        help="Output path for EPSG:3310 pre-projected SVG JSON",
    )
    args = parser.parse_args()

    raw_source = args.raw_geojson
    if not raw_source.exists() and args.out_geojson.exists():
        raw_source = args.out_geojson

    build_ca_counties_assets(
        raw_geojson_path=raw_source,
        csv_path=args.csv,
        out_geojson_path=args.out_geojson,
        out_svg_json_path=args.out_svg_json,
    )


if __name__ == "__main__":
    main()
