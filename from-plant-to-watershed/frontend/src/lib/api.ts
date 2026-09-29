import {
  TokenResponse,
  LoginPayload,
  RegisterPayload,
  User,
  Role,
  Permission,
  UserProfile,
  ProfileUpdatePayload,
  PasswordChangePayload
} from "../types/auth";
import {
  ClimateScenario,
  Watershed,
  SimulationRun,
  SimulationResult, SwatPlusConfiguration, SwatResultsResponse
  , ExternalModelInfo, DatasetInfo, CurrentFinalScientificReportResponse,
  AIInsightsResponse
} from "../types/simulation";
import { PlaybackPage, PlaybackQuery } from "../types/playback";
import type { SimulationAvailability } from "../types/playback-availability";
import { collectSimulationPages } from "./simulation-access";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiService {
  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("digitaltwin_token");
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData.detail || `Error HTTP ${response.status}: ${response.statusText}`;
      throw new Error(typeof message === "string" ? message : JSON.stringify(message));
    }

    return response.json();
  }

  // --- Auth ---
  async login(payload: LoginPayload): Promise<TokenResponse> {
    return this.request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async register(payload: RegisterPayload): Promise<User> {
    return this.request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async getMe(): Promise<User> {
    return this.request<User>("/auth/me");
  }

  async refreshToken(): Promise<TokenResponse> {
    return this.request<TokenResponse>("/auth/refresh", {
      method: "POST",
    });
  }

  // --- Users (Admin) ---
  async listUsers(skip = 0, limit = 50, role?: string): Promise<User[]> {
    const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
    if (role) params.append("role", role);
    return this.request<User[]>(`/users?${params.toString()}`);
  }

  async updateUser(userId: string, data: { full_name?: string; is_active?: boolean; role_names?: string[] }): Promise<User> {
    return this.request<User>(`/users/${userId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deactivateUser(userId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/users/${userId}`, {
      method: "DELETE",
    });
  }

  // --- Roles & Permissions ---
  async listRoles(): Promise<Role[]> {
    return this.request<Role[]>("/roles");
  }

  async listPermissions(): Promise<Permission[]> {
    return this.request<Permission[]>("/roles/permissions");
  }

  // --- Profile ---
  async getProfile(): Promise<UserProfile> {
    return this.request<UserProfile>("/profile");
  }

  async updateProfile(payload: ProfileUpdatePayload): Promise<UserProfile> {
    return this.request<UserProfile>("/profile", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  }

  async changePassword(payload: PasswordChangePayload): Promise<{ message: string }> {
    return this.request<{ message: string }>("/profile/change-password", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  }

  // --- Simulations & Scientific Engine ---
  async getClimateScenarios(): Promise<ClimateScenario[]> {
    return this.request<ClimateScenario[]>("/simulations/scenarios/all");
  }

  async getWatersheds(): Promise<Watershed[]> {
    return this.request<Watershed[]>("/simulations/watersheds/all");
  }

  async getSimulations(): Promise<SimulationRun[]> {
    return collectSimulationPages((skip, limit) =>
      this.request<SimulationRun[]>(`/simulations?skip=${skip}&limit=${limit}`));
  }

  async getSimulation(id: string): Promise<SimulationRun> {
    return this.request<SimulationRun>(`/simulations/${id}`);
  }

  async getSimulationResults(id: string, limit = 365): Promise<SimulationResult[]> {
    return this.request<SimulationResult[]>(`/simulations/${id}/results?limit=${limit}`);
  }

  async getSwatResults(id: string): Promise<SwatResultsResponse> {
    return this.request<SwatResultsResponse>(`/simulations/${id}/swat-results`);
  }

  async getSimulationAIInsights(id: string): Promise<AIInsightsResponse> {
    return this.request<AIInsightsResponse>(`/simulations/${encodeURIComponent(id)}/ai-insights`);
  }

  async generateSimulationAIInsights(id: string): Promise<AIInsightsResponse> {
    return this.request<AIInsightsResponse>(`/simulations/${encodeURIComponent(id)}/ai-insights`, {
      method: "POST",
    });
  }

  async getPlayback(id: string, query: PlaybackQuery = {}, signal?: AbortSignal): Promise<PlaybackPage> {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) params.set(key, String(value));
    }
    const suffix = params.size ? `?${params}` : "";
    return this.request<PlaybackPage>(`/simulations/${encodeURIComponent(id)}/playback${suffix}`, { signal });
  }

  async getPlaybackAvailability(id: string, date?: string, signal?: AbortSignal): Promise<SimulationAvailability> {
    const suffix = date ? `?date=${encodeURIComponent(date)}` : "";
    return this.request<SimulationAvailability>(`/simulations/${encodeURIComponent(id)}/availability${suffix}`, { signal });
  }

  async createSimulation(data: {
    name: string;
    watershed_id: string;
    scenario_id: string;
    duration_days: number;
    seed: number;
    parameters?: Record<string, number>;
    mode?: "RESEARCH_MULTISCALE" | "DEVELOPMENT_LEGACY_DEMO" | "ML_ASSISTED" | "SWAT_PLUS";
    plant_count?: number;
    hydrology_backend?: string;
    external_model_id?: string;
    management_scenario?: "BASELINE" | "NO_TILL" | "MAIZE_TO_SORGHUM";
    climate_source?: "SYNTHETIC" | "CMIP6_FILE" | "OBSERVED" | "OBSERVED_HYBRID" | "SWAT_PROJECT";
    dataset_ids?: string[];
    dataset_roles?: Record<string, "FORCING" | "OBSERVATION" | "SOIL_INPUT" | "LAND_COVER" | "YIELD_OBSERVATION" | "VALIDATION" | "CONTEXT_ONLY">;
    station_id?: string;
    start_date: string;
    end_date: string;
    swat_plus?: SwatPlusConfiguration;
  }): Promise<SimulationRun> {
    return this.request<SimulationRun>("/simulations", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getCapabilities(): Promise<Record<string, { status: string; evidence_type?: string }>> {
    return this.request("/system/capabilities");
  }

  async getExternalModels(): Promise<ExternalModelInfo[]> {
    return this.request<ExternalModelInfo[]>("/models");
  }

  async getDatasets(): Promise<DatasetInfo[]> {
    return this.request<DatasetInfo[]>("/datasets");
  }

  // --- Reports (PDF, Word, Excel) ---
  async downloadReport(simulationId: string, format: "pdf" | "docx" | "xlsx"): Promise<void> {
    const token = this.getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE}/reports/download/${simulationId}/${format}`, {
      headers,
    });

    if (!res.ok) {
      throw new Error(`Error descargando reporte ${format.toUpperCase()}: ${res.statusText}`);
    }

    // Extraer nombre del archivo del Content-Disposition si está disponible
    let filename = `reporte_simulacion.${format}`;
    const disposition = res.headers.get("content-disposition");
    if (disposition && disposition.includes("filename=")) {
      const match = disposition.match(/filename="?([^";]+)"?/);
      if (match && match[1]) filename = match[1];
    }

    const blob = await res.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(downloadUrl);
    a.remove();
  }

  // Legacy report consumers still use an untyped response.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  async getReportsHistory(): Promise<any[]> {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return this.request<any[]>("/reports/history");
  }

  async getFinalScientificReport(): Promise<CurrentFinalScientificReportResponse> {
    return this.request<CurrentFinalScientificReportResponse>("/reports/final-scientific");
  }
}

export const api = new ApiService();
