from datetime import datetime
from decimal import Decimal
from sqlmodel import Field, Relationship, SQLModel
from typing import Optional


class InfrastructureWastewaterTreatmentPlants(SQLModel, table=True):
    __tablename__ = "infrastructure_wastewater_treatment_plants"

    plant_id: Optional[int] = Field(default=None, primary_key=True)
    name: Optional[str] = Field(default=None)
    codigestion: Optional[str] = Field(default=None)
    flow_design_adjusted: Optional[Decimal] = Field(default=None)
    flow_average: Optional[Decimal] = Field(default=None)
    biosolids: Optional[Decimal] = Field(default=None)
    excess_flow: Optional[Decimal] = Field(default=None)
    biogas_utilized: Optional[bool] = Field(default=None)
    flaring: Optional[bool] = Field(default=None)
    excess_mass_loading_rate: Optional[Decimal] = Field(default=None)
    excess_mass_loading_rate_wet: Optional[Decimal] = Field(default=None)
    methane_production: Optional[Decimal] = Field(default=None)
    energy_content: Optional[Decimal] = Field(default=None)
    electric_kw: Optional[Decimal] = Field(default=None)
    thermal_mmbtu_d: Optional[Decimal] = Field(default=None)
    electric_kwh: Optional[Decimal] = Field(default=None)
    thermal_annual_mmbtu_y: Optional[Decimal] = Field(default=None)
    anaerobic_digestion_facility: Optional[str] = Field(default=None)
    dayload_bdt: Optional[Decimal] = Field(default=None)
    dayload: Optional[Decimal] = Field(default=None)
    equivalent_generation: Optional[Decimal] = Field(default=None)
    facility_type: Optional[str] = Field(default=None)
    feedstock: Optional[str] = Field(default=None)
    type: Optional[str] = Field(default=None)
    latitude: Optional[Decimal] = Field(default=None)
    longitude: Optional[Decimal] = Field(default=None)
    address_id: Optional[int] = Field(default=None, foreign_key="location_address.id")
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    address: Optional["LocationAddress"] = Relationship()
