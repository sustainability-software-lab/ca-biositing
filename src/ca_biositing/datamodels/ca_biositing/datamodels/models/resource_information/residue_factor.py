"""Residue Factor model for biomass resource characterization."""

from decimal import Decimal
from typing import Optional

from sqlmodel import Field, Relationship, UniqueConstraint

from ..base import BaseEntity


class ResidueFactor(BaseEntity, table=True):
    """Residue factor data for biomass resources.

    Stores factor values (min/mid/max ranges) and yield data for residue
    characterization. Uses composite unique constraint on (resource_id, factor_type)
    for UPSERT operations.
    """

    __tablename__ = "residue_factor"
    __table_args__ = (
        UniqueConstraint("resource_id", "factor_type", name="uq_residue_factor_resource_id_factor_type"),
    )

    # Foreign keys
    resource_id: int = Field(nullable=False, foreign_key="resource.id")
    """Reference to Resource table (required)"""

    resource_name: Optional[str] = Field(default=None)
    """Denormalized resource name for reference (from Resource.name at load time)"""

    data_source_id: Optional[int] = Field(default=None, foreign_key="data_source.id")
    """Reference to DataSource (contains URL and metadata)"""

    # Factor data
    factor_type: Optional[str] = Field(default=None)
    """Type classification of the residue factor"""

    factor_min: Optional[Decimal] = Field(default=None)
    """Minimum factor value"""

    factor_max: Optional[Decimal] = Field(default=None)
    """Maximum factor value"""

    factor_mid: Optional[Decimal] = Field(default=None)
    """Mid-point factor value (calculated if not provided)"""

    # Yield data
    prune_trim_yield: Optional[Decimal] = Field(default=None)
    """Prune/trim yield value"""

    prune_trim_yield_unit_id: Optional[int] = Field(default=None, foreign_key="unit.id")
    """Reference to Unit for prune_trim_yield measurement"""

    # Metadata
    notes: Optional[str] = Field(default=None)
    """Additional notes or comments"""

    # Relationships
    resource: Optional["Resource"] = Relationship()
    data_source: Optional["DataSource"] = Relationship()
    prune_trim_yield_unit: Optional["Unit"] = Relationship()
