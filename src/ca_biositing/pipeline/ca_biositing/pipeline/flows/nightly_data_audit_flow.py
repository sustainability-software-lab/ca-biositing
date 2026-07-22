from prefect import flow, task
from audit.agent import AuditorAgent

@task(name="run_data_audit_agent")
def run_data_audit_agent():
    """
    Instantiates and runs the AuditorAgent.
    """
    agent = AuditorAgent()
    agent.run()

@flow(name="Nightly Data Audit Flow", log_prints=True)
def nightly_data_audit_flow():
    """
    Prefect flow to run the nightly data audit.
    """
    run_data_audit_agent()

if __name__ == "__main__":
    nightly_data_audit_flow()
