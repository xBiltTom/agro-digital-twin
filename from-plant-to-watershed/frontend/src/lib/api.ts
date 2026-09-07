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
  SimulationResult
} from "../types/simulation";

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
    return this.request<SimulationRun[]>("/simulations");
  }

  async getSimulation(id: string): Promise<SimulationRun> {
    return this.request<SimulationRun>(`/simulations/${id}`);
  }

  async getSimulationResults(id: string, limit = 365): Promise<SimulationResult[]> {
    return this.request<SimulationResult[]>(`/simulations/${id}/results?limit=${limit}`);
  }

  async createSimulation(data: {
    name: string;
    watershed_id: string;
    scenario_id: string;
    duration_days: number;
    irrigation_efficiency: number;
    parameters?: any;
  }): Promise<SimulationRun> {
    return this.request<SimulationRun>("/simulations", {
      method: "POST",
      body: JSON.stringify(data),
    });
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

  async getReportsHistory(): Promise<any[]> {
    return this.request<any[]>("/reports/history");
  }
}

export const api = new ApiService();
