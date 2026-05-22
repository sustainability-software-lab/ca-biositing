from ..base import Aim2RecordBase
from datetime import datetime
from decimal import Decimal
from sqlmodel import Field, SQLModel
from typing import Optional


class FermentationRecord(Aim2RecordBase, table=True):
    __tablename__ = "fermentation_record"

    strain_id: Optional[int] = Field(default=None, foreign_key="strain.id")
    bioconversion_method_id: Optional[int] = Field(default=None, foreign_key="bioconversion_method.id")
    pretreatment_method_id: Optional[int] = Field(default=None, foreign_key="method.id")
    pretreatment_setup_id: Optional[int] = Field(default=None, foreign_key="pretreatment_setup.id")
    eh_method_id: Optional[int] = Field(default=None, foreign_key="method.id")
    eh_method_id_new: Optional[int] = Field(default=None, foreign_key="enz_hydr_method.id")
    well_position: Optional[str] = Field(default=None)
    vessel_id: Optional[int] = Field(default=None, foreign_key="decon_vessel.id")
    analyte_detection_equipment_id: Optional[int] = Field(default=None)
    # ... other fields if they exist
