from decimal import Decimal
from sqlmodel import Field, SQLModel
from typing import Optional


class InfrastructureFoodProcessingFacilities(SQLModel, table=True):
    __tablename__ = "infrastructure_food_processing_facilities"

    processing_facility_id: Optional[int] = Field(default=None, primary_key=True)
    address: Optional[str] = Field(default=None)
    county: Optional[str] = Field(default=None)
    city: Optional[str] = Field(default=None)
    company: Optional[str] = Field(default=None)
    join_count: Optional[int] = Field(default=None)
    master_type: Optional[str] = Field(default=None)
    state: Optional[str] = Field(default=None)
    subtype: Optional[str] = Field(default=None)
    target_fid: Optional[int] = Field(default=None)
    processing_type: Optional[str] = Field(default=None)
    zip: Optional[str] = Field(default=None)
    type: Optional[str] = Field(default=None)
    wkt_geom: Optional[str] = Field(default=None)
    geom: Optional[str] = Field(default=None)
    latitude: Optional[Decimal] = Field(default=None)
    longitude: Optional[Decimal] = Field(default=None)

# Fields from Kieran's food processor facilities dataset
    CARB_facility_id: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    air_district: Optional[str] = Field(default=None)
    process: Optional[str] = Field(default=None)
    byproducts: Optional[str] = Field(default=None) #list of byproducts, comma-separated
    quantities: Optional[str] = Field(default=None) #list of quantities (ton/year) corresponding to byproducts, comma-separated

    
