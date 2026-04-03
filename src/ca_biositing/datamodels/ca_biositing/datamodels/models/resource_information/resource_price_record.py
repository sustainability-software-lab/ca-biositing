from datetime import date
from typing import Optional

from sqlmodel import Field

from ..base import BaseEntity


class ResourcePriceRecord(BaseEntity, table=True):
    __tablename__ = "resource_price_record"

    dataset_id: int = Field(description="Reference to the dataset")
    method_id: Optional[int] = Field(default=None, description="Reference to method metadata")
    geoid: Optional[str] = Field(default=None, description="Place GEOID")
    resource_id: Optional[int] = Field(default=None, description="Reference to resource")
    # foreign_key="resource.id" (commented out per repo convention)
    primary_ag_product_id: Optional[int] = Field(default=None, description="Optional reference to primary agricultural product")
    # foreign_key="primary_ag_product.id" (commented out per repo convention)
    source_id: int = Field(description="Reference to data source")
    # foreign_key="data_source.id" (commented out per repo convention)
    report_start_date: date = Field(description="Start date of reported pricing period")
    report_end_date: date = Field(description="End date of reported pricing period")
    freight_terms: Optional[str] = Field(default=None, description="Freight terms from source pricing context")
    transport_mode: Optional[str] = Field(default=None, description="Transport mode from source pricing context")
    note: Optional[str] = Field(default=None, description="Additional notes")
