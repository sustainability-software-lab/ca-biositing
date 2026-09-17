"""MCP server for ca-biositing relational data and knowledge base proxy.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server import MCPServer
from sqlalchemy.orm import sessionmaker

from ca_biositing.webservice.config import WebServiceConfig
from ca_biositing.webservice.kb_client import call_kb_tool
from ca_biositing.webservice.services.analysis_service import AnalysisService
from ca_biositing.webservice.services.availability_service import AvailabilityService
from ca_biositing.webservice.services.usda_census_service import UsdaCensusService
from ca_biositing.webservice.services.usda_survey_service import UsdaSurveyService

logger = logging.getLogger(__name__)


def build_mcp_server(
    session_factory: sessionmaker,
    config: WebServiceConfig,
) -> tuple[MCPServer, dict[str, Callable[..., Awaitable[Any]]]]:
    """Build the MCP server plus a plain dict of the tool callables.
    """
    mcp = MCPServer(
        "ca-biositing",
        version=config.api_version,
        instructions=(
            "Geospatial bioeconomy data for California feedstocks. "
            "Includes resource availability, compositional analysis, and USDA agricultural data. "
            "Also provides access to scientific knowledge through the biocirv-kb proxy."
        ),
    )

    # --- Relational Tools (PostgreSQL) ---

    async def list_feedstock_resources() -> dict[str, Any]:
        """Discover all biomass resource names available in the database.
        Call this first to find valid resource names before querying availability or analysis.
        """
        with session_factory() as session:
            return {"resources": AvailabilityService.list_resources(session)}

    async def list_geoids() -> dict[str, Any]:
        """List all California county FIPS codes that have data.
        Use to discover valid geoid values.
        """
        with session_factory() as session:
            return {"geoids": AvailabilityService.list_geoids(session)}

    async def get_feedstock_availability(resource: str, geoid: str) -> dict[str, Any]:
        """Get the seasonal harvest window (from_month, to_month) for a specific resource in a specific county.
        """
        with session_factory() as session:
            return AvailabilityService.get_by_resource(session, resource, geoid)

    async def get_feedstock_analysis_all(resource: str, geoid: str) -> dict[str, Any]:
        """Get all compositional/proximate/ultimate analysis parameters for a resource+county combination.
        Returns ash, moisture, nitrogen, carbon, etc.
        """
        with session_factory() as session:
            return AnalysisService.list_by_resource(session, resource, geoid)

    async def get_feedstock_analysis_parameter(resource: str, geoid: str, parameter: str) -> dict[str, Any]:
        """Get a single named analysis parameter (e.g. 'ash', 'moisture') for a resource+county.
        """
        with session_factory() as session:
            return AnalysisService.get_by_resource(session, resource, geoid, parameter)

    async def get_usda_census_data(crop: str, geoid: str, parameter: str | None = None) -> dict[str, Any]:
        """Get USDA census data for a crop and county. Includes acreage, yield, production values.
        If parameter is omitted, all available parameters for the crop/county are returned.
        """
        with session_factory() as session:
            if parameter:
                return UsdaCensusService.get_by_crop(session, crop, geoid, parameter)
            return UsdaCensusService.list_by_crop(session, crop, geoid)

    async def get_usda_survey_data(crop: str, geoid: str, parameter: str | None = None) -> dict[str, Any]:
        """Get USDA survey data for a crop and county, including seasonal flags and survey period metadata.
        If parameter is omitted, all available parameters for the crop/county are returned.
        """
        with session_factory() as session:
            if parameter:
                return UsdaSurveyService.get_by_crop(session, crop, geoid, parameter)
            return UsdaSurveyService.list_by_crop(session, crop, geoid)

    # --- KB Proxy Tools (biocirv-kb) ---

    async def search_biositing_knowledge(
        query: str,
        top_k: int = 5,
        deep: bool = False,
    ) -> dict[str, Any]:
        """Search the bioeconomy scientific literature for evidence about a topic.
        Returns ranked text chunks with citations. Use when you need source text to reason over.
        """
        return await call_kb_tool(
            "search_corpus",
            {"query": query, "top_k": top_k, "deep": deep},
            config.kb_mcp_url,
            config.kb_api_key,
        )

    async def ask_biositing_question(
        query: str,
        top_k: int = 8,
    ) -> dict[str, Any]:
        """Ask the knowledge base a question and get a grounded, cited answer synthesized from the scientific literature.
        Use when you want a direct answer rather than raw evidence.
        """
        return await call_kb_tool(
            "answer_question",
            {"query": query, "top_k": top_k},
            config.kb_mcp_url,
            config.kb_api_key,
        )

    async def get_feedstock_entity_relationships(entity_name: str) -> dict[str, Any]:
        """Look up what the knowledge graph knows about a feedstock entity (e.g. 'rice straw').
        Returns all stated relationships with evidence quotes.
        """
        return await call_kb_tool(
            "get_entity_relationships",
            {"entity_name": entity_name},
            config.kb_mcp_url,
            config.kb_api_key,
        )

    tools: dict[str, Callable[..., Awaitable[Any]]] = {
        "list_feedstock_resources": list_feedstock_resources,
        "list_geoids": list_geoids,
        "get_feedstock_availability": get_feedstock_availability,
        "get_feedstock_analysis_all": get_feedstock_analysis_all,
        "get_feedstock_analysis_parameter": get_feedstock_analysis_parameter,
        "get_usda_census_data": get_usda_census_data,
        "get_usda_survey_data": get_usda_survey_data,
        "search_biositing_knowledge": search_biositing_knowledge,
        "ask_biositing_question": ask_biositing_question,
        "get_feedstock_entity_relationships": get_feedstock_entity_relationships,
    }

    for tool in tools.values():
        mcp.tool()(tool)

    return mcp, tools
