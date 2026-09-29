-- Current plant models do not calculate xylem sap velocity. New simulation
-- results store NULL rather than a velocity inferred from daily transpiration.
-- Existing rows are not rewritten. Before rolling back, confirm no row contains
-- NULL, then run: ALTER TABLE simulation_results ALTER COLUMN sap_flow_velocity_cmh SET NOT NULL;
ALTER TABLE simulation_results ALTER COLUMN sap_flow_velocity_cmh DROP NOT NULL;
