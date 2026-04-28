from ..base import LookupBase
from sqlmodel import Field
from typing import Optional


class Strain(LookupBase, table=True):
    __tablename__ = "strain"

    name: Optional[str] = Field(default=None, unique=True)
    parent_strain_id: Optional[int] = Field(default=None)
    genus: Optional[str] = Field(default=None)
    species: Optional[str] = Field(default=None)
    strain: Optional[str] = Field(default=None)
