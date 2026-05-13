from ..base import BaseEntity
from datetime import datetime
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column
from geoalchemy2 import Geometry
from typing import Any, Optional


class MultiLineString(BaseEntity, table=True):
    __tablename__ = "multilinestring"

    geoid: Optional[str] = Field(default=None)
    geom: Optional[Any] = Field(default=None, sa_column=Column(Geometry(spatial_index=False)))
    dataset_id: Optional[int] = Field(default=None, foreign_key="dataset.id")

    # Relationships
    dataset: Optional["Dataset"] = Relationship()
