from datetime import datetime
from decimal import Decimal
from sqlmodel import Field, Relationship, SQLModel
from typing import Optional


class InfrastructureTomatoProcessors(SQLModel, table=True):
    __tablename__ = "infrastructure_tomato_processors"

    processing_facility_id: Optional[str] = Field(default=None, primary_key=True)
    name: Optional[str] = Field(default=None)
    processing_capacity_for_tomato_paste_tons_hr: Optional[int] = Field(default=None)
    processing_capacity_of_peeled_chopped_tons_hr: Optional[Decimal] = Field(default=None)
    mold_metric_tons_yr: Optional[int] = Field(default=None)
    green_metric_tons_yr: Optional[int] = Field(default=None)
    vines_metric_tons_yr: Optional[int] = Field(default=None)
    pomace_metric_tons_yr: Optional[int] = Field(default=None)
    pomace_peels_metric_tons_yr: Optional[int] = Field(default=None)
    pomace_seeds_metric_tons_yr: Optional[int] = Field(default=None)
    peels_only_metric_tons_yr: Optional[int] = Field(default=None)
    seeds_metric_tons_yr: Optional[int] = Field(default=None)
    paste_data_source: Optional[str] = Field(default=None)
    chopped_data_source: Optional[str] = Field(default=None)
    reliability_of_chopped_data: Optional[str] = Field(default=None)
    link: Optional[str] = Field(default=None)
    address_id: Optional[int] = Field(default=None, foreign_key="location_address.id")
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    address: Optional["LocationAddress"] = Relationship()
