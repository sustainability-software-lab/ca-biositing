import argparse
import subprocess
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

def list_flows():
    """
    Lists available ETL flows by scanning the flows directory.
    """
    project_root = Path(__file__).parent.parent
    flows_dir = project_root / "src" / "ca_biositing" / "pipeline" / "ca_biositing" / "pipeline" / "flows"

    if not flows_dir.exists():
        logger.error(f"Flows directory not found at {flows_dir}")
        sys.exit(1)

    flows = [f.stem for f in flows_dir.glob("*.py") if f.name != "__init__.py"]

    if not flows:
        logger.info("No ETL flows found.")
        return

    logger.info("Available ETL flows:")
    for flow in sorted(flows):
        print(f"  - {flow}")

def run_flow(flow_name: str):
    """
    Triggers a specific ETL flow inside the Prefect worker container.
    """
    project_root = Path(__file__).parent.parent
    docker_compose_file = project_root / "resources" / "docker" / "docker-compose.yml"

    if not docker_compose_file.exists():
        logger.error(f"Docker Compose file not found at {docker_compose_file}")
        sys.exit(1)

    # Command to execute inside the container.
    # We use a python one-liner to import the module and call the first flow found.
    # This ensures flows run even if they lack an 'if __name__ == "__main__":' block.
    python_cmd = (
        f"import importlib, sys; from prefect import Flow; "
        f"mod = importlib.import_module('ca_biositing.pipeline.flows.{flow_name}'); "
        f"flow = next((obj for obj in mod.__dict__.values() if isinstance(obj, Flow)), None); "
        f"flow() if flow else sys.exit(1)"
    )

    inner_cmd = f"source /shell-hook.sh && python -c \"{python_cmd}\""

    cmd = [
        "docker-compose",
        "-f", str(docker_compose_file),
        "exec",
        "prefect-worker",
        "/bin/bash",
        "-c",
        inner_cmd
    ]

    logger.info(f"Triggering ETL flow: {flow_name}")
    logger.info(f"Executing: {' '.join(cmd)}")

    try:
        # We use Popen to stream output in real-time
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        if process.stdout:
            for line in process.stdout:
                print(line, end="")

        process.wait()

        if process.returncode == 0:
            logger.info(f"Flow {flow_name} completed successfully.")
        else:
            logger.error(f"Flow {flow_name} failed with exit code {process.returncode}.")
            sys.exit(process.returncode)

    except KeyboardInterrupt:
        logger.warning("\nExecution interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger or list ETL flows in the Prefect worker.")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a specific ETL flow")
    run_parser.add_argument("flow_name", help="The name of the flow module (e.g., landiq_etl)")

    # List command
    list_parser = subparsers.add_parser("list", help="List all available ETL flows")

    args = parser.parse_args()

    if args.command == "run":
        run_flow(args.flow_name)
    elif args.command == "list":
        list_flows()
    else:
        parser.print_help()
