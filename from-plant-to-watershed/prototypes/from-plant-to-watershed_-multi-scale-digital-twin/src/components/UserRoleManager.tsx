/**
 * Module 6: User Authentication, Roles, & Profiles (RBAC)
 * Supports JWT authentication, profile editing, and 4 differentiated roles:
 * - Administrador (Full Admin)
 * - Investigador (Researcher: simulations, field upload, validation)
 * - Analista/Policy maker (Dashboard, reports, scenario compare)
 * - Invitado (Guest: read-only public dashboard)
 */

import React, { useState } from 'react';
import { UserProfile, UserRole } from '../types/scientific';
import {
  Shield,
  User,
  Key,
  CheckCircle2,
  XCircle,
  Edit3,
  Save,
  Lock,
  RefreshCw,
  Award,
} from 'lucide-react';

interface UserRoleManagerProps {
  currentUser: UserProfile;
  onRoleChange: (newRole: UserRole) => void;
  onUpdateProfile: (updated: UserProfile) => void;
}

export const UserRoleManager: React.FC<UserRoleManagerProps> = ({
  currentUser,
  onRoleChange,
  onUpdateProfile,
}) => {
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [formData, setFormData] = useState<UserProfile>(currentUser);
  const [showTokenDetails, setShowTokenDetails] = useState<boolean>(false);
  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);

  const roleDefinitions: Record<
    UserRole,
    { title: string; description: string; badgeColor: string; permissions: string[] }
  > = {
    admin: {
      title: 'Administrador (System Admin)',
      description: 'Full administrative authority over database schemas, API keys, datasets, and user accounts.',
      badgeColor: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
      permissions: [
        'User Management & Role Assignment',
        'Global System Configuration & Redis Queues',
        'Dataset Ingestion & CMIP6 Bias Correction Triggers',
        'Execute Simulations & Override Parameters',
        'Export All Reports & Raw Databases',
      ],
    },
    researcher: {
      title: 'Investigador (Principal Investigator)',
      description: 'Scientific research lead with rights to configure FSPM parameters, launch multi-scale jobs, and run validation benchmarks.',
      badgeColor: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
      permissions: [
        'Configure FSPM & SWAT+ Biophysical Parameters',
        'Launch Multi-Scale Simulation Jobs (Celery)',
        'Upload Local In-Situ Field Datasets (CSV, NetCDF)',
        'Execute Statistical Validation Lab (NSE, KS, Sobol)',
        'Export Technical Briefs & Data Workbooks',
      ],
    },
    analyst: {
      title: 'Analista / Policy Maker',
      description: 'Decision support specialist focused on scenario comparisons, climate resilience planning, and stakeholder reports.',
      badgeColor: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
      permissions: [
        'Explore 3D Plant & Watershed Visualizers',
        'Run Predefined Climate Scenarios (Read-Only Mode)',
        'Inspect HRU Water Balances & Yield Deltas',
        'Generate & Download PDF/Word Reports',
      ],
    },
    guest: {
      title: 'Invitado (Public Observer)',
      description: 'Read-only access for academic observers and community water stakeholders.',
      badgeColor: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
      permissions: [
        'View Public Calibrated Hydrographs',
        'Inspect 3D FSPM Organ Models',
        'Inspect General Watershed Metadata',
      ],
    },
  };

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdateProfile(formData);
    setIsEditing(false);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  return (
    <div id="user-role-manager" className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 text-xs font-semibold rounded">
              Module 6: Authentication & Role-Based Access Control
            </span>
            <h3 className="text-base font-semibold text-white">User Profile & RBAC Security Matrix</h3>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            JWT session with refresh tokens and differentiated permissions across 4 institutional roles.
          </p>
        </div>

        {/* Live Role Switcher (Simulator) */}
        <div className="flex items-center gap-2 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
          <span className="text-slate-400 text-[11px] px-2 font-medium">Switch Active Role:</span>
          {(['admin', 'researcher', 'analyst', 'guest'] as UserRole[]).map((r) => (
            <button
              key={r}
              id={`switch-role-${r}-btn`}
              onClick={() => {
                onRoleChange(r);
                setFormData((prev) => ({ ...prev, role: r }));
              }}
              className={`px-2.5 py-1 rounded capitalize font-medium transition ${
                currentUser.role === r
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {savedSuccess && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-center gap-2 text-xs text-emerald-300">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>Profile changes saved successfully.</span>
        </div>
      )}

      {/* Main Grid: User Profile & Permissions Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: User Profile Card */}
        <div className="lg:col-span-5 bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-4 text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="font-semibold text-slate-200 flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-indigo-400" />
              Active User Identity
            </span>
            <button
              onClick={() => setIsEditing(!isEditing)}
              className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 text-[11px]"
            >
              <Edit3 className="w-3 h-3" />
              {isEditing ? 'Cancel' : 'Edit Profile'}
            </button>
          </div>

          {!isEditing ? (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white text-base">
                  {currentUser.name.charAt(0)}
                </div>
                <div>
                  <div className="font-semibold text-white text-sm">{currentUser.name}</div>
                  <div className="text-slate-400 text-[11px]">{currentUser.email}</div>
                  <div className="text-slate-400 text-[10px]">{currentUser.institution}</div>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-800/80 space-y-1.5">
                <div className="flex justify-between">
                  <span className="text-slate-400">Assigned Role:</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                      roleDefinitions[currentUser.role].badgeColor
                    }`}
                  >
                    {roleDefinitions[currentUser.role].title}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Auth Mechanism:</span>
                  <span className="font-mono text-slate-300 text-[10px]">OAuth2 / JWT Bearer</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Session Status:</span>
                  <span className="text-emerald-400 font-medium flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    Authenticated
                  </span>
                </div>
              </div>

              {/* JWT Token Inspector */}
              <div className="pt-2 border-t border-slate-800">
                <button
                  onClick={() => setShowTokenDetails(!showTokenDetails)}
                  className="text-[11px] text-slate-400 hover:text-slate-200 flex items-center gap-1"
                >
                  <Key className="w-3 h-3 text-indigo-400" />
                  {showTokenDetails ? 'Hide JWT Claims' : 'Inspect Signed JWT Claims'}
                </button>
                {showTokenDetails && (
                  <div className="mt-2 p-2 bg-slate-900 rounded font-mono text-[10px] text-slate-300 space-y-1 overflow-x-auto border border-slate-800">
                    <div><strong>sub:</strong> {currentUser.id}</div>
                    <div><strong>email:</strong> {currentUser.email}</div>
                    <div><strong>role:</strong> {currentUser.role}</div>
                    <div><strong>iss:</strong> https://twin.agrohydrology.org/auth</div>
                    <div><strong>exp:</strong> {Math.floor(Date.now() / 1000) + 3600}</div>
                    <div className="text-slate-500 pt-1 truncate"><strong>token:</strong> {currentUser.jwtToken.substring(0, 30)}...</div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <form onSubmit={handleSaveProfile} className="space-y-3">
              <div>
                <label className="text-slate-400 block mb-1">Full Name:</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-white"
                  required
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Institutional Email:</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-white"
                  required
                />
              </div>
              <div>
                <label className="text-slate-400 block mb-1">Research Institution / Agency:</label>
                <input
                  type="text"
                  value={formData.institution}
                  onChange={(e) => setFormData({ ...formData, institution: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-white"
                  required
                />
              </div>
              <button
                type="submit"
                className="w-full py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded font-medium flex items-center justify-center gap-1.5 transition"
              >
                <Save className="w-3.5 h-3.5" />
                Save Profile
              </button>
            </form>
          )}
        </div>

        {/* Right: Role Permission Matrix */}
        <div className="lg:col-span-7 bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-4 text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="font-semibold text-slate-200 flex items-center gap-1.5">
              <Shield className="w-3.5 h-3.5 text-indigo-400" />
              Role Permission Matrix & Capabilities
            </span>
            <span className="text-[10px] text-slate-400">Enforced by FastAPI JWT Middleware</span>
          </div>

          <div className="space-y-3">
            {(Object.keys(roleDefinitions) as UserRole[]).map((r) => {
              const def = roleDefinitions[r];
              const isCurrent = currentUser.role === r;
              return (
                <div
                  key={r}
                  className={`p-3 rounded-lg border transition ${
                    isCurrent
                      ? 'bg-slate-900/90 border-indigo-500/80 ring-1 ring-indigo-500/30'
                      : 'bg-slate-900/40 border-slate-800/80 opacity-70'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-white">{def.title}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${def.badgeColor}`}>
                      {isCurrent ? 'Active Role' : 'Available'}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mb-2">{def.description}</p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-[10px]">
                    {def.permissions.map((perm, i) => (
                      <div key={i} className="flex items-center gap-1.5 text-slate-300">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                        <span>{perm}</span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
