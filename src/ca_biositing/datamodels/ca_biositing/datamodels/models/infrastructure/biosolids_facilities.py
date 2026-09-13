from datetime import date, datetime
from decimal import Decimal
from sqlmodel import Field, Relationship, SQLModel
from typing import Optional


class InfrastructureBiosolidsFacilities(SQLModel, table=True):
    __tablename__ = "infrastructure_biosolids_facilities"

    biosolid_facility_id: Optional[int] = Field(default=None, primary_key=True)
    report_submitted_date: Optional[date] = Field(default=None)
    latitude: Optional[Decimal] = Field(default=None)
    longitude: Optional[Decimal] = Field(default=None)
    facility: Optional[str] = Field(default=None)
    authority: Optional[str] = Field(default=None)
    plant_type: Optional[str] = Field(default=None)
    aqmd: Optional[str] = Field(default=None)
    biosolids_number: Optional[str] = Field(default=None)
    biosolids_contact: Optional[str] = Field(default=None)
    biosolids_contact_phone: Optional[str] = Field(default=None)
    biosolids_contact_email: Optional[str] = Field(default=None)
    adwf: Optional[Decimal] = Field(default=None)
    potw_biosolids_generated: Optional[int] = Field(default=None)
    twtds_biosolids_treated: Optional[int] = Field(default=None)
    class_b_land_app: Optional[int] = Field(default=None)
    class_b_applier: Optional[str] = Field(default=None)
    class_a_compost: Optional[int] = Field(default=None)
    class_a_heat_dried: Optional[int] = Field(default=None)
    class_a_other: Optional[int] = Field(default=None)
    class_a_other_applier: Optional[str] = Field(default=None)
    twtds_transfer_to_second_preparer: Optional[int] = Field(default=None)
    twtds_second_preparer_name: Optional[str] = Field(default=None)
    adc_or_final_c: Optional[int] = Field(default=None)
    landfill: Optional[int] = Field(default=None)
    landfill_name: Optional[str] = Field(default=None)
    surface_disposal: Optional[int] = Field(default=None)
    deepwell_injection: Optional[str] = Field(default=None)
    stored: Optional[int] = Field(default=None)
    longterm_treatment: Optional[int] = Field(default=None)
    other: Optional[int] = Field(default=None)
    name_of_other: Optional[str] = Field(default=None)
    incineration: Optional[int] = Field(default=None)
    address_id: Optional[int] = Field(default=None, foreign_key="location_address.id")
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    address: Optional["LocationAddress"] = Relationship()
