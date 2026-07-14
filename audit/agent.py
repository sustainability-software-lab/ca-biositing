import pandas as pd
from pathlib import Path
from datetime import datetime
import json
from typing import List, Dict, Optional

from audit.config import settings
from audit.targets.registry import REGISTRY, AuditTarget
from audit.skills.statistical_profiling import run_statistical_profiling
from audit.skills.grouped_outlier_detection import detect_grouped_outliers
from audit.skills.data_quality_assertions import run_data_quality_assertions
from audit.skills.semantic_review import semantic_review
from audit.skills.analyst_report import generate_analyst_report
from audit.skills.anomaly_tracker import write_anomaly_tracker

# Import the database engine utility from the datamodels package
from ca_biositing.datamodels.database import get_engine
from sqlalchemy import create_engine
from datetime import date

class AuditorAgent:
    def __init__(self, targets: Optional[List[str]] = None):
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

            # 2. Skill 1: Statistical Profiling
            print("📊 Running statistical profiling...")
            profile_summary = run_statistical_profiling(
                obs_df, target_name, self.output_dir / "profiles"
            )

            # 3. Skill 2: Outlier Detection
            print("📍 Detecting outliers...")
            flagged = detect_grouped_outliers(
                pop_df, obs_df,
                group_cols=target.group_by_cols,
                zscore_threshold=settings.ZSCORE_THRESHOLD,
                min_group_size=settings.MIN_GROUP_SIZE
            )

            # Skill 6: Anomaly Tracker
            sheet_url = None
            if settings.ANOMALY_TRACKER_SHEET_KEY and flagged:
                try:
                    print("📋 Writing to Anomaly Tracker...")
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

            # 5. Skill 4: Semantic Review (LLM)
            llm_assessments = {}
            try:
                print("🧠 Running semantic review...")
                llm_assessments = semantic_review(
                    target_name, flagged, profile_summary, gx_result,
                    model=settings.LLM_MODEL,
                    max_tokens=settings.LLM_MAX_TOKENS
                )
            except Exception as e:
                print(f"⚠️ Semantic review failed for {target_name}: {e}")

            # Save LLM assessments
            if llm_assessments:
                llm_path = self.output_dir / f"llm_assessments_{target_name}.json"
                with open(llm_path, "w") as f:
                    json.dump(llm_assessments, f, indent=2)

            # 6. Skill 5: Generate Report
            print("📝 Generating analyst report...")
            report_md = generate_analyst_report(
                target_name, flagged, llm_assessments,
                zscore_threshold=settings.ZSCORE_THRESHOLD,
                min_group_size=settings.MIN_GROUP_SIZE
            )

            # Save individual target report
            target_report_path = self.output_dir / f"report_{target_name}.html"
            target_report_path.write_text(report_md)
            all_reports.append(report_md)

            # Save flagged observations as CSV
            if flagged:
                flagged_df = pd.DataFrame([vars(f) for f in flagged])
                flagged_df.to_csv(self.output_dir / f"flagged_{target_name}.csv", index=False)

        # Final aggregate report
        final_report_path = self.output_dir / "full_audit_report.html"
        final_report_path.write_text("\n\n".join(all_reports))

        if sheet_url:
            print(f"📊 Anomaly Tracker: {sheet_url}")

        print(f"✅ Audit Complete. Results in: {self.output_dir}")

if __name__ == "__main__":
    import audit.targets.views  # Trigger registration
    agent = AuditorAgent()
    agent.run()
