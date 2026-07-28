from typing import Optional, List
import pandas as pd
from prefect import flow, task
from audit.agent import AuditorAgent
import audit.targets.views  # Register targets

@task(name="Run Skill-Based Data Auditor")
def run_auditor_task(targets: Optional[List[str]] = None):
    agent = AuditorAgent(targets=targets)
    agent.run()

@flow(name="Data Quality Audit Flow")
def data_quality_audit_flow(targets: Optional[List[str]] = None):
    """
    Prefect flow to run the data auditor.
    """
    run_auditor_task(targets=targets)

if __name__ == "__main__":
    data_quality_audit_flow()
