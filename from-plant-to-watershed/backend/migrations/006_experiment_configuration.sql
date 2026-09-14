-- Explicit experiment period, gauge, and per-run dataset roles.
ALTER TABLE simulation_runs ADD COLUMN station_id VARCHAR(15);
ALTER TABLE simulation_runs ADD COLUMN start_date DATE;
ALTER TABLE simulation_runs ADD COLUMN end_date DATE;
ALTER TABLE simulation_runs ADD COLUMN dataset_roles JSON;
