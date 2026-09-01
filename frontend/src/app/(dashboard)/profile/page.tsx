"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "../../../context/AuthContext";
import { api } from "../../../lib/api";
import {
  UserCheck,
  Shield,
  GraduationCap,
  KeyRound,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Save
} from "lucide-react";

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();

  const [institution, setInstitution] = useState("");
  const [department, setDepartment] = useState("");
  const [specialty, setSpecialty] = useState("");
  const [bio, setBio] = useState("");
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileMsg, setProfileMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Password change state
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isChangingPwd, setIsChangingPwd] = useState(false);
  const [pwdMsg, setPwdMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    if (user?.profile) {
      setInstitution(user.profile.institution || "");
      setDepartment(user.profile.department || "");
      setSpecialty(user.profile.scientific_specialty || "");
      setBio(user.profile.bio || "");
    }
  }, [user]);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingProfile(true);
    setProfileMsg(null);
    try {
      await api.updateProfile({
        institution,
        department,
        scientific_specialty: specialty,
        bio,
      });
      await refreshUser();
      setProfileMsg({ type: "success", text: "Perfil científico actualizado correctamente." });
    } catch (err: any) {
      setProfileMsg({ type: "error", text: err.message || "Error al actualizar perfil" });
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwdMsg(null);
    if (newPassword !== confirmPassword) {
      setPwdMsg({ type: "error", text: "Las nuevas contraseñas no coinciden." });
      return;
    }
    if (newPassword.length < 6) {
      setPwdMsg({ type: "error", text: "La nueva contraseña debe tener mínimo 6 caracteres." });
      return;
    }

    setIsChangingPwd(true);
    try {
      await api.changePassword({
        old_password: oldPassword,
        new_password: newPassword,
      });
      setPwdMsg({ type: "success", text: "Contraseña cambiada exitosamente." });
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      setPwdMsg({ type: "error", text: err.message || "Error al cambiar contraseña" });
    } finally {
      setIsChangingPwd(false);
    }
  };

  return (
    <div className="flex flex-col gap-8 max-w-4xl mx-auto transition-colors duration-200">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <UserCheck className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
          <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">Mi Perfil de Investigador</h1>
        </div>
        <p className="text-xs text-zinc-600 dark:text-zinc-400">
          Administra tu información académica, roles asignados y credenciales de seguridad.
        </p>
      </div>

      {/* Role Summary Banner */}
      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-emerald-600 to-cyan-500 p-[1.5px]">
            <div className="w-full h-full bg-slate-50 dark:bg-zinc-950 rounded-[14.5px] flex items-center justify-center text-cyan-700 dark:text-cyan-300 font-bold text-xl">
              {user?.full_name?.charAt(0).toUpperCase()}
            </div>
          </div>
          <div className="flex flex-col">
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">{user?.full_name}</h2>
            <span className="text-xs text-zinc-500 dark:text-zinc-400 font-mono">{user?.email}</span>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {user?.roles?.map((r) => (
                <span
                  key={r.name}
                  className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-100 dark:bg-cyan-950/80 text-cyan-700 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-800/60 flex items-center gap-1 font-medium"
                >
                  <Shield className="w-2.5 h-2.5" />
                  {r.name}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Profile Form */}
      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800/80 shadow-sm dark:shadow-xl">
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-4 flex items-center gap-2">
          <GraduationCap className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          <span>Información Científica e Institucional</span>
        </h3>

        {profileMsg && (
          <div
            className={`mb-4 p-3 rounded-lg border text-xs flex items-center gap-2 ${
              profileMsg.type === "success"
                ? "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-300 dark:border-emerald-500/30 text-emerald-800 dark:text-emerald-300"
                : "bg-rose-50 dark:bg-rose-500/10 border-rose-300 dark:border-rose-500/30 text-rose-800 dark:text-rose-300"
            }`}
          >
            {profileMsg.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0" />
            )}
            <span>{profileMsg.text}</span>
          </div>
        )}

        <form onSubmit={handleUpdateProfile} className="flex flex-col gap-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1.5 font-medium">
                Institución / Universidad
              </label>
              <input
                type="text"
                value={institution}
                onChange={(e) => setInstitution(e.target.value)}
                placeholder="Universidad Nacional de Ingeniería"
                className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-200 text-xs focus:outline-none focus:border-emerald-500/80 shadow-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1.5 font-medium">
                Departamento / Laboratorio
              </label>
              <input
                type="text"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                placeholder="Lab. de Ecohidrología y Cambio Climático"
                className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-200 text-xs focus:outline-none focus:border-emerald-500/80 shadow-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1.5 font-medium">
              Especialidad Científica
            </label>
            <input
              type="text"
              value={specialty}
              onChange={(e) => setSpecialty(e.target.value)}
              placeholder="Modelado Hidrológico SWAT, Sensores y Fisiología Vegetal"
              className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-200 text-xs focus:outline-none focus:border-emerald-500/80 shadow-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1.5 font-medium">
              Biografía / Resumen de Investigación
            </label>
            <textarea
              rows={3}
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              placeholder="Describe tus áreas de investigación y líneas de trabajo..."
              className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-200 text-xs focus:outline-none focus:border-emerald-500/80 shadow-sm"
            />
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isSavingProfile}
              className="px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 dark:bg-emerald-500 dark:hover:bg-emerald-400 text-white dark:text-zinc-950 font-semibold text-xs transition flex items-center gap-2 cursor-pointer shadow-md shadow-emerald-500/20 disabled:opacity-50"
            >
              {isSavingProfile ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Save className="w-3.5 h-3.5" />
              )}
              <span>Guardar Perfil</span>
            </button>
          </div>
        </form>
      </div>

      {/* Change Password */}
      <div className="p-6 rounded-2xl bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-800/80 shadow-sm dark:shadow-xl">
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-4 flex items-center gap-2">
          <KeyRound className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          <span>Cambiar Contraseña</span>
        </h3>

        {pwdMsg && (
          <div
            className={`mb-4 p-3 rounded-lg border text-xs flex items-center gap-2 ${
              pwdMsg.type === "success"
                ? "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-300 dark:border-emerald-500/30 text-emerald-800 dark:text-emerald-300"
                : "bg-rose-50 dark:bg-rose-500/10 border-rose-300 dark:border-rose-500/30 text-rose-800 dark:text-rose-300"
            }`}
          >
            {pwdMsg.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0" />
            )}
            <span>{pwdMsg.text}</span>
          </div>
        )}

        <form onSubmit={handleChangePassword} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1.5 font-medium">
              Contraseña Actual
            </label>
            <input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              required
              className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-200 text-xs focus:outline-none focus:border-amber-500/80 shadow-sm"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1.5 font-medium">
                Nueva Contraseña
              </label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-200 text-xs focus:outline-none focus:border-amber-500/80 shadow-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-mono uppercase text-zinc-600 dark:text-zinc-400 mb-1.5 font-medium">
                Confirmar Nueva Contraseña
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-200 text-xs focus:outline-none focus:border-amber-500/80 shadow-sm"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={isChangingPwd}
              className="px-4 py-2.5 rounded-lg bg-amber-600 hover:bg-amber-500 dark:bg-amber-500 dark:hover:bg-amber-400 text-white dark:text-zinc-950 font-semibold text-xs transition flex items-center gap-2 cursor-pointer shadow-md shadow-amber-500/20 disabled:opacity-50"
            >
              {isChangingPwd ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <KeyRound className="w-3.5 h-3.5" />
              )}
              <span>Actualizar Contraseña</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
