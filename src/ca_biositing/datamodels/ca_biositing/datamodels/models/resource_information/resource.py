from ..base import BaseEntity, LookupBase
from datetime import datetime
from sqlmodel import Field, Relationship, SQLModel
from typing import Optional


class ResourceMorphology(SQLModel, table=True):
    __tablename__ = "resource_morphology"

    id: Optional[int] = Field(default=None, primary_key=True)
    resource_id: Optional[int] = Field(default=None, foreign_key="resource.id")
    morphology_uri: Optional[str] = Field(default=None)

    # Relationships
    resource: Optional["Resource"] = Relationship()


class Resource(BaseEntity, table=True):
    __tablename__ = "resource"

    name: Optional[str] = Field(default=None)
    primary_ag_product_id: Optional[int] = Field(default=None, foreign_key="primary_ag_product.id")
    resource_class_id: Optional[int] = Field(default=None, foreign_key="resource_class.id")
    resource_subclass_id: Optional[int] = Field(default=None, foreign_key="resource_subclass.id")
    resource_code: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    uri: Optional[str] = Field(default=None)

    # Relationships
    primary_ag_product: Optional["PrimaryAgProduct"] = Relationship()
    resource_class: Optional["ResourceClass"] = Relationship()
    resource_subclass: Optional["ResourceSubclass"] = Relationship()


class ResourceSubclass(LookupBase, table=True):
    __tablename__ = "resource_subclass"



class ResourceClass(LookupBase, table=True):
    __tablename__ = "resource_class"
