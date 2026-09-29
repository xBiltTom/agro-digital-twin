CREATE TABLE IF NOT EXISTS playback_frames (
    simulation_id VARCHAR(36) NOT NULL REFERENCES simulation_runs(id) ON DELETE CASCADE,
    resolution VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    payload JSONB NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    PRIMARY KEY (simulation_id, resolution, date)
);
CREATE INDEX IF NOT EXISTS ix_playback_frames_resolution_date ON playback_frames (resolution, date);
