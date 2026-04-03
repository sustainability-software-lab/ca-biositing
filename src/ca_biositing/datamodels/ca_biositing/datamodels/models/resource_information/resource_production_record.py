from datetime import date
from typing import Optional

from sqlmodel import Field

from ..base import BaseEntity


class ResourceProductionRecord(BaseEntity, table=True):
    __tablename__ = "resource_production_record"

    dataset_id: int = Field(description="Reference to the dataset")
    # foreign_key="dataset.id" (commented out per repo convention)
    method_id: Optional[int] = Field(default=None, description="Reference to method metadata")
    geoid: Optional[str] = Field(default=None, description="Place GEOID")
    primary_ag_product_id: Optional[int] = Field(default=None, description="Reference to primary agricultural product")
    # foreign_key="primary_ag_product.id" (commented out per repo convention)
    resource_id: Optional[int] = Field(default=None, description="Reference to resource")
    # foreign_key="resource.id" (commented out per repo convention)
    report_date: date = Field(description="Date/year for the reported production estimate")
    scenario: Optional[str] = Field(default=None, description="Scenario label if provided by source")
    note: Optional[str] = Field(default=None, description="Additional notes")
