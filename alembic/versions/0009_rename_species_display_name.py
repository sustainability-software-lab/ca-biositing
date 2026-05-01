"""rename species_display_name to strain_name

Revision ID: 55f93e3a6237
Revises: 0008bf16e6e2
Create Date: 2026-05-01 09:02:57.140346

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '55f93e3a6237'
down_revision: Union[str, Sequence[str], None] = '0008bf16e6e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DROP_INDEX_STATEMENTS = [
    "DROP INDEX IF EXISTS data_portal.idx_mv_biomass_fermentation_id",
    "DROP INDEX IF EXISTS data_portal.idx_mv_biomass_fermentation_resource_id",
    "DROP INDEX IF EXISTS data_portal.idx_mv_biomass_fermentation_geoid",
    "DROP INDEX IF EXISTS data_portal.idx_mv_biomass_fermentation_county",
    "DROP INDEX IF EXISTS data_portal.idx_mv_biomass_fermentation_species_display_name",
    "DROP INDEX IF EXISTS data_portal.idx_mv_biomass_fermentation_strain_name",
    "DROP INDEX IF EXISTS data_portal.idx_mv_biomass_fermentation_product_name",
]

CREATE_INDEX_STATEMENTS = [
    "CREATE UNIQUE INDEX idx_mv_biomass_fermentation_id ON data_portal.mv_biomass_fermentation (id)",
    "CREATE INDEX idx_mv_biomass_fermentation_resource_id ON data_portal.mv_biomass_fermentation (resource_id)",
    "CREATE INDEX idx_mv_biomass_fermentation_geoid ON data_portal.mv_biomass_fermentation (geoid)",
    "CREATE INDEX idx_mv_biomass_fermentation_county ON data_portal.mv_biomass_fermentation (county)",
    "CREATE INDEX idx_mv_biomass_fermentation_strain_name ON data_portal.mv_biomass_fermentation (strain_name)",
    "CREATE INDEX idx_mv_biomass_fermentation_product_name ON data_portal.mv_biomass_fermentation (product_name)",
]

PREVIOUS_CREATE_INDEX_STATEMENTS = [
    "CREATE UNIQUE INDEX idx_mv_biomass_fermentation_id ON data_portal.mv_biomass_fermentation (id)",
    "CREATE INDEX idx_mv_biomass_fermentation_resource_id ON data_portal.mv_biomass_fermentation (resource_id)",
    "CREATE INDEX idx_mv_biomass_fermentation_geoid ON data_portal.mv_biomass_fermentation (geoid)",
    "CREATE INDEX idx_mv_biomass_fermentation_county ON data_portal.mv_biomass_fermentation (county)",
    "CREATE INDEX idx_mv_biomass_fermentation_species_display_name ON data_portal.mv_biomass_fermentation (species_display_name)",
    "CREATE INDEX idx_mv_biomass_fermentation_product_name ON data_portal.mv_biomass_fermentation (product_name)",
]

NEW_MV_SQL = """
CREATE MATERIALIZED VIEW data_portal.mv_biomass_fermentation AS
SELECT row_number() OVER (
           ORDER BY fermentation_record.resource_id,
                    location_address.geography_id,
                    strain.name,
                    pm.name,
                    em.name,
                    bcm.name,
                    parameter.name,
                    unit.name
       ) AS id,
       fermentation_record.resource_id,
       resource.name AS resource_name,
       location_address.geography_id AS geoid,
       place.county_name AS county,
       LEFT(strain.genus, 1) || '. ' || strain.species AS strain_name,
       pm.name AS pretreatment_method,
       em.name AS enzyme_name,
       bcm.name AS bioconversion_method,
       coalesce(pm.duration, em.duration, bcm.time_h) AS elapsed_time,
       parameter.name AS product_name,
       avg(observation.value) AS avg_value,
       min(observation.value) AS min_value,
       max(observation.value) AS max_value,
       stddev(observation.value) AS std_dev,
       count(*) AS observation_count,
       unit.name AS unit
FROM fermentation_record
JOIN resource ON fermentation_record.resource_id = resource.id
LEFT OUTER JOIN prepared_sample ON fermentation_record.prepared_sample_id = prepared_sample.id
LEFT OUTER JOIN field_sample ON prepared_sample.field_sample_id = field_sample.id
LEFT OUTER JOIN location_address ON field_sample.sampling_location_id = location_address.id
LEFT OUTER JOIN place ON location_address.geography_id = place.geoid
LEFT OUTER JOIN strain ON fermentation_record.strain_id = strain.id
LEFT OUTER JOIN method AS pm ON fermentation_record.pretreatment_method_id = pm.id
LEFT OUTER JOIN method AS em ON fermentation_record.eh_method_id = em.id
LEFT OUTER JOIN bioconversion_method AS bcm ON fermentation_record.bioconversion_method_id = bcm.id
JOIN observation ON lower(observation.record_id) = lower(fermentation_record.record_id)
JOIN parameter ON observation.parameter_id = parameter.id
LEFT OUTER JOIN unit ON observation.unit_id = unit.id
WHERE fermentation_record.qc_pass != 'fail'
GROUP BY fermentation_record.resource_id,
         resource.name,
         location_address.geography_id,
         place.county_name,
         strain.name,
         strain.genus,
         strain.species,
         pm.name,
         em.name,
         bcm.name,
         coalesce(pm.duration, em.duration, bcm.time_h),
         parameter.name,
         unit.name
"""

PREVIOUS_MV_SQL = """
CREATE MATERIALIZED VIEW data_portal.mv_biomass_fermentation AS
SELECT row_number() OVER (
           ORDER BY fermentation_record.resource_id,
                    location_address.geography_id,
                    strain.name,
                    pm.name,
                    em.name,
                    bcm.name,
                    parameter.name,
                    unit.name
       ) AS id,
       fermentation_record.resource_id,
       resource.name AS resource_name,
       location_address.geography_id AS geoid,
       place.county_name AS county,
       LEFT(strain.genus, 1) || '. ' || strain.species AS species_display_name,
       pm.name AS pretreatment_method,
       em.name AS enzyme_name,
       bcm.name AS bioconversion_method,
       coalesce(pm.duration, em.duration, bcm.time_h) AS elapsed_time,
       parameter.name AS product_name,
       avg(observation.value) AS avg_value,
       min(observation.value) AS min_value,
       max(observation.value) AS max_value,
       stddev(observation.value) AS std_dev,
       count(*) AS observation_count,
       unit.name AS unit
FROM fermentation_record
JOIN resource ON fermentation_record.resource_id = resource.id
LEFT OUTER JOIN prepared_sample ON fermentation_record.prepared_sample_id = prepared_sample.id
LEFT OUTER JOIN field_sample ON prepared_sample.field_sample_id = field_sample.id
LEFT OUTER JOIN location_address ON field_sample.sampling_location_id = location_address.id
LEFT OUTER JOIN place ON location_address.geography_id = place.geoid
LEFT OUTER JOIN strain ON fermentation_record.strain_id = strain.id
LEFT OUTER JOIN method AS pm ON fermentation_record.pretreatment_method_id = pm.id
LEFT OUTER JOIN method AS em ON fermentation_record.eh_method_id = em.id
LEFT OUTER JOIN bioconversion_method AS bcm ON fermentation_record.bioconversion_method_id = bcm.id
JOIN observation ON lower(observation.record_id) = lower(fermentation_record.record_id)
JOIN parameter ON observation.parameter_id = parameter.id
LEFT OUTER JOIN unit ON observation.unit_id = unit.id
WHERE fermentation_record.qc_pass != 'fail'
GROUP BY fermentation_record.resource_id,
         resource.name,
         location_address.geography_id,
         place.county_name,
         strain.name,
         strain.genus,
         strain.species,
         pm.name,
         em.name,
         bcm.name,
         coalesce(pm.duration, em.duration, bcm.time_h),
         parameter.name,
         unit.name
"""

def upgrade() -> None:
    """Rename species_display_name to strain_name."""
    for statement in DROP_INDEX_STATEMENTS:
        op.execute(statement)

    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_fermentation CASCADE")
    op.execute(NEW_MV_SQL)

    for statement in CREATE_INDEX_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    """Restore species_display_name."""
    for statement in DROP_INDEX_STATEMENTS:
        op.execute(statement)

    op.execute("DROP MATERIALIZED VIEW IF EXISTS data_portal.mv_biomass_fermentation CASCADE")
    op.execute(PREVIOUS_MV_SQL)

    for statement in PREVIOUS_CREATE_INDEX_STATEMENTS:
        op.execute(statement)
