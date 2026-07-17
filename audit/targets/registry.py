import importlib
import pkgutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List

@dataclass
class AuditTarget:
    name: str                          # e.g. "mv_biomass_composition"
    source_type: str                   # "view" or "table"
    description: str
    population_sql: str                # Layer 1: group-level stats
    observation_sql: str               # Layer 2: individual records with record_id
    group_by_cols: List[str]           # Audit grain, e.g. ["resource_name", "parameter_name", "unit"]
    numeric_cols: List[str]            # Columns to run outlier detection on
    id_cols: List[str]                 # Columns identifying a specific record
    analyst_col: Optional[str] = None  # Column linking to analyst email
    gx_suite_path: Optional[str] = None
    use_isolation_forest: bool = False  # True for multivariate views (fermentation, gasification)

# Phase 1 registry — views only
REGISTRY: Dict[str, AuditTarget] = {}

def register(target: AuditTarget) -> None:
    REGISTRY[target.name] = target

def load_adhoc_targets():
    """
    Dynamically discover and register audit targets in the adhoc directory.
    """
    adhoc_dir = Path(__file__).parent / "adhoc"
    if not adhoc_dir.exists():
        return

    for _, name, is_pkg in pkgutil.iter_modules([str(adhoc_dir)]):
        if is_pkg or name == "__init__":
            continue

        module_name = f"audit.targets.adhoc.{name}"
        try:
            importlib.import_module(module_name)
        except Exception as e:
            print(f"⚠️ Failed to load adhoc target module {module_name}: {e}")
