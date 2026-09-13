from datetime import date, datetime
from decimal import Decimal
from sqlmodel import Field, Relationship, SQLModel
from typing import Optional


class InfrastructureLandfills(SQLModel, table=True):
    __tablename__ = "infrastructure_landfills"

    project_id: Optional[str] = Field(default=None, primary_key=True)
    project_int_id: Optional[int] = Field(default=None)
    ghgrp_id: Optional[str] = Field(default=None)
    landfill_id: Optional[int] = Field(default=None)
    landfill_name: Optional[str] = Field(default=None)
    ownership_type: Optional[str] = Field(default=None)
    landfill_owner_orgs: Optional[str] = Field(default=None)
    landfill_opened_year: Optional[int] = Field(default=None)
    landfill_closure_year: Optional[int] = Field(default=None)
    landfill_status: Optional[str] = Field(default=None)
    waste_in_place: Optional[int] = Field(default=None)
    waste_in_place_year: Optional[date] = Field(default=None)
    lfg_system_in_place: Optional[bool] = Field(default=None)
    lfg_collected: Optional[Decimal] = Field(default=None)
    lfg_flared: Optional[Decimal] = Field(default=None)
    project_status: Optional[str] = Field(default=None)
    project_name: Optional[str] = Field(default=None)
    project_start_date: Optional[date] = Field(default=None)
    project_shutdown_date: Optional[date] = Field(default=None)
    project_type_category: Optional[str] = Field(default=None)
    lfg_energy_project_type: Optional[str] = Field(default=None)
    rng_delivery_method: Optional[str] = Field(default=None)
    actual_mw_generation: Optional[Decimal] = Field(default=None)
    rated_mw_capacity: Optional[Decimal] = Field(default=None)
    lfg_flow_to_project: Optional[Decimal] = Field(default=None)
    direct_emission_reductions: Optional[Decimal] = Field(default=None)
    avoided_emission_reductions: Optional[Decimal] = Field(default=None)
    latitude: Optional[Decimal] = Field(default=None)
    longitude: Optional[Decimal] = Field(default=None)
    address_id: Optional[int] = Field(default=None, foreign_key="location_address.id")
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    address: Optional["LocationAddress"] = Relationship()
