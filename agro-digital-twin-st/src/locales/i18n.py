"""
Internationalization and institutional labels for Plant-to-Watershed AI Lab.
"""

STRINGS = {
    "app_title": "Plant-to-Watershed AI Lab",
    "app_subtitle": "Coupling Individual Plant Models (Maize FSPM) with SWAT+ Hydrology & Downscaled Climate Projections",
    "app_description": "Laboratorio de Inteligencia Artificial para análisis exploratorio, entrenamiento leak-free, validación estadística y exportación de modelos reutilizables por FastAPI.",
    "nav_dashboard": "📊 1. Dashboard & Explorer",
    "nav_eda": "📈 2. EDA Multiescala",
    "nav_training": "⚙️ 3. Entrenamiento de Modelos",
    "nav_prediction": "🔮 4. Predicción Cuenca & Rendimiento",
    "nav_benchmarking": "🔬 5. Benchmarking & Validación Estadística",
    "nav_scenarios": "🌐 6. Simulador de Escenarios",
    "nav_reports": "📄 7. Reportes Técnicos",
    "sidebar_title": "Plant-to-Watershed Lab",
    "sidebar_version": "v2.0.0 (AI Lab MVP)",
    "sidebar_env": "Python 3.12 • Keras 3 • scikit-learn • XGBoost",
    "hypothesis_h0": "H0: El acoplamiento planta-cuenca no mejora la predicción de escorrentía respecto a SWAT+ estándar.",
    "hypothesis_h1": "H1: El gemelo multi-escala reduce el RMSE mensual de escorrentía en al menos 15% respecto a SWAT+ estándar y representa mejor la variabilidad espacial de rendimiento."
}


def t(key: str, default: str = "") -> str:
    """Returns translated string or key if not found."""
    return STRINGS.get(key, default or key)
