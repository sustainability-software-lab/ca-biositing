from datetime import datetime
from decimal import Decimal
from sqlmodel import Field, Relationship, SQLModel
from typing import Optional


class InfrastructureFoodProcessingFacilities(SQLModel, table=True):
    __tablename__ = "infrastructure_food_processing_facilities"

    processing_facility_id: Optional[int] = Field(default=None, primary_key=True)
    company: Optional[str] = Field(default=None)
    join_count: Optional[int] = Field(default=None)
    master_type: Optional[str] = Field(default=None)
    subtype: Optional[str] = Field(default=None)
    target_fid: Optional[int] = Field(default=None)
    processing_type: Optional[str] = Field(default=None)
    type: Optional[str] = Field(default=None)
    wkt_geom: Optional[str] = Field(default=None)
    geom: Optional[str] = Field(default=None)
    latitude: Optional[Decimal] = Field(default=None)
    longitude: Optional[Decimal] = Field(default=None)
    address_id: Optional[int] = Field(default=None, foreign_key="location_address.id")
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    address: Optional["LocationAddress"] = Relationship()
