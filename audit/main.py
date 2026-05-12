import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from sqlalchemy import text
from ca_biositing.datamodels.database import get_engine

# Ensure we are in the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)

def run_audit(env="local"):
    """
    Orchestrates the database audit by running modular SQL scripts.

    Args:
        env (str): The environment name for reporting purposes.
    """
    print(f"🚀 Starting Database Audit (Environment: {env})")

    # Get the engine (initialization will use current environment variables)
    engine = get_engine()
    print(f"  (Connected to: {engine.url.host}:{engine.url.port}/{engine.url.database})")

    sql_dir = Path("audit/sql")
    output_dir = Path("audit/output")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().isoformat()
    audit_results = {
        "metadata": {
            "timestamp": timestamp,
            "environment": env,
            "project": "ca-biositing",
            "database": f"{engine.url.host}:{engine.url.port}"
        },
        "modules": {}
    }

    summary_file = output_dir / "audit_summary.md"

    with summary_file.open("w") as f:
        f.write(f"# Database Audit Summary ({env})\n")
        f.write(f"Generated: {timestamp}\n")
        f.write(f"Database: {engine.url.host}:{engine.url.port}\n\n")
        f.write("---\n\n")

        # Iterate through granular SQL modules
        sql_files = sorted(list(sql_dir.glob("*.sql")))
        if not sql_files:
            print("⚠️ No SQL modules found in audit/sql/")
            return

        for sql_file in sql_files:
            module_name = sql_file.stem
            print(f"  - Running {module_name}...")

            try:
                with sql_file.open("r") as sql_f:
                    sql_content = sql_f.read()

                # Split queries by semi-colon
                raw_queries = [q.strip() for q in sql_content.split(';') if q.strip()]

                # Filter out blocks that are just comments or empty
                queries = []
                for q in raw_queries:
                    # Remove comments from the query string for the check
                    lines = q.splitlines()
                    cleaned_lines = []
                    for line in lines:
                        if not line.strip().startswith("--"):
                            # Keep line but remove inline comments
                            if "--" in line:
                                cleaned_lines.append(line.split("--")[0].strip())
                            else:
                                cleaned_lines.append(line)
                    cleaned = "\n".join(cleaned_lines).strip()
                    if cleaned:
                        queries.append(cleaned)

                module_data = []
                f.write(f"## Module: {module_name}\n\n")

                for i, query in enumerate(queries):
                    try:
                        with engine.connect() as connection:
                            result = connection.execute(text(query))

                            rows = []
                            if result.returns_rows:
                                rows = [dict(row._mapping) for row in result.fetchall()]

                            module_data.append({
                                "query_index": i,
                                "data": rows
                            })

                            # Write to summary MD
                            if rows:
                                headers = rows[0].keys()
                                f.write(f"### Result {i+1}\n\n")
                                f.write("| " + " | ".join(headers) + " |\n")
                                f.write("| " + " | ".join(["---"] * len(headers)) + " |\n")
                                for row in rows[:50]:
                                    f.write("| " + " | ".join(str(v) for v in row.values()) + " |\n")
                                if len(rows) > 50:
                                    f.write(f"\n*Truncated: showing 50 of {len(rows)} rows.*\n")
                                f.write("\n")
                            else:
                                f.write(f"### Result {i+1}\n\nCommand executed successfully.\n\n")
                    except Exception as qe:
                        f.write(f"### Result {i+1} (FAILED)\n\nError: `{qe}`\n\n")

                audit_results["modules"][module_name] = {
                    "status": "success",
                    "data": module_data
                }
                f.write("\n---\n\n")

            except Exception as e:
                print(f"  ❌ Error in {module_name}: {e}")
                audit_results["modules"][module_name] = {
                    "status": "error",
                    "error": str(e)
                }
                f.write(f"## Module: {module_name} (FAILED)\n\n")
                f.write(f"Error: `{e}`\n\n---\n\n")

    # Save structured JSON
    with (output_dir / "audit_data.json").open("w") as jf:
        json.dump(audit_results, jf, indent=2, default=str)

    print(f"\n✅ Audit complete! Results saved to {output_dir}/")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CA Biositing Database Audit Orchestrator")
    parser.add_argument("--env", default="local", help="Environment name for reporting")
    args = parser.parse_args()

    run_audit(env=args.env)
