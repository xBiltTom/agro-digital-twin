"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../context/AuthContext";
import Sidebar from "../../components/layout/Sidebar";
import Navbar from "../../components/layout/Navbar";
import { Loader2, Menu } from "lucide-react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex flex-col items-center justify-center gap-4 text-zinc-600 dark:text-zinc-300">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-600 dark:text-emerald-400" />
        <span className="text-xs font-mono text-zinc-500 dark:text-zinc-400">
          Cargando entorno del gemelo digital...
        </span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="h-screen w-screen overflow-hidden bg-slate-50 dark:bg-slate-950 text-zinc-900 dark:text-zinc-100 flex flex-row transition-colors duration-200">
      <div className="hidden h-full md:block"><Sidebar /></div>
      <div className="flex-1 flex flex-col h-full min-w-0 overflow-hidden">
        <details
          className="relative z-40 shrink-0 border-b border-slate-300 bg-white dark:border-slate-800 dark:bg-slate-900 md:hidden"
          onClick={(event) => {
            if ((event.target as HTMLElement).closest("a")) event.currentTarget.open = false;
          }}
        >
          <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-emerald-600">
            <Menu aria-hidden="true" className="h-4 w-4" /> Módulos
          </summary>
          <div className="absolute left-0 top-full h-[calc(100dvh-3rem)] shadow-xl"><Sidebar /></div>
        </details>
        <Navbar />
        <main className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6 md:p-8 bg-slate-100/60 dark:bg-slate-950 transition-colors duration-200">
          {children}
        </main>
      </div>
    </div>
  );
}
