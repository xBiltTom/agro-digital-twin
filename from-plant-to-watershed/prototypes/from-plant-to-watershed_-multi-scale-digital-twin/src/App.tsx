/**
 * Main Application Component
 * "From Plant to Watershed: A Multi-Scale Digital Twin Framework Coupling Individual
 * Plant Models with SWAT Hydrology and Downscaled Climate Projections"
 */

import React, { useState } from 'react';
import { UserProfile, UserRole } from './types/scientific';
import { ThreeDPlantViewer } from './components/ThreeDPlantViewer';
import { WatershedGisViewer } from './components/WatershedGisViewer';
import { SimulationOrchestrator } from './components/SimulationOrchestrator';
import { ValidationLab } from './components/ValidationLab';
import { DataIngestionModule } from './components/DataIngestionModule';
import { ReportGenerator } from './components/ReportGenerator';
import { UserRoleManager } from './components/UserRoleManager';
import { ApiExplorer } from './components/ApiExplorer';
import { ArchitectureViewer } from './components/ArchitectureViewer';
import {
  Layers,
  Cpu,
  BarChart3,
  Database,
  FileText,
  Users,
  Code2,
  Terminal,
  Activity,
  Droplets,
  Sprout,
  Shield,
  ExternalLink,
  ChevronRight,
  TrendingUp,
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<
    'dashboard' | 'orchestrator' | 'validation' | 'data' | 'reports' | 'users' | 'api' | 'architecture'
  >('dashboard');

  const [currentUser, setCurrentUser] = useState<UserProfile>({
    id: 'usr-prof-dr-alvarez',
    name: 'Dr. Sofia Alvarez',
    email: 's.alvarez@agri-twin.org',
    institution: 'Institute for Agro-Hydrological Systems & Climate Informatics',
    role: 'researcher',
    jwtToken: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c3ItcHJvZi1kci1hbHZhcmV6Iiwicm9sZSI6InJlc2VhcmNoZXIifQ.scientific_twin_signature',
    refreshToken: 'ref-tok-88492019a',
  });

  const handleRoleChange = (newRole: UserRole) => {
    setCurrentUser((prev) => ({
      ...prev,
      role: newRole,
    }));
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      {/* Top Application Bar */}
      <header className="bg-slate-900/90 backdrop-blur border-b border-slate-800 sticky top-0 z-40 px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-600 via-teal-500 to-indigo-600 flex items-center justify-center shadow-md shadow-emerald-900/30">
            <Sprout className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold tracking-tight text-white">
                From Plant to Watershed: Multi-Scale Digital Twin
              </h1>
              <span className="px-1.5 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono rounded">
                v1.2-Scientific
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              FSPM Individual 3D Plant &bull; Field Aggregation &bull; SWAT+ Hydrology &bull; CMIP6 Projections
            </p>
          </div>
        </div>

        {/* User Identity & Active Role Badge */}
        <div className="flex items-center gap-3">
          <div className="text-right hidden md:block">
            <div className="text-xs font-semibold text-white">{currentUser.name}</div>
            <div className="text-[10px] text-slate-400 flex items-center justify-end gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              Role: <span className="text-indigo-300 font-mono capitalize">{currentUser.role}</span>
            </div>
          </div>

          <button
            id="btn-header-profile"
            onClick={() => setActiveTab('users')}
            className="w-8 h-8 rounded-full bg-indigo-600/80 border border-indigo-500 flex items-center justify-center text-xs font-bold text-white shadow hover:ring-2 hover:ring-indigo-400 transition"
            title="User Profile & Roles"
          >
            {currentUser.name.charAt(0)}
          </button>
        </div>
      </header>

      {/* Navigation Tab Bar */}
      <nav className="bg-slate-900/60 border-b border-slate-800/80 px-4 overflow-x-auto scrollbar-none">
        <div className="flex items-center gap-1 py-1.5 min-w-max text-xs">
          <button
            id="nav-tab-dashboard"
            onClick={() => setActiveTab('dashboard')}
            className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-2 ${
              activeTab === 'dashboard'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            3D Plant & Watershed Twin
          </button>

          <button
            id="nav-tab-orchestrator"
            onClick={() => setActiveTab('orchestrator')}
            className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-2 ${
              activeTab === 'orchestrator'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            Simulation Orchestrator
          </button>

          <button
            id="nav-tab-validation"
            onClick={() => setActiveTab('validation')}
            className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-2 ${
              activeTab === 'validation'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            Validation & Statistical Lab
          </button>

          <button
            id="nav-tab-data"
            onClick={() => setActiveTab('data')}
            className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-2 ${
              activeTab === 'data'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            Data Ingestion & Bias Correction
          </button>

          <button
            id="nav-tab-reports"
            onClick={() => setActiveTab('reports')}
            className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-2 ${
              activeTab === 'reports'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Scientific Reports (PDF/Word/Excel)
          </button>

          <button
            id="nav-tab-users"
            onClick={() => setActiveTab('users')}
            className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-2 ${
              activeTab === 'users'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            Roles & RBAC
          </button>

          <button
            id="nav-tab-api"
            onClick={() => setActiveTab('api')}
            className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-2 ${
              activeTab === 'api'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Code2 className="w-3.5 h-3.5" />
            REST API & Swagger
          </button>

          <button
            id="nav-tab-architecture"
            onClick={() => setActiveTab('architecture')}
            className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-2 ${
              activeTab === 'architecture'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Terminal className="w-3.5 h-3.5" />
            Python Backend Codebase
          </button>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 p-4 max-w-7xl w-full mx-auto space-y-6">
        {/* TAB 1: 3D Plant & Watershed Twin Dashboard */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Top KPI Ribbon */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl">
                <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Coupled NSE</div>
                <div className="text-lg font-bold text-emerald-400 font-mono mt-0.5">0.892</div>
                <div className="text-[10px] text-emerald-500 font-semibold flex items-center gap-1">
                  <span>Very Good</span>
                  <span className="text-slate-500 font-normal">(&gt; 0.75)</span>
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl">
                <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Percent Bias (PBIAS)</div>
                <div className="text-lg font-bold text-cyan-400 font-mono mt-0.5">+3.14 %</div>
                <div className="text-[10px] text-cyan-500 font-semibold flex items-center gap-1">
                  <span>Optimal</span>
                  <span className="text-slate-500 font-normal">(|bias| &lt; 10%)</span>
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl">
                <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Streamflow RMSE</div>
                <div className="text-lg font-bold text-white font-mono mt-0.5">0.284 m³/s</div>
                <div className="text-[10px] text-emerald-400">-32.7% vs SWAT+</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl">
                <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Mean Maize Yield</div>
                <div className="text-lg font-bold text-amber-400 font-mono mt-0.5">11.4 t/ha</div>
                <div className="text-[10px] text-slate-400">USDA NASS Calibrated</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl">
                <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Annual ET</div>
                <div className="text-lg font-bold text-emerald-400 font-mono mt-0.5">582 mm</div>
                <div className="text-[10px] text-slate-400">Transpiration + Interception</div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-3 rounded-xl">
                <div className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">USGS Gauge</div>
                <div className="text-lg font-bold text-rose-400 font-mono mt-0.5">05464500</div>
                <div className="text-[10px] text-slate-400">Walnut Creek, IA</div>
              </div>
            </div>

            {/* Side-by-Side Multi-Scale Visualizers */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left: Level 1 & 2 FSPM 3D Plant/Root Architecture */}
              <div className="lg:col-span-6 flex flex-col">
                <ThreeDPlantViewer currentDay={65} tempDelta={0.0} waterStress={0.92} isSorghum={false} />
              </div>

              {/* Right: Level 3 SWAT+ Watershed & HRUs GIS Map */}
              <div className="lg:col-span-6 flex flex-col">
                <WatershedGisViewer />
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: Simulation Orchestrator */}
        {activeTab === 'orchestrator' && (
          <SimulationOrchestrator userRole={currentUser.role} />
        )}

        {/* TAB 3: Scientific Validation Lab */}
        {activeTab === 'validation' && <ValidationLab />}

        {/* TAB 4: Data Ingestion & Bias Correction */}
        {activeTab === 'data' && <DataIngestionModule />}

        {/* TAB 5: Scientific Reports Generator */}
        {activeTab === 'reports' && <ReportGenerator />}

        {/* TAB 6: Users & Role Management */}
        {activeTab === 'users' && (
          <UserRoleManager
            currentUser={currentUser}
            onRoleChange={handleRoleChange}
            onUpdateProfile={(updated) => setCurrentUser(updated)}
          />
        )}

        {/* TAB 7: REST API & Swagger Explorer */}
        {activeTab === 'api' && <ApiExplorer />}

        {/* TAB 8: Python Backend Architecture Codebase */}
        {activeTab === 'architecture' && <ArchitectureViewer />}
      </main>

      {/* Footer */}
      <footer className="bg-slate-950 border-t border-slate-900 p-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>
            From Plant to Watershed: Multi-Scale Digital Twin Framework &bull; FSPM &bull; SWAT+ &bull; CMIP6
          </span>
          <div className="flex items-center gap-4 text-[11px]">
            <span>Walnut Creek Watershed (HUC-12: 070801050204)</span>
            <span>USGS Station 05464500</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
