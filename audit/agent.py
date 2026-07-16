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
from audit.skills.anomaly_tracker import write_anomaly_tracker

# Import the database engine utility from the datamodels package
from ca_biositing.datamodels.database import get_engine
from sqlalchemy import create_engine
from datetime import date

class AuditorAgent:
    def __init__(self, targets: Optional[List[str]] = None, config_path: Optional[str] = None, profile: bool = False):
        self.profile = profile
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

        all_reports = []
        sheet_url = None

        for target_name in self.targets:
            if target_name not in REGISTRY:
                print(f"⚠️ Target {target_name} not found in registry. Skipping.")
                continue

            target = REGISTRY[target_name]
            print(f"🔍 Auditing Target: {target_name}")

            # 1. Fetch Data
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
                group_cols=target.group_by_cols
            )

            # Skill 6: Anomaly Tracker
            sheet_url = None
            if settings.ANOMALY_TRACKER_SHEET_KEY and flagged:
                try:
                    print("📋 Writing to Anomaly Tracker...")
                    # Note: write_anomaly_tracker update will be handled in Task 4/5,
                    # but we keep it here as per Task 3 instructions to pass synthesis results if available.
                    sheet_url = write_anomaly_tracker(
                        flagged=flagged,
                        target_name=target_name,
                        audit_date=self.audit_date,
                        audit_run_id=self.timestamp,
                        sheet_key=settings.ANOMALY_TRACKER_SHEET_KEY,
                        credentials_path=settings.ANOMALY_TRACKER_CREDENTIALS,
                        worksheet_name=settings.ANOMALY_TRACKER_WORKSHEET,
                    )
                    print(f"  ✅ Anomaly Tracker updated: {sheet_url}")
                except Exception as e:
                    print(f"  ⚠️ Anomaly Tracker write failed: {e}")

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

            # 6. Skill 5: Generate Report
            print("📝 Generating analyst report...")
            llm_executive_summary = synthesis.executive_summary if synthesis else ""
            report_md = generate_analyst_report(
                target_name=target_name,
                flagged_observations=flagged,
                llm_synthesis=llm_executive_summary,
                sheet_url=sheet_url,
                zscore_threshold=settings.ZSCORE_THRESHOLD,
                min_group_size=settings.MIN_GROUP_SIZE
            )

            # Save individual target report
            target_report_path = self.output_dir / f"report_{target_name}.md"
            target_report_path.write_text(report_md)
            all_reports.append(report_md)

            # Save flagged observations as CSV
            if flagged:
                flagged_df = pd.DataFrame([vars(f) for f in flagged])
                flagged_df.to_csv(self.output_dir / f"flagged_{target_name}.csv", index=False)

        # Final aggregate report
        final_report_path = self.output_dir / "full_audit_report.md"
        final_report_path.write_text("\n\n".join(all_reports))

        if sheet_url:
            print(f"📊 Anomaly Tracker: {sheet_url}")

        print(f"✅ Audit Complete. Results in: {self.output_dir}")

if __name__ == "__main__":
    import argparse
    import audit.targets.views  # Trigger registration

    parser = argparse.ArgumentParser(description="CA Biositing Auditor Agent")
    parser.add_argument("--profile", action="store_true", help="Run full statistical profiling (ydata-profiling)")
    parser.add_argument("--targets", nargs="+", help="Specific targets to audit")
    args = parser.parse_args()

    agent = AuditorAgent(targets=args.targets, profile=args.profile)
    agent.run()
