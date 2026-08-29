"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../context/AuthContext";
import Sidebar from "../../components/layout/Sidebar";
import Navbar from "../../components/layout/Navbar";
import { Loader2 } from "lucide-react";

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
      <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center gap-4 text-zinc-300">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
        <span className="text-xs font-mono text-zinc-400">
          Cargando entorno del gemelo digital...
        </span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-row">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar />
        <main className="flex-1 p-6 md:p-8 overflow-y-auto bg-gradient-to-b from-zinc-950 via-zinc-900/40 to-zinc-950">
          {children}
        </main>
      </div>
    </div>
  );
}
