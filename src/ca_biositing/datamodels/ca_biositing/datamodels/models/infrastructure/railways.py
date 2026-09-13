from datetime import datetime
from decimal import Decimal
from sqlmodel import Field, SQLModel
from typing import Any, Optional
from sqlalchemy import Column
from geoalchemy2 import Geometry


class InfrastructureRailways(SQLModel, table=True):
    __tablename__ = "infrastructure_railways"

    object_id: Optional[int] = Field(default=None, primary_key=True)
    state: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    link_type: Optional[str] = Field(default=None)
    dir_flag: Optional[Decimal] = Field(default=None)
    volume: Optional[Decimal] = Field(default=None)
    capacity: Optional[Decimal] = Field(default=None)
    vcr: Optional[Decimal] = Field(default=None)
    artificial: Optional[int] = Field(default=None)
    shape_length: Optional[Decimal] = Field(default=None)
    mode_type: Optional[str] = Field(default=None)
    length: Optional[Decimal] = Field(default=None)
    geom: Optional[Any] = Field(default=None, sa_column=Column(Geometry("MULTILINESTRING")))
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
