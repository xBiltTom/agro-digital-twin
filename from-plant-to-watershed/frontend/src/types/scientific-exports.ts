export type ScientificFormat = "png" | "svg" | "pdf" | "csv";
export type ScientificVariant = "PRIMARY" | "EXCLUDE_ESTIMATED";
export type ScientificExportGroup = "results" | "partitions" | "configuration";

export interface ScientificExportEntry {
  id: string;
  title: string;
  group: ScientificExportGroup;
  formats: ScientificFormat[];
  supports_sensitivity: boolean;
}

export interface ScientificExportCatalog {
  experiment_id: string;
  test_interval: [string, string];
  entries: ScientificExportEntry[];
}
