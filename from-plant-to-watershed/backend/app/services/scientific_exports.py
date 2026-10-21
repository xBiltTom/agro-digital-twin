"""Read-only, reference-styled exports of the frozen South Fork experiment.

No simulation, fitting, evaluation or paper-packaging code is invoked here.
The historical paper assets and their manifests are never rewritten.
"""
from __future__ import annotations

import csv
from datetime import date
import hashlib
import io
import json
import math
from pathlib import Path
import textwrap
from threading import Lock


DOMAIN = Path(__file__).resolve().parents[3] / "research_domain"
ARMS = ("A", "B", "C", "D")
CONTRASTS = (
    ("B_vs_A", "B−A", "Aporte vegetal"),
    ("C_vs_A", "C−A", "Aporte ML"),
    ("D_vs_B", "D−B", "ML con vegetal"),
    ("D_vs_C", "D−C", "Vegetal con ML"),
    ("D_vs_A", "D−A", "Sistema completo / H₁"),
)
EXPORTS = (
    ("monthly-hydrograph", "Figura 5 · Hidrograma mensual TEST", "results", False),
    ("performance", "Tabla 5 · Desempeño A/B/C/D", "results", True),
    ("contrasts-plot", "Figura 6 · Contrastes de RMSE", "results", False),
    ("contrasts", "Tabla 6 · Contrastes e intervalos", "results", True),
    ("temporal-partition", "Figura 4 · Partición temporal", "partitions", False),
    ("partitions", "Tabla 4 · Particiones temporales", "partitions", True),
    ("plant-mapping", "Tabla 2 · Transformación vegetal", "configuration", True),
    ("experimental-design", "Tabla 3 · Diseño A/B/C/D", "configuration", True),
)
PARTITIONS = {
    "WARMUP": ("Warm-up", "Estabilización de estados", "Evaluación final"),
    "CALIBRATION": ("CALIBRATION", "Ajuste físico previo al desarrollo ML", "Ajuste usando TEST"),
    "TRAIN": ("TRAIN", "Ajuste de modelos y preprocesadores ML", "Selección usando TEST"),
    "VALIDATION": ("VALIDATION", "Selección de algoritmo e hiperparámetros", "Modificar tras observar TEST"),
    "TEST": ("TEST", "Evaluación final", "Selección o ajuste retrospectivo"),
}
_RENDER_LOCK = Lock()  # Matplotlib's font manager and rcParams are process-global.


def _checked(path: Path, expected: str) -> bytes:
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected:
        raise ValueError("Cambió la integridad de la evidencia científica")
    return content


def _number(value, digits=2):
    if not isinstance(value, (float, int)) or not math.isfinite(value):
        return "No disponible"
    return f"{value:.{digits}f}"


class ScientificExport:
    def __init__(self, domain: Path = DOMAIN, variant: str = "PRIMARY"):
        if variant not in {"PRIMARY", "EXCLUDE_ESTIMATED"}:
            raise ValueError("Variante no soportada")
        self.domain = domain
        self.variant = variant
        manifest = json.loads((domain / "test_v1/artifact-manifest.json").read_bytes())
        self.report = json.loads(_checked(
            domain / "south_fork_test_delivery_4_v1.json", manifest["report_sha256"]))
        self.protocol = json.loads(_checked(
            domain / "south_fork_multiyear_protocol_v1.json", self.report["parent_protocol_sha256"]))
        self.evaluation = self.report["primary" if variant == "PRIMARY" else "exclude_estimated_sensitivity"]
        self.manifest = manifest

    def catalog(self):
        return {
            "experiment_id": self.report["experiment_id"],
            "test_interval": self.report["test_interval"],
            "entries": [{"id": key, "title": title, "group": group,
                         "formats": ["png", "svg", "pdf"] + (["csv"] if table else []),
                         "supports_sensitivity": group == "results"}
                        for key, title, group, table in EXPORTS],
        }

    def _predictions(self):
        raw = _checked(self.domain / "test_v1/monthly-predictions.csv",
                       self.manifest["sha256"]["monthly-predictions.csv"])
        rows = csv.DictReader(io.StringIO(raw.decode("utf-8")))
        return [row for row in rows if row["variant"] == self.variant and row["series"] in ARMS]

    def _plant_contract(self):
        # The embedded contract is byte-for-byte reconstructable from delivery 2.
        # Verify against TEST's frozen hash; this also works without a SWAT runtime.
        delivery = json.loads((self.domain / "south_fork_multiyear_delivery_2_v1.json").read_bytes())
        contract = delivery["frozen_plant_contract"]
        raw = (json.dumps(contract, indent=2) + "\n").encode()
        if hashlib.sha256(raw).hexdigest() != self.report["plant_contract_sha256"]:
            raise ValueError("Cambió el contrato vegetal congelado")
        return contract

    def partition_rows(self):
        rows = []
        for key, (label, allowed, forbidden) in PARTITIONS.items():
            start, end = map(date.fromisoformat, self.protocol["partitions"][key])
            months = (end.year - start.year) * 12 + end.month - start.month + 1
            rows.append([label, f"{start.year}–{end.year} / {months}", allowed, forbidden])
        return rows

    def table(self, key):
        if key == "performance":
            rows = [[label, *[_number(self.evaluation["metrics"][arm][metric]["value"])
                             for arm in ARMS]] for metric, label in (
                                 ("rmse", "RMSE (m³/s)"), ("mae", "MAE (m³/s)"),
                                 ("nse", "NSE"), ("kge", "KGE"), ("pbias", "PBIAS (%)"))]
            return ["Métrica", *ARMS], rows, [0.28, 0.18, 0.18, 0.18, 0.18]
        if key == "contrasts":
            rows = []
            for name, label, meaning in CONTRASTS:
                item = self.evaluation["contrasts"][name]
                low, high = item["ci95_reduction_m3s"]
                conclusion = "No disponible" if low is None or high is None else (
                    "Incluye 0" if low <= 0 <= high else "Excluye 0")
                rows.append([label, meaning, _number(item["rmse_reduction_m3s"]),
                             _number(item["rmse_reduction_percent"], 1),
                             f"[{_number(low)}; {_number(high)}]", conclusion])
            return ["Contraste", "Interpretación", "ΔRMSE\n(m³/s)", "Mejora (%)", "IC 95 %\n(m³/s)", "Conclusión"], rows, [0.12, 0.24, 0.13, 0.13, 0.21, 0.17]
        if key == "partitions":
            return ["Partición", "Años / meses", "Uso permitido", "Uso no permitido"], self.partition_rows(), [0.17, 0.20, 0.33, 0.30]
        if key == "experimental-design":
            # A/B/C/D definitions are fixed by the frozen protocol; verify all exist.
            if not set(ARMS).issubset(self.evaluation["metrics"]):
                raise ValueError("Faltan brazos del experimento")
            return ["Brazo", "SWAT+", "Parametrización vegetal", "ML residual", "Función"], [
                ["A", "Sí", "No", "No", "Referencia física"],
                ["B", "Sí", "Sí", "No", "Aporte de la información vegetal"],
                ["C", "Sí", "No", "Sí", "Aporte del ML sobre SWAT+"],
                ["D", "Sí", "Sí", "Sí", "Sistema completo"],
            ], [0.09, 0.11, 0.28, 0.16, 0.36]
        if key == "plant-mapping":
            contract = self._plant_contract()
            summary = contract["summary"]
            lai = summary["swat_lai_contract"]
            definitions = [
                ("LAI máximo estacional", "lai_pot", "LAI potencial máximo", lai["lai_pot"], "Derivado del resumen vegetal"),
                ("Fracción térmica, primer punto", "frac_hu1", "Primer punto de la curva LAI–HU", lai["frac_hu1"], "Acotado al dominio válido"),
                ("LAI relativo, primer punto", "lai_max1", "LAI relativo en frac_hu1", lai["lai_max1"], "Derivado de trayectoria"),
                ("Fracción térmica, segundo punto", "frac_hu2", "Segundo punto de la curva LAI–HU", lai["frac_hu2"], "Posterior a frac_hu1"),
                ("LAI relativo, segundo punto", "lai_max2", "LAI relativo en frac_hu2", lai["lai_max2"], "Derivado de trayectoria"),
                ("Inicio de declinación", "hu_lai_decl", "Fracción térmica de senescencia del LAI", lai["hu_lai_decl"], "Post-pico"),
                ("Altura máxima", "can_ht_max", "Altura máxima del dosel (m)", summary["plant_height_mean_m"], "Derivada de población"),
                ("Profundidad radicular máxima", "rt_dp_max", "Profundidad máxima de raíces (m)", summary["root_depth_mean_m"], "Sujeta al límite del suelo"),
                ("Coeficiente de extinción", "ext_co", "Extinción de radiación", summary["canopy_extinction_coefficient"], "Supuesto paramétrico sin calibrar"),
                ("Eficiencia de uso de radiación", "bm_e", "Eficiencia biomasa–radiación", summary["biomass_energy_ratio_kg_ha_per_mj_m2"], "Parámetro base del modelo sin calibrar"),
            ]
            rows = [[state, parameter, interpretation, f"{_number(value, 4)} · {note}"]
                    for state, parameter, interpretation, value, note in definitions]
            return ["Estado/resumen vegetal", "Parámetro\nSWAT+", "Interpretación", "Valor / observación"], rows, [0.26, 0.16, 0.26, 0.32]
        raise ValueError("La figura no tiene formato de tabla")

    def render(self, key: str, fmt: str) -> bytes:
        entry = next((item for item in self.catalog()["entries"] if item["id"] == key), None)
        if entry is None or fmt not in entry["formats"]:
            raise ValueError("Exportación o formato no soportado")
        if fmt == "csv":
            headers, rows, _ = self.table(key)
            output = io.StringIO(newline="")
            writer = csv.writer(output)
            writer.writerow([h.replace("\n", " ") for h in headers])
            writer.writerows(rows)
            return output.getvalue().encode("utf-8-sig")

        # Lazy import keeps startup independent of font initialization. Figure
        # objects avoid pyplot's shared figure registry; lock covers rc/font state.
        from matplotlib import rc_context
        from matplotlib.figure import Figure
        with _RENDER_LOCK, rc_context({
            "font.family": "DejaVu Sans", "font.size": 11,
            "figure.facecolor": "white", "axes.facecolor": "white",
            "text.color": "black", "axes.labelcolor": "black",
            "svg.fonttype": "none", "svg.hashsalt": "south-fork-scientific-exports-v1",
        }):
            figure = Figure(figsize=(13, 6), layout="constrained")
            if key == "monthly-hydrograph":
                self._hydrograph(figure)
            elif key == "contrasts-plot":
                self._contrasts(figure)
            elif key == "temporal-partition":
                self._partition(figure)
            else:
                self._table_figure(figure, key)
            description = (f"Experimento {self.report['experiment_id']}; variante {self.variant}; "
                           f"TEST {self.report['test_interval']}; ΔRMSE = RMSE(referencia) − RMSE(candidato). "
                           f"KGE modificado; PBIAS simulado − observado. "
                           f"Reporte SHA-256 {self.manifest['report_sha256']}; "
                           "contrastes secundarios descriptivos sin ajuste por multiplicidad.")
            metadata = ({"Subject": description, "CreationDate": None, "ModDate": None} if fmt == "pdf"
                        else {"Description": description, **({"Date": None} if fmt == "svg" else {})})
            output = io.BytesIO()
            figure.savefig(output, format=fmt, dpi=300, facecolor="white", metadata=metadata)
            figure.clear()
            return output.getvalue()

    def _suffix(self):
        return " · sin observaciones estimadas" if self.variant == "EXCLUDE_ESTIMATED" else ""

    def _hydrograph(self, figure):
        from matplotlib.dates import DateFormatter, YearLocator
        rows = self._predictions()
        indexed = {(row["month"], row["series"]): row for row in rows}
        months = sorted({row["month"] for row in rows})
        dates = [date.fromisoformat(month + "-01") for month in months]

        def value(month, arm, field):
            row = indexed[month, arm]
            return float(row[field]) if row["eligible"] == "True" and row[field] else math.nan

        ax = figure.subplots()
        ax.plot(dates, [value(m, "A", "observed_streamflow_m3s") for m in months],
                color="black", lw=2, label="USGS")
        for arm, color in zip(ARMS, ("gray", "#1f77b4", "#ff7f0e", "#2ca02c")):
            ax.plot(dates, [value(m, arm, "predicted_streamflow_m3s") for m in months],
                    color=color, lw=1.3, label=arm)
        start, end = self.report["test_interval"]
        ax.set_title(f"Figura 5. Hidrograma mensual TEST {start[:4]}–{end[:4]}{self._suffix()}", pad=12)
        ax.set_ylabel("Caudal mensual (m³/s)")
        ax.xaxis.set_major_locator(YearLocator())
        ax.xaxis.set_major_formatter(DateFormatter("%Y"))
        ax.legend(loc="upper right", ncol=5, frameon=False)
        ax.set_xlim(dates[0], dates[-1])

    def _contrasts(self, figure):
        ax = figure.subplots()
        for i, (name, _, _) in enumerate(CONTRASTS):
            item = self.evaluation["contrasts"][name]
            low, high = item["ci95_reduction_m3s"]
            if low is not None and high is not None:
                ax.hlines(i, low, high, color="black", lw=2)
                ax.vlines([low, high], i - .08, i + .08, color="black", lw=1.5)
            ax.plot(item["rmse_reduction_m3s"], i, "o", color="black", ms=8)
        ax.axvline(0, color="red", ls="--", lw=1)
        ax.set_yticks(range(len(CONTRASTS)), [item[1] for item in CONTRASTS])
        ax.invert_yaxis()
        ax.set_ylim(len(CONTRASTS) - .65, -.35)
        ax.set_xlabel("ΔRMSE (m³/s), IC 95 % por bloques")
        ax.set_title(f"Figura 6. Contrastes entre brazos en TEST{self._suffix()}", pad=12)

    def _partition(self, figure):
        figure.set_size_inches(15, 4)
        ax = figure.subplots()
        ax.set_axis_off()
        for i, (row, color) in enumerate(zip(self.partition_rows(), ("#1f77b4", "#9467bd", "#ff7f0e", "#2ca02c", "#d62728"))):
            x = i / 5
            ax.plot([x + .015, x + .185], [.56, .56], color=color, lw=12, solid_capstyle="butt")
            ax.text(x + .10, .78, row[0], ha="center", fontsize=15, weight="bold")
            years, months = row[1].split(" / ")
            ax.text(x + .10, .29, f"{years}\n{months} meses", ha="center", fontsize=13, linespacing=1.6)
        ax.set(xlim=(0, 1), ylim=(0, 1))
        ax.set_title("Partición temporal del protocolo experimental", fontsize=20, weight="bold", pad=20)
        figure.text(.5, .015, "Calibración, TRAIN y VALIDATION para desarrollo; TEST para evaluación final.",
                    ha="center", fontsize=11)

    def _table_figure(self, figure, key):
        headers, rows, widths = self.table(key)
        wrapped = [[textwrap.fill(str(cell), max(10, int(width * 120)), break_long_words=False)
                    for cell, width in zip(row, widths)] for row in [headers, *rows]]
        heights = [max(cell.count("\n") + 1 for cell in row) * .21 + .10 for row in wrapped]
        figure.set_size_inches(12, sum(heights) + .2)
        ax = figure.subplots()
        ax.set_axis_off()
        table = ax.table(cellText=wrapped[1:], colLabels=wrapped[0], colWidths=widths,
                         loc="center", cellLoc="left", colLoc="left", bbox=[0, 0, 1, 1])
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        total = sum(heights)
        for (row, col), cell in table.get_celld().items():
            cell.set_height(heights[row] / total)
            cell.set_edgecolor("black")
            cell.set_linewidth(.6)
            cell.PAD = .04
            cell.get_text().set_fontfamily("DejaVu Serif")
            if row == 0:
                cell.set_facecolor("#e8e8e8")
                cell.get_text().set_weight("bold")
            else:
                cell.set_facecolor("white")
