from decimal import Decimal
from datetime import datetime
from sqlmodel import Field, SQLModel
from typing import Optional


class InfrastructureBiodieselPlants(SQLModel, table=True):
    """Biodiesel plants infrastructure."""
    __tablename__ = "infrastructure_biodiesel_plants"

    biodiesel_plant_id: Optional[int] = Field(default=None, primary_key=True)
    company: Optional[str] = Field(default=None)
    bbi_index: Optional[int] = Field(default=None)
    city: Optional[str] = Field(default=None)
    state: Optional[str] = Field(default=None)
    capacity_mmg_per_y: Optional[int] = Field(default=None)
    feedstock: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default=None)
    address: Optional[int] = Field(default=None)
    coordinates: Optional[str] = Field(default=None)
    latitude: Optional[Decimal] = Field(default=None)
    longitude: Optional[Decimal] = Field(default=None)
    source: Optional[str] = Field(default=None)
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
