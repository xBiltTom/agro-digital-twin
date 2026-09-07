/**
 * Module 7: API Explorer & OpenAPI / Swagger Documentation
 * Interactive tester for REST API v1 endpoints with OpenAPI 3.1 specifications,
 * curl snippets, pagination, query filters, and live JSON test runner.
 */

import React, { useState } from 'react';
import {
  Code,
  Play,
  Send,
  CheckCircle2,
  Copy,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Database,
  Terminal,
} from 'lucide-react';
import { HRU_DATASETS } from '../data/mockScientificData';

interface ApiEndpoint {
  method: 'GET' | 'POST' | 'DELETE';
  path: string;
  summary: string;
  description: string;
  parameters?: { name: string; type: string; required: boolean; description: string }[];
  requestBodyExample?: object;
  responseExample: object;
}

export const ApiExplorer: React.FC = () => {
  const [selectedEndpointIdx, setSelectedEndpointIdx] = useState<number>(0);
  const [apiResponse, setApiResponse] = useState<string | null>(null);
  const [responseCode, setResponseCode] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [copiedCurl, setCopiedCurl] = useState<boolean>(false);

  const endpoints: ApiEndpoint[] = [
    {
      method: 'POST',
      path: '/api/v1/simulations/run',
      summary: 'Submit asynchronous multi-scale simulation job',
      description: 'Dispatches Celery worker task coupling FSPM plant biophysics with SWAT+ HRUs and downscaled CMIP6 climate forcing. Returns job_id for WebSocket/SSE tracking.',
      requestBodyExample: {
        scenario_id: 'scen-temp2',
        crop_type: 'Maize',
        co2_ppm: 485,
        temperature_delta_c: 2.0,
        precipitation_delta_pct: 0.0,
        tillage_management: 'Conventional',
        spatial_resolution_m: 250,
      },
      responseExample: {
        job_id: 'job-celery-98f2a1c',
        status: 'QUEUED',
        created_at: '2026-09-06T15:30:00Z',
        websocket_url: 'wss://twin.agrohydrology.org/ws/simulations/job-celery-98f2a1c',
        estimated_duration_sec: 14.5,
      },
    },
    {
      method: 'GET',
      path: '/api/v1/simulations/{job_id}/status',
      summary: 'Get simulation job progress and stage logs',
      description: 'Polls Celery/Redis task status, progress percentage (0-100), and telemetry logs from intermediate models.',
      parameters: [
        { name: 'job_id', type: 'string (path)', required: true, description: 'Unique simulation job identifier' },
      ],
      responseExample: {
        job_id: 'job-celery-98f2a1c',
        status: 'COMPLETED',
        progress: 100,
        current_stage: 'Statistical Validation',
        elapsed_seconds: 12.8,
        logs_count: 5,
      },
    },
    {
      method: 'GET',
      path: '/api/v1/data/hru-layers',
      summary: 'Query Hydrologic Response Units (HRUs) with pagination and filters',
      description: 'Fetches spatial HRU polygons, Land Cover classifications (Landsat), and SoilGrids 2.0 stratified horizons with pagination.',
      parameters: [
        { name: 'subbasin_id', type: 'integer (query)', required: false, description: 'Filter by subbasin ID (1 to 3)' },
        { name: 'land_use', type: 'string (query)', required: false, description: 'Filter by crop/land use' },
        { name: 'page', type: 'integer (query)', required: false, description: 'Page number (default: 1)' },
        { name: 'limit', type: 'integer (query)', required: false, description: 'Items per page (default: 10)' },
      ],
      responseExample: {
        page: 1,
        limit: 10,
        total_records: 6,
        data: HRU_DATASETS.slice(0, 2),
      },
    },
    {
      method: 'GET',
      path: '/api/v1/validation/metrics',
      summary: 'Retrieve rigorous statistical benchmarks (NSE, PBIAS, Sobol)',
      description: 'Returns calibration statistics against USGS Station 05464500, non-parametric KS and Wilcoxon tests, and Sobol sensitivity indices.',
      responseExample: {
        calibration_station: 'USGS-05464500',
        hydrology: {
          nse: 0.892,
          pbias: 3.14,
          rmse_m3s: 0.284,
          r2: 0.946,
          rating: 'Very Good (Moriasi et al.)',
        },
        hypothesis_tests: {
          kolmogorov_smirnov: { d_stat: 0.125, p_value: 0.482, result: 'Pass' },
          wilcoxon_signed_rank: { w_stat: 38.5, z_score: -2.64, p_value: 0.0083, result: 'Significant' },
        },
        sobol_indices: [
          { param: 'kt', Si: 0.42, STi: 0.53 },
          { param: 'Zmax', Si: 0.29, STi: 0.38 },
        ],
      },
    },
    {
      method: 'POST',
      path: '/api/v1/reports/generate',
      summary: 'Programmatically trigger publication report export',
      description: 'Generates report in PDF, Excel (.xlsx), or Word (.docx) format with validation figures and simulation data.',
      requestBodyExample: {
        format: 'pdf',
        scenario_id: 'scen-base',
        include_sobol_sensitivity: true,
        include_hru_tables: true,
      },
      responseExample: {
        report_id: 'rep-8823a',
        download_url: '/api/v1/reports/downloads/rep-8823a.pdf',
        format: 'pdf',
        file_size_kb: 420,
      },
    },
  ];

  const currentEp = endpoints[selectedEndpointIdx];

  const handleTestApiCall = () => {
    setIsLoading(true);
    setApiResponse(null);
    setResponseCode(null);

    setTimeout(() => {
      setIsLoading(false);
      setResponseCode(currentEp.method === 'POST' ? 201 : 200);
      setApiResponse(JSON.stringify(currentEp.responseExample, null, 2));
    }, 600);
  };

  const copyCurlCommand = () => {
    const curl =
      currentEp.method === 'POST'
        ? `curl -X POST "https://twin.agrohydrology.org${currentEp.path}" \\\n  -H "Authorization: Bearer <JWT_TOKEN>" \\\n  -H "Content-Type: application/json" \\\n  -d '${JSON.stringify(currentEp.requestBodyExample)}'`
        : `curl -X GET "https://twin.agrohydrology.org${currentEp.path}" \\\n  -H "Authorization: Bearer <JWT_TOKEN>"`;
    navigator.clipboard.writeText(curl);
    setCopiedCurl(true);
    setTimeout(() => setCopiedCurl(false), 2000);
  };

  return (
    <div id="api-explorer-module" className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs font-semibold rounded">
              Module 7: REST API & OpenAPI Specification
            </span>
            <h3 className="text-base font-semibold text-white">Swagger / OpenAPI 3.1 Interactive Explorer</h3>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Async job queue, spatial HRU layers, statistical validation, and report generator endpoints under <code>/api/v1</code>.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="text-slate-400 font-mono">Base URL: /api/v1</span>
          <span className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded border border-slate-700">OpenAPI 3.1</span>
        </div>
      </div>

      {/* Main Split: Endpoint List & Active Tester */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Endpoint List Navigation */}
        <div className="lg:col-span-4 space-y-2">
          <div className="text-xs font-semibold text-slate-300 mb-2">Available Endpoints (/api/v1)</div>
          {endpoints.map((ep, idx) => {
            const isSelected = selectedEndpointIdx === idx;
            return (
              <button
                key={idx}
                id={`ep-btn-${idx}`}
                onClick={() => {
                  setSelectedEndpointIdx(idx);
                  setApiResponse(null);
                  setResponseCode(null);
                }}
                className={`w-full text-left p-3 rounded-lg border transition text-xs flex flex-col gap-1 ${
                  isSelected
                    ? 'bg-slate-950 border-amber-500 ring-1 ring-amber-500/30'
                    : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-2 font-mono">
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                      ep.method === 'POST'
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : 'bg-sky-500/20 text-sky-400'
                    }`}
                  >
                    {ep.method}
                  </span>
                  <span className="text-white font-medium truncate">{ep.path}</span>
                </div>
                <span className="text-[11px] text-slate-400 truncate">{ep.summary}</span>
              </button>
            );
          })}
        </div>

        {/* Right: Endpoint Detail & Live Executor */}
        <div className="lg:col-span-8 bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-4 text-xs">
          {/* Active Endpoint Title Bar */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2 font-mono">
              <span
                className={`px-2 py-0.5 rounded text-xs font-bold ${
                  currentEp.method === 'POST' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-sky-500/20 text-sky-400'
                }`}
              >
                {currentEp.method}
              </span>
              <span className="text-white font-semibold text-sm">{currentEp.path}</span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={copyCurlCommand}
                className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded border border-slate-700 flex items-center gap-1.5 text-[11px] transition"
              >
                <Copy className="w-3 h-3 text-slate-400" />
                {copiedCurl ? 'Copied Curl!' : 'Copy cURL'}
              </button>
              <button
                id="btn-execute-api-call"
                onClick={handleTestApiCall}
                disabled={isLoading}
                className="px-3 py-1 bg-amber-600 hover:bg-amber-500 text-white font-medium rounded flex items-center gap-1.5 transition shadow-sm"
              >
                <Play className="w-3 h-3 fill-white" />
                {isLoading ? 'Executing...' : 'Try It Out'}
              </button>
            </div>
          </div>

          <p className="text-slate-300 leading-relaxed text-[11px]">{currentEp.description}</p>

          {/* Parameters Table if any */}
          {currentEp.parameters && (
            <div className="space-y-1.5">
              <div className="font-semibold text-slate-200 text-[11px]">Request Parameters</div>
              <div className="bg-slate-900 rounded-lg p-2.5 border border-slate-800 space-y-1.5 font-mono text-[10px]">
                {currentEp.parameters.map((p, i) => (
                  <div key={i} className="flex justify-between items-center text-slate-300">
                    <div>
                      <span className="text-indigo-400 font-semibold">{p.name}</span>
                      <span className="text-slate-500 ml-2">({p.type})</span>
                    </div>
                    <span className="text-slate-400 font-sans">{p.description}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Request Body Example if POST */}
          {currentEp.requestBodyExample && (
            <div className="space-y-1.5">
              <div className="font-semibold text-slate-200 text-[11px]">Request Payload (application/json)</div>
              <pre className="bg-slate-900 p-3 rounded-lg border border-slate-800 text-slate-300 font-mono text-[10px] overflow-x-auto">
                {JSON.stringify(currentEp.requestBodyExample, null, 2)}
              </pre>
            </div>
          )}

          {/* Response Box */}
          <div className="space-y-1.5 pt-2 border-t border-slate-800">
            <div className="flex items-center justify-between text-[11px]">
              <span className="font-semibold text-slate-200">Server Response</span>
              {responseCode && (
                <span
                  className={`px-2 py-0.5 rounded font-mono font-bold ${
                    responseCode >= 200 && responseCode < 300
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-rose-500/20 text-rose-400'
                  }`}
                >
                  HTTP {responseCode} {responseCode === 201 ? 'Created' : 'OK'}
                </span>
              )}
            </div>

            <pre className="bg-slate-900/90 p-3 rounded-lg border border-slate-800 text-slate-300 font-mono text-[10px] max-h-56 overflow-y-auto">
              {apiResponse || JSON.stringify(currentEp.responseExample, null, 2)}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};
