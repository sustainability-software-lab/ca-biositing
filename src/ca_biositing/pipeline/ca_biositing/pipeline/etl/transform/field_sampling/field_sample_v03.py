"""Re-export of ``transform_field_sample`` and ``EXTRACT_SOURCES`` for backward compatibility."""

from ca_biositing.pipeline.etl.transform.field_sampling.field_sample import (
    EXTRACT_SOURCES,
    transform_field_sample,
)

transform_field_sample_v03 = transform_field_sample

__all__ = ["EXTRACT_SOURCES", "transform_field_sample", "transform_field_sample_v03"]
