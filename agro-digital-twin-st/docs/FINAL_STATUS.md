# 🌽 Plant-to-Watershed AI Lab — Final Consolidation & Technical Status Report

**Project Title**: *"From Plant to Watershed: A Multi-Scale Digital Twin Framework Coupling Individual Plant Models with SWAT Hydrology and Downscaled Climate Projections"*  
**Repository**: `agro-digital-twin-st` (Streamlit AI Lab & Decoupled Scientific Core)  
**Target Consumer**: `agro-digital-twin` (FastAPI + Next.js digital twin platform)  
**Date of Consolidation**: 2026-09-06  
**Status**: **CONSOLIDATED & PRODUCTION-READY FOR FASTAPI CONSUMPTION**  

---

## 1. Executive Summary

This final consolidation iteration freezes `agro-digital-twin-st` as a methodologically rigorous, leak-free, multi-scale AI laboratory. The application couples:
1. **Level 1 (Plant Scale)**: Individual *Zea mays* functional-structural plant modeling (FSPM: canopy architecture, root depth, dynamic LAI, stomatal transpiration, water stress).
2. **Level 2 (Field Scale)**: Soil water balance, infiltration, and field evapotranspiration ($ET$).
3. **Level 3 (Watershed Scale)**: SWAT+ hydrological routing across Hydrological Response Units (HRUs), surface runoff, and streamflow.
4. **Level 4 (Regional Climate)**: Historical meteorological forcing and CMIP6 climate scenarios (SSP2-4.5, SSP5-8.5).

The laboratory provides exploratory data analysis, leak-free training of traditional and hybrid deep learning models, objective hypothesis testing against uncoupled SWAT+ baselines, multi-format reporting, and export of standardized, self-contained **Artifact Bundles** consumable without Streamlit by FastAPI.

---

## 2. Core Methodological Corrections (P0 Requirements)

### P0.1: Real 3D Temporal Sequences for CNN-LSTM
- **Implementation**: [`src/core/features/sequences.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/agro-digital-twin-st/src/core/features/sequences.py) and [`src/core/models/deep_learning.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/agro-digital-twin-st/src/core/models/deep_learning.py).
- **Format**: `(samples, timesteps, features)` strictly formed within `(watershed_id, hru_id)` spatial units sorted chronologically.
- **Convention**: Window $[t - L + 1, \dots, t]$ predicts target $y(t)$.
- **Isolation**: Sequences never cross across HRU boundaries, watershed boundaries, or split partitions. Zero future temporal leakage.

### P0.2: Real 3D Temporal Input for LSTM-AE + RF
- **Implementation**: [`src/core/models/hybrid_ae_rf.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/agro-digital-twin-st/src/core/models/hybrid_ae_rf.py).
- **Workflow**: Sequence Autoencoder reconstructs the 3D window and compresses temporal dynamics into a latent vector $z$, which is concatenated with the current state $[x(t), z]$ to train a Random Forest regressor.

### P0.3: Formal 3-Way Leak-Free Split (Train, Validation, Test)
- **Implementation**: [`src/core/training/splitters.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/agro-digital-twin-st/src/core/training/splitters.py).
- **Splits**: `Temporal3WaySplitter` (Train: Past 65%, Val: Middle 15%, Test: Future 20%) and `Watershed3WaySplitter` (spatial holdout across independent watersheds).
- **Zero Leakage**: Preprocessor (`MultiScaleDataPreprocessor`) is fit **strictly on the TRAIN partition**. Test set is held out until final model evaluation.

### P0.4: Benchmarking with Real Predictions (No Artificial Noise)
- **Implementation**: [`src/ui/tabs/tab_benchmarking.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/agro-digital-twin-st/src/ui/tabs/tab_benchmarking.py).
- **Elimination of Noise**: Removed synthetic `y_twin = y_true + normal(...)`. Inferences are executed directly using `ModelBundle.load("artifacts/monthly_runoff_mm/champion")` on the held-out TEST partition.
- **Provenance Notice**: Explicit disclaimer badge: `DEMO / SYNTHETIC DATA — Evaluación ilustrativa con datos sintéticos`.

### P0.5: Seasonal Crop Yield Dataset
- **Implementation**: [`src/core/datasets/yield_dataset.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/agro-digital-twin-st/src/core/datasets/yield_dataset.py).
- **Aggregation**: Eliminates artificial monthly zeros by aggregating May–October growing season into 1 sample per HRU per year with cumulative GDD (base 10°C, cutoff 30°C), peak LAI, seasonal precipitation, and seasonal ET.

### P0.6: Unit-Independent Multi-Criteria Champion Ranking
- **Implementation**: [`src/core/metrics.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/agro-digital-twin-st/src/core/metrics.py) (`rank_models_multicriteria`).
- **Formulation**: Hydrological ordinal ranking using weighted composite rank: $0.35 \times \text{Rank}(NSE) + 0.35 \times \text{Rank}(RMSE) + 0.15 \times \text{Rank}(|PBIAS|) + 0.15 \times \text{Rank}(MAE)$. Crop yield uses $0.50 \times \text{Rank}(RMSE) + 0.25 \times \text{Rank}(MAE) + 0.25 \times \text{Rank}(R^2)$.

### P0.7 & P0.9: Decoupled ModelBundle & Lazy TensorFlow Loading
- **Implementation**: [`src/core/inference/bundle.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/agro-digital-twin-st/src/core/inference/bundle.py).
- **Lazy Loading**: Removed module-level `import tensorflow`. Traditional models (Random Forest, XGBoost, SVR) can be loaded and executed in production environments where TensorFlow is not installed.
- **Input Robustness**: Supports single dict payloads, lists of dicts, pandas DataFrames, 2D NumPy arrays, and 3D temporal sequence arrays.

### P0.8: Consolidated Trainer Pipeline
- **Implementation**: [`src/core/training/trainer.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/agro-digital-twin-st/src/core/training/trainer.py).
- Integrates 3-way split, sequence construction, preprocessor fitting on TRAIN only, hyperparameter tuning, evaluation on TEST, multi-criteria ranking, and bundle export.

### P0.10: Complete Unit Test Suite
- **Result**: **28 passed in 34.25s** across 9 test modules covering dataset generation, schemas, inference, metrics, models, sequences, splits, yield datasets, and auth/database.

---

## 3. Architecture Extensions (P1 Requirements)

### P1.1: Hyperparameter Tuning in FAST vs FULL Mode
- Implemented in `MultiScaleTrainer` with grid/random validation tuning on TRAIN + VAL for traditional models in FULL mode, while retaining instant fast execution in FAST mode.

### P1.2: Database Persistence (PostgreSQL & SQLite Fallback)
- **Implementation**: [`src/infrastructure/database/connection.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/agro-digital-twin-st/src/infrastructure/database/connection.py) and [`src/infrastructure/database/repositories.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/agro-digital-twin-st/src/infrastructure/database/repositories.py).
- Uses `DATABASE_URL` environment variable for PostgreSQL connections with automatic fallback to local SQLite (`data/agrotwin.db`). Provides ORM models and repository implementations for users, training runs, and prediction logs.

### P1.3: Authentication & 4 Role RBAC
- **Implementation**: [`src/infrastructure/auth/`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/agro-digital-twin-st/src/infrastructure/auth/).
- 4 Roles:
  - `ADMIN`: Complete system control, user management, configuration.
  - `RESEARCHER`: Training models, Sobol sensitivity, scenario exploration, reporting.
  - `ANALYST`: Inference, benchmarking, exploration, reporting.
  - `GUEST`: Read-only access to pre-computed dashboards (cannot train or export).
- Password security: `bcrypt` hashing with salt rounds. Pre-seeded test users (`admin`, `researcher`, `analyst`, `guest`).
- UI Sidebar Integration: Role badge, quick switcher, and capability enforcement.

### P1.4: Word Document (.docx) Technical Report Export
- **Implementation**: [`src/core/docx_generator.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/agro-digital-twin-st/src/core/docx_generator.py) and [`src/ui/tabs/tab_reports.py`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/agro-digital-twin-st/src/ui/tabs/tab_reports.py).
- Downloadable technical reports in Microsoft Word format (.docx) alongside PDF (ReportLab) and Excel (.xlsx).

### P1.5: Prominent CRISP-DM Labels
- Every tab header displays its explicit CRISP-DM phase:
  - Tab 1: `[CRISP-DM: Business / Domain Understanding]`
  - Tab 2: `[CRISP-DM: Data Understanding]`
  - Tab 3: `[CRISP-DM: Data Preparation & Simulation Coupling]`
  - Tab 4: `[CRISP-DM: Modeling]`
  - Tab 5: `[CRISP-DM: Evaluation & Hypothesis Testing]`
  - Tab 6: `[CRISP-DM: Deployment & API Serving]`
  - Tab 7: `[CRISP-DM: Academic Reporting & Governance]`

---

## 4. Verification & Testing Evidence

```bash
$ ./venv/bin/pytest
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
collected 28 items

tests/test_auth_db.py ....                                               [ 14%]
tests/test_dataset.py ..                                                 [ 21%]
tests/test_feature_schema.py ...                                         [ 32%]
tests/test_inference.py ..                                               [ 39%]
tests/test_metrics.py ....                                               [ 53%]
tests/test_models.py .....                                               [ 71%]
tests/test_sequences.py ..                                               [ 78%]
tests/test_splits.py ....                                                [ 92%]
tests/test_yield_dataset.py ..                                           [100%]

============================= 28 passed in 34.25s ==============================
```

Headless Streamlit verification:
```bash
$ ./venv/bin/python -c "import app; print('App imported successfully!')"
App imported successfully!
```

---

## 5. Instructions to Run

1. **Activate Virtual Environment**:
   ```bash
   source venv/bin/activate
   ```
2. **Launch Streamlit Lab**:
   ```bash
   streamlit run app.py
   ```
3. **Execute Unit Tests**:
   ```bash
   pytest
   ```
4. **Consume from FastAPI**:
   Refer to [`docs/FASTAPI_INTEGRATION.md`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/agro-digital-twin-st/docs/FASTAPI_INTEGRATION.md) and [`MODEL_CARD.md`](file:///home/bilton/Universidad/CICLO-VIII/ING-SOFTWARE-II/SESI%C3%93N-O1/gemelos-digitales/agro-digital-twin-st/MODEL_CARD.md).
