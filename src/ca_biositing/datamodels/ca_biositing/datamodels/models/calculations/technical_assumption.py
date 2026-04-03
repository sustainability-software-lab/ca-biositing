from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import Field

from ..base import BaseEntity


class TechnicalAssumption(BaseEntity, table=True):
    __tablename__ = "technical_assumption"

    assumption_name: str = Field(description="Name of the technical assumption")
    assumption_value: Decimal = Field(
        sa_column=Column(Numeric(18, 8), nullable=False),
        description="Numeric value of the technical assumption",
    )
    unit_id: Optional[int] = Field(default=None, description="Reference to unit")
    # foreign_key="unit.id" (commented out per repo convention)
    source_id: Optional[int] = Field(default=None, description="Reference to data source")
    # foreign_key="data_source.id" (commented out per repo convention)
    note: Optional[str] = Field(default=None, description="Additional notes")
