"""Basic cleaning helpers: name normalization, empty->NA, lowercase, and a small composed pipeline.

These functions are intended to be small, well-documented, and easy to test.
"""
from typing import Iterable, Optional
import logging
import pandas as pd
import numpy as np
# Import janitor to register the ``clean_names`` accessor on DataFrames
import janitor  # noqa: F401

logger = logging.getLogger(__name__)


def clean_names_df(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of `df` with cleaned column names using `janitor.clean_names()`.

    If `df` is not a DataFrame, the original value is returned and an error is logged.
    """
    if not isinstance(df, pd.DataFrame):
        logger.error("clean_names_df: input is not a DataFrame")
        return df
    # janitor.clean_names normalizes casing, removes punctuation/spaces, and converts to snake_case
    return df.clean_names()


def replace_empty_with_na(df: pd.DataFrame, columns: Optional[Iterable[str]] = None, regex: str = r"^\s*$") -> pd.DataFrame:
    """Replace empty/whitespace-only strings with `np.nan`.

    Args:
        df: input DataFrame
        columns: optional iterable of column names to process; if None operate on whole frame
        regex: regex used to identify empty/whitespace strings

    Returns:
        A new DataFrame with replacements applied.
    """
    if not isinstance(df, pd.DataFrame):
        logger.error("replace_empty_with_na: input is not a DataFrame")
        return df
    if columns is None:
        return df.astype("object").replace(regex, np.nan, regex=True)
    df = df.copy()
    cols = [c for c in columns if c in df.columns]
    if not cols:
        logger.warning("replace_empty_with_na: no matching columns found; returning original DataFrame")
        return df
    df[cols] = df[cols].astype("object").replace(regex, np.nan, regex=True)
    return df


def to_lowercase_df(
    df: pd.DataFrame,
    columns: Optional[Iterable[str]] = None,
    exclude: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """Lowercase string columns.

    Converts selected columns (or all string-like columns) to pandas `string` dtype, then applies
    `.str.lower()`. Missing values are preserved.

    Args:
        df: input DataFrame
        columns: optional iterable of column names to process; if None operate on all string-like columns
        exclude: optional iterable of column names to exclude from lowercasing
    """
    if not isinstance(df, pd.DataFrame):
        logger.error("to_lowercase_df: input is not a DataFrame")
        return df
    df = df.copy()
    if columns is None:
        str_cols = df.select_dtypes(include=["object", "string"]).columns
    else:
        str_cols = [c for c in columns if c in df.columns]

    if exclude is not None:
        str_cols = [c for c in str_cols if c not in exclude]

    for c in str_cols:
        df[c] = df[c].astype("string").str.lower().where(df[c].notna(), df[c])
    return df


def standard_clean(
    df: pd.DataFrame,
    lowercase: bool = True,
    replace_empty: bool = True,
    exclude_lowercase: Optional[Iterable[str]] = None,
) -> Optional[pd.DataFrame]:
    """Run a composed standard cleaning pipeline and return a cleaned DataFrame.

    Steps:
      1. `clean_names_df`
      2. `replace_empty_with_na` (optional)
      3. `to_lowercase_df` (optional, can exclude specific columns)
      4. `convert_dtypes()` to allow pandas to pick improved nullable dtypes
    """
    if not isinstance(df, pd.DataFrame):
        logger.error("standard_clean: input is not a DataFrame")
        return None
    df = clean_names_df(df)
    # Handle duplicate columns that might arise from name cleaning (e.g. 'Col A' and 'col_a' both becoming 'col_a')
    if df.columns.duplicated().any():
        logger.warning(
            f"standard_clean: duplicate columns found after name cleaning: {df.columns[df.columns.duplicated()].unique().tolist()}. Keeping first occurrence."
        )
        df = df.loc[:, ~df.columns.duplicated()]
    if replace_empty:
        df = replace_empty_with_na(df)
    if lowercase:
        df = to_lowercase_df(df, exclude=exclude_lowercase)
    df = df.convert_dtypes()
    return df
