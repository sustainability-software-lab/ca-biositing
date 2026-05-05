from ..base import BaseEntity
from sqlmodel import Field
from typing import Optional

class BioconversionMethod(BaseEntity, table=True):
    __tablename__ = "bioconversion_method"

    name: str = Field(unique=True)
    strain_id: Optional[int] = Field(default=None, foreign_key="strain.id")
    strain_name: Optional[str] = Field(default=None)
    inoculum_volume_L: Optional[float] = Field(default=None)
    reaction_volume_L: Optional[float] = Field(default=None)
    temperature_C: Optional[float] = Field(default=None)
    time_h: Optional[float] = Field(default=None)
    description: Optional[str] = Field(default=None)
    note: Optional[str] = Field(default=None)
    protocol_url: Optional[str] = Field(default=None)
