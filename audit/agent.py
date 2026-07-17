import pandas as pd
from pathlib import Path
from datetime import datetime
import json
from typing import List, Dict, Optional, Tuple

from audit.config import settings, load_yaml_config
from audit.targets.registry import REGISTRY, AuditTarget
from audit.skills.statistical_profiling import run_statistical_profiling
from audit.skills.evidently_engine import run_evidently_profile
from audit.skills.data_quality_assertions import run_data_quality_assertions
from audit.skills.llm_synthesis import run_llm_synthesis
from audit.skills.analyst_report import generate_analyst_report
from audit.skills.executive_summary import generate_executive_summary
from audit.skills.anomaly_tracker import write_anomaly_tracker, write_raw_anomaly_tracker
from audit.skills.deep_dives import (
    audit_provider_deep_dive,
    audit_resource_deep_dive,
    audit_analysis_type_review,
    audit_temporal_drift,
)

# Import the database engine utility from the datamodels package
from ca_biositing.datamodels.database import get_engine
from sqlalchemy import create_engine
from datetime import date

class AuditorAgent:
    def __init__(self, targets: Optional[List[str]] = None, config_path: Optional[str] = None, profile: bool = False, verbose: bool = False):
        self.profile = profile
        self.reference_root = Path("audit/references")
        self.verbose = verbose
        if config_path:
            global settings
            settings = load_yaml_config(config_path)

        self.targets = targets or list(REGISTRY.keys())
        self.audit_date = date.today().isoformat()   # "YYYY-MM-DD"
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        if settings.STAGING_DATABASE_URL:
            self.engine = create_engine(settings.STAGING_DATABASE_URL, echo=False)
        else:
            self.engine = get_engine()

        self.output_dir = Path(settings.OUTPUT_ROOT) / self.timestamp
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "profiles").mkdir(exist_ok=True)
        (self.output_dir / "evidently").mkdir(exist_ok=True)

    def run(self):
        print(f"🚀 Starting Data Audit: {self.timestamp}")

        target_results = []
        global_sheet_url = ""

        for target_name in self.targets:
            if target_name not in REGISTRY:
                print(f"⚠️ Target {target_name} not found in registry. Skipping.")
                continue

            target = REGISTRY[target_name]
            print(f"🔍 Auditing Target: {target_name}")

            # 1. Fetch Data
            # Check for Golden Reference
            ref_path = self.reference_root / f"{target_name}.csv"
            is_golden = False
            if ref_path.exists():
                print(f"  🏆 Using Golden Reference: {ref_path}")
                pop_df = pd.read_csv(ref_path)
                is_golden = True
            else:
                pop_df = pd.read_sql(target.population_sql, self.engine)

            obs_df = pd.read_sql(target.observation_sql, self.engine)

            # 2. Skill 1: Statistical Profiling (Gated by --profile)
            profile_summary = {}
            if self.profile:
                print("📊 Running statistical profiling...")
                profile_summary = run_statistical_profiling(
                    obs_df, target_name, self.output_dir / "profiles"
                )

            # 3. Skill 2: Outlier Detection (Evidently AI)
            print("📍 Detecting outliers with Evidently AI...")
            report_json, flagged = run_evidently_profile(
                population_df=pop_df,
                observation_df=obs_df,
                target_name=target_name,
                output_dir=self.output_dir / "evidently",
                group_cols=target.group_by_cols,
                is_golden_reference=is_golden
            )

            # 4. Skill 3: GX Assertions
            gx_result = {}
            if target.gx_suite_path and Path(target.gx_suite_path).exists():
                print("✅ Running DQ assertions...")
                gx_result = run_data_quality_assertions(obs_df, target.gx_suite_path)

            # 5. Skill 4: LLM Synthesis (Structured Output)
            synthesis = None
            try:
                print("🧠 Running LLM synthesis...")
                synthesis = run_llm_synthesis(
                    target_name=target_name,
                    flagged=flagged,
                    evidently_json=report_json,
                    model=settings.LLM_MODEL
                )
            except Exception as e:
                print(f"⚠️ LLM synthesis failed for {target_name}: {e}")

            # Save LLM synthesis as JSON
            if synthesis:
                llm_path = self.output_dir / f"llm_synthesis_{target_name}.json"
                with open(llm_path, "w") as f:
                    f.write(synthesis.model_dump_json(indent=2))

            # Save flagged observations as CSV (Backend data)
            raw_csv_path = ""
            if flagged:
                flagged_df = pd.DataFrame([vars(f) for f in flagged])
                csv_file = self.output_dir / f"flagged_{target_name}.csv"
                flagged_df.to_csv(csv_file, index=False)
                raw_csv_path = str(csv_file)

            # Skill 6: Anomaly Tracker (Grouped & Raw)
            sheet_url = ""
            if settings.ANOMALY_TRACKER_SHEET_KEY and flagged:
                try:
                    print("📋 Writing to Anomaly Tracker...")
                    # 1. Write Grouped Issues
                    grouped_issues = synthesis.grouped_issues if synthesis else []
                    sheet_url = write_anomaly_tracker(
                        grouped_issues=grouped_issues,
                        target_name=target_name,
                        audit_date=self.audit_date,
                        audit_run_id=self.timestamp,
                        sheet_key=settings.ANOMALY_TRACKER_SHEET_KEY,
                        credentials_path=settings.ANOMALY_TRACKER_CREDENTIALS,
                        evidently_report_url=f"evidently/{target_name}.html",
                        raw_csv_path=raw_csv_path,
                        worksheet_name=settings.ANOMALY_TRACKER_WORKSHEET,
                    )

                    # 2. Write Raw Anomalies
                    write_raw_anomaly_tracker(
                        flagged=flagged,
                        target_name=target_name,
                        audit_date=self.audit_date,
                        audit_run_id=self.timestamp,
                        sheet_key=settings.ANOMALY_TRACKER_SHEET_KEY,
                        credentials_path=settings.ANOMALY_TRACKER_CREDENTIALS,
                        worksheet_name="Raw Anomalies"
                    )

                    global_sheet_url = sheet_url
                    print(f"  ✅ Anomaly Tracker updated: {sheet_url}")
                except Exception as e:
                    print(f"  ⚠️ Anomaly Tracker write failed: {e}")

            # 6. Store results for Executive Summary
            evidently_html_rel_path = f"evidently/{target_name}.html"
            target_results.append({
                "target_name": target_name,
                "synthesis": synthesis,
                "flagged_count": len(flagged) if flagged else 0,
                "evidently_html_path": evidently_html_rel_path,
                "gx_pass_count": gx_result.get("statistics", {}).get("successful_expectations", 0),
                "gx_fail_count": gx_result.get("statistics", {}).get("unsuccessful_expectations", 0)
            })

            # Skill 5: Generate Detailed Report (only if --verbose)
            if self.verbose:
                print(f"📝 Generating detailed analyst report for {target_name}...")
                llm_exec = synthesis.executive_summary if synthesis else ""
                report_md = generate_analyst_report(
                    target_name=target_name,
                    flagged_observations=flagged,
                    llm_synthesis=llm_exec,
                    sheet_url=sheet_url,
                    zscore_threshold=settings.ZSCORE_THRESHOLD,
                    min_group_size=settings.MIN_GROUP_SIZE
                )
                target_report_path = self.output_dir / f"report_{target_name}.md"
                target_report_path.write_text(report_md)

        # Final Skill: Executive Summary
        print("🏛️ Generating Executive Audit Summary...")
        summary_path = generate_executive_summary(
            target_results=target_results,
            output_dir=self.output_dir,
            sheet_url=global_sheet_url
        )

        if global_sheet_url:
            print(f"📊 Anomaly Tracker: {global_sheet_url}")

        print(f"✅ Audit Complete. Results in: {self.output_dir}")

    def freeze_references(self):
        print(f"❄️ Freezing Golden References to {self.reference_root}")
        self.reference_root.mkdir(parents=True, exist_ok=True)

        for target_name in self.targets:
            if target_name not in REGISTRY:
                continue
            target = REGISTRY[target_name]
            print(f"  📦 Freezing {target_name}...")
            # We use observation_sql as the "golden" snapshot of compliant data
            df = pd.read_sql(target.observation_sql, self.engine)
            df.to_csv(self.reference_root / f"{target_name}.csv", index=False)
        print("✅ Golden References frozen successfully.")

if __name__ == "__main__":
    import argparse
    import audit.targets.views  # Trigger registration

    parser = argparse.ArgumentParser(description="CA Biositing Auditor Agent")
    parser.add_argument("--profile", action="store_true", help="Run full statistical profiling (ydata-profiling)")
    parser.add_argument("--verbose", action="store_true", help="Generate detailed per-target Markdown reports")
    parser.add_argument("--targets", nargs="+", help="Specific targets to audit")
    parser.add_argument("--deep-dive", choices=["provider", "resource", "analysis-type", "temporal"], help="Run a targeted deep-dive")
    parser.add_argument("--value", help="Value for deep-dive (provider codename, resource name, or analysis type)")
    parser.add_argument("--target", help="Target name for temporal deep-dive")
    parser.add_argument("--run-dir", help="Path to a previous audit run directory (optional, defaults to latest)")
    parser.add_argument("--freeze-reference", action="store_true", help="Freeze current data as golden reference CSVs")
    args = parser.parse_args()

    if args.freeze_reference:
        agent = AuditorAgent(targets=args.targets)
        agent.freeze_references()
    elif args.deep_dive:
        # Determine run_dir if not provided
        if not args.run_dir:
            output_root = Path(settings.OUTPUT_ROOT)
            runs = sorted([d for d in output_root.iterdir() if d.is_dir()], reverse=True)
            if not runs:
                print(f"❌ No audit runs found in {settings.OUTPUT_ROOT}")
                exit(1)
            run_dir = str(runs[0])
        else:
            run_dir = args.run_dir

        if args.deep_dive == "provider":
            if not args.value:
                print("❌ --value <provider_codename> is required for provider deep-dive")
                exit(1)
            audit_provider_deep_dive(args.value, run_dir)
        elif args.deep_dive == "resource":
            if not args.value:
                print("❌ --value <resource_name> is required for resource deep-dive")
                exit(1)
            audit_resource_deep_dive(args.value, run_dir)
        elif args.deep_dive == "analysis-type":
            if not args.value:
                print("❌ --value <analysis_type> is required for analysis-type review")
                exit(1)
            audit_analysis_type_review(args.value, run_dir)
        elif args.deep_dive == "temporal":
            if not args.target:
                print("❌ --target <target_name> is required for temporal drift analysis")
                exit(1)
            audit_temporal_drift(args.target, run_dir)
    else:
        agent = AuditorAgent(targets=args.targets, profile=args.profile, verbose=args.verbose)
        agent.run()
