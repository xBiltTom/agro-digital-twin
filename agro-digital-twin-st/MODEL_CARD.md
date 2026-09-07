# 🌽 Model Card: Plant-to-Watershed Digital Twin Models

## 1. Model Details
- **Model Family**: Plant-to-Watershed AI Lab Surrogates
- **Champion Architecture**: LSTM Autoencoder + Random Forest Hybrid (and Random Forest Residual Corrector)
- **Candidate Architectures**:
  - Random Forest Regressor (Scikit-Learn)
  - XGBoost Gradient Boosted Trees (XGBoost)
  - Support Vector Regression (SVR, RBF Kernel)
  - CNN-LSTM 1D-Temporal Hybrid (TensorFlow / Keras 3)
  - LSTM Sequence Autoencoder + Random Forest (TensorFlow + Scikit-Learn)
- **Version**: 1.0.0
- **Target Variables**:
  1. `monthly_runoff_mm` (Coupled monthly watershed runoff, mm/month)
  2. `monthly_streamflow_m3s` (Streamflow discharge at basin outlet, m³/s)
  3. `maize_yield_t_ha` (Annual grain yield of *Zea mays* at harvest, t/ha)
- **Primary Domain**: Agro-Hydrology, Corn Belt (*Zea mays*), SWAT+ (Soil and Water Assessment Tool).
- **License**: MIT / Academic Research Use

---

## 2. Intended Use & Scope
- **Primary Intended Uses**:
  - Fast surrogate modeling replacing computationally demanding SWAT+ and FSPM simulations.
  - Multi-scale scenario evaluation under climate change projections (CMIP6 SSP2-4.5, SSP5-8.5).
  - Residual correction of uncoupled SWAT+ baseline models by infusing individual plant physiological dynamics (LAI, rooting depth, stomatal transpiration, water stress).
  - Direct consumption via decoupled Python package into FastAPI microservices and Next.js digital twin dashboards (`agro-digital-twin`).
- **Out-of-Scope Uses**:
  - Direct operational flood control decision-making without field calibration against real USGS streamflow gauge observations.
  - Crop types other than Maize (*Zea mays*) without recalibrating physiological parameters.

---

## 3. Training Data & Provenance Notice
> [!WARNING]
> **SYNTHETIC DATASET NOTICE (DEMO / SYNTHETIC DATA)**
> The training dataset used in this laboratory was generated using the `SyntheticMultiScaleDatasetGenerator` simulating physical relationships derived from the literature (*Zea mays* physiology and Iowa Corn Belt SWAT+ hydrological characteristics). It serves architectural validation, hypothesis evaluation, and decoupling verification. For production deployments, real observational datasets (USGS streamflow, USDA NASS crop yields, Daymet/GridMET meteorology) must be substituted.

- **Spatial Granularity**: 3 Representative Corn Belt Watersheds (Cedar River, Raccoon River, Iowa River) with 4 Hydrological Response Units (HRUs) each (12 distinct spatial units).
- **Temporal Span**: 2000-01-01 to 2019-12-01 (20 years monthly = 240 timesteps per HRU; 2,880 records total).
- **Seasonal Yield Aggregation**: For `maize_yield_t_ha`, monthly records during the growing season (May–October) are aggregated into 1 sample per HRU per year (240 annual samples) with cumulative GDD (base 10°C), seasonal precipitation, seasonal ET, peak LAI, and maximum root depth.

---

## 4. Input Features Contract (4 Coupled Scales)
Models strictly validate inputs using `ModelFeatureSchema`:
- **Level 1 (Plant FSPM)**: `lai` [0–8], `root_depth_m` [0.05–3.0], `transpiration_mm` [0–250], `water_stress` [0–1].
- **Level 2 (Field Scale)**: `et_mm` [0–300].
- **Level 3 (Watershed SWAT+)**: `soil_moisture` [5–50%], `infiltration_mm` [0–400].
- **Level 4 (Regional Climate)**: `precip_mm` [0–500], `temp_mean_c` [-30–45°C], `solar_radiation` [0–40 MJ/m²/d].
- **SWAT+ Baseline (Residual Mode)**: `swat_baseline_runoff_mm`, `swat_baseline_streamflow_m3s`.

---

## 5. Methodological Rigor & Data Leakage Prevention
1. **3-Way Leak-Free Partition**: Data is formally divided into TRAIN (65%), VALIDATION (15%), and TEST (20%). Preprocessors (`StandardScaler`) are fit strictly on TRAIN. TEST data is never observed during training or hyperparameter tuning.
2. **3D Temporal Sequence Isolation**: Sequence windows `(samples, timesteps, features)` are constructed strictly within isolated `(watershed_id, hru_id)` groups in forward chronological order. Window $[t - L + 1, \dots, t]$ predicts target at $t$. Zero future data leaks into the past.
3. **Multi-Criteria Ranking**: Champion selection uses unit-independent ordinal ranking across $NSE$ (weight 0.35), $RMSE$ (0.35), $|PBIAS|$ (0.15), and $MAE$ (0.15), preventing arbitrary single-metric bias.

---

## 6. Evaluation Metrics & Performance
Hydrological evaluation follows ASCE / Moriasi et al. standards:
- **Nash-Sutcliffe Efficiency ($NSE$)**: $> 0.90$ (Very Good)
- **Percent Bias ($PBIAS$)**: $|\text{PBIAS}| < 5\%$ (Very Good)
- **RMSE & MAE**: Residual correction reduces SWAT+ baseline error by $> 15\%$, rejecting $H_0$ with Wilcoxon $p < 0.001$.

---

## 7. Artifact Bundle & FastAPI Deployment
All trained models export self-contained bundles:
```
artifacts/{target}/champion/
├── model.joblib / model.keras / (encoder.keras + rf_head.joblib)
├── preprocessing.joblib
├── feature_schema.json
├── metadata.json
└── metrics.json
```
- **Lazy TensorFlow Loading**: Non-DL models (Random Forest, XGBoost, SVR) can be loaded and executed in production without installing TensorFlow.
- **Inference Service**: Executed via `ModelBundle.load(path).predict(payload)`.
