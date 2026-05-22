from ..base import BaseEntity
from sqlmodel import Field
from typing import Optional


class EnzymaticHydrolysisMethod(BaseEntity, table=True):
    __tablename__ = "enz_hydr_method"

    eh_uuid: str = Field(nullable=False)
    eh_id: str = Field(nullable=False, unique=True)
    method_id: str = Field(nullable=False)
    name: Optional[str] = Field(default=None)
    enzyme_formulation: Optional[str] = Field(default=None)
    reaction_volume_ul: Optional[float] = Field(default=None)
    temperature_c: Optional[float] = Field(default=None)
    time_h: Optional[float] = Field(default=None)
    description: Optional[str] = Field(default=None)
    protocol_url: Optional[str] = Field(default=None)
