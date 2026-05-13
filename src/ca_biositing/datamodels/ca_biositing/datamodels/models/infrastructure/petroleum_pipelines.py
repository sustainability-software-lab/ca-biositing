from datetime import datetime
from decimal import Decimal
from sqlmodel import Field, SQLModel
from typing import Any, Optional
from sqlalchemy import Column
from geoalchemy2 import Geometry


class InfrastructurePetroleumPipelines(SQLModel, table=True):
    __tablename__ = "infrastructure_petroleum_pipelines"

    object_id: Optional[int] = Field(default=None, primary_key=True)
    operator_name: Optional[str] = Field(default=None)
    pipeline_name: Optional[str] = Field(default=None)
    source: Optional[str] = Field(default=None)
    pipeline_type: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    artificial: Optional[int] = Field(default=None)
    master_oid: Optional[int] = Field(default=None)
    commodity: Optional[str] = Field(default=None)
    volume: Optional[Decimal] = Field(default=None)
    capacity: Optional[Decimal] = Field(default=None)
    vcr: Optional[str] = Field(default=None)
    shape_length: Optional[Decimal] = Field(default=None)
    mode_type: Optional[str] = Field(default=None)
    length: Optional[Decimal] = Field(default=None)
    geom: Optional[Any] = Field(default=None, sa_column=Column(Geometry("MULTILINESTRING")))
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
    etl_run_id: Optional[int] = Field(default=None)
    lineage_group_id: Optional[int] = Field(default=None)
