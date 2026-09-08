-- Registry metadata for a reusable, independently trained ModelBundle.
ALTER TABLE external_models ADD COLUMN bundle_contract_version VARCHAR(100);
ALTER TABLE external_models ADD COLUMN learning_mode VARCHAR(30);
ALTER TABLE external_models ADD COLUMN training_data_type VARCHAR(40);
ALTER TABLE external_models ADD COLUMN training_dataset_version VARCHAR(100);
