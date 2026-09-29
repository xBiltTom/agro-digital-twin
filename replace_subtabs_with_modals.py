import sys

filepath = 'from-plant-to-watershed/frontend/src/app/(dashboard)/simulations/page.tsx'

with open(filepath, 'r') as f:
    content = f.read()

start_marker = """                  {/* Sub-Pestañas de la Consola de Trabajo */}"""
end_marker = """              ) : (
                <div className="p-12 rounded-none border border-dashed border-slate-200 dark:border-slate-800 text-center text-xs text-slate-400">"""

idx_start = content.find(start_marker)
idx_end = content.find(end_marker)

if idx_start == -1 or idx_end == -1:
    print("Markers not found:", idx_start, idx_end)
    sys.exit(1)

new_deck_and_modals = """                  {/* Sub-Pestañas de la Consola de Trabajo (Acceso Directo a Modales) */}
                  <div className="flex items-center gap-1 border-b border-slate-200 dark:border-slate-800 text-xs px-2 bg-slate-50/70 dark:bg-slate-950/40">
                    <button
                      type="button"
                      onClick={() => setActiveModalTab("CHARTS")}
                      className="px-3.5 py-2.5 font-medium border-b-2 border-transparent hover:border-slate-400 dark:hover:border-slate-500 text-slate-700 dark:text-slate-200 transition cursor-pointer flex items-center gap-1.5"
                      title="Abrir modal de series temporales e hidrograma"
                    >
                      <Waves className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                      <span>Series temporales e hidrograma</span>
                      <Maximize2 className="w-3 h-3 text-slate-400 ml-0.5" />
                    </button>

                    <button
                      type="button"
                      onClick={() => setActiveModalTab("AI")}
                      className="px-3.5 py-2.5 font-medium border-b-2 border-transparent hover:border-slate-400 dark:hover:border-slate-500 text-slate-700 dark:text-slate-200 transition cursor-pointer flex items-center gap-1.5"
                      title="Abrir modal de diagnóstico LangChain"
                    >
                      <FileText className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                      <span>Diagnóstico científico y políticas</span>
                      <Maximize2 className="w-3 h-3 text-slate-400 ml-0.5" />
                    </button>

                    <button
                      type="button"
                      onClick={() => setActiveModalTab("SPECIFICATIONS")}
                      className="px-3.5 py-2.5 font-medium border-b-2 border-transparent hover:border-slate-400 dark:hover:border-slate-500 text-slate-700 dark:text-slate-200 transition cursor-pointer flex items-center gap-1.5"
                      title="Abrir modal de acoplamiento y procedencia"
                    >
                      <Layers className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" />
                      <span>Acoplamiento multiescala y procedencia</span>
                      <Maximize2 className="w-3 h-3 text-slate-400 ml-0.5" />
                    </button>
                  </div>

                  {/* Panel Principal Cockpit: 3 Módulos de Comando */}
                  <div className="p-4 sm:p-5 flex flex-col gap-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
                      {/* Tarjeta 1: Series Temporales */}
                      <div className="p-4 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between hover:border-slate-400 dark:hover:border-slate-600 transition">
                        <div>
                          <div className="flex items-center justify-between gap-2 mb-2">
                            <span className="font-mono text-[9px] px-1.5 py-0.5 bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 uppercase font-semibold">
                              Telemetría 4 Escalas
                            </span>
                            <Waves className="w-4 h-4 text-blue-600" />
                          </div>
                          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                            Series temporales e hidrograma
                          </h3>
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 leading-relaxed">
                            Contraste continuo con estación USGS 05451210, hidrograma macro de cuenca, transpiración foliar micro y estrés CWSI edáfico.
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setActiveModalTab("CHARTS")}
                          className="mt-4 w-full py-2 bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:hover:bg-slate-200 text-white dark:text-slate-900 text-xs font-mono font-medium flex items-center justify-center gap-1.5 transition cursor-pointer"
                        >
                          <Maximize2 className="w-3.5 h-3.5" />
                          <span>Abrir series temporales (Modal)</span>
                        </button>
                      </div>

                      {/* Tarjeta 2: Diagnóstico LangChain */}
                      <div className="p-4 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between hover:border-slate-400 dark:hover:border-slate-600 transition">
                        <div>
                          <div className="flex items-center justify-between gap-2 mb-2">
                            <span className="font-mono text-[9px] px-1.5 py-0.5 bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 uppercase font-semibold">
                              LangChain Agent
                            </span>
                            <FileText className="w-4 h-4 text-emerald-600" />
                          </div>
                          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                            Diagnóstico científico y políticas
                          </h3>
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 leading-relaxed">
                            Evaluación biofísica multiescala del balance de masa, métricas de resiliencia climática y recomendaciones agronómicas de manejo.
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setActiveModalTab("AI")}
                          className="mt-4 w-full py-2 bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:hover:bg-slate-200 text-white dark:text-slate-900 text-xs font-mono font-medium flex items-center justify-center gap-1.5 transition cursor-pointer"
                        >
                          <Maximize2 className="w-3.5 h-3.5" />
                          <span>Abrir diagnóstico IA (Modal)</span>
                        </button>
                      </div>

                      {/* Tarjeta 3: Acoplamiento y Procedencia */}
                      <div className="p-4 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between hover:border-slate-400 dark:hover:border-slate-600 transition">
                        <div>
                          <div className="flex items-center justify-between gap-2 mb-2">
                            <span className="font-mono text-[9px] px-1.5 py-0.5 bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 uppercase font-semibold">
                              Procedencia {selectedSim.hydrology_backend}
                            </span>
                            <Layers className="w-4 h-4 text-purple-600" />
                          </div>
                          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                            Acoplamiento multiescala
                          </h3>
                          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 leading-relaxed">
                            Transferencia de tensores FSPM Planta → Parcela → HRU, semillas aleatorias Monte Carlo y auditoría criptográfica JSON.
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => setActiveModalTab("SPECIFICATIONS")}
                          className="mt-4 w-full py-2 bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:hover:bg-slate-200 text-white dark:text-slate-900 text-xs font-mono font-medium flex items-center justify-center gap-1.5 transition cursor-pointer"
                        >
                          <Maximize2 className="w-3.5 h-3.5" />
                          <span>Inspeccionar procedencia (Modal)</span>
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* MODAL 1: SERIES TEMPORALES E HIDROGRAMA */}
                  {activeModalTab === "CHARTS" && (
                    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 overflow-hidden">
                      <div className="w-full max-w-6xl max-h-[92vh] bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 shadow-2xl flex flex-col text-slate-900 dark:text-slate-100 overflow-hidden">
                        {/* Cabecera del Modal de Series Temporales */}
                        <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 shrink-0 flex items-center justify-between bg-slate-50 dark:bg-slate-950/60">
                          <div className="flex items-center gap-2.5">
                            <span className="font-mono text-[10px] px-2 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 font-semibold uppercase">
                              Modal 1
                            </span>
                            <div>
                              <h3 className="font-serif font-semibold text-sm sm:text-base text-slate-900 dark:text-slate-100">
                                Series temporales e hidrograma multiescala
                              </h3>
                              <p className="text-[11px] text-slate-500 font-mono">
                                Experimento: {selectedSim.name} · Periodo: {selectedSim.start_date || "2018-06-01"} a {selectedSim.end_date || "2018-08-31"}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">[Esc para cerrar]</span>
                            <button
                              type="button"
                              onClick={() => setActiveModalTab(null)}
                              className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 transition cursor-pointer"
                              title="Cerrar modal (Esc)"
                            >
                              <X className="w-5 h-5" />
                            </button>
                          </div>
                        </div>

                        {/* Cuerpo del Modal de Series Temporales */}
                        <div className="p-5 flex-1 min-h-0 flex flex-col gap-3 overflow-y-auto">
                          {isSelectedRealSwat && swatResults ? (
                            <SwatRunEvidencePanel simulation={selectedSim} result={swatResults} />
                          ) : (
                            <div className="flex flex-col gap-3">
                              {/* Barra de Control de Disposición */}
                              <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 bg-slate-50/50 dark:bg-slate-950/40 border border-slate-200 dark:border-slate-800 text-xs">
                                <div className="flex items-center gap-1.5">
                                  <span className="text-[11px] font-mono text-slate-500 mr-1">Disposición:</span>
                                  <button
                                    type="button"
                                    onClick={() => setChartLayout("GRID")}
                                    className={`px-2.5 py-1 text-xs font-mono flex items-center gap-1.5 transition cursor-pointer ${
                                      chartLayout === "GRID"
                                        ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 font-semibold"
                                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                                    }`}
                                  >
                                    <LayoutGrid className="w-3.5 h-3.5" />
                                    <span>Cuadrante 2x2</span>
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => setChartLayout("SPOTLIGHT")}
                                    className={`px-2.5 py-1 text-xs font-mono flex items-center gap-1.5 transition cursor-pointer ${
                                      chartLayout === "SPOTLIGHT"
                                        ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 font-semibold"
                                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                                    }`}
                                  >
                                    <Square className="w-3.5 h-3.5" />
                                    <span>Foco único</span>
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => setChartLayout("STACK")}
                                    className={`px-2.5 py-1 text-xs font-mono flex items-center gap-1.5 transition cursor-pointer ${
                                      chartLayout === "STACK"
                                        ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 font-semibold"
                                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700"
                                    }`}
                                  >
                                    <Rows3 className="w-3.5 h-3.5" />
                                    <span>Pila vertical</span>
                                  </button>
                                </div>

                                {chartLayout === "SPOTLIGHT" && (
                                  <div className="flex items-center gap-1 text-xs font-mono">
                                    <span className="text-[11px] text-slate-500 mr-1">Variable activa:</span>
                                    <button
                                      type="button"
                                      onClick={() => setChartViewMode("STREAMFLOW")}
                                      className={`px-2 py-0.5 text-[11px] transition cursor-pointer ${chartViewMode === "STREAMFLOW" ? "bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900 font-semibold" : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-300"}`}
                                    >
                                      Hidrograma
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => setChartViewMode("PLANT")}
                                      className={`px-2 py-0.5 text-[11px] transition cursor-pointer ${chartViewMode === "PLANT" ? "bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900 font-semibold" : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-300"}`}
                                    >
                                      Fisiología
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => setChartViewMode("SOIL")}
                                      className={`px-2 py-0.5 text-[11px] transition cursor-pointer ${chartViewMode === "SOIL" ? "bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900 font-semibold" : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-300"}`}
                                    >
                                      Suelo/Estrés
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => setChartViewMode("MONTHLY")}
                                      className={`px-2 py-0.5 text-[11px] transition cursor-pointer ${chartViewMode === "MONTHLY" ? "bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900 font-semibold" : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-300"}`}
                                    >
                                      Validación USGS
                                    </button>
                                  </div>
                                )}
                              </div>

                              {/* Cuadrante 2x2 */}
                              {chartLayout === "GRID" && (
                                <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                                  {/* 1. Validación USGS */}
                                  <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                                    <div className="p-2.5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2 bg-slate-50/60 dark:bg-slate-950/40">
                                      <div className="min-w-0">
                                        <div className="flex items-center gap-1.5">
                                          <span className="font-mono text-[9px] px-1.5 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold uppercase">USGS</span>
                                          <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">Validación mensual: Aforo vs Gemelo</h3>
                                        </div>
                                        <p className="text-[10px] text-slate-500 truncate mt-0.5">Estación USGS 05451210 South Fork Iowa</p>
                                      </div>
                                      <button
                                        type="button"
                                        onClick={() => setExpandedChartModal("MONTHLY")}
                                        className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition cursor-pointer shrink-0"
                                        title="Inspeccionar en alta resolución"
                                      >
                                        <Maximize2 className="w-3.5 h-3.5" />
                                      </button>
                                    </div>
                                    <div className="h-48 sm:h-52 w-full p-2">
                                      <ResponsiveContainer width="100%" height="100%">
                                        <LineChart data={monthlyComparisonData}>
                                          <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                          <XAxis dataKey="month" stroke="#9ca3af" fontSize={9} tickLine={false} />
                                          <YAxis stroke="#9ca3af" fontSize={9} tickLine={false} />
                                          <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "10px", color: "var(--foreground)" }} />
                                          <Legend wrapperStyle={{ fontSize: "10px" }} />
                                          <Line type="monotone" dataKey="observed_streamflow_m3s" name="USGS Observado" stroke="#09090b" className="dark:stroke-slate-100" strokeWidth={1.8} dot={false} />
                                          <Line type="monotone" dataKey="baseline_streamflow_m3s" name="Línea base" stroke="#ea580c" strokeWidth={1.2} dot={false} />
                                          <Line type="monotone" dataKey="twin_streamflow_m3s" name="Gemelo multiescala" stroke="#059669" strokeWidth={1.8} dot={false} />
                                          <Line type="monotone" dataKey="ml_assisted_streamflow_m3s" name="Híbrido ML" stroke="#7c3aed" strokeWidth={1.2} strokeDasharray="3 3" dot={false} />
                                        </LineChart>
                                      </ResponsiveContainer>
                                    </div>
                                  </div>

                                  {/* 2. Hidrograma de Cuenca */}
                                  <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                                    <div className="p-2.5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2 bg-slate-50/60 dark:bg-slate-950/40">
                                      <div className="min-w-0">
                                        <div className="flex items-center gap-1.5">
                                          <span className="font-mono text-[9px] px-1.5 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold uppercase">Macro</span>
                                          <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">Hidrograma de cuenca: Caudal y lluvia</h3>
                                        </div>
                                        <p className="text-[10px] text-slate-500 truncate mt-0.5">Respuesta de caudal en exutorio y lluvia diaria</p>
                                      </div>
                                      <button
                                        type="button"
                                        onClick={() => setExpandedChartModal("STREAMFLOW")}
                                        className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition cursor-pointer shrink-0"
                                        title="Inspeccionar en alta resolución"
                                      >
                                        <Maximize2 className="w-3.5 h-3.5" />
                                      </button>
                                    </div>
                                    <div className="h-48 sm:h-52 w-full p-2">
                                      {isLoadingResults ? (
                                        <div className="h-full flex items-center justify-center text-slate-400 text-xs font-mono">
                                          <Loader2 className="w-3.5 h-3.5 animate-spin mr-2" /> Cargando hidrograma...
                                        </div>
                                      ) : (
                                        <ResponsiveContainer width="100%" height="100%">
                                          <ComposedChart data={chartData}>
                                            <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                            <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={9} tickLine={false} />
                                            <YAxis yAxisId="left" stroke="#0d9488" fontSize={9} tickLine={false} />
                                            <YAxis yAxisId="right" orientation="right" stroke="#0284c7" fontSize={9} tickLine={false} />
                                            <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "10px", color: "var(--foreground)" }} />
                                            <Legend wrapperStyle={{ fontSize: "10px" }} />
                                            <Bar yAxisId="right" dataKey="precip_mm" name="Lluvia (mm)" fill="#0284c7" opacity={0.6} />
                                            <Area yAxisId="left" type="monotone" dataKey="streamflow_m3s" name="Caudal (m³/s)" stroke="#0d9488" fill="#0d9488" fillOpacity={0.15} strokeWidth={1.5} />
                                          </ComposedChart>
                                        </ResponsiveContainer>
                                      )}
                                    </div>
                                  </div>

                                  {/* 3. Fisiología Vegetal */}
                                  <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                                    <div className="p-2.5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2 bg-slate-50/60 dark:bg-slate-950/40">
                                      <div className="min-w-0">
                                        <div className="flex items-center gap-1.5">
                                          <span className="font-mono text-[9px] px-1.5 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold uppercase">Micro</span>
                                          <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">Fisiología: Transpiración vs ET0</h3>
                                        </div>
                                        <p className="text-[10px] text-slate-500 truncate mt-0.5">Dinámica estomática celular y flujo de savia</p>
                                      </div>
                                      <button
                                        type="button"
                                        onClick={() => setExpandedChartModal("PLANT")}
                                        className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition cursor-pointer shrink-0"
                                        title="Inspeccionar en alta resolución"
                                      >
                                        <Maximize2 className="w-3.5 h-3.5" />
                                      </button>
                                    </div>
                                    <div className="h-48 sm:h-52 w-full p-2">
                                      {isLoadingResults ? (
                                        <div className="h-full flex items-center justify-center text-slate-400 text-xs font-mono">
                                          <Loader2 className="w-3.5 h-3.5 animate-spin mr-2" /> Cargando fisiología...
                                        </div>
                                      ) : (
                                        <ResponsiveContainer width="100%" height="100%">
                                          <ComposedChart data={chartData}>
                                            <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                            <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={9} tickLine={false} />
                                            <YAxis yAxisId="left" stroke="#059669" fontSize={9} tickLine={false} />
                                            <YAxis yAxisId="right" orientation="right" stroke="#0284c7" fontSize={9} tickLine={false} />
                                            <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "10px", color: "var(--foreground)" }} />
                                            <Legend wrapperStyle={{ fontSize: "10px" }} />
                                            <Line yAxisId="left" type="monotone" dataKey="potential_et_mm" name="Demanda ET0" stroke="#ea580c" strokeWidth={1.2} dot={false} strokeDasharray="3 3" />
                                            <Line yAxisId="left" type="monotone" dataKey="plant_transpiration_mm" name="Transpiración" stroke="#059669" strokeWidth={1.8} dot={false} />
                                            <Line yAxisId="right" type="monotone" dataKey="sap_flow_velocity_cmh" name="Savia (cm/h)" stroke="#0284c7" strokeWidth={1.2} dot={false} />
                                          </ComposedChart>
                                        </ResponsiveContainer>
                                      )}
                                    </div>
                                  </div>

                                  {/* 4. Dinámica de Suelo y CWSI */}
                                  <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                                    <div className="p-2.5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2 bg-slate-50/60 dark:bg-slate-950/40">
                                      <div className="min-w-0">
                                        <div className="flex items-center gap-1.5">
                                          <span className="font-mono text-[9px] px-1.5 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold uppercase">Meso</span>
                                          <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">Dinámica de suelo: Humedad θ y CWSI</h3>
                                        </div>
                                        <p className="text-[10px] text-slate-500 truncate mt-0.5">Umbrales de déficit: 0.25 (moderado) y 0.50 (crítico)</p>
                                      </div>
                                      <button
                                        type="button"
                                        onClick={() => setExpandedChartModal("SOIL")}
                                        className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition cursor-pointer shrink-0"
                                        title="Inspeccionar en alta resolución"
                                      >
                                        <Maximize2 className="w-3.5 h-3.5" />
                                      </button>
                                    </div>
                                    <div className="h-48 sm:h-52 w-full p-2">
                                      {isLoadingResults ? (
                                        <div className="h-full flex items-center justify-center text-slate-400 text-xs font-mono">
                                          <Loader2 className="w-3.5 h-3.5 animate-spin mr-2" /> Cargando suelo...
                                        </div>
                                      ) : (
                                        <ResponsiveContainer width="100%" height="100%">
                                          <ComposedChart data={chartData}>
                                            <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                            <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={9} tickLine={false} />
                                            <YAxis yAxisId="left" stroke="#0284c7" fontSize={9} tickLine={false} domain={[0, 45]} />
                                            <YAxis yAxisId="right" orientation="right" stroke="#e11d48" fontSize={9} tickLine={false} domain={[0, 1]} />
                                            <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "10px", color: "var(--foreground)" }} />
                                            <Legend wrapperStyle={{ fontSize: "10px" }} />
                                            <Area yAxisId="left" type="monotone" dataKey="soil_moisture_vol" name="Humedad θ (%)" stroke="#0284c7" fill="#0284c7" fillOpacity={0.15} strokeWidth={1.5} />
                                            <Line yAxisId="right" type="monotone" dataKey="cwsi_stress_index" name="Estrés CWSI" stroke="#e11d48" strokeWidth={1.5} dot={false} />
                                            <ReferenceLine yAxisId="right" y={0.25} stroke="#f59e0b" strokeDasharray="3 3" />
                                            <ReferenceLine yAxisId="right" y={0.50} stroke="#ef4444" strokeDasharray="3 3" />
                                          </ComposedChart>
                                        </ResponsiveContainer>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              )}

                              {/* Modo SPOTLIGHT */}
                              {chartLayout === "SPOTLIGHT" && (
                                <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                                  <div className="p-3 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2 bg-slate-50/60 dark:bg-slate-950/40">
                                    <div className="flex items-center gap-2">
                                      <span className="font-mono text-[10px] px-2 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold uppercase">
                                        {chartViewMode === "STREAMFLOW" ? "Escala Macro" : chartViewMode === "PLANT" ? "Escala Micro" : chartViewMode === "SOIL" ? "Escala Meso" : "Validación USGS"}
                                      </span>
                                      <h3 className="text-xs sm:text-sm font-semibold text-slate-900 dark:text-slate-100">
                                        {chartViewMode === "STREAMFLOW" && "Hidrograma de cuenca: Caudal en exutorio y precipitación diaria"}
                                        {chartViewMode === "PLANT" && "Fisiología vegetal: Transpiración foliar real vs demanda evaporativa (ET0)"}
                                        {chartViewMode === "SOIL" && "Dinámica de suelo: Humedad volumétrica θ (%) e índice de estrés CWSI"}
                                        {chartViewMode === "MONTHLY" && "Validación mensual: Aforo observado USGS vs Gemelo digital"}
                                      </h3>
                                    </div>
                                    <button
                                      type="button"
                                      onClick={() => setExpandedChartModal(chartViewMode as any)}
                                      className="p-1.5 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 transition cursor-pointer flex items-center gap-1 text-xs font-mono"
                                    >
                                      <Maximize2 className="w-3.5 h-3.5" />
                                      <span>Inspeccionar</span>
                                    </button>
                                  </div>

                                  <div className="h-72 sm:h-80 w-full p-3">
                                    {isLoadingResults && chartViewMode !== "MONTHLY" ? (
                                      <div className="h-full flex items-center justify-center text-slate-400 text-xs font-mono">
                                        <Loader2 className="w-4 h-4 animate-spin mr-2" /> Cargando serie temporal...
                                      </div>
                                    ) : (
                                      <ResponsiveContainer width="100%" height="100%">
                                        {chartViewMode === "MONTHLY" ? (
                                          <LineChart data={monthlyComparisonData}>
                                            <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                            <XAxis dataKey="month" stroke="#9ca3af" fontSize={10} tickLine={false} />
                                            <YAxis stroke="#9ca3af" fontSize={10} tickLine={false} />
                                            <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "11px", color: "var(--foreground)" }} />
                                            <Legend wrapperStyle={{ fontSize: "11px" }} />
                                            <Line type="monotone" dataKey="observed_streamflow_m3s" name="Observado real (USGS)" stroke="#09090b" className="dark:stroke-slate-100" strokeWidth={2} dot={false} />
                                            <Line type="monotone" dataKey="baseline_streamflow_m3s" name="Línea base sin acoplar" stroke="#ea580c" strokeWidth={1.5} dot={false} />
                                            <Line type="monotone" dataKey="twin_streamflow_m3s" name="Gemelo multiescala" stroke="#059669" strokeWidth={2} dot={false} />
                                            <Line type="monotone" dataKey="ml_assisted_streamflow_m3s" name="Predicción híbrida ML" stroke="#7c3aed" strokeWidth={1.5} strokeDasharray="3 3" dot={false} />
                                          </LineChart>
                                        ) : chartViewMode === "STREAMFLOW" ? (
                                          <ComposedChart data={chartData}>
                                            <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                            <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={10} tickLine={false} />
                                            <YAxis yAxisId="left" stroke="#0d9488" fontSize={10} tickLine={false} label={{ value: "Caudal (m³/s)", angle: -90, position: "insideLeft", fill: "#0d9488", fontSize: 10 }} />
                                            <YAxis yAxisId="right" orientation="right" stroke="#0284c7" fontSize={10} tickLine={false} label={{ value: "Lluvia (mm)", angle: 90, position: "insideRight", fill: "#0284c7", fontSize: 10 }} />
                                            <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "11px", color: "var(--foreground)" }} />
                                            <Legend wrapperStyle={{ fontSize: "11px" }} />
                                            <Bar yAxisId="right" dataKey="precip_mm" name="Precipitación diaria (mm)" fill="#0284c7" opacity={0.6} />
                                            <Area yAxisId="left" type="monotone" dataKey="streamflow_m3s" name="Caudal simulado (m³/s)" stroke="#0d9488" fill="#0d9488" fillOpacity={0.15} strokeWidth={1.8} />
                                          </ComposedChart>
                                        ) : chartViewMode === "PLANT" ? (
                                          <ComposedChart data={chartData}>
                                            <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                            <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={10} tickLine={false} />
                                            <YAxis yAxisId="left" stroke="#059669" fontSize={10} tickLine={false} label={{ value: "Agua (mm/d)", angle: -90, position: "insideLeft", fill: "#059669", fontSize: 10 }} />
                                            <YAxis yAxisId="right" orientation="right" stroke="#0284c7" fontSize={10} tickLine={false} label={{ value: "Savia (cm/h)", angle: 90, position: "insideRight", fill: "#0284c7", fontSize: 10 }} />
                                            <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "11px", color: "var(--foreground)" }} />
                                            <Legend wrapperStyle={{ fontSize: "11px" }} />
                                            <Line yAxisId="left" type="monotone" dataKey="potential_et_mm" name="Demanda atmosférica ET0 (mm/d)" stroke="#ea580c" strokeWidth={1.5} dot={false} strokeDasharray="3 3" />
                                            <Line yAxisId="left" type="monotone" dataKey="plant_transpiration_mm" name="Transpiración real (mm/d)" stroke="#059669" strokeWidth={2} dot={false} />
                                            <Line yAxisId="right" type="monotone" dataKey="sap_flow_velocity_cmh" name="Velocidad savia (cm/h)" stroke="#0284c7" strokeWidth={1.5} dot={false} />
                                          </ComposedChart>
                                        ) : (
                                          <ComposedChart data={chartData}>
                                            <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                            <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={10} tickLine={false} />
                                            <YAxis yAxisId="left" stroke="#0284c7" fontSize={10} tickLine={false} domain={[0, 45]} label={{ value: "Humedad θ (%)", angle: -90, position: "insideLeft", fill: "#0284c7", fontSize: 10 }} />
                                            <YAxis yAxisId="right" orientation="right" stroke="#e11d48" fontSize={10} tickLine={false} domain={[0, 1]} label={{ value: "Estrés CWSI (0-1)", angle: 90, position: "insideRight", fill: "#e11d48", fontSize: 10 }} />
                                            <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "11px", color: "var(--foreground)" }} />
                                            <Legend wrapperStyle={{ fontSize: "11px" }} />
                                            <Area yAxisId="left" type="monotone" dataKey="soil_moisture_vol" name="Humedad volumétrica θ (%)" stroke="#0284c7" fill="#0284c7" fillOpacity={0.15} strokeWidth={1.8} />
                                            <Line yAxisId="right" type="monotone" dataKey="cwsi_stress_index" name="Estrés CWSI" stroke="#e11d48" strokeWidth={1.8} dot={false} />
                                            <ReferenceLine yAxisId="right" y={0.25} stroke="#f59e0b" strokeDasharray="3 3" />
                                            <ReferenceLine yAxisId="right" y={0.50} stroke="#ef4444" strokeDasharray="3 3" />
                                          </ComposedChart>
                                        )}
                                      </ResponsiveContainer>
                                    )}
                                  </div>
                                </div>
                              )}

                              {/* Modo STACK */}
                              {chartLayout === "STACK" && (
                                <div className="flex flex-col gap-4">
                                  <div className="p-4 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col gap-2">
                                    <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                                      <div>
                                        <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                                          Validación mensual: Aforo observado USGS vs Gemelo digital multiescala
                                        </h3>
                                        <p className="text-[11px] text-slate-500 mt-0.5">
                                          Contraste directo contra la estación USGS 05451210 en el exutorio del río South Fork Iowa.
                                        </p>
                                      </div>
                                      <button
                                        type="button"
                                        onClick={() => setExpandedChartModal("MONTHLY")}
                                        className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition cursor-pointer"
                                      >
                                        <Maximize2 className="w-3.5 h-3.5" />
                                      </button>
                                    </div>
                                    <div className="h-60 w-full">
                                      <ResponsiveContainer width="100%" height="100%">
                                        <LineChart data={monthlyComparisonData}>
                                          <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                          <XAxis dataKey="month" stroke="#9ca3af" fontSize={10} tickLine={false} />
                                          <YAxis stroke="#9ca3af" fontSize={10} tickLine={false} label={{ value: "Caudal (m³/s)", angle: -90, position: "insideLeft", fill: "#6b7280", fontSize: 10 }} />
                                          <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "11px", color: "var(--foreground)" }} />
                                          <Legend wrapperStyle={{ fontSize: "11px" }} />
                                          <Line type="monotone" dataKey="observed_streamflow_m3s" name="Observado real (USGS)" stroke="#09090b" className="dark:stroke-slate-100" strokeWidth={2} dot={false} />
                                          <Line type="monotone" dataKey="baseline_streamflow_m3s" name="Línea base sin acoplar" stroke="#ea580c" strokeWidth={1.5} dot={false} />
                                          <Line type="monotone" dataKey="twin_streamflow_m3s" name="Gemelo multiescala" stroke="#059669" strokeWidth={2} dot={false} />
                                          <Line type="monotone" dataKey="ml_assisted_streamflow_m3s" name="Predicción híbrida ML" stroke="#7c3aed" strokeWidth={1.5} strokeDasharray="3 3" dot={false} />
                                        </LineChart>
                                      </ResponsiveContainer>
                                    </div>
                                  </div>

                                  <div className="p-4 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col gap-2">
                                    <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                                      <div>
                                        <h3 className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                                          Hidrograma de cuenca: Caudal en exutorio y precipitación diaria
                                        </h3>
                                        <p className="text-[11px] text-slate-500 mt-0.5">
                                          Respuesta hidrológica superficial y recesión del caudal base ante eventos de lluvia.
                                        </p>
                                      </div>
                                      <button
                                        type="button"
                                        onClick={() => setExpandedChartModal("STREAMFLOW")}
                                        className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition cursor-pointer"
                                      >
                                        <Maximize2 className="w-3.5 h-3.5" />
                                      </button>
                                    </div>
                                    <div className="h-60 w-full">
                                      {isLoadingResults ? (
                                        <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                                          <Loader2 className="w-4 h-4 animate-spin mr-2" /> Cargando hidrograma...
                                        </div>
                                      ) : (
                                        <ResponsiveContainer width="100%" height="100%">
                                          <ComposedChart data={chartData}>
                                            <CartesianGrid strokeDasharray="2 2" stroke="#e5e7eb" className="dark:stroke-slate-800" vertical={false} />
                                            <XAxis dataKey="date_str" stroke="#9ca3af" fontSize={10} tickLine={false} />
                                            <YAxis yAxisId="left" stroke="#0d9488" fontSize={10} tickLine={false} label={{ value: "Caudal (m³/s)", angle: -90, position: "insideLeft", fill: "#0d9488", fontSize: 10 }} />
                                            <YAxis yAxisId="right" orientation="right" stroke="#0284c7" fontSize={10} tickLine={false} label={{ value: "Lluvia (mm)", angle: 90, position: "insideRight", fill: "#0284c7", fontSize: 10 }} />
                                            <Tooltip contentStyle={{ backgroundColor: "var(--background)", borderColor: "#e5e7eb", borderRadius: "0px", fontSize: "11px", color: "var(--foreground)" }} />
                                            <Legend wrapperStyle={{ fontSize: "11px" }} />
                                            <Bar yAxisId="right" dataKey="precip_mm" name="Precipitación diaria (mm)" fill="#0284c7" opacity={0.6} />
                                            <Area yAxisId="left" type="monotone" dataKey="streamflow_m3s" name="Caudal simulado (m³/s)" stroke="#0d9488" fill="#0d9488" fillOpacity={0.15} strokeWidth={1.8} />
                                          </ComposedChart>
                                        </ResponsiveContainer>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* MODAL 2: DIAGNÓSTICO CIENTÍFICO (LANGCHAIN) */}
                  {activeModalTab === "AI" && (
                    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 overflow-hidden">
                      <div className="w-full max-w-5xl max-h-[92vh] bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 shadow-2xl flex flex-col text-slate-900 dark:text-slate-100 overflow-hidden">
                        {/* Cabecera del Modal de IA */}
                        <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 shrink-0 flex items-center justify-between bg-slate-50 dark:bg-slate-950/60">
                          <div className="flex items-center gap-2.5">
                            <span className="font-mono text-[10px] px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900 text-emerald-800 dark:text-emerald-200 font-semibold uppercase">
                              Modal 2 · IA
                            </span>
                            <div>
                              <h3 className="font-serif font-semibold text-sm sm:text-base text-slate-900 dark:text-slate-100">
                                Diagnóstico biofísico y recomendaciones de manejo
                              </h3>
                              <p className="text-[11px] text-slate-500 font-mono">
                                Experimento: {selectedSim.name} · Protocolo Ficha Técnica
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">[Esc para cerrar]</span>
                            <button
                              type="button"
                              onClick={() => setActiveModalTab(null)}
                              className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 transition cursor-pointer"
                              title="Cerrar modal"
                            >
                              <X className="w-5 h-5" />
                            </button>
                          </div>
                        </div>

                        {/* Contenido del Diagnóstico */}
                        <div className="p-5 flex-1 min-h-0 overflow-y-auto">
                          <AIInsightsCard
                            key={selectedSim.id}
                            simulationId={selectedSim.id}
                            initialInsights={(selectedSim.provenance as Record<string, any>)?.ai_insights}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* MODAL 3: ACOPLAMIENTO MULTIESCALA & PROCEDENCIA */}
                  {activeModalTab === "SPECIFICATIONS" && (
                    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6 overflow-hidden">
                      <div className="w-full max-w-5xl max-h-[92vh] bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 shadow-2xl flex flex-col text-slate-900 dark:text-slate-100 overflow-hidden">
                        {/* Cabecera del Modal de Procedencia */}
                        <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 shrink-0 flex items-center justify-between bg-slate-50 dark:bg-slate-950/60">
                          <div className="flex items-center gap-2.5">
                            <span className="font-mono text-[10px] px-2 py-0.5 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 font-semibold uppercase">
                              Modal 3 · Procedencia
                            </span>
                            <div>
                              <h3 className="font-serif font-semibold text-sm sm:text-base text-slate-900 dark:text-slate-100">
                                Acoplamiento multiescala y trazabilidad de procedencia
                              </h3>
                              <p className="text-[11px] text-slate-500 font-mono">
                                Identificador: {selectedSim.id} · Motor: {selectedSim.hydrology_backend}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">[Esc para cerrar]</span>
                            <button
                              type="button"
                              onClick={() => setActiveModalTab(null)}
                              className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 transition cursor-pointer"
                              title="Cerrar modal"
                            >
                              <X className="w-5 h-5" />
                            </button>
                          </div>
                        </div>

                        {/* Contenido de Procedencia */}
                        <div className="p-5 flex-1 min-h-0 flex flex-col gap-4 overflow-y-auto">
                          {/* Tarjetas de Transferencia de Escala */}
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                            <div className="p-3.5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                              <span className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 pb-2 border-b border-slate-100 dark:border-slate-800">
                                <Sprout className="w-3.5 h-3.5 text-emerald-600" />
                                Micro a meso: Planta a parcela
                              </span>
                              <div className="mt-2 space-y-1 text-slate-600 dark:text-slate-400">
                                <div>Población: <strong className="text-slate-800 dark:text-slate-200">{selectedSim.plant_count?.toLocaleString()} plantas FSPM</strong></div>
                                <div>Índice foliar: <strong className="text-slate-800 dark:text-slate-200">{Number(selectedSim.field_aggregates?.mean_lai ?? 0).toFixed(3)} m²/m²</strong></div>
                                <div>Profundidad raíz: <strong className="text-slate-800 dark:text-slate-200">{Number(selectedSim.field_aggregates?.mean_root_depth_cm ?? 0).toFixed(1)} cm</strong></div>
                              </div>
                            </div>

                            <div className="p-3.5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                              <span className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 pb-2 border-b border-slate-100 dark:border-slate-800">
                                <Droplets className="w-3.5 h-3.5 text-blue-600" />
                                Meso a macro: Parcela a HRU
                              </span>
                              <div className="mt-2 space-y-1 text-slate-600 dark:text-slate-400">
                                <div>Unidades HRU: <strong className="text-slate-800 dark:text-slate-200">{selectedSim.hru_aggregates?.count ?? 0} HRUs</strong></div>
                                <div>Fracción área: <strong className="text-slate-800 dark:text-slate-200">{Number(selectedSim.hru_aggregates?.area_fraction_sum ?? 0).toFixed(2)}</strong></div>
                                <div>Curva SCS: <strong className="text-slate-800 dark:text-slate-200">CN = {(selectedSim as any).parameters?.curve_number ?? 74}</strong></div>
                              </div>
                            </div>

                            <div className="p-3.5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between">
                              <span className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 pb-2 border-b border-slate-100 dark:border-slate-800">
                                <Waves className="w-3.5 h-3.5 text-teal-600" />
                                Macro a aforo: Contraste USGS
                              </span>
                              <div className="mt-2 space-y-1 text-slate-600 dark:text-slate-400">
                                <div>Estación: <strong className="text-slate-800 dark:text-slate-200">USGS {selectedSim.station_id || "05451210"}</strong></div>
                                <div>Meses aforo: <strong className="text-slate-800 dark:text-slate-200">{selectedSim.validation?.aligned_months ?? 0} meses</strong></div>
                                <div>Reducción RMSE: <strong className="text-emerald-700 dark:text-emerald-400">{selectedSim.validation?.improvement_percent?.value?.toFixed?.(2) ?? "0.00"}%</strong></div>
                              </div>
                            </div>
                          </div>

                          {/* Parámetros Criptográficos y Datos de Entrada */}
                          <div className="p-4 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col gap-3 text-xs">
                            <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                              <span className="font-semibold text-slate-900 dark:text-slate-100">
                                Auditoría de parámetros y semillas
                              </span>
                              <span className="font-mono text-[10px] text-slate-400">
                                Semilla estocástica: {selectedSim.seed}
                              </span>
                            </div>

                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                              <div>
                                <span className="text-slate-400 block text-[10px]">Semilla</span>
                                <span className="font-semibold text-slate-800 dark:text-slate-200">seed = {selectedSim.seed}</span>
                              </div>
                              <div>
                                <span className="text-slate-400 block text-[10px]">Motor físico</span>
                                <span className="font-semibold text-slate-800 dark:text-slate-200">{selectedSim.hydrology_backend}</span>
                              </div>
                              <div>
                                <span className="text-slate-400 block text-[10px]">Fuente climática</span>
                                <span className="font-semibold text-slate-800 dark:text-slate-200">{selectedSim.climate_source || "SINTÉTICO"}</span>
                              </div>
                              <div>
                                <span className="text-slate-400 block text-[10px]">Duración</span>
                                <span className="font-semibold text-slate-800 dark:text-slate-200">{selectedSim.duration_days} días</span>
                              </div>
                            </div>

                            {/* Detalle JSON de Procedencia */}
                            <details className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-slate-500" open>
                              <summary className="cursor-pointer font-medium hover:text-slate-800 dark:hover:text-slate-300">
                                Registro completo de procedencia criptográfica (JSON)
                              </summary>
                              <pre className="mt-2 p-3 bg-slate-950 text-slate-300 font-mono text-[11px] overflow-x-auto max-h-64">
                                {JSON.stringify(selectedSim.provenance, null, 2)}
                              </pre>
                            </details>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}"""

content = content[:idx_start] + new_deck_and_modals + "\n" + content[idx_end:]

with open(filepath, 'w') as f:
    f.write(content)

print("Subtabs converted to Modals successfully!")
