"""
UI Tabs package for Plant-to-Watershed AI Lab.
"""

from . import (
    tab_dashboard,
    tab_eda,
    tab_training,
    tab_prediction,
    tab_benchmarking,
    tab_scenarios,
    tab_reports
)

# Backwards compatibility aliases
tab_diagnosis = tab_prediction
tab_statistics = tab_benchmarking
tab_mcnemar = tab_benchmarking

__all__ = [
    "tab_dashboard",
    "tab_eda",
    "tab_training",
    "tab_prediction",
    "tab_benchmarking",
    "tab_scenarios",
    "tab_reports",
    "tab_diagnosis",
    "tab_statistics",
    "tab_mcnemar"
]
