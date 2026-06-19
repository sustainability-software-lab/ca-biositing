-- 1a. Delete phantom blank-key rows
DELETE FROM infrastructure_food_processing_facilities
WHERE name IS NULL AND address IS NULL AND city IS NULL AND zip IS NULL;

-- 1a. Delete phantom blank-key rows
DELETE FROM infrastructure_food_processing_facilities
WHERE address = 'TEST';

-- 1b. Delete the test row
DELETE FROM infrastructure_food_processing_facilities
WHERE name = 'test' AND address = 'test';

-- 1c. Uppercase all identity columns (name, address, city, county, state)
UPDATE infrastructure_food_processing_facilities
SET
    name    = UPPER(name),
    address = UPPER(address),
    city    = UPPER(city),
    county  = UPPER(county),
    state   = UPPER(state)
WHERE
    name    IS DISTINCT FROM UPPER(name)
    OR address IS DISTINCT FROM UPPER(address)
    OR city    IS DISTINCT FROM UPPER(city)
    OR county  IS DISTINCT FROM UPPER(county)
    OR state   IS DISTINCT FROM UPPER(state);

-- 1d. Reset geocode_status='success' rows that have no lat/lon → NULL (pending)
UPDATE infrastructure_food_processing_facilities
SET geocode_status = NULL
WHERE geocode_status = 'success'
  AND (latitude IS NULL OR longitude IS NULL);

-- Verify
SELECT geocode_status, COUNT(*) FROM infrastructure_food_processing_facilities GROUP BY geocode_status;
-- Expect: success ~5821, failed ~3, NULL ~224 (the re-queued rows), no ''
SELECT COUNT(*) FROM infrastructure_food_processing_facilities WHERE name IS NULL AND address IS NULL;
-- Expect: 0

SELECT COUNT(*) FROM infrastructure_food_processing_facilities WHERE address IS NOT NULL;

SELECT COUNT(*) FROM infrastructure_food_processing_facilities WHERE geocode_status IS NULL;

SELECT COUNT(*) FROM infrastructure_food_processing_facilities ;


-- Should return 0 rows if all geocoded facilities are in CA
SELECT name, address, city, latitude, longitude
FROM infrastructure_food_processing_facilities
WHERE latitude IS NOT NULL
  AND (
    latitude  < 32.5 OR latitude  > 42.0 OR
    longitude < -124.5 OR longitude > -114.1
  );

SELECT
    geocode_status,
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
FROM infrastructure_food_processing_facilities
GROUP BY geocode_status
ORDER BY count DESC;

--clear table
TRUNCATE TABLE infrastructure_food_processing_facilities RESTART IDENTITY;
