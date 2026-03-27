import sys
import traceback
from prefect import flow, get_run_logger
from prefect.utilities.importtools import import_object

# A dictionary mapping flow names to their import paths
AVAILABLE_FLOWS = {
    #"primary_ag_product": "ca_biositing.pipeline.flows.primary_ag_product.primary_ag_product_flow",
    #"analysis_type": "ca_biositing.pipeline.flows.analysis_type.analysis_type_flow",
    "resource_information": "ca_biositing.pipeline.flows.resource_information.resource_information_flow",
    "static_resource_info": "ca_biositing.pipeline.flows.static_resource_info.static_resource_info_flow",
    "samples": "ca_biositing.pipeline.flows.samples_etl.samples_etl_flow",
    "analysis_records": "ca_biositing.pipeline.flows.analysis_records.analysis_records_flow",
    "aim2_bioconversion": "ca_biositing.pipeline.flows.aim2_bioconversion.aim2_bioconversion_flow",
    "usda_etl": "ca_biositing.pipeline.flows.usda_etl.usda_etl_flow",
    "landiq": "ca_biositing.pipeline.flows.landiq_etl.landiq_etl_flow",
    "billion_ton": "ca_biositing.pipeline.flows.billion_ton_etl.billion_ton_etl_flow",
    #"field_sample": "ca_biositing.pipeline.flows.field_sample_etl.field_sample_etl_flow",
    #"prepared_sample": "ca_biositing.pipeline.flows.prepared_sample_etl.prepared_sample_etl_flow",
}

@flow(name="Master ETL Flow", log_prints=True)
def master_flow():
    """
    A master flow to orchestrate all ETL pipelines.
    This flow dynamically imports and runs sub-flows, allowing it to continue
    even if some sub-flows fail to import or run.
    """
    logger = get_run_logger()
    logger.info("Running master ETL flow...")
    for flow_name, flow_path in AVAILABLE_FLOWS.items():
        try:
            logger.info(f"--- Running sub-flow: {flow_name} ---")
            print(f"DEBUG: Attempting to import {flow_path}")
            # Split the path to import the module first
            module_path, obj_name = flow_path.rsplit(".", 1)
            import importlib
            print(f"DEBUG: Importing module {module_path}")
            mod = importlib.import_module(module_path)
            print(f"DEBUG: Module {module_path} imported")
            flow_func = getattr(mod, obj_name)
            print(f"DEBUG: Successfully got attribute {obj_name}")

            logger.info(f"Executing {flow_name} as sub-flow")
            # We must call the flow function. If it's a Prefect flow object,
            # calling it will trigger the orchestration.
            result = flow_func()
        except Exception:
            logger.exception(f"Flow '{flow_name}' failed")
    logger.info("Master ETL flow completed.")

if __name__ == "__main__":
    # This script is a placeholder for running flows directly.
    # Deployments are now managed via the 'prefect.yaml' file and the 'prefect deploy' command.
    print("This script is not intended for creating deployments.")
    print("To deploy, run the following command from within the container:")
    print("\n  prefect deploy\n")
    print("To run the flow directly for testing (using a temporary server), run:")
    print("\n  python -c 'from run_prefect_flow import master_flow; master_flow()'\n")
