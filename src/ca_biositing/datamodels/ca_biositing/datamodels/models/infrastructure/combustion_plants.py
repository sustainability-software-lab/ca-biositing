from datetime import datetime
from decimal import Decimal
from sqlmodel import Field, Relationship, SQLModel
from typing import Optional


class InfrastructureCombustionPlants(SQLModel, table=True):
    __tablename__ = "infrastructure_combustion_plants"

    combustion_fid: Optional[int] = Field(default=None, primary_key=True)
    objectid: Optional[int] = Field(default=None)
    status: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    equivalent_generation: Optional[Decimal] = Field(default=None)
    np_mw: Optional[Decimal] = Field(default=None)
    cf: Optional[Decimal] = Field(default=None)
    yearload: Optional[int] = Field(default=None)
    fuel: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    type: Optional[str] = Field(default=None)
    wkt_geom: Optional[str] = Field(default=None)
    geom: Optional[str] = Field(default=None)
    latitude: Optional[Decimal] = Field(default=None)
    longitude: Optional[Decimal] = Field(default=None)
    address_id: Optional[int] = Field(default=None, foreign_key="location_address.id")
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    address: Optional["LocationAddress"] = Relationship()
