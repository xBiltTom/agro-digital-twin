-- MVP management and data-source manifest fields. Existing runs remain reproducible legacy/demo runs.
ALTER TABLE simulation_runs ADD COLUMN management_scenario VARCHAR(40) NOT NULL DEFAULT 'BASELINE';
ALTER TABLE simulation_runs ADD COLUMN climate_source VARCHAR(40) NOT NULL DEFAULT 'SYNTHETIC';
ALTER TABLE simulation_runs ADD COLUMN dataset_ids JSON;
