from ..base import BaseEntity
from datetime import date
from sqlmodel import Field, Column, JSON
from typing import Optional, List


class PretreatmentSetup(BaseEntity, table=True):
    __tablename__ = "pretreatment_setup"

    pretreatment_uuid: str = Field(nullable=False)
    pretreatment_exper_id: str = Field(nullable=False, unique=True)
    pretreatment_exper_name: str = Field(nullable=False)
    resources: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    prepared_samples: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    decon_method_id: Optional[int] = Field(default=None, foreign_key="method.id")
    decon_vessel_id: Optional[int] = Field(default=None, foreign_key="decon_vessel.id")
    eh_method_id: Optional[int] = Field(default=None, foreign_key="method.id")
    experiment_date: Optional[date] = Field(default=None)
    experiment_setup_url: Optional[str] = Field(default=None)
    analyst_email: Optional[str] = Field(default=None)
    pretr_url_batch_record: Optional[str] = Field(default=None)
    pretr_notes: Optional[str] = Field(default=None)
