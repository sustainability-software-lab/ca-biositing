# audit/scripts/freeze_reference.py
import pandas as pd
from datetime import datetime
from pathlib import Path
import argparse
import sys

# Add project root to path so we can import ca_biositing and audit
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from audit.targets.registry import REGISTRY, load_adhoc_targets
from ca_biositing.datamodels.database import get_engine

def freeze_target(target_name: str, output_dir: Path):
    """
    Query the database for the given target's observations and save to a CSV
    prefixed with the current date (YYYYMMDD).
    """
    engine = get_engine()

    # Ensure all targets are loaded
    load_adhoc_targets()

    if target_name not in REGISTRY:
        print(f"❌ Target '{target_name}' not found in registry.")
        return

    target = REGISTRY[target_name]
    print(f"❄️ Freezing Target: {target_name}")

    # We use observation_sql because Golden References expect raw record granularity
    # for the most detailed Evidently reports.
    try:
        df = pd.read_sql(target.observation_sql, engine)
    except Exception as e:
        print(f"❌ Failed to query {target_name}: {e}")
        return

    datestr = datetime.now().strftime("%Y%m%d")
    output_path = output_dir / f"{datestr}_{target_name}.csv"

    df.to_csv(output_path, index=False)
    print(f"✅ Frozen {target_name} to {output_path} ({len(df)} records)")

def main():
    parser = argparse.ArgumentParser(description="Freeze database state as a Golden Reference for auditing.")
    parser.add_argument("--target", help="Name of the audit target to freeze (e.g. proximate). Use 'all' for all targets.")

    args = parser.parse_args()

    output_dir = PROJECT_ROOT / "audit" / "references"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not args.target:
        print("Error: --target is required. Use --target all or specify a target name.")
        sys.exit(1)

    if args.target == "all":
        load_adhoc_targets()
        for name in REGISTRY.keys():
            freeze_target(name, output_dir)
    else:
        freeze_target(args.target, output_dir)

if __name__ == "__main__":
    main()
