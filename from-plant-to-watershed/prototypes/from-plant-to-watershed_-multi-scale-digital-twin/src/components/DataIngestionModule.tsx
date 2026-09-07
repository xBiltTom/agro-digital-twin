/**
 * Module 1: Data Ingestion & ETL Pipeline
 * Connectors for USDA NASS, CHIRPS, SoilGrids 2.0, Landsat, and CMIP6.
 * Features Quantile Delta Mapping (QDM) bias correction visualizer and raster ingestion triggers.
 */

import React, { useState } from 'react';
import { DATASET_CONNECTORS } from '../data/mockScientificData';
import { DatasetConnector } from '../types/scientific';
import {
  Database,
  RefreshCw,
  UploadCloud,
  CheckCircle2,
  FileCode,
  SlidersHorizontal,
  Server,
  Download,
  Filter,
} from 'lucide-react';

export const DataIngestionModule: React.FC = () => {
  const [connectors, setConnectors] = useState<DatasetConnector[]>(DATASET_CONNECTORS);
  const [selectedConnector, setSelectedConnector] = useState<DatasetConnector>(DATASET_CONNECTORS[4]); // CMIP6
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [biasMethod, setBiasMethod] = useState<'QDM' | 'EQM' | 'LinearScaling'>('QDM');

  const handleSyncDataset = (id: string) => {
    setSyncingId(id);
    setTimeout(() => {
      setConnectors((prev) =>
        prev.map((conn) =>
          conn.id === id
            ? {
                ...conn,
                status: 'ONLINE',
                lastSynced: new Date().toISOString().replace('T', ' ').substring(0, 16) + ' UTC',
                recordsCount: conn.recordsCount + Math.floor(Math.random() * 45),
              }
            : conn
        )
      );
      setSyncingId(null);
    }, 1500);
  };

  return (
    <div id="data-ingestion-module" className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-6">
      {/* Module Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-xs font-semibold rounded">
              Module 1: Data Ingestion & Bias Correction
            </span>
            <h3 className="text-base font-semibold text-white">Scientific Datasets & Environmental ETL</h3>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Automated connectors for raster NetCDF, GeoTIFF, and REST APIs with Quantile Delta Mapping (QDM).
          </p>
        </div>

        <button
          id="sync-all-datasets-btn"
          onClick={() => handleSyncDataset(connectors[0].id)}
          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium border border-slate-700 flex items-center gap-2 transition"
        >
          <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
          Poll Remote Upstreams
        </button>
      </div>

      {/* Dataset Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {connectors.map((conn) => {
          const isSelected = selectedConnector.id === conn.id;
          const isSyncing = syncingId === conn.id;
          return (
            <div
              key={conn.id}
              onClick={() => setSelectedConnector(conn)}
              className={`p-3 rounded-xl border cursor-pointer transition flex flex-col justify-between ${
                isSelected
                  ? 'bg-slate-950 border-cyan-500 ring-1 ring-cyan-500/40'
                  : 'bg-slate-950/70 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div>
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-white">{conn.source}</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono ${
                      conn.status === 'ONLINE'
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                    }`}
                  >
                    {conn.status}
                  </span>
                </div>
                <div className="text-[11px] text-cyan-400 font-medium mt-0.5">{conn.category}</div>
                <div className="text-[10px] text-slate-400 mt-2 space-y-0.5">
                  <div>Coverage: {conn.temporalRange}</div>
                  <div>Resolution: {conn.spatialResolution}</div>
                  <div>Format: {conn.format}</div>
                </div>
              </div>

              <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-400">
                <span>{conn.recordsCount.toLocaleString()} tiles/records</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSyncDataset(conn.id);
                  }}
                  disabled={isSyncing}
                  className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium"
                >
                  <RefreshCw className={`w-3 h-3 ${isSyncing ? 'animate-spin' : ''}`} />
                  {isSyncing ? 'Syncing...' : 'Sync'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* CMIP6 Bias Correction (Quantile Delta Mapping) Showcase */}
      <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
          <div>
            <span className="text-xs font-semibold text-slate-200 flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4 text-cyan-400" />
              Climate Bias Correction (NASA NEX-GDDP-CMIP6 Downscaling)
            </span>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Quantile Delta Mapping (QDM) preserves model projected relative changes while matching historical empirical CDF.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400 text-[11px]">Method:</span>
            <select
              value={biasMethod}
              onChange={(e) => setBiasMethod(e.target.value as any)}
              className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs focus:outline-none"
            >
              <option value="QDM">Quantile Delta Mapping (QDM - Recommended)</option>
              <option value="EQM">Empirical Quantile Mapping (EQM)</option>
              <option value="LinearScaling">Linear Scaling (LS)</option>
            </select>
          </div>
        </div>

        {/* Quantile Cumulative Distribution Comparison Chart */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-8 bg-slate-900/90 p-3 rounded-lg border border-slate-800">
            <div className="flex justify-between items-center mb-2 text-xs">
              <span className="font-semibold text-slate-300">Empirical Cumulative Distribution Function (ECDF)</span>
              <div className="flex items-center gap-3 text-[10px]">
                <span className="flex items-center gap-1 text-slate-400">
                  <span className="w-2.5 h-1 bg-slate-400" /> Observed (CHIRPS)
                </span>
                <span className="flex items-center gap-1 text-rose-400">
                  <span className="w-2.5 h-1 bg-rose-400 border-dashed" /> Raw GCM (CMIP6)
                </span>
                <span className="flex items-center gap-1 text-cyan-400 font-medium">
                  <span className="w-2.5 h-1 bg-cyan-400" /> QDM Bias-Corrected
                </span>
              </div>
            </div>

            {/* SVG ECDF Chart */}
            <div className="h-40 w-full">
              <svg viewBox="0 0 540 140" className="w-full h-full">
                {/* Axes */}
                <line x1="30" y1="120" x2="520" y2="120" stroke="#334155" strokeWidth="1" />
                <line x1="30" y1="10" x2="30" y2="120" stroke="#334155" strokeWidth="1" />

                {/* Grid lines */}
                <line x1="30" y1="65" x2="520" y2="65" stroke="#1e293b" strokeWidth="1" strokeDasharray="2,2" />
                <text x="5" y="70" fill="#64748b" fontSize="9">F=0.5</text>
                <text x="5" y="15" fill="#64748b" fontSize="9">F=1.0</text>
                <text x="500" y="132" fill="#64748b" fontSize="9">P (mm)</text>

                {/* Observed Historical Curve (Smooth Sigmoid) */}
                <path
                  d="M 30 120 C 140 120, 180 80, 260 40 T 500 12"
                  fill="none"
                  stroke="#94a3b8"
                  strokeWidth="2"
                />

                {/* Raw GCM (Biased Curve shifted left - overestimating drizzle) */}
                <path
                  d="M 30 120 C 80 100, 140 60, 210 30 T 480 12"
                  fill="none"
                  stroke="#f43f5e"
                  strokeWidth="1.8"
                  strokeDasharray="4,2"
                />

                {/* QDM Bias Corrected (Aligned to Observed distribution with climate trend preserved) */}
                <path
                  d="M 30 120 C 135 120, 175 78, 255 38 T 505 10"
                  fill="none"
                  stroke="#38bdf8"
                  strokeWidth="2.5"
                />
              </svg>
            </div>
          </div>

          <div className="lg:col-span-4 bg-slate-900/90 p-3 rounded-lg border border-slate-800 text-xs space-y-2.5">
            <div className="font-semibold text-slate-200">Correction Diagnostics</div>
            <div className="space-y-1 text-slate-300 text-[11px]">
              <div className="flex justify-between">
                <span className="text-slate-400">Precipitation Bias:</span>
                <span className="font-mono text-emerald-400">-0.12 mm/d (Corrected)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Drizzle Frequency Factor:</span>
                <span className="font-mono text-slate-200">Reduced by 34%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Extreme 99th Percentile:</span>
                <span className="font-mono text-cyan-400">+6.4 mm restored</span>
              </div>
              <div className="flex justify-between border-t border-slate-800 pt-1.5">
                <span className="text-slate-400">Target Scenarios:</span>
                <span className="font-mono text-indigo-400">SSP2-4.5 & SSP5-8.5</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
