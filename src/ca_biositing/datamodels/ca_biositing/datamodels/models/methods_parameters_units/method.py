from ..base import BaseEntity, LookupBase
from datetime import datetime
from sqlmodel import Field, Relationship, SQLModel
from typing import Optional


class Method(BaseEntity, table=True):
    __tablename__ = "method"

    name: Optional[str] = Field(default=None)
    duration: Optional[float] = Field(default=None)
    method_abbrev_id: Optional[int] = Field(default=None, foreign_key="method_abbrev.id")
    method_category_id: Optional[int] = Field(default=None, foreign_key="method_category.id")
    method_standard_id: Optional[int] = Field(default=None, foreign_key="method_standard.id")
    description: Optional[str] = Field(default=None)
    detection_limits: Optional[str] = Field(default=None)
    source_id: Optional[int] = Field(default=None, foreign_key="data_source.id")

    # Relationships
    method_abbrev: Optional["MethodAbbrev"] = Relationship()
    method_category: Optional["MethodCategory"] = Relationship()
    method_standard: Optional["MethodStandard"] = Relationship()
    source: Optional["DataSource"] = Relationship()


class MethodAbbrev(LookupBase, table=True):
    __tablename__ = "method_abbrev"



class MethodCategory(LookupBase, table=True):
    __tablename__ = "method_category"



class MethodStandard(LookupBase, table=True):
    __tablename__ = "method_standard"
