/**
 * Multi-Scale Simulation Orchestrator
 * Coupler for FSPM (Plant) → Field → SWAT+ (Watershed) → CMIP6 (Climate)
 * Features async job queue, Celery worker emulation, real-time WebSocket progress,
 * scenario switcher, and interactive Causal DAG.
 */

import React, { useState, useEffect } from 'react';
import { ScenarioDefinition, SimulationJob } from '../types/scientific';
import { PREDEFINED_SCENARIOS } from '../data/mockScientificData';
import { evaluateCausalDAG } from '../services/scientificEngine';
import {
  Play,
  RotateCw,
  Sliders,
  CheckCircle2,
  Clock,
  Terminal,
  ArrowRight,
  TrendingUp,
  Cpu,
  RefreshCw,
  GitBranch,
  Shield,
  Gauge,
  Sparkles,
} from 'lucide-react';

interface SimulationOrchestratorProps {
  onSimulationComplete?: (job: SimulationJob) => void;
  userRole?: string;
}

export const SimulationOrchestrator: React.FC<SimulationOrchestratorProps> = ({
  onSimulationComplete,
  userRole = 'researcher',
}) => {
  const [scenarios, setScenarios] = useState<ScenarioDefinition[]>(PREDEFINED_SCENARIOS);
  const [selectedScenario, setSelectedScenario] = useState<ScenarioDefinition>(PREDEFINED_SCENARIOS[0]);
  const [activeJob, setActiveJob] = useState<SimulationJob | null>(null);
  const [jobHistory, setJobHistory] = useState<SimulationJob[]>([]);

  // DAG Interactive Parameter Modulators
  const [co2Ppm, setCo2Ppm] = useState<number>(selectedScenario.co2Ppm);
  const [tempDelta, setTempDelta] = useState<number>(selectedScenario.tempDeltaC);
  const [precipDelta, setPrecipDelta] = useState<number>(selectedScenario.precipDeltaPct);
  const [tillagePractice, setTillagePractice] = useState<'Conventional' | 'No-Till (Conservation)'>(
    selectedScenario.tillagePractice === 'No-Till (Conservation)' ? 'No-Till (Conservation)' : 'Conventional'
  );
  const [cropType, setCropType] = useState<'Maize' | 'Sorghum'>(selectedScenario.cropType);

  // Synchronize parameter sliders when scenario changes
  useEffect(() => {
    setCo2Ppm(selectedScenario.co2Ppm);
    setTempDelta(selectedScenario.tempDeltaC);
    setPrecipDelta(selectedScenario.precipDeltaPct);
    setTillagePractice(
      selectedScenario.tillagePractice === 'No-Till (Conservation)' ? 'No-Till (Conservation)' : 'Conventional'
    );
    setCropType(selectedScenario.cropType);
  }, [selectedScenario]);

  // Compute Causal DAG real-time outcomes
  const dagOutcomes = evaluateCausalDAG({
    co2Ppm,
    tempDeltaC: tempDelta,
    precipDeltaPct: precipDelta,
    conservationTillage: tillagePractice === 'No-Till (Conservation)',
    cropType,
  });

  // Launch Async Multi-Scale Simulation (Celery + Redis task simulation)
  const handleLaunchSimulation = () => {
    if (userRole === 'guest') {
      alert('Invitado role has read-only access. Switch to Investigador or Administrador to trigger simulations.');
      return;
    }

    const newJobId = `job-celery-${Math.random().toString(36).substring(2, 9)}`;
    const newJob: SimulationJob = {
      jobId: newJobId,
      scenarioId: selectedScenario.id,
      scenarioName: selectedScenario.name,
      startTime: new Date().toISOString().replace('T', ' ').substring(0, 19),
      status: 'RUNNING',
      progress: 5,
      currentStage: 'Climate Downscaling',
      logs: [
        {
          timestamp: new Date().toLocaleTimeString(),
          level: 'INFO',
          message: `[Celery Worker @ ip-10-0-4-12] Dispatched job ${newJobId} with scenario: ${selectedScenario.name}`,
        },
        {
          timestamp: new Date().toLocaleTimeString(),
          level: 'INFO',
          message: `Forcing variables: CO2=${co2Ppm}ppm, ΔT=+${tempDelta}°C, ΔP=${precipDelta}%, Tillage=${tillagePractice}`,
        },
      ],
    };

    setActiveJob(newJob);

    // Progressive stage advancement via simulated WebSocket stream
    const stages: Array<{
      progress: number;
      stage: SimulationJob['currentStage'];
      log: string;
    }> = [
      {
        progress: 25,
        stage: 'Climate Downscaling',
        log: 'NASA NEX-GDDP-CMIP6 bias correction applied (Quantile Delta Mapping on CHIRPS baseline).',
      },
      {
        progress: 50,
        stage: 'FSPM Plant Growth',
        log: `Level 1 FSPM calculated 120 days of Zea mays L. organ growth. Max root depth: 138cm, Peak LAI: 4.85.`,
      },
      {
        progress: 72,
        stage: 'Field Aggregation',
        log: 'Level 2 Field Aggregation processed ~1000 plants with microtopographic variance; Field ET: 585 mm/yr.',
      },
      {
        progress: 90,
        stage: 'SWAT+ Routing',
        log: 'Level 3 SWAT+ HRUs solved: surface runoff, percolation, and channel routing into USGS Gauge 05464500.',
      },
      {
        progress: 100,
        stage: 'Statistical Validation',
        log: 'Level 4 Statistical validation complete: NSE=0.892, PBIAS=3.14%, KS-Test passed (p=0.48). Results stored in TimescaleDB.',
      },
    ];

    let currentStep = 0;
    const interval = setInterval(() => {
      if (currentStep < stages.length) {
        const step = stages[currentStep];
        setActiveJob((prev) => {
          if (!prev) return null;
          return {
            ...prev,
            progress: step.progress,
            currentStage: step.stage,
            logs: [
              ...prev.logs,
              {
                timestamp: new Date().toLocaleTimeString(),
                level: 'INFO',
                message: step.log,
              },
            ],
          };
        });
        currentStep++;
      } else {
        clearInterval(interval);
        setActiveJob((prev) => {
          if (!prev) return null;
          const completed: SimulationJob = {
            ...prev,
            status: 'COMPLETED',
            completionTime: new Date().toISOString().replace('T', ' ').substring(0, 19),
            resultSummary: {
              annualStreamflowM3s: dagOutcomes.watershedYieldM3s,
              meanAnnualETmm: Math.round(560 * dagOutcomes.transpirationModifier),
              meanCropYieldTonHa: parseFloat((11.4 * (1 + dagOutcomes.plantGrowthImpactPct / 100)).toFixed(1)),
              nseScore: 0.892,
              peakDischargeM3s: parseFloat((dagOutcomes.watershedYieldM3s * 2.8).toFixed(1)),
            },
          };
          setJobHistory((h) => [completed, ...h]);
          if (onSimulationComplete) onSimulationComplete(completed);
          return completed;
        });
      }
    }, 1200);
  };

  return (
    <div id="simulation-orchestrator" className="space-y-6">
      {/* Top Header with Scenario Selection Cards */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <Cpu className="w-4 h-4 text-indigo-400" />
              Multi-Scale Simulation Orchestrator
            </h3>
            <p className="text-xs text-slate-400">
              Couples Individual 3D FSPM (Plant) → 1000-Plant Field → SWAT+ (Watershed) → CMIP6 (Climate)
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Worker Status:</span>
            <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[11px] font-mono rounded-full flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Celery Cluster Online (4 Nodes)
            </span>
          </div>
        </div>

        {/* Predefined Scenario Selector Grid */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-2.5">
          {scenarios.map((scen) => {
            const isSelected = selectedScenario.id === scen.id;
            return (
              <button
                key={scen.id}
                id={`btn-select-scen-${scen.code}`}
                onClick={() => setSelectedScenario(scen)}
                className={`text-left p-3 rounded-xl border transition duration-150 flex flex-col justify-between ${
                  isSelected
                    ? 'bg-indigo-950/70 border-indigo-500 text-white shadow-lg ring-1 ring-indigo-500/50'
                    : 'bg-slate-900/80 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-mono text-indigo-400 font-semibold">{scen.climateScenario}</span>
                    {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />}
                  </div>
                  <div className="font-medium text-xs text-white mt-1">{scen.name}</div>
                  <p className="text-[10px] text-slate-400 line-clamp-2 mt-1 leading-snug">{scen.description}</p>
                </div>
                <div className="mt-2.5 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono">
                  <span>ΔT: {scen.tempDeltaC >= 0 ? `+${scen.tempDeltaC}` : scen.tempDeltaC}°C</span>
                  <span>ΔP: {scen.precipDeltaPct}%</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Interactive Causal DAG & Biophysical Parameter Modulation */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Parameter Sliders */}
        <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-4 text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="font-semibold text-slate-200 flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-indigo-400" />
              Biophysical & Management Controls
            </span>
            <span className="text-[10px] text-slate-400 font-mono">Live Sensitivity Input</span>
          </div>

          {/* Temperature Slider */}
          <div className="space-y-1">
            <div className="flex justify-between text-slate-300">
              <span>Atmospheric Thermal Forcing (ΔT):</span>
              <span className="font-mono font-bold text-amber-400">
                {tempDelta >= 0 ? `+${tempDelta}` : tempDelta} °C
              </span>
            </div>
            <input
              id="slider-temp-delta"
              type="range"
              min="-1.0"
              max="4.0"
              step="0.5"
              value={tempDelta}
              onChange={(e) => setTempDelta(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-amber-500"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>-1.0 °C</span>
              <span>0 °C (Hist)</span>
              <span>+2.0 °C (SSP2-4.5)</span>
              <span>+4.0 °C (SSP5-8.5)</span>
            </div>
          </div>

          {/* Precipitation Slider */}
          <div className="space-y-1">
            <div className="flex justify-between text-slate-300">
              <span>Precipitation Delta (CHIRPS Forcing):</span>
              <span className="font-mono font-bold text-sky-400">
                {precipDelta >= 0 ? `+${precipDelta}` : precipDelta} %
              </span>
            </div>
            <input
              id="slider-precip-delta"
              type="range"
              min="-30"
              max="30"
              step="5"
              value={precipDelta}
              onChange={(e) => setPrecipDelta(parseInt(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>-30% (Severe Drought)</span>
              <span>0% Baseline</span>
              <span>+30% (Surplus)</span>
            </div>
          </div>

          {/* CO2 Concentration Slider */}
          <div className="space-y-1">
            <div className="flex justify-between text-slate-300">
              <span>CO₂ Atmospheric Concentration:</span>
              <span className="font-mono font-bold text-emerald-400">{co2Ppm} ppm</span>
            </div>
            <input
              id="slider-co2-ppm"
              type="range"
              min="415"
              max="700"
              step="25"
              value={co2Ppm}
              onChange={(e) => setCo2Ppm(parseInt(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>418 ppm (2024)</span>
              <span>550 ppm</span>
              <span>700 ppm (High SSP5)</span>
            </div>
          </div>

          {/* Agricultural Management Modulators */}
          <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-800">
            <div>
              <label className="text-slate-400 block mb-1">Tillage Management:</label>
              <select
                id="select-tillage"
                value={tillagePractice}
                onChange={(e) => setTillagePractice(e.target.value as any)}
                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
              >
                <option value="Conventional">Conventional Tillage</option>
                <option value="No-Till (Conservation)">No-Till (Conservation + Cover)</option>
              </select>
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Crop Species:</label>
              <select
                id="select-crop-type"
                value={cropType}
                onChange={(e) => setCropType(e.target.value as any)}
                className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
              >
                <option value="Maize">Zea mays (Maize)</option>
                <option value="Sorghum">Sorghum bicolor (Sorghum)</option>
              </select>
            </div>
          </div>

          {/* Launch Button */}
          <button
            id="launch-simulation-btn"
            onClick={handleLaunchSimulation}
            disabled={activeJob?.status === 'RUNNING'}
            className={`w-full py-2.5 px-4 rounded-lg font-semibold text-xs transition flex items-center justify-center gap-2 ${
              activeJob?.status === 'RUNNING'
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30'
            }`}
          >
            {activeJob?.status === 'RUNNING' ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
                Executing Coupled Simulation...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                Execute Multi-Scale Simulation (Celery)
              </>
            )}
          </button>
        </div>

        {/* Right: Causal DAG Interactive Flowchart */}
        <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between text-xs">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
              <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                <GitBranch className="w-3.5 h-3.5 text-emerald-400" />
                Agro-Hydrological Causal DAG (System Dynamics)
              </span>
              <span className="text-[10px] text-slate-400">
                Management modulations alter causality arrows
              </span>
            </div>

            {/* Causal Chain Nodes */}
            <div className="space-y-3">
              {/* Row 1: Forcing Drivers */}
              <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 bg-purple-500/20 text-purple-300 font-semibold rounded text-[10px]">
                    CLIMATE FORCING
                  </span>
                  <span className="text-slate-300 font-medium">CO₂ + Temperature + Precipitation</span>
                </div>
                <div className="text-[11px] font-mono text-slate-400">
                  {co2Ppm}ppm | {tempDelta >= 0 ? `+${tempDelta}` : tempDelta}°C | {precipDelta}%
                </div>
              </div>

              {/* Arrow Down */}
              <div className="flex justify-center -my-1 text-slate-600">
                <div className="flex items-center gap-1 text-[10px] text-indigo-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                  <span>Modulated by Plant Stomatal Conductance & Species WUE</span>
                  <ArrowRight className="w-3 h-3 rotate-90" />
                </div>
              </div>

              {/* Row 2: Level 1 FSPM Plant Growth */}
              <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-300 font-semibold rounded text-[10px]">
                    LEVEL 1 & 2: FSPM CANOPY / ROOTS
                  </span>
                  <span className="text-slate-300 font-medium">Biomass, LAI & Root Water Uptake</span>
                </div>
                <div className="text-[11px] font-mono font-semibold text-emerald-400">
                  Growth: {dagOutcomes.plantGrowthImpactPct >= 0 ? `+${dagOutcomes.plantGrowthImpactPct}` : dagOutcomes.plantGrowthImpactPct}%
                </div>
              </div>

              {/* Arrow Down */}
              <div className="flex justify-center -my-1 text-slate-600">
                <div className="flex items-center gap-1 text-[10px] text-cyan-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                  <span>Modulated by Tillage Practice (Infiltration vs Runoff Partitioning)</span>
                  <ArrowRight className="w-3 h-3 rotate-90" />
                </div>
              </div>

              {/* Row 3: Level 3 SWAT+ Hydrology Partitioning */}
              <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 grid grid-cols-2 gap-2">
                <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-400">Actual ET Flux:</div>
                  <div className="text-sm font-semibold font-mono text-emerald-400">
                    {(dagOutcomes.transpirationModifier * 100).toFixed(0)}% of potential
                  </div>
                </div>
                <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-400">Surface Runoff Response:</div>
                  <div className="text-sm font-semibold font-mono text-sky-400">
                    {dagOutcomes.surfaceRunoffDeltaPct >= 0 ? `+${dagOutcomes.surfaceRunoffDeltaPct}` : dagOutcomes.surfaceRunoffDeltaPct}%
                  </div>
                </div>
              </div>

              {/* Arrow Down */}
              <div className="flex justify-center -my-1 text-slate-600">
                <div className="flex items-center gap-1 text-[10px] text-amber-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                  <span>Hydrologic Channel Routing into USGS Station 05464500</span>
                  <ArrowRight className="w-3 h-3 rotate-90" />
                </div>
              </div>

              {/* Row 4: End Target: Watershed Water Availability */}
              <div className="p-2.5 bg-indigo-950/40 rounded-lg border border-indigo-500/40 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 bg-indigo-500/30 text-indigo-200 font-semibold rounded text-[10px]">
                    WATERSHED WATER YIELD
                  </span>
                  <span className="text-white font-semibold">Mean Discharge Availability</span>
                </div>
                <div className="text-base font-bold font-mono text-cyan-300">
                  {dagOutcomes.watershedYieldM3s} m³/s
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Live Celery Worker Streaming Progress & Terminal Logs */}
      {activeJob && (
        <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-3 text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-emerald-400" />
              <span className="font-semibold text-white">
                Task Execution Pipeline: {activeJob.jobId}
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-mono ${
                  activeJob.status === 'COMPLETED'
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-amber-500/20 text-amber-400 border border-amber-500/30 animate-pulse'
                }`}
              >
                {activeJob.status} ({activeJob.progress}%)
              </span>
            </div>
            <span className="text-slate-400 font-mono text-[11px]">
              Stage: <span className="text-indigo-400 font-medium">{activeJob.currentStage}</span>
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className="bg-indigo-500 h-full rounded-full transition-all duration-500 ease-out"
              style={{ width: `${activeJob.progress}%` }}
            />
          </div>

          {/* Terminal Console Output */}
          <div className="bg-slate-900/90 rounded-lg p-3 font-mono text-[11px] text-slate-300 max-h-36 overflow-y-auto space-y-1 border border-slate-800">
            {activeJob.logs.map((log, index) => (
              <div key={index} className="flex gap-2">
                <span className="text-slate-500 select-none">[{log.timestamp}]</span>
                <span className={log.level === 'INFO' ? 'text-emerald-400' : 'text-amber-400'}>
                  [{log.level}]
                </span>
                <span>{log.message}</span>
              </div>
            ))}
          </div>

          {/* Completed Job KPIs Banner */}
          {activeJob.status === 'COMPLETED' && activeJob.resultSummary && (
            <div className="p-3 bg-emerald-950/30 border border-emerald-500/30 rounded-lg grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
              <div>
                <div className="text-[10px] text-slate-400">Mean Streamflow</div>
                <div className="text-sm font-bold text-white font-mono">
                  {activeJob.resultSummary.annualStreamflowM3s} m³/s
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-400">Coupled NSE Score</div>
                <div className="text-sm font-bold text-emerald-400 font-mono">
                  {activeJob.resultSummary.nseScore} (Very Good)
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-400">Mean Crop Yield</div>
                <div className="text-sm font-bold text-amber-400 font-mono">
                  {activeJob.resultSummary.meanCropYieldTonHa} ton/ha
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-400">Peak Discharge</div>
                <div className="text-sm font-bold text-cyan-400 font-mono">
                  {activeJob.resultSummary.peakDischargeM3s} m³/s
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
