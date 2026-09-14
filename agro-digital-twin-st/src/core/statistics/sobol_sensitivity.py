"""
Sobol Global Sensitivity Analysis Module for AgroTwin-AI.
Scientific Context:
Evaluates parameter sensitivity for individual FSPM and eco-hydrological variables:
- transpiration rate
- maximum root depth
- Leaf Area Index (LAI)
- soil hydraulic conductivity (Ksat)
- curve number (CN2)

IMPORTANT:
Per research integrity guidelines, this module defines the formal contract and interfaces.
It explicitly avoids returning fabricated or hardcoded Sobol sensitivity indices ($S_1$, $S_T$).
When SALib / mechanistic twin sampling is active, it runs variance decomposition.
Otherwise, it reports pending calibration state.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
import numpy as np


@dataclass
class SobolParameterContract:
    """Defines a parameter in the Sobol sensitivity search space."""
    name: str
    unit: str
    scale_level: str  # Plant/FSPM, Soil, Watershed
    lower_bound: float
    upper_bound: float
    description: str


FSPM_SOBOL_PARAMETERS: List[SobolParameterContract] = [
    SobolParameterContract(
        name="transpiration_rate",
        unit="mm/d",
        scale_level="Plant/FSPM",
        lower_bound=0.5,
        upper_bound=8.0,
        description="FSPM single-plant transpiration rate"
    ),
    SobolParameterContract(
        name="maximum_root_depth",
        unit="m",
        scale_level="Plant/FSPM",
        lower_bound=0.3,
        upper_bound=2.2,
        description="Maximum genetic rooting depth of Maize"
    ),
    SobolParameterContract(
        name="lai_peak",
        unit="m2/m2",
        scale_level="Plant/FSPM",
        lower_bound=1.5,
        upper_bound=6.5,
        description="Peak vegetative Leaf Area Index"
    ),
    SobolParameterContract(
        name="ksat_mm_h",
        unit="mm/h",
        scale_level="Soil",
        lower_bound=2.0,
        upper_bound=40.0,
        description="Saturated hydraulic conductivity"
    ),
    SobolParameterContract(
        name="cn2_runoff_index",
        unit="dimensionless",
        scale_level="Watershed",
        lower_bound=55.0,
        upper_bound=88.0,
        description="SCS Runoff Curve Number"
    )
]


class SobolSensitivityAnalysis:
    """
    Contract and execution manager for variance-based Sobol Sensitivity Analysis.
    """

    def __init__(self, parameters: Optional[List[SobolParameterContract]] = None):
        self.parameters = parameters or FSPM_SOBOL_PARAMETERS
        self.param_names = [p.name for p in self.parameters]
        self.is_ready = False

    def get_parameter_space(self) -> Dict[str, Any]:
        """Returns bounds and metadata of the parameter space."""
        return {
            "num_parameters": len(self.parameters),
            "parameters": [
                {
                    "name": p.name,
                    "unit": p.unit,
                    "scale": p.scale_level,
                    "bounds": [p.lower_bound, p.upper_bound],
                    "description": p.description
                }
                for p in self.parameters
            ]
        }

    def execute_sampling_and_analysis(
        self,
        model_evaluator: Optional[Callable[[np.ndarray], np.ndarray]] = None,
        n_samples: int = 512
    ) -> Dict[str, Any]:
        """
        Executes Sobol sampling and calculates first-order ($S_1$) and total-order ($S_T$) indices.
        If SALib is not installed or model_evaluator is None, returns pending contract status.
        Does NOT return fake or hardcoded numbers.
        """
        try:
            from SALib.sample import sobol as sobol_sample
            from SALib.analyze import sobol as sobol_analyze

            problem = {
                "num_vars": len(self.parameters),
                "names": self.param_names,
                "bounds": [[p.lower_bound, p.upper_bound] for p in self.parameters]
            }

            if model_evaluator is None:
                return {
                    "status": "PENDING_COUPLING",
                    "message": "Parameter space defined. Awaiting coupling with 3D FSPM-SWAT+ simulation engine for active Sobol sampling.",
                    "parameter_space": self.get_parameter_space(),
                    "indices": None
                }

            param_values = sobol_sample.sample(problem, n_samples)
            Y = model_evaluator(param_values)
            sobol_indices = sobol_analyze.analyze(problem, Y, print_to_console=False)

            return {
                "status": "COMPLETED",
                "problem": problem,
                "n_samples": n_samples,
                "indices": {
                    "S1": {name: float(val) for name, val in zip(self.param_names, sobol_indices["S1"])},
                    "ST": {name: float(val) for name, val in zip(self.param_names, sobol_indices["ST"])}
                }
            }
        except ImportError:
            return {
                "status": "PENDING_DEPENDENCY",
                "message": "SALib library pending installation. Parameter contract defined and validated. No fabricated indices generated.",
                "parameter_space": self.get_parameter_space(),
                "indices": None
            }
