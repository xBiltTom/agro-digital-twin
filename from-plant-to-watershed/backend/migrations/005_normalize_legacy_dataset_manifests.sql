-- Runs created before the MVP provenance manifest have no dataset list.
-- Keep their meaning explicit and compatible with the non-null ORM contract.
UPDATE simulation_runs
SET dataset_ids = '[]'
WHERE dataset_ids IS NULL;
