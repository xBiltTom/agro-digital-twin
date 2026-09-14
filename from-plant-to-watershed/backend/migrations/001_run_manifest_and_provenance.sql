-- Non-destructive forward migration for databases created before Phase B.
-- Back up the database and apply exactly once. Fresh installations use create_all.
ALTER TABLE climate_scenarios ADD COLUMN source_type VARCHAR(30) NOT NULL DEFAULT 'SYNTHETIC';
ALTER TABLE simulation_runs ADD COLUMN seed INTEGER NOT NULL DEFAULT 42;
ALTER TABLE simulation_runs ADD COLUMN requested_config JSON;
ALTER TABLE simulation_runs ADD COLUMN effective_config JSON;
ALTER TABLE simulation_runs ADD COLUMN provenance JSON;
ALTER TABLE simulation_runs ADD COLUMN error JSON;
ALTER TABLE simulation_runs ADD COLUMN started_at TIMESTAMP;
ALTER TABLE simulation_runs ADD COLUMN finished_at TIMESTAMP;
ALTER TABLE simulation_results ADD COLUMN water_balance_residual_mm FLOAT NOT NULL DEFAULT 0.0;

-- Existing runs predate manifests and must not be represented as reproducible.
UPDATE simulation_runs
SET provenance = '{"run_evidence_type":"DEMO","legacy":true,"statement":"Legacy run. Effective configuration and seed were not captured at execution time."}'
WHERE provenance IS NULL;
