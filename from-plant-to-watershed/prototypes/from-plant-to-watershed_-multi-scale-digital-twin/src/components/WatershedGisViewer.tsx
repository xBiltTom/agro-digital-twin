/**
 * Level 3: Watershed & Hydrologic Response Units (HRUs) GIS Viewer
 * Interactive GIS mapping for SWAT+ hydrological integration, USGS streamflow monitoring,
 * and SoilGrids/Landsat layered inspection.
 */

import React, { useState } from 'react';
import { HRUData } from '../types/scientific';
import { HRU_DATASETS, USGS_STREAMFLOW_GAUGE, WATERSHED_METADATA } from '../data/mockScientificData';
import {
  MapPin,
  Layers,
  Droplet,
  Sun,
  Sprout,
  BarChart3,
  Compass,
  Info,
  ChevronRight,
  TrendingDown,
  Activity,
  Maximize,
} from 'lucide-react';

interface WatershedGisViewerProps {
  onSelectHRU?: (hru: HRUData) => void;
  runoffMultiplier?: number;
}

export const WatershedGisViewer: React.FC<WatershedGisViewerProps> = ({
  onSelectHRU,
  runoffMultiplier = 1.0,
}) => {
  const [selectedHRU, setSelectedHRU] = useState<HRUData>(HRU_DATASETS[0]);
  const [activeLayer, setActiveLayer] = useState<'runoff' | 'et' | 'yield' | 'soilWater'>('runoff');
  const [hoveredHRU, setHoveredHRU] = useState<HRUData | null>(null);
  const [showGaugeDetails, setShowGaugeDetails] = useState<boolean>(false);

  // SVG coordinate transformation for HRU polygons
  // Scale normalized 0..1 coordinates to 600x420 viewBox
  const mapWidth = 640;
  const mapHeight = 440;

  const getPolygonPoints = (coords: [number, number][]) => {
    return coords
      .map(([x, y]) => `${(x * (mapWidth - 80) + 40).toFixed(1)},${(y * (mapHeight - 80) + 40).toFixed(1)}`)
      .join(' ');
  };

  // Color generator for HRU based on active metric
  const getHRUColor = (hru: HRUData) => {
    if (activeLayer === 'runoff') {
      const runoff = hru.surfaceRunoffMm * runoffMultiplier;
      // 0 to 140 mm
      const fraction = Math.min(1, Math.max(0, runoff / 140));
      return fraction > 0.7
        ? 'fill-rose-500/60 stroke-rose-400'
        : fraction > 0.4
        ? 'fill-amber-500/60 stroke-amber-400'
        : 'fill-sky-500/60 stroke-sky-400';
    } else if (activeLayer === 'et') {
      // 550 to 650 mm
      const fraction = Math.min(1, Math.max(0, (hru.actualETmm - 550) / 100));
      return fraction > 0.6
        ? 'fill-emerald-500/60 stroke-emerald-400'
        : 'fill-teal-500/60 stroke-teal-400';
    } else if (activeLayer === 'yield') {
      // 0 to 12 ton/ha
      if (hru.cropYieldTonHa === 0) return 'fill-slate-600/40 stroke-slate-500';
      const fraction = hru.cropYieldTonHa / 12;
      return fraction > 0.85
        ? 'fill-lime-500/60 stroke-lime-400'
        : 'fill-yellow-600/60 stroke-yellow-500';
    } else {
      // Soil water
      return 'fill-indigo-500/60 stroke-indigo-400';
    }
  };

  const handleHRUClick = (hru: HRUData) => {
    setSelectedHRU(hru);
    if (onSelectHRU) onSelectHRU(hru);
  };

  return (
    <div id="watershed-gis-viewer" className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col md:flex-row h-full">
      {/* Left / Main Map Section */}
      <div className="flex-1 relative flex flex-col bg-slate-950">
        {/* Map Header Overlay */}
        <div className="p-3 bg-slate-900/80 backdrop-blur border-b border-slate-800 flex items-center justify-between z-10">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 border border-blue-500/30 text-xs font-semibold rounded">
                Level 3: SWAT+ Hydrological Mesh
              </span>
              <span className="text-xs text-slate-300 font-medium">
                {WATERSHED_METADATA.name}
              </span>
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              Area: {WATERSHED_METADATA.drainageAreaKm2} km² • Soils: SoilGrids 2.0 • Land Use: Landsat 30m
            </div>
          </div>

          {/* Map Layer Switcher */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
            <button
              id="layer-runoff-btn"
              onClick={() => setActiveLayer('runoff')}
              className={`px-2.5 py-1 rounded transition flex items-center gap-1.5 ${
                activeLayer === 'runoff' ? 'bg-sky-600 text-white font-medium shadow-sm' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Droplet className="w-3.5 h-3.5" />
              Surface Runoff
            </button>
            <button
              id="layer-et-btn"
              onClick={() => setActiveLayer('et')}
              className={`px-2.5 py-1 rounded transition flex items-center gap-1.5 ${
                activeLayer === 'et' ? 'bg-emerald-600 text-white font-medium shadow-sm' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Sun className="w-3.5 h-3.5" />
              Actual ET
            </button>
            <button
              id="layer-yield-btn"
              onClick={() => setActiveLayer('yield')}
              className={`px-2.5 py-1 rounded transition flex items-center gap-1.5 ${
                activeLayer === 'yield' ? 'bg-amber-600 text-white font-medium shadow-sm' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Sprout className="w-3.5 h-3.5" />
              Crop Yield
            </button>
          </div>
        </div>

        {/* Interactive SVG GIS Map Canvas */}
        <div className="flex-1 relative flex items-center justify-center p-2 min-h-[380px]">
          <svg
            viewBox={`0 0 ${mapWidth} ${mapHeight}`}
            className="w-full h-full max-h-[440px] drop-shadow-lg"
          >
            <defs>
              {/* Topographic elevation hillshade gradient */}
              <linearGradient id="streamGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.7" />
                <stop offset="100%" stopColor="#0284c7" stopOpacity="1" />
              </linearGradient>
              <pattern id="contourGrid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#334155" strokeWidth="0.4" strokeDasharray="2,2" />
              </pattern>
            </defs>

            {/* Background Map Grid */}
            <rect width={mapWidth} height={mapHeight} fill="#0b1120" />
            <rect width={mapWidth} height={mapHeight} fill="url(#contourGrid)" />

            {/* Watershed Boundary Polyline */}
            <path
              d="M 120 70 Q 240 40 380 50 T 560 110 Q 580 230 520 340 T 360 395 Q 220 390 140 330 T 90 180 Z"
              fill="none"
              stroke="#475569"
              strokeWidth="2.5"
              strokeDasharray="6,4"
            />

            {/* HRU Polygons */}
            {HRU_DATASETS.map((hru) => {
              const isSelected = selectedHRU.id === hru.id;
              const points = getPolygonPoints(hru.coordinates);
              const colorClass = getHRUColor(hru);

              return (
                <g key={hru.id} className="cursor-pointer transition-all">
                  <polygon
                    id={`hru-poly-${hru.id}`}
                    points={points}
                    className={`${colorClass} transition-all duration-200 stroke-[1.8] ${
                      isSelected ? 'stroke-white stroke-[3.5] filter drop-shadow-[0_0_8px_rgba(255,255,255,0.6)]' : 'hover:stroke-slate-200'
                    }`}
                    onClick={() => handleHRUClick(hru)}
                    onMouseEnter={() => setHoveredHRU(hru)}
                    onMouseLeave={() => setHoveredHRU(null)}
                  />
                  {/* HRU ID Centroid Label */}
                  {hru.coordinates.length > 0 && (
                    <text
                      x={(hru.coordinates[0][0] * (mapWidth - 80) + 40) + 20}
                      y={(hru.coordinates[0][1] * (mapHeight - 80) + 40) + 25}
                      fill="#e2e8f0"
                      fontSize="11"
                      fontWeight="600"
                      className="pointer-events-none select-none drop-shadow"
                    >
                      {hru.id}
                    </text>
                  )}
                </g>
              );
            })}

            {/* River Stream Network (Main Channel & Tributaries) */}
            <path
              d="M 520 140 Q 420 180 340 220 T 220 280 T 130 310"
              fill="none"
              stroke="url(#streamGrad)"
              strokeWidth="4"
              strokeLinecap="round"
            />
            <path
              d="M 450 70 Q 390 130 340 220"
              fill="none"
              stroke="#38bdf8"
              strokeWidth="2.5"
              strokeDasharray="4,2"
            />
            <path
              d="M 280 370 Q 250 320 220 280"
              fill="none"
              stroke="#38bdf8"
              strokeWidth="2"
            />

            {/* USGS Streamflow Gauging Station Outlet Pin */}
            <g
              className="cursor-pointer transition transform hover:scale-110"
              onClick={() => setShowGaugeDetails(true)}
            >
              <circle cx="130" cy="310" r="9" fill="#ef4444" className="animate-pulse" />
              <circle cx="130" cy="310" r="4" fill="#ffffff" />
              <text x="145" y="315" fill="#f87171" fontSize="11" fontWeight="700">
                USGS 05464500 (Outlet)
              </text>
            </g>
          </svg>

          {/* Map Compass & Scale Legend */}
          <div className="absolute bottom-3 right-3 bg-slate-900/80 backdrop-blur p-2 rounded-lg border border-slate-800 text-[10px] text-slate-400 space-y-1">
            <div className="flex items-center gap-1.5 font-medium text-slate-300">
              <Compass className="w-3.5 h-3.5 text-indigo-400" />
              Orientation: North Up
            </div>
            <div className="flex items-center gap-2">
              <div className="w-12 h-1 bg-slate-600 rounded" />
              <span>2.5 km</span>
            </div>
          </div>

          {/* Hover HRU Quick Tooltip */}
          {hoveredHRU && (
            <div className="absolute top-3 right-3 bg-slate-900/95 backdrop-blur-md p-2.5 rounded-lg border border-slate-700 shadow-xl text-xs max-w-[210px] pointer-events-none">
              <div className="font-semibold text-white">{hoveredHRU.name}</div>
              <div className="text-slate-400 text-[11px]">{hoveredHRU.landUse}</div>
              <div className="mt-1 text-[11px] grid grid-cols-2 gap-1 text-slate-300">
                <span>Runoff:</span>
                <span className="font-mono text-sky-400">{(hoveredHRU.surfaceRunoffMm * runoffMultiplier).toFixed(1)} mm</span>
                <span>Actual ET:</span>
                <span className="font-mono text-emerald-400">{hoveredHRU.actualETmm} mm</span>
                <span>Yield:</span>
                <span className="font-mono text-amber-400">{hoveredHRU.cropYieldTonHa} t/ha</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right / HRU & SoilGrids Detailed Inspection Drawer */}
      <div className="w-full md:w-80 bg-slate-900/95 border-t md:border-t-0 md:border-l border-slate-800 p-4 flex flex-col justify-between overflow-y-auto max-h-[500px] text-xs">
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-semibold text-indigo-400 uppercase tracking-wider">
                HRU Spatial Unit Inspector
              </span>
              <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-300 font-mono text-[10px] rounded border border-indigo-500/30">
                {selectedHRU.id}
              </span>
            </div>
            <h4 className="text-sm font-semibold text-white mt-1">{selectedHRU.name}</h4>
            <p className="text-[11px] text-slate-400 mt-0.5">{selectedHRU.soilType}</p>
          </div>

          {/* HRU Hydrological Balance Card */}
          <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
            <div className="text-[11px] font-semibold text-slate-300 flex items-center justify-between">
              <span>Annual Water Balance (SWAT+)</span>
              <span className="text-[10px] text-slate-400">P = ET + Q + Perc + ΔS</span>
            </div>

            <div className="space-y-1.5 text-slate-300 text-[11px]">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Precipitation (P):</span>
                <span className="font-mono font-medium text-white">{selectedHRU.precipitationMm} mm</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Actual Evapotranspiration (ET):</span>
                <span className="font-mono font-medium text-emerald-400">{selectedHRU.actualETmm} mm</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Surface Runoff (Q):</span>
                <span className="font-mono font-medium text-sky-400">{(selectedHRU.surfaceRunoffMm * runoffMultiplier).toFixed(1)} mm</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Deep Percolation:</span>
                <span className="font-mono font-medium text-indigo-400">{selectedHRU.percolationMm} mm</span>
              </div>
              <div className="flex justify-between items-center border-t border-slate-800 pt-1">
                <span className="text-slate-400">Soil Water Storage (ΔS):</span>
                <span className="font-mono font-medium text-amber-400">+{selectedHRU.soilStorageChangeMm} mm</span>
              </div>
            </div>
          </div>

          {/* SoilGrids 2.0 Horizon Layer Stratigraphy */}
          <div>
            <div className="text-[11px] font-semibold text-slate-300 mb-1.5 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-amber-400" />
              SoilGrids 2.0 Horizon Profiles
            </div>

            <div className="space-y-2">
              {selectedHRU.soilHorizons.map((horizon, i) => (
                <div key={i} className="bg-slate-950/70 p-2 rounded border border-slate-800 text-[11px] space-y-1">
                  <div className="flex justify-between text-slate-200 font-medium">
                    <span>{horizon.name}</span>
                    <span className="text-slate-400 font-mono">
                      {horizon.depthRangeCm[0]}-{horizon.depthRangeCm[1]} cm
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-1 text-[10px] text-slate-400">
                    <span>Texture: {horizon.texture}</span>
                    <span>Clay: {horizon.clayPercent}% | Sand: {horizon.sandPercent}%</span>
                    <span>K_sat: {horizon.saturatedConductivityMmHr} mm/h</span>
                    <span>Bulk Density: {horizon.bulkDensityGcm3} g/cm³</span>
                  </div>
                  {/* Moisture Bar */}
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden mt-1">
                    <div
                      className="bg-cyan-500 h-full rounded-full"
                      style={{ width: `${(horizon.currentWaterContentPct / horizon.fieldCapacityPct) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* USGS Gauge Link Status */}
        <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            Coupled to Gauge 05464500
          </span>
          <span className="font-mono text-slate-300">Lag: 4.2 hrs</span>
        </div>
      </div>
    </div>
  );
};
