"use client";

import { useMemo, useState } from "react";
import {
  Layers,
  Waves,
  Calendar,
  X,
  Search,
  Filter,
  Info,
  Sprout,
  ShieldAlert,
} from "lucide-react";
import type { PlaybackRecord, VariableState } from "../../types/playback";
import { variableText } from "../../lib/playback-scene";

interface Props {
  record: PlaybackRecord;
  isOpen: boolean;
  onClose: () => void;
  initialTab?: "hrus" | "channels" | "calendars";
  onSelectPlant?: (plantId: string) => void;
  onNavigateToScale?: (scale: "MESO" | "MICRO") => void;
}

function EvidenceBadge({ evidence }: { evidence?: string }) {
  if (!evidence) return <span className="text-[10px] text-zinc-500">N/D</span>;
  const color =
    evidence === "MODELLED_SWAT_PLUS"
      ? "bg-teal-500/20 text-teal-300 border-teal-500/30"
      : evidence === "SIMPLIFIED_FSPM"
      ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
      : evidence === "DERIVED"
      ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
      : evidence === "OBSERVED"
      ? "bg-sky-500/20 text-sky-300 border-sky-500/30"
      : "bg-zinc-700/30 text-zinc-400 border-zinc-700";

  const label =
    evidence === "MODELLED_SWAT_PLUS"
      ? "SWAT+ Modelado"
      : evidence === "SIMPLIFIED_FSPM"
      ? "FSPM Simulado"
      : evidence === "DERIVED"
      ? "Estimación Derivada"
      : evidence === "OBSERVED"
      ? "Observado USGS"
      : evidence;

  return (
    <span className={`rounded border px-1.5 py-0.5 text-[9px] font-mono ${color}`}>
      {label}
    </span>
  );
}

function VariableRow({ name, state }: { name: string; state?: VariableState }) {
  return (
    <div className="flex flex-col gap-0.5 border-b border-zinc-800/80 py-1.5 last:border-b-0">
      <div className="flex items-center justify-between text-xs">
        <span className="text-zinc-300">{name}</span>
        <span className="font-mono font-semibold text-zinc-100">
          {variableText(state)}
        </span>
      </div>
      <div className="flex items-center justify-between text-[10px] text-zinc-400">
        <EvidenceBadge evidence={state?.evidence} />
        <span className="text-right truncate max-w-[200px]" title={state?.source ?? ""}>
          {state?.source ?? "Fuente no declarada"}
        </span>
      </div>
      {state?.limitation && (
        <div className="text-[9px] text-amber-300/80 italic">
          Límite: {state.limitation}
        </div>
      )}
    </div>
  );
}

export default function MacroEntityExplorer({
  record,
  isOpen,
  onClose,
  initialTab = "hrus",
  onSelectPlant,
  onNavigateToScale,
}: Props) {
  const [activeTab, setActiveTab] = useState<"hrus" | "channels" | "calendars">(initialTab);
  const [hruFilter, setHruFilter] = useState<"all" | "active" | "fallow">("all");
  const [searchHru, setSearchHru] = useState("");
  const [selectedHruId, setSelectedHruId] = useState<string | null>(null);

  const [searchChannel, setSearchChannel] = useState("");
  const [selectedChannelId, setSelectedChannelId] = useState<string | null>("25");

  const filteredHrus = useMemo(() => {
    return record.hru_results.filter((hru) => {
      const matchSearch =
        searchHru === "" ||
        hru.hru_id.toLowerCase().includes(searchHru.toLowerCase()) ||
        (hru.calendar_id ?? "").toLowerCase().includes(searchHru.toLowerCase()) ||
        (hru.gis_id ?? "").toLowerCase().includes(searchHru.toLowerCase());

      const isActive = hru.crop?.active === true;
      const matchFilter =
        hruFilter === "all" ||
        (hruFilter === "active" && isActive) ||
        (hruFilter === "fallow" && !isActive);

      return matchSearch && matchFilter;
    });
  }, [record.hru_results, searchHru, hruFilter]);

  const filteredChannels = useMemo(() => {
    return record.channel_results.filter((ch) => {
      return (
        searchChannel === "" ||
        ch.channel_id.toLowerCase().includes(searchChannel.toLowerCase()) ||
        (ch.gis_id ?? "").toLowerCase().includes(searchChannel.toLowerCase())
      );
    });
  }, [record.channel_results, searchChannel]);

  const selectedHru = useMemo(() => {
    if (!selectedHruId) return record.hru_results[0] ?? null;
    return record.hru_results.find((h) => h.hru_id === selectedHruId) ?? record.hru_results[0] ?? null;
  }, [record.hru_results, selectedHruId]);

  const selectedChannel = useMemo(() => {
    if (!selectedChannelId) return record.channel_results.find((c) => c.gis_id === "153") ?? record.channel_results[0] ?? null;
    return record.channel_results.find((c) => c.channel_id === selectedChannelId) ?? record.channel_results[0] ?? null;
  }, [record.channel_results, selectedChannelId]);

  // Grupos de calendarios de maíz
  const calendarGroups = useMemo(() => {
    const groupsMap = new Map<string, {
      calendarId: string;
      hruIds: string[];
      activeSampleCount: number;
      samplePlantIds: string[];
    }>();

    record.hru_results.forEach((hru) => {
      if (hru.calendar_id) {
        if (!groupsMap.has(hru.calendar_id)) {
          groupsMap.set(hru.calendar_id, {
            calendarId: hru.calendar_id,
            hruIds: [],
            activeSampleCount: 0,
            samplePlantIds: [],
          });
        }
        groupsMap.get(hru.calendar_id)!.hruIds.push(hru.hru_id);
      }
    });

    record.plant_samples.forEach((sample) => {
      if (sample.calendar_id && groupsMap.has(sample.calendar_id)) {
        const g = groupsMap.get(sample.calendar_id)!;
        g.activeSampleCount += 1;
        g.samplePlantIds.push(sample.plant_id);
      }
    });

    return Array.from(groupsMap.values());
  }, [record.hru_results, record.plant_samples]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-3 backdrop-blur-sm sm:p-6">
      <div className="flex h-full max-h-[88vh] w-full max-w-5xl flex-col rounded-2xl border border-zinc-700 bg-zinc-950 text-zinc-100 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900/80 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500/20 text-cyan-300">
              <Layers className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-zinc-100 sm:text-base">
                Explorador Científico Multiescala · South Fork 2019
              </h2>
              <p className="text-[11px] text-zinc-400">
                Estados diarios SWAT+ y acoplamiento FSPM · Fecha: <b className="text-cyan-300">{record.date}</b> ({record.resolution})
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-white transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Alerta de restricción científica: contexto vs resultados */}
        <div className="flex items-center gap-2 border-b border-amber-500/20 bg-amber-950/30 px-4 py-2 text-[11px] text-amber-300 sm:px-6">
          <ShieldAlert className="h-4 w-4 shrink-0 text-amber-400" />
          <p>
            <b>Restricción científica:</b> los polígonos y la red fluvial 3D son geometrías contextuales esquemáticas. No existe correspondencia GIS 1:1 verificada con las HRUs ni tramos de canal. Los valores mostrados abajo son los resultados oficiales calculados por SWAT+ y FSPM.
          </p>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-zinc-800 bg-zinc-900/50 px-4 sm:px-6">
          <button
            onClick={() => setActiveTab("hrus")}
            className={`flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-xs font-semibold transition ${
              activeTab === "hrus"
                ? "border-cyan-400 text-cyan-300"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Layers className="h-3.5 w-3.5" />
            36 Unidades Hidrológicas (HRUs)
          </button>
          <button
            onClick={() => setActiveTab("channels")}
            className={`flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-xs font-semibold transition ${
              activeTab === "channels"
                ? "border-cyan-400 text-cyan-300"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Waves className="h-3.5 w-3.5" />
            37 Canales SWAT+
          </button>
          <button
            onClick={() => setActiveTab("calendars")}
            className={`flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-xs font-semibold transition ${
              activeTab === "calendars"
                ? "border-cyan-400 text-cyan-300"
                : "border-transparent text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Calendar className="h-3.5 w-3.5" />
            7 Calendarios de Manejo (32 HRU de maíz)
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-hidden p-4 sm:p-6">
          {/* TAB 1: HRUS */}
          {activeTab === "hrus" && (
            <div className="grid h-full grid-cols-1 gap-4 lg:grid-cols-12 overflow-hidden">
              {/* Lista y Filtros de HRUs */}
              <div className="flex flex-col gap-3 lg:col-span-6 overflow-hidden">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="relative flex-1">
                    <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-zinc-500" />
                    <input
                      type="text"
                      placeholder="Buscar HRU por ID o calendario…"
                      value={searchHru}
                      onChange={(e) => setSearchHru(e.target.value)}
                      className="w-full rounded-lg border border-zinc-800 bg-zinc-900/90 py-1.5 pl-8 pr-3 text-xs text-zinc-100 placeholder-zinc-500 focus:border-cyan-500 focus:outline-none"
                    />
                  </div>
                  <div className="flex items-center gap-1 text-xs">
                    <Filter className="h-3.5 w-3.5 text-zinc-400" />
                    <select
                      value={hruFilter}
                      onChange={(e) => setHruFilter(e.target.value as "all" | "active" | "fallow")}
                      className="rounded-lg border border-zinc-800 bg-zinc-900 px-2 py-1.5 text-xs text-zinc-200"
                    >
                      <option value="all">Todas ({record.hru_results.length})</option>
                      <option value="active">Cultivo activo ({record.hru_results.filter((h) => h.crop?.active).length})</option>
                      <option value="fallow">En barbecho ({record.hru_results.filter((h) => !h.crop?.active).length})</option>
                    </select>
                  </div>
                </div>

                {/* Tabla/Lista con scroll */}
                <div className="flex-1 overflow-y-auto rounded-xl border border-zinc-800 bg-zinc-900/40 p-1">
                  <div className="divide-y divide-zinc-800/60">
                    {filteredHrus.map((hru) => {
                      const isSelected = selectedHru?.hru_id === hru.hru_id;
                      const isActive = hru.crop?.active === true;
                      const soilWater = hru.variables.soil_water_mm?.value;
                      const rootMoisture = hru.variables.estimated_soil_moisture_vol_percent?.value;

                      return (
                        <div
                          key={hru.hru_id}
                          onClick={() => setSelectedHruId(hru.hru_id)}
                          className={`flex cursor-pointer items-center justify-between p-2.5 text-xs transition rounded-lg ${
                            isSelected
                              ? "bg-cyan-950/60 border border-cyan-500/40 text-cyan-200"
                              : "hover:bg-zinc-800/50 text-zinc-300"
                          }`}
                        >
                          <div className="flex flex-col gap-0.5">
                            <div className="flex items-center gap-2">
                              <span className="font-bold font-mono">HRU #{hru.hru_id}</span>
                              <span
                                className={`rounded px-1.5 py-0.2 text-[9px] font-mono ${
                                  isActive
                                    ? "bg-emerald-500/20 text-emerald-300"
                                    : "bg-zinc-800 text-zinc-400"
                                }`}
                              >
                                {isActive ? "Maíz Activo" : "Barbecho"}
                              </span>
                              {hru.gis_id && (
                                <span className="text-[10px] text-zinc-500">GIS #{hru.gis_id}</span>
                              )}
                            </div>
                            <span className="text-[10px] text-zinc-400 truncate max-w-[220px]">
                              {hru.calendar_id ?? "Sin calendario de cultivo asignado"}
                            </span>
                          </div>

                          <div className="flex flex-col items-end gap-0.5 font-mono text-[11px]">
                            <span className="text-zinc-200">
                              Agua: {soilWater !== null && soilWater !== undefined ? `${Number(soilWater).toFixed(1)} mm` : "N/D"}
                            </span>
                            <span className="text-teal-400 text-[10px]">
                              θ radicular: {rootMoisture !== null && rootMoisture !== undefined ? `${Number(rootMoisture).toFixed(1)}%` : "N/D"}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Inspector Detallado de la HRU seleccionada */}
              <div className="flex flex-col gap-3 rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 lg:col-span-6 overflow-y-auto max-h-[62vh]">
                {selectedHru ? (
                  <>
                    <div className="flex items-start justify-between border-b border-zinc-800 pb-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-base font-bold text-cyan-300">
                            HRU #{selectedHru.hru_id}
                          </h3>
                          <span
                            className={`rounded px-2 py-0.5 text-[10px] font-mono font-bold ${
                              selectedHru.crop?.active
                                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                                : "bg-zinc-800 text-zinc-400 border border-zinc-700"
                            }`}
                          >
                            {selectedHru.crop?.active ? "CULTIVO ACTIVO" : "BARBECHO"}
                          </span>
                        </div>
                        <p className="text-[11px] text-zinc-400 font-mono mt-0.5">
                          Soporte espacial: {selectedHru.spatial_support} · GIS #{selectedHru.gis_id ?? "N/D"}
                        </p>
                      </div>
                      {selectedHru.crop?.active && selectedHru.calendar_id && (
                        <button
                          type="button"
                          onClick={() => {
                            const sample = record.plant_samples.find((s) => s.calendar_id === selectedHru.calendar_id);
                            if (sample && onSelectPlant) {
                              onSelectPlant(sample.plant_id);
                              onNavigateToScale?.("MICRO");
                              onClose();
                            } else {
                              onNavigateToScale?.("MESO");
                              onClose();
                            }
                          }}
                          className="flex items-center gap-1 rounded-lg bg-emerald-600/30 hover:bg-emerald-600/50 border border-emerald-500/40 px-2.5 py-1 text-[11px] font-bold text-emerald-200 transition"
                        >
                          <Sprout className="h-3.5 w-3.5" />
                          Ver en 3D →
                        </button>
                      )}
                    </div>

                    {/* Resumen agronómico y calendario */}
                    <div className="rounded-lg bg-zinc-950/70 p-2.5 text-xs font-mono space-y-1 border border-zinc-800/80">
                      <div className="text-zinc-400">
                        Calendario: <b className="text-zinc-200">{selectedHru.calendar_id ?? "No asignado"}</b>
                      </div>
                      <div className="text-zinc-400">
                        Cultivo: <span className="text-emerald-300 font-bold">{selectedHru.crop?.crop ?? "Sin cultivo activo"}</span>
                        {selectedHru.crop?.phenological_stage && ` (${selectedHru.crop.phenological_stage})`}
                      </div>
                      <div className="text-[10px] text-zinc-400">
                        Origen evento: {selectedHru.crop?.source ?? "SWAT+ mgt_out.txt"}
                      </div>
                    </div>

                    {/* Lista exhaustiva de variables */}
                    <div className="space-y-1">
                      <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider text-[10px]">
                        Variables Hidrológicas y de Suelo (SWAT+)
                      </h4>
                      <VariableRow name="Almacenamiento de agua en suelo" state={selectedHru.variables.soil_water_mm} />
                      <VariableRow name="Agua de suelo media (sw_ave)" state={selectedHru.variables.soil_water_average_mm} />
                      <VariableRow name="Precipitación diaria" state={selectedHru.variables.precipitation_mm} />
                      <VariableRow name="Escorrentía superficial" state={selectedHru.variables.runoff_mm} />
                      <VariableRow name="Evapotranspiración total" state={selectedHru.variables.evapotranspiration_mm} />
                      <VariableRow name="Percolación" state={selectedHru.variables.percolation_mm} />

                      <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider text-[10px] pt-2">
                        Estimaciones Derivadas de Zona Radicular
                      </h4>
                      <VariableRow name="Humedad volumétrica estimada" state={selectedHru.variables.estimated_soil_moisture_vol_percent} />
                      <VariableRow name="Agua en zona radicular estimada" state={selectedHru.variables.estimated_root_zone_water_mm} />
                      <VariableRow name="Profundidad de zona radicular" state={selectedHru.variables.estimated_root_zone_depth_mm} />
                      <VariableRow name="Fracción de agua disponible" state={selectedHru.variables.estimated_plant_available_fraction} />

                      <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider text-[10px] pt-2">
                        Variables Agronómicas SWAT+
                      </h4>
                      <VariableRow name="LAI vegetal SWAT+" state={selectedHru.variables.swat_lai_m2_m2} />
                      <VariableRow name="Biomasa vegetal SWAT+" state={selectedHru.variables.swat_biomass_kg_ha} />
                      <VariableRow name="Factor de estrés hídrico" state={selectedHru.variables.swat_water_stress_factor} />
                      <VariableRow name="Factor de estrés térmico" state={selectedHru.variables.swat_temperature_stress_factor} />
                      <VariableRow name="Factor de estrés de nitrógeno" state={selectedHru.variables.swat_nitrogen_stress_factor} />
                      <VariableRow name="Unidades de calor acumuladas (PHU)" state={selectedHru.variables.swat_plant_heat_unit_fraction} />
                    </div>
                  </>
                ) : (
                  <div className="flex h-full items-center justify-center text-xs text-zinc-500">
                    Selecciona una HRU para ver sus variables detalladas.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: CANALES */}
          {activeTab === "channels" && (
            <div className="grid h-full grid-cols-1 gap-4 lg:grid-cols-12 overflow-hidden">
              {/* Lista y Filtros de Canales */}
              <div className="flex flex-col gap-3 lg:col-span-6 overflow-hidden">
                <div className="relative">
                  <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-zinc-500" />
                  <input
                    type="text"
                    placeholder="Buscar canal por ID o GIS…"
                    value={searchChannel}
                    onChange={(e) => setSearchChannel(e.target.value)}
                    className="w-full rounded-lg border border-zinc-800 bg-zinc-900/90 py-1.5 pl-8 pr-3 text-xs text-zinc-100 placeholder-zinc-500 focus:border-cyan-500 focus:outline-none"
                  />
                </div>

                <div className="flex-1 overflow-y-auto rounded-xl border border-zinc-800 bg-zinc-900/40 p-1">
                  <div className="divide-y divide-zinc-800/60">
                    {filteredChannels.map((ch) => {
                      const isSelected = selectedChannel?.channel_id === ch.channel_id;
                      const isOutlet = ch.gis_id === "153" || ch.channel_id === "25";
                      const qOut = ch.variables.streamflow_m3s?.value;
                      const storage = ch.variables.channel_water_storage_m3?.value;

                      return (
                        <div
                          key={ch.channel_id}
                          onClick={() => setSelectedChannelId(ch.channel_id)}
                          className={`flex cursor-pointer items-center justify-between p-2.5 text-xs transition rounded-lg ${
                            isSelected
                              ? "bg-cyan-950/60 border border-cyan-500/40 text-cyan-200"
                              : "hover:bg-zinc-800/50 text-zinc-300"
                          }`}
                        >
                          <div className="flex flex-col gap-0.5">
                            <div className="flex items-center gap-2">
                              <span className="font-bold font-mono">Canal #{ch.channel_id}</span>
                              <span className="text-[10px] text-zinc-400 font-mono">GIS #{ch.gis_id ?? "N/D"}</span>
                              {isOutlet && (
                                <span className="rounded bg-teal-500/20 px-1.5 py-0.2 text-[9px] font-mono font-bold text-teal-300 border border-teal-500/30">
                                  Outlet USGS
                                </span>
                              )}
                            </div>
                            <span className="text-[10px] text-zinc-500">
                              Almacenamiento: {storage !== null && storage !== undefined ? `${Number(storage).toFixed(1)} m³` : "0 m³"}
                            </span>
                          </div>

                          <div className="flex flex-col items-end gap-0.5 font-mono text-[11px]">
                            <span className="font-bold text-teal-300">
                              Q: {qOut !== null && qOut !== undefined ? `${Number(qOut).toFixed(3)} m³/s` : "N/D"}
                            </span>
                            <span className="text-[10px] text-zinc-400">
                              Entrada: {ch.variables.channel_inflow_m3s?.value !== null && ch.variables.channel_inflow_m3s?.value !== undefined
                                ? `${Number(ch.variables.channel_inflow_m3s.value).toFixed(3)} m³/s`
                                : "N/D"}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Inspector Detallado del Canal seleccionado */}
              <div className="flex flex-col gap-3 rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 lg:col-span-6 overflow-y-auto max-h-[62vh]">
                {selectedChannel ? (
                  <>
                    <div className="flex items-start justify-between border-b border-zinc-800 pb-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-base font-bold text-cyan-300">
                            Canal #{selectedChannel.channel_id}
                          </h3>
                          {selectedChannel.gis_id === "153" && (
                            <span className="rounded bg-teal-500/20 px-2 py-0.5 text-[10px] font-mono font-bold text-teal-300 border border-teal-500/30">
                              OUTLET DE CUENCA
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-zinc-400 font-mono mt-0.5">
                          GIS ID: {selectedChannel.gis_id ?? "N/D"} · Soporte: {selectedChannel.spatial_support}
                        </p>
                      </div>
                    </div>

                    {selectedChannel.gis_id === "153" && (
                      <div className="rounded-lg bg-teal-950/40 p-2.5 text-xs border border-teal-500/30 text-teal-200">
                        <div className="flex items-center gap-1.5 font-bold text-teal-300">
                          <Info className="h-4 w-4" />
                          <span>Punto de Aforo y Descarga Principal USGS #05451210</span>
                        </div>
                        <p className="mt-1 text-[11px] text-zinc-300">
                          Este canal corresponde a la desembocadura de la cuenca South Fork Iowa River en New Providence, IA. Su caudal de salida es el streamflow total publicado a escala Macro.
                        </p>
                      </div>
                    )}

                    {/* Explicación de unidades: m3/s y m3 no son nivel */}
                    <div className="rounded-lg bg-zinc-950/70 p-2.5 text-[11px] text-zinc-400 border border-zinc-800/80">
                      <b>Interpretación hidráulica:</b> El caudal se expresa en <code className="text-teal-300">m³/s</code> y el almacenamiento en <code className="text-teal-300">m³</code>. Ninguna de estas magnitudes equivale directamente a la profundidad o nivel de la lámina de agua.
                    </div>

                    <div className="space-y-1">
                      <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider text-[10px]">
                        Balances de Caudal y Volumen en Canal (SWAT+)
                      </h4>
                      <VariableRow name="Caudal de salida (Streamflow)" state={selectedChannel.variables.streamflow_m3s} />
                      <VariableRow name="Caudal de entrada (Inflow)" state={selectedChannel.variables.channel_inflow_m3s} />
                      <VariableRow name="Almacenamiento de agua en cauce" state={selectedChannel.variables.channel_water_storage_m3} />
                      <VariableRow name="Temperatura del agua en cauce" state={selectedChannel.variables.channel_water_temp_c} />
                      <VariableRow name="Volumen de evaporación del cauce" state={selectedChannel.variables.channel_evap_volume_m3} />
                      <VariableRow name="Volumen de infiltración/pérdida (Seep)" state={selectedChannel.variables.channel_seep_volume_m3} />
                      <VariableRow name="Precipitación directa sobre cauce" state={selectedChannel.variables.channel_precip_volume_m3} />
                      <VariableRow name="Área del cauce" state={selectedChannel.variables.channel_area_ha} />
                    </div>
                  </>
                ) : (
                  <div className="flex h-full items-center justify-center text-xs text-zinc-500">
                    Selecciona un canal para inspeccionar sus variables.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: CALENDARIOS */}
          {activeTab === "calendars" && (
            <div className="flex flex-col gap-4 overflow-y-auto max-h-[64vh]">
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
                <h3 className="text-sm font-bold text-zinc-100">
                  Estructura de Manejo Agrícola · 7 Grupos de Calendario en 32 HRUs de Maíz
                </h3>
                <p className="mt-1 text-xs text-zinc-400">
                  El motor FSPM crece la vegetación de cada grupo de calendario de forma independiente basándose en los eventos ejecutados por SWAT+ (siembra entre 15 y 16 de mayo; cosechas escalonadas entre 27 de agosto y 3 de septiembre). El campo en Meso muestra el promedio ponderado, mientras que las muestras FSPM conservan su calendario específico.
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {calendarGroups.map((group) => {
                  return (
                    <div
                      key={group.calendarId}
                      className="flex flex-col justify-between rounded-xl border border-zinc-800 bg-zinc-900/70 p-3.5 text-xs text-zinc-200"
                    >
                      <div>
                        <div className="flex items-center justify-between border-b border-zinc-800 pb-1.5">
                          <span className="font-mono font-bold text-teal-300 truncate max-w-[200px]" title={group.calendarId}>
                            {group.calendarId}
                          </span>
                          <span
                            className={`rounded px-1.5 py-0.5 text-[9px] font-mono ${
                              group.activeSampleCount > 0
                                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                                : "bg-zinc-800 text-zinc-500"
                            }`}
                          >
                            {group.activeSampleCount > 0 ? "Activo hoy" : "Sin plantas hoy"}
                          </span>
                        </div>

                        <div className="mt-2 space-y-1 font-mono text-[11px] text-zinc-400">
                          <div>
                            HRUs ({group.hruIds.length}):{" "}
                            <span className="text-zinc-200">{group.hruIds.join(", ")}</span>
                          </div>
                          <div>
                            Muestras FSPM activas hoy:{" "}
                            <b className="text-emerald-300">{group.activeSampleCount}</b>
                          </div>
                        </div>
                      </div>

                      {group.samplePlantIds.length > 0 && onSelectPlant && (
                        <div className="mt-3 pt-2 border-t border-zinc-800/80">
                          <button
                            type="button"
                            onClick={() => {
                              onSelectPlant(group.samplePlantIds[0]);
                              onNavigateToScale?.("MICRO");
                              onClose();
                            }}
                            className="w-full rounded-lg bg-emerald-700/40 hover:bg-emerald-700/60 py-1 text-center text-[10px] font-bold text-emerald-200 transition"
                          >
                            Ver muestra {group.samplePlantIds[0].split(":").pop()} (Micro) →
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-zinc-800 bg-zinc-900/60 px-4 py-2.5 sm:px-6 text-xs text-zinc-400">
          <span>{record.hru_results.length} HRUs · {record.channel_results.length} Canales · {record.plant_samples.length} Muestras activas</span>
          <button
            onClick={onClose}
            className="rounded-lg bg-zinc-800 px-3 py-1 text-xs text-zinc-200 hover:bg-zinc-700 transition"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
