"use client";
import Link from "next/link";
import SouthForkResearchPanel from "../../components/research/SouthForkResearchPanel";

export default function DashboardPage() {
  return <main className="mx-auto max-w-6xl space-y-5 pb-10">
    <header><h1 className="font-serif text-3xl">Gemelo digital ecohidrológico</h1><p className="mt-2 text-sm text-slate-500">Consulta el experimento actual o ejecuta y explora una reproducción propia.</p></header>
    <nav className="flex flex-wrap gap-5 text-sm"><Link className="underline" href="/simulations">Ejecutar y consultar simulaciones</Link><Link className="underline" href="/reports">Informes y descargas</Link><Link className="underline" href="/twin-3d">Visor del gemelo</Link></nav>
    <SouthForkResearchPanel />
  </main>;
}
