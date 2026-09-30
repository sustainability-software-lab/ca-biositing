import sys
import traceback
from prefect import flow, get_run_logger, task
from prefect.utilities.importtools import import_object

# A dictionary mapping flow names to their import paths
# THE ORDER MATTERS HERE: foundational flows should run before specialized ones.
AVAILABLE_FLOWS = {
    # "geography": "ca_biositing.pipeline.flows.geography.geography_etl_flow",
    # "primary_ag_product": "ca_biositing.pipeline.flows.primary_ag_product.primary_ag_product_flow",
    # "analysis_type": "ca_biositing.pipeline.flows.analysis_type.analysis_type_flow",
    "biodiesel_plants": "ca_biositing.pipeline.flows.biodiesel_plants.biodiesel_plants_flow",
    # "residue_factors": "ca_biositing.pipeline.flows.residue_factors_flow.residue_factors_etl_flow",
    # "resource_information": "ca_biositing.pipeline.flows.resource_information.resource_information_flow",
    # "county_ag_report": "ca_biositing.pipeline.flows.county_ag_report_etl.county_ag_report_flow",
    # "static_resource_info": "ca_biositing.pipeline.flows.static_resource_info.static_resource_info_flow",
    # "samples": "ca_biositing.pipeline.flows.samples_etl.samples_etl_flow",
    # "usda_etl": "ca_biositing.pipeline.flows.usda_etl.usda_etl_flow",
    # "almond_nsjv": "ca_biositing.pipeline.flows.almond_nsjv_etl.almond_nsjv_etl_flow",
    # "qualitative": "ca_biositing.pipeline.flows.qualitative.qualitative_etl_flow",
    # "analysis_records": "ca_biositing.pipeline.flows.analysis_records.analysis_records_flow",
    # "aim2_bioconversion": "ca_biositing.pipeline.flows.aim2_bioconversion.aim2_bioconversion_flow",
    # "landiq": "ca_biositing.pipeline.flows.landiq_etl.landiq_etl_flow",
    # "billion_ton": "ca_biositing.pipeline.flows.billion_ton_etl.billion_ton_etl_flow",
    # "field_sample": "ca_biositing.pipeline.flows.field_sample_etl.field_sample_etl_flow",
    # "prepared_sample": "ca_biositing.pipeline.flows.prepared_sample_etl.prepared_sample_etl_flow",
    # "thermochem": "ca_biositing.pipeline.flows.thermochem_etl.thermochem_etl_flow",
    # Infrastructure pipelines
    "tomato_processors": "ca_biositing.pipeline.flows.tomato_processors.tomato_processors_flow",
    "food_manufacturers_carb": "ca_biositing.pipeline.flows.food_manufacturers_carb.food_manufacturers_carb_flow",
    "food_manufacturers_epa": "ca_biositing.pipeline.flows.food_manufacturers_epa.food_manufacturers_epa_flow",
    "crude_oil_pipelines": "ca_biositing.pipeline.flows.crude_oil_pipelines.crude_oil_pipelines_flow",
    "railways": "ca_biositing.pipeline.flows.railways.railways_flow",
    "petroleum_pipelines": "ca_biositing.pipeline.flows.petroleum_pipelines.petroleum_pipelines_flow",
    "biosolids_facilities": "ca_biositing.pipeline.flows.biosolids_facilities.biosolids_facilities_flow",
    "cafo_manure_locations": "ca_biositing.pipeline.flows.cafo_manure_locations.cafo_manure_locations_flow",
    "combustion_plants": "ca_biositing.pipeline.flows.combustion_plants.combustion_plants_flow",
    "district_energy_systems": "ca_biositing.pipeline.flows.district_energy_systems.district_energy_systems_flow",
    "ethanol_biorefineries": "ca_biositing.pipeline.flows.ethanol_biorefineries.ethanol_biorefineries_flow",
    "food_processing_facilities": "ca_biositing.pipeline.flows.food_processing_facilities.food_processing_facilities_flow",
    "landfills": "ca_biositing.pipeline.flows.landfills.landfills_flow",
    "livestock_anaerobic_digesters": "ca_biositing.pipeline.flows.livestock_anaerobic_digesters.livestock_anaerobic_digesters_flow",
    "msw_to_energy_anaerobic_digesters": "ca_biositing.pipeline.flows.msw_to_energy_anaerobic_digesters.msw_to_energy_anaerobic_digesters_flow",
    "saf_and_renewable_diesel_plants": "ca_biositing.pipeline.flows.saf_and_renewable_diesel_plants.saf_and_renewable_diesel_plants_flow",
    "wastewater_treatment_plants": "ca_biositing.pipeline.flows.wastewater_treatment_plants.wastewater_treatment_plants_flow",
}

@task(name="Refresh materialized views", retries=3, retry_delay_seconds=30)
def refresh_materialized_views_task():
    """Refreshes all materialized views once ETL data loads are complete."""
    from ca_biositing.datamodels.database import get_engine
    from ca_biositing.datamodels.views import refresh_all_views

    logger = get_run_logger()
    logger.info("Refreshing materialized views (including data_portal schema)...")
    engine = get_engine()
    try:
        refresh_all_views(engine)
    finally:
        engine.dispose()
    logger.info("Materialized views refresh completed.")

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
    refresh_materialized_views_task()
    logger.info("Master ETL flow completed.")

if __name__ == "__main__":
    # This script is a placeholder for running flows directly.
    # Deployments are now managed via the 'prefect.yaml' file and the 'prefect deploy' command.
    print("This script is not intended for creating deployments.")
    print("To deploy, run the following command from within the container:")
    print("\n  prefect deploy\n")
    print("To run the flow directly for testing (using a temporary server), run:")
    print("\n  python -c 'from run_prefect_flow import master_flow; master_flow()'\n")
