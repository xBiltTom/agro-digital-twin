"use client";

import React, { useEffect, useState } from "react";
import { useTheme } from "../../context/ThemeContext";
import { Sun, Moon } from "lucide-react";

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div
        aria-hidden="true"
        className="h-9 w-9 border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950"
      />
    );
  }

  const isDark = theme === "dark";

  return (
    <button
      onClick={toggleTheme}
      type="button"
      title={isDark ? "Activar tema claro" : "Activar tema oscuro"}
      aria-label={isDark ? "Activar tema claro" : "Activar tema oscuro"}
      className="group flex h-9 w-9 cursor-pointer items-center justify-center border border-slate-200 bg-slate-50 text-slate-700 transition-colors hover:border-slate-400 hover:bg-white hover:text-amber-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-300 dark:hover:border-slate-600 dark:hover:bg-slate-900 dark:hover:text-amber-400 dark:focus-visible:ring-emerald-400"
    >
      {isDark ? (
        <Sun aria-hidden="true" className="h-4 w-4 text-amber-500 dark:text-amber-400" />
      ) : (
        <Moon aria-hidden="true" className="h-4 w-4 text-slate-600 dark:text-slate-300" />
      )}
    </button>
  );
}
