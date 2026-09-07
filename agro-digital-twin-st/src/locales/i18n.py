"""
Módulo de internacionalización y textos institucionales para AgroTwin-AI.
Proporciona la función t(key) para acceder a etiquetas y descripciones.
"""

STRINGS = {
    "app_title": "AgroTwin-AI — Deep Eco-Hydrology Platform",
    "app_subtitle": "Deep Surrogate Modeling para Predicción de Estrés Hídrico de Cultivo (CWSI) y Dosificación de Riego Inteligente",
    "app_description": "Plataforma de Inteligencia Artificial que acopla modelos fisiológicos vegetales con hidrología de cuenca SWAT bajo proyecciones de cambio climático.",
    "nav_eda": "📈 1. EDA & Dashboard",
    "nav_training": "⚙️ 2. Entrenamiento",
    "nav_inference": "🔍 3. Inferencia",
    "nav_statistics": "📊 4. Estadísticas",
    "nav_hypothesis": "🔬 5. Pruebas (Hipótesis / McNemar)",
    "nav_reports": "📄 6. Reportes",
    "sidebar_title": "AgroTwin-AI Lab",
    "sidebar_version": "v1.0.0 (MVP)",
    "sidebar_env": "Python 3.12 • Keras 3 • TensorFlow 2",
    "mcnemar.title": "Validación de Hipótesis y Pruebas Estadísticas",
    "mcnemar.theoretical_foundations": "Fundamentos Teóricos y Métricas de Rigor",
    "mcnemar.mcc_theory_title": "Prueba no paramétrica de Wilcoxon Signed-Rank",
    "mcnemar.mcc_theory_formula": "W = sum(rank(|d_i|) * sign(d_i))",
    "mcnemar.mcc_theory_purpose": "Propósito: Demostrar si las mejoras en error cuadrático (MSE) del modelo Deep Learning frente al baseline son estadísticamente significativas con p < 0.05.",
    "mcnemar.mcc_theory_advantages": "Ventaja: No asume distribución normal en los errores residuales de campo.",
}

def t(key: str, default: str = "") -> str:
    """Retorna la cadena traducida o la clave si no existe."""
    return STRINGS.get(key, default or key)
