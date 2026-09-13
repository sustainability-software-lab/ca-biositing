from datetime import datetime
from sqlmodel import Field, Relationship, SQLModel
from typing import Optional


class InfrastructureEthanolBiorefineries(SQLModel, table=True):
    __tablename__ = "infrastructure_ethanol_biorefineries"

    ethanol_biorefinery_id: Optional[int] = Field(default=None, primary_key=True)
    name: Optional[str] = Field(default=None)
    type: Optional[str] = Field(default=None)
    capacity_mgy: Optional[int] = Field(default=None)
    production_mgy: Optional[int] = Field(default=None)
    constr_exp: Optional[int] = Field(default=None)
    address_id: Optional[int] = Field(default=None, foreign_key="location_address.id")
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    address: Optional["LocationAddress"] = Relationship()
