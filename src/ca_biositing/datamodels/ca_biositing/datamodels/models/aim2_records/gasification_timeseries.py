from typing import Optional

from sqlmodel import Field, UniqueConstraint

from ..base import BaseEntity


class GasificationTimeseries(BaseEntity, table=True):
    """
    Metadata for archived gasification timeseries data stored in GCS.
    """

    __tablename__ = "gasification_timeseries"
    __table_args__ = (
        UniqueConstraint(
            "resource_id", "experiment_id", name="uq_gasification_timeseries_res_exp"
        ),
    )
    resource_id: Optional[int] = Field(default=None, foreign_key="resource.id")
    experiment_id: Optional[int] = Field(default=None, foreign_key="experiment.id")
    resource_name: Optional[str] = Field(default=None)
    reactor_type_id: Optional[int] = Field(default=None, foreign_key="decon_vessel.id")
    gsheet_url: Optional[str] = Field(default=None)
    bucket_path: Optional[str] = Field(default=None)
    file_size: Optional[int] = Field(default=None)
    file_format: str = Field(default="csv")
    checksum_md5: Optional[str] = Field(default=None)
