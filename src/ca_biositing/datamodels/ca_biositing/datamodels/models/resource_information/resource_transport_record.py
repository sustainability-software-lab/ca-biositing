from typing import Optional

from sqlmodel import Field

from ..base import BaseEntity


class ResourceTransportRecord(BaseEntity, table=True):
    __tablename__ = "resource_transport_record"

    dataset_id: int = Field(description="Reference to the dataset")
    method_id: int = Field(description="Reference to method metadata")
    # foreign_key="dataset.id" / foreign_key="method.id" (commented out per repo convention)
    geoid: Optional[str] = Field(default=None, description="Place GEOID")
    transport_description: str = Field(description="Transport description from source")
    resource_id: Optional[int] = Field(default=None, description="Reference to resource")
    # foreign_key="resource.id" (commented out per repo convention)
    note: Optional[str] = Field(default=None, description="Additional notes")
