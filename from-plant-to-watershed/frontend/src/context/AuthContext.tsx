"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { User, LoginPayload, RegisterPayload } from "../types/auth";
import { api } from "../lib/api";

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  hasRole: (roleName: string) => boolean;
  hasAnyRole: (roleNames: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshUser = useCallback(async () => {
    try {
      const storedToken = localStorage.getItem("digitaltwin_token");
      if (!storedToken) {
        setUser(null);
        setToken(null);
        return;
      }
      setToken(storedToken);
      const currentUser = await api.getMe();
      setUser(currentUser);
    } catch (err) {
      console.warn("Sesión caducada o token inválido:", err);
      localStorage.removeItem("digitaltwin_token");
      setUser(null);
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (payload: LoginPayload) => {
    setIsLoading(true);
    try {
      const response = await api.login(payload);
      localStorage.setItem("digitaltwin_token", response.access_token);
      setToken(response.access_token);
      const currentUser = await api.getMe();
      setUser(currentUser);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (payload: RegisterPayload) => {
    setIsLoading(true);
    try {
      await api.register(payload);
      // Tras registrarse exitosamente, inicia sesión automáticamente
      await login({ email: payload.email, password: payload.password });
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("digitaltwin_token");
    setToken(null);
    setUser(null);
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  };

  const hasRole = (roleName: string): boolean => {
    if (!user) return false;
    const roleNames = user.roles.map((r) => r.name);
    if (roleNames.includes("SUPERADMIN")) return true;
    return roleNames.includes(roleName);
  };

  const hasAnyRole = (roleNames: string[]): boolean => {
    if (!user) return false;
    const userRoles = user.roles.map((r) => r.name);
    if (userRoles.includes("SUPERADMIN")) return true;
    return roleNames.some((r) => userRoles.includes(r));
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refreshUser,
        hasRole,
        hasAnyRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth debe utilizarse dentro de un AuthProvider");
  }
  return context;
}
