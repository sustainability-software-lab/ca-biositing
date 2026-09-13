from datetime import datetime
from decimal import Decimal
from sqlmodel import Field, Relationship, SQLModel
from typing import Optional


class InfrastructureMswToEnergyAnaerobicDigesters(SQLModel, table=True):
    __tablename__ = "infrastructure_msw_to_energy_anaerobic_digesters"

    wte_id: Optional[int] = Field(default=None, primary_key=True)
    equivalent_generation: Optional[Decimal] = Field(default=None)
    feedstock: Optional[str] = Field(default=None)
    dayload: Optional[Decimal] = Field(default=None)
    dayload_bdt: Optional[Decimal] = Field(default=None)
    facility_type: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    source: Optional[str] = Field(default=None)
    type: Optional[str] = Field(default=None)
    wkt_geom: Optional[str] = Field(default=None)
    geom: Optional[str] = Field(default=None)
    latitude: Optional[Decimal] = Field(default=None)
    longitude: Optional[Decimal] = Field(default=None)
    address_id: Optional[int] = Field(default=None, foreign_key="location_address.id")
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    address: Optional["LocationAddress"] = Relationship()
