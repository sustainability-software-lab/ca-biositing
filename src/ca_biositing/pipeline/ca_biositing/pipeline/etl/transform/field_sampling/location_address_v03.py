"""Re-export of ``transform_location_address`` for backward compatibility."""

from ca_biositing.pipeline.etl.transform.field_sampling.location_address import (
    transform_location_address,
)

transform_location_address_v03 = transform_location_address

__all__ = ["transform_location_address", "transform_location_address_v03"]
