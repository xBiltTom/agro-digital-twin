-- Phase C: portable registry and normalized daily observations. No existing rows are changed.
CREATE TABLE IF NOT EXISTS datasets (
    id VARCHAR(36) PRIMARY KEY,
    provider VARCHAR(80) NOT NULL,
    dataset_name VARCHAR(160) NOT NULL,
    version VARCHAR(100),
    variable VARCHAR(80) NOT NULL,
    unit VARCHAR(40) NOT NULL,
    temporal_resolution VARCHAR(40) NOT NULL,
    spatial_support VARCHAR(160) NOT NULL,
    coverage_start DATE,
    coverage_end DATE,
    source_reference TEXT NOT NULL,
    license TEXT,
    evidence_type VARCHAR(30) NOT NULL,
    quality_control JSON NOT NULL,
    metadata_json JSON NOT NULL,
    retrieved_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
CREATE TABLE IF NOT EXISTS dataset_artifacts (
    id VARCHAR(36) PRIMARY KEY,
    dataset_id VARCHAR(36) NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    artifact_kind VARCHAR(20) NOT NULL,
    storage_path TEXT NOT NULL,
    checksum_sha256 VARCHAR(64) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    byte_size INTEGER NOT NULL,
    retrieved_at TIMESTAMP NOT NULL,
    metadata_json JSON NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
CREATE TABLE IF NOT EXISTS streamflow_observations (
    id VARCHAR(36) PRIMARY KEY,
    dataset_id VARCHAR(36) NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    artifact_id VARCHAR(36) REFERENCES dataset_artifacts(id) ON DELETE SET NULL,
    station_id VARCHAR(30) NOT NULL,
    observed_on DATE NOT NULL,
    value_m3s DOUBLE PRECISION,
    original_value DOUBLE PRECISION,
    original_unit VARCHAR(40) NOT NULL,
    variable VARCHAR(80) NOT NULL,
    quality_status VARCHAR(120),
    source TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_streamflow_observations_station_date ON streamflow_observations(station_id, observed_on);
CREATE INDEX IF NOT EXISTS ix_dataset_artifacts_checksum ON dataset_artifacts(checksum_sha256);
