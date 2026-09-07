/**
 * Scientific types for Multi-Scale Digital Twin
 * Coupling Individual Plant Models (FSPM) with SWAT+ Hydrology and CMIP6 Projections
 */

export type UserRole = 'admin' | 'researcher' | 'analyst' | 'guest';

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  institution: string;
  role: UserRole;
  avatarUrl?: string;
  jwtToken: string;
  refreshToken: string;
}

export interface PlantArchitecture {
  dayOfGrowth: number; // 1 to 120 (VE to R6)
  growthStage: 'VE' | 'V4' | 'V8' | 'V12' | 'VT' | 'R1' | 'R6';
  plantHeightCm: number;
  maxRootDepthCm: number;
  leafAreaIndex: number;
  biomassGrams: number;
  transpirationRateMmDay: number;
  leafCount: number;
  waterStressFactor: number; // 0 (severe stress) to 1 (optimal)
  xylemPotentialMpa: number;
  rootArchitecture: {
    primaryRootDepthCm: number;
    seminalRootCount: number;
    crownRootCount: number;
    lateralBranchingDensity: number; // branches per cm
    rootLengthDensityProfile: { depthCm: number; rldCmPerCm3: number }[];
  };
}

export interface FieldAggregation {
  plantCount: number; // ~1000
  gridDimensionsMeters: { length: number; width: number };
  meanLAI: number;
  spatialVarianceLAI: number;
  fieldETmmDay: number;
  canopyInterceptionMm: number;
  microTopographyVariance: number;
}

export interface SoilHorizon {
  name: string;
  depthRangeCm: [number, number];
  texture: 'Sandy Loam' | 'Clay Loam' | 'Silt Loam' | 'Silty Clay';
  clayPercent: number;
  sandPercent: number;
  organicCarbonGKg: number;
  bulkDensityGcm3: number;
  saturatedConductivityMmHr: number;
  currentWaterContentPct: number;
  fieldCapacityPct: number;
  wiltingPointPct: number;
}

export interface HRUData {
  id: string;
  name: string;
  subbasinId: number;
  areaHa: number;
  landUse: 'Maize (Continuous)' | 'Maize-Soybean' | 'Sorghum' | 'Pasture' | 'Forest';
  soilType: string;
  slopePct: number;
  soilHorizons: SoilHorizon[];
  // Monthly aggregated water balance (mm)
  precipitationMm: number;
  actualETmm: number;
  surfaceRunoffMm: number;
  percolationMm: number;
  soilStorageChangeMm: number;
  cropYieldTonHa: number;
  sedimentYieldTonHa: number;
  coordinates: [number, number][]; // Polygon
}

export interface StreamflowGauge {
  id: string;
  usgsStationId: string;
  name: string;
  drainageAreaKm2: number;
  latitude: number;
  longitude: number;
  observedFlowM3s: number[];
  dates: string[];
}

export interface ScenarioDefinition {
  id: string;
  name: string;
  code: 'baseline' | 'temp_plus2' | 'precip_minus15' | 'conservation_notill' | 'sorghum_replacement';
  description: string;
  climateScenario: 'Historical' | 'SSP2-4.5' | 'SSP5-8.5';
  tempDeltaC: number;
  precipDeltaPct: number;
  co2Ppm: number;
  tillagePractice: 'Conventional' | 'No-Till (Conservation)' | 'Reduced Tillage';
  cropType: 'Maize' | 'Sorghum';
  active: boolean;
}

export interface ValidationMetrics {
  variableName: string;
  timeStep: 'Daily' | 'Monthly' | 'Annual';
  // Standard Hydrological performance
  rmse: number;
  nse: number; // Nash-Sutcliffe Efficiency
  pbias: number; // Percent Bias (%)
  r2: number; // Coefficient of Determination
  kge?: number; // Kling-Gupta Efficiency
  sampleSize: number;
  performanceRating: 'Very Good' | 'Good' | 'Satisfactory' | 'Unsatisfactory';
  
  // Non-parametric statistical tests (Twin vs Standard SWAT+)
  ksTest: {
    statisticD: number;
    pValue: number;
    identicalDistribution: boolean;
  };
  wilcoxonTest: {
    statisticW: number;
    zScore: number;
    pValue: number;
    significantDifference: boolean;
  };

  // Sobol Global Sensitivity Analysis
  sobolIndices: {
    parameter: string;
    description: string;
    firstOrderSi: number; // First order
    totalOrderSTi: number; // Total order
  }[];

  // Bootstrap 95% Confidence Intervals
  bootstrapCI: {
    metric: string;
    observedValue: number;
    ciLower95: number;
    ciUpper95: number;
    standardError: number;
  }[];
}

export interface SimulationJob {
  jobId: string;
  scenarioId: string;
  scenarioName: string;
  startTime: string;
  completionTime?: string;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  progress: number; // 0 - 100
  currentStage: 'Climate Downscaling' | 'FSPM Plant Growth' | 'Field Aggregation' | 'SWAT+ Routing' | 'Statistical Validation' | 'Idle';
  logs: { timestamp: string; level: 'INFO' | 'WARNING' | 'ERROR'; message: string }[];
  resultSummary?: {
    annualStreamflowM3s: number;
    meanAnnualETmm: number;
    meanCropYieldTonHa: number;
    nseScore: number;
    peakDischargeM3s: number;
  };
}

export interface DatasetConnector {
  id: string;
  source: 'USDA NASS' | 'SoilGrids 2.0' | 'CHIRPS' | 'Landsat' | 'NASA NEX-GDDP-CMIP6' | 'USGS Streamflow';
  category: 'Crop & Yield' | 'Soil Grids' | 'Precipitation' | 'Land Cover' | 'Climate Projections' | 'Hydrology';
  temporalRange: string;
  spatialResolution: string;
  format: 'GeoTIFF / NetCDF' | 'REST API / JSON' | 'CSV / OGC WCS';
  lastSynced: string;
  status: 'ONLINE' | 'SYNCED' | 'STANDBY';
  recordsCount: number;
  biasCorrectionApplied?: boolean;
}
