from datetime import datetime
from decimal import Decimal
from sqlmodel import Field, Relationship, SQLModel
from typing import Optional


class InfrastructureFoodManufacturersCARB(SQLModel, table=True):
    __tablename__ = "infrastructure_food_manufacturers_carb"

    processing_facility_id: Optional[int] = Field(default=None, primary_key=True)
    name: Optional[str] = Field(default=None)
    primary_ag_product: Optional[str] = Field(default=None)
    process_type: Optional[str] = Field(default=None)
    byproducts: Optional[str] = Field(default=None)
    quantities: Optional[str] = Field(default=None)
    general_source_info: Optional[str] = Field(default=None)
    carb_facility_id: Optional[int] = Field(default=None)
    air_district: Optional[str] = Field(default=None)
    address_id: Optional[int] = Field(default=None, foreign_key="location_address.id")
    etl_run_id: Optional[int] = Field(default=None, foreign_key="etl_run.id")
    lineage_group_id: Optional[int] = Field(default=None)
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    address: Optional["LocationAddress"] = Relationship()
