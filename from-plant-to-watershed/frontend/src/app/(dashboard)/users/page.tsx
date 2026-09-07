"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "../../../context/AuthContext";
import { api } from "../../../lib/api";
import { User, Role } from "../../../types/auth";
import {
  Users,
  Shield,
  Search,
  CheckCircle,
  XCircle,
  Edit2,
  Lock,
  Loader2,
  RefreshCw,
  AlertCircle
} from "lucide-react";

export default function UsersManagementPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [editRoleNames, setEditRoleNames] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const isSuperadmin = currentUser?.roles?.some((r) => r.name === "SUPERADMIN");

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [usersData, rolesData] = await Promise.all([
        api.listUsers(),
        api.listRoles(),
      ]);
      setUsers(usersData);
      setRoles(rolesData);
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Error cargando usuarios" });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const openEditModal = (u: User) => {
    setSelectedUser(u);
    setEditRoleNames(u.roles.map((r) => r.name));
    setMessage(null);
  };

  const handleSaveRoles = async () => {
    if (!selectedUser) return;
    setIsSaving(true);
    setMessage(null);
    try {
      const updated = await api.updateUser(selectedUser.id, {
        role_names: editRoleNames,
      });
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      setMessage({ type: "success", text: `Roles de ${updated.full_name} actualizados.` });
      setSelectedUser(null);
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Error al actualizar roles" });
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleActive = async (u: User) => {
    if (!isSuperadmin) return;
    if (u.id === currentUser?.id) {
      setMessage({ type: "error", text: "No puedes desactivar tu propia cuenta." });
      return;
    }
    try {
      const updated = await api.updateUser(u.id, {
        is_active: !u.is_active,
      });
      setUsers((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      setMessage({
        type: "success",
        text: `Usuario ${updated.full_name} ${updated.is_active ? "activado" : "desactivado"}.`,
      });
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Error al modificar estado" });
    }
  };

  const filteredUsers = users.filter(
    (u) =>
      u.full_name.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase()) ||
      u.roles.some((r) => r.name.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto transition-colors duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Users className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
            <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">
              Administración de Usuarios y Roles (RBAC)
            </h1>
          </div>
          <p className="text-xs text-zinc-600 dark:text-zinc-400 mt-1">
            Control de identidades, asignación de perfiles y privilegios de acceso en el gemelo digital.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={isLoading}
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 text-zinc-700 dark:text-zinc-300 text-xs font-medium transition cursor-pointer shadow-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          <span>Actualizar Lista</span>
        </button>
      </div>

      {message && (
        <div
          className={`p-3 rounded-lg border text-xs flex items-center gap-2 ${
            message.type === "success"
              ? "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-300 dark:border-emerald-500/30 text-emerald-800 dark:text-emerald-300"
              : "bg-rose-50 dark:bg-rose-500/10 border-rose-300 dark:border-rose-500/30 text-rose-800 dark:text-rose-300"
          }`}
        >
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{message.text}</span>
        </div>
      )}

      {/* Filter and Search */}
      <div className="flex items-center gap-3 bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800/80 rounded-xl p-3 shadow-sm">
        <Search className="w-4 h-4 text-zinc-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por nombre, correo o rol..."
          className="w-full bg-transparent text-xs text-zinc-800 dark:text-zinc-200 placeholder:text-zinc-400 focus:outline-none"
        />
      </div>

      {/* Users Table */}
      <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800/80 bg-white dark:bg-zinc-900/40 overflow-hidden shadow-sm dark:shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-zinc-50 dark:bg-zinc-950/80 border-b border-zinc-200 dark:border-zinc-800 text-[11px] font-mono uppercase text-zinc-500 dark:text-zinc-400">
              <tr>
                <th className="py-3 px-4">Usuario</th>
                <th className="py-3 px-4">Institución / Especialidad</th>
                <th className="py-3 px-4">Roles Asignados</th>
                <th className="py-3 px-4">Estado</th>
                <th className="py-3 px-4 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-zinc-400">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto text-emerald-500 mb-2" />
                    <span>Cargando directorio de usuarios...</span>
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-zinc-400">
                    No se encontraron usuarios que coincidan con la búsqueda.
                  </td>
                </tr>
              ) : (
                filteredUsers.map((u) => (
                  <tr key={u.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/30 transition">
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-cyan-100 dark:bg-cyan-950 border border-cyan-300 dark:border-cyan-800/50 flex items-center justify-center text-cyan-700 dark:text-cyan-300 font-semibold text-xs">
                          {u.full_name.charAt(0).toUpperCase()}
                        </div>
                        <div className="flex flex-col">
                          <span className="font-semibold text-zinc-900 dark:text-zinc-200">{u.full_name}</span>
                          <span className="text-[11px] text-zinc-500 dark:text-zinc-400">{u.email}</span>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex flex-col">
                        <span className="text-zinc-800 dark:text-zinc-300 font-medium">
                          {u.profile?.institution || "No especificada"}
                        </span>
                        <span className="text-[11px] text-zinc-500 dark:text-zinc-400">
                          {u.profile?.scientific_specialty || "General"}
                        </span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex flex-wrap gap-1">
                        {u.roles.map((r) => (
                          <span
                            key={r.id}
                            className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700"
                          >
                            {r.name}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      {u.is_active ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-200 dark:border-emerald-500/20">
                          <CheckCircle className="w-3 h-3" />
                          Activo
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-mono text-rose-700 dark:text-rose-400 bg-rose-50 dark:bg-rose-500/10 px-2 py-0.5 rounded border border-rose-200 dark:border-rose-500/20">
                          <XCircle className="w-3 h-3" />
                          Inactivo
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {isSuperadmin && (
                          <>
                            <button
                              onClick={() => openEditModal(u)}
                              className="p-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-600 dark:text-zinc-300 hover:text-cyan-600 dark:hover:text-cyan-300 transition"
                              title="Modificar Roles"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleToggleActive(u)}
                              disabled={u.id === currentUser?.id}
                              className={`p-1.5 rounded-lg border transition ${
                                u.is_active
                                  ? "border-rose-200 dark:border-rose-900/50 hover:bg-rose-50 dark:hover:bg-rose-950/30 text-rose-600 dark:text-rose-400"
                                  : "border-emerald-200 dark:border-emerald-900/50 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400"
                              } disabled:opacity-40`}
                              title={u.is_active ? "Desactivar Usuario" : "Activar Usuario"}
                            >
                              <Lock className="w-3.5 h-3.5" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Roles Modal */}
      {selectedUser && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 shadow-2xl flex flex-col gap-5 text-zinc-900 dark:text-zinc-100">
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                Gestionar Roles de {selectedUser.full_name}
              </h3>
            </div>

            <p className="text-xs text-zinc-600 dark:text-zinc-400">
              Selecciona los roles de acceso científico y técnico asignados a este usuario:
            </p>

            <div className="flex flex-col gap-2 max-h-60 overflow-y-auto">
              {roles.map((r) => {
                const isChecked = editRoleNames.includes(r.name);
                return (
                  <label
                    key={r.id}
                    className={`flex items-center justify-between p-3 rounded-xl border transition cursor-pointer ${
                      isChecked
                        ? "bg-cyan-50 dark:bg-cyan-950/40 border-cyan-300 dark:border-cyan-800/80 text-cyan-900 dark:text-cyan-200"
                        : "bg-zinc-50 dark:bg-zinc-900/40 border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-900"
                    }`}
                  >
                    <div className="flex flex-col">
                      <span className="text-xs font-semibold">{r.name}</span>
                      <span className="text-[10px] text-zinc-500 dark:text-zinc-400 mt-0.5">{r.description}</span>
                    </div>
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setEditRoleNames((prev) => [...prev, r.name]);
                        } else {
                          setEditRoleNames((prev) => prev.filter((name) => name !== r.name));
                        }
                      }}
                      className="accent-cyan-500 w-4 h-4 rounded"
                    />
                  </label>
                );
              })}
            </div>

            <div className="flex items-center justify-end gap-3 mt-2">
              <button
                onClick={() => setSelectedUser(null)}
                className="px-4 py-2 rounded-xl text-xs text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-900 transition cursor-pointer"
              >
                Cancelar
              </button>
              <button
                onClick={handleSaveRoles}
                disabled={isSaving}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold transition cursor-pointer disabled:opacity-50"
              >
                {isSaving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Guardar Cambios</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
