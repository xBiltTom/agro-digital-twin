export interface ResearchEvaluation {
  hypothesis_status: string;
  eligible_months: number;
  calendar_months: number;
  metrics: Record<string, Record<string, { value: number | null }>>;
  contrasts: Record<string, { rmse_reduction_m3s: number; rmse_reduction_percent: number; ci95_reduction_m3s: [number, number] }>;
}
export interface ResearchReport {
  experiment_id: string;
  test_interval: string[];
  primary: ResearchEvaluation;
  sensitivity: ResearchEvaluation;
  reference_status: string;
  observation_qc: { accepted_days: number; approved_estimated_days: number };
  limitations: string[];
  predictions: { month: string; series: string; variant: string; eligible: boolean; observed: number | null; predicted: number | null }[];
  publications: { year: number; A: string | null; B: string | null }[];
  paper_available: boolean;
}
export interface MonthlyPrediction {
  month: string;
  physical_streamflow_m3s?: number | null;
  observed_streamflow_m3s: number | null;
  predicted_streamflow_m3s: number | null;
}
