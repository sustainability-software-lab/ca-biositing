-- Raw observations with null counts
SELECT COUNT(*) AS total_count,
       SUM(CASE WHEN value IS NULL THEN 1 ELSE 0 END) AS null_values,
       SUM(CASE WHEN parameter_id IS NULL THEN 1 ELSE 0 END) AS null_params,
       SUM(CASE WHEN unit_id IS NULL THEN 1 ELSE 0 END) AS null_units,
       SUM(CASE WHEN dataset_id IS NULL THEN 1 ELSE 0 END) AS null_datasets
FROM observation
WHERE record_type = 'resource_production_record';

-- The 11 NULL value rows - all columns
SELECT id, record_id, record_type, value, parameter_id, unit_id, dataset_id,
       dimension_type_id, dimension_value, dimension_unit_id, note, created_at
FROM observation
WHERE record_type = 'resource_production_record'
  AND value IS NULL
ORDER BY id;

-- Sample of NON-NULL rows - all columns
SELECT id, record_id, record_type, value, parameter_id, unit_id, dataset_id,
       dimension_type_id, dimension_value, dimension_unit_id, note, created_at
FROM observation
WHERE record_type = 'resource_production_record'
  AND value IS NOT NULL
ORDER BY id
LIMIT 10;

-- Group by to find patterns in the NULL rows
SELECT parameter_id, unit_id, dataset_id, COUNT(*) AS count
FROM observation
WHERE record_type = 'resource_production_record'
  AND value IS NULL
GROUP BY parameter_id, unit_id, dataset_id;

-- Count nulls
SELECT SUBSTRING(record_id, '(\d+)$') AS last_part, COUNT(*) AS count, SUM(CASE WHEN value IS NULL THEN 1 ELSE 0 END) AS null_count
FROM observation
WHERE record_type = 'resource_production_record'
GROUP BY SUBSTRING(record_id, '(\d+)$')
ORDER BY last_part;

-- Delete stale observation data
DELETE FROM observation
WHERE record_type = 'resource_production_record'
  AND value IS NULL
  ;

  select
  id,
  name,
  resource_code,
  total_annual_volume,
  county_count,
  volume_unit,
  has_volume_data
from data_portal.mv_biomass_search
where total_annual_volume is not null
order by total_annual_volume desc nulls last
limit 20;

select
  r.name,
  count(*) as production_rows,
  count(distinct pr.geoid) as county_count,
  sum(o.value) as total_volume,
  max(u.name) as unit
from resource_production_record pr
join resource r on r.id = pr.resource_id
left join observation o
  on o.record_id = pr.id::text
 and o.record_type = 'resource_production_record'
left join parameter p on p.id = o.parameter_id
left join unit u on u.id = o.unit_id
where lower(p.name) like '%production%'
group by r.name
order by total_volume desc nulls last;