from datetime import date, datetime
from decimal import Decimal
from sqlmodel import Field, Relationship, SQLModel
from typing import Optional


class InfrastructureLivestockAnaerobicDigesters(SQLModel, table=True):
    __tablename__ = "infrastructure_livestock_anaerobic_digesters"

    digester_id: Optional[int] = Field(default=None, primary_key=True)
    project_name: Optional[str] = Field(default=None)
    project_type: Optional[str] = Field(default=None)
    digester_type: Optional[str] = Field(default=None)
    profile: Optional[str] = Field(default=None)
    year_operational: Optional[date] = Field(default=None)
    animal_type_class: Optional[str] = Field(default=None)
    animal_types: Optional[str] = Field(default=None)
    pop_feeding_digester: Optional[str] = Field(default=None)
    total_pop_feeding_digester: Optional[int] = Field(default=None)
    cattle: Optional[int] = Field(default=None)
    dairy: Optional[int] = Field(default=None)
    poultry: Optional[int] = Field(default=None)
    swine: Optional[int] = Field(default=None)
    codigestion: Optional[str] = Field(default=None)
    biogas_generation_estimate: Optional[int] = Field(default=None)
    electricity_generated: Optional[int] = Field(default=None)
    biogas_end_uses: Optional[str] = Field(default=None)
    methane_emission_reductions: Optional[int] = Field(default=None)
    latitude: Optional[Decimal] = Field(default=None)
    longitude: Optional[Decimal] = Field(default=None)
    address_id: Optional[int] = Field(default=None, foreign_key="location_address.id")
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    address: Optional["LocationAddress"] = Relationship()
