from datetime import datetime
from decimal import Decimal
from sqlmodel import Field, Relationship, SQLModel
from typing import Optional


class InfrastructureDistrictEnergySystems(SQLModel, table=True):
    __tablename__ = "infrastructure_district_energy_systems"

    des_fid: Optional[int] = Field(default=None, primary_key=True)
    cbg_id: Optional[int] = Field(default=None)
    name: Optional[str] = Field(default=None)
    system: Optional[str] = Field(default=None)
    object_id: Optional[int] = Field(default=None)
    primary_fuel: Optional[str] = Field(default=None)
    secondary_fuel: Optional[str] = Field(default=None)
    usetype: Optional[str] = Field(default=None)
    cap_st: Optional[Decimal] = Field(default=None)
    cap_hw: Optional[Decimal] = Field(default=None)
    cap_cw: Optional[Decimal] = Field(default=None)
    chpcg_cap: Optional[Decimal] = Field(default=None)
    excess_c: Optional[Decimal] = Field(default=None)
    excess_h: Optional[Decimal] = Field(default=None)
    type: Optional[str] = Field(default=None)
    wkt_geom: Optional[str] = Field(default=None)
    geom: Optional[str] = Field(default=None)
    latitude: Optional[Decimal] = Field(default=None)
    longitude: Optional[Decimal] = Field(default=None)
    address_id: Optional[int] = Field(default=None, foreign_key="location_address.id")
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    address: Optional["LocationAddress"] = Relationship()
