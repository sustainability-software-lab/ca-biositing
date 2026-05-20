"""Type coercion helpers for ETL: ints, floats, datetimes, booleans, categories, geometry."""
from typing import Iterable, Optional
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def _coerce_int(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    return df


def _coerce_float(df: pd.DataFrame, cols: Iterable[str], float_dtype=np.float64) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            # Force conversion to string to handle any mixed types or weird objects
            # Then remove commas and whitespace
            s = df[c].astype(str)
            # Remove commas
            s = s.str.replace(",", "", regex=False)
            # Remove currency symbols
            s = s.str.replace("$", "", regex=False)
            # Remove all whitespace
            s = s.str.replace(r"\s+", "", regex=True)
            # Replace various null-like strings with actual NaN
            s = s.replace(["", "nan", "None", "NaN", "null"], np.nan)

            # Convert to numeric
            df[c] = pd.to_numeric(s, errors="coerce").astype(float_dtype)
    return df


def _coerce_datetime(df: pd.DataFrame, cols: Iterable[str], **kwargs) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", **kwargs)
    return df


def _coerce_bool(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    mapping = {
        True: True,
        False: False,
        "true": True,
        "false": False,
        "1": True,
        "0": False,
        "yes": True,
        "no": False,
        "y": True,
        "n": False,
    }
    for c in cols:
        if c in df.columns:
            # Convert to lowercase if string to match mapping
            if df[c].dtype == "object":
                df[c] = df[c].str.lower()
            df[c] = df[c].map(mapping).astype("boolean")
    return df


def _coerce_category(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype("category")
    return df


def _coerce_geometry(df: pd.DataFrame, cols: Iterable[str], geom_format: str = "wkt") -> pd.DataFrame:
    """Coerce geometry columns to shapely geometry objects.

    Supports:
    - 'wkt': WKT (Well-Known Text) strings converted via shapely
    - 'geodataframe': assumes columns are already GeoSeries from geopandas (no conversion needed)
    """
    if geom_format == "geodataframe":
        # Columns are already geometry type from geopandas; no conversion needed
        logger.info(f"Geometry columns {list(cols)} are already GeoSeries; skipping coercion")
        return df

    try:
        from shapely import wkt
    except ImportError:
        logger.warning("shapely not available; geometry coercion skipped")
        return df

    for c in cols:
        if c in df.columns:
            df[c] = df[c].apply(lambda v: wkt.loads(v) if isinstance(v, str) and v.strip() else None)
    return df


def coerce_columns(
    df: pd.DataFrame,
    int_cols: Optional[Iterable[str]] = None,
    float_cols: Optional[Iterable[str]] = None,
    datetime_cols: Optional[Iterable[str]] = None,
    bool_cols: Optional[Iterable[str]] = None,
    category_cols: Optional[Iterable[str]] = None,
    geometry_cols: Optional[Iterable[str]] = None,
    dtype_map: Optional[dict] = None,
    float_dtype=np.float64,
    geometry_format: str = "wkt",
) -> pd.DataFrame:
    """Coerce groups of columns to target types.

    `dtype_map` may be provided as an alternative mapping with keys like 'int','float','datetime','bool','category','geometry'.
    Explicit keyword lists take precedence over `dtype_map` entries.

    `geometry_format` controls how geometry columns are coerced:
    - 'wkt': parse WKT strings using shapely (default)
    - 'geodataframe': skip coercion (columns already GeoSeries from geopandas)
    """
    if not isinstance(df, pd.DataFrame):
        logger.error("coerce_columns: input is not a DataFrame")
        return df
    df = df.copy()
    if dtype_map:
        int_cols = int_cols or dtype_map.get("int") or dtype_map.get("integer")
        float_cols = float_cols or dtype_map.get("float")
        datetime_cols = datetime_cols or dtype_map.get("datetime") or dtype_map.get("date")
        bool_cols = bool_cols or dtype_map.get("bool")
        category_cols = category_cols or dtype_map.get("category")
        geometry_cols = geometry_cols or dtype_map.get("geometry")

    if int_cols:
        df = _coerce_int(df, int_cols)
    if float_cols:
        df = _coerce_float(df, float_cols, float_dtype)
    if datetime_cols:
        df = _coerce_datetime(df, datetime_cols)
    if bool_cols:
        df = _coerce_bool(df, bool_cols)
    if category_cols:
        df = _coerce_category(df, category_cols)
    if geometry_cols:
        df = _coerce_geometry(df, geometry_cols, geom_format=geometry_format)

    return df


def coerce_columns_list(dfs: Iterable[pd.DataFrame], **coerce_kwargs) -> list:
    """Apply `coerce_columns` to each DataFrame in `dfs` and return a list of results.

    Non-DataFrame items are preserved with a warning.
    """
    out = []
    for i, df in enumerate(dfs):
        if not isinstance(df, pd.DataFrame):
            logger.warning(f"Item {i} is not a DataFrame; skipping")
            out.append(df)
            continue
        out.append(coerce_columns(df.copy(), **coerce_kwargs))
    return out
