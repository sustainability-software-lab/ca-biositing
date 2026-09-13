from datetime import date, datetime
from decimal import Decimal
from sqlmodel import Field, Relationship, SQLModel
from typing import Optional


class InfrastructureCafoManureLocations(SQLModel, table=True):
    __tablename__ = "infrastructure_cafo_manure_locations"

    cafo_manure_id: Optional[int] = Field(default=None, primary_key=True)
    latitude: Optional[Decimal] = Field(default=None)
    longitude: Optional[Decimal] = Field(default=None)
    owner_name: Optional[str] = Field(default=None)
    facility_name: Optional[str] = Field(default=None)
    animal: Optional[str] = Field(default=None)
    animal_feed_operation_type: Optional[str] = Field(default=None)
    animal_units: Optional[int] = Field(default=None)
    animal_count: Optional[int] = Field(default=None)
    manure_total_solids: Optional[Decimal] = Field(default=None)
    source: Optional[str] = Field(default=None)
    date_accessed: Optional[date] = Field(default=None)
    address_id: Optional[int] = Field(default=None, foreign_key="location_address.id")
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    address: Optional["LocationAddress"] = Relationship()
