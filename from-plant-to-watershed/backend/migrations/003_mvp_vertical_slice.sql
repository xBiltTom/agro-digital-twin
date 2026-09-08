CREATE TABLE IF NOT EXISTS external_models (
    id VARCHAR(36) PRIMARY KEY, name VARCHAR(160) NOT NULL, target VARCHAR(100) NOT NULL,
    framework VARCHAR(80) NOT NULL, artifact_path TEXT NOT NULL UNIQUE, version VARCHAR(100),
    feature_schema JSON NOT NULL, metrics JSON NOT NULL, checksum VARCHAR(64) NOT NULL,
    loaded_at TIMESTAMP NOT NULL, status VARCHAR(30) NOT NULL, provenance JSON NOT NULL,
    created_at TIMESTAMP NOT NULL, updated_at TIMESTAMP NOT NULL
);
ALTER TABLE simulation_runs ADD COLUMN mode VARCHAR(40) NOT NULL DEFAULT 'DEMO_MULTISCALE';
ALTER TABLE simulation_runs ADD COLUMN plant_count INTEGER NOT NULL DEFAULT 1000;
ALTER TABLE simulation_runs ADD COLUMN hydrology_backend VARCHAR(40) NOT NULL DEFAULT 'SIMPLIFIED';
ALTER TABLE simulation_runs ADD COLUMN external_model_id VARCHAR(36);
ALTER TABLE simulation_runs ADD COLUMN field_aggregates JSON;
ALTER TABLE simulation_runs ADD COLUMN hru_aggregates JSON;
ALTER TABLE simulation_runs ADD COLUMN plant_sample JSON;
ALTER TABLE simulation_runs ADD COLUMN monthly_outputs JSON;
ALTER TABLE simulation_runs ADD COLUMN validation JSON;
ALTER TABLE simulation_runs ADD COLUMN ml_result JSON;
