from datetime import datetime
from decimal import Decimal
from sqlmodel import Field, Relationship, SQLModel
from typing import Optional


class InfrastructureFoodManufacturersEPA(SQLModel, table=True):
    __tablename__ = "infrastructure_food_manufacturers_epa"

    manufacturer_id: Optional[int] = Field(default=None, primary_key=True)
    name: Optional[str] = Field(default=None)
    naics_code: Optional[str] = Field(default=None)
    naics_code_description: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    website: Optional[str] = Field(default=None)
    excess_food_estimate_low_tons_per_year: Optional[Decimal] = Field(default=None)
    excess_food_estimate_high_tons_per_year: Optional[Decimal] = Field(default=None)
    address_id: Optional[int] = Field(default=None, foreign_key="location_address.id")
    etl_run_id: Optional[int] = Field(default=None, foreign_key="etl_run.id")
    lineage_group_id: Optional[int] = Field(default=None)
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    address: Optional["LocationAddress"] = Relationship()
