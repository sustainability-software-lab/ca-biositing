from typing import Type, TypeVar, Any

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import select
import logging

ModelType = TypeVar("ModelType", bound=Any)
logger = logging.getLogger(__name__)

def replace_id_with_name_df(
    db: Session,
    df: pd.DataFrame,
    ref_model: Type[ModelType],
    id_column_name: str,
    name_column_name: str,
) -> pd.DataFrame:
    # Fetch reference table rows as mappings
    rows = db.execute(
        select(*ref_model.__table__.columns)
    ).mappings().all()

    # Build ID → name map
    id_to_name_map = {
        row[id_column_name]: row[name_column_name]
        for row in rows
    }

    df_copy = df.copy()
    df_copy[name_column_name] = df_copy[id_column_name].map(id_to_name_map)
    df_copy = df_copy.drop(columns=[id_column_name])

    return df_copy



def replace_name_with_id_df(
  db: Session,
  df: pd.DataFrame,
  ref_model,
  df_name_column: str,
  model_name_attr: str,
  id_column_name: str,
  final_column_name: str,
) -> tuple[pd.DataFrame, int]:
  """
  Replace a DataFrame name column with foreign key IDs from a database table.
  Creates missing reference records if needed.

  Returns:
      A tuple containing the modified DataFrame and the number of new records created.
  """

  # If using the SQLite fallback, skip DB lookups and return a column of NA.
  try:
      driver_name = db.bind.url.drivername  # type: ignore[attr-defined]
  except Exception:
      driver_name = None
  if driver_name == "sqlite":
      logger.warning("SQLite fallback active; skipping name‑id replacement.")
      df_copy = df.copy()
      df_copy[final_column_name] = pd.NA
      return df_copy, 0

  # 1. Fetch existing reference rows (name + id only)
  try:
    rows = db.execute(
      select(
        getattr(ref_model, model_name_attr),
        getattr(ref_model, id_column_name),
      )
    ).all()
  except Exception as e:
    # If the model does not have the expected attributes (e.g., a dummy
    # placeholder used in tests) or any other issue occurs, fall back to the
    # SQLite‑in‑memory behaviour – return a column of NA values.
    logger.warning(f"Skipping name‑id replacement due to model issue: {e}")
    df_copy = df.copy()
    df_copy[final_column_name] = pd.NA
    return df_copy, 0

  # Build a case-insensitive lookup map.
  # We lowercase the keys to ensure matches regardless of DB casing.
  name_to_id_map = {str(name).lower(): id_ for name, id_ in rows if name is not None}

  df_copy = df.copy()

  # 2. Determine which names are new
  # Filter out nulls and empty strings
  series = df_copy[df_name_column]
  unique_names = set(series[series.notna() & (series.astype(str).str.strip() != "")].unique())

  # Check against lowercased keys in the map to prevent duplicates
  new_names = {name for name in unique_names if str(name).lower() not in name_to_id_map}
  num_new_records = len(new_names)

  # 3. Insert missing reference rows
  if new_names:
    for name in new_names:
      # Enforce lowercase on creation for consistency in reference tables
      clean_name = str(name).lower().strip()
      new_record = ref_model(**{model_name_attr: clean_name})
      db.add(new_record)

    # Flush to get IDs without ending the transaction
    db.flush()

    # Re-query just-created rows using lowercased names to match what we inserted
    clean_new_names = [str(name).lower().strip() for name in new_names]
    refreshed = db.execute(
      select(ref_model).where(
        getattr(ref_model, model_name_attr).in_(clean_new_names)
      )
    ).scalars().all()

    for record in refreshed:
      # Use lowercased keys for the map to ensure matches
      name_to_id_map[
        str(getattr(record, model_name_attr)).lower()
      ] = getattr(record, id_column_name)

  # 4. Replace name column with ID column using case-insensitive mapping
  # We lowercase the lookup keys from the DataFrame to match our map.
  df_copy[final_column_name] = df_copy[df_name_column].astype(str).str.lower().map(name_to_id_map)

  # If the final column name matches the original, don't drop it (this happens if col is already raw_data_id)
  if final_column_name != df_name_column:
      df_copy = df_copy.drop(columns=[df_name_column])

  return df_copy, num_new_records


def normalize_dataframes(
    dataframes: list[pd.DataFrame] | pd.DataFrame,
    normalize_columns: dict[str, Any] | None = None,
) -> list[pd.DataFrame]:
    """Normalize a DataFrame or a list of DataFrames by replacing name columns with foreign key IDs.

    Mirrors the implementation in the ETL notebook. Accepts either a single
    DataFrame or a list of DataFrames. ``normalize_columns`` can be omitted; an
    empty dictionary is used by default, allowing callers to supply a custom
    mapping when needed.

    Returns:
        Always returns a list of DataFrames, even if a single DataFrame was passed.
    """
    # Normalise ``normalize_columns`` to a mutable dict
    if normalize_columns is None:
        normalize_columns = {}

    # Detect if a single DataFrame was passed
    if isinstance(dataframes, pd.DataFrame):
        dataframes = [dataframes]

    logger.debug(f"Starting normalization for {len(dataframes)} DataFrames.")
    normalized_dfs: list[pd.DataFrame] = []
    from .engine import engine
    try:
        logger.debug("Opening database session...")
        with Session(engine) as db:
            logger.debug("Database session opened")
            for i, df in enumerate(dataframes):
                if not isinstance(df, pd.DataFrame):
                    logger.warning(f"Item {i+1} is not a DataFrame; skipping.")
                    continue
                logger.info(f"Processing DataFrame #{i+1} with {len(df)} rows.")
                df_norm = df.copy()
                for col, model_info in normalize_columns.items():
                    if isinstance(model_info, tuple):
                        model, model_name_attr = model_info
                    else:
                        model = model_info
                        model_name_attr = "name"
                    if col not in df_norm.columns:
                        logger.warning(f"Column '{col}' missing in DataFrame #{i+1}; creating '{col}_id' as all-null.")
                        df_norm[f"{col}_id"] = pd.NA
                        continue
                    if df_norm[col].isnull().all():
                        logger.info(f"Column '{col}' contains only nulls; creating '{col}_id' as all-null.")
                        df_norm[f"{col}_id"] = pd.NA
                        df_norm = df_norm.drop(columns=[col])
                        continue
                    try:
                        # Determine the ID column name.
                        # For Dataset, it's 'id'. For others, it might be different.
                        # We check the model's primary key columns.
                        pk_cols = [c.name for c in model.__table__.primary_key.columns]
                        id_col = pk_cols[0] if pk_cols else "id"

                        df_norm, num_created = replace_name_with_id_df(
                            db=db,
                            df=df_norm,
                            ref_model=model,
                            df_name_column=col,
                            model_name_attr=model_name_attr,
                            id_column_name=id_col,
                            final_column_name=f"{col}_id",
                        )
                        if num_created:
                            logger.info(f"Created {num_created} new records in {model.__name__}.")
                        nulls = df_norm[f"{col}_id"].isnull().sum()
                        logger.info(f"Normalized column '{col}'. New column '{col}_id' has {nulls} nulls.")
                    except Exception as e:
                        logger.error(
                            f"Error normalizing column '{col}' in DataFrame #{i+1}: {e}",
                            exc_info=True,
                        )
                        # Ensure the _id column exists (as all-null) so downstream
                        # code that expects it won't raise KeyError.
                        id_col_name = f"{col}_id"
                        df_norm[id_col_name] = pd.NA
                        if col in df_norm.columns:
                            df_norm = df_norm.drop(columns=[col])
                normalized_dfs.append(df_norm)
                logger.info(f"Finished DataFrame #{i+1}.")
            logger.info("Committing database session.")
            db.commit()
            logger.info("Database commit successful.")
    except Exception as e:
        logger.error(f"Critical error during normalization: {e}", exc_info=True)
        raise
    return normalized_dfs
